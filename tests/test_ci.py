"""Spec 002, R7: o workflow da CI roda uv sync, pytest e namescommons run --offline sobre as fixtures."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent
WORKFLOW = RAIZ / ".github" / "workflows" / "ci.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _comandos() -> list[str]:
    passos = _workflow()["jobs"]["testes"]["steps"]
    return [p["run"] for p in passos if "run" in p]


def test_roda_em_todo_push_e_pull_request():
    dados = _workflow()
    gatilhos = dados.get("on", dados.get(True))  # PyYAML lê a chave "on" como True
    assert set(gatilhos) == {"push", "pull_request"}


def test_passos_da_ci():
    comandos = _comandos()
    assert comandos[0] == "uv sync"
    assert comandos[1] == "uv run pytest -q"
    assert "namescommons run --offline" in comandos[2]


def test_cache_fica_fora_do_git():
    assert "/cache/" in (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv fora do PATH")
def test_passo_offline_da_ci_roda_localmente(tmp_path):
    passo = next(p for p in _workflow()["jobs"]["testes"]["steps"] if "namescommons run" in p.get("run", ""))
    ambiente = {**os.environ, **passo["env"], "RUNNER_TEMP": str(tmp_path)}
    r = subprocess.run(["bash", "-e", "-c", passo["run"]], cwd=RAIZ, env=ambiente,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "dist" / "by_country" / "PT.csv").is_file()
    assert "OK: 8 observações, 1 país" in r.stdout


NO_CSV = """\
kind,name,name_key,ascii,script,count,count_type,rank,female_share,gender_basis,first_year,last_year
family,Hansen,hansen,hansen,Latn,47879,population,1,,0,2025,2025
family,Abdo,abdo,abdo,Latn,232,population,2,,0,2025,2025
family,Da Silva,da silva,da silva,Latn,219,population,3,,0,2025,2025
given,Nora,nora,nora,Latn,432,births,1,1.000000,432,1990,2025
given,Kim,kim,kim,Latn,422,births,2,0.049763,422,1990,1990
given,Jakob,jakob,jakob,Latn,329,births,3,0.000000,329,1990,2025
given,Åse,åse,ase,Latn,93,births,4,1.000000,93,1990,2025
"""


# Spec 003d: Noah 36 F de 2301 (0,015645); Riley 35 + 261 F de 762 (0,388451).
CA_CSV = """\
kind,name,name_key,ascii,script,count,count_type,rank,female_share,gender_basis,first_year,last_year
given,Noah,noah,noah,Latn,2301,births,1,0.015645,2301,1991,2025
given,Olivia,olivia,olivia,Latn,2019,births,2,1.000000,2019,1991,2025
given,Riley,riley,riley,Latn,762,births,3,0.388451,762,1991,2025
given,Marie-Eve,marie-eve,marie-eve,Latn,664,births,4,1.000000,664,1991,1991
given,Jean-Philippe,jean-philippe,jean-philippe,Latn,447,births,5,0.000000,447,1991,1991
given,D'Arcy,d'arcy,d'arcy,Latn,13,births,6,0.000000,13,1991,1991
"""


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv fora do PATH")
def test_passo_das_fontes_oficiais_roda_localmente(tmp_path):
    """Spec 003, R5: a CI roda as fontes de sources.yaml sobre um cache montado com as amostras."""
    passo = next(p for p in _workflow()["jobs"]["testes"]["steps"] if "cache-oficiais" in p.get("run", ""))
    ambiente = {**os.environ, **passo.get("env", {}), "RUNNER_TEMP": str(tmp_path)}
    r = subprocess.run(["bash", "-e", "-c", passo["run"]], cwd=RAIZ, env=ambiente,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert "OK: 51 observações, 5 países" in r.stdout
    assert (tmp_path / "dist-oficiais" / "by_country" / "NO.csv").read_text(encoding="utf-8") == NO_CSV
    assert (tmp_path / "dist-oficiais" / "by_country" / "CA.csv").read_text(encoding="utf-8") == CA_CSV


def test_passo_das_fontes_oficiais_confere_todos_os_paises():
    """Spec 003d, R5: o passo confere by_country/ de cada país de sources.yaml, inclusive CA."""
    passo = next(p for p in _workflow()["jobs"]["testes"]["steps"] if "cache-oficiais" in p.get("run", ""))
    assert "for pais in CA FR IE NO US;" in passo["run"]
