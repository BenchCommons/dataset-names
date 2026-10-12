"""Adaptadores de fonte do dataset de nomes (spec 002, R1; spec 003, R2; spec 007, R3.1).

Cada fonte com adaptador tem um módulo <pacote>.<id_com_underscore> que expõe
SOURCE_ID, RESOURCES (lista de Resource) e parse(files) -> Iterator[RawRecord],
e opcionalmente links(files) -> Iterator[RawLink] (spec 004, R4.1).
O adaptador converte os valores da fonte: year e count como int, gender como F ou M,
country em ISO 3166-1 alfa-2, kind como given ou family. Valores suprimidos são omitidos.

O contrato genérico (Resource, SourceFiles, erros, parse_count, parse_code, check_adapter,
load_adapter) é o do kit de fontes do tools-dataset (spec 004 de lá, R4), reexportado aqui
como os mesmos objetos. Daqui são só os tipos de registro, o pacote padrão e a função
opcional links.
"""

from dataclasses import dataclass
from types import ModuleType

from datasettool.sources import adapters as _kit
from datasettool.sources.adapters import (
    AdapterError, FormatError, Resource, SourceFiles, module_name, parse_code, parse_count,
)

__all__ = [
    "DEFAULT_PACKAGE", "OPTIONAL", "AdapterError", "FormatError", "RawLink", "RawRecord", "Resource",
    "SourceFiles", "check_adapter", "load_adapter", "module_name", "parse_code", "parse_count",
]

DEFAULT_PACKAGE = "namescommons.adapters"
OPTIONAL = ("links",)  # funções opcionais do protocolo de nomes (spec 004, R4.1)


@dataclass(frozen=True)
class RawRecord:
    """Registro como a fonte publica; o pipeline o transforma em Observation."""

    name: str
    kind: str
    country: str | None = None
    gender: str | None = None
    year: int | None = None
    count: int | None = None


@dataclass(frozen=True)
class RawLink:
    """Ligação entre dois nomes como a fonte publica (spec 004, R4.1); o pipeline a transforma em VariantLink."""

    relation: str
    qid: str
    name: str
    kind: str
    target_qid: str
    target_name: str
    target_kind: str


def check_adapter(mod: object, source_id: str) -> None:
    """Levanta AdapterError se o módulo não cumpre o contrato do kit ou tem links que não é função."""
    _kit.check_adapter(mod, source_id, OPTIONAL)


def load_adapter(source_id: str, package: str = DEFAULT_PACKAGE) -> ModuleType:
    """Importa e confere o adaptador; ausente e quebrado são distinguidos pelo kit."""
    return _kit.load_adapter(source_id, package, OPTIONAL)
