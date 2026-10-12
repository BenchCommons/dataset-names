"""Spec 005, R5 (ADR 0010 e 0011): agrupamento de variantes com ligações escritas à mão."""

import random

import pytest

from namescommons.links import VariantLink
from namescommons.normalize import ascii_form, detect_script, name_key
from namescommons.variants import group_ids


def _l(relacao, nome, alvo, kind="given", target_kind=None, qid="Q1", target_qid=None):
    if relacao in ("same_item", "transliteration"):
        target_qid = qid
    return VariantLink(
        source_id="wikidata", relation=relacao, qid=qid, name=nome, name_key=name_key(nome), kind=kind,
        target_qid=target_qid or "Q2", target_name=alvo, target_name_key=name_key(alvo),
        target_kind=target_kind or kind,
    )


def _grupos(nomes, ligacoes=(), sem_acento=(), kind="given"):
    """nome -> group_id; nomes do índice com ascii só para os latinos, como name_index monta."""
    chaves = sorted({name_key(n) for n in nomes})
    formas = {name_key(n): n for n in nomes}
    escritas = [detect_script(formas[k]) for k in chaves]
    ascii_ = [ascii_form(formas[k]) if e == "Latn" else "" for k, e in zip(chaves, escritas)]
    marcas = [formas[k] in sem_acento for k in chaves]
    ids = group_ids(chaves, ascii_, marcas, list(ligacoes), kind, escritas)
    return {formas[k]: g for k, g in zip(chaves, ids)}


def test_nome_sozinho_e_seu_grupo():
    assert _grupos(["Maria", "José"]) == {"Maria": "maria", "José": "josé"}


def test_same_item_junta_e_e_nao_dirigido():
    g = _grupos(["Марія", "Maria", "Mariia"], [_l("same_item", "Mariia", "Марія")])
    assert g["Марія"] == g["Mariia"] == "mariia"
    assert g["Maria"] == "maria"


def test_other_gender_so_em_sobrenomes():
    familia = _grupos(["Иванов", "Иванова"], [_l("other_gender", "Иванов", "Иванова", kind="family")], kind="family")
    assert familia["Иванов"] == familia["Иванова"]
    prenome = _grupos(["Paulo", "Paula"], [_l("other_gender", "Paulo", "Paula")])
    assert prenome["Paulo"] != prenome["Paula"]


def test_transliteracao_inequivoca_junta():
    nomes = ["Иванов", "Иванова", "Ivanov"]
    ligacoes = [
        _l("other_gender", "Иванов", "Иванова", kind="family", qid="Q1", target_qid="Q2"),
        _l("transliteration", "Иванов", "Ivanov", kind="family", qid="Q1"),
    ]
    g = _grupos(nomes, ligacoes, kind="family")
    assert g["Иванов"] == g["Иванова"] == g["Ivanov"] == "ivanov"


def test_romanizacao_ambigua_nao_junta():
    ligacoes = [
        _l("transliteration", "陈", "Chen", kind="family", qid="Q1"),
        _l("transliteration", "沈", "Chen", kind="family", qid="Q2"),
    ]
    g = _grupos(["陈", "沈", "Chen"], ligacoes, kind="family")
    assert len(set(g.values())) == 3


def test_romanizacao_de_rotulos_do_mesmo_grupo_junta():
    """Qualificador de um rótulo ligado a todos os rótulos do item (spec 004): o resultado não muda."""
    ligacoes = [
        _l("same_item", "陳", "陈", kind="family"),
        _l("transliteration", "陳", "Chen", kind="family"),
        _l("transliteration", "陈", "Chen", kind="family"),
    ]
    g = _grupos(["陳", "陈", "Chen"], ligacoes, kind="family")
    assert len(set(g.values())) == 1


def test_sem_acento_junta_marie_eve():
    g = _grupos(["Marie-Eve", "Marie-Ève", "Josee", "Josée"], sem_acento={"Marie-Eve", "Josee"})
    assert g["Marie-Eve"] == g["Marie-Ève"] == "marie-eve"
    assert g["Josee"] == g["Josée"] == "josee"


def test_sem_acento_ambiguo_nao_junta():
    g = _grupos(["Ines", "Inès", "Inés"], sem_acento={"Ines"})
    assert len(set(g.values())) == 3


def test_sem_acento_com_leituras_do_mesmo_grupo_junta():
    g = _grupos(["Ines", "Inès", "Inés"], [_l("same_item", "Inès", "Inés")], sem_acento={"Ines"})
    assert len(set(g.values())) == 1


def test_acentuados_nao_se_juntam_sem_fonte_sem_acento():
    g = _grupos(["Đức", "Đúc", "Duc"])
    assert len(set(g.values())) == 3


def test_sem_acento_nao_junta_outra_escrita():
    g = _grupos(["Ivan", "Иван"], sem_acento={"Ivan"})
    assert g["Ivan"] != g["Иван"]


def test_different_from_separa():
    """Q1 (Ivanov, Иванов) e Q2 (Ivanova) são o mesmo sobrenome, mas Иванов é different_from Ivanova."""
    ligacoes = [
        _l("same_item", "Ivanov", "Иванов", kind="family", qid="Q1"),
        _l("other_gender", "Ivanov", "Ivanova", kind="family", qid="Q1", target_qid="Q2"),
        _l("different_from", "Иванов", "Ivanova", kind="family", qid="Q1", target_qid="Q2"),
    ]
    g = _grupos(["Ivanov", "Иванов", "Ivanova"], ligacoes, kind="family")
    assert g["Иванов"] != g["Ivanova"]
    # Ordem fixa: ivanov e ivanova entram antes de иванов, que é pulado.
    assert g["Ivanov"] == g["Ivanova"] == "ivanov"
    assert g["Иванов"] == "иванов"


def test_different_from_separa_tambem_na_fase_2():
    ligacoes = [_l("different_from", "Marie-Ève", "Marie-Eve", qid="Q1", target_qid="Q2")]
    g = _grupos(["Marie-Eve", "Marie-Ève"], ligacoes, sem_acento={"Marie-Eve"})
    assert g["Marie-Eve"] != g["Marie-Ève"]


def test_tipos_diferentes_nunca_juntam():
    ligacoes = [_l("family_name_identical", "John", "John", kind="given", target_kind="family"),
                _l("said_to_be_the_same", "Jon", "John", kind="given", target_kind="family")]
    assert len(set(_grupos(["John", "Jon"], ligacoes).values())) == 2


def test_p460_nao_junta():
    g = _grupos(["John", "Johann"], [_l("said_to_be_the_same", "John", "Johann")])
    assert g["John"] != g["Johann"]


def test_ligacao_sem_observacao_e_ignorada():
    """Mariya só existe como transliteração: não liga Мария a Марія."""
    ligacoes = [_l("transliteration", "Мария", "Mariya", qid="Q1"),
                _l("transliteration", "Марія", "Mariya", qid="Q2")]
    g = _grupos(["Мария", "Марія"], ligacoes)
    assert g["Мария"] != g["Марія"]


def test_juncao_pela_chave_e_nao_pelo_texto():
    g = _grupos(["Mckenzie", "Маккензи"], [_l("same_item", "McKenzie", "Маккензи")])
    assert g["Mckenzie"] == g["Маккензи"]


def test_resultado_nao_depende_da_ordem():
    nomes = ["Ana", "Anna", "Anne", "Ann", "Annie", "Marie-Eve", "Marie-Ève", "Анна"]
    ligacoes = [
        _l("same_item", "Ana", "Anna", qid="Q1"),
        _l("same_item", "Anne", "Annie", qid="Q3"),
        _l("same_item", "Ann", "Annie", qid="Q3"),
        _l("different_from", "Ana", "Anne", qid="Q1", target_qid="Q3"),
        _l("different_from", "Ann", "Ana", qid="Q3", target_qid="Q1"),
        _l("same_item", "Marie-Ève", "Анна", qid="Q5"),
    ]
    # Transliteração e sem acento têm direção própria: entram embaralhadas, sem inverter.
    dirigidas = [_l("transliteration", "Анна", "Anna", qid="Q6")]
    esperado = _grupos(nomes, ligacoes + dirigidas, sem_acento={"Marie-Eve"})
    for semente in range(20):
        embaralhadas = ligacoes[:]
        random.Random(semente).shuffle(embaralhadas)
        invertidas = [
            _l(v.relation, v.target_name, v.name, qid=v.target_qid, target_qid=v.qid) for v in embaralhadas
        ]
        todas = embaralhadas + dirigidas
        random.Random(semente).shuffle(todas)
        assert _grupos(nomes, todas, sem_acento={"Marie-Eve"}) == esperado
        assert _grupos(nomes, invertidas + dirigidas, sem_acento={"Marie-Eve"}) == esperado


def test_group_id_e_a_menor_chave():
    ligacoes = [_l("same_item", "Zoë", "Zoe"), _l("same_item", "Zoe", "Ζωή")]
    assert set(_grupos(["Zoë", "Zoe", "Ζωή"], ligacoes).values()) == {"zoe"}


def test_sem_ligacoes():
    assert group_ids(["a", "b"], ["a", "b"], [False, False], None, "given") == ["a", "b"]


# Revisão do PR #38: rótulo homógrafo de itens diferentes não faz ponte.
def test_rotulo_de_dois_itens_nao_junta_os_itens():
    """장 é rótulo de 张 (Q1) e de 蒋 (Q2): fica sozinho, e 张 e 蒋 continuam separados."""
    ligacoes = [_l("same_item", "张", "장", kind="family", qid="Q1"),
                _l("same_item", "蒋", "장", kind="family", qid="Q2")]
    g = _grupos(["张", "蒋", "장"], ligacoes, kind="family")
    assert len(set(g.values())) == 3


def test_rotulo_de_dois_itens_do_mesmo_grupo_junta():
    """Herman de Q1 e de Q2, com Q1 e Q2 ligados por other_gender: os itens já são um grupo."""
    ligacoes = [_l("same_item", "Herman", "Hermanová", kind="family", qid="Q1"),
                _l("same_item", "Herman", "Хэрман", kind="family", qid="Q2"),
                _l("other_gender", "Herman", "Hermanová", kind="family", qid="Q2", target_qid="Q1")]
    g = _grupos(["Herman", "Hermanová", "Хэрман"], ligacoes, kind="family")
    assert len(set(g.values())) == 1


def test_transliteracao_para_rotulo_de_outro_nome_nao_junta():
    """見 tem a transliteração 현, que já é rótulo de 玄: 見 não entra no grupo de 玄."""
    ligacoes = [_l("same_item", "玄", "현", kind="family", qid="Q1"),
                _l("transliteration", "見", "현", kind="family", qid="Q2")]
    g = _grupos(["玄", "현", "見"], ligacoes, kind="family")
    assert g["玄"] == g["현"] != g["見"]


def test_transliteracao_para_grupo_de_outra_escrita_junta():
    """Герман -> Herman, e Herman já está com Hermanová (other_gender): junção legítima."""
    ligacoes = [_l("other_gender", "Hermanová", "Herman", kind="family", qid="Q2", target_qid="Q3"),
                _l("other_gender", "Herman", "Hermanová", kind="family", qid="Q3", target_qid="Q2"),
                _l("transliteration", "Герман", "Herman", kind="family", qid="Q1")]
    g = _grupos(["Herman", "Hermanová", "Герман"], ligacoes, kind="family")
    assert g["Herman"] == g["Hermanová"] == g["Герман"] == "herman"


def test_sem_acento_ja_em_outro_grupo_nao_junta():
    """Jose já está com Хосе (mesmo item); José está em outro grupo: concorrem, nada junta."""
    ligacoes = [_l("same_item", "Jose", "Хосе", qid="Q1"), _l("same_item", "José", "Josè", qid="Q2")]
    g = _grupos(["Jose", "Хосе", "José", "Josè"], ligacoes, sem_acento={"Jose"})
    assert g["Jose"] != g["José"]


def test_rotulo_ambiguo_nao_recebe_transliteracao():
    """현 é rótulo de 玄 (Q1) e de 見 (Q2); a transliteração 見 -> 현 não o tira dessa ambiguidade."""
    ligacoes = [_l("same_item", "玄", "현", kind="family", qid="Q1"),
                _l("same_item", "見", "현", kind="family", qid="Q2"),
                _l("transliteration", "見", "현", kind="family", qid="Q2")]
    g = _grupos(["玄", "見", "현"], ligacoes, kind="family")
    assert len(set(g.values())) == 3


def test_transliteracao_para_rotulo_de_outro_item_com_rotulo_ambiguo_nao_junta():
    """玄 é ambíguo (rótulo de Q1 e Q3), e 현 fica sozinho no grupo; ainda assim é rótulo de Q1, de escrita han."""
    ligacoes = [_l("same_item", "현", "玄", kind="family", qid="Q1"),
                _l("same_item", "玄", "Hyeon", kind="family", qid="Q3"),
                _l("transliteration", "見", "현", kind="family", qid="Q2")]
    g = _grupos(["玄", "見", "현", "Hyeon"], ligacoes, kind="family")
    assert g["見"] != g["현"]


# Segunda revisão do PR #38: homógrafos escondidos, leque e romanização de CJK.
def test_origem_de_transliteracao_em_dois_itens_e_homografa():
    """Герман é rótulo de Q1 (-> German) e de Q2 (-> Herman): German, Germán e Herman não se juntam."""
    ligacoes = [_l("transliteration", "Герман", "German", qid="Q1"),
                _l("transliteration", "Герман", "Herman", qid="Q2"),
                _l("same_item", "German", "Germán", qid="Q3")]
    g = _grupos(["Герман", "German", "Germán", "Herman"], ligacoes)
    assert g["German"] == g["Germán"]
    assert len({g["Герман"], g["German"], g["Herman"]}) == 3


def test_transliteracao_em_leque_nao_junta():
    """кінаш -> kinach e kinasz, sobrenomes poloneses de itens diferentes: nenhum se junta."""
    ligacoes = [_l("transliteration", "Кінаш", "Kinach", kind="family", qid="Q1"),
                _l("transliteration", "Кінаш", "Kinasz", kind="family", qid="Q1"),
                _l("same_item", "Kinach", "Kinachowa", kind="family", qid="Q2"),
                _l("same_item", "Kinasz", "Kinaszowa", kind="family", qid="Q3")]
    g = _grupos(["Кінаш", "Kinach", "Kinachowa", "Kinasz", "Kinaszowa"], ligacoes, kind="family")
    assert len({g["Кінаш"], g["Kinach"], g["Kinasz"]}) == 3


def test_cirilico_para_grupo_latino_de_outro_item_junta():
    """Омельчук -> Omelczuk, que já está com Omelczukowa: cirílico para latino continua juntando."""
    ligacoes = [_l("transliteration", "Омельчук", "Omelczuk", kind="family", qid="Q1"),
                _l("same_item", "Omelczuk", "Omelczukowa", kind="family", qid="Q2")]
    g = _grupos(["Омельчук", "Omelczuk", "Omelczukowa"], ligacoes, kind="family")
    assert len(set(g.values())) == 1


@pytest.mark.parametrize("origem, latinos", [
    ("术", ("Suk", "Suková")),
    ("黑", ("Hak", "Haková")),
    ("炳", ("Bing", "Bingová")),
    ("辉", ("Fai", "Faiová")),
    ("福", ("Fuk", "Fukowa")),
    ("郦", ("Lik", "Likowa")),
])
def test_romanizacao_de_han_nao_entra_em_sobrenome_latino_de_outro_item(origem, latinos):
    a, b = latinos
    ligacoes = [_l("transliteration", origem, a, kind="family", qid="Q1"),
                _l("other_gender", a, b, kind="family", qid="Q2", target_qid="Q3")]
    g = _grupos([origem, a, b], ligacoes, kind="family")
    assert g[a] == g[b] != g[origem]


def test_romanizacao_de_han_sem_outro_item_junta():
    ligacoes = [_l("same_item", "陳", "陈", kind="family", qid="Q1"),
                _l("transliteration", "陈", "Chen", kind="family", qid="Q1")]
    g = _grupos(["陳", "陈", "Chen"], ligacoes, kind="family")
    assert len(set(g.values())) == 1
