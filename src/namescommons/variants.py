"""Agrupamento de variantes (spec 005, R5; ADRs 0010 e 0011): group_id de cada nome do índice.

Os nós são as chaves (name_key) de um kind com observação, numeradas pela posição na lista
ordenada. As junções são feitas em duas fases sobre inteiros, e `different_from` proíbe que dois
nós fiquem no mesmo grupo.
"""

from collections import defaultdict
from collections.abc import Iterable

from namescommons.links import VariantLink

# R5.3: relações da fase 1 por kind.
FASE_1 = {"given": frozenset({"same_item"}), "family": frozenset({"same_item", "other_gender"})}


class _Grupos:
    """União e busca com proibições entre nós (R5.6)."""

    def __init__(self, n: int):
        self.pai = list(range(n))
        self.proibidos: dict[int, set[int]] = {}  # raiz -> nós proibidos para o grupo

    def raiz(self, x: int) -> int:
        pai = self.pai
        while pai[x] != x:
            pai[x] = pai[pai[x]]
            x = pai[x]
        return x

    def proibir(self, a: int, b: int) -> None:
        self.proibidos.setdefault(a, set()).add(b)
        self.proibidos.setdefault(b, set()).add(a)

    def juntar(self, a: int, b: int) -> bool:
        """Junta os grupos de a e b; False se já estavam juntos ou se a junção é proibida."""
        ra, rb = self.raiz(a), self.raiz(b)
        if ra == rb:
            return False
        pa, pb = self.proibidos.get(ra, ()), self.proibidos.get(rb, ())
        # As proibições são simétricas: basta olhar o lado menor.
        menor, outra = (pa, rb) if len(pa) <= len(pb) else (pb, ra)
        if any(self.raiz(x) == outra for x in menor):
            return False
        filho, mae = (ra, rb) if len(pa) <= len(pb) else (rb, ra)
        self.pai[filho] = mae
        resto = self.proibidos.pop(filho, None)
        if resto:
            self.proibidos.setdefault(mae, set()).update(resto)
        return True


def _par(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def group_ids(
    keys: list[str],
    ascii: list[str],
    unaccented: list[bool],
    links: Iterable[VariantLink] | None,
    kind: str,
) -> list[str]:
    """group_id de cada chave (R5): o menor name_key do grupo.

    keys: chaves de um kind, ordenadas e sem repetição. ascii: forma ASCII das chaves latinas e
    "" nas demais. unaccented: a chave é atestada por fonte com strips_accents (ADR 0011).
    """
    posicao = {k: i for i, k in enumerate(keys)}
    fase_1 = FASE_1[kind]
    juncoes_1: set[tuple[int, int]] = set()
    proibicoes: set[tuple[int, int]] = set()
    origens: dict[int, set[int]] = defaultdict(set)  # destino de transliteração -> origens
    for v in links or ():
        # R5.1 e R5.2: só o kind pedido, nas duas pontas, e só nós com observação.
        if v.kind != kind or v.target_kind != kind:
            continue
        a, b = posicao.get(v.name_key), posicao.get(v.target_name_key)
        if a is None or b is None or a == b:
            continue
        if v.relation in fase_1:
            juncoes_1.add(_par(a, b))
        elif v.relation == "different_from":
            proibicoes.add(_par(a, b))
        elif v.relation == "transliteration":
            origens[b].add(a)

    grupos = _Grupos(len(keys))
    for a, b in proibicoes:
        grupos.proibir(a, b)
    for a, b in sorted(juncoes_1):
        grupos.juntar(a, b)

    # R5.4: anexações calculadas sobre os grupos da fase 1, aplicadas depois em ordem fixa.
    juncoes_2: set[tuple[int, int]] = set()
    for destino, fontes in origens.items():
        if len({grupos.raiz(x) for x in fontes}) == 1:
            juncoes_2.add(_par(destino, min(fontes)))
    sem_acento = {ascii[i] for i, marca in enumerate(unaccented) if marca and ascii[i]}
    if sem_acento:
        por_ascii: dict[str, list[int]] = defaultdict(list)
        for i, forma in enumerate(ascii):
            if forma in sem_acento:
                por_ascii[forma].append(i)
        for i, marca in enumerate(unaccented):
            if not (marca and ascii[i]):
                continue
            candidatos = [j for j in por_ascii[ascii[i]] if j != i]
            if candidatos and len({grupos.raiz(j) for j in candidatos}) == 1:
                juncoes_2.add(_par(i, min(candidatos)))
    for a, b in sorted(juncoes_2):
        grupos.juntar(a, b)

    # R5.7: a menor chave do grupo é a primeira na lista ordenada.
    menor: dict[int, int] = {}
    ids = []
    for i in range(len(keys)):
        r = grupos.raiz(i)
        primeira = menor.setdefault(r, i)
        ids.append(keys[primeira])
    return ids
