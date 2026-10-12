"""Spec 002, R3: validate confere a observação contra a fonte registrada e a faixa de year."""

from dataclasses import replace
from datetime import date

import pytest

from namescommons.schema import ValidationError, make_observation, validate


def _ssa(**campos):
    base = dict(kind="given", source_id="us-ssa", count_type="births", country="US",
                gender="F", year=2020, count=10)
    return make_observation("Maria", **{**base, **campos})


def test_count_type_diferente_do_da_fonte(fontes):
    o = _ssa(count_type="population")
    with pytest.raises(ValidationError, match="count_type 'population' diverge da fonte 'us-ssa' \\('births'\\)"):
        validate([o], fontes)


def test_country_diferente_do_da_fonte(fontes):
    with pytest.raises(ValidationError, match="país 'BR' diverge da fonte 'us-ssa' \\('US'\\)"):
        validate([_ssa(country="BR")], fontes)


def test_country_vazio_em_fonte_nacional(fontes):
    with pytest.raises(ValidationError, match="país None diverge da fonte 'us-ssa'"):
        validate([_ssa(country=None)], fontes)


def test_fonte_sem_pais_aceita_qualquer_pais(fontes):
    o = make_observation("Maria", kind="given", source_id="wikidata", count_type="attested", country="PT")
    validate([o], fontes)


@pytest.mark.parametrize("ano", [1799, date.today().year + 2])
def test_year_fora_da_faixa(fontes, ano):
    with pytest.raises(ValidationError, match="year .* fora de 1800 a"):
        validate([_ssa(year=ano)], fontes)


@pytest.mark.parametrize("ano", [1800, date.today().year + 1, None])
def test_year_dentro_da_faixa(fontes, ano):
    validate([_ssa(year=ano)], fontes)


def test_pais_invalido_nao_gera_erro_duplicado(observacoes, fontes):
    with pytest.raises(ValidationError) as e:
        validate([replace(observacoes[0], country="XX")], fontes)
    assert len(e.value.erros) == 1
