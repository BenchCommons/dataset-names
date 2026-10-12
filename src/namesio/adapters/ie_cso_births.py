"""CSO, nomes de bebês da Irlanda, tabelas VSA50 (meninos) e VSA60 (meninas) do PxStat (spec 003, R1.3).

Cada CSV traz o cubo inteiro: todos os nomes em todos os anos, com a contagem (estatística C01)
e o rank (C02). Contagem vazia é nome com menos de 3 ocorrências naquele ano, ou ausente.
"""

import csv
from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import FormatError, RawRecord, Resource, parse_count

SOURCE_ID = "ie-cso-births"
_API = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/{}/CSV/1.0/en"
RESOURCES = [Resource(_API.format("VSA50"), "VSA50.csv"), Resource(_API.format("VSA60"), "VSA60.csv")]

# arquivo -> (código da estatística de contagem, coluna do nome, gender)
_TABELAS = {
    "VSA50.csv": ("VSA50C01", "Boys Names", "M"),
    "VSA60.csv": ("VSA60C01", "Girls Names", "F"),
}


def _ler(caminho: Path, estatistica: str, coluna: str, genero: str) -> Iterator[RawRecord]:
    with open(caminho, encoding="utf-8-sig", newline="") as fh:
        leitor = csv.DictReader(fh)
        faltando = {"STATISTIC", "TLIST(A1)", coluna, "VALUE"} - set(leitor.fieldnames or ())
        if faltando:
            raise FormatError(f"{caminho.name}: colunas ausentes {sorted(faltando)}; cabeçalho {leitor.fieldnames}")
        for linha in leitor:
            if linha["STATISTIC"] != estatistica:
                continue
            contagem = parse_count(linha["VALUE"], missing={""})
            if contagem is None:
                continue
            yield RawRecord(
                name=linha[coluna], kind="given", country="IE", gender=genero,
                year=parse_count(linha["TLIST(A1)"], field="TLIST(A1)"), count=contagem,
            )


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    for arquivo, (estatistica, coluna, genero) in _TABELAS.items():
        yield from _ler(files[arquivo], estatistica, coluna, genero)
