"""Leitura das tabelas de nomes do Statistics Norway (SSB) em JSON-stat 2.0 (spec 003, R1.4 e R1.5).

Não é adaptador: o nome começa com _ e não corresponde a nenhum id de sources.yaml.
"""

import json
from collections.abc import Iterator
from pathlib import Path

from namescommons.adapters import FormatError

API = (
    "https://data.ssb.no/api/pxwebapi/v2/tables/{tabela}/data?lang=en&outputFormat=json-stat2"
    "&valueCodes%5B{dimensao}%5D=%2A&valueCodes%5BContentsCode%5D=Personer&valueCodes%5BTid%5D=%2A"
)
# "." = menos que o limite de divulgação (4 nascimentos ou 200 pessoas); ".." = dado indisponível.
MARCADORES = {".", ".."}


def _categorias(dados: dict, dimensao: str) -> list[tuple[str, str]]:
    categoria = dados["dimension"][dimensao]["category"]
    indice = categoria["index"]
    codigos = sorted(indice, key=indice.get) if isinstance(indice, dict) else list(indice)
    rotulos = categoria.get("label", {})
    return [(c, rotulos.get(c, c)) for c in codigos]


def cells(caminho: Path, dimensao: str) -> Iterator[tuple[str, str, int, int]]:
    """(código, rótulo, ano, valor) de cada célula publicada; células suprimidas são omitidas."""
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if dados.get("class") != "dataset" or dados.get("id") != [dimensao, "ContentsCode", "Tid"]:
        raise FormatError(f"{Path(caminho).name}: esperava dataset com dimensões [{dimensao}, ContentsCode, Tid], "
                          f"veio {dados.get('id')}")
    nomes, anos = _categorias(dados, dimensao), _categorias(dados, "Tid")
    medidas = _categorias(dados, "ContentsCode")
    if [c for c, _ in medidas] != ["Personer"]:
        raise FormatError(f"{Path(caminho).name}: esperava só a medida Personer, veio {medidas}")
    valores, status = dados["value"], dados.get("status") or {}
    if not isinstance(valores, list) or len(valores) != len(nomes) * len(anos):
        raise FormatError(f"{Path(caminho).name}: 'value' não é uma lista densa de {len(nomes) * len(anos)} células")
    if not isinstance(status, (list, dict)):
        raise FormatError(f"{Path(caminho).name}: 'status' deve ser lista ou dicionário, veio {type(status).__name__}")
    if isinstance(status, list):
        status = {str(k): s for k, s in enumerate(status) if s is not None}
    for ano, _ in anos:
        if not ano.isdigit():
            raise FormatError(f"{Path(caminho).name}: ano {ano!r} não é numérico em 'Tid'")
    for i, (codigo, rotulo) in enumerate(nomes):
        for j, (ano, _) in enumerate(anos):
            k = i * len(anos) + j
            valor = valores[k]
            if valor is None:
                if status.get(str(k)) not in MARCADORES:
                    raise FormatError(f"{Path(caminho).name}: célula {k} vazia sem marcador conhecido")
                continue
            if type(valor) is not int:
                raise FormatError(f"{Path(caminho).name}: célula {k} com valor {valor!r}, esperava inteiro")
            yield codigo, rotulo, int(ano), valor
