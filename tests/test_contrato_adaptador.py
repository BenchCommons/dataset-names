"""Spec 003, R2: regras do contrato do adaptador que a spec 002 deixou implícitas (issue #8).

parse_count, parse_code, SourceFiles e load_adapter são testados no tools-dataset (spec 007, R2.6).
"""

import shutil
from datetime import date
from pathlib import Path

import pytest

from namescommons.adapters import RawRecord
from namescommons.pipeline import PipelineError, RecordError, ingest_sources, select_sources, to_observations
from namescommons.sources import load_sources, parse_sources

FIXTURES = Path(__file__).parent / "fixtures"


def _fonte(**campos):
    base = {"id": "pt-x", "name": "x", "url": "https://x.example", "license": "CC0-1.0",
            "attribution": "x", "country": "PT", "count_type": "births", "primary": True,
            "suppression": None, "retrieved": date(2026, 1, 1)}
    return next(iter(parse_sources([{**base, **campos}]).values()))


# R2.1: o adaptador converte os valores; o pipeline confere na ordem do arquivo -------------------

@pytest.mark.parametrize("campos, trecho", [
    ({"kind": "first"}, "registro 2: kind 'first' inválido; use 'given' ou 'family'"),
    ({"gender": "Mujer"}, "registro 2: gender 'Mujer' inválido; use 'F', 'M' ou vazio"),
    ({"gender": "1"}, "registro 2: gender '1' inválido"),
    ({"country": "PRT"}, "registro 2: country 'PRT' fora da ISO 3166-1 alfa-2"),
    ({"country": "pt"}, "registro 2: country 'pt' fora da ISO 3166-1 alfa-2"),
])
def test_r2_1_valor_nao_convertido_nomeia_a_posicao_no_arquivo(campos, trecho):
    ok = {"name": "Ana", "kind": "given", "country": "PT", "gender": "F", "year": 2020, "count": 1}
    ruim = RawRecord(**{**ok, "name": "Maria", **campos})
    with pytest.raises(RecordError) as e:
        to_observations([RawRecord(**ok), ruim], _fonte())
    assert str(e.value).startswith(trecho)


# R2.3: valores suprimidos são omitidos, nunca emitidos com count vazio ------------------------------

def test_r2_3_count_vazio_em_fonte_com_contagem_e_recusado():
    with pytest.raises(RecordError, match="registro 1: count vazio numa fonte 'population'; valor suprimido"):
        to_observations([RawRecord("Ana", "given", "PT", "F", 2020, None)], _fonte(count_type="population"))


def test_r2_3_count_em_fonte_attested_e_recusado():
    with pytest.raises(RecordError, match="registro 1: count 3 numa fonte 'attested'"):
        to_observations([RawRecord("Ana", "given", None, None, None, 3)],
                        _fonte(country=None, count_type="attested"))


# R2.5: teste de adaptador contra o servidor local ----------------------------------------------

def test_r2_5_servir_fixtures_baixa_do_servidor_local(servir_fixtures, tmp_path):
    import adaptadores.exemplo
    servidor = servir_fixtures(adaptadores.exemplo)
    fontes = load_sources(FIXTURES / "sources.yaml")
    obs = ingest_sources(select_sources(fontes, ["exemplo"]), fontes, tmp_path, adapters="adaptadores")
    assert len(obs) == 8
    assert sorted(servidor.caminhos()) == ["/exemplo/primeiros.csv", "/exemplo/sobrenomes.csv"]
    assert all(r.url.startswith("http://127.0.0.1:") for r in adaptadores.exemplo.RESOURCES)


# R2.6: mensagens de erro --------------------------------------------------------------------------

def test_r2_6_ingest_com_chave_errada_nomeia_a_fonte(tmp_path, monkeypatch):
    import adaptadores.exemplo
    monkeypatch.setattr(adaptadores.exemplo, "parse", lambda arquivos: iter([arquivos["nomes.csv"]]))
    shutil.copytree(FIXTURES / "exemplo", tmp_path / "exemplo")
    fontes = load_sources(FIXTURES / "sources.yaml")
    with pytest.raises(PipelineError, match="fonte 'exemplo': parse asked for file 'nomes.csv', outside RESOURCES"):
        ingest_sources([fontes["exemplo"]], fontes, tmp_path, offline=True, adapters="adaptadores")
