"""Spec 002, R1 e R7: parse do adaptador de exemplo sobre a fixture e pacote padrão.

O contrato genérico do adaptador é testado no tools-dataset (spec 007, R2.6).
"""

from pathlib import Path

import pytest

from namescommons.adapters import AdapterError, RawRecord, load_adapter

FIXTURES = Path(__file__).parent / "fixtures"


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


def test_pacote_padrao_ainda_nao_tem_adaptadores():
    with pytest.raises(AdapterError, match="namescommons.adapters.us_ssa"):
        load_adapter("us-ssa")
