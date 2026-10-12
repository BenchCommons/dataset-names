"""Medição de R8 (spec 002): namescommons ingest e build sobre observações sintéticas.

Gera um CSV sintético num cache, um adaptador temporário e um sources.yaml, e roda
os comandos reais da CLI. Registra tempo de cada etapa e pico de memória do processo.
Não roda na CI.

Uso: uv run python tools/bench_pipeline.py [--observacoes 3000000] [--dir DIR] [--registro r8.json]
     [--wikidata CACHE/wikidata]

--wikidata inclui na mesma medição o Wikidata com os arquivos já baixados no diretório indicado
(spec 005, R9.4; issue #31), com ingest --links e build --links.
"""

import argparse
import csv
import json
import os
import platform
import resource
import shutil
import sys
import tempfile
import time
from pathlib import Path

from namescommons.cli import main as namescommons

LIMITE_SEGUNDOS = 600
LIMITE_MB = 4096
PAISES = ("AR", "BR", "CA", "DE", "ES", "FR", "IT", "MX", "PT", "US")
ANOS = range(1990, 2020)
GENEROS = ("F", "M")
PAISES_POR_NOME = 2
BLOCO = PAISES_POR_NOME * len(ANOS) * len(GENEROS)  # observações por nome
SILABAS = ("ma", "ri", "an", "jo", "se", "lu", "ca", "el", "in", "ra",
           "to", "ne", "li", "sa", "be", "do", "vi", "ga", "ru", "te")

FONTES_YAML = """\
sources:
  - id: sintetica
    name: Fonte sintética da medição de R8
    url: https://example.org/sintetica/
    license: CC0-1.0
    attribution: namescommons
    country: null
    count_type: births
    primary: true
    suppression: null
    retrieved: 2026-10-01
    uniform_case: true
"""

ADAPTADOR = '''\
import csv
from namescommons.adapters import RawRecord, Resource

SOURCE_ID = "sintetica"
RESOURCES = [Resource("https://example.org/sintetica/dados.csv", "dados.csv")]


def parse(files):
    with open(files["dados.csv"], encoding="utf-8", newline="") as fh:
        for nome, pais, genero, ano, contagem in csv.reader(fh):
            yield RawRecord(nome, "given", pais, genero, int(ano), int(contagem))
'''


WIKIDATA_YAML = """\
  - id: wikidata
    name: Wikidata
    url: https://www.wikidata.org/wiki/Wikidata:Licensing
    license: CC0-1.0
    attribution: Wikidata
    country: null
    count_type: attested
    primary: false
    suppression: null
    retrieved: 2026-10-12
"""

WIKIDATA_ADAPTADOR = "from namescommons.adapters.wikidata import SOURCE_ID, RESOURCES, parse, links  # noqa: F401\n"


def _incluir_wikidata(base: Path, origem: Path) -> None:
    """Fonte, adaptador e cache do Wikidata no diretório da medição.

    Os arquivos de origem entram no cache por link físico (ou cópia, se o link não for possível):
    o cache do tools-dataset recusa caminho que resolve fora do diretório do cache, como um link simbólico.
    """
    with open(base / "sources.yaml", "a", encoding="utf-8") as fh:
        fh.write(WIKIDATA_YAML)
    (base / "bench_adaptadores" / "wikidata.py").write_text(WIKIDATA_ADAPTADOR, encoding="utf-8")
    destino = base / "cache" / "wikidata"
    destino.mkdir(parents=True)
    for arquivo in sorted(origem.resolve().iterdir()):
        if arquivo.is_file():
            try:
                os.link(arquivo, destino / arquivo.name)
            except OSError:
                shutil.copy2(arquivo, destino / arquivo.name)


def total_de_observacoes(pedidas: int) -> int:
    """Maior múltiplo de BLOCO que não passa de pedidas (no mínimo um bloco)."""
    return max(1, pedidas // BLOCO) * BLOCO


SILABAS_POR_NOME = 5
NOMES_POSSIVEIS = len(SILABAS) ** SILABAS_POR_NOME


def _nome(i: int) -> str:
    """Nome distinto para cada i abaixo de NOMES_POSSIVEIS (3,2 milhões)."""
    silabas = []
    for _ in range(SILABAS_POR_NOME):
        i, resto = divmod(i, len(SILABAS))
        silabas.append(SILABAS[resto])
    return "".join(silabas).upper()


def _gerar(base: Path, total: int) -> None:
    if total // BLOCO > NOMES_POSSIVEIS:
        raise ValueError(f"{total} observações pedem mais de {NOMES_POSSIVEIS} nomes distintos")
    (base / "cache" / "sintetica").mkdir(parents=True)
    (base / "bench_adaptadores").mkdir()
    (base / "bench_adaptadores" / "__init__.py").write_text("", encoding="utf-8")
    (base / "bench_adaptadores" / "sintetica.py").write_text(ADAPTADOR, encoding="utf-8")
    (base / "sources.yaml").write_text(FONTES_YAML, encoding="utf-8")
    with open(base / "cache" / "sintetica" / "dados.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        for i in range(total // BLOCO):
            nome = _nome(i)
            for d in range(PAISES_POR_NOME):
                pais = PAISES[(i + d) % len(PAISES)]
                for ano in ANOS:
                    for g, genero in enumerate(GENEROS):
                        w.writerow((nome, pais, genero, ano, (i * 7919 + ano * 31 + g) % 5000 + 5))


def _memoria_pico_mb() -> float:
    pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return pico / (1024 * 1024) if sys.platform == "darwin" else pico / 1024


def _falha(etapa: str, codigo: int, base: Path) -> int:
    """Mesmo formato da linha R8 de sucesso, para o registro da medição nunca ficar sem ela."""
    print(f"R8: FALHA no {etapa} (código {codigo}); dados mantidos em {base}")
    return codigo


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--observacoes", type=int, default=3_000_000)
    ap.add_argument("--dir", type=Path, help="diretório de trabalho (padrão: temporário)")
    ap.add_argument("--registro", type=Path, help="grava o resultado em JSON")
    ap.add_argument("--wikidata", type=Path, help="diretório com os arquivos do Wikidata já baixados")
    args = ap.parse_args(argv)
    total = total_de_observacoes(args.observacoes)
    base = args.dir or Path(tempfile.mkdtemp(prefix="namescommons-r8-"))
    base.mkdir(parents=True, exist_ok=True)
    if any(base.iterdir()):
        print(f"{base} já contém arquivos; use um diretório novo ou vazio", file=sys.stderr)
        return 2

    inicio = time.perf_counter()
    _gerar(base, total)
    if args.wikidata:
        _incluir_wikidata(base, args.wikidata)
    ligacoes = ["--links", str(base / "variant_links.parquet")] if args.wikidata else []
    geracao = time.perf_counter() - inicio
    comum = ["--sources", str(base / "sources.yaml")]
    sys.path.insert(0, str(base))
    try:
        inicio = time.perf_counter()
        codigo = namescommons(["ingest", "--offline", "--out", str(base / "observations.parquet"),
                          "--cache", str(base / "cache"), "--adapters", "bench_adaptadores", *ligacoes, *comum])
        ingest = time.perf_counter() - inicio
        if codigo != 0:
            return _falha("ingest", codigo, base)
        inicio = time.perf_counter()
        codigo = namescommons(["build", str(base / "observations.parquet"), "--out", str(base / "dist"),
                          "--release", "2026.10", *ligacoes, *comum])
        build = time.perf_counter() - inicio
        if codigo != 0:
            return _falha("build", codigo, base)
    finally:
        sys.path.remove(str(base))
        for modulo in [m for m in sys.modules if m.split(".")[0] == "bench_adaptadores"]:
            del sys.modules[modulo]

    memoria = _memoria_pico_mb()
    dentro = ingest + build < LIMITE_SEGUNDOS and memoria < LIMITE_MB
    resultado = {
        "observacoes": total, "geracao_s": round(geracao, 1), "ingest_s": round(ingest, 1),
        "build_s": round(build, 1), "memoria_pico_mb": round(memoria), "python": platform.python_version(),
        "maquina": f"{platform.system()} {platform.machine()}", "dentro_dos_limites": dentro,
        "wikidata": bool(args.wikidata),
    }
    print(
        f"R8: {total} observações" + (" sintéticas mais o Wikidata" if args.wikidata else "") + f"; ingest {ingest:.1f} s, build {build:.1f} s, "
        f"pico de memória {memoria:.0f} MB; "
        + ("dentro dos limites" if dentro else f"FORA dos limites ({LIMITE_SEGUNDOS} s, {LIMITE_MB} MB)")
    )
    if args.registro:
        args.registro.write_text(json.dumps(resultado, indent=2) + "\n", encoding="utf-8")
    return 0 if dentro else 1


if __name__ == "__main__":
    sys.exit(main())
