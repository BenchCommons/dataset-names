"""Tabela variant_links (spec 004, R4; ADR 0009): ligações entre nomes publicadas por uma fonte."""

import re
from dataclasses import dataclass

from namescommons.normalize import name_key
from namescommons.schema import KINDS, ValidationError
from namescommons.sources import Source

RELATIONS = (
    "same_item", "said_to_be_the_same", "family_name_identical",
    "other_gender", "different_from", "transliteration",
)
# Relações entre rótulos do mesmo item: o destino é o próprio item.
MESMO_ITEM = ("same_item", "transliteration")
QID = re.compile(r"Q[1-9][0-9]*")


@dataclass(frozen=True, slots=True)
class VariantLink:
    source_id: str
    relation: str
    qid: str
    name: str
    name_key: str
    kind: str
    target_qid: str
    target_name: str
    target_name_key: str
    target_kind: str

    def ordem(self) -> tuple:
        return (self.source_id, self.qid, self.relation, self.kind, self.name_key, self.name,
                self.target_qid, self.target_kind, self.target_name_key, self.target_name)


def link_problems(v) -> list[str]:
    """Problemas de valor de uma ligação (bruta ou normalizada), sem conferir name_key."""
    problemas = []
    if v.relation not in RELATIONS:
        problemas.append(f"relation {v.relation!r} inválida; use uma de {list(RELATIONS)}")
    for campo in ("qid", "target_qid"):
        valor = getattr(v, campo)
        if not isinstance(valor, str) or not QID.fullmatch(valor):
            problemas.append(f"{campo} {valor!r} fora do formato Q<n>")
    for campo in ("kind", "target_kind"):
        if getattr(v, campo) not in KINDS:
            problemas.append(f"{campo} {getattr(v, campo)!r} inválido; use 'given' ou 'family'")
    if v.relation in MESMO_ITEM and v.target_qid != v.qid:
        problemas.append(f"{v.relation} exige target_qid igual a qid")
    return problemas


def validate_links(links: list[VariantLink], sources: dict[str, Source]) -> None:
    """Levanta ValidationError com todos os problemas da tabela (R4.5)."""
    erros: list[str] = []
    vistas: set[VariantLink] = set()
    for i, v in enumerate(links, start=1):
        r = f"ligação {i} ({v.name!r} -> {v.target_name!r})"
        erros.extend(f"{r}: {p}" for p in link_problems(v))
        for campo, chave in (("name", "name_key"), ("target_name", "target_name_key")):
            nome = getattr(v, campo)
            if not nome:
                erros.append(f"{r}: '{campo}' vazio")
            elif getattr(v, chave) != name_key(nome):
                erros.append(f"{r}: '{chave}' {getattr(v, chave)!r} diverge de name_key({campo})")
        if (v.name_key, v.kind) == (v.target_name_key, v.target_kind):
            erros.append(f"{r}: liga o nome a ele mesmo (mesmo name_key e kind)")
        if v.source_id not in sources:
            erros.append(f"{r}: source_id {v.source_id!r} ausente de sources.yaml")
        if v in vistas:
            erros.append(f"{r}: repetida")
        vistas.add(v)
    if erros:
        raise ValidationError(erros)
