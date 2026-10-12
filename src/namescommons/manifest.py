"""manifest.json de uma release (spec 001, R5).

O formato da release, schema_version e a lista sources são daqui; o SHA-256 e a contagem de
registros de cada arquivo vêm de datasettool.files (spec 007, R3.4).
"""

import re
from pathlib import Path

import pyarrow.parquet as pq
from datasettool.files import count_csv_records, describe_files

from namescommons.schema import SCHEMA_VERSION
from namescommons.sources import Source

RELEASE = re.compile(r"\d{4}\.(0[1-9]|1[0-2])(\.[1-9]\d*)?")


def _linhas_parquet(path: Path) -> int:
    return pq.ParquetFile(path).metadata.num_rows


CONTADORES = {".csv": count_csv_records, ".parquet": _linhas_parquet}


def build_manifest(release: str, out_dir: Path, sources: dict[str, Source], used: set[str]) -> dict:
    if not RELEASE.fullmatch(release):
        raise ValueError(f"release '{release}' fora do formato AAAA.MM[.N]")
    desconhecidas = sorted(used - set(sources))
    if desconhecidas:
        raise ValueError(f"source_id desconhecido em sources.yaml: {desconhecidas}")
    return {
        "release": release,
        "schema_version": SCHEMA_VERSION,
        "sources": [
            {"id": s.id, "license": s.license, "retrieved": s.retrieved.isoformat()}
            for s in sorted((sources[i] for i in used), key=lambda s: s.id)
        ],
        "files": describe_files(out_dir, counters=CONTADORES),
    }
