import json
from dataclasses import replace

import pyarrow as pa
import pyarrow.parquet as pq
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


def test_validate_singular(observacoes, tmp_path, capsys):
    obs, fontes = _preparar(tmp_path, observacoes[:1])
    assert main(["validate", str(obs), "--sources", str(fontes)]) == 0
    assert "OK: 1 observação válida." in capsys.readouterr().out


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


def test_build_release_invalida_nao_cria_saida(observacoes, tmp_path, capsys):
    obs, fontes = _preparar(tmp_path, observacoes)
    out = tmp_path / "d"
    assert main(["build", str(obs), "--sources", str(fontes), "--out", str(out), "--release", "2026.13"]) == 1
    assert "AAAA.MM" in capsys.readouterr().err
    assert not out.exists()


def test_arquivo_ausente_retorna_1_sem_traceback(tmp_path, capsys):
    fontes = tmp_path / "sources.yaml"
    fontes.write_text(yaml.safe_dump({"sources": FONTES}, allow_unicode=True), encoding="utf-8")
    assert main(["validate", str(tmp_path / "nao_existe.parquet"), "--sources", str(fontes)]) == 1
    err = capsys.readouterr().err
    assert "arquivo não encontrado" in err and "nao_existe.parquet" in err
    assert "Traceback" not in err


def test_parquet_corrompido_retorna_1(tmp_path, capsys):
    fontes = tmp_path / "sources.yaml"
    fontes.write_text(yaml.safe_dump({"sources": FONTES}, allow_unicode=True), encoding="utf-8")
    obs = tmp_path / "obs.parquet"
    obs.write_text("isto não é parquet", encoding="utf-8")
    assert main(["validate", str(obs), "--sources", str(fontes)]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_parquet_com_colunas_erradas_retorna_1(tmp_path, capsys):
    fontes = tmp_path / "sources.yaml"
    fontes.write_text(yaml.safe_dump({"sources": FONTES}, allow_unicode=True), encoding="utf-8")
    obs = tmp_path / "obs.parquet"
    pq.write_table(pa.table({"coluna_estranha": ["x"]}), obs)
    assert main(["validate", str(obs), "--sources", str(fontes)]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_build_recusa_out_nao_vazio_sem_tocar_nos_arquivos(observacoes, tmp_path, capsys):
    obs, fontes = _preparar(tmp_path, observacoes)
    out = tmp_path / "dist"
    out.mkdir()
    existente = out / "guardado.txt"
    existente.write_text("não apagar", encoding="utf-8")
    assert main(["build", str(obs), "--sources", str(fontes), "--out", str(out), "--release", "2026.10"]) == 1
    assert "não está vazio" in capsys.readouterr().err
    assert sorted(p.name for p in out.iterdir()) == ["guardado.txt"]
    assert existente.read_text(encoding="utf-8") == "não apagar"


def test_parquet_com_tipo_de_coluna_errado_retorna_1(observacoes, tmp_path, capsys):
    fontes = tmp_path / "sources.yaml"
    fontes.write_text(yaml.safe_dump({"sources": FONTES}, allow_unicode=True), encoding="utf-8")
    obs = tmp_path / "obs.parquet"
    write_observations(observacoes, obs)
    tabela = pq.read_table(obs)
    i = tabela.schema.get_field_index("count")
    pq.write_table(tabela.set_column(i, "count", pa.array(["muitos"] * tabela.num_rows)), obs)
    assert main(["validate", str(obs), "--sources", str(fontes)]) == 1
    err = capsys.readouterr().err
    assert err.strip()
    assert "Traceback" not in err
