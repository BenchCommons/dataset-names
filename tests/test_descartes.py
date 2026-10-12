"""Spec 006, R1: canal de descarte do adaptador (RawDrop), contado por fonte e guardado no Parquet."""

import json
import logging
import shutil
from pathlib import Path

import pytest
import yaml

import namescommons.adapters.nz_dia_births as nz
from namescommons.adapters import RawDrop, RawRecord
from namescommons.cli import main
from namescommons.io import read_dropped, read_observations, write_observations
from namescommons.pipeline import Drops, PipelineError, ingest_sources, select_sources
from namescommons.sources import load_sources

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fontes():
    return load_sources(RAIZ / "sources.yaml")


def _cache(tmp_path: Path, *ids: str) -> Path:
    cache = tmp_path / "cache"
    for i in ids:
        shutil.copytree(FIXTURES / i, cache / i)
    return cache


def _ingerir(fontes, cache, ids, drops):
    return ingest_sources(select_sources(fontes, list(ids)), fontes, cache, offline=True, drops=drops)


def test_pipeline_conta_descartes_por_fonte(fontes, tmp_path):
    cache = _cache(tmp_path, "nz-dia-births", "ie-cso-births")
    drops: dict[str, Drops] = {}
    _ingerir(fontes, cache, ["nz-dia-births", "ie-cso-births"], drops)
    assert drops["nz-dia-births"].as_dict() == {"lines": 3, "records": 49}
    assert drops["nz-dia-births"].forms == {"K�whai", "M?ia", "N�kau"}
    assert drops["ie-cso-births"].as_dict() == {"lines": 0, "records": 0}


def test_pipeline_avisa_descartes_no_logger(fontes, tmp_path, caplog):
    cache = _cache(tmp_path, "nz-dia-births", "ie-cso-births")
    with caplog.at_level(logging.WARNING, logger="namescommons.pipeline"):
        _ingerir(fontes, cache, ["nz-dia-births", "ie-cso-births"], {})
    avisos = [r.getMessage() for r in caplog.records if r.name == "namescommons.pipeline"]
    assert avisos == [
        "nz-dia-births: 3 linha(s) descartada(s) pelo adaptador, 49 registro(s), 3 forma(s): "
        "'K�whai', 'M?ia', 'N�kau'"
    ]


@pytest.mark.parametrize("descarte, trecho", [
    (RawDrop(name=1, count=2), "descarte 1: 'name' deve ser texto"),
    (RawDrop(name="M?ia", count=-1), "descarte 1: 'count' deve ser inteiro não negativo"),
    (RawDrop(name="M?ia", count="3"), "descarte 1: 'count' deve ser inteiro não negativo"),
    (RawDrop(name="M?ia", count=True), "descarte 1: 'count' deve ser inteiro não negativo"),
])
def test_descarte_invalido_e_erro(fontes, tmp_path, monkeypatch, descarte, trecho):
    monkeypatch.setattr(nz, "parse", lambda files: iter([RawRecord("Mia", "given", "NZ", "F", 2025, 10), descarte]))
    with pytest.raises(PipelineError, match=f"fonte 'nz-dia-births': {trecho}"):
        _ingerir(fontes, _cache(tmp_path, "nz-dia-births"), ["nz-dia-births"], {})


def test_descarte_sem_contagem_conta_a_linha(fontes, tmp_path, monkeypatch):
    monkeypatch.setattr(nz, "parse", lambda files: iter([RawDrop("M?ia", None), RawRecord("Mia", "given", "NZ", "F", 2025, 10)]))
    drops: dict[str, Drops] = {}
    _ingerir(fontes, _cache(tmp_path, "nz-dia-births"), ["nz-dia-births"], drops)
    assert drops["nz-dia-births"].as_dict() == {"lines": 1, "records": 0}


def test_numeracao_de_registros_ignora_descartes(fontes, tmp_path, monkeypatch):
    monkeypatch.setattr(nz, "parse", lambda files: iter([
        RawDrop("M?ia", 10), RawRecord("Mia", "given", "NZ", "F", 2025, 10), RawRecord("Ana", "outro", "NZ", "F", 2025, 10),
    ]))
    with pytest.raises(PipelineError, match="registro 2: kind 'outro'"):
        _ingerir(fontes, _cache(tmp_path, "nz-dia-births"), ["nz-dia-births"], {})


def test_ingest_grava_descartes_no_parquet(tmp_path):
    cache = _cache(tmp_path, "nz-dia-births", "ie-cso-births")
    out = tmp_path / "observations.parquet"
    assert main(["ingest", "nz-dia-births", "ie-cso-births", "--offline", "--cache", str(cache), "--out", str(out)]) == 0
    assert read_dropped(out) == {
        "ie-cso-births": {"lines": 0, "records": 0},
        "nz-dia-births": {"lines": 3, "records": 49},
    }


def test_parquet_sem_metadados_da_descartes_desconhecidos(observacoes, tmp_path):
    write_observations(observacoes, tmp_path / "o.parquet")
    assert read_dropped(tmp_path / "o.parquet") is None


def _build(obs, out):
    return main(["build", str(obs), "--out", str(out), "--release", "2026.10"])


def _manifesto(out: Path) -> dict:
    return json.loads((out / "manifest.json").read_text(encoding="utf-8"))


def test_build_le_descartes_do_parquet(tmp_path):
    """Spec 006, R1.4 e R2.1: ingest grava, build lê e o manifesto mostra."""
    cache = _cache(tmp_path, "nz-dia-births")
    obs = tmp_path / "observations.parquet"
    assert main(["ingest", "nz-dia-births", "--offline", "--cache", str(cache), "--out", str(obs)]) == 0
    assert _build(obs, tmp_path / "dist") == 0
    (nz_,) = _manifesto(tmp_path / "dist")["sources"]
    assert nz_["dropped"] == {"lines": 3, "records": 49}
    assert nz_["observations"] == 15
    assert read_dropped(tmp_path / "dist" / "observations.parquet") == {"nz-dia-births": {"lines": 3, "records": 49}}


def test_build_sem_metadados_deixa_dropped_nulo(tmp_path):
    cache = _cache(tmp_path, "nz-dia-births")
    obs = tmp_path / "observations.parquet"
    assert main(["ingest", "nz-dia-births", "--offline", "--cache", str(cache), "--out", str(obs)]) == 0
    write_observations(read_observations(obs), obs)  # regrava sem metadados, como antes da spec 006
    assert _build(obs, tmp_path / "dist") == 0
    assert _manifesto(tmp_path / "dist")["sources"][0]["dropped"] is None


def test_run_grava_descartes_no_manifesto(tmp_path):
    cache = _cache(tmp_path, "nz-dia-births", "ie-cso-births")
    dados = yaml.safe_load((RAIZ / "sources.yaml").read_text(encoding="utf-8"))
    dados["sources"] = [f for f in dados["sources"] if f["id"] in ("nz-dia-births", "ie-cso-births")]
    sources = tmp_path / "sources.yaml"
    sources.write_text(yaml.safe_dump(dados), encoding="utf-8")
    out = tmp_path / "dist"
    assert main(["run", "--offline", "--cache", str(cache), "--sources", str(sources), "--out", str(out),
                 "--release", "2026.10"]) == 0
    assert {s["id"]: s["dropped"] for s in _manifesto(out)["sources"]} == {
        "ie-cso-births": {"lines": 0, "records": 0}, "nz-dia-births": {"lines": 3, "records": 49},
    }
