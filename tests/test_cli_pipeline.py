"""Spec 002, R5 e R6, critérios de aceite 1, 3 e 4: fetch, ingest, build e run pela CLI."""

import csv
import json
import shutil
from pathlib import Path

import pyarrow.parquet as pq
import pytest

import adaptadores.exemplo
from namescommons.adapters import Resource
from namescommons.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
FONTES = str(FIXTURES / "sources.yaml")
ADAPTADORES = ["--sources", FONTES, "--adapters", "adaptadores"]

PT_CSV = """\
kind,name,name_key,ascii,script,count,count_type,rank,female_share,gender_basis,first_year,last_year
family,Silva,silva,silva,Latn,500,births,1,,0,2020,2020
family,Santos,santos,santos,Latn,300,births,2,,0,2020,2020
given,João,joão,joao,Latn,200,births,1,0.000000,200,2020,2021
given,Maria,maria,maria,Latn,200,births,1,1.000000,200,2020,2021
given,Ana Clara,ana clara,ana clara,Latn,15,births,2,1.000000,15,2021,2021
given,José,josé,jose,Latn,15,births,2,0.000000,15,2021,2021
"""


@pytest.fixture
def exemplo_no_servidor(servidor, monkeypatch):
    for nome in ("primeiros.csv", "sobrenomes.csv"):
        servidor.arquivos[f"/exemplo/{nome}"] = (FIXTURES / "exemplo" / nome).read_bytes()
    monkeypatch.setattr(adaptadores.exemplo, "RESOURCES", [
        Resource(servidor.url("/exemplo/primeiros.csv"), "primeiros.csv"),
        Resource(servidor.url("/exemplo/sobrenomes.csv"), "sobrenomes.csv"),
    ])
    return servidor


@pytest.fixture
def cache_das_fixtures(tmp_path):
    shutil.copytree(FIXTURES / "exemplo", tmp_path / "cache" / "exemplo")
    return tmp_path / "cache"


def test_criterio_1_fetch_ingest_build(exemplo_no_servidor, tmp_path, capsys):
    cache = str(tmp_path / "cache")
    obs = tmp_path / "trabalho" / "observations.parquet"
    assert main(["fetch", "--cache", cache, *ADAPTADORES]) == 0
    assert sorted(exemplo_no_servidor.caminhos()) == ["/exemplo/primeiros.csv", "/exemplo/sobrenomes.csv"]
    assert main(["ingest", "--out", str(obs), "--offline", "--cache", cache, *ADAPTADORES]) == 0
    assert "OK: 8 observações de 1 fonte" in capsys.readouterr().out
    dist = tmp_path / "dist"
    assert main(["build", str(obs), "--sources", FONTES, "--out", str(dist), "--release", "2026.10"]) == 0
    assert (dist / "by_country" / "PT.csv").read_text(encoding="utf-8") == PT_CSV
    given = {l["name_key"]: l for l in csv.DictReader(open(dist / "given_names.csv", encoding="utf-8"))}
    assert list(given) == ["ana clara", "josé", "joão", "maria"]
    assert json.loads(given["maria"]["countries"]) == [
        {"country": "PT", "count": 200, "count_type": "births", "rank": 1},
    ]
    assert (given["maria"]["female_share"], given["maria"]["sources"]) == ("1.000000", '["exemplo"]')
    family = list(csv.DictReader(open(dist / "family_names.csv", encoding="utf-8")))
    assert [(l["name"], l["female_share"], l["gender_basis"]) for l in family] == [
        ("Santos", "", "0"), ("Silva", "", "0"),
    ]
    manifest = json.loads((dist / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sources"] == [{"id": "exemplo", "license": "CC0-1.0", "retrieved": "2026-10-01"}]


def test_criterio_3_fetch_sem_refresh_nao_repete_requisicao(exemplo_no_servidor, tmp_path):
    cache = str(tmp_path / "cache")
    assert main(["fetch", "exemplo", "--cache", cache, *ADAPTADORES]) == 0
    assert main(["fetch", "exemplo", "--cache", cache, *ADAPTADORES]) == 0
    assert len(exemplo_no_servidor.requisicoes) == 2
    assert main(["fetch", "exemplo", "--refresh", "--cache", cache, *ADAPTADORES]) == 0
    assert len(exemplo_no_servidor.requisicoes) == 4


def test_criterio_3_offline_sem_cache_falha_com_mensagem(tmp_path, capsys):
    out = tmp_path / "dist"
    args = ["run", "--offline", "--out", str(out), "--release", "2026.10", "--cache", str(tmp_path / "vazio")]
    assert main([*args, *ADAPTADORES]) == 1
    err = capsys.readouterr().err
    assert "fonte 'exemplo'" in err and "missing from the cache" in err
    assert "Traceback" not in err
    assert not out.exists()


def test_criterio_4_dois_runs_offline_identicos(cache_das_fixtures, tmp_path):
    saidas = []
    for n in (1, 2):
        out = tmp_path / f"dist{n}"
        args = ["run", "--offline", "--out", str(out), "--release", "2026.10", "--cache", str(cache_das_fixtures)]
        assert main([*args, *ADAPTADORES]) == 0
        saidas.append(out)
    a, b = saidas
    csvs = sorted(p.relative_to(a).as_posix() for p in a.rglob("*.csv"))
    assert csvs == ["by_country/PT.csv", "family_names.csv", "given_names.csv"]
    for nome in csvs:
        assert (a / nome).read_bytes() == (b / nome).read_bytes(), nome
    for nome in ("observations.parquet", "given_names.parquet", "family_names.parquet"):
        assert pq.read_table(a / nome).equals(pq.read_table(b / nome)), nome
    assert (a / "by_country" / "PT.csv").read_text(encoding="utf-8") == PT_CSV


def test_run_com_rede_baixa_e_gera_a_release(exemplo_no_servidor, tmp_path, capsys):
    out = tmp_path / "dist"
    args = ["run", "--out", str(out), "--release", "2026.10", "--cache", str(tmp_path / "cache")]
    assert main([*args, *ADAPTADORES]) == 0
    assert (out / "by_country" / "PT.csv").read_text(encoding="utf-8") == PT_CSV
    assert "OK: 8 observações, 1 país" in capsys.readouterr().out
    assert len(exemplo_no_servidor.requisicoes) == 2


def test_run_refresh_baixa_de_novo(exemplo_no_servidor, cache_das_fixtures, tmp_path):
    args = ["run", "--refresh", "--out", str(tmp_path / "dist"), "--release", "2026.10",
            "--cache", str(cache_das_fixtures)]
    assert main([*args, *ADAPTADORES]) == 0
    assert len(exemplo_no_servidor.requisicoes) == 2


def test_run_offline_e_refresh_sao_incompativeis(tmp_path, capsys):
    args = ["run", "--offline", "--refresh", "--out", str(tmp_path / "d"), "--release", "2026.10"]
    assert main([*args, *ADAPTADORES]) == 1
    assert "incompatíveis" in capsys.readouterr().err


def test_run_valida_release_antes_de_baixar(exemplo_no_servidor, tmp_path, capsys):
    args = ["run", "--out", str(tmp_path / "d"), "--release", "2026.13", "--cache", str(tmp_path / "c")]
    assert main([*args, *ADAPTADORES]) == 1
    assert "AAAA.MM" in capsys.readouterr().err
    assert exemplo_no_servidor.requisicoes == []


def test_run_recusa_out_nao_vazio(cache_das_fixtures, tmp_path, capsys):
    out = tmp_path / "dist"
    out.mkdir()
    (out / "guardado.txt").write_text("x", encoding="utf-8")
    args = ["run", "--offline", "--out", str(out), "--release", "2026.10", "--cache", str(cache_das_fixtures)]
    assert main([*args, *ADAPTADORES]) == 1
    assert "não está vazio" in capsys.readouterr().err


def test_fetch_com_falha_nomeia_a_fonte(exemplo_no_servidor, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("datasettool.sources.cache.BACKOFF", 0)
    del exemplo_no_servidor.arquivos["/exemplo/primeiros.csv"]
    assert main(["fetch", "--cache", str(tmp_path / "cache"), *ADAPTADORES]) == 1
    err = capsys.readouterr().err
    assert "fonte 'exemplo'" in err and "404" in err
    assert "Traceback" not in err


def test_ingest_com_arquivo_corrompido_falha_sem_saida(cache_das_fixtures, tmp_path, capsys):
    (cache_das_fixtures / "exemplo" / "primeiros.csv").write_text("cabecalho,errado\n1,2\n", encoding="utf-8")
    obs = tmp_path / "observations.parquet"
    args = ["ingest", "--out", str(obs), "--offline", "--cache", str(cache_das_fixtures)]
    assert main([*args, *ADAPTADORES]) == 1
    err = capsys.readouterr().err
    assert "fonte 'exemplo': KeyError: 'nome'" in err
    assert not obs.exists()


def test_ingest_com_fonte_sem_registros_falha_sem_saida(tmp_path, capsys):
    cache = tmp_path / "cache"
    (cache / "exemplo").mkdir(parents=True)
    for nome in ("primeiros.csv", "sobrenomes.csv"):
        (cache / "exemplo" / nome).write_text("nome,sexo,ano,quantidade\n", encoding="utf-8")
    obs = tmp_path / "observations.parquet"
    assert main(["ingest", "--out", str(obs), "--offline", "--cache", str(cache), *ADAPTADORES]) == 1
    err = capsys.readouterr().err
    assert "fonte 'exemplo': nenhum registro produzido por parse" in err
    assert not obs.exists()


def test_fonte_desconhecida_ou_manual(tmp_path, capsys):
    assert main(["fetch", "nao-existe", "--cache", str(tmp_path), *ADAPTADORES]) == 1
    assert "fonte 'nao-existe' ausente de sources.yaml" in capsys.readouterr().err
    assert main(["ingest", "manual", "--out", str(tmp_path / "o.parquet"), "--cache", str(tmp_path),
                 *ADAPTADORES]) == 1
    assert "adapter: false" in capsys.readouterr().err


def test_ajuda_lista_os_comandos(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    saida = capsys.readouterr().out
    for comando in ("fetch", "ingest", "validate", "build", "run"):
        assert comando in saida


def test_fetch_imprime_a_mensagem_de_sucesso(exemplo_no_servidor, tmp_path, capsys):
    cache = tmp_path / "cache"
    assert main(["fetch", "--cache", str(cache), *ADAPTADORES]) == 0
    assert capsys.readouterr().out == f"OK: 1 fonte em {cache}.\n"


def test_ingest_avisa_ao_sobrescrever_e_grava_de_forma_atomica(cache_das_fixtures, tmp_path, capsys):
    obs = tmp_path / "observations.parquet"
    args = ["ingest", "--out", str(obs), "--offline", "--cache", str(cache_das_fixtures), *ADAPTADORES]
    assert main(args) == 0
    assert "substituído" not in capsys.readouterr().err
    assert main(args) == 0
    assert f"aviso: {obs} já existe e será substituído" in capsys.readouterr().err
    assert sorted(p.name for p in tmp_path.iterdir() if p.name.startswith("observations")) == ["observations.parquet"]


def test_ingest_que_falha_preserva_o_arquivo_existente(cache_das_fixtures, tmp_path, capsys, monkeypatch):
    obs = tmp_path / "observations.parquet"
    obs.write_bytes(b"anterior")

    def falha(observacoes, caminho):
        caminho.write_bytes(b"parcial")
        raise OSError("disco cheio")

    class EscritorQueFalha:  # spec 005, R9.3: a escrita é em lotes, por ParquetWriter
        def __init__(self, caminho, esquema):
            self.caminho = caminho

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def write_table(self, tabela):
            falha(None, self.caminho)

    monkeypatch.setattr("namescommons.io.pq.ParquetWriter", EscritorQueFalha)
    args = ["ingest", "--out", str(obs), "--offline", "--cache", str(cache_das_fixtures), *ADAPTADORES]
    assert main(args) == 1
    assert obs.read_bytes() == b"anterior"
    assert [p.name for p in tmp_path.iterdir() if p.name != "cache"] == ["observations.parquet"]


def _parquet(cache, tmp_path):
    obs = tmp_path / "observations.parquet"
    assert main(["ingest", "--out", str(obs), "--offline", "--cache", str(cache), *ADAPTADORES]) == 0
    return obs


@pytest.mark.parametrize("existente", [False, True])
def test_build_que_falha_na_agregacao_nao_deixa_saida_parcial(
    cache_das_fixtures, tmp_path, capsys, monkeypatch, existente,
):
    from namescommons.aggregate import AggregationError

    obs = _parquet(cache_das_fixtures, tmp_path)
    out = tmp_path / "dist"
    if existente:
        out.mkdir()

    def falha(*a, **k):
        raise AggregationError("agregação impossível")

    monkeypatch.setattr("namescommons.cli.name_index", falha)
    assert main(["build", str(obs), "--out", str(out), "--release", "2026.10", "--sources", FONTES]) == 1
    assert "agregação impossível" in capsys.readouterr().err
    assert (out.is_dir() and list(out.iterdir()) == []) if existente else not out.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(["cache", "observations.parquet"] + (["dist"] if existente else []))


def test_build_em_diretorio_vazio_existente_funciona(cache_das_fixtures, tmp_path):
    obs = _parquet(cache_das_fixtures, tmp_path)
    out = tmp_path / "dist"
    out.mkdir()
    assert main(["build", str(obs), "--out", str(out), "--release", "2026.10", "--sources", FONTES]) == 0
    assert (out / "manifest.json").is_file() and (out / "by_country" / "PT.csv").is_file()
    assert [p.name for p in tmp_path.iterdir() if p.name.startswith("dist")] == ["dist"]
