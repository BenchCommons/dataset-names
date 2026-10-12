"""Registro de fontes (sources.yaml), regras de licença do ADR 0001 (ampliado pelo 0004) e campos da spec 002 (R2)."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pycountry
import yaml

from namescommons.adapters import url_http

LICENCAS_COMPATIVEIS = frozenset({
    "public-domain", "CC0-1.0", "CC-BY-3.0", "CC-BY-4.0",
    "ODC-By-1.0", "OGL-UK-3.0", "etalab-2.0",
    "statcan-open-licence",  # ADR 0004 (docs/adr/0004-licenca-statistics-canada.md)
})
ID_FORMATO = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
COUNT_TYPES = ("births", "population", "attested")
CAMPOS = (
    "id", "name", "url", "license", "attribution", "country",
    "count_type", "primary", "suppression", "retrieved",
)
# Campos opcionais da spec 002 (R2) e seus valores padrão.
OPCIONAIS = {"uniform_case": False, "adapter": True}


class SourceError(ValueError):
    """sources.yaml inválido. A mensagem lista todos os problemas encontrados."""


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


def is_country(code: object) -> bool:
    """Código ISO 3166-1 alfa-2 em maiúsculas."""
    if not isinstance(code, str) or len(code) != 2 or code != code.upper():
        return False
    try:
        return pycountry.countries.get(alpha_2=code) is not None
    except (KeyError, LookupError):
        return False


def load_sources(path: Path) -> dict[str, Source]:
    try:
        dados = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise SourceError(f"não foi possível ler {path}: {e}") from e
    except yaml.YAMLError as e:
        raise SourceError(f"{path}: YAML inválido: {e}") from e
    if dados is None:
        dados = {}
    if not isinstance(dados, dict):
        raise SourceError(f"{path}: a raiz deve ser um mapeamento com a chave 'sources'")
    entradas = dados.get("sources", [])
    if entradas is None:
        entradas = []
    if not isinstance(entradas, list):
        raise SourceError(f"{path}: 'sources' deve ser uma lista")
    return parse_sources(entradas)


def parse_sources(entradas: list[dict]) -> dict[str, Source]:
    erros: list[str] = []
    fontes: dict[str, Source] = {}
    for i, e in enumerate(entradas):
        if not isinstance(e, dict):
            erros.append(f"#{i}: entrada deve ser um mapeamento")
            continue
        rotulo = str(e.get("id") or f"#{i}")
        antes = len(erros)
        faltando = [c for c in CAMPOS if c not in e]
        if faltando:
            erros.append(f"{rotulo}: campos ausentes {faltando}")
            continue
        extras = sorted(set(e) - set(CAMPOS) - set(OPCIONAIS))
        if extras:
            erros.append(f"{rotulo}: campos desconhecidos {extras}")
        for campo in ("id", "name", "url", "attribution"):
            if not isinstance(e[campo], str) or not e[campo].strip():
                erros.append(f"{rotulo}: '{campo}' vazio")
        if isinstance(e["id"], str) and e["id"].strip() and not ID_FORMATO.fullmatch(e["id"]):
            erros.append(f"{rotulo}: 'id' com formato inválido (use [a-z0-9]+(-[a-z0-9]+)*)")
        if isinstance(e["url"], str) and e["url"].strip() and not url_http(e["url"]):
            erros.append(f"{rotulo}: 'url' deve usar o esquema http ou https")
        if not isinstance(e["license"], str) or e["license"] not in LICENCAS_COMPATIVEIS:
            erros.append(f"{rotulo}: licença '{e['license']}' incompatível com o ADR 0001")
        if isinstance(e["country"], bool):
            erros.append(f"{rotulo}: país lido como booleano {e['country']}; escreva o código entre aspas, ex.: \"NO\"")
        elif e["country"] is not None and not is_country(e["country"]):
            erros.append(f"{rotulo}: país '{e['country']}' fora da ISO 3166-1 alfa-2")
        if e["count_type"] not in COUNT_TYPES:
            erros.append(f"{rotulo}: count_type '{e['count_type']}' inválido")
        if not isinstance(e["primary"], bool):
            erros.append(f"{rotulo}: 'primary' deve ser true ou false")
        s = e["suppression"]
        if s is not None and (isinstance(s, bool) or not isinstance(s, int) or s < 1):
            erros.append(f"{rotulo}: 'suppression' deve ser inteiro positivo ou vazio")
        if not isinstance(e["retrieved"], date) or isinstance(e["retrieved"], datetime):
            erros.append(f"{rotulo}: 'retrieved' deve ser uma data AAAA-MM-DD, sem hora")
        for campo in OPCIONAIS:
            if campo in e and not isinstance(e[campo], bool):
                erros.append(f"{rotulo}: '{campo}' deve ser true ou false")
        if len(erros) > antes:
            continue
        if e["id"] in fontes:
            erros.append(f"{rotulo}: id duplicado")
            continue
        opcionais = {c: e.get(c, padrao) for c, padrao in OPCIONAIS.items()}
        fontes[e["id"]] = Source(**{c: e[c] for c in CAMPOS}, **opcionais)

    # Exatamente uma primary por (country, count_type) com contagem; em attested, primary não
    # tem efeito e não é conferido (spec 004, R5; issue #3).
    grupos: dict[tuple, list[Source]] = {}
    for f in fontes.values():
        if f.count_type == "attested":
            continue
        grupos.setdefault((f.country, f.count_type), []).append(f)
    for (pais, tipo), fs in sorted(grupos.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        if len(fs) > 1 and sum(f.primary is True for f in fs) != 1:
            ids = sorted(f.id for f in fs)
            erros.append(f"{pais}/{tipo}: fontes {ids}; exatamente uma deve ter primary: true")

    if erros:
        raise SourceError("\n".join(erros))
    return fontes
