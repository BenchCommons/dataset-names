"""Spec 003b, R1: leitor de planilhas XLS e XLSX (namescommons.spreadsheet)."""

import zipfile
from pathlib import Path

import pytest

from namescommons.adapters import FormatError
from namescommons.spreadsheet import cell_count, rows, sheet_names

FIXTURES = Path(__file__).parent / "fixtures"
NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
NS_R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _xlsx(caminho: Path, abas: list[tuple[str, str]], textos: list[str] = (), alvo="worksheets/sheet{n}.xml",
          ordem=None) -> Path:
    """Grava um XLSX mínimo. abas: (nome, XML do sheetData); textos: XML de cada <si>."""
    ordem = ordem or list(range(1, len(abas) + 1))
    folhas = "".join(f'<sheet name="{nome}" sheetId="{n}" r:id="rId{n}"/>'
                     for n, (nome, _) in zip(ordem, abas))
    rels = "".join(f'<Relationship Id="rId{n}" Type="{REL}/worksheet" Target="{alvo.format(n=n)}"/>'
                   for n in ordem)
    rels += f'<Relationship Id="rId99" Type="{REL}/sharedStrings" Target="sharedStrings.xml"/>'
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("xl/workbook.xml", f'<?xml version="1.0"?><workbook {NS} {NS_R}><sheets>{folhas}</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   f'<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>')
        z.writestr("xl/sharedStrings.xml",
                   f'<?xml version="1.0"?><sst {NS}>' + "".join(f"<si>{t}</si>" for t in textos) + "</sst>")
        for n, (_, dados) in zip(ordem, abas):
            z.writestr(f"xl/worksheets/sheet{n}.xml", f'<?xml version="1.0"?><worksheet {NS}><sheetData>{dados}</sheetData></worksheet>')
    return caminho


TIPOS_XML = (
    '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c></row>'
    '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2"><v>590938</v></c><c r="C2" s="5"><v>58.7</v></c></row>'
    '<row r="3"><c r="A3" t="inlineStr"><is><t>IÑIGO</t></is></c><c r="B3" t="n"><v>1E3</v></c></row>'
    '<row r="4"/>'
    '<row r="5"><c r="A5" t="str"><v>JOANA D\'ARC</v></c><c r="B5" t="b"><v>1</v></c>'
    '<c r="C5" s="3"/><c r="D5" t="b"><v>0</v></c><c r="E5" s="2"/></row>'
    '<row r="7"><c r="C7" t="s"><v>4</v></c></row>'
)
TIPOS_TEXTOS = ["<t>Orden</t>", "<t>Nombre</t>", "<t>Frecuencia</t>", "<t>ANTONIO</t>", "<t>..</t>"]
TIPOS_ESPERADO = [
    (1, ["Orden", "Nombre", "Frecuencia"]),
    (2, ["ANTONIO", 590938, 58.7]),
    (3, ["IÑIGO", 1000]),
    (5, ["JOANA D'ARC", True, None, False]),
    (7, [None, None, ".."]),
]


# R1.1 --------------------------------------------------------------------------------------------

def test_r1_1_sheet_names_na_ordem_do_arquivo(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("Hombres", ""), ("Mujeres", ""), ("Notas", "")])
    assert sheet_names(arq) == ["Hombres", "Mujeres", "Notas"]


def test_r1_1_aba_ausente_lista_as_abas(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("Hombres", ""), ("Mujeres", "")])
    with pytest.raises(FormatError, match=r"a.xlsx: aba 'Varones' não existe; abas: \['Hombres', 'Mujeres'\]"):
        list(rows(arq, "Varones"))


def test_r1_1_numero_da_linha_do_excel_e_coluna_pela_referencia(tmp_path):
    dados = ('<row r="1"><c r="A1"><v>1</v></c></row>'
             '<row r="3"><c r="C3"><v>3</v></c></row>'
             '<row r="10"><c r="AA10"><v>27</v></c></row>')
    arq = _xlsx(tmp_path / "a.xlsx", [("X", dados)])
    assert list(rows(arq, "X")) == [(1, [1]), (3, [None, None, 3]), (10, [None] * 26 + [27])]


# R1.2 --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("conteudo", [
    b"<!DOCTYPE html><html><body>Error 500</body></html>",
    b"",
    b"Orden;Nombre;Frecuencia\n1;ANTONIO;590938\n",
])
def test_r1_2_conteudo_que_nao_e_planilha(tmp_path, conteudo):
    arq = tmp_path / "nombres.xlsx"
    arq.write_bytes(conteudo)
    with pytest.raises(FormatError, match="nombres.xlsx: não é planilha XLS nem XLSX"):
        sheet_names(arq)
    with pytest.raises(FormatError, match="não é planilha XLS nem XLSX"):
        list(rows(arq, "Hombres"))


def test_r1_2_zip_que_nao_e_xlsx(tmp_path):
    arq = tmp_path / "a.xlsx"
    with zipfile.ZipFile(arq, "w") as z:
        z.writestr("nomes.csv", "a,b\n")
    with pytest.raises(FormatError, match="a.xlsx: ZIP sem xl/workbook.xml; não é XLSX"):
        sheet_names(arq)


def test_r1_2_formato_pelo_conteudo_e_nao_pela_extensao(tmp_path):
    arq = _xlsx(tmp_path / "planilha.xls", [("X", '<row r="1"><c r="A1"><v>1</v></c></row>')])
    assert list(rows(arq, "X")) == [(1, [1])]


# R1.3 --------------------------------------------------------------------------------------------

def test_r1_3_tipos_de_celula_xlsx(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("Dados", TIPOS_XML)], TIPOS_TEXTOS)
    obtido = list(rows(arq, "Dados"))
    assert obtido == TIPOS_ESPERADO
    assert [type(v) for v in obtido[1][1]] == [str, int, float]
    assert type(obtido[2][1][1]) is int


def test_r1_3_linhas_vazias_puladas_e_none_final_cortado(tmp_path):
    dados = ('<row r="1"><c r="A1" s="1"/><c r="B1" s="1"/></row>'
             '<row r="2"><c r="A2" t="inlineStr"><is><t></t></is></c><c r="B2"><v>2</v></c><c r="C2" s="1"/></row>'
             '<row r="3"><c r="A3"><v>3</v></c><c r="B3" t="s"/></row>')
    arq = _xlsx(tmp_path / "a.xlsx", [("X", dados)])
    assert list(rows(arq, "X")) == [(2, ["", 2]), (3, [3])]


def test_r1_3_erro_de_formula_nomeia_aba_e_celula(tmp_path):
    dados = '<row r="1"><c r="A1"><v>1</v></c></row><row r="2"><c r="B2" t="e"><v>#N/A</v></c></row>'
    arq = _xlsx(tmp_path / "a.xlsx", [("Hombres", dados)])
    with pytest.raises(FormatError, match=r"a.xlsx, aba 'Hombres', célula B2: erro de fórmula '#N/A'"):
        list(rows(arq, "Hombres"))


def test_r1_3_tipo_de_celula_desconhecido(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("X", '<row r="1"><c r="A1" t="d"><v>2025-01-01</v></c></row>')])
    with pytest.raises(FormatError, match="célula A1: tipo 'd' desconhecido"):
        list(rows(arq, "X"))


def test_r1_3_numero_invalido(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("X", '<row r="1"><c r="A1"><v>doze</v></c></row>')])
    with pytest.raises(FormatError, match="célula A1: número 'doze' inválido"):
        list(rows(arq, "X"))


# R1.4 --------------------------------------------------------------------------------------------

def test_r1_4_texto_compartilhado_com_formatacao_e_rph(tmp_path):
    textos = [
        "<r><rPr><b/></rPr><t>MARIA </t></r><r><t xml:space=\"preserve\">BEGOÑA</t></r>",
        "<t>東京</t><rPh sb=\"0\" eb=\"2\"><t>トウキョウ</t></rPh>",
    ]
    dados = '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
    arq = _xlsx(tmp_path / "a.xlsx", [("X", dados)], textos)
    assert list(rows(arq, "X")) == [(1, ["MARIA BEGOÑA", "東京"])]


def test_r1_4_indice_de_texto_compartilhado_fora_da_tabela(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("X", '<row r="1"><c r="A1" t="s"><v>7</v></c></row>')], ["<t>a</t>"])
    with pytest.raises(FormatError, match="célula A1: texto compartilhado 7 fora da tabela de 1"):
        list(rows(arq, "X"))


@pytest.mark.parametrize("alvo", ["worksheets/sheet{n}.xml", "/xl/worksheets/sheet{n}.xml"])
def test_r1_4_aba_pelo_alvo_das_relacoes(tmp_path, alvo):
    abas = [("Primeira", '<row r="1"><c r="A1"><v>2</v></c></row>'),
            ("Segunda", '<row r="1"><c r="A1"><v>1</v></c></row>')]
    arq = _xlsx(tmp_path / "a.xlsx", abas, alvo=alvo, ordem=[2, 1])
    assert sheet_names(arq) == ["Primeira", "Segunda"]
    assert list(rows(arq, "Primeira")) == [(1, [2])]
    assert list(rows(arq, "Segunda")) == [(1, [1])]


# R1.6 --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("valor, esperado", [
    (590938, 590938), (0, 0), (" 20 ", 20), ("..", None), (None, None),
])
def test_r1_6_cell_count(valor, esperado):
    assert cell_count(valor, {"..", ""}) == esperado


@pytest.mark.parametrize("valor, trecho", [
    (20.5, "contagem 20.5 não é inteiro"),
    (-1, "contagem -1 negativa"),
    (True, "contagem True não é número"),
    ("<20", r"contagem '<20' não é inteiro nem marcador conhecido \['..'\]"),
    (None, "contagem vazia"),
])
def test_r1_6_cell_count_recusa(valor, trecho):
    with pytest.raises(FormatError, match=trecho):
        cell_count(valor, {".."})


def test_r1_6_cell_count_nomeia_o_campo():
    with pytest.raises(FormatError, match="Frecuencia 1.5 não é inteiro"):
        cell_count(1.5, field="Frecuencia")


# R1.3 e R1.5: XLS pelo xlrd ----------------------------------------------------------------------

TIPOS_XLS = FIXTURES / "planilhas" / "tipos.xls"
INE = FIXTURES / "es-ine-residentes"


def test_r1_3_tipos_de_celula_xls():
    assert sheet_names(TIPOS_XLS) == ["Dados", "Erros"]
    obtido = list(rows(TIPOS_XLS, "Dados"))
    assert obtido == TIPOS_ESPERADO
    assert [type(v) for v in obtido[1][1]] == [str, int, float]
    assert [type(v) for v in obtido[3][1]] == [str, bool, type(None), bool]


def test_r1_3_erro_de_formula_xls():
    with pytest.raises(FormatError, match=r"tipos.xls, aba 'Erros', célula B2: erro de fórmula '#N/A'"):
        list(rows(TIPOS_XLS, "Erros"))


def test_r1_3_mesmos_valores_nos_dois_formatos(tmp_path):
    xlsx = _xlsx(tmp_path / "tipos.xlsx", [("Dados", TIPOS_XML)], TIPOS_TEXTOS)
    assert list(rows(xlsx, "Dados")) == list(rows(TIPOS_XLS, "Dados"))


def test_r1_1_aba_ausente_xls():
    with pytest.raises(FormatError, match=r"tipos.xls: aba 'Notas' não existe; abas: \['Dados', 'Erros'\]"):
        list(rows(TIPOS_XLS, "Notas"))


def test_r1_3_amostras_do_ine():
    nomes = INE / "nombres_por_edad_media.xlsx"
    assert sheet_names(nomes) == ["Hombres", "Mujeres"]
    assert list(rows(nomes, "Hombres"))[:5] == [
        (1, ["Frecuencias de nombres masculinos"]),
        (2, ["Datos procedentes de Censos de población anuales a fecha 01/01/2025"]),
        (4, ["Nombres masculinos con frecuencia mayor o igual a 20 a nivel nacional."]),
        (5, ["(*) Edad media de las personas que tienen ese nombre a nivel nacional."]),
        (7, ["Orden", "Nombre", "Frecuencia", "Edad Media (*)"]),
    ]
    assert list(rows(nomes, "Mujeres"))[-1] == (32328, [32321, "ZULMA PATRICIA", 20, 43])
    apellidos = INE / "apellidos_frecuencia.xls"
    assert sheet_names(apellidos) == ["Apellidos >=100", "Apellidos >=20 y <=99"]
    obtido = list(rows(apellidos, "Apellidos >=100"))
    assert obtido[2:6] == [
        (3, ["Datos procedentes de Censos de población anuales a fecha 01/01/2025"]),
        (4, [None, None, "Apellido 1º", "Apellido 2º", "Ambos apellidos"]),
        (5, ["Orden", "Apellido", "Total", "Total", "Total"]),
        (6, [1, "GARCIA", 1446937, 1468824, 74765, 74765, 1468824]),
    ]
    assert obtido[-2] == (16097, [16092, "LYU", 208, "..", "..", 9999999, 9999999])


def test_r1_5_xls_corrompido(tmp_path):
    arq = tmp_path / "quebrado.xls"
    arq.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 600)
    with pytest.raises(FormatError, match="quebrado.xls: XLS ilegível"):
        sheet_names(arq)


def test_r1_5_xlrd_fixado():
    import tomllib
    projeto = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8"))
    assert "xlrd==2.0.2" in projeto["project"]["dependencies"]


# Revisão do PR #27: entradas malformadas e ZIP desproporcional viram FormatError ------------------

def test_membro_da_aba_ausente_no_zip(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("X", "")], alvo="worksheets/nao_existe{n}.xml")
    with pytest.raises(FormatError, match=r"a.xlsx: aba 'X' aponta para xl/worksheets/nao_existe1.xml, ausente do ZIP"):
        list(rows(arq, "X"))


def test_indice_de_texto_compartilhado_nao_inteiro(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("X", '<row r="1"><c r="A1" t="s"><v>abc</v></c></row>')], ["<t>a</t>"])
    with pytest.raises(FormatError, match="célula A1: índice de texto compartilhado 'abc' não é inteiro"):
        list(rows(arq, "X"))


@pytest.mark.parametrize("ref, trecho", [
    ("XFE1", "célula XFE1: coluna além de XFD"),
    ("1A", "referência de célula '1A' inválida"),
    ("a1", "referência de célula 'a1' inválida"),
])
def test_referencia_de_celula_invalida(tmp_path, ref, trecho):
    arq = _xlsx(tmp_path / "a.xlsx", [("X", f'<row r="1"><c r="{ref}"><v>1</v></c></row>')])
    with pytest.raises(FormatError, match=trecho):
        list(rows(arq, "X"))


def test_numero_de_linha_invalido(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("X", '<row r="x"><c r="A1"><v>1</v></c></row>')])
    with pytest.raises(FormatError, match="linha 'x' inválida"):
        list(rows(arq, "X"))


def test_zip_com_taxa_de_compressao_desproporcional(tmp_path):
    enchimento = " " * 3_000_000
    arq = _xlsx(tmp_path / "a.xlsx", [("X", f'<row r="1"><c r="A1"><v>1</v></c></row>{enchimento}')])
    with pytest.raises(FormatError, match=r"a.xlsx: membro xl/worksheets/sheet1.xml descompacta 3\d{6} bytes, .*taxa"):
        list(rows(arq, "X"))


def test_zip_com_membro_grande_demais(tmp_path, monkeypatch):
    import namescommons.spreadsheet as planilha
    monkeypatch.setattr(planilha, "_MAX_MEMBRO", 100)
    arq = _xlsx(tmp_path / "a.xlsx", [("X", '<row r="1"><c r="A1"><v>1</v></c></row>')])
    with pytest.raises(FormatError, match=r"a.xlsx: membro xl/workbook.xml descompacta \d+ bytes, acima do limite de 100"):
        sheet_names(arq)


def test_linhas_lidas_saem_da_arvore(tmp_path):
    """Memória plana: a aba de 63 mil linhas do INE não acumula elementos <row> já lidos."""
    import namescommons.spreadsheet as planilha
    dados = "".join(f'<row r="{i}"><c r="A{i}"><v>{i}</v></c></row>' for i in range(1, 2001))
    arq = _xlsx(tmp_path / "a.xlsx", [("X", dados)])
    vistos = []
    original = planilha.ET.iterparse

    def espia(*args, **kwargs):
        it = original(*args, **kwargs)
        for evento, el in it:
            yield evento, el
            if evento == "end" and el.tag.endswith("sheetData"):
                vistos.append(len(el))

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(planilha.ET, "iterparse", espia)
    try:
        assert sum(1 for _ in rows(arq, "X")) == 2000
    finally:
        monkeypatch.undo()
    assert vistos == [0]


# Defesa em profundidade contra DTD (ADR 0005) -----------------------------------------------------

def _regravar(origem: Path, destino: Path, membro: str, conteudo: str) -> Path:
    with zipfile.ZipFile(origem) as zin, zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zout.writestr(info.filename, conteudo if info.filename == membro else zin.read(info.filename))
    return destino


BILLION_LAUGHS = (
    '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
    '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
    '<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">]>'
    f'<worksheet {NS}><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>&lol3;</t></is></c></row></sheetData></worksheet>'
)


@pytest.mark.parametrize("membro, operacao", [
    ("xl/workbook.xml", lambda a: sheet_names(a)),
    ("xl/_rels/workbook.xml.rels", lambda a: sheet_names(a)),
    ("xl/sharedStrings.xml", lambda a: list(rows(a, "X"))),
    ("xl/worksheets/sheet1.xml", lambda a: list(rows(a, "X"))),
])
@pytest.mark.parametrize("prolog", [
    '<!DOCTYPE x [<!ENTITY a "b">]>',
    '<!doctype x>',
    '<!-- c --><!ENTITY a "b">',
])
def test_r1_4_dtd_no_prologo_e_recusado(tmp_path, membro, operacao, prolog):
    base = _xlsx(tmp_path / "base.xlsx", [("X", '<row r="1"><c r="A1"><v>1</v></c></row>')])
    raiz = {"xl/workbook.xml": f"<workbook {NS} {NS_R}/>", "xl/_rels/workbook.xml.rels": "<Relationships/>",
            "xl/sharedStrings.xml": f"<sst {NS}/>", "xl/worksheets/sheet1.xml": f"<worksheet {NS}/>"}[membro]
    arq = _regravar(base, tmp_path / "a.xlsx", membro, f'<?xml version="1.0"?>{prolog}{raiz}')
    with pytest.raises(FormatError, match=rf"a\.xlsx: membro {membro} tem DTD"):
        operacao(arq)


def test_r1_4_billion_laughs_falha_pela_checagem_de_dtd(tmp_path):
    base = _xlsx(tmp_path / "base.xlsx", [("X", '<row r="1"><c r="A1"><v>1</v></c></row>')])
    arq = _regravar(base, tmp_path / "a.xlsx", "xl/worksheets/sheet1.xml", BILLION_LAUGHS)
    with pytest.raises(FormatError, match=r"a\.xlsx: membro xl/worksheets/sheet1\.xml tem DTD"):
        list(rows(arq, "X"))


def test_r1_4_doctype_dentro_de_comentario_nao_e_dtd(tmp_path):
    base = _xlsx(tmp_path / "base.xlsx", [("X", '<row r="1"><c r="A1"><v>1</v></c></row>')])
    conteudo = f'<?xml version="1.0"?><!-- <!DOCTYPE x> --><worksheet {NS}><sheetData><row r="1"><c r="A1"><v>7</v></c></row></sheetData></worksheet>'
    arq = _regravar(base, tmp_path / "a.xlsx", "xl/worksheets/sheet1.xml", conteudo)
    assert list(rows(arq, "X")) == [(1, [7])]


def test_r1_4_texto_com_doctype_depois_da_raiz_nao_e_dtd(tmp_path):
    arq = _xlsx(tmp_path / "a.xlsx", [("X", '<row r="1"><c r="A1" t="inlineStr"><is><t>&lt;!DOCTYPE</t></is></c></row>')])
    assert list(rows(arq, "X")) == [(1, ["<!DOCTYPE"])]


def test_r1_4_prologo_gigante_e_recusado(tmp_path):
    base = _xlsx(tmp_path / "base.xlsx", [("X", '<row r="1"><c r="A1"><v>1</v></c></row>')])
    conteudo = '<?xml version="1.0"?><!--' + "x" * 70_000 + f'--><worksheet {NS}/>'
    arq = _regravar(base, tmp_path / "a.xlsx", "xl/worksheets/sheet1.xml", conteudo)
    with pytest.raises(FormatError, match=r"a\.xlsx: membro xl/worksheets/sheet1\.xml tem prólogo acima de 65536 bytes"):
        list(rows(arq, "X"))


def test_r1_4_xlsx_normal_com_bom_continua_lido(tmp_path):
    base = _xlsx(tmp_path / "base.xlsx", [("X", "")])
    conteudo = '﻿<?xml version="1.0" encoding="UTF-8"?>\n' + f'<worksheet {NS}><sheetData><row r="1"><c r="A1"><v>3</v></c></row></sheetData></worksheet>'
    arq = _regravar(base, tmp_path / "a.xlsx", "xl/worksheets/sheet1.xml", conteudo)
    assert list(rows(arq, "X")) == [(1, [3])]


def test_r1_4_300_mil_linhas_em_fluxo_com_memoria_plana(tmp_path):
    import tracemalloc
    n = 300_000
    dados = "".join(f'<row r="{i}"><c r="A{i}"><v>{i}</v></c><c r="B{i}" t="inlineStr"><is><t>NOME{i}</t></is></c></row>'
                    for i in range(1, n + 1))
    arq = _xlsx(tmp_path / "a.xlsx", [("X", dados)])
    del dados
    tracemalloc.start()
    try:
        total = ultimo = 0
        for numero, valores in rows(arq, "X"):
            total += 1
            ultimo = valores[0]
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert (total, ultimo) == (n, n)
    assert pico < 5 * 1024 * 1024, f"pico de {pico} bytes: a aba não está sendo lida em fluxo"


@pytest.mark.parametrize("membro, operacao", [
    ("xl/workbook.xml", lambda a: sheet_names(a)),
    ("xl/_rels/workbook.xml.rels", lambda a: sheet_names(a)),
    ("xl/sharedStrings.xml", lambda a: list(rows(a, "X"))),
    ("xl/worksheets/sheet1.xml", lambda a: list(rows(a, "X"))),
])
@pytest.mark.parametrize("prolog", [
    '<!DOCTYPE l [<!ENTITY a "AAAA"><!ENTITY b "&a;&a;">]>',
    '<!-- c --><!DOCTYPE l [<!ENTITY a "AAAA">]>',
])
def test_r1_4_dtd_depois_de_bom_utf8_e_recusado(tmp_path, membro, operacao, prolog):
    base = _xlsx(tmp_path / "base.xlsx", [("X", '<row r="1"><c r="A1"><v>1</v></c></row>')])
    raiz = {"xl/workbook.xml": f"<workbook {NS} {NS_R}/>", "xl/_rels/workbook.xml.rels": "<Relationships/>",
            "xl/sharedStrings.xml": f"<sst {NS}/>", "xl/worksheets/sheet1.xml": f"<worksheet {NS}/>"}[membro]
    arq = _regravar(base, tmp_path / "a.xlsx", membro, f'﻿<?xml version="1.0"?>{prolog}{raiz}')
    with pytest.raises(FormatError, match=rf"a\.xlsx: membro {membro} tem DTD"):
        operacao(arq)
