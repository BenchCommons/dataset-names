"""Tabela canônica de observações (spec 001, R1) e sua validação."""

import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone

from namescommons.normalize import ascii_form, detect_script, name_key, normalize_name
from namescommons.sources import COUNT_TYPES, Source, is_country

# 1.1.0: variant_links.parquet na release (spec 004, R4.7).
# 1.2.0 (spec 005, R8): group_id preenchido; ascii em cirílico e possivelmente vazio em latim;
# Jpan, Hrkt e Kore; partículas e nova forma de exibição. ingest e build de uma release devem usar
# a mesma versão: validate confere script por igualdade com detect_script(name) e ascii só como
# ASCII em minúsculas (não recalcula a transliteração).
SCHEMA_VERSION = "1.2.0"
KINDS = ("given", "family")
GENDERS = ("F", "M")
ANO_MINIMO = 1800


def _agora(tz: timezone) -> datetime:
    return datetime.now(tz)


@dataclass(frozen=True, slots=True)
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


def derive_name_fields(raw_name: str, uniform_case: bool | None = None) -> tuple[str, str, str, str]:
    """(name, name_key, ascii, script) derivados do nome publicado."""
    name = normalize_name(raw_name, uniform_case)
    script = detect_script(name)
    return name, name_key(name), ascii_form(name, script), script


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
    uniform_case: bool | None = None,
) -> Observation:
    """Constrói uma observação derivando name, name_key, ascii e script do nome publicado."""
    name, chave, forma_ascii, script = derive_name_fields(raw_name, uniform_case)
    return Observation(
        name=name, name_key=chave, ascii=forma_ascii, script=script,
        kind=kind, country=country, gender=gender, year=year, count=count,
        count_type=count_type, source_id=source_id,
    )


def validate(observations: list[Observation], sources: dict[str, Source]) -> None:
    """Levanta ValidationError com todos os problemas encontrados."""
    ano_maximo = _agora(timezone.utc).year + 1  # UTC: o resultado não depende do fuso da máquina
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
        if o.ascii and (not o.ascii.isascii() or o.ascii != o.ascii.lower()):
            erros.append(f"{r}: 'ascii' {o.ascii!r} com maiúscula ou caractere fora do ASCII (spec 005, R2.5)")
        if o.kind and o.kind not in KINDS:
            erros.append(f"{r}: kind '{o.kind}' inválido")
        fonte = sources.get(o.source_id)
        if o.country is not None and not is_country(o.country):
            erros.append(f"{r}: país '{o.country}' fora da ISO 3166-1 alfa-2")
        elif fonte is not None and fonte.country is not None and o.country != fonte.country:
            erros.append(f"{r}: país {o.country!r} diverge da fonte '{fonte.id}' ('{fonte.country}')")
        if o.gender is not None and o.gender not in GENDERS:
            erros.append(f"{r}: gender '{o.gender}' inválido")
        if o.count is not None and o.count < 0:
            erros.append(f"{r}: count negativo")
        if o.count_type and o.count_type not in COUNT_TYPES:
            erros.append(f"{r}: count_type '{o.count_type}' inválido")
        elif fonte is not None and o.count_type != fonte.count_type:
            erros.append(
                f"{r}: count_type '{o.count_type}' diverge da fonte '{fonte.id}' ('{fonte.count_type}')"
            )
        if o.year is not None and not ANO_MINIMO <= o.year <= ano_maximo:
            erros.append(f"{r}: year {o.year} fora de {ANO_MINIMO} a {ano_maximo}")
        if (o.count is None) != (o.count_type == "attested"):
            erros.append(f"{r}: count vazio exige count_type 'attested' e vice-versa (R1.1)")
        if o.source_id and o.source_id not in sources:
            erros.append(f"{r}: source_id '{o.source_id}' ausente de sources.yaml")
        if o.key() in vistas:
            erros.append(f"{r}: duplicata pela chave (R1.4) {o.key()}")
        vistas.add(o.key())
    if erros:
        raise ValidationError(erros)
