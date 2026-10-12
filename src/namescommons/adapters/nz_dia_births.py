"""DIA, nomes de bebês da Nova Zelândia, "Baby Name popularity over time" (spec 003e).

O CSV traz Year,Sex,Name,Count, com o ano do registro do nascimento. A fonte omite nomes com
menos de 10 registros no ano; não há marcador de supressão no arquivo.

Codificação (spec 003e, R2, e ADR 0007): se o arquivo inteiro for UTF-8 válido, é lido como UTF-8.
Senão, os bytes acima de 0x7F passam pela tabela _LEGADO, medida no arquivo real de 2026-10-12;
qualquer outro byte vira U+FFFD. Nome com '?' ou U+FFFD é descartado, e os descartes são avisados
no logger deste módulo ao fim do arquivo. Um byte só entra em _LEGADO com evidência registrada na spec.

Download: o catálogo (Imperva) devolve uma página HTML de desafio a clientes que não são navegador,
e o fetch falha (spec 003e, R4). Abra https://catalogue.data.govt.nz/dataset/baby-name-popularity-over-time
no navegador, baixe o CSV e grave-o em <cache>/nz-dia-births/baby-names-1900-to-2025.csv; depois rode
com --offline.
"""

import csv
import io
import logging
from collections.abc import Iterator
from pathlib import Path

from namescommons.adapters import FormatError, RawRecord, Resource, parse_code, parse_count

SOURCE_ID = "nz-dia-births"
_ARQUIVO = "baby-names-1900-to-2025.csv"
RESOURCES = [
    Resource(
        "https://catalogue.data.govt.nz/dataset/01ee87cd-ecf8-44a1-ad33-b376a689e597"
        f"/resource/0b0b326c-d720-480f-8f86-bf2d221c7d3f/download/{_ARQUIVO}",
        _ARQUIVO,
    )
]

_CABECALHO = ["Year", "Sex", "Name", "Count"]
_SEXO = {"F": "F", "M": "M"}
# Byte -> letra, só quando todas as ocorrências do byte no arquivo real formam um nome atestado
# (spec 003e, R2.2, e ADR 0007): 0x82 é 'é' em CP437/CP850 (Amélie, André, Esmé); 0xE9 e 0xF6 são
# 'é' e 'ö' em Latin-1 (Zoé, Esmé, Björn). Os demais bytes de 0x80 a 0xFF viram U+FFFD.
_LEGADO = {0x82: "é", 0xE9: "é", 0xF6: "ö"}
_TABELA = {b: _LEGADO.get(b, "\ufffd") for b in range(0x80, 0x100)}  # para str.translate sobre Latin-1
_CORROMPIDO = ("?", "\ufffd")

_log = logging.getLogger(__name__)


def _decodificar(dados: bytes) -> str:
    try:
        return dados.decode("utf-8")
    except UnicodeDecodeError:
        return dados.decode("latin-1").translate(_TABELA)


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    caminho = files[_ARQUIVO]
    dados = caminho.read_bytes()
    if dados.lstrip().startswith(b"<"):
        raise FormatError(
            f"{caminho} parece uma página HTML (bloqueio do catálogo), e não o CSV: baixe o CSV pelo navegador "
            "em https://catalogue.data.govt.nz/dataset/baby-name-popularity-over-time e grave-o nesse caminho"
        )
    leitor = csv.reader(io.StringIO(_decodificar(dados).removeprefix("\ufeff"), newline=""))
    cabecalho = next(leitor, None)
    if cabecalho is None:
        raise FormatError(f"{caminho.name}: arquivo vazio")
    if cabecalho != _CABECALHO:
        raise FormatError(f"{caminho.name}: cabeçalho {cabecalho}, esperado {_CABECALHO}")
    descartadas, registros, formas = 0, 0, {}
    for linha, campos in enumerate(leitor, start=2):
        if len(campos) != len(_CABECALHO):
            raise FormatError(f"{caminho.name}, linha {linha}: esperava 4 campos, veio {len(campos)}: {campos!r}")
        ano, sexo, nome, contagem = campos
        try:
            registro = RawRecord(
                name=nome, kind="given", country="NZ", gender=parse_code(sexo, _SEXO, "sexo"),
                year=parse_count(ano, field="ano"), count=parse_count(contagem),
            )
        except FormatError as e:
            raise FormatError(f"{caminho.name}, linha {linha}: {e}") from e
        if any(c in nome for c in _CORROMPIDO):
            descartadas += 1
            registros += registro.count
            formas[nome] = None
            continue
        yield registro
    if descartadas:
        _log.warning(
            "%s: %d linha(s) com nome corrompido na fonte descartada(s), %d registro(s): %s",
            SOURCE_ID, descartadas, registros, ", ".join(repr(f) for f in sorted(formas)),
        )
