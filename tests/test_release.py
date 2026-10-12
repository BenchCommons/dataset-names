"""Spec 006, R7, e ADR 0014: tools/release.sh e o workflow de release.

O envio é testado com um `gh` falso no PATH, que registra os argumentos e simula o rascunho;
nenhum teste chama o gh real nem a rede.
"""

import os
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "tools" / "release.sh"
RELEASE_YML = RAIZ / ".github" / "workflows" / "release.yml"
CI_YML = RAIZ / ".github" / "workflows" / "ci.yml"
ASSETS = sorted([
    "ATTRIBUTION.txt", "DATASET_CARD.md", "DATA_LICENSE", "SHA256SUMS", "by_country.zip", "family_names.csv",
    "family_names.parquet", "given_names.csv", "given_names.parquet", "manifest.json", "observations.parquet",
    "variant_links.parquet",
])

GH_FALSO = r"""#!/usr/bin/env bash
# gh falso: registra a chamada e simula um rascunho conforme FAKE_DRAFT (true, false, ausente ou erro).
# O estado dos assets fica em FAKE_STATE: delete-asset tira o cache, salvo com FAKE_DELETE_IGNORADO.
printf '%s\n' "$*" >> "$FAKE_GH_LOG"
estado="$FAKE_GH_LOG.assets"
[ -f "$estado" ] || printf '%s\n' $FAKE_ASSETS > "$estado"
case "$1 $2" in
  "release view")
    [ "$FAKE_DRAFT" = ausente ] && { echo "release not found" >&2; exit 1; }
    [ "$FAKE_DRAFT" = erro ] && { echo "HTTP 401: Bad credentials (https://api.github.com/graphql)" >&2; exit 1; }
    case "$*" in
      *isDraft*) echo "$FAKE_DRAFT" ;;
      *assets*)
        if [ -n "$FAKE_VIEW_ASSETS_FALHA" ] && grep -q "release upload" "$FAKE_GH_LOG"; then
          echo "HTTP 502" >&2; exit 1
        fi
        cat "$estado" ;;
    esac ;;
  "release download")
    [ -n "$FAKE_TAR" ] || { echo "no assets match" >&2; exit 1; }
    while [ $# -gt 0 ]; do [ "$1" = --dir ] && dir=$2; shift; done
    cp "$FAKE_TAR" "$dir/source-cache.tar.gz" ;;
  "release delete-asset")
    [ -n "$FAKE_DELETE_IGNORADO" ] || { grep -vx "$4" "$estado" > "$estado.novo"; mv "$estado.novo" "$estado"; } ;;
esac
exit 0
"""

pytestmark = pytest.mark.skipif(shutil.which("uv") is None or shutil.which("bash") is None, reason="uv ou bash fora do PATH")


def _rodar(*args, cwd=RAIZ, **env_extra):
    return subprocess.run(["bash", str(SCRIPT), *map(str, args)], cwd=cwd, capture_output=True, text=True,
                          timeout=300, env={**os.environ, **env_extra})


@pytest.fixture
def gh(tmp_path):
    binario = tmp_path / "bin"
    binario.mkdir()
    (binario / "gh").write_text(GH_FALSO, encoding="utf-8")
    (binario / "gh").chmod(0o755)
    log = tmp_path / "gh.log"
    log.touch()
    ambiente = {"PATH": f"{binario}{os.pathsep}{os.environ['PATH']}", "FAKE_GH_LOG": str(log),
                "FAKE_DRAFT": "true", "FAKE_ASSETS": "source-cache.tar.gz", "FAKE_TAR": "",
                "FAKE_VIEW_ASSETS_FALHA": "", "FAKE_DELETE_IGNORADO": ""}
    return ambiente, log


@pytest.fixture(scope="module")
def release_pronta(tmp_path_factory):
    """Uma release montada por tools/release.sh sobre as amostras, reaproveitada pelos testes de envio."""
    base = tmp_path_factory.mktemp("release")
    r = _rodar("fixture-cache", base / "cache")
    assert r.returncode == 0, r.stderr
    r = _rodar("build", "2026.10", base / "cache", base / "dist" / "2026.10")
    assert r.returncode == 0, r.stderr
    return base / "dist" / "2026.10"


def _copia(release_pronta, tmp_path):
    destino = tmp_path / "2026.10"
    shutil.copytree(release_pronta, destino)
    return destino


# Script ------------------------------------------------------------------------------------------

def test_build_local_sobre_as_amostras(release_pronta):
    assert sorted(p.name for p in release_pronta.iterdir() if p.is_file()) == ASSETS
    assert (release_pronta / "by_country").is_dir()


def test_build_recusa_somas_que_nao_conferem(release_pronta, tmp_path):
    saida = _copia(release_pronta, tmp_path)
    with open(saida / "given_names.csv", "a", encoding="utf-8") as fh:
        fh.write("adulterado\n")
    r = _rodar("verify", saida)
    assert r.returncode != 0 and "given_names.csv" in r.stdout + r.stderr


@pytest.mark.parametrize("release", ["2026-10", "2026.13", "26.10", "2026.10.0", "2026.1", "v2026.10", "2026.10;ls"])
def test_release_fora_de_calver_e_recusada(release, gh, tmp_path):
    ambiente, log = gh
    for args in (["check", release], ["fetch-cache", release, tmp_path / "c"], ["upload", release, tmp_path]):
        r = _rodar(*args, **ambiente)
        assert r.returncode != 0 and "AAAA.MM" in r.stderr
    assert log.read_text(encoding="utf-8") == ""


def test_calver_aceito(gh):
    ambiente, _ = gh
    for release in ("2026.10", "2026.01.2", "2027.12.10"):
        assert _rodar("check", release, **ambiente).returncode == 0


def test_fetch_cache_sem_rascunho_falha(gh, tmp_path):
    ambiente, _ = gh
    r = _rodar("fetch-cache", "2026.10", tmp_path / "c", **{**ambiente, "FAKE_DRAFT": "ausente"})
    assert r.returncode != 0 and "rascunho" in r.stderr and "source-cache.tar.gz" in r.stderr


def test_fetch_cache_recusa_release_publicada(gh, tmp_path):
    ambiente, _ = gh
    r = _rodar("fetch-cache", "2026.10", tmp_path / "c", **{**ambiente, "FAKE_DRAFT": "false"})
    assert r.returncode != 0 and "publicada" in r.stderr


def test_fetch_cache_extrai_o_cache_do_rascunho(gh, tmp_path):
    ambiente, log = gh
    pacote = tmp_path / "pacote.tar.gz"
    with tarfile.open(pacote, "w:gz") as tar:
        tar.add(RAIZ / "tests" / "fixtures" / "nz-dia-births", arcname="nz-dia-births")
    r = _rodar("fetch-cache", "2026.10", tmp_path / "c", **{**ambiente, "FAKE_TAR": str(pacote)})
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "c" / "nz-dia-births" / "baby-names-1900-to-2025.csv").is_file()
    assert "release download 2026.10 --pattern source-cache.tar.gz" in log.read_text(encoding="utf-8")


def test_fetch_cache_sem_o_asset_falha(gh, tmp_path):
    ambiente, _ = gh
    r = _rodar("fetch-cache", "2026.10", tmp_path / "c", **ambiente)
    assert r.returncode != 0 and "source-cache.tar.gz" in r.stderr


def test_upload_recusa_release_publicada(gh, release_pronta, tmp_path):
    ambiente, log = gh
    r = _rodar("upload", "2026.10", _copia(release_pronta, tmp_path), **{**ambiente, "FAKE_DRAFT": "false"})
    assert r.returncode != 0 and "publicada" in r.stderr
    assert "upload" not in log.read_text(encoding="utf-8") and "delete-asset" not in log.read_text(encoding="utf-8")


def test_upload_sem_rascunho_falha(gh, release_pronta, tmp_path):
    ambiente, log = gh
    r = _rodar("upload", "2026.10", _copia(release_pronta, tmp_path), **{**ambiente, "FAKE_DRAFT": "ausente"})
    assert r.returncode != 0 and "rascunho" in r.stderr
    assert "release upload" not in log.read_text(encoding="utf-8")


def test_upload_sem_clobber_e_remove_o_cache_depois(gh, release_pronta, tmp_path):
    ambiente, log = gh
    saida = _copia(release_pronta, tmp_path)
    r = _rodar("upload", "2026.10", saida, **ambiente)
    assert r.returncode == 0, r.stderr
    chamadas = log.read_text(encoding="utf-8").splitlines()
    envio = next(i for i, c in enumerate(chamadas) if c.startswith("release upload 2026.10 "))
    remocao = next(i for i, c in enumerate(chamadas) if c.startswith("release delete-asset 2026.10 source-cache.tar.gz"))
    assert envio < remocao
    assert all("--clobber" not in c for c in chamadas)
    enviados = chamadas[envio].split()[3:]
    assert sorted(Path(p).name for p in enviados) == ASSETS


def test_upload_envia_so_os_arquivos_do_nivel_de_cima(gh, release_pronta, tmp_path):
    ambiente, log = gh
    assert _rodar("upload", "2026.10", _copia(release_pronta, tmp_path), **ambiente).returncode == 0
    envio = next(c for c in log.read_text(encoding="utf-8").splitlines() if c.startswith("release upload"))
    assert "by_country/" not in envio and "/by_country " not in envio


def test_upload_sem_cache_no_rascunho_nao_remove_nada(gh, release_pronta, tmp_path):
    ambiente, log = gh
    assert _rodar("upload", "2026.10", _copia(release_pronta, tmp_path), **{**ambiente, "FAKE_ASSETS": "x.csv"}).returncode == 0
    assert "delete-asset" not in log.read_text(encoding="utf-8")


def test_upload_recusa_saida_adulterada(gh, release_pronta, tmp_path):
    ambiente, log = gh
    saida = _copia(release_pronta, tmp_path)
    (saida / "extra.txt").write_text("fora das somas\n", encoding="utf-8")
    r = _rodar("upload", "2026.10", saida, **ambiente)
    assert r.returncode != 0 and "extra.txt" in r.stderr
    assert "release upload" not in log.read_text(encoding="utf-8")


# Workflows ---------------------------------------------------------------------------------------

def _yaml(caminho):
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    return dados, dados.get("on", dados.get(True))


def _runs(job):
    return [p.get("run", "") for p in job["steps"]]


def test_workflow_nao_publica_nem_cria_tag():
    texto = RELEASE_YML.read_text(encoding="utf-8") + SCRIPT.read_text(encoding="utf-8")
    for proibido in ("gh release create", "gh release edit", "--draft=false", "git push", "git tag", "--clobber",
                     "softprops/action-gh-release"):
        assert proibido not in texto, proibido


def test_gatilhos_do_workflow_de_release():
    dados, gatilhos = _yaml(RELEASE_YML)
    assert set(gatilhos) == {"push", "workflow_dispatch"}
    assert set(gatilhos["push"]) == {"tags"}
    assert dados["permissions"] == {"contents": "read"}


def test_dispatch_e_ensaio():
    dados, _ = _yaml(RELEASE_YML)
    ensaio, release = dados["jobs"]["ensaio"], dados["jobs"]["release"]
    assert "workflow_dispatch" in ensaio["if"] and "push" in release["if"]
    assert ensaio.get("permissions", dados["permissions"]) == {"contents": "read"}
    comandos = "\n".join(_runs(ensaio))
    assert "fixture-cache" in comandos and "tools/release.sh build" in comandos
    assert "fetch-cache" not in comandos and "upload" not in comandos and "gh " not in comandos
    assert release["permissions"] == {"contents": "write"}
    comandos = _runs(release)
    ordem = [next(i for i, c in enumerate(comandos) if t in c)
             for t in ("tools/release.sh check", "fetch-cache", "tools/release.sh build", "tools/release.sh upload")]
    assert ordem == sorted(ordem)


def test_release_passa_ao_shell_so_por_variavel():
    """R7.6: o nome da release chega ao shell por env, nunca interpolado no script do passo."""
    dados, _ = _yaml(RELEASE_YML)
    for job in dados["jobs"].values():
        assert "RELEASE" in job["env"]
        for comando in _runs(job):
            assert "${{" not in comando


def test_padroes_de_tag_sao_calver():
    _, gatilhos = _yaml(RELEASE_YML)
    assert gatilhos["push"]["tags"] == ["[0-9][0-9][0-9][0-9].[0-9][0-9]", "[0-9][0-9][0-9][0-9].[0-9][0-9].[0-9]*"]


def test_ci_roda_o_ensaio():
    dados, _ = _yaml(CI_YML)
    comandos = "\n".join(_runs(dados["jobs"]["testes"]))
    assert "tools/release.sh fixture-cache" in comandos and "tools/release.sh build" in comandos


def test_token_so_nos_passos_que_usam_o_gh():
    """Revisão do PR #45: GH_TOKEN não chega ao uv sync nem ao build."""
    dados, _ = _yaml(RELEASE_YML)
    for nome, job in dados["jobs"].items():
        assert "GH_TOKEN" not in job.get("env", {}) and "GH_REPO" not in job.get("env", {}), nome
        for passo in job["steps"]:
            usa_gh = any(c in passo.get("run", "") for c in ("fetch-cache", "tools/release.sh upload"))
            assert ("GH_TOKEN" in passo.get("env", {})) == usa_gh, passo.get("name")
            if passo.get("uses", "").startswith("actions/checkout"):
                assert passo["with"]["persist-credentials"] is False


def test_actions_fixadas_por_sha():
    texto = RELEASE_YML.read_text(encoding="utf-8")
    usos = re.findall(r"uses: (\S+)(.*)", texto)
    assert usos
    for acao, resto in usos:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", acao), acao
        assert re.fullmatch(r"\s+# v\d+\.\d+\.\d+", resto), acao


def test_job_release_sem_cache_do_uv():
    dados, _ = _yaml(RELEASE_YML)
    uv = next(p for p in dados["jobs"]["release"]["steps"] if p.get("uses", "").startswith("astral-sh/setup-uv"))
    assert uv["with"]["enable-cache"] is False


def test_upload_falha_se_nao_consegue_listar_os_assets(gh, release_pronta, tmp_path):
    """Revisão do PR #45: view falhando depois do upload não pode pular a remoção do cache em silêncio."""
    ambiente, log = gh
    r = _rodar("upload", "2026.10", _copia(release_pronta, tmp_path), **{**ambiente, "FAKE_VIEW_ASSETS_FALHA": "1"})
    assert r.returncode != 0
    assert "release upload" in log.read_text(encoding="utf-8")


def test_upload_falha_se_o_cache_continua_no_rascunho(gh, release_pronta, tmp_path):
    ambiente, _ = gh
    r = _rodar("upload", "2026.10", _copia(release_pronta, tmp_path), **{**ambiente, "FAKE_DELETE_IGNORADO": "1"})
    assert r.returncode != 0 and "source-cache.tar.gz" in r.stderr


def test_estado_com_erro_que_nao_e_ausencia_falha(gh, tmp_path):
    ambiente, _ = gh
    r = _rodar("fetch-cache", "2026.10", tmp_path / "c", **{**ambiente, "FAKE_DRAFT": "erro"})
    assert r.returncode != 0
    assert "HTTP 401: Bad credentials" in r.stderr and "rascunho" not in r.stderr
