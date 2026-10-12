"""Linha de comando: namescommons fetch | ingest | validate | build | run."""

import argparse
import json
from collections import Counter
import os
import shutil
import sys
import tempfile
from pathlib import Path

from pyarrow import ArrowException

from namescommons.adapters import DEFAULT_PACKAGE
from namescommons.aggregate import AggregationError, by_country, name_index
from namescommons.io import (
    read_dropped, read_links, read_observations, write_by_country, write_index, write_links, write_observations,
)
from namescommons.links import VariantLink, validate_links
from namescommons.manifest import RELEASE, build_manifest
from namescommons.pipeline import Drops, PipelineError, fetch_sources, ingest_links, ingest_sources, select_sources
from namescommons.schema import Observation, ValidationError, validate
from namescommons.sources import Source, SourceError, load_sources


def _n(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _opcoes_de_fonte(p: argparse.ArgumentParser, com_ids: bool = True) -> None:
    if com_ids:
        p.add_argument("ids", nargs="*", metavar="ID", help="fontes de sources.yaml (padrão: todas com adaptador)")
    p.add_argument("--cache", type=Path, default=Path("cache"), help="diretório do cache de downloads (padrão: %(default)s)")
    p.add_argument("--adapters", default=DEFAULT_PACKAGE, help="pacote Python dos adaptadores; precisa ser importável, ex.: PYTHONPATH=tests para o adaptador de teste (padrão: %(default)s)")


class _Ajuda(argparse.ArgumentDefaultsHelpFormatter):
    """Mostra o padrão só quando ele diz algo (nem None nem flags desligadas)."""

    def _get_help_string(self, action):
        if action.default in (None, False, argparse.SUPPRESS) or action.default == []:
            return action.help
        return super()._get_help_string(action)


def _com_padroes(add):
    """Faz os subcomandos mostrarem os valores padrão no --help."""
    def novo(*a, **kw):
        kw.setdefault("formatter_class", _Ajuda)
        return add(*a, **kw)
    return novo


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="namescommons", formatter_class=_Ajuda)
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="{fetch,ingest,validate,build,run}")
    sub.add_parser = _com_padroes(sub.add_parser)
    p = sub.add_parser("fetch", help="baixa os recursos das fontes para o cache")
    _opcoes_de_fonte(p)
    p.add_argument("--refresh", action="store_true", help="baixa de novo mesmo com o arquivo no cache")
    p = sub.add_parser("ingest", help="roda os adaptadores sobre o cache e grava observations.parquet")
    _opcoes_de_fonte(p)
    p.add_argument("--out", type=Path, required=True, help="arquivo observations.parquet a gravar")
    p.add_argument("--offline", action="store_true", help="não acessa a rede; arquivo ausente do cache é erro")
    p.add_argument("--links", type=Path, help="arquivo variant_links.parquet a gravar com as ligações entre variantes (spec 004)")
    ajuda = {
        "validate": "valida um observations.parquet (spec 001)",
        "build": "gera as saídas da release a partir de um observations.parquet (spec 001)",
    }
    for nome in ("validate", "build"):
        p = sub.add_parser(nome, help=ajuda[nome])
        p.add_argument("observations", type=Path, help="observations.parquet")
        if nome == "build":
            p.add_argument("--out", type=Path, required=True, help="diretório novo ou vazio para as saídas da release")
            p.add_argument("--release", required=True, help="AAAA.MM[.N]")
            p.add_argument("--links", type=Path, help="variant_links.parquet gravado por ingest --links, copiado para a release")
    p = sub.add_parser("run", help="fetch, ingest e build em sequência")
    _opcoes_de_fonte(p, com_ids=False)
    p.add_argument("--out", type=Path, required=True, help="diretório novo ou vazio para as saídas da release")
    p.add_argument("--release", required=True, help="AAAA.MM[.N]")
    p.add_argument("--offline", action="store_true", help="pula o fetch e não acessa a rede")
    p.add_argument("--refresh", action="store_true", help="baixa de novo mesmo com o arquivo no cache")
    for p in sub.choices.values():
        p.add_argument(
            "--sources", type=Path, default=Path("sources.yaml"), help="arquivo de catálogo de fontes (padrão: %(default)s)"
        )
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


def _build(
    obs: list[Observation], fontes: dict[str, Source], out: Path, release: str,
    links: list[VariantLink] | None = None,
    dropped: dict[str, dict[str, int]] | None = None,
) -> int:
    """Grava as saídas da spec 001 (e variant_links da spec 004, se houver) em out, tudo ou nada;
    devolve o número de países.

    As saídas são montadas num diretório temporário ao lado de out e só então renomeadas:
    uma falha em qualquer etapa não deixa saída parcial.
    """
    paises = by_country(obs, fontes)
    out.parent.mkdir(parents=True, exist_ok=True)
    temporario = Path(tempfile.mkdtemp(prefix=f".{out.name}.", dir=out.parent))
    try:
        umask = os.umask(0)
        os.umask(umask)
        temporario.chmod(0o777 & ~umask)
        write_observations(obs, temporario / "observations.parquet", dropped)
        for kind, base in (("given", "given_names"), ("family", "family_names")):
            write_index(name_index(obs, paises, kind, fontes, links), temporario / f"{base}.csv", temporario / f"{base}.parquet")
        write_by_country(paises, temporario / "by_country")
        if links is not None:
            write_links(links, temporario / "variant_links.parquet")
        # Spec 005, R7.4: fontes das observações e das ligações.
        usadas = {o.source_id for o in obs} | {v.source_id for v in links or ()}
        por_fonte = Counter(o.source_id for o in obs)
        manifest = build_manifest(release, temporario, fontes, usadas, observations=por_fonte, dropped=dropped)
        (temporario / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        # rename sobre um diretório vazio existente (já checado por _saida_invalida) o substitui
        # de forma atômica em POSIX, sem apagar antes o diretório do usuário.
        os.replace(temporario, out)
    except BaseException:
        shutil.rmtree(temporario, ignore_errors=True)
        raise
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
                print(f"OK: {_n(len(selecionadas), 'fonte', 'fontes')} em {args.cache}.")
                return 0
            descartes: dict[str, Drops] = {}
            obs = ingest_sources(
                selecionadas, fontes, args.cache, offline=args.offline, adapters=args.adapters, drops=descartes,
            )
            dropped = {i: d.as_dict() for i, d in descartes.items()}
            links = None
            if args.cmd == "run" or args.links is not None:
                links = ingest_links(selecionadas, fontes, args.cache, offline=args.offline, adapters=args.adapters)
            if args.cmd == "ingest":
                if args.out.exists():
                    print(f"aviso: {args.out} já existe e será substituído", file=sys.stderr)
                write_observations(obs, args.out, dropped)
                mensagem = f"OK: {_n(len(obs), 'observação', 'observações')} de {_n(len(selecionadas), 'fonte', 'fontes')} em {args.out}"
                if args.links is not None:
                    write_links(links or [], args.links)
                    mensagem += f"; {_n(len(links or []), 'ligação', 'ligações')} em {args.links}"
                print(mensagem + ".")
                return 0
        else:
            if not args.observations.exists():
                return _erro(f"arquivo não encontrado: {args.observations}")
            try:
                obs = read_observations(args.observations)
            except (OSError, ArrowException, TypeError, KeyError) as e:
                return _erro(f"não foi possível ler {args.observations}: {e}")
            validate(obs, fontes)
            dropped = read_dropped(args.observations)
            links = None
            if getattr(args, "links", None) is not None:
                if not args.links.exists():
                    return _erro(f"arquivo não encontrado: {args.links}")
                try:
                    links = read_links(args.links)
                except (OSError, ArrowException, TypeError, KeyError) as e:
                    return _erro(f"não foi possível ler {args.links}: {e}")
                validate_links(links, fontes)
            if args.cmd == "validate":
                print(f"OK: {_n(len(obs), 'observação válida', 'observações válidas')}.")
                return 0
        paises = _build(obs, fontes, args.out, args.release, links, dropped)
    except (
        PipelineError, SourceError, ValidationError, AggregationError, ValueError, OSError, ArrowException,
    ) as e:
        return _erro(str(e))
    print(f"OK: {_n(len(obs), 'observação', 'observações')}, {_n(paises, 'país', 'países')} em {args.out}.")
    return 0
