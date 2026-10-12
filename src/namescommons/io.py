"""Leitura e escrita das tabelas em Parquet e CSV."""

import csv
import json
import os
from dataclasses import asdict, fields
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from namescommons.aggregate import CountryRow, IndexRow
from namescommons.links import VariantLink
from namescommons.schema import Observation

OBSERVATION_SCHEMA = pa.schema([
    ("name", pa.string()), ("name_key", pa.string()), ("ascii", pa.string()),
    ("script", pa.string()), ("kind", pa.string()), ("country", pa.string()),
    ("gender", pa.string()), ("year", pa.int32()), ("count", pa.int64()),
    ("count_type", pa.string()), ("source_id", pa.string()),
])

# read_observations constrói Observation por posição (R8): a ordem precisa coincidir.
assert [f.name for f in fields(Observation)] == OBSERVATION_SCHEMA.names, "OBSERVATION_SCHEMA fora de ordem"

# Spec 004, R4.2: tabela variant_links, na ordem dos campos de VariantLink.
LINK_SCHEMA = pa.schema([(f.name, pa.string()) for f in fields(VariantLink)])

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
    # Colunar: evita um dicionário por observação (R8, spec 002).
    colunas = {campo: [getattr(o, campo) for o in observations] for campo in OBSERVATION_SCHEMA.names}
    tabela = pa.Table.from_pydict(colunas, schema=OBSERVATION_SCHEMA)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Grava ao lado e troca por rename: uma falha não deixa arquivo parcial nem apaga o anterior.
    temporario = path.with_name(path.name + ".part")
    try:
        pq.write_table(tabela, temporario)
        os.replace(temporario, path)
    finally:
        temporario.unlink(missing_ok=True)


def _valores(coluna: pa.ChunkedArray) -> list:
    """Valores Python da coluna; textos repetidos compartilham o mesmo objeto."""
    if not pa.types.is_string(coluna.type):
        return coluna.to_pylist()
    codificada = coluna.combine_chunks().dictionary_encode()
    textos = codificada.dictionary.to_pylist()
    return [None if i is None else textos[i] for i in codificada.indices.to_pylist()]


def read_observations(path: Path) -> list[Observation]:
    tabela = pq.read_table(path).select(OBSERVATION_SCHEMA.names).cast(OBSERVATION_SCHEMA)
    colunas = [_valores(tabela.column(campo)) for campo in OBSERVATION_SCHEMA.names]
    return [Observation(*valores) for valores in zip(*colunas)]


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
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
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


def write_links(links: list[VariantLink], path: Path) -> None:
    colunas = {campo: [getattr(v, campo) for v in links] for campo in LINK_SCHEMA.names}
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pydict(colunas, schema=LINK_SCHEMA), path)


def read_links(path: Path) -> list[VariantLink]:
    tabela = pq.read_table(path).select(LINK_SCHEMA.names).cast(LINK_SCHEMA)
    colunas = [_valores(tabela.column(campo)) for campo in LINK_SCHEMA.names]
    return [VariantLink(*valores) for valores in zip(*colunas)]
