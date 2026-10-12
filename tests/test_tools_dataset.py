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
