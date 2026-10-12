"""Spec 002, R1 e R7: contrato do adaptador e parse do adaptador de exemplo sobre a fixture."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from namescommons.adapters import AdapterError, RawRecord, Resource, check_adapter, load_adapter, module_name

FIXTURES = Path(__file__).parent / "fixtures"


def _parse(files):
    return iter(())


def _adaptador(**campos):
    base = dict(SOURCE_ID="x", RESOURCES=[Resource("https://example.org/a.csv", "a.csv")], parse=_parse)
    return SimpleNamespace(**{**base, **campos})


def test_nome_do_modulo():
    assert module_name("us-ssa-births") == "us_ssa_births"


def test_carrega_o_adaptador_de_exemplo():
    mod = load_adapter("exemplo", "adaptadores")
    assert mod.SOURCE_ID == "exemplo"
    assert [r.filename for r in mod.RESOURCES] == ["primeiros.csv", "sobrenomes.csv"]


def test_parse_da_fixture_sem_rede():
    mod = load_adapter("exemplo", "adaptadores")
    pasta = FIXTURES / "exemplo"
    registros = list(mod.parse({r.filename: pasta / r.filename for r in mod.RESOURCES}))
    assert registros == [
        RawRecord("MARIA", "given", "PT", "F", 2020, 100),
        RawRecord("MARIA", "given", "PT", "F", 2020, 20),
        RawRecord("MARIA", "given", "PT", "F", 2021, 80),
        RawRecord("JOÃO", "given", "PT", "M", 2020, 90),
        RawRecord("JOÃO", "given", "PT", "M", 2021, 110),
        RawRecord("ANA CLARA", "given", "PT", "F", 2021, 15),
        RawRecord("JOSÉ", "given", "PT", "M", 2021, 15),
        RawRecord("SILVA", "family", "PT", "", 2020, 500),
        RawRecord("SANTOS", "family", "PT", " ", 2020, 300),
    ]


def test_adaptador_inexistente():
    with pytest.raises(AdapterError, match="adaptadores.nao_existe"):
        load_adapter("nao-existe", "adaptadores")


def test_pacote_padrao_ainda_nao_tem_adaptadores():
    with pytest.raises(AdapterError, match="namescommons.adapters.us_ssa"):
        load_adapter("us-ssa")


def test_adaptador_valido():
    check_adapter(_adaptador(), "x")


@pytest.mark.parametrize("campos, trecho", [
    ({"SOURCE_ID": "y"}, "SOURCE_ID 'y' diverge"),
    ({"RESOURCES": []}, "RESOURCES"),
    ({"RESOURCES": [("https://example.org/a.csv", "a.csv")]}, "RESOURCES"),
    ({"RESOURCES": [Resource("ftp://example.org/a.csv", "a.csv")]}, "http ou https"),
    ({"RESOURCES": [Resource("https://example.org/a.csv", "../a.csv")]}, "filename"),
    ({"RESOURCES": [Resource("https://example.org/a.csv", "a.csv.meta.json")]}, "filename"),
    ({"RESOURCES": [Resource("https://example.org/a.csv", "a.csv"),
                    Resource("https://example.org/b.csv", "a.csv")]}, "repetido"),
    ({"parse": None}, "parse"),
])
def test_adaptador_invalido(campos, trecho):
    with pytest.raises(AdapterError, match=trecho):
        check_adapter(_adaptador(**campos), "x")


def test_adaptador_sem_atributo():
    with pytest.raises(AdapterError, match="SOURCE_ID"):
        check_adapter(SimpleNamespace(RESOURCES=[], parse=_parse), "x")
