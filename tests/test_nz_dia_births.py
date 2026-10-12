"""Spec 003e: adaptador do DIA (Nova Zelândia) sobre a amostra real em tests/fixtures/nz-dia-births/."""

from pathlib import Path

import pytest

from namescommons.adapters import FormatError, RawDrop, RawRecord, load_adapter

ARQUIVO = "baby-names-1900-to-2025.csv"
AMOSTRA = Path(__file__).parent / "fixtures" / "nz-dia-births" / ARQUIVO
CABECALHO = b"Year,Sex,Name,Count\r\n"


@pytest.fixture
def dia():
    return load_adapter("nz-dia-births")


def _arquivos(tmp_path, conteudo: bytes) -> dict[str, Path]:
    (tmp_path / ARQUIVO).write_bytes(conteudo)
    return {ARQUIVO: tmp_path / ARQUIVO}


def _r(nome, sexo, ano, contagem):
    return RawRecord(nome, "given", "NZ", sexo, ano, contagem)


def _registros(dia, arquivos):
    return [r for r in dia.parse(arquivos) if isinstance(r, RawRecord)]


def test_parse_da_amostra_real(dia):
    assert _registros(dia, {ARQUIVO: AMOSTRA}) == [
        _r("Aadhya", "F", 2022, 13),
        _r("André", "M", 2003, 20),       # 0x82, CP437
        _r("Anne-Marie", "F", 1967, 24),
        _r("Aroha", "F", 2025, 22),
        _r("Björn", "M", 2025, 10),       # 0xF6, Latin-1
        _r("Esmé", "F", 2022, 25),        # 0x82
        _r("Esmé", "F", 2025, 20),        # 0xE9, mesmo nome noutra codificação
        _r("John", "M", 1900, 636),
        _r("Mary", "F", 1900, 410),
        _r("Nikau", "M", 2025, 36),
        _r("Te Ao", "F", 2024, 15),
        _r("Te Ao", "M", 2024, 12),
        _r("Te Ariki", "M", 2025, 34),
        _r("Zoé", "F", 2007, 26),         # 0xE9
        _r("Zoya", "F", 2015, 11),
    ]


def test_nz_emite_raw_drop_para_nomes_corrompidos(dia):
    """Spec 006, R1: os descartes do ADR 0007 saem como RawDrop, com a contagem publicada."""
    itens = list(dia.parse({ARQUIVO: AMOSTRA}))
    descartes = [i for i in itens if isinstance(i, RawDrop)]
    assert sorted(descartes, key=lambda d: d.name) == [
        RawDrop("K\ufffdwhai", 11), RawDrop("M?ia", 25), RawDrop("N\ufffdkau", 13),
    ]
    assert sum(d.count for d in descartes) == 49
    assert not any("?" in r.name or "\ufffd" in r.name for r in itens if isinstance(r, RawRecord))


def test_nz_nao_usa_logging():
    fonte = Path(__file__).resolve().parent.parent / "src" / "namescommons" / "adapters" / "nz_dia_births.py"
    assert "logging" not in fonte.read_text(encoding="utf-8")


def test_sem_descarte_nao_emite_raw_drop(dia, tmp_path):
    assert list(dia.parse(_arquivos(tmp_path, CABECALHO + b"2025,F,Zo\xe9,10\r\n"))) == [_r("Zoé", "F", 2025, 10)]


def test_arquivo_utf8_valido_e_lido_como_utf8(dia, tmp_path):
    conteudo = CABECALHO + "2025,F,Māia,25\r\n2025,F,Zoé,10\r\n".encode("utf-8")
    assert [r.name for r in _registros(dia, _arquivos(tmp_path, conteudo))] == ["Māia", "Zoé"]


def test_utf8_com_caractere_de_substituicao_tambem_e_descartado(dia, tmp_path):
    conteudo = CABECALHO + "2025,F,Am\ufffdlie,10\r\n2025,F,Ana,10\r\n".encode("utf-8")
    assert [r.name for r in _registros(dia, _arquivos(tmp_path, conteudo))] == ["Ana"]


@pytest.mark.parametrize("byte", [b"\xe1", b"\x8d", b"\xff"])
def test_byte_fora_da_tabela_descarta_o_nome(dia, tmp_path, byte):
    conteudo = CABECALHO + b"2025,F,M" + byte + b"ia,25\r\n2025,F,Mia,125\r\n"
    assert [r.name for r in _registros(dia, _arquivos(tmp_path, conteudo))] == ["Mia"]


@pytest.mark.parametrize("conteudo, trecho", [
    (b"Ano,Sexo,Nome,Total\r\n2025,F,Mia,1\r\n", r"cabeçalho \['Ano', 'Sexo', 'Nome', 'Total'\]"),
    (b"", "arquivo vazio"),
    (CABECALHO + b"2025,U,Mia,12\r\n", "linha 2: sexo 'U' unknown"),
    (CABECALHO + b"2025,F,Mia,<10\r\n", "linha 2: count '<10'"),
    (CABECALHO + b"2025,F,Mia,12\r\n20x5,F,Mia,12\r\n", "linha 3: ano '20x5'"),
    (CABECALHO + b"2025,F,Mia\r\n", "linha 2: esperava 4 campos, veio 3"),
    (CABECALHO + b"2025,F,Mia,Rose,12\r\n", "linha 2: esperava 4 campos, veio 5"),
])
def test_formato_inesperado_falha(dia, tmp_path, conteudo, trecho):
    with pytest.raises(FormatError, match=trecho):
        list(dia.parse(_arquivos(tmp_path, conteudo)))


def test_pagina_html_no_cache_explica_o_que_fazer(dia, tmp_path):
    arquivos = _arquivos(tmp_path, b"<!DOCTYPE html>\n<html><head><title>Pardon Our Interruption</title>")
    with pytest.raises(FormatError) as e:
        list(dia.parse(arquivos))
    assert "página HTML" in str(e.value)
    assert str(tmp_path / ARQUIVO) in str(e.value)
