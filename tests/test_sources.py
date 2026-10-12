"""Registro de fontes: campos de nomes, licenças do ADR 0001 e regra de primary (spec 001, R2; spec 007, R3.2).

Os campos e as regras genéricas do registro são testados no tools-dataset (spec 007, R2.6).
"""

from datetime import date

import pytest

from namescommons.sources import SourceError, load_sources, parse_sources


def fonte(**campos):
    base = {
        "id": "us-ssa-births", "name": "SSA Baby Names", "url": "https://www.ssa.gov/oact/babynames/",
        "license": "public-domain", "attribution": "U.S. Social Security Administration",
        "country": "US", "count_type": "births", "primary": True, "suppression": 5,
        "retrieved": date(2026, 10, 1),
    }
    return {**base, **campos}


def test_fonte_valida():
    fontes = parse_sources([fonte()])
    assert fontes["us-ssa-births"].suppression == 5


def test_carrega_yaml(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(
        "sources:\n"
        "  - id: wikidata\n"
        "    name: Wikidata\n"
        "    url: https://www.wikidata.org/\n"
        "    license: CC0-1.0\n"
        "    attribution: Wikidata\n"
        "    country: null\n"
        "    count_type: attested\n"
        "    primary: false\n"
        "    suppression: null\n"
        "    retrieved: 2026-10-01\n",
        encoding="utf-8",
    )
    assert load_sources(p)["wikidata"].retrieved == date(2026, 10, 1)


@pytest.mark.parametrize("licenca", ["CC-BY-SA-4.0", "ODbL-1.0", "CC-BY-NC-4.0", "desconhecida"])
def test_licenca_incompativel_e_recusada(licenca):
    with pytest.raises(SourceError, match="ADR 0001"):
        parse_sources([fonte(license=licenca)])


def test_statcan_open_licence_e_aceita_pelo_adr_0004():
    # ADR 0004 (0004-licenca-statistics-canada.md) amplia a lista do ADR 0001.
    fontes = parse_sources([fonte(license="statcan-open-licence")])
    assert fontes["us-ssa-births"].license == "statcan-open-licence"


@pytest.mark.parametrize("campos, trecho", [
    ({"country": "XX"}, "ISO 3166-1"),
    ({"country": "br"}, "ISO 3166-1"),
    ({"count_type": "deaths"}, "count_type"),
    ({"primary": "sim"}, "primary"),
    ({"suppression": 0}, "suppression"),
])
def test_campo_invalido(campos, trecho):
    with pytest.raises(SourceError, match=trecho):
        parse_sources([fonte(**campos)])


@pytest.mark.parametrize("campo", ["country", "count_type", "primary", "suppression"])
def test_campo_de_nomes_ausente(campo):
    entrada = fonte()
    del entrada[campo]
    with pytest.raises(SourceError, match=f"us-ssa-births: missing fields \\['{campo}'\\]"):
        parse_sources([entrada])


def test_duas_fontes_no_mesmo_par_exigem_uma_primary():
    with pytest.raises(SourceError, match="exatamente uma"):
        parse_sources([fonte(id="a"), fonte(id="b")])
    with pytest.raises(SourceError, match="exatamente uma"):
        parse_sources([fonte(id="a", primary=False), fonte(id="b", primary=False)])
    assert set(parse_sources([fonte(id="a"), fonte(id="b", primary=False)])) == {"a", "b"}


def test_todos_os_erros_sao_listados():
    with pytest.raises(SourceError) as e:
        parse_sources([fonte(license="ODbL-1.0", country="XX")])
    assert "ADR 0001" in str(e.value) and "ISO 3166-1" in str(e.value)


@pytest.mark.parametrize("campos, trecho", [
    ({"country": ["US"]}, "ISO 3166-1"),
    ({"count_type": ["births"]}, "count_type"),
])
def test_campo_nao_textual_vira_source_error(campos, trecho):
    with pytest.raises(SourceError, match=trecho):
        parse_sources([fonte(**campos)])


def test_attested_nao_exige_primary():
    """Spec 004, R5 (issue #3): em attested, primary não tem efeito e não é conferido."""
    sem_pais = [fonte(id=i, country=None, count_type="attested", primary=False) for i in ("a", "b")]
    assert set(parse_sources(sem_pais)) == {"a", "b"}
    mesmo_pais = [fonte(id=i, count_type="attested", primary=True) for i in ("a", "b")]
    assert set(parse_sources(mesmo_pais)) == {"a", "b"}


@pytest.mark.parametrize("tipo", ["births", "population"])
def test_contagem_continua_exigindo_uma_primary(tipo):
    with pytest.raises(SourceError, match=f"US/{tipo}: fontes \\['a', 'b'\\]; exatamente uma"):
        parse_sources([fonte(id=i, count_type=tipo, primary=False) for i in ("a", "b")])
