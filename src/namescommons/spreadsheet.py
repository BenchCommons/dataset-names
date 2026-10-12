"""Leitor de planilhas XLS e XLSX para adaptadores de fontes (spec 003b, R1; ADR 0005).

O formato é reconhecido pelos primeiros bytes. XLSX é lido em fluxo com a biblioteca padrão;
XLS, com xlrd. Os dois devolvem valores do mesmo tipo: str, int, float, bool ou None.
"""

import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from pathlib import Path

import xlrd

from namescommons.adapters import FormatError, parse_count

_ZIP = b"PK\x03\x04"
_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_DOC = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_REL_PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_ROW, _C, _V, _IS, _T, _R, _SI, _SHEET, _SHEET_DATA = (
    _MAIN + n for n in ("row", "c", "v", "is", "t", "r", "si", "sheet", "sheetData")
)
_REF = re.compile(r"([A-Z]{1,3})([0-9]+)")
_MAX_COLUNAS = 16384  # XFD, a última coluna do Excel
# Proteção contra ZIP desproporcional: membro acima de 1 GiB, ou acima de 1 MiB com taxa maior que 100:1.
_MAX_MEMBRO = 1 << 30
_MAX_TAXA = 100
_MIN_BYTES_TAXA = 1 << 20
_INTEIRO = re.compile(r"-?[0-9]+")
# Defesa em profundidade (ADR 0005): membro XML com DTD é recusado antes de ir ao parser.
_MAX_PROLOGO = 1 << 16
_ESPACO = re.compile(r"[\s\ufeff]*")


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


def _membro(z: zipfile.ZipFile, nome: str, caminho: Path):
    """Abre um membro do ZIP depois de conferir o tamanho descompactado declarado."""
    try:
        info = z.getinfo(nome)
    except KeyError:
        raise FormatError(f"{caminho.name}: membro {nome} ausente do ZIP") from None
    tamanho, compactado = info.file_size, max(info.compress_size, 1)
    if tamanho > _MAX_MEMBRO:
        raise FormatError(f"{caminho.name}: membro {nome} descompacta {tamanho} bytes, acima do limite de {_MAX_MEMBRO}")
    if tamanho > _MIN_BYTES_TAXA and tamanho / compactado > _MAX_TAXA:
        raise FormatError(f"{caminho.name}: membro {nome} descompacta {tamanho} bytes, "
                          f"taxa de compressão {tamanho // compactado}:1 acima de {_MAX_TAXA}:1")
    return _SemDtd(z.open(info), nome, caminho)


class _SemDtd(io.RawIOBase):
    """Fluxo de um membro XML que recusa DTD no prólogo e depois repassa os bytes ao parser.

    Lê no máximo 64 KiB, até a primeira tag de elemento, e devolve esse prefixo ao parser antes
    do resto do fluxo; a leitura em fluxo de abas grandes continua igual.
    """

    def __init__(self, fh, nome: str, caminho: Path):
        super().__init__()
        self._fh = fh
        prefixo = b""
        while True:
            parte = fh.read(4096)
            prefixo += parte
            decisao = _prologo(prefixo)
            if decisao == "dtd":
                fh.close()
                raise FormatError(f"{caminho.name}: membro {nome} tem DTD (DOCTYPE ou ENTITY); recusado")
            if decisao == "raiz" or not parte:
                break
            if len(prefixo) >= _MAX_PROLOGO:
                fh.close()
                raise FormatError(f"{caminho.name}: membro {nome} tem prólogo acima de {_MAX_PROLOGO} bytes sem elemento raiz")
        self._prefixo = memoryview(prefixo)

    def readable(self) -> bool:
        return True

    def readinto(self, buf) -> int:
        if self._prefixo:
            n = min(len(buf), len(self._prefixo))
            buf[:n] = self._prefixo[:n]
            self._prefixo = self._prefixo[n:]
            return n
        return self._fh.readinto(buf)

    def close(self) -> None:
        self._fh.close()
        super().close()


def _prologo(dados: bytes) -> str:
    """'dtd' se há DOCTYPE/ENTITY antes do elemento raiz, 'raiz' se a raiz já começou, senão 'mais'."""
    if dados[:2] in (b"\xff\xfe", b"\xfe\xff"):
        texto = dados.decode("utf-16", errors="replace")
    elif b"\x00" in dados[:4]:
        texto = dados.decode("utf-16-le" if dados[1:2] == b"\x00" else "utf-16-be", errors="replace")
    else:
        # UTF-8 (BOM opcional). UTF-32 e EBCDIC não são inspecionados e falham no expat.
        texto = dados.removeprefix(b"\xef\xbb\xbf").decode("utf-8", errors="replace")
    i = 0
    while True:
        i = _ESPACO.match(texto, i).end()
        if i >= len(texto):
            return "mais"
        if texto.startswith("<?", i):
            fim, salto = texto.find("?>", i), 2
        elif texto.startswith("<!--", i):
            fim, salto = texto.find("-->", i), 3
        elif texto[i:i + 9].upper() == "<!DOCTYPE" or texto[i:i + 8].upper() == "<!ENTITY":
            return "dtd"
        elif len(texto) - i < 9 and any(marca.startswith(texto[i:].upper()) for marca in ("<!DOCTYPE", "<!ENTITY", "<!--")):
            return "mais"  # prefixo curto demais para decidir
        else:
            return "raiz"  # elemento raiz (ou lixo, que o parser descreve)
        if fim < 0:
            return "mais"
        i = fim + salto


def _xlsx_abas(z: zipfile.ZipFile, caminho: Path) -> list[tuple[str, str]]:
    """(nome, membro do ZIP) de cada aba, na ordem de xl/workbook.xml."""
    try:
        with _membro(z, "xl/workbook.xml", caminho) as fh:
            livro = ET.parse(fh).getroot()
        with _membro(z, "xl/_rels/workbook.xml.rels", caminho) as fh:
            rels = ET.parse(fh).getroot()
    except ET.ParseError as e:
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
    with _membro(z, "xl/sharedStrings.xml", caminho) as fh:
        try:
            for _, el in ET.iterparse(fh):
                if el.tag == _SI:
                    textos.append(_texto(el))
                    el.clear()
        except ET.ParseError as e:
            raise FormatError(f"{caminho.name}: sharedStrings.xml ilegível: {e}") from None
    return textos


def _coluna(ref: str, onde: str) -> int:
    """Índice da coluna (A = 0) de uma referência como 'C7'."""
    m = _REF.fullmatch(ref)
    if not m:
        raise FormatError(f"{onde}: referência de célula {ref!r} inválida")
    n = 0
    for letra in m.group(1):
        n = n * 26 + ord(letra) - ord("A") + 1
    if n > _MAX_COLUNAS:
        raise FormatError(f"{onde}, célula {ref}: coluna além de XFD")
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
        try:
            indice = int(v.text)
        except ValueError:
            raise FormatError(f"{onde}: índice de texto compartilhado {v.text!r} não é inteiro") from None
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
        if membro not in z.namelist():
            raise FormatError(f"{caminho.name}: aba {sheet!r} aponta para {membro}, ausente do ZIP")
        with _membro(z, membro, caminho) as fh:
            numero, pai = 0, None
            try:
                for evento, el in ET.iterparse(fh, events=("start", "end")):
                    if evento == "start":
                        if el.tag == _SHEET_DATA:
                            pai = el
                        continue
                    if el.tag != _ROW:
                        continue
                    r = el.get("r")
                    if r is None:
                        numero += 1
                    elif r.isdigit():
                        numero = int(r)
                    else:
                        raise FormatError(f"{prefixo}: linha {r!r} inválida")
                    valores: list = []
                    for c in el.iter(_C):
                        ref = c.get("r")
                        posicao = len(valores) if ref is None else _coluna(ref, prefixo)
                        valores.extend([None] * (posicao - len(valores) + 1))
                        valores[posicao] = _valor(c, textos, f"{prefixo}, célula {ref or posicao}")
                    # Tira a linha lida da árvore: a memória fica plana na aba inteira.
                    el.clear()
                    if pai is not None:
                        pai.remove(el)
                    if _sem_none_final(valores):
                        yield numero, valores
            except ET.ParseError as e:
                raise FormatError(f"{prefixo}: XML ilegível: {e}") from None


# XLS ----------------------------------------------------------------------------------------------

def _xls_abrir(caminho: Path):
    try:
        return xlrd.open_workbook(caminho, on_demand=True)
    except Exception as e:  # xlrd levanta XLRDError, CompDocError, AssertionError e outras
        raise FormatError(f"{caminho.name}: XLS ilegível: {type(e).__name__}: {e}") from None


def _xls_sheet_names(caminho: Path) -> list[str]:
    livro = _xls_abrir(caminho)
    try:
        return livro.sheet_names()
    finally:
        livro.release_resources()


def _xls_valor(celula, onde: str):
    tipo = celula.ctype
    if tipo in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return None
    if tipo == xlrd.XL_CELL_TEXT:
        return celula.value
    if tipo in (xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_DATE):
        valor = float(celula.value)
        return int(valor) if valor.is_integer() else valor
    if tipo == xlrd.XL_CELL_BOOLEAN:
        return bool(celula.value)
    if tipo == xlrd.XL_CELL_ERROR:
        texto = xlrd.error_text_from_code.get(celula.value, f"código {celula.value}")
        raise FormatError(f"{onde}: erro de fórmula {texto!r}")
    raise FormatError(f"{onde}: tipo de célula {tipo} desconhecido")


def _xls_rows(caminho: Path, sheet: str) -> Iterator[tuple[int, list]]:
    livro = _xls_abrir(caminho)
    try:
        if sheet not in livro.sheet_names():
            raise FormatError(f"{caminho.name}: aba {sheet!r} não existe; abas: {livro.sheet_names()}")
        try:
            aba = livro.sheet_by_name(sheet)
        except Exception as e:
            raise FormatError(f"{caminho.name}, aba {sheet!r}: XLS ilegível: {type(e).__name__}: {e}") from None
        prefixo = f"{caminho.name}, aba {sheet!r}"
        for i in range(aba.nrows):
            valores = [
                _xls_valor(celula, f"{prefixo}, célula {xlrd.cellname(i, j)}")
                for j, celula in enumerate(aba.row(i))
            ]
            if _sem_none_final(valores):
                yield i + 1, valores
    finally:
        livro.release_resources()
