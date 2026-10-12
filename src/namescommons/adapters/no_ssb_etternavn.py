"""SSB, pessoas por sobrenome usado por 200 ou mais, tabela 12891 (spec 003, R1.5).

Mesmo instituto de no-ssb-fornavn, mas outro count_type (population), por isso outra fonte (R2.4).
"""

from collections.abc import Iterator
from pathlib import Path

from namescommons.adapters import RawRecord, Resource
from namescommons.adapters._ssb import API, cells

SOURCE_ID = "no-ssb-etternavn"
RESOURCES = [Resource(API.format(tabela="12891", dimensao="Etternavn"), "12891.json")]


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    for _, nome, ano, contagem in cells(files["12891.json"], "Etternavn"):
        yield RawRecord(name=nome, kind="family", country="NO", year=ano, count=contagem)
