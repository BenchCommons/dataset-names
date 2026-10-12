"""SSB, nascidos por primeiro nome, tabela 10467 (spec 003, R1.4).

O código de cada nome começa com 1 (meninas) ou 2 (meninos); o rótulo é o nome publicado.
Até 2020 o ano é o de nascimento; desde 2021, o de registro do nome.
"""

from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import RawRecord, Resource, parse_code
from namesio.adapters._ssb import API, cells

SOURCE_ID = "no-ssb-fornavn"
RESOURCES = [Resource(API.format(tabela="10467", dimensao="Fornavn"), "10467.json")]

_SEXO = {"1": "F", "2": "M"}


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    for codigo, nome, ano, contagem in cells(files["10467.json"], "Fornavn"):
        yield RawRecord(
            name=nome, kind="given", country="NO",
            gender=parse_code(codigo[:1], _SEXO, "prefixo de sexo"), year=ano, count=contagem,
        )
