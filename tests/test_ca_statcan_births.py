"""Spec 003d: adaptador da Statistics Canada (tabela 17-10-0147-01) sobre a amostra real
em tests/fixtures/ca-statcan-births/."""

import zipfile
from pathlib import Path

import pytest

from namescommons.adapters import FormatError, RawRecord, load_adapter
from namescommons.pipeline import to_observations
from namescommons.sources import load_sources

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO = "17100147-eng.zip"
FIXTURE = RAIZ / "tests" / "fixtures" / "ca-statcan-births" / ARQUIVO
CABECALHO = (
    '﻿"REF_DATE","GEO","DGUID","Sex at birth","First name at birth","Indicator","UOM","UOM_ID",'
    '"SCALAR_FACTOR","SCALAR_ID","VECTOR","COORDINATE","VALUE","STATUS","SYMBOL","TERMINATED","DECIMALS"\n'
)


@pytest.fixture
def statcan():
    return load_adapter("ca-statcan-births")


def linha(nome="AVA", valor="10", status="", simbolo="", ano="2020", geo="Canada", sexo="Female",
          indicador="Frequency", escala="0") -> str:
    """Linha no formato do CSV real; os campos que o adaptador não lê copiam a linha de OLIVIA 2025."""
    campos = [ano, geo, "2021A000011124", sexo, nome, indicador, "Number", "223", "units", escala,
              "v1491674874", "1.2.1.1", valor, status, simbolo, "", "0"]
    return ",".join(f'"{c}"' for c in campos) + "\n"


def _zip(tmp_path, *linhas: str, membro: str = "17100147.csv", cabecalho: str = CABECALHO) -> dict[str, Path]:
    caminho = tmp_path / ARQUIVO
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr(membro, (cabecalho + "".join(linhas)).encode("utf-8"))
        z.writestr("17100147_MetaData.csv", b'"Cube Title"\n')
    return {ARQUIVO: caminho}


def test_parse_da_amostra_real(statcan):
    assert list(statcan.parse({ARQUIVO: FIXTURE})) == [
        RawRecord("D'ARCY", "given", "CA", "M", 1991, 13),
        RawRecord("JEAN-PHILIPPE", "given", "CA", "M", 1991, 447),
        RawRecord("NOAH", "given", "CA", "M", 1991, 75),
        RawRecord("RILEY", "given", "CA", "M", 1991, 270),
        RawRecord("MARIE-EVE", "given", "CA", "F", 1991, 664),
        RawRecord("OLIVIA", "given", "CA", "F", 1991, 574),
        RawRecord("RILEY", "given", "CA", "F", 1991, 35),
        RawRecord("NOAH", "given", "CA", "M", 2025, 2190),
        RawRecord("RILEY", "given", "CA", "M", 2025, 196),
        RawRecord("NOAH", "given", "CA", "F", 2025, 36),
        RawRecord("OLIVIA", "given", "CA", "F", 2025, 1445),
        RawRecord("RILEY", "given", "CA", "F", 2025, 261),
    ]


def test_caixa_uniforme_gera_nomes_capitalizados(statcan):
    fonte = load_sources(RAIZ / "sources.yaml")["ca-statcan-births"]
    nomes = sorted({o.name for o in to_observations(statcan.parse({ARQUIVO: FIXTURE}), fonte)})
    assert nomes == ["D'Arcy", "Jean-Philippe", "Marie-Eve", "Noah", "Olivia", "Riley"]


# R1.1: só a frequência -------------------------------------------------------------------------

def test_so_frequencia_gera_registro(statcan, tmp_path):
    files = _zip(tmp_path, linha(valor="10"), linha(indicador="Rank", valor="3"),
                 linha(indicador="Proportion (%)", valor="0.0123"))
    assert list(statcan.parse(files)) == [RawRecord("AVA", "given", "CA", "F", 2020, 10)]


def test_indicador_desconhecido_falha(statcan, tmp_path):
    files = _zip(tmp_path, linha(), linha(indicador="Number"))
    with pytest.raises(FormatError, match="17100147.csv, linha 3: Indicator 'Number' desconhecido"):
        list(statcan.parse(files))


# R1.2: só o nível nacional ---------------------------------------------------------------------

def test_geografia_nao_nacional_e_pulada(statcan, tmp_path):
    files = _zip(tmp_path, linha(geo="Ontario", valor="7"), linha(valor="10"))
    assert list(statcan.parse(files)) == [RawRecord("AVA", "given", "CA", "F", 2020, 10)]


@pytest.mark.parametrize("linhas", [
    (),
    (linha(geo="Ontario"),),
    (linha(indicador="Rank"),),
    (linha(nome="Grand Total", status="..", valor=""),),
])
def test_sem_linhas_nacionais_de_frequencia_falha(statcan, tmp_path, linhas):
    with pytest.raises(FormatError, match="nenhuma linha 'Frequency' de 'Canada'"):
        list(statcan.parse(_zip(tmp_path, *linhas)))


# R1.3: sexo ------------------------------------------------------------------------------------

def test_sexo_por_mapeamento(statcan, tmp_path):
    files = _zip(tmp_path, linha(sexo="Male"), linha(sexo="Female"))
    assert [r.gender for r in statcan.parse(files)] == ["M", "F"]


@pytest.mark.parametrize("sexo", ["Both sexes", "M", "F", "male"])
def test_sexo_desconhecido_falha(statcan, tmp_path, sexo):
    with pytest.raises(FormatError, match=f"17100147.csv, linha 2: Sex at birth '{sexo}' unknown"):
        list(statcan.parse(_zip(tmp_path, linha(sexo=sexo))))


# R1.4: agregado --------------------------------------------------------------------------------

def test_grand_total_e_pulado_mesmo_com_valor(statcan, tmp_path):
    files = _zip(tmp_path, linha(nome="Grand Total", valor="180000"), linha(nome="Grand Total", status=".."),
                 linha(nome="Grand Total", indicador="Rank", valor="1"), linha(valor="10"))
    assert [r.name for r in statcan.parse(files)] == ["AVA"]


# R1.5: valores suprimidos ----------------------------------------------------------------------

def test_celula_suprimida_e_omitida(statcan, tmp_path):
    files = _zip(tmp_path, linha(nome="ABA", valor="", status=".."), linha(valor="10"))
    assert list(statcan.parse(files)) == [RawRecord("AVA", "given", "CA", "F", 2020, 10)]


@pytest.mark.parametrize("campos, trecho", [
    ({"valor": "", "status": "x"}, "STATUS 'x'"),
    ({"valor": "", "status": "F"}, "STATUS 'F'"),
    ({"valor": "12", "status": "E"}, "STATUS 'E'"),
    ({"valor": "0", "status": "0s"}, "STATUS '0s'"),
    ({"valor": "", "status": "<LOD"}, "STATUS '<LOD'"),
    ({"valor": "12", "status": ".."}, "STATUS '..'"),
    ({"valor": "", "status": ""}, "VALUE vazio sem STATUS '..'"),
    ({"valor": "n/a"}, "VALUE 'n/a'"),
    ({"valor": "12.5"}, "VALUE '12.5'"),
    ({"simbolo": "t"}, "SYMBOL 't'"),
    ({"simbolo": "x"}, "SYMBOL 'x'"),
])
def test_status_ou_simbolo_desconhecido_falha(statcan, tmp_path, campos, trecho):
    with pytest.raises(FormatError, match=f"17100147.csv, linha 2: .*{trecho}"):
        list(statcan.parse(_zip(tmp_path, linha(**campos))))


# R1.6: símbolos de revisão ---------------------------------------------------------------------

@pytest.mark.parametrize("simbolo", ["p", "r"])
def test_simbolos_de_revisao_sao_aceitos(statcan, tmp_path, simbolo):
    assert [r.count for r in statcan.parse(_zip(tmp_path, linha(simbolo=simbolo)))] == [10]


# R1.7 e R1.8: escala e ano ---------------------------------------------------------------------

def test_escala_diferente_de_unidades_falha(statcan, tmp_path):
    with pytest.raises(FormatError, match="17100147.csv, linha 2: SCALAR_ID '3'"):
        list(statcan.parse(_zip(tmp_path, linha(escala="3"))))


@pytest.mark.parametrize("ano", ["2020-01", "", "20x0"])
def test_ano_invalido_falha(statcan, tmp_path, ano):
    with pytest.raises(FormatError, match="17100147.csv, linha 2: REF_DATE"):
        list(statcan.parse(_zip(tmp_path, linha(ano=ano))))


# R2: leitura em fluxo e formato do arquivo ------------------------------------------------------

def test_parse_e_preguicoso(statcan, tmp_path):
    registros = statcan.parse(_zip(tmp_path, linha(valor="10"), linha(sexo="Both sexes")))
    assert next(registros) == RawRecord("AVA", "given", "CA", "F", 2020, 10)
    with pytest.raises(FormatError, match="linha 3"):
        next(registros)


def test_membro_ausente_falha(statcan, tmp_path):
    with pytest.raises(FormatError, match="sem o membro '17100147.csv'.*'17100148.csv'"):
        list(statcan.parse(_zip(tmp_path, linha(), membro="17100148.csv")))


def test_coluna_ausente_falha(statcan, tmp_path):
    cabecalho = '"REF_DATE","GEO","Sex at birth","First name at birth","VALUE"\n'
    with pytest.raises(FormatError, match="colunas ausentes \\['Indicator', 'SCALAR_ID', 'STATUS', 'SYMBOL'\\]"):
        list(statcan.parse(_zip(tmp_path, cabecalho=cabecalho)))


def test_linha_com_numero_de_campos_errado_falha(statcan, tmp_path):
    with pytest.raises(FormatError, match="17100147.csv, linha 2: esperava 17 campos, veio 3"):
        list(statcan.parse(_zip(tmp_path, '"2020","Canada","x"\n')))
