"""Pipeline de ingestão (spec 002, R1 e R5): fontes -> cache -> parse -> observações."""

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from namescommons.adapters import (
    DEFAULT_PACKAGE, AdapterError, FormatError, RawLink, RawRecord, SourceFiles, load_adapter,
)
from namescommons.cache import FetchError, fetch_resource
from namescommons.links import VariantLink, link_problems, validate_links
from namescommons.schema import GENDERS, KINDS, Observation, ValidationError, derive_name_fields, validate
from namescommons.sources import Source, is_country


class PipelineError(Exception):
    """Falha de uma fonte em fetch ou ingest; a mensagem nomeia a fonte e a causa."""


class RecordError(ValueError):
    """Registros de uma fonte que violam R1.4 ou R1.5."""


# Exceções cuja mensagem já explica a causa; as demais ganham o nome do tipo.
_ERROS_DO_DOMINIO = (AdapterError, FetchError, ValidationError, RecordError, FormatError)


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


def _resolver_formas(formas: dict[str, list]) -> Observation:
    """R1.4: soma as contagens das formas de um mesmo nome e fica com a de maior peso.

    Mesmo critério de `display_name` na agregação; no empate vale a forma do primeiro registro.
    """
    pesos = [c for _, c in formas.values()]
    melhor = max(formas.values(), key=lambda f: -1 if f[1] is None else f[1])[0]
    return replace(melhor, count=None if pesos[0] is None else sum(pesos))


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


def _checar_kind(kind: str, posicao: int) -> None:
    """Spec 003, R2.1: kind é conferido antes de derivar o nome, para ser o primeiro erro do registro."""
    if kind not in KINDS:
        raise RecordError(f"registro {posicao}: kind {kind!r} inválido; use 'given' ou 'family'")


def _checar_valores(o: Observation, posicao: int, paises: dict[str, bool]) -> None:
    """Spec 003, R2.1 e R2.3: valores convertidos pelo adaptador, conferidos na ordem do arquivo."""
    if o.gender is not None and o.gender not in GENDERS:
        raise RecordError(f"registro {posicao}: gender {o.gender!r} inválido; use 'F', 'M' ou vazio")
    if o.country is not None:
        valido = paises.get(o.country)
        if valido is None:
            valido = paises[o.country] = is_country(o.country)
        if not valido:
            raise RecordError(f"registro {posicao}: country {o.country!r} fora da ISO 3166-1 alfa-2")
    if o.count is None and o.count_type != "attested":
        raise RecordError(
            f"registro {posicao}: count vazio numa fonte '{o.count_type}'; "
            "valor suprimido deve ser omitido pelo adaptador"
        )
    if o.count is not None and o.count_type == "attested":
        raise RecordError(f"registro {posicao}: count {o.count} numa fonte 'attested'")


def to_observations(records: Iterable[RawRecord], source: Source) -> list[Observation]:
    """Aplica R1.1 a R1.5 aos registros brutos de uma fonte."""
    derivados: dict[str, tuple[str, str, str, str]] = {}
    paises: dict[str, bool] = {}
    unicas: dict[tuple, Observation] = {}
    formas: dict[tuple, dict[str, list]] = {}  # só chaves com mais de uma forma de escrita
    for posicao, r in enumerate(records, start=1):
        _checar_tipos(r, posicao)
        _checar_kind(r.kind, posicao)
        campos = derivados.get(r.name)
        if campos is None:
            campos = derivados[r.name] = derive_name_fields(r.name, source.uniform_case)
        nome, chave, forma_ascii, escrita = campos
        o = Observation(
            name=nome, name_key=chave, ascii=forma_ascii, script=escrita, kind=r.kind,
            country=_vazio(r.country), gender=_vazio(r.gender), year=r.year, count=r.count,
            count_type=source.count_type, source_id=source.id,
        )
        _checar_valores(o, posicao, paises)
        chave_o = o.key()
        anterior = unicas.get(chave_o)
        if anterior is None:
            unicas[chave_o] = o
            continue
        if (anterior.count is None) != (o.count is None):
            raise RecordError(f"R1.4: registros repetidos com e sem count para {chave_o}")
        por_forma = formas.get(chave_o)
        if por_forma is not None:  # caminho lento: a chave já tem duas formas de escrita
            visto = por_forma.get(o.name)
            if visto is None:
                por_forma[o.name] = [o, o.count]
            elif o.count is not None:
                visto[1] += o.count
        elif anterior.name != o.name:
            formas[chave_o] = {anterior.name: [anterior, anterior.count], o.name: [o, o.count]}
        elif o.count is not None:  # caminho rápido: mesma forma, soma no lugar
            unicas[chave_o] = replace(anterior, count=anterior.count + o.count)
    for chave_o, por_forma in formas.items():
        unicas[chave_o] = _resolver_formas(por_forma)
    _checar_genero(unicas.values())
    return sorted(unicas.values(), key=_ordem)


_CAMPOS_DA_LIGACAO = ("relation", "qid", "name", "kind", "target_qid", "target_name", "target_kind")


def to_links(records: Iterable[RawLink], source: Source) -> list[VariantLink]:
    """Spec 004, R4.2 e R4.4: normaliza os nomes, descarta auto-ligações e repetidas e ordena."""
    derivados: dict[str, tuple[str, str, str, str]] = {}
    unicas: set[VariantLink] = set()
    for posicao, r in enumerate(records, start=1):
        for campo in _CAMPOS_DA_LIGACAO:
            v = getattr(r, campo)
            if not isinstance(v, str):
                raise RecordError(f"ligação {posicao}: '{campo}' deve ser texto, recebeu {type(v).__name__} {v!r}")
        problemas = link_problems(r)
        if problemas:
            raise RecordError(f"ligação {posicao}: {problemas[0]}")
        nomes = []
        for campo in ("name", "target_name"):
            bruto = getattr(r, campo)
            campos = derivados.get(bruto)
            if campos is None:
                campos = derivados[bruto] = derive_name_fields(bruto, source.uniform_case)
            if not campos[0]:
                raise RecordError(f"ligação {posicao}: {campo} vazio")
            nomes.append(campos)
        (nome, chave, *_), (alvo, chave_alvo, *_) = nomes
        if (chave, r.kind) == (chave_alvo, r.target_kind):
            continue
        unicas.add(VariantLink(
            source_id=source.id, relation=r.relation, qid=r.qid, name=nome, name_key=chave, kind=r.kind,
            target_qid=r.target_qid, target_name=alvo, target_name_key=chave_alvo, target_kind=r.target_kind,
        ))
    return sorted(unicas, key=VariantLink.ordem)


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
            arquivos = SourceFiles(
                (r.filename, fetch_resource(cache_dir, fonte.id, r, offline=offline, **opcoes))
                for r in mod.RESOURCES
            )
            obs = to_observations(mod.parse(arquivos), fonte)
            if not obs:
                raise RecordError("nenhum registro produzido por parse")
            validate(obs, sources)
        except Exception as e:
            raise _falha(fonte, e) from e
        observacoes.extend(obs)
    return observacoes


def ingest_links(
    selected: list[Source],
    sources: dict[str, Source],
    cache_dir: Path,
    *,
    offline: bool = False,
    adapters: str = DEFAULT_PACKAGE,
    **opcoes,
) -> list[VariantLink] | None:
    """Roda links sobre o cache das fontes que o implementam (spec 004, R4); None se nenhuma implementa."""
    ligacoes: list[VariantLink] | None = None
    for fonte in selected:
        try:
            mod = load_adapter(fonte.id, adapters)
            if getattr(mod, "links", None) is None:
                continue
            arquivos = SourceFiles(
                (r.filename, fetch_resource(cache_dir, fonte.id, r, offline=offline, **opcoes))
                for r in mod.RESOURCES
            )
            daqui = to_links(mod.links(arquivos), fonte)
            validate_links(daqui, sources)
        except Exception as e:
            raise _falha(fonte, e) from e
        ligacoes = (ligacoes or []) + daqui
    return ligacoes
