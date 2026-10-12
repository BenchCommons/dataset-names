"""Spec 002, R1 e R5: transformação de RawRecord em Observation, fetch e ingest por fonte."""

import random
import shutil
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

import adaptadores.exemplo
from namescommons.adapters import RawRecord, Resource
from namescommons.pipeline import (
    PipelineError, RecordError, fetch_sources, ingest_sources, select_sources, to_observations,
)
from namescommons.sources import load_sources, parse_sources

FIXTURES = Path(__file__).parent / "fixtures"


def _fonte(**campos):
    base = {"id": "pt-x", "name": "x", "url": "https://x.example", "license": "CC0-1.0",
            "attribution": "x", "country": "PT", "count_type": "births", "primary": True,
            "suppression": None, "retrieved": date(2026, 1, 1)}
    return next(iter(parse_sources([{**base, **campos}]).values()))


@pytest.fixture
def fontes_exemplo():
    return load_sources(FIXTURES / "sources.yaml")


def _cache_das_fixtures(destino: Path) -> Path:
    shutil.copytree(FIXTURES / "exemplo", destino / "exemplo")
    return destino


def _campos(obs):
    return [(o.name, o.kind, o.country, o.gender, o.year, o.count) for o in obs]


# R1.1 a R1.5 -------------------------------------------------------------------------------------

@pytest.mark.parametrize("vazio", ["", "   ", None])
def test_r1_1_country_e_gender_vazios_viram_none(vazio):
    fonte = _fonte(country=None, count_type="attested")
    [o] = to_observations([RawRecord("Maria", "given", country=vazio, gender=vazio)], fonte)
    assert (o.country, o.gender) == (None, None)


def test_r1_1_espacos_em_volta_sao_removidos():
    [o] = to_observations([RawRecord("Maria", "given", " PT ", " F ", 2020, 1)], _fonte())
    assert (o.country, o.gender) == ("PT", "F")


def test_r1_2_count_type_e_source_id_vem_da_fonte():
    [o] = to_observations([RawRecord("Maria", "given", "PT", "F", 2020, 1)], _fonte(count_type="births"))
    assert (o.count_type, o.source_id) == ("births", "pt-x")


def test_r1_3_fonte_de_caixa_uniforme_capitaliza():
    obs = to_observations([RawRecord("DJ", "given", "PT", "M", 2020, 3)], _fonte(uniform_case=True))
    assert obs[0].name == "Dj"


def test_r1_3_fonte_de_caixa_mista_preserva():
    obs = to_observations([RawRecord("DJ", "given", "PT", "M", 2020, 3),
                           RawRecord("MARIA", "given", "PT", "F", 2020, 3)], _fonte(uniform_case=False))
    assert sorted(o.name for o in obs) == ["DJ", "MARIA"]


def test_r1_4_repetidos_sao_somados():
    obs = to_observations([
        RawRecord("MARIA", "given", "PT", "F", 2020, 100),
        RawRecord("Maria", "given", "PT", "F", 2020, 20),
        RawRecord("MARIA", "given", "PT", "F", 2021, 80),
    ], _fonte(uniform_case=True))
    assert _campos(obs) == [("Maria", "given", "PT", "F", 2020, 120), ("Maria", "given", "PT", "F", 2021, 80)]


def test_r1_4_repetidos_sem_contagem_viram_uma_linha():
    fonte = _fonte(country=None, count_type="attested")
    obs = to_observations([RawRecord("Maria", "given"), RawRecord("Maria", "given")], fonte)
    assert _campos(obs) == [("Maria", "given", None, None, None, None)]


def test_r1_4_repetidos_com_e_sem_contagem_sao_recusados():
    # Desde a spec 003 (R2.3), count vazio numa fonte births é recusado já no registro.
    with pytest.raises(RecordError, match="registro 2: count vazio numa fonte 'births'"):
        to_observations([RawRecord("Maria", "given", "PT", "F", 2020, 1),
                         RawRecord("Maria", "given", "PT", "F", 2020, None)], _fonte())


def test_r1_5_total_e_divisao_por_genero_juntos_sao_recusados():
    with pytest.raises(RecordError, match="R1.5.*'maria', 'given', 'PT', 2020"):
        to_observations([
            RawRecord("Maria", "given", "PT", "F", 2020, 100),
            RawRecord("Maria", "given", "PT", "", 2020, 100),
        ], _fonte())


def test_r1_5_anos_diferentes_nao_conflitam():
    obs = to_observations([
        RawRecord("Maria", "given", "PT", "F", 2020, 100),
        RawRecord("Maria", "given", "PT", None, 2021, 100),
    ], _fonte())
    assert len(obs) == 2


def test_saida_independe_da_ordem_dos_registros():
    registros = [RawRecord(n, k, "PT", g, a, 1) for n in ("Ana", "Bia", "Rui") for k in ("given", "family")
                 for g in ("F", "M") for a in (2020, 2021)]
    embaralhados = registros[:]
    random.Random(4).shuffle(embaralhados)
    assert to_observations(embaralhados, _fonte()) == to_observations(registros, _fonte())


# Seleção de fontes -----------------------------------------------------------------------------

def test_sem_ids_seleciona_as_fontes_com_adaptador(fontes_exemplo):
    assert [f.id for f in select_sources(fontes_exemplo, [])] == ["exemplo"]


def test_id_desconhecido(fontes_exemplo):
    with pytest.raises(PipelineError, match="fonte 'nao-existe' ausente de sources.yaml"):
        select_sources(fontes_exemplo, ["nao-existe"])


def test_id_sem_adaptador(fontes_exemplo):
    with pytest.raises(PipelineError, match="fonte 'manual' tem adapter: false"):
        select_sources(fontes_exemplo, ["manual"])


def test_nenhuma_fonte_com_adaptador():
    with pytest.raises(PipelineError, match="nenhuma fonte com adaptador"):
        select_sources({}, [])


# fetch e ingest -------------------------------------------------------------------------------

def test_ingest_offline_sobre_o_cache(fontes_exemplo, tmp_path):
    cache = _cache_das_fixtures(tmp_path)
    obs = ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, cache,
                         offline=True, adapters="adaptadores")
    assert _campos(obs) == [
        ("Santos", "family", "PT", None, 2020, 300),
        ("Silva", "family", "PT", None, 2020, 500),
        ("Ana Clara", "given", "PT", "F", 2021, 15),
        ("José", "given", "PT", "M", 2021, 15),
        ("João", "given", "PT", "M", 2020, 90),
        ("João", "given", "PT", "M", 2021, 110),
        ("Maria", "given", "PT", "F", 2020, 120),
        ("Maria", "given", "PT", "F", 2021, 80),
    ]
    assert {(o.count_type, o.source_id) for o in obs} == {("births", "exemplo")}


def test_ingest_offline_sem_cache_nomeia_a_fonte(fontes_exemplo, tmp_path):
    with pytest.raises(PipelineError, match="fonte 'exemplo': .*primeiros.csv ausente do cache"):
        ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, tmp_path,
                       offline=True, adapters="adaptadores")


def test_ingest_arquivo_corrompido_nomeia_a_fonte_e_a_causa(fontes_exemplo, tmp_path):
    cache = _cache_das_fixtures(tmp_path)
    (cache / "exemplo" / "sobrenomes.csv").write_text("nome,sexo,ano,quantidade\nSILVA,,2020,muitos\n",
                                                      encoding="utf-8")
    with pytest.raises(PipelineError, match="fonte 'exemplo': ValueError: .*'muitos'"):
        ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, cache,
                       offline=True, adapters="adaptadores")


def test_ingest_recusa_violacao_de_r1_5(fontes_exemplo, tmp_path):
    cache = _cache_das_fixtures(tmp_path)
    with open(cache / "exemplo" / "sobrenomes.csv", "a", encoding="utf-8") as fh:
        fh.write("SILVA,F,2020,200\n")
    with pytest.raises(PipelineError, match="fonte 'exemplo': R1.5"):
        ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, cache,
                       offline=True, adapters="adaptadores")


def test_ingest_recusa_fonte_sem_registros(fontes_exemplo, tmp_path):
    for nome in ("primeiros.csv", "sobrenomes.csv"):
        (tmp_path / "exemplo").mkdir(exist_ok=True)
        (tmp_path / "exemplo" / nome).write_text("nome,sexo,ano,quantidade\n", encoding="utf-8")
    with pytest.raises(PipelineError, match="^fonte 'exemplo': nenhum registro produzido por parse$"):
        ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, tmp_path,
                       offline=True, adapters="adaptadores")


def test_ingest_valida_contra_a_fonte(fontes_exemplo, tmp_path):
    cache = _cache_das_fixtures(tmp_path)
    fontes = {**fontes_exemplo, "exemplo": replace(fontes_exemplo["exemplo"], country="BR")}
    erro = "(?s)fonte 'exemplo': .*erro\\(s\\) de validação.*diverge da fonte"
    with pytest.raises(PipelineError, match=erro):
        ingest_sources(select_sources(fontes, []), fontes, cache, offline=True, adapters="adaptadores")


@pytest.fixture
def exemplo_no_servidor(servidor, monkeypatch):
    for nome in ("primeiros.csv", "sobrenomes.csv"):
        servidor.arquivos[f"/exemplo/{nome}"] = (FIXTURES / "exemplo" / nome).read_bytes()
    monkeypatch.setattr(adaptadores.exemplo, "RESOURCES", [
        Resource(servidor.url("/exemplo/primeiros.csv"), "primeiros.csv"),
        Resource(servidor.url("/exemplo/sobrenomes.csv"), "sobrenomes.csv"),
    ])
    return servidor


def test_fetch_baixa_todos_os_recursos(fontes_exemplo, exemplo_no_servidor, tmp_path):
    fetch_sources(select_sources(fontes_exemplo, []), tmp_path, adapters="adaptadores")
    for nome in ("primeiros.csv", "sobrenomes.csv"):
        assert (tmp_path / "exemplo" / nome).read_bytes() == (FIXTURES / "exemplo" / nome).read_bytes()
        assert (tmp_path / "exemplo" / f"{nome}.meta.json").is_file()


def test_fetch_com_falha_nomeia_a_fonte(fontes_exemplo, exemplo_no_servidor, tmp_path):
    del exemplo_no_servidor.arquivos["/exemplo/sobrenomes.csv"]
    with pytest.raises(PipelineError, match="fonte 'exemplo': falha ao baixar .*sobrenomes.csv.*404"):
        fetch_sources(select_sources(fontes_exemplo, []), tmp_path, adapters="adaptadores", espera=0)


def test_ingest_sem_offline_baixa_o_que_falta(fontes_exemplo, exemplo_no_servidor, tmp_path):
    obs = ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, tmp_path, adapters="adaptadores")
    assert len(obs) == 8
    assert sorted(exemplo_no_servidor.caminhos()) == ["/exemplo/primeiros.csv", "/exemplo/sobrenomes.csv"]


@pytest.mark.parametrize("campo, valor, tipo", [
    ("year", 2020.7, "float"), ("count", 5.9, "float"),
    ("year", True, "bool"), ("count", True, "bool"),
    ("year", "2020", "str"), ("count", "5", "str"),
])
def test_r1_tipo_errado_em_year_ou_count_nomeia_campo_valor_e_posicao(campo, valor, tipo):
    ok = RawRecord("Ana", "given", "PT", "F", 2020, 1)
    ruim = replace(ok, name="Maria", **{campo: valor})
    with pytest.raises(RecordError) as e:
        to_observations([ok, ruim], _fonte())
    assert str(e.value) == f"registro 2: '{campo}' deve ser inteiro, recebeu {tipo} {valor!r}"


def test_r1_name_que_nao_e_texto_nomeia_campo_e_posicao():
    with pytest.raises(RecordError, match=r"registro 1: 'name' deve ser texto, recebeu int 7"):
        to_observations([RawRecord(7, "given", "PT", "F", 2020, 1)], _fonte())


def test_r1_tipo_errado_aparece_com_o_id_da_fonte_no_ingest(tmp_path, monkeypatch):
    import adaptadores.exemplo
    monkeypatch.setattr(adaptadores.exemplo, "parse", lambda arquivos: [RawRecord("Ana", "given", "PT", "F", 2020, 5.9)])
    cache = _cache_das_fixtures(tmp_path)
    fontes = load_sources(FIXTURES / "sources.yaml")
    with pytest.raises(PipelineError, match=r"fonte 'exemplo': registro 1: 'count' deve ser inteiro, recebeu float 5.9"):
        ingest_sources([fontes["exemplo"]], fontes, cache, offline=True, adapters="adaptadores")


# Forma de exibição de registros repetidos --------------------------------------------------------

def test_r1_4_repetidos_mantem_a_forma_de_maior_peso():
    obs = to_observations([
        RawRecord("MARIA", "given", "PT", "F", 2020, 10),
        RawRecord("Maria", "given", "PT", "F", 2020, 90),
        RawRecord("MARIA", "given", "PT", "F", 2021, 5),
        RawRecord("Maria", "given", "PT", "F", 2021, 1),
    ], _fonte(uniform_case=False))
    assert _campos(obs) == [("Maria", "given", "PT", "F", 2020, 100), ("MARIA", "given", "PT", "F", 2021, 6)]


def test_r1_4_empate_de_peso_fica_com_o_primeiro_registro():
    registros = [RawRecord("MARIA", "given", "PT", "F", 2020, 10), RawRecord("Maria", "given", "PT", "F", 2020, 10)]
    assert to_observations(registros, _fonte())[0].name == "MARIA"
    assert to_observations(registros[::-1], _fonte())[0].name == "Maria"


def test_r1_4_forma_de_maior_peso_atualiza_os_campos_derivados():
    [o] = to_observations([
        RawRecord("ÁLVARO", "given", "PT", "M", 2020, 1),
        RawRecord("Álvaro", "given", "PT", "M", 2020, 9),
    ], _fonte())
    assert (o.name, o.name_key, o.ascii, o.count) == ("Álvaro", "álvaro", "alvaro", 10)


def test_kind_invalido_e_o_primeiro_erro_mesmo_com_nome_que_quebraria_a_derivacao():
    with pytest.raises(RecordError, match="registro 1: kind 'middle' inválido"):
        to_observations([RawRecord(None, "middle", "PT", "F", 2020, 1)], _fonte())


# Recusas no nível do pipeline -----------------------------------------------------------------------

def _ingest_com_registros(registros, fonte, monkeypatch, tmp_path):
    import types
    mod = types.SimpleNamespace(
        SOURCE_ID=fonte.id, RESOURCES=[Resource("https://example.org/a.csv", "a.csv")],
        parse=lambda files: iter(registros),
    )
    monkeypatch.setattr("namescommons.pipeline.load_adapter", lambda *a, **k: mod)
    (tmp_path / fonte.id).mkdir()
    (tmp_path / fonte.id / "a.csv").write_text("x", encoding="utf-8")
    return ingest_sources([fonte], {fonte.id: fonte}, tmp_path, offline=True)


def test_ingest_recusa_year_fora_do_intervalo(monkeypatch, tmp_path):
    with pytest.raises(PipelineError, match="(?s)fonte 'pt-x': .*year 1500 fora de 1800"):
        _ingest_com_registros([RawRecord("Ana", "given", "PT", "F", 1500, 1)], _fonte(), monkeypatch, tmp_path)


def test_ingest_recusa_count_type_fora_do_dominio_com_uma_so_causa(monkeypatch, tmp_path):
    fonte = replace(_fonte(), count_type="deaths")
    with pytest.raises(PipelineError) as e:
        _ingest_com_registros([RawRecord("Ana", "given", "PT", "F", 2020, 1)], fonte, monkeypatch, tmp_path)
    assert "count_type 'deaths' inválido" in str(e.value) and "diverge" not in str(e.value)
