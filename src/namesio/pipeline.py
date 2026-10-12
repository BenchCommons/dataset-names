"""Pipeline de ingestão (spec 002, R1 e R5): fontes -> cache -> parse -> observações."""

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from namesio.adapters import DEFAULT_PACKAGE, AdapterError, RawRecord, load_adapter
from namesio.cache import FetchError, fetch_resource
from namesio.schema import Observation, ValidationError, derive_name_fields, validate
from namesio.sources import Source


class PipelineError(Exception):
    """Falha de uma fonte em fetch ou ingest; a mensagem nomeia a fonte e a causa."""


class RecordError(ValueError):
    """Registros de uma fonte que violam R1.4 ou R1.5."""


# Exceções cuja mensagem já explica a causa; as demais ganham o nome do tipo.
_ERROS_DO_DOMINIO = (AdapterError, FetchError, ValidationError, RecordError)


def _falha(fonte: Source, e: Exception) -> PipelineError:
    causa = str(e) if isinstance(e, _ERROS_DO_DOMINIO) else f"{type(e).__name__}: {e}"
    return PipelineError(f"fonte '{fonte.id}': {causa}")


def _vazio(valor: str | None) -> str | None:
    """R1.1: vazio e só espaços viram None; espaços em volta são removidos."""
    if valor is None:
        return None
    return valor.strip() or None


def _ordem(o: Observation) -> tuple:
    return (o.source_id, o.kind, o.country or "", o.name_key, -1 if o.year is None else o.year, o.gender or "")


def _somar(a: Observation, b: Observation) -> Observation:
    """R1.4: soma duas observações com a mesma chave; mantém a forma do primeiro registro."""
    if (a.count is None) != (b.count is None):
        raise RecordError(f"R1.4: registros repetidos com e sem count para {a.key()}")
    return a if a.count is None else replace(a, count=a.count + b.count)


def _checar_genero(observacoes: Iterable[Observation]) -> None:
    """R1.5: total sem gender e divisão por gender não podem coexistir no mesmo grupo."""
    com: set[tuple] = set()
    sem: set[tuple] = set()
    for o in observacoes:
        (com if o.gender is not None else sem).add((o.name_key, o.kind, o.country, o.year))
    conflitos = sorted(com & sem, key=repr)
    if conflitos:
        raise RecordError(
            f"R1.5: {len(conflitos)} grupo(s) com linhas com e sem gender, ex.: {conflitos[0]}"
        )


def _checar_tipos(r: RawRecord, posicao: int) -> None:
    """Rejeita tipos errados nos campos do registro, nomeando campo, valor e posição (1 = primeiro)."""
    for campo in ("year", "count"):
        v = getattr(r, campo)
        if v is not None and (type(v) is not int):
            raise RecordError(
                f"registro {posicao}: '{campo}' deve ser inteiro, recebeu {type(v).__name__} {v!r}"
            )
    for campo in ("name", "kind", "country", "gender"):
        v = getattr(r, campo)
        if v is not None and not isinstance(v, str):
            raise RecordError(
                f"registro {posicao}: '{campo}' deve ser texto, recebeu {type(v).__name__} {v!r}"
            )


def to_observations(records: Iterable[RawRecord], source: Source) -> list[Observation]:
    """Aplica R1.1 a R1.5 aos registros brutos de uma fonte."""
    derivados: dict[str, tuple[str, str, str, str]] = {}
    unicas: dict[tuple, Observation] = {}
    for posicao, r in enumerate(records, start=1):
        _checar_tipos(r, posicao)
        campos = derivados.get(r.name)
        if campos is None:
            campos = derivados[r.name] = derive_name_fields(r.name, source.uniform_case)
        nome, chave, forma_ascii, escrita = campos
        o = Observation(
            name=nome, name_key=chave, ascii=forma_ascii, script=escrita, kind=r.kind,
            country=_vazio(r.country), gender=_vazio(r.gender), year=r.year, count=r.count,
            count_type=source.count_type, source_id=source.id,
        )
        anterior = unicas.get(o.key())
        unicas[o.key()] = o if anterior is None else _somar(anterior, o)
    _checar_genero(unicas.values())
    return sorted(unicas.values(), key=_ordem)


def select_sources(sources: dict[str, Source], ids: list[str]) -> list[Source]:
    """Fontes indicadas, ou todas com adaptador se nenhuma for indicada."""
    if not ids:
        escolhidas = [f for f in sources.values() if f.adapter]
        if not escolhidas:
            raise PipelineError("nenhuma fonte com adaptador em sources.yaml")
        return sorted(escolhidas, key=lambda f: f.id)
    escolhidas = []
    for i in dict.fromkeys(ids):
        if i not in sources:
            raise PipelineError(f"fonte '{i}' ausente de sources.yaml")
        if not sources[i].adapter:
            raise PipelineError(f"fonte '{i}' tem adapter: false e não pode ser baixada nem ingerida")
        escolhidas.append(sources[i])
    return escolhidas


def fetch_sources(
    selected: list[Source],
    cache_dir: Path,
    *,
    refresh: bool = False,
    adapters: str = DEFAULT_PACKAGE,
    **opcoes,
) -> None:
    """Baixa os recursos de cada fonte para o cache (R4); para na primeira fonte que falhar."""
    for fonte in selected:
        try:
            mod = load_adapter(fonte.id, adapters)
            for recurso in mod.RESOURCES:
                fetch_resource(cache_dir, fonte.id, recurso, refresh=refresh, **opcoes)
        except Exception as e:
            raise _falha(fonte, e) from e


def ingest_sources(
    selected: list[Source],
    sources: dict[str, Source],
    cache_dir: Path,
    *,
    offline: bool = False,
    adapters: str = DEFAULT_PACKAGE,
    **opcoes,
) -> list[Observation]:
    """Roda parse sobre o cache, aplica R1 e valida cada fonte (spec 001 e R3)."""
    observacoes: list[Observation] = []
    for fonte in selected:
        try:
            mod = load_adapter(fonte.id, adapters)
            arquivos = {
                r.filename: fetch_resource(cache_dir, fonte.id, r, offline=offline, **opcoes)
                for r in mod.RESOURCES
            }
            obs = to_observations(mod.parse(arquivos), fonte)
            if not obs:
                raise RecordError("nenhum registro produzido por parse")
            validate(obs, sources)
        except Exception as e:
            raise _falha(fonte, e) from e
        observacoes.extend(obs)
    return observacoes
