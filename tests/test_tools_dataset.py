"""Spec 007: integração com o kit de fontes do tools-dataset (R1 e R5.3)."""

import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VERSAO = "0.1.0"
DISTRIBUICAO = "benchcommons-tools-dataset"


def _pyproject() -> dict:
    return tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))


# R1: dependência fixada na versão e na tag (ADR 0013) -------------------------------------------

def test_dependencia_fixada_na_versao_e_na_tag():
    dados = _pyproject()
    assert f"{DISTRIBUICAO}=={VERSAO}" in dados["project"]["dependencies"]
    assert dados["tool"]["uv"]["sources"][DISTRIBUICAO] == {
        "git": "https://github.com/BenchCommons/tools-dataset", "tag": f"v{VERSAO}",
    }


def test_uv_lock_aponta_a_tag():
    lock = tomllib.loads((RAIZ / "uv.lock").read_text(encoding="utf-8"))
    pacote = next(p for p in lock["package"] if p["name"] == DISTRIBUICAO)
    assert pacote["version"] == VERSAO
    assert pacote["source"]["git"].startswith(f"https://github.com/BenchCommons/tools-dataset?tag=v{VERSAO}#")


def test_kit_instalado_na_versao_fixada():
    import datasettool
    assert datasettool.__version__ == VERSAO


# R3.1: base do adaptador do kit -------------------------------------------------------------------

def test_reexporta_os_objetos_do_kit():
    import datasettool.sources.adapters as kit

    import namescommons.adapters as nomes
    for nome in ("AdapterError", "FormatError", "Resource", "SourceFiles", "module_name", "parse_count", "parse_code"):
        assert getattr(nomes, nome) is getattr(kit, nome), nome


def test_load_adapter_usa_o_pacote_padrao():
    from namescommons.adapters import DEFAULT_PACKAGE, load_adapter
    mod = load_adapter("us-ssa-births")
    assert mod.__name__ == f"{DEFAULT_PACKAGE}.us_ssa_births"


def test_check_adapter_confere_links():
    from types import SimpleNamespace

    import pytest

    from namescommons.adapters import AdapterError, Resource, check_adapter
    base = dict(SOURCE_ID="x", RESOURCES=[Resource("https://example.org/a.csv", "a.csv")], parse=lambda f: iter(()))
    check_adapter(SimpleNamespace(**base), "x")
    check_adapter(SimpleNamespace(**base, links=lambda f: iter(())), "x")
    with pytest.raises(AdapterError, match="'x': links must be a function"):
        check_adapter(SimpleNamespace(**base, links="não"), "x")


# R2: módulos movidos para o kit não existem mais aqui ---------------------------------------------

def test_namescommons_spreadsheet_nao_existe():
    import importlib.util
    assert importlib.util.find_spec("namescommons.spreadsheet") is None


def test_namescommons_cache_nao_existe():
    import importlib.util
    assert importlib.util.find_spec("namescommons.cache") is None


# R3.3: downloads pelo kit com o User-Agent deste projeto ------------------------------------------

def test_user_agent_igual_ao_anterior():
    from importlib.metadata import version

    from namescommons import USER_AGENT
    assert USER_AGENT == f"namescommons/{version('names-commons-dataset')} (+https://github.com/BenchCommons/dataset-names)"


def test_pipeline_envia_o_user_agent_do_projeto(servir_fixtures, tmp_path):
    import adaptadores.exemplo

    from namescommons import USER_AGENT
    from namescommons.pipeline import fetch_sources, select_sources
    from namescommons.sources import load_sources
    servidor = servir_fixtures(adaptadores.exemplo)
    fontes = load_sources(RAIZ / "tests" / "fixtures" / "sources.yaml")
    fetch_sources(select_sources(fontes, ["exemplo"]), tmp_path, adapters="adaptadores")
    assert [agente for _, agente in servidor.requisicoes] == [USER_AGENT, USER_AGENT]


# R3.2: registro de fontes sobre o kit -------------------------------------------------------------

def test_source_error_e_o_registry_error_do_kit():
    from datasettool.sources.registry import RegistryError

    from namescommons.sources import SourceError
    assert SourceError is RegistryError


def test_esquema_de_nomes_sobre_o_kit():
    from datasettool.sources.registry import ATTRIBUTION_ONLY_LICENSES, RegistrySchema

    from namescommons.sources import SCHEMA
    assert isinstance(SCHEMA, RegistrySchema)
    assert SCHEMA.accepted_licenses == ATTRIBUTION_ONLY_LICENSES | {"statcan-open-licence"}
    assert SCHEMA.license_policy == "ADR 0001"
    campos = {f.name: (f.required, f.default) for f in SCHEMA.fields}
    assert campos == {
        "country": (True, None), "count_type": (True, None), "primary": (True, None), "suppression": (True, None),
        "uniform_case": (False, False), "strips_accents": (False, False),
    }
