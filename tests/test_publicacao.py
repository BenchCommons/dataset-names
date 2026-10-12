"""Spec 006, R3 a R6: atribuições, licença, cartão do dataset e pacote da release."""

from dataclasses import replace
from pathlib import Path

import pytest

from namescommons.aggregate import by_country
from namescommons.publication import AVISOS, LICENCAS, attribution_text, dataset_attribution, dataset_card
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


# R6 ----------------------------------------------------------------------------------------------

SECOES = ["## Summary", "## Files", "## Fields", "## Sources", "## Coverage", "## Suppression",
          "## Known limitations", "## Licence", "## How to cite"]


def _manifesto(fontes, usadas, dropped=None, links=None):
    arquivos = {
        "by_country/BR.csv": {"sha256": "0" * 64, "rows": 3},
        "by_country/US.csv": {"sha256": "0" * 64, "rows": 4},
        "family_names.csv": {"sha256": "0" * 64, "rows": 2},
        "family_names.parquet": {"sha256": "0" * 64, "rows": 2},
        "given_names.csv": {"sha256": "0" * 64, "rows": 5},
        "given_names.parquet": {"sha256": "0" * 64, "rows": 5},
        "observations.parquet": {"sha256": "0" * 64, "rows": 16},
    }
    if links is not None:
        arquivos["variant_links.parquet"] = {"sha256": "0" * 64, "rows": links}
    return {
        "release": "2026.10", "schema_version": "1.3.0", "data_license": "CC-BY-4.0",
        "sources": [
            {"id": i, "name": fontes[i].name, "license": fontes[i].license,
             "retrieved": fontes[i].retrieved.isoformat(), "observations": 4,
             "dropped": (dropped or {}).get(i)}
            for i in sorted(usadas)
        ],
        "files": arquivos,
    }


@pytest.fixture
def cartao(observacoes, fontes):
    paises = by_country(observacoes, fontes)
    usadas = {o.source_id for o in observacoes}
    m = _manifesto(fontes, usadas, dropped={"us-ssa": {"lines": 3, "records": 49}, "br-ibge-censo": {"lines": 0, "records": 0}}, links=47)
    return dataset_card(m, fontes, paises)


def test_cartao_tem_as_secoes(cartao):
    assert cartao.startswith("# Names Commons Dataset, release 2026.10\n")
    posicoes = [cartao.index(f"\n{s}\n") for s in SECOES]
    assert posicoes == sorted(posicoes)
    assert "\r" not in cartao and "—" not in cartao


def test_cartao_usa_os_numeros_do_manifesto(cartao):
    for trecho in ("Schema version: 1.3.0", "Observations: 16", "Given names: 5", "Family names: 2",
                   "Countries: 2", "Variant links: 47",
                   "| `given_names.csv` | 5 |", "| `by_country.zip` | 7 |", "| `variant_links.parquet` | 47 |"):
        assert trecho in cartao, trecho
    # BR usa só a edição mais recente (population); US tem Ana Clara só atestada (fonte não primary).
    assert "| BR | 2 (population) | 1 (population) | 2022 to 2022 |" in cartao
    assert "| US | 4 (attested, births) |  | 2020 to 2021 |" in cartao


def test_cartao_lista_fontes_sem_acento_e_descartes(observacoes, fontes):
    fontes = {**fontes, "us-ssa": replace(fontes["us-ssa"], strips_accents=True),
              "br-ibge-censo": replace(fontes["br-ibge-censo"], uniform_case=True)}
    usadas = {o.source_id for o in observacoes}
    m = _manifesto(fontes, usadas, dropped={"us-ssa": {"lines": 3, "records": 49}})
    texto = dataset_card(m, fontes, by_country(observacoes, fontes))
    limitacoes = texto.split("## Known limitations", 1)[1].split("\n## ", 1)[0]
    assert "Sources that publish names without accents: SSA." in limitacoes
    assert "Sources that publish names in a single case, recapitalised by the pipeline: IBGE Censo." in limitacoes
    assert "3 lines (49 records) were dropped" in limitacoes
    assert "Drop counts are unknown for: IBGE Censo" in limitacoes
    assert "`group_id`" in limitacoes and "within one release" in limitacoes
    assert "`female_share`" in limitacoes
    fontes_tabela = texto.split("## Sources", 1)[1].split("\n## ", 1)[0]
    assert "| SSA | `us-ssa` | US | births | public-domain | below 5 | 2026-10-01 | 4 | 3 lines, 49 records |" in fontes_tabela
    assert "| IBGE Censo | `br-ibge-censo` | BR | population | CC-BY-4.0 | none | 2026-10-01 | 4 | unknown |" in fontes_tabela


def test_cartao_data_do_wikidata(cartao):
    assert "QLever" in cartao and "2026-10-01" in cartao.split("QLever", 1)[1].split("\n", 1)[0]


def test_cartao_sem_statcan_nao_traz_avisos(cartao):
    assert "Statistics Canada" not in cartao
    assert dataset_attribution("2026.10") in cartao.split("## How to cite", 1)[1]
    assert "https://github.com/BenchCommons/dataset-names/releases/tag/2026.10" in cartao


def test_cartao_traz_os_avisos_da_statcan(reais):
    m = _manifesto(reais, {STATCAN, "wikidata"})
    texto = dataset_card(m, reais, {})
    licenca = texto.split("## Licence", 1)[1].split("\n## ", 1)[0]
    assert reais[STATCAN].attribution in licenca
    assert AVISOS["statcan-open-licence"] in licenca
