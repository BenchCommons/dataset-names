"""manifest.json de uma release (spec 001, R5).

O formato da release, schema_version e a lista sources são daqui; o SHA-256 e a contagem de
registros de cada arquivo vêm de datasettool.files (spec 007, R3.4).
"""

import re
from collections.abc import Mapping
from pathlib import Path

import pyarrow.parquet as pq
from datasettool.files import count_csv_records, describe_files

from namescommons.schema import SCHEMA_VERSION
from namescommons.sources import Source

RELEASE = re.compile(r"\d{4}\.(0[1-9]|1[0-2])(\.[1-9]\d*)?")
DATA_LICENSE_SPDX = "CC-BY-4.0"  # ADR 0001; spec 006, R2.2


def _linhas_parquet(path: Path) -> int:
    return pq.ParquetFile(path).metadata.num_rows


CONTADORES = {".csv": count_csv_records, ".parquet": _linhas_parquet}


def build_manifest(
    release: str,
    out_dir: Path,
    sources: dict[str, Source],
    used: set[str],
    observations: Mapping[str, int] | None = None,
    dropped: Mapping[str, Mapping[str, int]] | None = None,
) -> dict:
    """Manifesto da release. observations conta as linhas por fonte; dropped traz os descartes
    por fonte (spec 006, R2.1), e fonte ausente de dropped (ou dropped None) fica com null."""
    if not RELEASE.fullmatch(release):
        raise ValueError(f"release '{release}' fora do formato AAAA.MM[.N]")
    desconhecidas = sorted(used - set(sources))
    if desconhecidas:
        raise ValueError(f"source_id desconhecido em sources.yaml: {desconhecidas}")
    return {
        "release": release,
        "schema_version": SCHEMA_VERSION,
        "data_license": DATA_LICENSE_SPDX,
        "sources": [
            {
                "id": s.id, "name": s.name, "license": s.license, "retrieved": s.retrieved.isoformat(),
                "observations": (observations or {}).get(s.id, 0),
                "dropped": None if dropped is None or s.id not in dropped else dict(dropped[s.id]),
            }
            for s in sorted((sources[i] for i in used), key=lambda s: s.id)
        ],
        "files": describe_files(out_dir, counters=CONTADORES),
    }
