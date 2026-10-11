import json
from dataclasses import replace

import yaml

from namesio.cli import main
from namesio.io import write_observations

from conftest import FONTES


def _preparar(tmp_path, observacoes):
    fontes = tmp_path / "sources.yaml"
    fontes.write_text(yaml.safe_dump({"sources": FONTES}, allow_unicode=True), encoding="utf-8")
    obs = tmp_path / "obs.parquet"
    write_observations(observacoes, obs)
    return obs, fontes


def test_validate_ok(observacoes, tmp_path, capsys):
    obs, fontes = _preparar(tmp_path, observacoes)
    assert main(["validate", str(obs), "--sources", str(fontes)]) == 0
    assert "16 observações válidas" in capsys.readouterr().out


def test_validate_falha_com_mensagem(observacoes, tmp_path, capsys):
    obs, fontes = _preparar(tmp_path, [replace(observacoes[0], gender="X")])
    assert main(["validate", str(obs), "--sources", str(fontes)]) == 1
    assert "gender 'X'" in capsys.readouterr().err


def test_build_gera_todas_as_saidas(observacoes, tmp_path):
    obs, fontes = _preparar(tmp_path, observacoes)
    out = tmp_path / "dist"
    assert main(["build", str(obs), "--sources", str(fontes), "--out", str(out), "--release", "2026.10"]) == 0
    arquivos = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert arquivos == [
        "by_country/BR.csv", "by_country/US.csv", "family_names.csv", "family_names.parquet",
        "given_names.csv", "given_names.parquet", "manifest.json", "observations.parquet",
    ]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["release"] == "2026.10"
    assert "manifest.json" not in manifest["files"]


def test_build_recusa_release_invalida(observacoes, tmp_path, capsys):
    obs, fontes = _preparar(tmp_path, observacoes)
    assert main(["build", str(obs), "--sources", str(fontes), "--out", str(tmp_path / "d"), "--release", "out"]) == 1
    assert "AAAA.MM" in capsys.readouterr().err
