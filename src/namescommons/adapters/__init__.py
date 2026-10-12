"""Contrato do adaptador de fonte (spec 002, R1, com as regras da spec 003, R2).

Cada fonte com adaptador tem um módulo <pacote>.<id_com_underscore> que expõe
SOURCE_ID, RESOURCES (lista de Resource) e parse(files) -> Iterator[RawRecord],
e opcionalmente links(files) -> Iterator[RawLink] (spec 004, R4.1).
O adaptador converte os valores da fonte: year e count como int, gender como F ou M,
country em ISO 3166-1 alfa-2, kind como given ou family. Valores suprimidos são omitidos.
"""

import importlib
import importlib.util
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from urllib.parse import urlsplit

DEFAULT_PACKAGE = "namescommons.adapters"


class AdapterError(Exception):
    """Adaptador ausente ou fora do contrato de R1."""


class FormatError(ValueError):
    """Arquivo da fonte fora do formato que o adaptador espera (spec 003, R2.2)."""


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


def module_name(source_id: str) -> str:
    return source_id.replace("-", "_")


def url_http(url: object) -> bool:
    """URL http ou https com host, sem espaços nem caracteres de controle; nunca levanta exceção."""
    if not isinstance(url, str) or any(c.isspace() or not c.isprintable() for c in url):
        return False
    try:
        partes = urlsplit(url)
        return partes.scheme.lower() in ("http", "https") and bool(partes.netloc)
    except ValueError:
        return False


def _filename_seguro(nome: object) -> bool:
    return (
        isinstance(nome, str) and nome.isprintable() and nome not in ("", ".", "..") and not nome.startswith(".")
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
        if not url_http(r.url):
            raise AdapterError(f"'{source_id}': url {r.url!r} deve usar http ou https")
        if not _filename_seguro(r.filename):
            raise AdapterError(f"'{source_id}': filename {r.filename!r} inválido")
        if r.filename in vistos:
            raise AdapterError(f"'{source_id}': filename {r.filename!r} repetido")
        vistos.add(r.filename)
    if not callable(mod.parse):
        raise AdapterError(f"'{source_id}': parse deve ser uma função")
    if hasattr(mod, "links") and not callable(mod.links):
        raise AdapterError(f"'{source_id}': links deve ser uma função")


def _caminho_esperado(package: str, modulo: str) -> str:
    try:
        spec = importlib.util.find_spec(package)
    except ImportError:
        spec = None
    if spec is None or not spec.submodule_search_locations:
        return f"pacote {package!r} não encontrado"
    return str(Path(list(spec.submodule_search_locations)[0]) / f"{modulo}.py")


def load_adapter(source_id: str, package: str = DEFAULT_PACKAGE) -> ModuleType:
    nome = f"{package}.{module_name(source_id)}"
    try:
        mod = importlib.import_module(nome)
    except ModuleNotFoundError as e:
        if e.name is not None and (nome == e.name or nome.startswith(e.name + ".")):
            esperado = _caminho_esperado(package, module_name(source_id))
            raise AdapterError(f"adaptador {nome} ausente (esperado em {esperado})") from e
        raise AdapterError(f"adaptador {nome} quebrado: {type(e).__name__}: {e}") from e
    except Exception as e:
        raise AdapterError(f"adaptador {nome} quebrado: {type(e).__name__}: {e}") from e
    check_adapter(mod, source_id)
    return mod


class SourceFiles(dict):
    """Arquivos baixados de uma fonte (chave = filename); chave fora de RESOURCES gera AdapterError."""

    def __missing__(self, chave):
        raise AdapterError(f"parse pediu o arquivo {chave!r}, fora de RESOURCES; disponíveis: {sorted(self)}")


_INTEIRO = re.compile(r"[0-9]+")


def parse_count(value: str, missing: Collection[str] = (), field: str = "contagem") -> int | None:
    """Inteiro publicado (contagem ou ano); um marcador de `missing` (valor suprimido ou ausente) vira None.

    Qualquer outro texto levanta FormatError, para que um marcador novo da fonte não passe calado.
    """
    texto = value.strip()
    if texto in missing:
        return None
    if _INTEIRO.fullmatch(texto):
        return int(texto)
    raise FormatError(f"{field} {value!r} não é inteiro nem marcador conhecido {sorted(missing)}")


def parse_code(value: str, mapping: Mapping[str, str], field: str) -> str:
    """Traduz um código da fonte (ex.: sexo '1' e '2') pelo mapeamento; código desconhecido é FormatError."""
    try:
        return mapping[value.strip()]
    except KeyError:
        raise FormatError(f"{field} {value!r} desconhecido; esperado um de {sorted(mapping)}") from None
