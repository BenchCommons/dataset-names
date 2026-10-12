"""Spec 002, R8: o script de medição roda de ponta a ponta, e as observações ocupam pouca memória."""

import importlib.util
import json
from pathlib import Path

from namescommons.io import read_observations, write_observations

RAIZ = Path(__file__).resolve().parent.parent


def _bench():
    spec = importlib.util.spec_from_file_location("bench_pipeline", RAIZ / "tools" / "bench_pipeline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bench_com_poucas_observacoes(tmp_path, capsys):
    registro = tmp_path / "r8.json"
    assert _bench().main(["--observacoes", "1200", "--dir", str(tmp_path / "b"), "--registro", str(registro)]) == 0
    saida = capsys.readouterr().out
    assert "1200 observações" in saida and "dentro dos limites" in saida
    dados = json.loads(registro.read_text(encoding="utf-8"))
    assert dados["observacoes"] == 1200
    assert dados["ingest_s"] >= 0 and dados["build_s"] >= 0 and dados["memoria_pico_mb"] > 0
    assert (tmp_path / "b" / "dist" / "given_names.csv").is_file()


def test_numero_de_observacoes_e_multiplo_do_bloco(tmp_path):
    assert _bench().total_de_observacoes(3_000_000) == 3_000_000
    assert _bench().total_de_observacoes(1000) == 600


def test_observacao_sem_dicionario_por_instancia(observacoes):
    assert not hasattr(observacoes[0], "__dict__")


def test_leitura_compartilha_textos_repetidos(observacoes, tmp_path):
    p = tmp_path / "observations.parquet"
    write_observations(observacoes, p)
    lidas = read_observations(p)
    assert lidas == observacoes
    assert lidas[0].source_id is lidas[1].source_id
    assert lidas[0].name is lidas[1].name
