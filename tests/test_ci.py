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


NZ_CSV = """\
kind,name,name_key,ascii,script,count,count_type,rank,female_share,gender_basis,first_year,last_year
given,John,john,john,Latn,636,births,1,0.000000,636,1900,1900
given,Mary,mary,mary,Latn,410,births,2,1.000000,410,1900,1900
given,Esmé,esmé,esme,Latn,45,births,3,1.000000,45,2022,2025
given,Nikau,nikau,nikau,Latn,36,births,4,0.000000,36,2025,2025
given,Te Ariki,te ariki,te ariki,Latn,34,births,5,0.000000,34,2025,2025
given,Te Ao,te ao,te ao,Latn,27,births,6,0.555556,27,2024,2024
given,Zoé,zoé,zoe,Latn,26,births,7,1.000000,26,2007,2007
given,Anne-Marie,anne-marie,anne-marie,Latn,24,births,8,1.000000,24,1967,1967
given,Aroha,aroha,aroha,Latn,22,births,9,1.000000,22,2025,2025
given,André,andré,andre,Latn,20,births,10,0.000000,20,2003,2003
given,Aadhya,aadhya,aadhya,Latn,13,births,11,1.000000,13,2022,2022
given,Zoya,zoya,zoya,Latn,11,births,12,1.000000,11,2015,2015
given,Björn,björn,bjorn,Latn,10,births,13,0.000000,10,2025,2025
"""


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv fora do PATH")
def test_passo_das_fontes_oficiais_roda_localmente(tmp_path):
    """Spec 003, R5: a CI roda as fontes de sources.yaml sobre um cache montado com as amostras."""
    passo = next(p for p in _workflow()["jobs"]["testes"]["steps"] if "cache-oficiais" in p.get("run", ""))
    ambiente = {**os.environ, **passo.get("env", {}), "RUNNER_TEMP": str(tmp_path)}
    r = subprocess.run(["bash", "-e", "-c", passo["run"]], cwd=RAIZ, env=ambiente,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert "OK: 54 observações, 5 países" in r.stdout
    assert (tmp_path / "dist-oficiais" / "by_country" / "NO.csv").read_text(encoding="utf-8") == NO_CSV
    # Spec 003e, R6: a Nova Zelândia entra no passo, sem os nomes corrompidos na fonte.
    assert "for pais in FR IE NO NZ US;" in passo["run"]
    assert (tmp_path / "dist-oficiais" / "by_country" / "NZ.csv").read_text(encoding="utf-8") == NZ_CSV
    assert "nz-dia-births: 3 linha(s) com nome corrompido" in r.stderr
