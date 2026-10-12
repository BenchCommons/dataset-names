"""Contrato do adaptador de fonte (spec 002, R1).

Cada fonte com adaptador tem um módulo <pacote>.<id_com_underscore> que expõe
SOURCE_ID, RESOURCES (lista de Resource) e parse(files) -> Iterator[RawRecord].
"""

import importlib
from dataclasses import dataclass
from types import ModuleType
from urllib.parse import urlsplit

DEFAULT_PACKAGE = "namesio.adapters"


class AdapterError(Exception):
    """Adaptador ausente ou fora do contrato de R1."""


@dataclass(frozen=True)
class Resource:
    url: str
    filename: str


@dataclass(frozen=True)
class RawRecord:
    """Registro como a fonte publica; o pipeline o transforma em Observation."""

    name: str
    kind: str
    country: str | None = None
    gender: str | None = None
    year: int | None = None
    count: int | None = None


def module_name(source_id: str) -> str:
    return source_id.replace("-", "_")


def _filename_seguro(nome: object) -> bool:
    return (
        isinstance(nome, str) and nome not in ("", ".", "..") and not nome.startswith(".")
        and "/" not in nome and "\\" not in nome
        and not nome.endswith((".meta.json", ".part"))
    )


def check_adapter(mod: object, source_id: str) -> None:
    """Levanta AdapterError se o módulo não cumpre o contrato de R1."""
    for atributo in ("SOURCE_ID", "RESOURCES", "parse"):
        if not hasattr(mod, atributo):
            raise AdapterError(f"adaptador de '{source_id}' sem {atributo}")
    if mod.SOURCE_ID != source_id:
        raise AdapterError(f"SOURCE_ID '{mod.SOURCE_ID}' diverge do id '{source_id}' em sources.yaml")
    recursos = mod.RESOURCES
    if not isinstance(recursos, (list, tuple)) or not recursos or not all(
        isinstance(r, Resource) for r in recursos
    ):
        raise AdapterError(f"'{source_id}': RESOURCES deve ser uma lista não vazia de Resource")
    vistos: set[str] = set()
    for r in recursos:
        partes = urlsplit(r.url)
        if partes.scheme.lower() not in ("http", "https") or not partes.netloc:
            raise AdapterError(f"'{source_id}': url {r.url!r} deve usar http ou https")
        if not _filename_seguro(r.filename):
            raise AdapterError(f"'{source_id}': filename {r.filename!r} inválido")
        if r.filename in vistos:
            raise AdapterError(f"'{source_id}': filename {r.filename!r} repetido")
        vistos.add(r.filename)
    if not callable(mod.parse):
        raise AdapterError(f"'{source_id}': parse deve ser uma função")


def load_adapter(source_id: str, package: str = DEFAULT_PACKAGE) -> ModuleType:
    nome = f"{package}.{module_name(source_id)}"
    try:
        mod = importlib.import_module(nome)
    except ImportError as e:
        raise AdapterError(f"não foi possível importar o adaptador {nome}: {e}") from e
    check_adapter(mod, source_id)
    return mod
