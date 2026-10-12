"""Adaptador de exemplo, escrito só para teste (spec 002, critério de aceite 1).

Lê dois CSV no formato de um instituto fictício de Portugal: nomes em maiúsculas,
sexo em branco nos sobrenomes e uma linha repetida que o pipeline soma.
"""

import csv
from collections.abc import Iterator
from pathlib import Path

from namescommons.adapters import RawRecord, Resource

SOURCE_ID = "exemplo"
RESOURCES = [
    Resource("https://example.org/exemplo/primeiros.csv", "primeiros.csv"),
    Resource("https://example.org/exemplo/sobrenomes.csv", "sobrenomes.csv"),
]


def _ler(path: Path, kind: str) -> Iterator[RawRecord]:
    with open(path, encoding="utf-8", newline="") as fh:
        for linha in csv.DictReader(fh):
            yield RawRecord(
                name=linha["nome"], kind=kind, country="PT", gender=linha["sexo"],
                year=int(linha["ano"]), count=int(linha["quantidade"]),
            )


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    yield from _ler(files["primeiros.csv"], "given")
    yield from _ler(files["sobrenomes.csv"], "family")
