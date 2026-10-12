"""Spec 005, R5 (ADR 0010 e 0011): agrupamento de variantes com ligações escritas à mão."""

import random

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
    ascii_ = [ascii_form(formas[k]) if detect_script(formas[k]) == "Latn" else "" for k in chaves]
    marcas = [formas[k] in sem_acento for k in chaves]
    ids = group_ids(chaves, ascii_, marcas, list(ligacoes), kind)
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
    """A e B são different_from; C é rótulo do mesmo item que A e que B: só uma junção entra."""
    ligacoes = [
        _l("same_item", "Ana", "Anna", qid="Q1"),
        _l("same_item", "Anna", "Anne", qid="Q3"),
        _l("different_from", "Ana", "Anne", qid="Q1", target_qid="Q3"),
    ]
    g = _grupos(["Ana", "Anna", "Anne"], ligacoes)
    assert g["Ana"] != g["Anne"]
    # Ordem fixa: (ana, anna) entra antes de (anna, anne), que é pulada.
    assert g["Ana"] == g["Anna"] == "ana"
    assert g["Anne"] == "anne"


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
    nomes = ["Ana", "Anna", "Anne", "Ann", "Annie", "Marie-Eve", "Marie-Ève"]
    ligacoes = [
        _l("same_item", "Ana", "Anna", qid="Q1"),
        _l("same_item", "Anna", "Anne", qid="Q3"),
        _l("same_item", "Ann", "Annie", qid="Q4"),
        _l("same_item", "Annie", "Anne", qid="Q4"),
        _l("different_from", "Ana", "Anne", qid="Q1", target_qid="Q3"),
        _l("different_from", "Ann", "Ana", qid="Q4", target_qid="Q1"),
    ]
    esperado = _grupos(nomes, ligacoes, sem_acento={"Marie-Eve"})
    for semente in range(20):
        embaralhadas = ligacoes[:]
        random.Random(semente).shuffle(embaralhadas)
        invertidas = [
            _l(v.relation, v.target_name, v.name, qid=v.target_qid, target_qid=v.qid) for v in embaralhadas
        ]
        assert _grupos(nomes, embaralhadas, sem_acento={"Marie-Eve"}) == esperado
        assert _grupos(nomes, invertidas, sem_acento={"Marie-Eve"}) == esperado


def test_group_id_e_a_menor_chave():
    ligacoes = [_l("same_item", "Zoë", "Zoe"), _l("same_item", "Zoe", "Ζωή")]
    assert set(_grupos(["Zoë", "Zoe", "Ζωή"], ligacoes).values()) == {"zoe"}


def test_sem_ligacoes():
    assert group_ids(["a", "b"], ["a", "b"], [False, False], None, "given") == ["a", "b"]
