"""Spec 006, R3 a R6: atribuições, licença, cartão do dataset e pacote da release."""

from dataclasses import replace
from pathlib import Path

import pytest

from namescommons.publication import AVISOS, LICENCAS, attribution_text, dataset_attribution
from namescommons.sources import LICENCAS_COMPATIVEIS, load_sources

RAIZ = Path(__file__).resolve().parent.parent
STATCAN = "ca-statcan-births"


@pytest.fixture
def reais():
    return load_sources(RAIZ / "sources.yaml")


# R3 e R4 -----------------------------------------------------------------------------------------

def test_tabela_cobre_as_licencas_aceitas():
    assert set(LICENCAS) == set(LICENCAS_COMPATIVEIS)
    assert set(AVISOS) <= set(LICENCAS)
    for nome, url in LICENCAS.values():
        assert nome and (url is None or url.startswith("https://"))


def test_atribuicao_reproduz_o_texto_sem_edicao(reais):
    texto = attribution_text("2026.10", reais, set(reais))
    for fonte in reais.values():
        assert f"\nAttribution: {fonte.attribution}\n" in texto
        assert f"\nURL: {fonte.url}\n" in texto
        assert f"\nLicence: {LICENCAS[fonte.license][0]}" in texto
    assert texto.startswith("Attribution for the Names Commons Dataset, release 2026.10\n")
    assert dataset_attribution("2026.10") in texto
    assert texto.endswith("\n") and "\r" not in texto and not texto.startswith("﻿")


def test_atribuicao_em_ordem_de_id_so_com_fontes_usadas(reais):
    texto = attribution_text("2026.10", reais, {"wikidata", "fr-insee-births"})
    assert texto.index("Id: fr-insee-births") < texto.index("Id: wikidata")
    assert "us-ssa-births" not in texto
    assert reais["us-ssa-births"].attribution not in texto


def test_aviso_de_condicoes_so_com_statcan(reais):
    aviso = AVISOS["statcan-open-licence"]
    com = attribution_text("2026.10", reais, {STATCAN, "wikidata"})
    sem = attribution_text("2026.10", reais, {"wikidata"})
    assert com.count(aviso) == 1 and com.index("Notices") < com.index(aviso)
    assert aviso not in sem and "Statistics Canada" not in sem


def test_licenca_sem_entrada_falha(reais):
    fontes = {**reais, "wikidata": replace(reais["wikidata"], license="licenca-nova")}
    with pytest.raises(ValueError, match="licença 'licenca-nova' da fonte 'wikidata'"):
        attribution_text("2026.10", fontes, {"wikidata"})


def test_aviso_do_readme_igual_ao_da_tabela():
    """ADR 0004: o README traz o aviso de condições sem tradução, igual ao da release."""
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    assert AVISOS["statcan-open-licence"] in readme
    assert AVISOS["statcan-open-licence"].startswith("Data adapted from Statistics Canada remain subject to")


def test_data_license_tem_a_linha_de_atribuicao():
    texto = (RAIZ / "DATA_LICENSE").read_text(encoding="utf-8")
    assert dataset_attribution("<release>") in texto
    assert texto.index(dataset_attribution("<release>")) < texto.index("\nAttribution 4.0 International\n")
    assert "ATTRIBUTION.txt" in texto and "Apache-2.0" in texto and "legacy/" in texto


def test_linha_de_atribuicao_do_dataset():
    assert dataset_attribution("2026.10") == (
        "Names Commons Dataset, release 2026.10, BenchCommons (https://github.com/BenchCommons/dataset-names), "
        "licensed under CC BY 4.0. Upstream sources and notices: see ATTRIBUTION.txt."
    )


def test_sem_simbolos_da_statcan():
    """R3.5: nenhum logotipo ou símbolo da Statistics Canada ou do Governo do Canadá no projeto."""
    proibidos = ("statcan", "canada", "maple", "wordmark", "coat-of-arms")
    for imagem in (RAIZ / "assets").iterdir():
        assert not any(p in imagem.name.lower() for p in proibidos), imagem.name
    readme = (RAIZ / "README.md").read_text(encoding="utf-8").lower()
    assert "<img" not in readme or all(p not in readme.split("<img", 1)[1].split(">", 1)[0] for p in proibidos)
