"""Fixture do critério de aceite 3: duas fontes births no mesmo país (uma primary),
uma population, uma attested; escritas latina, cirílica e chinesa; nome com espaço."""

from datetime import date

import pytest

from namesio.schema import make_observation
from namesio.sources import parse_sources

FONTES = [
    {"id": "us-ssa", "name": "SSA", "url": "https://www.ssa.gov/oact/babynames/",
     "license": "public-domain", "attribution": "SSA", "country": "US",
     "count_type": "births", "primary": True, "suppression": 5, "retrieved": date(2026, 10, 1)},
    {"id": "us-births-b", "name": "Outra fonte de nascimentos dos EUA", "url": "https://example.org/b",
     "license": "CC-BY-4.0", "attribution": "Exemplo", "country": "US",
     "count_type": "births", "primary": False, "suppression": None, "retrieved": date(2026, 10, 1)},
    {"id": "br-ibge-censo", "name": "IBGE Censo", "url": "https://censo2022.ibge.gov.br/nomes/",
     "license": "CC-BY-4.0", "attribution": "IBGE", "country": "BR",
     "count_type": "population", "primary": True, "suppression": None, "retrieved": date(2026, 10, 1)},
    {"id": "wikidata", "name": "Wikidata", "url": "https://www.wikidata.org/",
     "license": "CC0-1.0", "attribution": "Wikidata", "country": None,
     "count_type": "attested", "primary": False, "suppression": None, "retrieved": date(2026, 10, 1)},
]


def _obs():
    g, f = "given", "family"
    us = dict(country="US", count_type="births")
    br = dict(country="BR", count_type="population", source_id="br-ibge-censo")
    wd = dict(count_type="attested", source_id="wikidata")
    return [
        make_observation("Maria", kind=g, source_id="us-ssa", gender="F", year=2020, count=100, **us),
        make_observation("Maria", kind=g, source_id="us-ssa", gender="F", year=2021, count=50, **us),
        make_observation("Maria", kind=g, source_id="us-ssa", gender="M", year=2021, count=5, **us),
        make_observation("James", kind=g, source_id="us-ssa", gender="M", year=2021, count=200, **us),
        make_observation("Deshawn", kind=g, source_id="us-ssa", gender="M", year=2021, count=30, **us),
        make_observation("Maria", kind=g, source_id="us-births-b", gender="F", year=2021, count=999, **us),
        make_observation("DeShawn", kind=g, source_id="us-births-b", gender="M", year=2021, count=40, **us),
        make_observation("Ana Clara", kind=g, source_id="us-births-b", gender="F", year=2021, count=7, **us),
        make_observation("MARIA", kind=g, gender="F", year=2010, count=11000, **br),
        make_observation("MARIA", kind=g, gender="M", year=2010, count=300, **br),
        make_observation("MARIA", kind=g, gender="F", year=2022, count=12000, **br),
        make_observation("ANA CLARA", kind=g, gender="F", year=2022, count=800, **br),
        make_observation("SILVA", kind=f, year=2022, count=5000, **br),
        make_observation("Мария", kind=g, **wd),
        make_observation("Maria", kind=g, **wd),
        make_observation("李", kind=f, **wd),
    ]


@pytest.fixture
def fontes():
    return parse_sources(FONTES)


@pytest.fixture
def observacoes():
    return _obs()
