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
    assert _bench().total_de_observacoes(1000) == 960
    assert _bench().total_de_observacoes(10) == 120


def test_observacao_sem_dicionario_por_instancia(observacoes):
    assert not hasattr(observacoes[0], "__dict__")


def test_leitura_compartilha_textos_repetidos(observacoes, tmp_path):
    p = tmp_path / "observations.parquet"
    write_observations(observacoes, p)
    lidas = read_observations(p)
    assert lidas == observacoes
    assert lidas[0].source_id is lidas[1].source_id
    assert lidas[0].name is lidas[1].name


def test_nomes_sao_distintos_ate_o_limite_de_3_2_milhoes():
    bench = _bench()
    assert bench.NOMES_POSSIVEIS == 3_200_000
    nomes = {bench._nome(i) for i in range(200_000)}
    assert len(nomes) == 200_000
    # com 3 milhões de observações há 25 mil nomes, não os ~5 mil do protótipo
    assert bench.total_de_observacoes(3_000_000) // bench.BLOCO >= 25_000


def test_dir_ja_usado_e_recusado_com_mensagem(tmp_path, capsys):
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "restos").write_text("x", encoding="utf-8")
    assert _bench().main(["--observacoes", "120", "--dir", str(tmp_path / "b")]) == 2
    assert "já contém arquivos" in capsys.readouterr().err
    assert (tmp_path / "b" / "restos").read_text(encoding="utf-8") == "x"


def test_falha_numa_etapa_imprime_a_linha_r8_e_o_diretorio(tmp_path, capsys, monkeypatch):
    bench = _bench()
    monkeypatch.setattr(bench, "namescommons", lambda argv: 1)
    assert bench.main(["--observacoes", "120", "--dir", str(tmp_path / "b")]) == 1
    saida = capsys.readouterr().out
    assert saida.startswith("R8: FALHA no ingest (código 1)") and str(tmp_path / "b") in saida


def test_escrita_em_lotes_relê_as_mesmas_observacoes(observacoes, tmp_path, monkeypatch):
    """Spec 005, R9.3 (issue #31): write_observations grava em lotes."""
    import pyarrow.parquet as pq
    import namescommons.io as io_
    monkeypatch.setattr(io_, "LOTE_DE_ESCRITA", 2)
    p = tmp_path / "observations.parquet"
    write_observations(observacoes, p)
    assert read_observations(p) == observacoes
    assert pq.ParquetFile(p).metadata.num_row_groups == (len(observacoes) + 1) // 2


def test_escrita_sem_observacoes_mantem_o_esquema(tmp_path):
    import pyarrow.parquet as pq
    from namescommons.io import OBSERVATION_SCHEMA
    p = tmp_path / "observations.parquet"
    write_observations([], p)
    assert pq.read_table(p).schema.equals(OBSERVATION_SCHEMA) and read_observations(p) == []


def test_bench_com_wikidata(tmp_path, capsys):
    """Spec 005, R9.4 (issue #31): o Wikidata entra na medição com as ligações."""
    registro = tmp_path / "r8.json"
    assert _bench().main(["--observacoes", "120", "--dir", str(tmp_path / "b"), "--registro", str(registro),
                          "--wikidata", str(RAIZ / "tests" / "fixtures" / "wikidata")]) == 0
    saida = capsys.readouterr().out
    assert "120 observações sintéticas mais o Wikidata; ingest " in saida and "dentro dos limites" in saida
    assert (tmp_path / "b" / "dist" / "variant_links.parquet").is_file()
    dados = json.loads(registro.read_text(encoding="utf-8"))
    assert dados["observacoes"] == 120 and dados["wikidata"] is True
