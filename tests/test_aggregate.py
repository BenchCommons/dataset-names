"""Critério de aceite 3: valores esperados calculados à mão a partir de tests/conftest.py."""

from dataclasses import replace
from datetime import date

import pytest

from namescommons.aggregate import AggregationError, CountryEntry, by_country, display_name, name_index
from namescommons.schema import make_observation
from namescommons.sources import parse_sources


def _linha(rows, kind, chave):
    return next(r for r in rows if r.kind == kind and r.name_key == chave)


def test_paises_presentes(observacoes, fontes):
    assert list(by_country(observacoes, fontes)) == ["BR", "US"]


def test_us_births_soma_anos_so_da_fonte_primary(observacoes, fontes):
    us = by_country(observacoes, fontes)["US"]
    maria = _linha(us, "given", "maria")
    assert (maria.count, maria.count_type, maria.first_year, maria.last_year) == (155, "births", 2020, 2021)
    assert maria.female_share == pytest.approx(150 / 155)
    assert maria.gender_basis == 155


def test_us_rank_denso_decrescente(observacoes, fontes):
    us = by_country(observacoes, fontes)["US"]
    assert [(r.name_key, r.rank) for r in us] == [
        ("james", 1), ("maria", 2), ("deshawn", 3), ("ana clara", None),
    ]


def test_nome_so_na_fonte_secundaria_fica_sem_contagem(observacoes, fontes):
    ana = _linha(by_country(observacoes, fontes)["US"], "given", "ana clara")
    assert (ana.count, ana.count_type, ana.rank, ana.female_share, ana.gender_basis) == (
        None, "attested", None, None, 0,
    )


def test_forma_de_exibicao_usa_todas_as_fontes(observacoes, fontes):
    deshawn = _linha(by_country(observacoes, fontes)["US"], "given", "deshawn")
    assert deshawn.name == "DeShawn"  # 40 (us-births-b) > 30 (us-ssa)
    assert deshawn.count == 30  # mas a contagem vem só da primary


def test_br_population_usa_a_edicao_mais_recente(observacoes, fontes):
    br = by_country(observacoes, fontes)["BR"]
    maria = _linha(br, "given", "maria")
    assert (maria.name, maria.count, maria.first_year, maria.last_year) == ("Maria", 12000, 2022, 2022)
    assert (maria.female_share, maria.gender_basis) == (1.0, 12000)


def test_br_nome_com_espaco_e_sobrenome(observacoes, fontes):
    br = by_country(observacoes, fontes)["BR"]
    ana = _linha(br, "given", "ana clara")
    silva = _linha(br, "family", "silva")
    assert (ana.name, ana.count, ana.rank) == ("Ana Clara", 800, 2)
    assert (silva.name, silva.count, silva.rank, silva.female_share) == ("Silva", 5000, 1, None)


def test_population_tem_precedencia_sobre_births_no_mesmo_pais():
    fontes = parse_sources([
        {"id": "pop", "name": "p", "url": "https://p", "license": "CC0-1.0", "attribution": "p",
         "country": "FR", "count_type": "population", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
        {"id": "nas", "name": "n", "url": "https://n", "license": "CC0-1.0", "attribution": "n",
         "country": "FR", "count_type": "births", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
    ])
    obs = [
        make_observation("Léa", kind="given", source_id="pop", count_type="population",
                         country="FR", gender="F", year=2020, count=90000),
        make_observation("Léa", kind="given", source_id="nas", count_type="births",
                         country="FR", gender="F", year=2020, count=4000),
    ]
    lea = by_country(obs, fontes)["FR"][0]
    assert (lea.count, lea.count_type) == (90000, "population")


def test_rank_separado_por_count_type():
    fontes = parse_sources([
        {"id": "pop", "name": "p", "url": "https://p", "license": "CC0-1.0", "attribution": "p",
         "country": "FR", "count_type": "population", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
        {"id": "nas", "name": "n", "url": "https://n", "license": "CC0-1.0", "attribution": "n",
         "country": "FR", "count_type": "births", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
    ])
    obs = [
        make_observation("Léa", kind="given", source_id="pop", count_type="population",
                         country="FR", year=2020, count=90000),
        make_observation("Jade", kind="given", source_id="nas", count_type="births",
                         country="FR", year=2020, count=4000),
    ]
    assert {(r.name, r.count_type, r.rank) for r in by_country(obs, fontes)["FR"]} == {
        ("Léa", "population", 1), ("Jade", "births", 1),
    }


def test_indice_given(observacoes, fontes):
    indice = name_index(observacoes, by_country(observacoes, fontes), "given")
    assert [r.name_key for r in indice] == ["ana clara", "deshawn", "james", "maria", "мария"]
    maria = indice[3]
    assert maria.country_count == 2
    assert maria.countries == (
        CountryEntry("BR", 12000, "population", 1),
        CountryEntry("US", 155, "births", 2),
    )
    assert maria.female_share == pytest.approx(12150 / 12155)
    assert maria.gender_basis == 12155
    assert maria.sources == ("br-ibge-censo", "us-births-b", "us-ssa", "wikidata")
    assert maria.group_id is None


def test_indice_nome_so_atestado(observacoes, fontes):
    maria_cirilico = name_index(observacoes, by_country(observacoes, fontes), "given")[4]
    assert (maria_cirilico.name, maria_cirilico.script, maria_cirilico.ascii) == ("Мария", "Cyrl", "")
    assert (maria_cirilico.country_count, maria_cirilico.countries) == (0, ())
    assert (maria_cirilico.female_share, maria_cirilico.gender_basis) == (None, 0)


def test_indice_family(observacoes, fontes):
    indice = name_index(observacoes, by_country(observacoes, fontes), "family")
    assert [(r.name, r.script, r.country_count) for r in indice] == [("Silva", "Latn", 1), ("李", "Hani", 0)]


def test_empate_na_forma_de_exibicao_vai_para_ordem_lexicografica():
    a = make_observation("Mcdonald", kind="family", source_id="x", count_type="attested")
    b = make_observation("McDonald", kind="family", source_id="y", count_type="attested")
    assert display_name([a, b]) == "McDonald"


def test_fontes_ambiguas_sem_primary():
    fontes = parse_sources([
        {"id": "a", "name": "a", "url": "https://a", "license": "CC0-1.0", "attribution": "a",
         "country": "FR", "count_type": "births", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
        {"id": "b", "name": "b", "url": "https://b", "license": "CC0-1.0", "attribution": "b",
         "country": None, "count_type": "births", "primary": False, "suppression": None,
         "retrieved": date(2026, 1, 1)},
    ])
    obs = [
        make_observation("Léa", kind="given", source_id="b", count_type="births",
                         country="FR", year=2020, count=1),
        make_observation("Jade", kind="given", source_id="b", count_type="births",
                         country="FR", year=2020, count=1),
    ]
    obs.append(make_observation("Léa", kind="given", source_id="a", count_type="births",
                                country="FR", year=2020, count=2))
    fr = by_country(obs, fontes)["FR"]
    assert {(r.name, r.count) for r in fr} == {("Léa", 2), ("Jade", None)}
    fontes_sem_primary = dict(fontes)
    fontes_sem_primary["a"] = replace(fontes["a"], primary=False)
    with pytest.raises(AggregationError, match="primary"):
        by_country(obs, fontes_sem_primary)


def test_population_nome_so_em_edicao_antiga_nao_e_contado(observacoes, fontes):
    antigo = make_observation("JOAO", kind="given", source_id="br-ibge-censo", gender="M",
                              year=2010, count=9000, country="BR", count_type="population")
    br = by_country(observacoes + [antigo], fontes)["BR"]
    joao = _linha(br, "given", "joao")
    assert (joao.count, joao.count_type, joao.rank, joao.first_year, joao.last_year) == (
        None, "attested", None, None, None,
    )
    maria = _linha(br, "given", "maria")
    assert (maria.count, maria.rank) == (12000, 1)
