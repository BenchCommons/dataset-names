"""Spec 004, R4.1, R4.2, R4.4, R4.5 e R4.7: tabela variant_links no contrato e no pipeline."""

from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import pytest

from namescommons import pipeline
from namescommons.adapters import AdapterError, RawLink, Resource, check_adapter
from namescommons.io import read_links, write_links
from namescommons.links import RELATIONS, VariantLink, validate_links
from namescommons.pipeline import PipelineError, RecordError, ingest_links, to_links
from namescommons.schema import SCHEMA_VERSION, ValidationError
from namescommons.sources import parse_sources

FONTES = parse_sources([
    {"id": "wd", "name": "x", "url": "https://x.example", "license": "CC0-1.0", "attribution": "x",
     "country": None, "count_type": "attested", "primary": False, "suppression": None,
     "retrieved": date(2026, 1, 1)},
    {"id": "pt-x", "name": "x", "url": "https://x.example", "license": "CC0-1.0", "attribution": "x",
     "country": "PT", "count_type": "births", "primary": True, "suppression": None,
     "retrieved": date(2026, 1, 1)},
])


def _l(relation="said_to_be_the_same", qid="Q1", name="Maria", kind="given",
       target_qid="Q2", target_name="Мария", target_kind="given"):
    return RawLink(relation, qid, name, kind, target_qid, target_name, target_kind)


def test_relacoes():
    assert RELATIONS == ("same_item", "said_to_be_the_same", "family_name_identical",
                         "other_gender", "different_from", "transliteration")


def test_to_links_normaliza_e_deriva_name_key():
    [v] = to_links([_l(name="  Maria   Clara ", target_name="МАРИЯ")], FONTES["wd"])
    assert v == VariantLink(
        source_id="wd", relation="said_to_be_the_same", qid="Q1", name="Maria Clara",
        name_key="maria clara", kind="given", target_qid="Q2", target_name="МАРИЯ",
        target_name_key="мария", target_kind="given",
    )


def test_auto_ligacao_e_descartada():
    """R4.4: mesmo name_key e mesmo kind nos dois lados não informa nada para agrupar."""
    assert to_links([_l(relation="different_from", target_name="MARIA")], FONTES["wd"]) == []
    [v] = to_links([_l(relation="family_name_identical", target_name="Maria", target_kind="family")],
                   FONTES["wd"])
    assert (v.kind, v.target_kind) == ("given", "family")


def test_repetidas_uma_vez_e_ordem_estavel():
    a = _l(target_qid="Q3", target_name="Marie")
    b = _l(relation="other_gender", target_qid="Q4", target_name="Mario")
    c = _l(name="Ana", target_name="Anna")
    links = to_links([b, a, c, a, b], FONTES["wd"])
    assert [(v.qid, v.relation, v.target_name) for v in links] == [
        ("Q1", "other_gender", "Mario"),
        ("Q1", "said_to_be_the_same", "Anna"),
        ("Q1", "said_to_be_the_same", "Marie"),
    ]
    assert to_links([a, b, c], FONTES["wd"]) == links


@pytest.mark.parametrize("campos, trecho", [
    ({"relation": "x"}, "ligação 2: relation 'x' inválida"),
    ({"kind": "first"}, "ligação 2: kind 'first' inválido"),
    ({"target_kind": "nome"}, "ligação 2: target_kind 'nome' inválido"),
    ({"qid": "P31"}, "ligação 2: qid 'P31' fora do formato Q<n>"),
    ({"target_qid": "Q01"}, "ligação 2: target_qid 'Q01' fora do formato Q<n>"),
    ({"name": "   "}, "ligação 2: name vazio"),
    ({"target_name": 5}, "ligação 2: 'target_name' deve ser texto"),
    ({"relation": "same_item", "target_qid": "Q9"}, "ligação 2: same_item exige target_qid igual a qid"),
])
def test_ligacao_invalida_nomeia_a_posicao(campos, trecho):
    with pytest.raises(RecordError) as e:
        to_links([_l(), replace(_l(), **campos)], FONTES["wd"])
    assert str(e.value).startswith(trecho)


def _v(**campos):
    base = VariantLink("wd", "said_to_be_the_same", "Q1", "Maria", "maria", "given",
                       "Q2", "Мария", "мария", "given")
    return replace(base, **campos)


def test_validate_links_aceita_tabela_valida():
    validate_links([_v(), _v(target_qid="Q3")], FONTES)


@pytest.mark.parametrize("campos, trecho", [
    ({"relation": "x"}, "relation 'x' inválida"),
    ({"qid": "Q"}, "qid 'Q' fora do formato"),
    ({"target_qid": "L1"}, "target_qid 'L1' fora do formato"),
    ({"kind": "x"}, "kind 'x' inválido"),
    ({"target_kind": "x"}, "target_kind 'x' inválido"),
    ({"name": ""}, "'name' vazio"),
    ({"target_name": ""}, "'target_name' vazio"),
    ({"name_key": "Maria"}, "'name_key' 'Maria' diverge"),
    ({"target_name_key": "maria"}, "'target_name_key' 'maria' diverge"),
    ({"source_id": "nada"}, "source_id 'nada' ausente de sources.yaml"),
    ({"target_name": "MARIA", "target_name_key": "maria"}, "liga o nome a ele mesmo"),
    ({"relation": "transliteration", "target_qid": "Q9"}, "transliteration exige target_qid igual a qid"),
])
def test_validate_links_recusa(campos, trecho):
    with pytest.raises(ValidationError, match=trecho):
        validate_links([_v(**campos)], FONTES)


def test_validate_links_recusa_repetida():
    with pytest.raises(ValidationError, match="ligação 2 .*repetida"):
        validate_links([_v(), _v()], FONTES)


def test_ida_e_volta_em_parquet(tmp_path):
    links = [_v(), _v(relation="transliteration", target_qid="Q1", target_name="Mariya", target_name_key="mariya")]
    write_links(links, tmp_path / "sub" / "variant_links.parquet")
    assert read_links(tmp_path / "sub" / "variant_links.parquet") == links


def test_versao_do_esquema():
    assert SCHEMA_VERSION == "1.2.0"  # 1.1.0 na spec 004; 1.2.0 na spec 005, R8


def _modulo(**extra):
    return SimpleNamespace(SOURCE_ID="wd", RESOURCES=[Resource("https://x.example/a", "a.json")],
                           parse=lambda files: iter(()), **extra)


def test_check_adapter_recusa_links_que_nao_e_funcao():
    with pytest.raises(AdapterError, match="'wd': links deve ser uma função"):
        check_adapter(_modulo(links=[]), "wd")
    check_adapter(_modulo(links=lambda files: iter(())), "wd")


def test_ingest_links(tmp_path, monkeypatch):
    (tmp_path / "wd").mkdir()
    (tmp_path / "wd" / "a.json").write_text("{}", encoding="utf-8")
    vistos = []

    def links(files):
        vistos.append(sorted(files))
        yield _l()

    monkeypatch.setattr(pipeline, "load_adapter", lambda source_id, package: _modulo(links=links))
    assert ingest_links([FONTES["wd"]], FONTES, tmp_path, offline=True) == [_v()]
    assert vistos == [["a.json"]]
    monkeypatch.setattr(pipeline, "load_adapter", lambda source_id, package: _modulo())
    assert ingest_links([FONTES["wd"]], FONTES, tmp_path, offline=True) is None


def test_ingest_links_nomeia_a_fonte(tmp_path, monkeypatch):
    (tmp_path / "wd").mkdir()
    (tmp_path / "wd" / "a.json").write_text("{}", encoding="utf-8")
    modulo = _modulo(links=lambda files: iter([_l(relation="x")]))
    monkeypatch.setattr(pipeline, "load_adapter", lambda source_id, package: modulo)
    with pytest.raises(PipelineError, match="fonte 'wd': ligação 1: relation 'x' inválida"):
        ingest_links([FONTES["wd"]], FONTES, tmp_path, offline=True)
