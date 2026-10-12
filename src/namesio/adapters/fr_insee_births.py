"""INSEE, Fichier des prénoms, edição 2025, nível nacional (spec 003, R1.2).

O ZIP traz um CSV separado por ponto e vírgula com sexe;prenom;periode;valeur;rang.
Sexo 1 é masculino e 2 é feminino. Os valores vêm arredondados ao múltiplo de 5 mais próximo.
"""

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import FormatError, RawRecord, Resource, parse_code, parse_count

SOURCE_ID = "fr-insee-births"
RESOURCES = [
    Resource("https://www.insee.fr/fr/statistiques/fichier/8595130/prenoms-2025-nat_csv.zip",
             "prenoms-2025-nat_csv.zip"),
]

_SEXO = {"1": "M", "2": "F"}
_COLUNAS = {"sexe", "prenom", "periode", "valeur"}


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    with zipfile.ZipFile(files["prenoms-2025-nat_csv.zip"]) as z:
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
                if prenom.startswith("_") or periode == "XXXX":
                    continue
                yield RawRecord(
                    name=prenom, kind="given", country="FR",
                    gender=parse_code(linha["sexe"], _SEXO, "sexe"),
                    year=parse_count(periode, field="periode"), count=parse_count(linha["valeur"]),
                )
