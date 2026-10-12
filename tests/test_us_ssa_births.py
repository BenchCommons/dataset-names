"""Spec 003, R1.1 e R4: adaptador da SSA (EUA) sobre a amostra real em tests/fixtures/us-ssa-births/."""

import zipfile
from pathlib import Path

import pytest

from namescommons.adapters import FormatError, RawRecord, Resource, load_adapter
from namescommons.cache import FetchError, fetch_resource

FIXTURES = Path(__file__).parent / "fixtures" / "us-ssa-births"


@pytest.fixture
def ssa():
    return load_adapter("us-ssa-births")


def _zip(tmp_path, arquivos: dict[str, bytes]) -> dict[str, Path]:
    caminho = tmp_path / "names.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)
    return {"names.zip": caminho}


def test_parse_da_amostra_real(ssa):
    registros = list(ssa.parse({"names.zip": FIXTURES / "names.zip"}))
    assert registros == [
        RawRecord("Mary", "given", "US", "F", 1880, 7065),
        RawRecord("Anna", "given", "US", "F", 1880, 2604),
        RawRecord("John", "given", "US", "M", 1880, 9655),
        RawRecord("William", "given", "US", "M", 1880, 9532),
        RawRecord("Olivia", "given", "US", "F", 2024, 14718),
        RawRecord("Avery", "given", "US", "F", 2024, 5632),
        RawRecord("Liam", "given", "US", "F", 2024, 34),
        RawRecord("Liam", "given", "US", "M", 2024, 22164),
        RawRecord("Avery", "given", "US", "M", 2024, 1348),
        RawRecord("Zyre", "given", "US", "M", 2024, 5),
    ]


def test_ignora_outros_membros_e_aceita_fim_de_linha_lf(ssa, tmp_path):
    arquivos = _zip(tmp_path, {"NationalReadMe.pdf": b"%PDF", "yob2000.txt": b"Ana,F,9\n"})
    assert list(ssa.parse(arquivos)) == [RawRecord("Ana", "given", "US", "F", 2000, 9)]


def test_anos_em_ordem_numerica(ssa, tmp_path):
    arquivos = _zip(tmp_path, {"yob2001.txt": b"B,M,5\r\n", "yob1999.txt": b"A,F,5\r\n"})
    assert [r.year for r in ssa.parse(arquivos)] == [1999, 2001]


@pytest.mark.parametrize("linha, trecho", [
    (b"Ana,X,9\r\n", "sexo 'X' desconhecido"),
    (b"Ana,F,<5\r\n", "contagem '<5'"),
    (b"Ana,F\r\n", "yob2000.txt, linha 1: esperava nome,sexo,contagem"),
])
def test_formato_inesperado_falha(ssa, tmp_path, linha, trecho):
    with pytest.raises(FormatError, match=trecho):
        list(ssa.parse(_zip(tmp_path, {"yob2000.txt": linha})))


def test_zip_sem_arquivos_anuais_falha(ssa, tmp_path):
    with pytest.raises(FormatError, match="sem arquivos yobAAAA.txt"):
        list(ssa.parse(_zip(tmp_path, {"leia.txt": b"x"})))


def test_403_explica_como_colocar_o_arquivo_no_cache(servidor, tmp_path):
    servidor.recusados.add("/oact/babynames/names.zip")
    recurso = Resource(servidor.url("/oact/babynames/names.zip"), "names.zip")
    with pytest.raises(FetchError) as e:
        fetch_resource(tmp_path, "us-ssa-births", recurso, espera=0)
    mensagem = str(e.value)
    assert "HTTP Error 403" in mensagem
    assert f"grave-o em {tmp_path / 'us-ssa-births' / 'names.zip'} e rode com --offline" in mensagem
    assert len(servidor.requisicoes) == 1  # 4xx não se resolve tentando de novo


def test_byte_nao_ascii_vira_format_error_com_membro_e_linha(ssa, tmp_path):
    arquivos = _zip(tmp_path, {"yob2000.txt": b"Mary,F,10\nJos\xc3\xa9,M,5\n"})
    with pytest.raises(FormatError, match="yob2000.txt, linha 2: byte fora de ASCII"):
        list(ssa.parse(arquivos))


@pytest.mark.parametrize("fim", [b"\r", b"\n", b"\r\n"])
def test_aceita_qualquer_fim_de_linha_inclusive_so_cr(ssa, tmp_path, fim):
    conteudo = fim.join([b"Ana,F,9", b"Bia,F,7", b"Rui,M,5"]) + fim
    arquivos = _zip(tmp_path, {"yob2000.txt": conteudo})
    assert [(r.name, r.count) for r in ssa.parse(arquivos)] == [("Ana", 9), ("Bia", 7), ("Rui", 5)]


def test_linha_em_branco_no_meio_continua_sendo_erro_com_a_linha_certa(ssa, tmp_path):
    arquivos = _zip(tmp_path, {"yob2000.txt": b"Ana,F,9\r\n\r\nBia,F,7\r\n"})
    with pytest.raises(FormatError, match="yob2000.txt, linha 2: esperava nome,sexo,contagem"):
        list(ssa.parse(arquivos))


def test_byte_nao_ascii_com_cr_so_aponta_a_linha(ssa, tmp_path):
    arquivos = _zip(tmp_path, {"yob2000.txt": b"Mary,F,10\rJos\xc3\xa9,M,5\r"})
    with pytest.raises(FormatError, match="yob2000.txt, linha 2: byte fora de ASCII"):
        list(ssa.parse(arquivos))
