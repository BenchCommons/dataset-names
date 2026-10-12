"""Spec 004, R4.6 e critério de aceite 5: variant_links pela CLI."""

import json
import shutil
from pathlib import Path

import pytest

from namescommons.cli import main
from namescommons.io import read_links

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
FONTES = str(RAIZ / "sources.yaml")


@pytest.fixture
def cache(tmp_path):
    shutil.copytree(FIXTURES / "wikidata", tmp_path / "cache" / "wikidata")
    return str(tmp_path / "cache")


def test_ingest_links_e_build_links(cache, tmp_path, capsys):
    obs, ligacoes = tmp_path / "t" / "observations.parquet", tmp_path / "t" / "variant_links.parquet"
    assert main(["ingest", "wikidata", "--offline", "--cache", cache, "--sources", FONTES,
                 "--out", str(obs), "--links", str(ligacoes)]) == 0
    saida = capsys.readouterr().out
    assert "OK: 22 observações de 1 fonte" in saida and "47 ligações em" in saida
    links = read_links(ligacoes)
    assert len(links) == 47 and {v.source_id for v in links} == {"wikidata"}
    dist = tmp_path / "dist"
    assert main(["build", str(obs), "--links", str(ligacoes), "--sources", FONTES,
                 "--out", str(dist), "--release", "2026.10"]) == 0
    assert read_links(dist / "variant_links.parquet") == links
    manifest = json.loads((dist / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.1.0"
    assert manifest["files"]["variant_links.parquet"]["rows"] == 47


def test_ingest_sem_links_nao_grava_tabela(cache, tmp_path):
    obs = tmp_path / "t" / "observations.parquet"
    assert main(["ingest", "wikidata", "--offline", "--cache", cache, "--sources", FONTES, "--out", str(obs)]) == 0
    assert sorted(p.name for p in obs.parent.iterdir()) == ["observations.parquet"]


def test_build_recusa_tabela_invalida(cache, tmp_path, capsys):
    obs, ligacoes = tmp_path / "observations.parquet", tmp_path / "variant_links.parquet"
    assert main(["ingest", "wikidata", "--offline", "--cache", cache, "--sources", FONTES,
                 "--out", str(obs), "--links", str(ligacoes)]) == 0
    fontes = tmp_path / "sources.yaml"
    texto = Path(FONTES).read_text(encoding="utf-8").replace("id: wikidata", "id: wikidata-x")
    fontes.write_text(texto, encoding="utf-8")
    capsys.readouterr()
    assert main(["build", str(obs), "--links", str(ligacoes), "--sources", str(fontes),
                 "--out", str(tmp_path / "dist"), "--release", "2026.10"]) == 1
    assert "source_id" in capsys.readouterr().err


def test_build_com_links_ausente(tmp_path, cache, capsys):
    obs = tmp_path / "observations.parquet"
    assert main(["ingest", "wikidata", "--offline", "--cache", cache, "--sources", FONTES, "--out", str(obs)]) == 0
    assert main(["build", str(obs), "--links", str(tmp_path / "nada.parquet"), "--sources", FONTES,
                 "--out", str(tmp_path / "dist"), "--release", "2026.10"]) == 1
    assert "arquivo não encontrado" in capsys.readouterr().err


def test_run_grava_variant_links_so_com_fonte_de_ligacoes(tmp_path):
    fontes = tmp_path / "sources.yaml"
    entradas = Path(FONTES).read_text(encoding="utf-8").split("\n  - id: ")
    fontes.write_text(entradas[0] + "\n  - id: " + next(e for e in entradas if e.startswith("wikidata")),
                      encoding="utf-8")
    cache = tmp_path / "cache"
    shutil.copytree(FIXTURES / "wikidata", cache / "wikidata")
    assert main(["run", "--offline", "--cache", str(cache), "--sources", str(fontes),
                 "--out", str(tmp_path / "dist"), "--release", "2026.10"]) == 0
    assert len(read_links(tmp_path / "dist" / "variant_links.parquet")) == 47
    sem = tmp_path / "sem.yaml"
    sem.write_text(entradas[0] + "\n  - id: " + entradas[4], encoding="utf-8")
    shutil.copytree(FIXTURES / "no-ssb-fornavn", cache / "no-ssb-fornavn")
    assert main(["run", "--offline", "--cache", str(cache), "--sources", str(sem),
                 "--out", str(tmp_path / "dist2"), "--release", "2026.10"]) == 0
    assert not (tmp_path / "dist2" / "variant_links.parquet").exists()
