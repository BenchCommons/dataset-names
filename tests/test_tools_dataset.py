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
