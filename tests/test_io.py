import csv
import json
from dataclasses import fields

import pyarrow.parquet as pq
import pytest

from namescommons.aggregate import by_country, name_index
from namescommons.io import OBSERVATION_SCHEMA, read_observations, write_by_country, write_index, write_observations
from namescommons.manifest import build_manifest
from namescommons.schema import Observation


def test_schema_de_observacoes_acompanha_a_dataclass():
    assert [f.name for f in fields(Observation)] == OBSERVATION_SCHEMA.names


def test_observacoes_ida_e_volta(observacoes, tmp_path):
    p = tmp_path / "observations.parquet"
    write_observations(observacoes, p)
    assert read_observations(p) == observacoes


def test_indice_csv_e_parquet(observacoes, fontes, tmp_path):
    indice = name_index(observacoes, by_country(observacoes, fontes), "given")
    write_index(indice, tmp_path / "g.csv", tmp_path / "g.parquet")
    linhas = list(csv.DictReader(open(tmp_path / "g.csv", encoding="utf-8")))
    maria = next(l for l in linhas if l["name_key"] == "maria")
    assert json.loads(maria["countries"])[0] == {"country": "BR", "count": 12000, "count_type": "population", "rank": 1}
    assert json.loads(maria["sources"])[-1] == "wikidata"
    assert maria["female_share"] == "0.999589"
    assert next(l for l in linhas if l["name_key"] == "мария")["female_share"] == ""
    tabela = pq.read_table(tmp_path / "g.parquet").to_pylist()
    assert [t["name_key"] for t in tabela] == [l["name_key"] for l in linhas]
    assert next(t for t in tabela if t["name_key"] == "maria")["countries"][1]["count"] == 155


def test_by_country_csv(observacoes, fontes, tmp_path):
    write_by_country(by_country(observacoes, fontes), tmp_path / "by_country")
    assert sorted(p.name for p in (tmp_path / "by_country").iterdir()) == ["BR.csv", "US.csv"]
    us = list(csv.DictReader(open(tmp_path / "by_country" / "US.csv", encoding="utf-8")))
    assert us[0] == {
        "kind": "given", "name": "James", "name_key": "james", "ascii": "james", "script": "Latn",
        "count": "200", "count_type": "births", "rank": "1", "female_share": "0.000000",
        "gender_basis": "200", "first_year": "2021", "last_year": "2021",
    }
    assert "female" not in us[0]


def test_manifest(observacoes, fontes, tmp_path):
    write_by_country(by_country(observacoes, fontes), tmp_path / "by_country")
    write_observations(observacoes, tmp_path / "observations.parquet")
    m = build_manifest("2026.10", tmp_path, fontes, {o.source_id for o in observacoes})
    assert m["schema_version"] == "1.0.0"
    assert [s["id"] for s in m["sources"]] == ["br-ibge-censo", "us-births-b", "us-ssa", "wikidata"]
    assert m["files"]["observations.parquet"]["rows"] == len(observacoes)
    assert m["files"]["by_country/US.csv"]["rows"] == 4
    assert len(m["files"]["by_country/BR.csv"]["sha256"]) == 64


@pytest.mark.parametrize("release", ["2026-10", "2026.13", "26.10", "2026.10.0", "2026.1"])
def test_release_fora_do_formato(release, fontes, tmp_path):
    with pytest.raises(ValueError, match="AAAA.MM"):
        build_manifest(release, tmp_path, fontes, set())
