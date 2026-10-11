from dataclasses import replace

import pytest

from namesio.schema import ValidationError, make_observation, validate


def test_make_observation_deriva_campos():
    o = make_observation("ÁLVARO", kind="given", source_id="us-ssa", count_type="births",
                         country="US", gender="M", year=2021, count=12)
    assert (o.name, o.name_key, o.ascii, o.script) == ("Álvaro", "álvaro", "alvaro", "Latn")


def test_fixture_valida(observacoes, fontes):
    validate(observacoes, fontes)


@pytest.mark.parametrize("campos, trecho", [
    ({"name": ""}, "'name' vazio"),
    ({"kind": "middle"}, "kind"),
    ({"country": "XX"}, "ISO 3166-1"),
    ({"gender": "X"}, "gender"),
    ({"count": -1}, "negativo"),
    ({"count": None}, "R1.1"),
    ({"count_type": "attested"}, "R1.1"),
    ({"count_type": "deaths"}, "count_type"),
    ({"source_id": "inexistente"}, "sources.yaml"),
    ({"ascii": ""}, "ascii"),
])
def test_observacao_invalida(observacoes, fontes, campos, trecho):
    ruim = replace(observacoes[0], **campos)
    with pytest.raises(ValidationError, match=trecho):
        validate([ruim], fontes)


def test_nome_so_com_espacos_e_recusado(fontes):
    o = make_observation("   ", kind="given", source_id="wikidata", count_type="attested")
    with pytest.raises(ValidationError, match="'name' vazio"):
        validate([o], fontes)


def test_duplicata_pela_chave(observacoes, fontes):
    with pytest.raises(ValidationError, match="duplicata"):
        validate([observacoes[0], replace(observacoes[0], count=1)], fontes)


def test_mesma_chave_em_kind_diferente_nao_e_duplicata(fontes):
    a = make_observation("Thomas", kind="given", source_id="wikidata", count_type="attested")
    b = make_observation("Thomas", kind="family", source_id="wikidata", count_type="attested")
    validate([a, b], fontes)


def test_lista_todos_os_erros(observacoes, fontes):
    ruim = replace(observacoes[0], gender="X", country="XX")
    with pytest.raises(ValidationError) as e:
        validate([ruim], fontes)
    assert len(e.value.erros) == 2


@pytest.mark.parametrize("campos, trecho", [
    ({"name_key": "zzz"}, "name_key"),
    ({"script": "Cyrl"}, "script"),
    ({"name": "Ana  Clara"}, "NFC"),
    ({"name": "José"}, "NFC"),
])
def test_campos_derivados_contradizem_r1(fontes, campos, trecho):
    ok = make_observation("Ana Clara", kind="given", source_id="wikidata", count_type="attested")
    with pytest.raises(ValidationError, match=trecho):
        validate([replace(ok, **campos)], fontes)
