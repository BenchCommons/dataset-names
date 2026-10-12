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
    with zipfile.ZipFile(caminho, "w") as z:
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
