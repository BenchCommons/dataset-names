"""manifest.json de uma release (spec 001, R5)."""

import hashlib
import re
from pathlib import Path

import pyarrow.parquet as pq

from namesio.schema import SCHEMA_VERSION
from namesio.sources import Source

RELEASE = re.compile(r"\d{4}\.(0[1-9]|1[0-2])(\.[1-9]\d*)?")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _linhas(path: Path) -> int:
    if path.suffix == ".parquet":
        return pq.ParquetFile(path).metadata.num_rows
    with open(path, encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1  # desconta o cabeçalho


def build_manifest(release: str, out_dir: Path, sources: dict[str, Source], used: set[str]) -> dict:
    if not RELEASE.fullmatch(release):
        raise ValueError(f"release '{release}' fora do formato AAAA.MM[.N]")
    arquivos = {}
    for p in sorted(out_dir.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            arquivos[p.relative_to(out_dir).as_posix()] = {"sha256": _sha256(p), "rows": _linhas(p)}
    return {
        "release": release,
        "schema_version": SCHEMA_VERSION,
        "sources": [
            {"id": s.id, "license": s.license, "retrieved": s.retrieved.isoformat()}
            for s in sorted((sources[i] for i in used), key=lambda s: s.id)
        ],
        "files": arquivos,
    }
