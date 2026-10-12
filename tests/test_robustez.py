"""Spec 002, R9: robustez herdada da revisão da spec 001 (issue #2)."""

from datetime import date

import pytest

from namesio.aggregate import AggregationError, by_country, name_index
from namesio.io import read_observations, write_by_country, write_index, write_observations
from namesio.manifest import build_manifest
from namesio.schema import make_observation
from namesio.sources import parse_sources


def _fonte(id, country, count_type, primary=True):
    return {"id": id, "name": id, "url": f"https://{id}.example", "license": "CC0-1.0",
            "attribution": id, "country": country, "count_type": count_type, "primary": primary,
            "suppression": None, "retrieved": date(2026, 1, 1)}


def _nasc(nome, source_id="fr", count=1, **campos):
    return make_observation(nome, kind="given", source_id=source_id, count_type="births",
                            country="FR", year=2020, count=count, **campos)


def test_source_id_desconhecido_na_agregacao_e_erro_do_dominio():
    fontes = parse_sources([_fonte("fr", "FR", "births")])
    with pytest.raises(AggregationError, match="source_id desconhecido.*'outra'"):
        by_country([_nasc("Léa"), _nasc("Léa", source_id="outra")], fontes)


def test_source_id_desconhecido_no_manifesto_e_erro_do_dominio(tmp_path):
    fontes = parse_sources([_fonte("fr", "FR", "births")])
    with pytest.raises(ValueError, match="source_id desconhecido.*'outra'"):
        build_manifest("2026.10", tmp_path, fontes, {"fr", "outra"})


def test_escritas_criam_o_diretorio_pai(observacoes, fontes, tmp_path):
    write_observations(observacoes, tmp_path / "a" / "b" / "observations.parquet")
    indice = name_index(observacoes, by_country(observacoes, fontes), "given")
    write_index(indice, tmp_path / "c" / "g.csv", tmp_path / "d" / "g.parquet")
    assert (tmp_path / "a" / "b" / "observations.parquet").is_file()
    assert (tmp_path / "c" / "g.csv").is_file()
    assert (tmp_path / "d" / "g.parquet").is_file()


def test_manifesto_conta_registros_csv_e_nao_linhas_fisicas(tmp_path):
    (tmp_path / "x.csv").write_text('name,nota\n"Ana","linha 1\nlinha 2"\nBia,ok\n', encoding="utf-8")
    m = build_manifest("2026.10", tmp_path, {}, set())
    assert m["files"]["x.csv"]["rows"] == 2


def test_manifesto_conta_linhas_dos_indices(observacoes, fontes, tmp_path):
    paises = by_country(observacoes, fontes)
    write_index(name_index(observacoes, paises, "given"), tmp_path / "given_names.csv",
                tmp_path / "given_names.parquet")
    m = build_manifest("2026.10", tmp_path, fontes, {o.source_id for o in observacoes})
    assert m["files"]["given_names.csv"]["rows"] == 5
    assert m["files"]["given_names.parquet"]["rows"] == 5


def test_rank_denso_com_empate():
    fontes = parse_sources([_fonte("fr", "FR", "births")])
    obs = [_nasc("Léa", count=50), _nasc("Jade", count=50), _nasc("Emma", count=20), _nasc("Zoé", count=90)]
    fr = by_country(obs, fontes)["FR"]
    assert [(r.name, r.rank) for r in fr] == [("Zoé", 1), ("Jade", 2), ("Léa", 2), ("Emma", 3)]


def test_duas_fontes_primary_no_mesmo_par_e_erro():
    fontes = parse_sources([_fonte("fr", "FR", "births"), _fonte("mundo", None, "births")])
    obs = [_nasc("Léa"), _nasc("Léa", source_id="mundo")]
    with pytest.raises(AggregationError, match="sem exatamente uma primary"):
        by_country(obs, fontes)


def test_population_sem_ano():
    fontes = parse_sources([_fonte("pop", "FR", "population")])
    obs = [
        make_observation("Léa", kind="given", source_id="pop", count_type="population",
                         country="FR", gender="F", count=900),
        make_observation("Jade", kind="given", source_id="pop", count_type="population",
                         country="FR", gender="F", count=400),
    ]
    fr = by_country(obs, fontes)["FR"]
    assert [(r.name, r.count, r.rank, r.first_year, r.last_year) for r in fr] == [
        ("Léa", 900, 1, None, None), ("Jade", 400, 2, None, None),
    ]


def test_parquet_ida_e_volta_com_campos_vazios(tmp_path):
    obs = [
        make_observation("李", kind="family", source_id="wikidata", count_type="attested"),
        make_observation("Maria", kind="given", source_id="wikidata", count_type="attested",
                         country="PT"),
    ]
    assert (obs[0].country, obs[0].gender, obs[0].year, obs[0].count, obs[0].ascii) == (None, None, None, None, "")
    p = tmp_path / "observations.parquet"
    write_observations(obs, p)
    assert read_observations(p) == obs


def test_nome_de_exibicao_no_indice(observacoes, fontes):
    indice = name_index(observacoes, by_country(observacoes, fontes), "given")
    maria = next(r for r in indice if r.name_key == "maria")
    assert maria.name == "Maria"


def test_csv_por_pais_sem_contagem(observacoes, fontes, tmp_path):
    write_by_country(by_country(observacoes, fontes), tmp_path / "x" / "by_country")
    linhas = (tmp_path / "x" / "by_country" / "US.csv").read_text(encoding="utf-8").splitlines()
    assert linhas[-1] == "given,Ana Clara,ana clara,ana clara,Latn,,attested,,,0,,"
