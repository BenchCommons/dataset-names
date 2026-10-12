"""Spec 002, R7: o workflow da CI roda uv sync, pytest e namescommons run --offline sobre as fixtures."""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pyarrow.parquet as pq
import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent
FONTES_OFICIAIS = ("fr-insee-births", "ie-cso-births", "no-ssb-etternavn", "no-ssb-fornavn", "us-ssa-births")
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


def test_push_so_na_branch_principal_para_nao_rodar_duas_vezes_em_pr_do_mesmo_repositorio():
    dados = _workflow()
    gatilhos = dados.get("on", dados.get(True))
    assert gatilhos["push"] == {"branches": ["master"]}
    assert gatilhos["pull_request"] in (None, {})


def test_permissoes_minimas_e_cache_do_uv():
    dados = _workflow()
    assert dados["permissions"] == {"contents": "read"}
    uv = next(p for p in dados["jobs"]["testes"]["steps"] if p.get("uses", "").startswith("astral-sh/setup-uv"))
    assert uv["with"]["enable-cache"] is True


def _indice(comandos, trecho):
    return next(i for i, c in enumerate(comandos) if trecho in c)


def test_passos_da_ci():
    """Confere os passos pelo conteúdo e pela ordem, não pela posição na lista."""
    comandos = _comandos()
    assert comandos[_indice(comandos, "uv sync")].strip() == "uv sync"
    assert comandos[_indice(comandos, "uv run pytest")].strip() == "uv run pytest -q"
    assert _indice(comandos, "uv sync") < _indice(comandos, "uv run pytest") < _indice(comandos, "namescommons run --offline")


def test_release_da_ci_nao_e_fixa():
    for comando in _comandos():
        if "--release" in comando:
            assert "--release 2026.10" not in comando
            assert '--release "$(date -u +%Y.%m)"' in comando


def test_cache_das_fontes_oficiais_copia_so_as_amostras_das_fontes():
    passo = next(c for c in _comandos() if "cache-oficiais" in c)
    assert "tests/fixtures/." not in passo


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


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv fora do PATH")
def test_passo_das_fontes_oficiais_roda_localmente(tmp_path):
    """Spec 003, R5: a CI roda as fontes de sources.yaml sobre um cache montado com as amostras."""
    passo = next(p for p in _workflow()["jobs"]["testes"]["steps"] if "cache-oficiais" in p.get("run", ""))
    ambiente = {**os.environ, **passo.get("env", {}), "RUNNER_TEMP": str(tmp_path)}
    r = subprocess.run(["bash", "-e", "-c", passo["run"]], cwd=RAIZ, env=ambiente,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    resumo = re.search(r"OK: (\d+) observações, 4 países", r.stdout)
    assert resumo, r.stdout
    assert int(resumo.group(1)) == pq.ParquetFile(tmp_path / "dist-oficiais" / "observations.parquet").metadata.num_rows > 0
    assert sorted(p.name for p in (tmp_path / "cache-oficiais").iterdir()) == sorted(FONTES_OFICIAIS)
    assert (tmp_path / "dist-oficiais" / "by_country" / "NO.csv").read_text(encoding="utf-8") == NO_CSV
