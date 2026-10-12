"""INSEE, Fichier des prénoms, nível nacional (spec 003, R1.2).

O ZIP traz um CSV separado por ponto e vírgula com sexe;prenom;periode;valeur;rang.
Sexo 1 é masculino e 2 é feminino. Os valores vêm arredondados ao múltiplo de 5 mais próximo.

Passo anual (issue #16): cada edição vive numa página nova do INSEE, com id novo, e não há listagem
estável da mais recente (a página antiga não aponta para a nova; o dataset do data.gouv.fr aponta
para uma edição de 2022). Por isso a URL é trocada à mão: ao sair uma edição, ajuste EDICAO e PAGINA
abaixo e siga o "Passo anual do INSEE" do AGENTS.md. tests/test_insee_edicao.py falha se
sources.yaml, a amostra ou a atribuição ficarem para trás.
"""

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

from namescommons.adapters import FormatError, RawRecord, Resource, parse_code, parse_count

SOURCE_ID = "fr-insee-births"
EDICAO = 2025
PAGINA = 8595130  # id da página da edição em insee.fr/fr/statistiques/<id>
ARQUIVO = f"prenoms-{EDICAO}-nat_csv.zip"
RESOURCES = [Resource(f"https://www.insee.fr/fr/statistiques/fichier/{PAGINA}/{ARQUIVO}", ARQUIVO)]

_SEXO = {"1": "M", "2": "F"}
_COLUNAS = {"sexe", "prenom", "periode", "valeur"}
_PRENOMS_RARES = "_PRENOMS_RARES"


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    with zipfile.ZipFile(files[ARQUIVO]) as z:
        membros = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(membros) != 1:
            raise FormatError(f"esperava um CSV no ZIP, encontrei {membros}")
        with z.open(membros[0]) as bruto:
            leitor = csv.DictReader(io.TextIOWrapper(bruto, encoding="utf-8-sig", newline=""), delimiter=";")
            faltando = _COLUNAS - set(leitor.fieldnames or ())
            if faltando:
                raise FormatError(f"{membros[0]}: colunas ausentes {sorted(faltando)}; cabeçalho {leitor.fieldnames}")
            for linha in leitor:
                prenom, periode = linha["prenom"], linha["periode"]
                # Edições anteriores agregavam nomes raros em _PRENOMS_RARES e anos ignorados em XXXX.
                if prenom == _PRENOMS_RARES or periode == "XXXX":
                    continue
                if prenom.startswith("_"):
                    raise FormatError(
                        f"{membros[0]}, linha {leitor.line_num}: prenom {prenom!r} começa com _ "
                        f"e não é o agregado conhecido {_PRENOMS_RARES!r}"
                    )
                yield RawRecord(
                    name=prenom, kind="given", country="FR",
                    gender=parse_code(linha["sexe"], _SEXO, "sexe"),
                    year=parse_count(periode, field="periode"), count=parse_count(linha["valeur"]),
                )
