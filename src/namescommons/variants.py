"""Agrupamento de variantes (spec 005, R5; ADRs 0010 e 0011): group_id de cada nome do índice.

Os nós são as chaves (name_key) de um kind com observação, numeradas pela posição na lista
ordenada; os itens do Wikidata ganham posições depois delas. Na fase 1, os itens se juntam por
other_gender (sobrenomes) e cada nó entra no grupo dos seus itens só se todos eles já são um
grupo: um rótulo homógrafo de itens diferentes (장 de 张 e de 蒋) não faz ponte. `different_from`
proíbe que dois nós fiquem no mesmo grupo.
"""

from collections import defaultdict
from collections.abc import Iterable

from namescommons.links import VariantLink

# R5.4: escritas cuja romanização não se anexa a nome de outro item (leituras homófonas).
CJK = frozenset({"Hani", "Hira", "Kana", "Hrkt", "Hang", "Jpan", "Kore"})

# R5.3: relação entre itens que os junta na fase 1, por kind.
ITENS_JUNTADOS_POR = {"given": frozenset(), "family": frozenset({"other_gender"})}


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
    scripts: list[str] | None = None,
    stats: dict[str, int] | None = None,
) -> list[str]:
    """group_id de cada chave (R5): o menor name_key do grupo.

    keys: chaves de um kind, ordenadas e sem repetição. ascii: forma ASCII das chaves latinas e
    "" nas demais. unaccented: a chave é atestada por fonte com strips_accents (ADR 0011).
    scripts: escrita de cada chave (R5.4); sem ela, todas contam como da mesma escrita.
    stats: se dado, recebe contagens de cada regra (para a medição da spec, R5.8).
    """
    conta: dict[str, int] = stats if stats is not None else {}

    def contar(regra: str) -> None:
        conta[regra] = conta.get(regra, 0) + 1

    n = len(keys)
    posicao = {k: i for i, k in enumerate(keys)}
    item_pos: dict[str, int] = {}  # QID -> posição n + j
    itens_do_no: dict[int, set[int]] = defaultdict(set)
    juncoes_itens: set[tuple[int, int]] = set()
    proibicoes: set[tuple[int, int]] = set()
    origens: dict[int, set[int]] = defaultdict(set)  # destino de transliteração -> origens

    def item(qid: str) -> int:
        return item_pos.setdefault(qid, n + len(item_pos))

    for v in links or ():
        # R5.1 e R5.2: só o kind pedido, nas duas pontas, e só nós com observação.
        if v.kind != kind or v.target_kind != kind:
            continue
        a, b = posicao.get(v.name_key), posicao.get(v.target_name_key)
        if v.relation == "same_item" or v.relation in ITENS_JUNTADOS_POR[kind]:
            # Os rótulos que estas relações ligam são os nomes dos itens na fase 1.
            if a is not None:
                itens_do_no[a].add(item(v.qid))
            if b is not None:
                itens_do_no[b].add(item(v.target_qid))
        elif v.relation == "transliteration" and a is not None:
            # A origem de uma transliteração é rótulo do item: um rótulo de itens diferentes
            # (Герман de dois itens) é homógrafo, como em same_item.
            itens_do_no[a].add(item(v.qid))
        if v.relation in ITENS_JUNTADOS_POR[kind]:
            juncoes_itens.add(_par(item(v.qid), item(v.target_qid)))
        if a is None or b is None or a == b:
            continue
        if v.relation == "different_from":
            proibicoes.add(_par(a, b))
        elif v.relation == "transliteration":
            origens[b].add(a)

    grupos = _Grupos(n + len(item_pos))
    for a, b in proibicoes:
        grupos.proibir(a, b)
    # Fase 1 (R5.3): itens juntados entre si, depois cada nó no grupo único dos seus itens.
    for a, b in sorted(juncoes_itens):
        grupos.juntar(a, b)
    juncoes_1 = []
    ambiguos: set[int] = set()  # rótulos de itens de grupos diferentes: não fazem ponte em nenhuma fase
    for no in sorted(itens_do_no):
        raizes = {grupos.raiz(x) for x in itens_do_no[no]}
        if len(raizes) == 1:
            juncoes_1.append((no, min(itens_do_no[no])))
        else:
            ambiguos.add(no)
            contar("rotulo_ambiguo")
    for no, it in juncoes_1:
        if not grupos.juntar(no, it) and grupos.raiz(no) != grupos.raiz(it):
            contar("pulada_por_different_from")

    # Para as concorrências da fase 2: tamanho de cada grupo da fase 1 em nós e as escritas dos
    # nomes de cada grupo e de cada item (inclusive rótulos ambíguos, que não entraram no grupo).
    def escrita(i: int) -> str:
        return scripts[i] if scripts else ""

    tamanho: dict[int, int] = defaultdict(int)
    escritas_do_grupo: dict[int, set[str]] = defaultdict(set)
    for i in range(n):
        r = grupos.raiz(i)
        tamanho[r] += 1
        escritas_do_grupo[r].add(escrita(i))
    escritas_do_item: dict[int, set[str]] = defaultdict(set)
    for no, itens in itens_do_no.items():
        for x in itens:
            escritas_do_item[grupos.raiz(x)].add(escrita(no))

    # R5.4: anexações calculadas sobre os grupos da fase 1, aplicadas depois em ordem fixa.
    juncoes_2: set[tuple[int, int]] = set()
    candidatas: list[tuple[int, int, int, int | None]] = []  # (destino, origem, grupo da origem, grupo rival)
    for destino, fontes in sorted(origens.items()):
        raizes = {grupos.raiz(x) for x in fontes}
        if len(raizes) != 1 or destino in ambiguos or fontes & ambiguos:
            contar("transliteracao_ambigua")
            continue
        (da_origem,) = raizes
        do_destino = grupos.raiz(destino)
        outro_grupo = do_destino != da_origem and tamanho[do_destino] > 1
        outros_itens = [grupos.raiz(x) for x in itens_do_no.get(destino, ()) if grupos.raiz(x) != da_origem]
        escritas_origem = {escrita(x) for x in fontes}
        # O destino concorre se já é nome de outro grupo ou rótulo de outro item que tem um nome
        # na escrita da origem (현, rótulo de 玄, não é romanização de 見; Herman, só latino, é de Герман).
        rivais: set[str] = set(escritas_do_grupo[do_destino]) if outro_grupo else set()
        for r in outros_itens:
            rivais |= escritas_do_item[r]
        if rivais & escritas_origem:
            contar("transliteracao_de_outro_nome")
            continue
        # Romanização de han, kana ou hangul é leitura homófona: não se anexa a nome de outro item
        # (suk/suková não são romanização de 术).
        if escritas_origem & CJK and (outro_grupo or outros_itens):
            contar("transliteracao_cjk_de_outro_item")
            continue
        candidatas.append((destino, min(fontes), da_origem, do_destino if outro_grupo else None))
    # Leque: as transliterações de um grupo que chegam a dois ou mais grupos de outros nomes
    # (кінаш -> kinach e kinasz) não se anexam a nenhum deles.
    rivais_por_origem: dict[int, set[int]] = defaultdict(set)
    for _, _, da_origem, rival in candidatas:
        if rival is not None:
            rivais_por_origem[da_origem].add(rival)
    for destino, origem, da_origem, rival in candidatas:
        if rival is not None and len(rivais_por_origem[da_origem]) > 1:
            contar("transliteracao_em_leque")
            continue
        contar("transliteracao")
        juncoes_2.add(_par(destino, origem))
    sem_acento = {ascii[i] for i, marca in enumerate(unaccented) if marca and ascii[i]}
    if sem_acento:
        por_ascii: dict[str, list[int]] = defaultdict(list)
        for i, forma in enumerate(ascii):
            if forma in sem_acento:
                por_ascii[forma].append(i)
        for i, marca in enumerate(unaccented):
            if not (marca and ascii[i]) or i in ambiguos:
                continue
            candidatos = [j for j in por_ascii[ascii[i]] if j != i]
            raizes = {grupos.raiz(j) for j in candidatos}
            proprio = grupos.raiz(i)
            # O próprio grupo, se já tem outros nomes e não é o dos candidatos, concorre.
            if not candidatos:
                continue
            if len(raizes) != 1 or (proprio not in raizes and tamanho[proprio] > 1):
                contar("sem_acento_ambiguo")
                continue
            contar("sem_acento")
            juncoes_2.add(_par(i, min(candidatos)))
    for a, b in sorted(juncoes_2):
        if not grupos.juntar(a, b) and grupos.raiz(a) != grupos.raiz(b):
            contar("pulada_por_different_from")

    # R5.7: a menor chave do grupo é a primeira na lista ordenada.
    menor: dict[int, int] = {}
    ids = []
    for i in range(n):
        r = grupos.raiz(i)
        primeira = menor.setdefault(r, i)
        ids.append(keys[primeira])
    return ids
