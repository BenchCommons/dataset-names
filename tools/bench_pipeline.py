"""Medição de R8 (spec 002): namescommons ingest e build sobre observações sintéticas.

Gera um CSV sintético num cache, um adaptador temporário e um sources.yaml, e roda
os comandos reais da CLI. Registra tempo de cada etapa e pico de memória do processo.
Não roda na CI.

Uso: uv run python tools/bench_pipeline.py [--observacoes 3000000] [--dir DIR] [--registro r8.json]
"""

import argparse
import csv
import json
import platform
import resource
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
BLOCO = len(PAISES) * len(ANOS) * len(GENEROS)  # observações por nome
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


def total_de_observacoes(pedidas: int) -> int:
    """Maior múltiplo de BLOCO que não passa de pedidas (no mínimo um bloco)."""
    return max(1, pedidas // BLOCO) * BLOCO


def _nome(i: int) -> str:
    silabas = []
    for _ in range(3):
        i, resto = divmod(i, len(SILABAS))
        silabas.append(SILABAS[resto])
    return "".join(silabas).upper()


def _gerar(base: Path, total: int) -> None:
    (base / "cache" / "sintetica").mkdir(parents=True)
    (base / "bench_adaptadores").mkdir()
    (base / "bench_adaptadores" / "__init__.py").write_text("", encoding="utf-8")
    (base / "bench_adaptadores" / "sintetica.py").write_text(ADAPTADOR, encoding="utf-8")
    (base / "sources.yaml").write_text(FONTES_YAML, encoding="utf-8")
    with open(base / "cache" / "sintetica" / "dados.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        for i in range(total // BLOCO):
            nome = _nome(i)
            for pais in PAISES:
                for ano in ANOS:
                    for g, genero in enumerate(GENEROS):
                        w.writerow((nome, pais, genero, ano, (i * 7919 + ano * 31 + g) % 5000 + 5))


def _memoria_pico_mb() -> float:
    pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return pico / (1024 * 1024) if sys.platform == "darwin" else pico / 1024


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--observacoes", type=int, default=3_000_000)
    ap.add_argument("--dir", type=Path, help="diretório de trabalho (padrão: temporário)")
    ap.add_argument("--registro", type=Path, help="grava o resultado em JSON")
    args = ap.parse_args(argv)
    total = total_de_observacoes(args.observacoes)
    base = args.dir or Path(tempfile.mkdtemp(prefix="namescommons-r8-"))
    base.mkdir(parents=True, exist_ok=True)

    inicio = time.perf_counter()
    _gerar(base, total)
    geracao = time.perf_counter() - inicio
    comum = ["--sources", str(base / "sources.yaml")]
    sys.path.insert(0, str(base))
    try:
        inicio = time.perf_counter()
        codigo = namescommons(["ingest", "--offline", "--out", str(base / "observations.parquet"),
                          "--cache", str(base / "cache"), "--adapters", "bench_adaptadores", *comum])
        ingest = time.perf_counter() - inicio
        if codigo != 0:
            return codigo
        inicio = time.perf_counter()
        codigo = namescommons(["build", str(base / "observations.parquet"), "--out", str(base / "dist"),
                          "--release", "2026.10", *comum])
        build = time.perf_counter() - inicio
        if codigo != 0:
            return codigo
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
    }
    print(
        f"R8: {total} observações; ingest {ingest:.1f} s, build {build:.1f} s, "
        f"pico de memória {memoria:.0f} MB; "
        + ("dentro dos limites" if dentro else f"FORA dos limites ({LIMITE_SEGUNDOS} s, {LIMITE_MB} MB)")
    )
    if args.registro:
        args.registro.write_text(json.dumps(resultado, indent=2) + "\n", encoding="utf-8")
    return 0 if dentro else 1


if __name__ == "__main__":
    sys.exit(main())
