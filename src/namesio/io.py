"""Leitura e escrita das tabelas em Parquet e CSV."""

import csv
import json
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from namesio.aggregate import CountryRow, IndexRow
from namesio.schema import Observation

OBSERVATION_SCHEMA = pa.schema([
    ("name", pa.string()), ("name_key", pa.string()), ("ascii", pa.string()),
    ("script", pa.string()), ("kind", pa.string()), ("country", pa.string()),
    ("gender", pa.string()), ("year", pa.int32()), ("count", pa.int64()),
    ("count_type", pa.string()), ("source_id", pa.string()),
])

INDEX_SCHEMA = pa.schema([
    ("name", pa.string()), ("name_key", pa.string()), ("ascii", pa.string()),
    ("script", pa.string()), ("country_count", pa.int32()),
    ("countries", pa.list_(pa.struct([
        ("country", pa.string()), ("count", pa.int64()),
        ("count_type", pa.string()), ("rank", pa.int32()),
    ]))),
    ("female_share", pa.float64()), ("gender_basis", pa.int64()),
    ("group_id", pa.string()), ("sources", pa.list_(pa.string())),
])

INDEX_CSV_COLUMNS = [f.name for f in INDEX_SCHEMA]
COUNTRY_CSV_COLUMNS = [
    "kind", "name", "name_key", "ascii", "script", "count", "count_type", "rank",
    "female_share", "gender_basis", "first_year", "last_year",
]


def write_observations(observations: list[Observation], path: Path) -> None:
    tabela = pa.Table.from_pylist([asdict(o) for o in observations], schema=OBSERVATION_SCHEMA)
    pq.write_table(tabela, path)


def read_observations(path: Path) -> list[Observation]:
    tabela = pq.read_table(path).select(OBSERVATION_SCHEMA.names).cast(OBSERVATION_SCHEMA)
    return [Observation(**linha) for linha in tabela.to_pylist()]


def _celula(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor:.6f}"
    return str(valor)


def _index_dict(r: IndexRow) -> dict:
    return {
        **asdict(r),
        "countries": [asdict(c) for c in r.countries],
        "sources": list(r.sources),
    }


def write_index(rows: list[IndexRow], csv_path: Path, parquet_path: Path) -> None:
    dados = [_index_dict(r) for r in rows]
    pq.write_table(pa.Table.from_pylist(dados, schema=INDEX_SCHEMA), parquet_path)
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(INDEX_CSV_COLUMNS)
        for d in dados:
            w.writerow([
                json.dumps(d[c], ensure_ascii=False, separators=(",", ":"))
                if c in ("countries", "sources") else _celula(d[c])
                for c in INDEX_CSV_COLUMNS
            ])


def write_by_country(rows_by_country: dict[str, list[CountryRow]], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for pais, rows in rows_by_country.items():
        with open(directory / f"{pais}.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(COUNTRY_CSV_COLUMNS)
            for r in rows:
                w.writerow([_celula(getattr(r, c)) for c in COUNTRY_CSV_COLUMNS])
