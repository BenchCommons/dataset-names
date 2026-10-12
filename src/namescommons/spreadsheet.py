"""Leitor de planilhas XLS e XLSX para adaptadores de fontes (spec 003b, R1; ADR 0004).

O formato é reconhecido pelos primeiros bytes. XLSX é lido em fluxo com a biblioteca padrão;
XLS, com xlrd. Os dois devolvem valores do mesmo tipo: str, int, float, bool ou None.
"""

import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from pathlib import Path

from namescommons.adapters import FormatError, parse_count

_ZIP = b"PK\x03\x04"
_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_DOC = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_REL_PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_ROW, _C, _V, _IS, _T, _R, _SI, _SHEET = (
    _MAIN + n for n in ("row", "c", "v", "is", "t", "r", "si", "sheet")
)
_REF = re.compile(r"([A-Z]+)([0-9]+)")
_INTEIRO = re.compile(r"-?[0-9]+")


def _formato(caminho: Path) -> str:
    with open(caminho, "rb") as fh:
        inicio = fh.read(8)
    if inicio.startswith(_ZIP):
        return "xlsx"
    if inicio == _OLE2:
        return "xls"
    raise FormatError(f"{caminho.name}: não é planilha XLS nem XLSX (começa com {inicio!r})")


def sheet_names(path: str | Path) -> list[str]:
    """Abas na ordem do arquivo."""
    caminho = Path(path)
    if _formato(caminho) == "xls":
        return _xls_sheet_names(caminho)
    with _abrir_zip(caminho) as z:
        return [nome for nome, _ in _xlsx_abas(z, caminho)]


def rows(path: str | Path, sheet: str) -> Iterator[tuple[int, list]]:
    """(número da linha no Excel, valores por coluna) de cada linha não vazia da aba."""
    caminho = Path(path)
    if _formato(caminho) == "xls":
        yield from _xls_rows(caminho, sheet)
    else:
        yield from _xlsx_rows(caminho, sheet)


def cell_count(value: object, missing: Iterable[str] = (), field: str = "contagem") -> int | None:
    """Contagem de uma célula (spec 003b, R1.6). Marcador de `missing` vira None; o resto é FormatError."""
    marcadores = set(missing)
    if value is None:
        if "" in marcadores:
            return None
        raise FormatError(f"{field} vazia; esperava inteiro ou marcador conhecido {sorted(marcadores)}")
    if isinstance(value, bool):
        raise FormatError(f"{field} {value!r} não é número")
    if isinstance(value, float):
        if not value.is_integer():
            raise FormatError(f"{field} {value!r} não é inteiro")
        value = int(value)
    if isinstance(value, int):
        if value < 0:
            raise FormatError(f"{field} {value!r} negativa")
        return value
    if isinstance(value, str):
        return parse_count(value, marcadores, field)
    raise FormatError(f"{field} {value!r} de tipo {type(value).__name__} inesperado")


def _sem_none_final(valores: list) -> list:
    while valores and valores[-1] is None:
        valores.pop()
    return valores


# XLSX ---------------------------------------------------------------------------------------------

def _abrir_zip(caminho: Path) -> zipfile.ZipFile:
    try:
        z = zipfile.ZipFile(caminho)
    except zipfile.BadZipFile as e:
        raise FormatError(f"{caminho.name}: XLSX corrompido: {e}") from None
    if "xl/workbook.xml" not in z.namelist():
        z.close()
        raise FormatError(f"{caminho.name}: ZIP sem xl/workbook.xml; não é XLSX")
    return z


def _xlsx_abas(z: zipfile.ZipFile, caminho: Path) -> list[tuple[str, str]]:
    """(nome, membro do ZIP) de cada aba, na ordem de xl/workbook.xml."""
    try:
        livro = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    except (KeyError, ET.ParseError) as e:
        raise FormatError(f"{caminho.name}: workbook do XLSX ilegível: {e}") from None
    alvos = {r.get("Id"): r.get("Target", "") for r in rels.iter(_REL_PKG + "Relationship")}
    abas = []
    for folha in livro.iter(_SHEET):
        alvo = alvos.get(folha.get(_REL_DOC + "id"))
        if alvo is None:
            raise FormatError(f"{caminho.name}: aba {folha.get('name')!r} sem relação em workbook.xml.rels")
        membro = alvo.lstrip("/") if alvo.startswith("/") else posixpath.normpath(posixpath.join("xl", alvo))
        abas.append((folha.get("name"), membro))
    return abas


def _texto(elemento: ET.Element) -> str:
    """Texto de <si> ou <is>: <t> diretos e de trechos <r>; a leitura fonética <rPh> fica fora."""
    partes = []
    for filho in elemento:
        if filho.tag == _T:
            partes.append(filho.text or "")
        elif filho.tag == _R:
            partes.extend(t.text or "" for t in filho.iter(_T))
    return "".join(partes)


def _textos_compartilhados(z: zipfile.ZipFile, caminho: Path) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    textos = []
    with z.open("xl/sharedStrings.xml") as fh:
        try:
            for _, el in ET.iterparse(fh):
                if el.tag == _SI:
                    textos.append(_texto(el))
                    el.clear()
        except ET.ParseError as e:
            raise FormatError(f"{caminho.name}: sharedStrings.xml ilegível: {e}") from None
    return textos


def _coluna(letras: str) -> int:
    n = 0
    for letra in letras:
        n = n * 26 + ord(letra) - ord("A") + 1
    return n - 1


def _numero(texto: str, onde: str) -> int | float:
    texto = texto.strip()
    if _INTEIRO.fullmatch(texto):
        return int(texto)
    try:
        valor = float(texto)
    except ValueError:
        raise FormatError(f"{onde}: número {texto!r} inválido") from None
    return int(valor) if valor.is_integer() else valor


def _valor(c: ET.Element, textos: list[str], onde: str):
    tipo = c.get("t", "n")
    v = c.find(_V)
    if tipo == "inlineStr":
        bloco = c.find(_IS)
        return None if bloco is None else _texto(bloco)
    if v is None or v.text is None:
        return "" if tipo == "str" and v is not None else None
    if tipo == "s":
        indice = int(v.text)
        if not 0 <= indice < len(textos):
            raise FormatError(f"{onde}: texto compartilhado {indice} fora da tabela de {len(textos)}")
        return textos[indice]
    if tipo == "str":
        return v.text
    if tipo == "n":
        return _numero(v.text, onde)
    if tipo == "b":
        return v.text.strip() == "1"
    if tipo == "e":
        raise FormatError(f"{onde}: erro de fórmula {v.text!r}")
    raise FormatError(f"{onde}: tipo {tipo!r} desconhecido")


def _xlsx_rows(caminho: Path, sheet: str) -> Iterator[tuple[int, list]]:
    with _abrir_zip(caminho) as z:
        abas = _xlsx_abas(z, caminho)
        membro = dict(abas).get(sheet)
        if membro is None:
            raise FormatError(f"{caminho.name}: aba {sheet!r} não existe; abas: {[n for n, _ in abas]}")
        textos = _textos_compartilhados(z, caminho)
        prefixo = f"{caminho.name}, aba {sheet!r}"
        with z.open(membro) as fh:
            numero = 0
            try:
                for _, el in ET.iterparse(fh):
                    if el.tag != _ROW:
                        continue
                    numero = int(el.get("r", numero + 1))
                    valores: list = []
                    for c in el.iter(_C):
                        ref = c.get("r")
                        m = _REF.fullmatch(ref or "")
                        posicao = _coluna(m.group(1)) if m else len(valores)
                        valores.extend([None] * (posicao - len(valores) + 1))
                        valores[posicao] = _valor(c, textos, f"{prefixo}, célula {ref or posicao}")
                    el.clear()
                    if _sem_none_final(valores):
                        yield numero, valores
            except ET.ParseError as e:
                raise FormatError(f"{prefixo}: XML ilegível: {e}") from None


# XLS ----------------------------------------------------------------------------------------------

def _xls_sheet_names(caminho: Path) -> list[str]:
    raise FormatError(f"{caminho.name}: XLS ainda não suportado")


def _xls_rows(caminho: Path, sheet: str) -> Iterator[tuple[int, list]]:
    raise FormatError(f"{caminho.name}: XLS ainda não suportado")
