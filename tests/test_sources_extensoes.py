"""Spec 002, R2 e spec 005, R6: campos opcionais de nomes.

adapter, retrieved e url são campos genéricos, testados no tools-dataset (spec 007, R2.6).
"""

from datetime import date

import pytest

from namescommons.sources import SourceError, load_sources, parse_sources


def fonte(**campos):
    base = {
        "id": "pt-exemplo", "name": "Exemplo", "url": "https://example.org/nomes",
        "license": "CC-BY-4.0", "attribution": "Exemplo", "country": "PT",
        "count_type": "births", "primary": True, "suppression": None,
        "retrieved": date(2026, 10, 1),
    }
    return {**base, **campos}


def test_campos_opcionais_tem_padrao():
    f = parse_sources([fonte()])["pt-exemplo"]
    assert (f.uniform_case, f.adapter) == (False, True)


def test_campos_opcionais_declarados():
    f = parse_sources([fonte(uniform_case=True, adapter=False)])["pt-exemplo"]
    assert (f.uniform_case, f.adapter) == (True, False)


@pytest.mark.parametrize("campo", ["uniform_case", "strips_accents"])
@pytest.mark.parametrize("valor", ["sim", 1, None])
def test_campo_opcional_nao_booleano(campo, valor):
    with pytest.raises(SourceError, match=f"'{campo}' deve ser true ou false"):
        parse_sources([fonte(**{campo: valor})])


def test_strips_accents_tem_padrao_false_e_aceita_true():
    """Spec 005, R6."""
    assert parse_sources([fonte()])["pt-exemplo"].strips_accents is False
    assert parse_sources([fonte(strips_accents=True)])["pt-exemplo"].strips_accents is True


def test_fontes_que_removem_acentos_em_sources_yaml():
    """Spec 005, R6: só as fontes com evidência registrada na spec."""
    from pathlib import Path
    fontes = load_sources(Path(__file__).resolve().parent.parent / "sources.yaml")
    assert sorted(f.id for f in fontes.values() if f.strips_accents) == [
        "ca-statcan-births", "es-ine-residentes", "us-ssa-births",
    ]
