"""Spec 003, R1.3: adaptador do CSO (Irlanda) sobre a amostra real em tests/fixtures/ie-cso-births/."""

from pathlib import Path

import pytest

from namescommons.adapters import FormatError, RawRecord, load_adapter

FIXTURES = Path(__file__).parent / "fixtures" / "ie-cso-births"
CABECALHO = '﻿"STATISTIC","Statistic Label","TLIST(A1)","Year","C02512V04117","Boys Names","UNIT","VALUE"\r\n'


@pytest.fixture
def cso():
    return load_adapter("ie-cso-births")


def _arquivos(tmp_path, meninos: str) -> dict[str, Path]:
    (tmp_path / "VSA50.csv").write_text(meninos, encoding="utf-8", newline="")
    return {"VSA50.csv": tmp_path / "VSA50.csv", "VSA60.csv": FIXTURES / "VSA60.csv"}


def test_parse_da_amostra_real(cso):
    arquivos = {nome: FIXTURES / nome for nome in ("VSA50.csv", "VSA60.csv")}
    assert list(cso.parse(arquivos)) == [
        RawRecord("Jack", "given", "IE", "M", 2025, 475),
        RawRecord("Seán", "given", "IE", "M", 2025, 185),
        RawRecord("Seán Óg", "given", "IE", "M", 2025, 17),
        RawRecord("Mary", "given", "IE", "F", 1964, 3471),
        RawRecord("Emily", "given", "IE", "F", 2025, 246),
        RawRecord("Mary", "given", "IE", "F", 2025, 41),
        RawRecord("Saoirse", "given", "IE", "F", 2025, 176),
    ]


def test_valor_vazio_e_rank_sao_ignorados(cso, tmp_path):
    texto = CABECALHO + '"VSA50C01","x","2020","2020","1","Ola","Number",""\r\n' \
        '"VSA50C02","x","2020","2020","1","Ola","Number","7"\r\n'
    assert [r for r in cso.parse(_arquivos(tmp_path, texto)) if r.gender == "M"] == []


@pytest.mark.parametrize("texto, trecho", [
    ('"STATISTIC","TLIST(A1)","Nomes","VALUE"\r\n', "colunas ausentes \\['Boys Names'\\]"),
    (CABECALHO + '"VSA50C01","x","2020","2020","1","Ola","Number","<3"\r\n', "contagem '<3'"),
])
def test_formato_inesperado_falha(cso, tmp_path, texto, trecho):
    with pytest.raises(FormatError, match=trecho):
        list(cso.parse(_arquivos(tmp_path, texto)))


@pytest.mark.parametrize("tabela, codigo, coluna", [
    ("VSA50.csv", "VSA50C01", "Boys Names"),
    ("VSA60.csv", "VSA60C01", "Girls Names"),
])
def test_estatistica_de_contagem_renomeada_falha(cso, tmp_path, tabela, codigo, coluna):
    cab = CABECALHO.replace("Boys Names", coluna)
    novo = codigo.replace("C01", "C09")
    (tmp_path / tabela).write_text(cab + f'"{novo}","x","2020","2020","1","Ola","Number","5"\r\n',
                                   encoding="utf-8", newline="")
    arquivos = {n: FIXTURES / n for n in ("VSA50.csv", "VSA60.csv")}
    arquivos[tabela] = tmp_path / tabela
    with pytest.raises(FormatError, match=f"{tabela}: nenhuma linha com a estatística '{codigo}'; vistas \\['{novo}'\\]"):
        list(cso.parse(arquivos))


def test_linha_curta_vira_format_error_com_arquivo_e_linha(cso, tmp_path):
    texto = CABECALHO + '"VSA50C01","x","2020","2020","1","Ola","Number","5"\r\n"VSA50C01","x","2020"\r\n'
    with pytest.raises(FormatError, match="VSA50.csv, linha 3: 3 campos, o cabeçalho tem 8"):
        list(cso.parse(_arquivos(tmp_path, texto)))
