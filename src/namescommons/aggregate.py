"""Saídas agregadas (spec 001, R3): listas por país e índice mundial."""

from collections import defaultdict
from dataclasses import dataclass, replace

from namescommons.normalize import ascii_form, detect_script
from namescommons.schema import Observation
from namescommons.sources import Source

# Ordem de preferência quando o mesmo nome tem contagens de tipos diferentes no país.
PRECEDENCIA = ("population", "births")


class AggregationError(ValueError):
    """Dados que impedem uma agregação inequívoca."""


@dataclass(frozen=True)
class CountryRow:
    country: str
    kind: str
    name: str
    name_key: str
    ascii: str
    script: str
    count: int | None
    count_type: str
    rank: int | None
    female_share: float | None
    gender_basis: int
    female: int  # interno: alimenta o índice mundial; não sai no CSV
    first_year: int | None
    last_year: int | None


@dataclass(frozen=True)
class CountryEntry:
    country: str
    count: int | None
    count_type: str
    rank: int | None


@dataclass(frozen=True)
class IndexRow:
    name: str
    name_key: str
    ascii: str
    script: str
    country_count: int
    countries: tuple[CountryEntry, ...]
    female_share: float | None
    gender_basis: int
    group_id: str | None
    sources: tuple[str, ...]


def display_name(obs: list[Observation]) -> str:
    """Forma mais frequente por soma de count; empate: mais atestada; depois ordem lexicográfica."""
    peso: dict[str, int] = defaultdict(int)
    atestacoes: dict[str, int] = defaultdict(int)
    for o in obs:
        peso[o.name] += o.count or 0
        atestacoes[o.name] += 1
    return min(peso, key=lambda n: (-peso[n], -atestacoes[n], n))


def _fontes_oficiais(observations: list[Observation], sources: dict[str, Source]) -> dict[tuple, str]:
    """(país, count_type) -> source_id cuja contagem vale (R3.3)."""
    desconhecidas = sorted({o.source_id for o in observations} - set(sources))
    if desconhecidas:
        raise AggregationError(f"source_id desconhecido em sources.yaml: {desconhecidas}")
    ids: dict[tuple, set[str]] = defaultdict(set)
    for o in observations:
        if o.count is not None and o.country is not None:
            ids[(o.country, o.count_type)].add(o.source_id)
    oficiais = {}
    for par, fs in ids.items():
        if len(fs) == 1:
            oficiais[par] = next(iter(fs))
            continue
        primarias = sorted(f for f in fs if sources[f].primary)
        if len(primarias) != 1:
            raise AggregationError(f"{par}: fontes {sorted(fs)} sem exatamente uma primary")
        oficiais[par] = primarias[0]
    return oficiais


def _edicoes(observations: list[Observation], oficiais: dict[tuple, str]) -> dict[str, int]:
    """país -> edição mais recente (maior year) da fonte population oficial (R3.3)."""
    edicoes: dict[str, int] = {}
    for o in observations:
        if (
            o.count_type == "population" and o.year is not None and o.country is not None
            and o.source_id == oficiais.get((o.country, "population"))
        ):
            edicoes[o.country] = max(edicoes.get(o.country, o.year), o.year)
    return edicoes


def _contagem(obs: list[Observation], oficiais: dict[tuple, str], edicoes: dict[str, int]):
    """-> (count_type, observações contadas, first_year, last_year) para um nome num país."""
    pais = obs[0].country
    for tipo in PRECEDENCIA:
        fonte = oficiais.get((pais, tipo))
        contadas = [o for o in obs if o.count_type == tipo and o.source_id == fonte]
        if not contadas:
            continue
        if tipo == "population" and pais in edicoes:
            ultimo = edicoes[pais]
            contadas = [o for o in contadas if o.year == ultimo]
            if not contadas:
                continue
            return tipo, contadas, ultimo, ultimo
        anos = [o.year for o in contadas if o.year is not None]
        return tipo, contadas, (min(anos) if anos else None), (max(anos) if anos else None)
    return "attested", [], None, None


def _ranquear(linhas: list[CountryRow]) -> list[CountryRow]:
    """Rank denso por (kind, count_type), decrescente por count."""
    valores: dict[tuple, list[int]] = defaultdict(list)
    for r in linhas:
        if r.count is not None:
            valores[(r.kind, r.count_type)].append(r.count)
    posicao = {
        grupo: {v: i + 1 for i, v in enumerate(sorted(set(vs), reverse=True))}
        for grupo, vs in valores.items()
    }
    ranqueadas = [
        r if r.count is None else replace(r, rank=posicao[(r.kind, r.count_type)][r.count])
        for r in linhas
    ]
    return sorted(ranqueadas, key=lambda r: (r.kind, r.rank is None, r.count_type, r.rank or 0, r.name_key))


def by_country(observations: list[Observation], sources: dict[str, Source]) -> dict[str, list[CountryRow]]:
    oficiais = _fontes_oficiais(observations, sources)
    edicoes = _edicoes(observations, oficiais)
    grupos: dict[tuple, list[Observation]] = defaultdict(list)
    for o in observations:
        if o.country is not None:
            grupos[(o.country, o.kind, o.name_key)].append(o)
    linhas: dict[str, list[CountryRow]] = defaultdict(list)
    for (pais, kind, chave), obs in grupos.items():
        tipo, contadas, primeiro, ultimo = _contagem(obs, oficiais, edicoes)
        f = sum(o.count for o in contadas if o.gender == "F")
        m = sum(o.count for o in contadas if o.gender == "M")
        nome = display_name(obs)
        escrita = detect_script(nome)
        linhas[pais].append(CountryRow(
            country=pais, kind=kind, name=nome, name_key=chave,
            ascii=ascii_form(nome, escrita), script=escrita,
            count=sum(o.count for o in contadas) if contadas else None,
            count_type=tipo, rank=None,
            female_share=f / (f + m) if f + m else None, gender_basis=f + m, female=f,
            first_year=primeiro, last_year=ultimo,
        ))
    return {pais: _ranquear(rows) for pais, rows in sorted(linhas.items())}


def name_index(
    observations: list[Observation],
    country_rows: dict[str, list[CountryRow]],
    kind: str,
) -> list[IndexRow]:
    obs_por_chave: dict[str, list[Observation]] = defaultdict(list)
    for o in observations:
        if o.kind == kind:
            obs_por_chave[o.name_key].append(o)
    linhas_por_chave: dict[str, list[CountryRow]] = defaultdict(list)
    for rows in country_rows.values():
        for r in rows:
            if r.kind == kind:
                linhas_por_chave[r.name_key].append(r)
    indice = []
    for chave in sorted(obs_por_chave):
        obs = obs_por_chave[chave]
        rows = sorted(linhas_por_chave.get(chave, []), key=lambda r: r.country)
        nome = display_name(obs)
        escrita = detect_script(nome)
        female = sum(r.female for r in rows)
        base = sum(r.gender_basis for r in rows)
        indice.append(IndexRow(
            name=nome, name_key=chave, ascii=ascii_form(nome, escrita), script=escrita,
            country_count=len(rows),
            countries=tuple(CountryEntry(r.country, r.count, r.count_type, r.rank) for r in rows),
            female_share=female / base if base else None, gender_basis=base,
            group_id=None, sources=tuple(sorted({o.source_id for o in obs})),
        ))
    return indice
