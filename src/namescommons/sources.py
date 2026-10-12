"""Registro de fontes (sources.yaml) do dataset de nomes (spec 001, R2; spec 002, R2; spec 007, R3.2).

A leitura do YAML, os campos genéricos (id, name, url, license, attribution, retrieved, adapter)
e a coleta de todos os erros são do registro do kit de fontes do tools-dataset (spec 004 de lá, R5).
Daqui são os campos de nomes, a lista de licenças aceitas pelo ADR 0001 (ampliado pelo 0004),
a regra de uma primary por país e tipo de contagem e o tipo Source.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pycountry
from datasettool.sources.registry import (
    ATTRIBUTION_ONLY_LICENSES, Field, RegistryError, RegistrySchema, load_registry, parse_registry,
)

LICENCAS_COMPATIVEIS = ATTRIBUTION_ONLY_LICENSES | {
    "statcan-open-licence",  # ADR 0004 (docs/adr/0004-licenca-statistics-canada.md)
}
COUNT_TYPES = ("births", "population", "attested")

SourceError = RegistryError  # sources.yaml inválido; a mensagem lista todos os problemas encontrados


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str
    license: str
    attribution: str
    country: str | None
    count_type: str
    primary: bool
    suppression: int | None
    retrieved: date
    uniform_case: bool = False
    adapter: bool = True
    strips_accents: bool = False


def is_country(code: object) -> bool:
    """Código ISO 3166-1 alfa-2 em maiúsculas."""
    if not isinstance(code, str) or len(code) != 2 or code != code.upper():
        return False
    try:
        return pycountry.countries.get(alpha_2=code) is not None
    except (KeyError, LookupError):
        return False


def _country(valor: object) -> str | None:
    if isinstance(valor, bool):
        return f"país lido como booleano {valor}; escreva o código entre aspas, ex.: \"NO\""
    if valor is not None and not is_country(valor):
        return f"país '{valor}' fora da ISO 3166-1 alfa-2"
    return None


def _count_type(valor: object) -> str | None:
    return None if valor in COUNT_TYPES else f"count_type '{valor}' inválido"


def _booleano(campo: str):
    def conferir(valor: object) -> str | None:
        return None if isinstance(valor, bool) else f"'{campo}' deve ser true ou false"
    return conferir


def _suppression(valor: object) -> str | None:
    if valor is not None and (isinstance(valor, bool) or not isinstance(valor, int) or valor < 1):
        return "'suppression' deve ser inteiro positivo ou vazio"
    return None


def _uma_primary(fontes: Mapping[str, Source]) -> list[str]:
    """Exatamente uma primary por (country, count_type) com contagem; em attested, primary não
    tem efeito e não é conferido (spec 004, R5; issue #3)."""
    grupos: dict[tuple, list[Source]] = {}
    for f in fontes.values():
        if f.count_type == "attested":
            continue
        grupos.setdefault((f.country, f.count_type), []).append(f)
    erros = []
    for (pais, tipo), fs in sorted(grupos.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        if len(fs) > 1 and sum(f.primary is True for f in fs) != 1:
            erros.append(f"{pais}/{tipo}: fontes {sorted(f.id for f in fs)}; exatamente uma deve ter primary: true")
    return erros


SCHEMA: RegistrySchema[Source] = RegistrySchema(
    accepted_licenses=LICENCAS_COMPATIVEIS,
    license_policy="ADR 0001",
    fields=(
        Field("country", _country),
        Field("count_type", _count_type),
        Field("primary", _booleano("primary")),
        Field("suppression", _suppression),
        Field("uniform_case", _booleano("uniform_case"), required=False, default=False),  # spec 002, R2
        Field("strips_accents", _booleano("strips_accents"), required=False, default=False),  # spec 005, R6
    ),
    checks=(_uma_primary,),
    factory=lambda campos: Source(**campos),
)


def load_sources(path: Path) -> dict[str, Source]:
    return load_registry(Path(path), SCHEMA)


def parse_sources(entradas: list[dict]) -> dict[str, Source]:
    return parse_registry(entradas, SCHEMA)
