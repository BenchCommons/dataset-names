"""Wikidata: prenomes (Q202444) e sobrenomes (Q101352) com rótulo nativo e classe de gênero (spec 004).

Os recursos são páginas de consultas SPARQL ao QLever (ADR 0008), no formato SPARQL 1.1 Query
Results JSON. parse emite os nomes; links emite as ligações entre variantes (ADR 0009).
"""

import json
import re
import unicodedata
from collections.abc import Iterator
from itertools import combinations
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from namescommons.adapters import FormatError, RawLink, RawRecord, Resource
from namescommons.normalize import name_key, normalize_name

SOURCE_ID = "wikidata"
ENDPOINT = "https://qlever.dev/api/wikidata"
LINHAS_POR_PAGINA = 200_000
PREFIXOS = (
    "PREFIX wd: <http://www.wikidata.org/entity/> "
    "PREFIX wdt: <http://www.wikidata.org/prop/direct/> "
    "PREFIX p: <http://www.wikidata.org/prop/> "
    "PREFIX pq: <http://www.wikidata.org/prop/qualifier/>"
)
_ENTIDADE = re.compile(r"http://www\.wikidata\.org/entity/(Q[1-9][0-9]*)")

# R3.4: classe de gênero (alcançada por P31/P279*) -> gêneros emitidos.
GENERO_PRENOME = {"Q12308941": ("M",), "Q11879590": ("F",), "Q3409032": ("F", "M")}
GENERO_SOBRENOME = {
    "Q18972245": ("M",), "Q136439710": ("M",),
    "Q18972207": ("F",), "Q136439688": ("F",),
}

# R3.2: caracteres que denunciam um rótulo que não é só o nome.
_PROIBIDOS = frozenset("()[]{}/\\,;:_|?!@#\"=<>*+&%$~^`")


@dataclass(frozen=True)
class Consulta:
    """Consulta SPARQL paginada: arquivo <nome>-<k>.json para k de 1 a paginas."""

    nome: str
    variaveis: tuple[str, ...]
    padrao: str  # padrão do WHERE, sem chaves
    paginas: int

    def sparql(self, pagina: int | None = None, itens: tuple[str, ...] = ()) -> str:
        """Texto da consulta; `itens` restringe a poucos itens (só para gerar a amostra)."""
        restricao = f"VALUES ?item {{ {' '.join('wd:' + q for q in itens)} }} " if itens else ""
        selecao = " ".join("?" + v for v in self.variaveis)
        texto = (f"{PREFIXOS} SELECT DISTINCT {selecao} WHERE {{ {restricao}{self.padrao} }} "
                 f"ORDER BY {selecao}")
        if pagina is not None:
            texto += f" LIMIT {LINHAS_POR_PAGINA} OFFSET {(pagina - 1) * LINHAS_POR_PAGINA}"
        return texto

    def arquivo(self, pagina: int) -> str:
        return f"{self.nome}-{pagina}.json"


def _rotulos(raiz: str, generos: dict) -> str:
    classes = " ".join("wd:" + q for q in generos)
    return (f"?item wdt:P31/wdt:P279* wd:{raiz} . ?item wdt:P1705 ?name . "
            f"OPTIONAL {{ VALUES ?gender {{ {classes} }} ?item wdt:P31/wdt:P279* ?gender }}")


_ITEM_DE_NOME = "VALUES ?root { wd:Q202444 wd:Q101352 } ?item wdt:P31/wdt:P279* ?root . "

PRENOMES = Consulta("given-names", ("item", "name", "gender"), _rotulos("Q202444", GENERO_PRENOME), 1)
SOBRENOMES = Consulta("family-names", ("item", "name", "gender"), _rotulos("Q101352", GENERO_SOBRENOME), 5)
# R4.3: propriedade -> (relação, páginas).
PROPRIEDADES = {
    "P460": ("said_to_be_the_same", 3),
    "P1533": ("family_name_identical", 1),
    "P1560": ("other_gender", 1),
    "P5278": ("other_gender", 1),
    "P1889": ("different_from", 2),
}
LIGACOES = {
    p: Consulta(f"links-{p}", ("item", "target"), f"{_ITEM_DE_NOME}?item wdt:{p} ?target .", paginas)
    for p, (_, paginas) in PROPRIEDADES.items()
}
TRANSLITERACOES = Consulta(
    "transliterations", ("item", "transliteration"),
    f"{_ITEM_DE_NOME}{{ ?item wdt:P2440 ?transliteration }} UNION {{ ?item p:P1705/pq:P2440 ?transliteration }}",
    1,
)
CONSULTAS = (PRENOMES, SOBRENOMES, *LIGACOES.values(), TRANSLITERACOES)


def url(consulta: Consulta, pagina: int) -> str:
    return f"{ENDPOINT}?{urlencode({'query': consulta.sparql(pagina), 'action': 'sparql_json'})}"


RESOURCES = [
    Resource(url(c, k), c.arquivo(k)) for c in CONSULTAS for k in range(1, c.paginas + 1)
]


def linhas(files: dict[str, Path], consulta: Consulta) -> Iterator[dict]:
    """Linhas de todas as páginas da consulta, uma página por vez (R2.3)."""
    incompleta = None
    for k in range(1, consulta.paginas + 1):
        nome = consulta.arquivo(k)
        try:
            dados = json.loads(Path(files[nome]).read_text(encoding="utf-8"))
            variaveis, pagina = dados["head"]["vars"], dados["results"]["bindings"]
        except (ValueError, KeyError, TypeError) as e:
            raise FormatError(f"{nome}: não é um resultado SPARQL JSON ({type(e).__name__}: {e})") from None
        if variaveis != list(consulta.variaveis):
            raise FormatError(f"{nome}: variáveis {variaveis}, esperava {list(consulta.variaveis)}")
        if not isinstance(pagina, list) or len(pagina) > LINHAS_POR_PAGINA:
            raise FormatError(f"{nome}: esperava uma lista de no máximo {LINHAS_POR_PAGINA} linhas")
        if pagina and incompleta is not None:
            raise FormatError(
                f"{nome}: página com linhas depois da página incompleta {incompleta}; o índice mudou "
                f"entre os downloads, baixe de novo com fetch --refresh {SOURCE_ID}"
            )
        if len(pagina) == LINHAS_POR_PAGINA and k == consulta.paginas:
            raise FormatError(
                f"{nome}: última página cheia ({LINHAS_POR_PAGINA} linhas); aumente as páginas de "
                f"'{consulta.nome}' em {__name__}"
            )
        if len(pagina) < LINHAS_POR_PAGINA and incompleta is None:
            incompleta = nome
        del dados
        yield from pagina


def _entidade(termo: object) -> str | None:
    """QID de um termo URI de entidade; None para outro termo (valor desconhecido, genid)."""
    if isinstance(termo, dict) and termo.get("type") == "uri":
        m = _ENTIDADE.fullmatch(termo.get("value", ""))
        if m:
            return m.group(1)
    return None


def _item(linha: dict, consulta: Consulta) -> str:
    qid = _entidade(linha.get("item"))
    if qid is None:
        raise FormatError(f"{consulta.nome}: item {linha.get('item')!r} não é entidade do Wikidata")
    return qid


def _literal(termo: object, campo: str, consulta: Consulta) -> str | None:
    """Texto de um literal; None para valor desconhecido (URI ou nó em branco)."""
    if not isinstance(termo, dict):
        raise FormatError(f"{consulta.nome}: {campo} ausente")
    if termo.get("type") == "literal" and isinstance(termo.get("value"), str):
        return termo["value"]
    if termo.get("type") in ("uri", "bnode"):
        return None
    raise FormatError(f"{consulta.nome}: {campo} {termo!r} não é literal")


def nome_aceito(texto: str) -> bool:
    """R3.2: sem algarismo de nenhuma escrita e sem os caracteres de _PROIBIDOS."""
    return bool(texto.strip()) and not any(
        c in _PROIBIDOS or unicodedata.category(c).startswith("N") for c in texto
    )


def rotulos(files: dict[str, Path]) -> Iterator[tuple[str, str, str, tuple[str | None, ...]]]:
    """(qid, kind, nome, gêneros) de cada rótulo nativo aceito (R3.1 a R3.4)."""
    for kind, consulta, generos in (("given", PRENOMES, GENERO_PRENOME), ("family", SOBRENOMES, GENERO_SOBRENOME)):
        for linha in linhas(files, consulta):
            qid = _item(linha, consulta)
            nome = _literal(linha.get("name"), "name", consulta)
            if nome is None or not nome_aceito(nome):
                continue
            classe = linha.get("gender")
            if classe is None:
                yield qid, kind, nome, (None,)
                continue
            codigo = _entidade(classe)
            if codigo not in generos:
                raise FormatError(
                    f"{consulta.nome}: classe de gênero {classe.get('value') if isinstance(classe, dict) else classe!r} "
                    f"desconhecida; esperado uma de {sorted(generos)}"
                )
            yield qid, kind, nome, generos[codigo]


def _chave(nome: str, kind: str) -> tuple[str, str]:
    return name_key(normalize_name(nome, False)), kind


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    """Um registro por gênero informado de cada (name_key, kind); sem gênero só se nenhum item informa (R3.5)."""
    grupos: dict[tuple[str, str], tuple[str, set]] = {}
    for _, kind, nome, generos in rotulos(files):
        grupo = grupos.setdefault(_chave(nome, kind), (nome, set()))
        grupo[1].update(generos)
    for (_, kind), (nome, generos) in grupos.items():
        for genero in sorted(g for g in generos if g) or [None]:
            yield RawRecord(name=nome, kind=kind, gender=genero)


def _alvo(linha: dict, consulta: Consulta) -> str | None:
    """QID do alvo; None para valor desconhecido (genid); termo que não é URI é FormatError (R2.4)."""
    termo = linha.get("target")
    if not isinstance(termo, dict) or termo.get("type") not in ("uri", "bnode"):
        raise FormatError(f"{consulta.nome}: target {termo!r} não é URI")
    return _entidade(termo)


def links(files: dict[str, Path]) -> Iterator[RawLink]:
    """Ligações entre rótulos aceitos (R4.3); o pipeline descarta auto-ligações e repetidas."""
    por_item: dict[str, dict[tuple[str, str], str]] = {}
    for qid, kind, nome, _ in rotulos(files):
        por_item.setdefault(qid, {}).setdefault(_chave(nome, kind), nome)
    for qid, nomes in por_item.items():
        for ((_, ka), a), ((_, kb), b) in combinations(nomes.items(), 2):
            if ka == kb:
                yield RawLink("same_item", qid, a, ka, qid, b, kb)
    for propriedade, (relacao, _) in PROPRIEDADES.items():
        consulta = LIGACOES[propriedade]
        for linha in linhas(files, consulta):
            origem, destino = _item(linha, consulta), _alvo(linha, consulta)
            alvos = por_item.get(destino, {}) if destino else {}
            for (_, ka), a in por_item.get(origem, {}).items():
                for (_, kb), b in alvos.items():
                    yield RawLink(relacao, origem, a, ka, destino, b, kb)
    for linha in linhas(files, TRANSLITERACOES):
        origem = _item(linha, TRANSLITERACOES)
        texto = _literal(linha.get("transliteration"), "transliteration", TRANSLITERACOES)
        if texto is None or not nome_aceito(texto):
            continue
        for (_, kind), nome in por_item.get(origem, {}).items():
            yield RawLink("transliteration", origem, nome, kind, origem, texto, kind)
