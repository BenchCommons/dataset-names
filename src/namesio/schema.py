"""Tabela canônica de observações (spec 001, R1) e sua validação."""

import unicodedata
from dataclasses import dataclass

from namesio.normalize import ascii_form, detect_script, name_key, normalize_name
from namesio.sources import COUNT_TYPES, Source, is_country

SCHEMA_VERSION = "1.0.0"
KINDS = ("given", "family")
GENDERS = ("F", "M")


@dataclass(frozen=True)
class Observation:
    name: str
    name_key: str
    ascii: str
    script: str
    kind: str
    country: str | None
    gender: str | None
    year: int | None
    count: int | None
    count_type: str
    source_id: str

    def key(self) -> tuple:
        """Chave de unicidade (R1.4)."""
        return (self.name_key, self.kind, self.country, self.gender, self.year, self.source_id)


class ValidationError(ValueError):
    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__(f"{len(erros)} erro(s) de validação:\n" + "\n".join(erros[:50]))


def make_observation(
    raw_name: str,
    *,
    kind: str,
    source_id: str,
    count_type: str,
    country: str | None = None,
    gender: str | None = None,
    year: int | None = None,
    count: int | None = None,
) -> Observation:
    """Constrói uma observação derivando name, name_key, ascii e script do nome publicado."""
    name = normalize_name(raw_name)
    script = detect_script(name)
    return Observation(
        name=name, name_key=name_key(name), ascii=ascii_form(name, script), script=script,
        kind=kind, country=country, gender=gender, year=year, count=count,
        count_type=count_type, source_id=source_id,
    )


def validate(observations: list[Observation], sources: dict[str, Source]) -> None:
    """Levanta ValidationError com todos os problemas encontrados."""
    erros: list[str] = []
    vistas: set[tuple] = set()
    for i, o in enumerate(observations):
        r = f"observação {i} ({o.name!r})"
        for campo in ("name", "name_key", "script", "kind", "count_type", "source_id"):
            if not getattr(o, campo):
                erros.append(f"{r}: '{campo}' vazio")
        if o.name != " ".join(unicodedata.normalize("NFC", o.name).split()):
            erros.append(f"{r}: 'name' fora de NFC ou com espaços não colapsados (R1)")
        if o.name_key != name_key(o.name):
            erros.append(f"{r}: 'name_key' {o.name_key!r} diverge de name_key(name) (R1)")
        if o.script != detect_script(o.name):
            erros.append(f"{r}: 'script' {o.script!r} diverge da escrita detectada em name (R1)")
        if o.script == "Latn" and not o.ascii:
            erros.append(f"{r}: 'ascii' vazio em escrita latina")
        if o.kind and o.kind not in KINDS:
            erros.append(f"{r}: kind '{o.kind}' inválido")
        if o.country is not None and not is_country(o.country):
            erros.append(f"{r}: país '{o.country}' fora da ISO 3166-1 alfa-2")
        if o.gender is not None and o.gender not in GENDERS:
            erros.append(f"{r}: gender '{o.gender}' inválido")
        if o.count is not None and o.count < 0:
            erros.append(f"{r}: count negativo")
        if o.count_type and o.count_type not in COUNT_TYPES:
            erros.append(f"{r}: count_type '{o.count_type}' inválido")
        if (o.count is None) != (o.count_type == "attested"):
            erros.append(f"{r}: count vazio exige count_type 'attested' e vice-versa (R1.1)")
        if o.source_id and o.source_id not in sources:
            erros.append(f"{r}: source_id '{o.source_id}' ausente de sources.yaml")
        if o.key() in vistas:
            erros.append(f"{r}: duplicata pela chave (R1.4) {o.key()}")
        vistas.add(o.key())
    if erros:
        raise ValidationError(erros)
