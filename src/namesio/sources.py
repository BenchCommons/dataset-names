"""Registro de fontes (sources.yaml) e regras de licença do ADR 0001."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pycountry
import yaml

LICENCAS_COMPATIVEIS = frozenset({
    "public-domain", "CC0-1.0", "CC-BY-3.0", "CC-BY-4.0",
    "ODC-By-1.0", "OGL-UK-3.0", "etalab-2.0",
})
COUNT_TYPES = ("births", "population", "attested")
CAMPOS = (
    "id", "name", "url", "license", "attribution", "country",
    "count_type", "primary", "suppression", "retrieved",
)


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


def is_country(code: object) -> bool:
    """Código ISO 3166-1 alfa-2 em maiúsculas."""
    if not isinstance(code, str) or len(code) != 2 or code != code.upper():
        return False
    try:
        return pycountry.countries.get(alpha_2=code) is not None
    except (KeyError, LookupError):
        return False


def load_sources(path: Path) -> dict[str, Source]:
    dados = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return parse_sources(dados.get("sources") or [])


def parse_sources(entradas: list[dict]) -> dict[str, Source]:
    erros: list[str] = []
    fontes: dict[str, Source] = {}
    for i, e in enumerate(entradas):
        rotulo = e.get("id") or f"#{i}"
        faltando = [c for c in CAMPOS if c not in e]
        if faltando:
            erros.append(f"{rotulo}: campos ausentes {faltando}")
            continue
        extras = sorted(set(e) - set(CAMPOS))
        if extras:
            erros.append(f"{rotulo}: campos desconhecidos {extras}")
        for campo in ("id", "name", "url", "attribution"):
            if not isinstance(e[campo], str) or not e[campo].strip():
                erros.append(f"{rotulo}: '{campo}' vazio")
        if e["license"] not in LICENCAS_COMPATIVEIS:
            erros.append(f"{rotulo}: licença '{e['license']}' incompatível com o ADR 0001")
        if e["country"] is not None and not is_country(e["country"]):
            erros.append(f"{rotulo}: país '{e['country']}' fora da ISO 3166-1 alfa-2")
        if e["count_type"] not in COUNT_TYPES:
            erros.append(f"{rotulo}: count_type '{e['count_type']}' inválido")
        if not isinstance(e["primary"], bool):
            erros.append(f"{rotulo}: 'primary' deve ser true ou false")
        s = e["suppression"]
        if s is not None and (isinstance(s, bool) or not isinstance(s, int) or s < 1):
            erros.append(f"{rotulo}: 'suppression' deve ser inteiro positivo ou vazio")
        if not isinstance(e["retrieved"], date):
            erros.append(f"{rotulo}: 'retrieved' deve ser uma data AAAA-MM-DD")
        if e["id"] in fontes:
            erros.append(f"{rotulo}: id duplicado")
            continue
        fontes[e["id"]] = Source(**{c: e[c] for c in CAMPOS})

    grupos: dict[tuple, list[Source]] = {}
    for f in fontes.values():
        grupos.setdefault((f.country, f.count_type), []).append(f)
    for (pais, tipo), fs in sorted(grupos.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        if len(fs) > 1 and sum(f.primary is True for f in fs) != 1:
            ids = sorted(f.id for f in fs)
            erros.append(f"{pais}/{tipo}: fontes {ids}; exatamente uma deve ter primary: true")

    if erros:
        raise SourceError("\n".join(erros))
    return fontes
