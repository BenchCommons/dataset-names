"""Statistics Canada, tabela 17-10-0147-01, primeiros nomes no nascimento por sexo (spec 003d).

O ZIP traz 17100147.csv (dados) e 17100147_MetaData.csv (ignorado). O CSV tem uma linha por
ano, geografia, sexo, nome e indicador (Frequency, Rank, Proportion (%)); só a frequência
nacional vira registro. VALUE vazio com STATUS '..' é nome ausente ou suprimido (menos de 5)
e é omitido (ADR 0002). Os nomes vêm em maiúsculas e sem acento.

STATUS, SYMBOL, sexo, escala e ano são conferidos só nas linhas nacionais de frequência que não são
o agregado Grand Total; marcadores em linhas descartadas (Rank, Proportion (%), outra geografia)
não são conferidos de propósito, porque nada delas entra no dataset. O indicador é conferido em todas.

O CSV real tem 582 MB: a leitura é em fluxo, linha a linha, sem guardar o arquivo.
"""

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

from namescommons.adapters import FormatError, RawRecord, Resource, parse_code, parse_count

SOURCE_ID = "ca-statcan-births"
RESOURCES = [Resource("https://www150.statcan.gc.ca/n1/tbl/csv/17100147-eng.zip", "17100147-eng.zip")]

MEMBRO = "17100147.csv"
_COLUNAS = ("REF_DATE", "GEO", "Sex at birth", "First name at birth", "Indicator",
            "SCALAR_ID", "VALUE", "STATUS", "SYMBOL")
_INDICADORES = frozenset({"Frequency", "Rank", "Proportion (%)"})
_SEXO = {"Male": "M", "Female": "F"}
_NACIONAL = "Canada"
_AGREGADO = "Grand Total"
_UNIDADES = "0"
# Legenda de símbolos da tabela: p (preliminar) e r (revisado) não mudam o valor.
_SIMBOLOS = frozenset({"", "p", "r"})
_SUPRIMIDO = ".."


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    with zipfile.ZipFile(files["17100147-eng.zip"]) as z:
        if MEMBRO not in z.namelist():
            raise FormatError(f"17100147-eng.zip sem o membro {MEMBRO!r}; membros: {z.namelist()}")
        with z.open(MEMBRO) as bruto:
            yield from _ler(csv.reader(io.TextIOWrapper(bruto, encoding="utf-8-sig", newline="")))


def _ler(leitor) -> Iterator[RawRecord]:
    cabecalho = next(leitor, None)
    if cabecalho is None:
        raise FormatError(f"{MEMBRO} vazio")
    faltando = sorted(set(_COLUNAS) - set(cabecalho))
    if faltando:
        raise FormatError(f"{MEMBRO}: colunas ausentes {faltando}; cabeçalho {cabecalho}")
    ano, geo, sexo, nome, indicador, escala, valor, status, simbolo = (cabecalho.index(c) for c in _COLUNAS)
    largura = len(cabecalho)
    nacionais = 0
    for campos in leitor:
        try:
            if len(campos) != largura:
                raise FormatError(f"esperava {largura} campos, veio {len(campos)}")
            if campos[indicador] not in _INDICADORES:
                raise FormatError(f"Indicator {campos[indicador]!r} desconhecido; esperado um de {sorted(_INDICADORES)}")
            if campos[indicador] != "Frequency" or campos[geo] != _NACIONAL:
                continue
            if campos[nome] == _AGREGADO:
                continue
            nacionais += 1
            genero = parse_code(campos[sexo], _SEXO, "Sex at birth")
            if campos[escala] != _UNIDADES:
                raise FormatError(f"SCALAR_ID {campos[escala]!r}; esperado {_UNIDADES!r} (unidades)")
            if campos[simbolo] not in _SIMBOLOS:
                raise FormatError(f"SYMBOL {campos[simbolo]!r} desconhecido; esperado um de {sorted(_SIMBOLOS)}")
            contagem = _contagem(campos[valor], campos[status])
            if contagem is None:
                continue
            yield RawRecord(name=campos[nome], kind="given", country="CA", gender=genero,
                            year=parse_count(campos[ano], field="REF_DATE"), count=contagem)
        except FormatError as e:
            raise FormatError(f"{MEMBRO}, linha {leitor.line_num}: {e}") from None
    if not nacionais:
        raise FormatError(f"{MEMBRO}: nenhuma linha 'Frequency' de {_NACIONAL!r}")


def _contagem(valor: str, status: str) -> int | None:
    """Inteiro publicado, ou None para a célula suprimida (VALUE vazio com STATUS '..')."""
    if status == _SUPRIMIDO:
        if valor.strip():
            raise FormatError(f"STATUS {status!r} com VALUE {valor!r}; esperado VALUE vazio")
        return None
    if status:
        raise FormatError(f"STATUS {status!r} desconhecido; esperado vazio ou {_SUPRIMIDO!r}")
    if not valor.strip():
        raise FormatError(f"VALUE vazio sem STATUS {_SUPRIMIDO!r}")
    return parse_count(valor, field="VALUE")
