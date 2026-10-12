"""Linha de comando: namesio fetch | ingest | validate | build | run."""

import argparse
import json
import sys
from pathlib import Path

from pyarrow import ArrowException

from namesio.adapters import DEFAULT_PACKAGE
from namesio.aggregate import AggregationError, by_country, name_index
from namesio.io import read_observations, write_by_country, write_index, write_observations
from namesio.manifest import RELEASE, build_manifest
from namesio.pipeline import PipelineError, fetch_sources, ingest_sources, select_sources
from namesio.schema import Observation, ValidationError, validate
from namesio.sources import Source, SourceError, load_sources


def _opcoes_de_fonte(p: argparse.ArgumentParser, com_ids: bool = True) -> None:
    if com_ids:
        p.add_argument("ids", nargs="*", metavar="ID", help="fontes de sources.yaml (padrão: todas com adaptador)")
    p.add_argument("--cache", type=Path, default=Path("cache"), help="diretório do cache de downloads")
    p.add_argument("--adapters", default=DEFAULT_PACKAGE, help="pacote Python dos adaptadores")


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="namesio")
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="{fetch,ingest,validate,build,run}")
    p = sub.add_parser("fetch", help="baixa os recursos das fontes para o cache")
    _opcoes_de_fonte(p)
    p.add_argument("--refresh", action="store_true", help="baixa de novo mesmo com o arquivo no cache")
    p = sub.add_parser("ingest", help="roda os adaptadores sobre o cache e grava observations.parquet")
    _opcoes_de_fonte(p)
    p.add_argument("--out", type=Path, required=True, help="observations.parquet")
    p.add_argument("--offline", action="store_true", help="não acessa a rede; arquivo ausente do cache é erro")
    ajuda = {
        "validate": "valida um observations.parquet (spec 001)",
        "build": "gera as saídas da release a partir de um observations.parquet (spec 001)",
    }
    for nome in ("validate", "build"):
        p = sub.add_parser(nome, help=ajuda[nome])
        p.add_argument("observations", type=Path, help="observations.parquet")
        if nome == "build":
            p.add_argument("--out", type=Path, required=True)
            p.add_argument("--release", required=True, help="AAAA.MM[.N]")
    p = sub.add_parser("run", help="fetch, ingest e build em sequência")
    _opcoes_de_fonte(p, com_ids=False)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--release", required=True, help="AAAA.MM[.N]")
    p.add_argument("--offline", action="store_true", help="pula o fetch e não acessa a rede")
    p.add_argument("--refresh", action="store_true", help="baixa de novo mesmo com o arquivo no cache")
    for p in sub.choices.values():
        p.add_argument("--sources", type=Path, default=Path("sources.yaml"))
    return ap


def _erro(mensagem: str) -> int:
    print(mensagem, file=sys.stderr)
    return 1


def _saida_invalida(release: str, out: Path) -> str | None:
    if not RELEASE.fullmatch(release):
        return f"release '{release}' fora do formato AAAA.MM[.N]"
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        return f"--out {out} já existe e não está vazio; use um diretório novo"
    return None


def _build(obs: list[Observation], fontes: dict[str, Source], out: Path, release: str) -> int:
    """Grava as saídas da spec 001 em out; devolve o número de países."""
    paises = by_country(obs, fontes)
    out.mkdir(parents=True, exist_ok=True)
    write_observations(obs, out / "observations.parquet")
    for kind, base in (("given", "given_names"), ("family", "family_names")):
        write_index(name_index(obs, paises, kind), out / f"{base}.csv", out / f"{base}.parquet")
    write_by_country(paises, out / "by_country")
    manifest = build_manifest(release, out, fontes, {o.source_id for o in obs})
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(paises)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd in ("build", "run"):
        problema = _saida_invalida(args.release, args.out)
        if problema:
            return _erro(problema)
    if args.cmd == "run" and args.offline and args.refresh:
        return _erro("--offline e --refresh são incompatíveis")
    try:
        fontes = load_sources(args.sources)
        if args.cmd in ("fetch", "ingest", "run"):
            selecionadas = select_sources(fontes, getattr(args, "ids", []))
            if args.cmd == "fetch" or (args.cmd == "run" and not args.offline):
                fetch_sources(selecionadas, args.cache, refresh=args.refresh, adapters=args.adapters)
            if args.cmd == "fetch":
                print(f"OK: {len(selecionadas)} fonte(s) em {args.cache}.")
                return 0
            obs = ingest_sources(selecionadas, fontes, args.cache, offline=args.offline, adapters=args.adapters)
            if args.cmd == "ingest":
                write_observations(obs, args.out)
                print(f"OK: {len(obs)} observações de {len(selecionadas)} fonte(s) em {args.out}.")
                return 0
        else:
            try:
                obs = read_observations(args.observations)
            except (OSError, ArrowException, TypeError, KeyError) as e:
                return _erro(f"não foi possível ler {args.observations}: {e}")
            validate(obs, fontes)
            if args.cmd == "validate":
                print(f"OK: {len(obs)} observações válidas.")
                return 0
        paises = _build(obs, fontes, args.out, args.release)
    except (
        PipelineError, SourceError, ValidationError, AggregationError, ValueError, OSError, ArrowException,
    ) as e:
        return _erro(str(e))
    print(f"OK: {len(obs)} observações, {paises} países em {args.out}.")
    return 0
