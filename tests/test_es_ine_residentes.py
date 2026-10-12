"""Spec 003b, R2: adaptador do INE (Espanha) sobre as amostras reais em tests/fixtures/es-ine-residentes/."""

import zipfile
from pathlib import Path

import pytest

from namescommons.adapters import FormatError, RawRecord, load_adapter
from namescommons.sources import load_sources

RAIZ = Path(__file__).resolve().parent.parent
AMOSTRA = RAIZ / "tests" / "fixtures" / "es-ine-residentes"
NOMES, APELLIDOS = "nombres_por_edad_media.xlsx", "apellidos_frecuencia.xls"
ARQUIVOS = {NOMES: AMOSTRA / NOMES, APELLIDOS: AMOSTRA / APELLIDOS}


def _g(nome, sexo, n):
    return RawRecord(nome, "given", "ES", sexo, 2025, n)


def _f(nome, n):
    return RawRecord(nome, "family", "ES", None, 2025, n)


ESPERADO = [
    _g("ANTONIO", "M", 590938), _g("IÑIGO", "M", 22083), _g("ANDREA", "M", 3043),
    _g("LLORENÇ", "M", 2513), _g("FRANCESC D'ASSIS", "M", 192), _g("ZUNAIR", "M", 20),
    _g("MARIA CARMEN", "F", 618622), _g("ANDREA", "F", 110011), _g("BEGOÑA", "F", 36293),
    _g("FRANÇOISE", "F", 338), _g("JOANA D'ARC", "F", 21), _g("ZULMA PATRICIA", "F", 20),
    _f("GARCIA", 1446937), _f("MUÑOZ", 284951), _f("GONÇALVES", 3020), _f("O'BRIEN", 573),
    _f("LYU", 208), _f("TUDORICA", 100), _f("ANCHUSTEGUI", 99), _f("NEL·LO", 26), _f("ZRHAIDA", 20),
]


@pytest.fixture
def mod():
    return load_adapter("es-ine-residentes")


def test_parse_da_amostra_real(mod):
    assert list(mod.parse(ARQUIVOS)) == ESPERADO


def test_resources_apontam_para_o_ine(mod):
    assert [(r.url, r.filename) for r in mod.RESOURCES] == [
        ("https://www.ine.es/daco/daco42/nombyapel/nombres_por_edad_media.xlsx", NOMES),
        ("https://www.ine.es/daco/daco42/nombyapel/apellidos_frecuencia.xls", APELLIDOS),
    ]


def test_r2_1_uma_fonte_population_para_nomes_e_sobrenomes(mod):
    fonte = load_sources(RAIZ / "sources.yaml")["es-ine-residentes"]
    assert (fonte.country, fonte.count_type, fonte.primary, fonte.suppression, fonte.uniform_case) == (
        "ES", "population", True, 20, True)
    assert fonte.license == "CC-BY-4.0"
    assert {r.kind for r in mod.parse(ARQUIVOS)} == {"given", "family"}


# Amostra XLSX alterada: troca textos compartilhados no XML -------------------------------------------

def _xlsx_alterado(tmp_path: Path, trocas: dict[str, str], membro="xl/sharedStrings.xml") -> dict[str, Path]:
    destino = tmp_path / NOMES
    with zipfile.ZipFile(AMOSTRA / NOMES) as orig, zipfile.ZipFile(destino, "w") as novo:
        for item in orig.infolist():
            dados = orig.read(item.filename)
            if item.filename == membro:
                texto = dados.decode("utf-8")
                for antes, depois in trocas.items():
                    assert antes in texto, antes
                    texto = texto.replace(antes, depois)
                dados = texto.encode("utf-8")
            novo.writestr(item, dados)
    return {NOMES: destino, APELLIDOS: AMOSTRA / APELLIDOS}


def test_r2_3_ano_da_edicao_vem_do_conteudo(mod, tmp_path, monkeypatch):
    arquivos = _xlsx_alterado(tmp_path, {"a fecha 01/01/2025": "a fecha 01/01/2026"})
    nova = ["Datos procedentes de Censos de población anuales a fecha 01/01/2026"]
    _linhas_xls(mod, monkeypatch, lambda aba, n, v: nova if n == 3 else v)
    assert {r.year for r in mod.parse(arquivos)} == {2026}


def test_r2_3_arquivos_de_edicoes_diferentes_falham(mod, tmp_path):
    """O INE atualizou um arquivo e não o outro: ficar só com a edição mais recente apagaria o outro kind."""
    arquivos = _xlsx_alterado(tmp_path, {"a fecha 01/01/2025": "a fecha 01/01/2026"})
    with pytest.raises(FormatError, match=r"edições diferentes entre as abas: .*Hombres.*2026.*Apellidos >=100.*2025"):
        next(mod.parse(arquivos))


def test_r2_3_abas_de_nomes_de_edicoes_diferentes_falham(mod, monkeypatch):
    original = mod.rows

    def rows(caminho, aba):
        for numero, valores in original(caminho, aba):
            if aba == "Mujeres" and numero == 2:
                valores = ["Datos procedentes de Censos de población anuales a fecha 01/01/2024"]
            yield numero, valores

    monkeypatch.setattr(mod, "rows", rows)
    with pytest.raises(FormatError, match=r"edições diferentes entre as abas: .*'Hombres': 2025.*'Mujeres': 2024"):
        next(mod.parse(ARQUIVOS))


def test_r2_3_sem_a_frase_da_data_falha(mod, tmp_path):
    arquivos = _xlsx_alterado(tmp_path, {"a fecha 01/01/2025": "en 2025"})
    with pytest.raises(FormatError, match=r"nombres_por_edad_media.xlsx, aba 'Hombres': .*'a fecha DD/MM/AAAA' antes do cabeçalho"):
        list(mod.parse(arquivos))


def test_r2_4_aba_desconhecida_falha(mod, tmp_path):
    arquivos = _xlsx_alterado(tmp_path, {'name="Mujeres"': 'name="Total"'}, membro="xl/workbook.xml")
    with pytest.raises(FormatError, match=r"aba de nomes 'Total' unknown; expected one of \['Hombres', 'Mujeres'\]"):
        list(mod.parse(arquivos))


def test_r2_4_cabecalho_dos_nomes_trocado_falha(mod, tmp_path):
    arquivos = _xlsx_alterado(tmp_path, {"<t>Frecuencia</t>": "<t>Tanto por mil</t>"})
    with pytest.raises(FormatError, match=r"aba 'Hombres': cabeçalho \['Orden', 'Nombre', 'Frecuencia'\] não encontrado"):
        list(mod.parse(arquivos))


# Amostra XLS alterada: substitui as linhas que o leitor devolve --------------------------------------

def _linhas_xls(mod, monkeypatch, altera):
    """Aplica `altera(aba, numero, valores) -> valores | None` às linhas do XLS da amostra."""
    original = mod.rows

    def rows(caminho, aba):
        for numero, valores in original(caminho, aba):
            if Path(caminho).name == APELLIDOS:
                valores = altera(aba, numero, list(valores))
                if valores is None:
                    continue
            yield numero, valores

    monkeypatch.setattr(mod, "rows", rows)


def test_r2_5_sobrenome_pelo_primeiro_apellido(mod):
    familia = {r.name: r.count for r in mod.parse(ARQUIVOS) if r.kind == "family"}
    # LYU: '..' no segundo apellido e no par; TUDORICA: '..' no par; GARCIA: 1º 1446937, 2º 1468824
    assert (familia["LYU"], familia["TUDORICA"], familia["GARCIA"]) == (208, 100, 1446937)


def test_r2_5_cabecalho_sem_apellido_1_falha(mod, monkeypatch):
    _linhas_xls(mod, monkeypatch, lambda aba, n, v: [None, None, "Apellido 2º"] if n == 4 else v)
    with pytest.raises(FormatError, match=r"apellidos_frecuencia.xls, aba 'Apellidos >=100', linha 5: "
                                          r"esperava 'Apellido 1º' na coluna C da linha de cima"):
        list(mod.parse(ARQUIVOS))


def test_r2_7_marcador_na_coluna_lida_e_omitido(mod, monkeypatch):
    _linhas_xls(mod, monkeypatch, lambda aba, n, v: [v[0], v[1], ".."] + v[3:] if n == 21 else v)
    nomes = [r.name for r in mod.parse(ARQUIVOS) if r.kind == "family"]
    assert "MUÑOZ" not in nomes and "GARCIA" in nomes


def test_r2_7_marcador_desconhecido_falha(mod, monkeypatch):
    _linhas_xls(mod, monkeypatch, lambda aba, n, v: [v[0], v[1], "<20"] + v[3:] if n == 21 else v)
    with pytest.raises(FormatError, match=r"aba 'Apellidos >=100', linha 21: Apellido 1º '<20' is neither an integer"):
        list(mod.parse(ARQUIVOS))


@pytest.mark.parametrize("altera, trecho", [
    (lambda v: [v[0], v[1], 20.5] + v[3:], "linha 21: Apellido 1º 20.5 não é inteiro"),
    (lambda v: [v[0], "", v[2]], "linha 21: nome vazio"),
    (lambda v: [v[0], None, v[2]], "linha 21: nome vazio"),
    (lambda v: ["Total", v[1], v[2]], "linha 21: ordem 'Total' não é inteiro"),
    (lambda v: v[:2], "linha 21: Apellido 1º vazia"),
])
def test_formato_inesperado_falha(mod, monkeypatch, altera, trecho):
    _linhas_xls(mod, monkeypatch, lambda aba, n, v: altera(v) if n == 21 else v)
    with pytest.raises(FormatError, match=trecho):
        list(mod.parse(ARQUIVOS))


def test_aba_sem_linhas_de_dados_falha(mod, monkeypatch):
    _linhas_xls(mod, monkeypatch, lambda aba, n, v: v if n <= 5 or aba != "Apellidos >=20 y <=99" else None)
    with pytest.raises(FormatError, match=r"aba 'Apellidos >=20 y <=99': nenhuma linha de dados"):
        list(mod.parse(ARQUIVOS))
