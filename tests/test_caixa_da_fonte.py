"""Spec 002, R1.3: a capitalização segue uniform_case da fonte, não a caixa de cada nome."""

import pytest

from namesio.normalize import normalize_name
from namesio.schema import derive_name_fields, make_observation


@pytest.mark.parametrize("bruto, esperado", [
    ("DJ", "DJ"),
    ("MARIA", "MARIA"),
    ("maria", "maria"),
    ("McDonald", "McDonald"),
    ("  ana   CLARA ", "ana CLARA"),
])
def test_fonte_de_caixa_mista_preserva_a_caixa_publicada(bruto, esperado):
    assert normalize_name(bruto, uniform_case=False) == esperado


@pytest.mark.parametrize("bruto, esperado", [
    ("DJ", "Dj"),
    ("MARIA", "Maria"),
    ("maria", "Maria"),
    ("McDonald", "Mcdonald"),
    ("JEAN-PIERRE", "Jean-Pierre"),
    ("O'NEILL", "O'Neill"),
    ("DA SILVA", "Da Silva"),
    ("李", "李"),
])
def test_fonte_de_caixa_uniforme_capitaliza_todos(bruto, esperado):
    assert normalize_name(bruto, uniform_case=True) == esperado


def test_sem_uniform_case_mantem_a_regra_da_001():
    assert normalize_name("MARIA") == "Maria"
    assert normalize_name("DJ") == "Dj"
    assert normalize_name("McDonald") == "McDonald"


def test_derive_name_fields():
    assert derive_name_fields("ÁLVARO", uniform_case=True) == ("Álvaro", "álvaro", "alvaro", "Latn")
    assert derive_name_fields("DJ", uniform_case=False) == ("DJ", "dj", "dj", "Latn")


def test_make_observation_aceita_uniform_case():
    o = make_observation("DJ", kind="given", source_id="x", count_type="attested", uniform_case=False)
    assert (o.name, o.name_key) == ("DJ", "dj")
