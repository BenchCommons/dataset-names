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
FONTES_OFICIAIS = ("fr-insee-births", "ca-statcan-births", "es-ine-residentes", "ie-cso-births", "no-ssb-etternavn", "no-ssb-fornavn", "us-ssa-births", "wikidata")
WORKFLOW = RAIZ / ".github" / "workflows" / "ci.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _comandos() -> list[str]:
    passos = _workflow()["jobs"]["testes"]["steps"]
    return [p["run"] for p in passos if "run" in p]


def test_gatilhos_sao_push_e_pull_request():
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


ES_CSV = """\
kind,name,name_key,ascii,script,count,count_type,rank,female_share,gender_basis,first_year,last_year
family,Garcia,garcia,garcia,Latn,1446937,population,1,,0,2025,2025
family,Muñoz,muñoz,munoz,Latn,284951,population,2,,0,2025,2025
family,Gonçalves,gonçalves,goncalves,Latn,3020,population,3,,0,2025,2025
family,O'Brien,o'brien,o'brien,Latn,573,population,4,,0,2025,2025
family,Lyu,lyu,lyu,Latn,208,population,5,,0,2025,2025
family,Tudorica,tudorica,tudorica,Latn,100,population,6,,0,2025,2025
family,Anchustegui,anchustegui,anchustegui,Latn,99,population,7,,0,2025,2025
family,Nel·lo,nel·lo,nello,Latn,26,population,8,,0,2025,2025
family,Zrhaida,zrhaida,zrhaida,Latn,20,population,9,,0,2025,2025
given,Maria Carmen,maria carmen,maria carmen,Latn,618622,population,1,1.000000,618622,2025,2025
given,Antonio,antonio,antonio,Latn,590938,population,2,0.000000,590938,2025,2025
given,Andrea,andrea,andrea,Latn,113054,population,3,0.973084,113054,2025,2025
given,Begoña,begoña,begona,Latn,36293,population,4,1.000000,36293,2025,2025
given,Iñigo,iñigo,inigo,Latn,22083,population,5,0.000000,22083,2025,2025
given,Llorenç,llorenç,llorenc,Latn,2513,population,6,0.000000,2513,2025,2025
given,Françoise,françoise,francoise,Latn,338,population,7,1.000000,338,2025,2025
given,Francesc D'Assis,francesc d'assis,francesc d'assis,Latn,192,population,8,0.000000,192,2025,2025
given,Joana D'Arc,joana d'arc,joana d'arc,Latn,21,population,9,1.000000,21,2025,2025
given,Zulma Patricia,zulma patricia,zulma patricia,Latn,20,population,10,1.000000,20,2025,2025
given,Zunair,zunair,zunair,Latn,20,population,10,0.000000,20,2025,2025
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
    """Spec 003, R5, e spec 004, R7: a CI roda as fontes de sources.yaml sobre um cache montado com as amostras."""
    passo = next(p for p in _workflow()["jobs"]["testes"]["steps"] if "cache-oficiais" in p.get("run", ""))
    ambiente = {**os.environ, **passo.get("env", {}), "RUNNER_TEMP": str(tmp_path)}
    r = subprocess.run(["bash", "-e", "-c", passo["run"]], cwd=RAIZ, env=ambiente,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    resumo = re.search(r"OK: (\d+) observações, 6 países", r.stdout)
    assert resumo, r.stdout
    assert int(resumo.group(1)) == pq.ParquetFile(tmp_path / "dist-oficiais" / "observations.parquet").metadata.num_rows > 0
    assert sorted(p.name for p in (tmp_path / "cache-oficiais").iterdir()) == sorted(FONTES_OFICIAIS)
    assert (tmp_path / "dist-oficiais" / "by_country" / "NO.csv").read_text(encoding="utf-8") == NO_CSV
    assert (tmp_path / "dist-oficiais" / "by_country" / "CA.csv").read_text(encoding="utf-8") == CA_CSV
    # Spec 003b, R4: Espanha com nomes e sobrenomes population de 2025; ANDREA dos dois sexos
    assert (tmp_path / "dist-oficiais" / "by_country" / "ES.csv").read_text(encoding="utf-8") == ES_CSV
    # Spec 004, R7: o Wikidata entra no passo e grava a tabela de ligações.
    assert "variant_links.parquet" in passo["run"]
    assert (tmp_path / "dist-oficiais" / "variant_links.parquet").stat().st_size > 0


def test_passo_das_fontes_oficiais_confere_todos_os_paises():
    """Spec 003d, R5: o passo confere by_country/ de cada país de sources.yaml, inclusive CA e ES."""
    passo = next(p for p in _workflow()["jobs"]["testes"]["steps"] if "cache-oficiais" in p.get("run", ""))
    assert "for pais in CA ES FR IE NO US;" in passo["run"]
