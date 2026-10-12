"""SSA, nomes de bebês dos EUA (spec 003, R1.1).

names.zip traz um arquivo yobAAAA.txt por ano de nascimento, com linhas nome,sexo,contagem.
A SSA omite nomes com menos de 5 ocorrências; não há marcador de supressão no arquivo.
"""

import csv
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path

from namescommons.adapters import FormatError, RawRecord, Resource, parse_code, parse_count

SOURCE_ID = "us-ssa-births"
RESOURCES = [Resource("https://www.ssa.gov/oact/babynames/names.zip", "names.zip")]

_ANO = re.compile(r"yob(\d{4})\.txt")
_FIM_DE_LINHA = re.compile(r"\r\n|\r|\n")
_SEXO = {"F": "F", "M": "M"}


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    with zipfile.ZipFile(files["names.zip"]) as z:
        anuais = sorted((int(m.group(1)), nome) for nome in z.namelist() if (m := _ANO.fullmatch(nome)))
        if not anuais:
            raise FormatError("names.zip sem arquivos yobAAAA.txt")
        for ano, nome in anuais:
            dados = z.read(nome)
            try:
                texto = dados.decode("ascii")
            except UnicodeDecodeError as e:
                linha = len(_FIM_DE_LINHA.split(dados[:e.start].decode("ascii")))
                raise FormatError(f"{nome}, linha {linha}: byte fora de ASCII ({e.reason})") from e
            linhas = _FIM_DE_LINHA.split(texto)
            if linhas[-1] == "":  # terminador da última linha
                linhas.pop()
            for linha, bruta in enumerate(linhas, start=1):
                campos = next(csv.reader([bruta]), [])
                if len(campos) != 3:
                    raise FormatError(f"{nome}, linha {linha}: esperava nome,sexo,contagem, veio {campos!r}")
                yield RawRecord(
                    name=campos[0], kind="given", country="US",
                    gender=parse_code(campos[1], _SEXO, "sexo"), year=ano, count=parse_count(campos[2]),
                )
