"""Spec 003, R1 e R3: cada fonte de sources.yaml tem adaptador, amostra real e atribuição,
e passa por fetch (servidor local) e ingest sem rede."""

from pathlib import Path

import pytest

from namescommons.adapters import load_adapter
from namescommons.pipeline import fetch_sources, ingest_sources
from namescommons.sources import load_sources

RAIZ = Path(__file__).resolve().parent.parent
FONTES = load_sources(RAIZ / "sources.yaml")
IDS = sorted(i for i, f in FONTES.items() if f.adapter)
ATRIBUICAO = (RAIZ / "tests" / "fixtures" / "ATRIBUICAO.md").read_text(encoding="utf-8")


def test_ha_fontes_com_adaptador():
    assert IDS


@pytest.mark.parametrize("source_id", IDS)
def test_amostra_e_atribuicao(source_id):
    mod = load_adapter(source_id)
    pasta = RAIZ / "tests" / "fixtures" / source_id
    arquivos = [p for p in pasta.iterdir() if not p.name.startswith(".")]
    assert sorted(p.name for p in arquivos) == sorted(r.filename for r in mod.RESOURCES)
    assert sum(p.stat().st_size for p in arquivos) < 20_000
    linha = next(l for l in ATRIBUICAO.splitlines() if l.startswith(f"| `{source_id}` |"))
    assert f"| {FONTES[source_id].license} |" in linha


@pytest.mark.parametrize("source_id", IDS)
def test_fetch_e_ingest_sobre_a_amostra(source_id, servir_fixtures, tmp_path):
    fonte = FONTES[source_id]
    servidor = servir_fixtures(load_adapter(source_id))
    fetch_sources([fonte], tmp_path)
    obs = ingest_sources([fonte], FONTES, tmp_path, offline=True)
    assert len(servidor.requisicoes) == len(load_adapter(source_id).RESOURCES)
    assert obs
    assert {(o.source_id, o.country, o.count_type) for o in obs} == {(source_id, fonte.country, fonte.count_type)}
