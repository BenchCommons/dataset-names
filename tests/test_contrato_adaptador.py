"""Spec 003, R2: regras do contrato do adaptador que a spec 002 deixou implícitas (issue #8)."""

import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

from namescommons.adapters import (
    AdapterError, FormatError, RawRecord, SourceFiles, load_adapter, parse_code, parse_count,
)
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


# R2.2: auxiliares de conversão ------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [("5", 5), (" 1532 ", 1532), ("0", 0), ("<5", None), ("..", None)])
def test_r2_2_parse_count(texto, esperado):
    assert parse_count(texto, {"<5", ".."}) == esperado


@pytest.mark.parametrize("texto", ["", "1.5", "-3", "x", "<3", "١٢"])
def test_r2_2_parse_count_recusa_o_que_nao_conhece(texto):
    with pytest.raises(FormatError, match="contagem"):
        parse_count(texto, {"<5"})


def test_r2_2_parse_code_traduz_e_recusa_codigo_desconhecido():
    sexo = {"1": "M", "2": "F"}
    assert parse_code(" 2 ", sexo, "sexo") == "F"
    with pytest.raises(FormatError, match=r"sexo 'M' desconhecido; esperado um de \['1', '2'\]"):
        parse_code("M", sexo, "sexo")


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

def test_r2_6_arquivo_fora_de_resources_lista_os_disponiveis():
    arquivos = SourceFiles({"a.csv": Path("a.csv")})
    with pytest.raises(AdapterError, match=r"parse pediu o arquivo 'b.csv', fora de RESOURCES; disponíveis: \['a.csv'\]"):
        arquivos["b.csv"]


def test_r2_6_ingest_com_chave_errada_nomeia_a_fonte(tmp_path, monkeypatch):
    import adaptadores.exemplo
    monkeypatch.setattr(adaptadores.exemplo, "parse", lambda arquivos: iter([arquivos["nomes.csv"]]))
    shutil.copytree(FIXTURES / "exemplo", tmp_path / "exemplo")
    fontes = load_sources(FIXTURES / "sources.yaml")
    with pytest.raises(PipelineError, match="fonte 'exemplo': parse pediu o arquivo 'nomes.csv'"):
        ingest_sources([fontes["exemplo"]], fontes, tmp_path, offline=True, adapters="adaptadores")


def test_r2_6_adaptador_ausente_mostra_o_caminho_esperado():
    with pytest.raises(AdapterError) as e:
        load_adapter("nao-existe", "adaptadores")
    mensagem = str(e.value)
    assert "adaptador adaptadores.nao_existe ausente" in mensagem
    assert str(Path(__file__).parent / "adaptadores" / "nao_existe.py") in mensagem


def test_r2_6_adaptador_quebrado_nao_se_passa_por_ausente(tmp_path, monkeypatch):
    pacote = tmp_path / "quebrados"
    pacote.mkdir()
    (pacote / "__init__.py").write_text("", encoding="utf-8")
    (pacote / "fonte_x.py").write_text("import modulo_que_nao_existe\n", encoding="utf-8")
    (pacote / "fonte_y.py").write_text("1/0\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(AdapterError, match="adaptador quebrados.fonte_x quebrado: ModuleNotFoundError: .*modulo_que_nao_existe"):
        load_adapter("fonte-x", "quebrados")
    with pytest.raises(AdapterError, match="adaptador quebrados.fonte_y quebrado: ZeroDivisionError"):
        load_adapter("fonte-y", "quebrados")
    for nome in ("quebrados", "quebrados.fonte_x", "quebrados.fonte_y"):
        sys.modules.pop(nome, None)


def test_r2_6_pacote_de_adaptadores_inexistente():
    with pytest.raises(AdapterError, match="pacote 'nao_ha_pacote' não encontrado"):
        load_adapter("x", "nao_ha_pacote")
