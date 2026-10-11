"""Linha de comando: namesio validate | namesio build."""

import argparse
import json
import sys
from pathlib import Path

from namesio.aggregate import AggregationError, by_country, name_index
from namesio.io import read_observations, write_by_country, write_index, write_observations
from namesio.manifest import build_manifest
from namesio.schema import ValidationError, validate
from namesio.sources import SourceError, load_sources


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="namesio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("validate", "build"):
        p = sub.add_parser(nome)
        p.add_argument("observations", type=Path, help="observations.parquet")
        p.add_argument("--sources", type=Path, default=Path("sources.yaml"))
        if nome == "build":
            p.add_argument("--out", type=Path, required=True)
            p.add_argument("--release", required=True, help="AAAA.MM[.N]")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        fontes = load_sources(args.sources)
        obs = read_observations(args.observations)
        validate(obs, fontes)
        if args.cmd == "validate":
            print(f"OK: {len(obs)} observações válidas.")
            return 0
        paises = by_country(obs, fontes)
        args.out.mkdir(parents=True, exist_ok=True)
        write_observations(obs, args.out / "observations.parquet")
        for kind, base in (("given", "given_names"), ("family", "family_names")):
            write_index(name_index(obs, paises, kind), args.out / f"{base}.csv", args.out / f"{base}.parquet")
        write_by_country(paises, args.out / "by_country")
        manifest = build_manifest(args.release, args.out, fontes, {o.source_id for o in obs})
    except (SourceError, ValidationError, AggregationError, ValueError) as e:
        print(e, file=sys.stderr)
        return 1
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OK: {len(obs)} observações, {len(paises)} países em {args.out}.")
    return 0
