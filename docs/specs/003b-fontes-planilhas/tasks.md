# 003b. Fontes em planilha: tarefas

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar todos os comandos na raiz do repositório, a partir de `master` com a spec 003 e o renome do ADR 0003. Antes da Task 1, rodar `uv sync` e conferir `uv run pytest -q` verde.

Cada tarefa segue TDD: escrever os testes, ver falhar com `uv run pytest -q <arquivo>`, escrever o código, ver passar, rodar a suíte inteira e fazer um commit.

---

### Task 1: leitor de XLSX e reconhecimento do formato

**Arquivos:**
- Criar: `src/namescommons/spreadsheet.py`
- Teste: `tests/test_spreadsheet.py`

**Interfaces:**
- Consome: `FormatError`, `parse_count` de `namescommons.adapters` (spec 003, R2.2).
- Produz: `sheet_names(path) -> list[str]`; `rows(path, sheet) -> Iterator[tuple[int, list]]`; `cell_count(value, missing=(), field="contagem") -> int | None`.

- [x] **Passo 1: testes que falham** em `tests/test_spreadsheet.py`, com um auxiliar `_xlsx(tmp_path, abas)` que grava um XLSX mínimo (workbook, relações, textos compartilhados e abas em XML escrito à mão):
  - `test_r1_1_sheet_names_na_ordem_do_arquivo`
  - `test_r1_1_aba_ausente_lista_as_abas`
  - `test_r1_1_numero_da_linha_do_excel_e_coluna_pela_referencia` (linhas 1, 3 e 10; células em A, C e AA)
  - `test_r1_2_conteudo_que_nao_e_planilha` (HTML, texto vazio, ZIP sem `xl/workbook.xml`)
  - `test_r1_3_tipos_de_celula_xlsx` (`s`, `inlineStr`, `str`, `n`, sem tipo, `b`; `590938` vira `int`, `58.7` vira `float`, `1E3` vira `int`)
  - `test_r1_3_linhas_vazias_puladas_e_none_final_cortado`
  - `test_r1_3_erro_de_formula_nomeia_aba_e_celula`
  - `test_r1_4_texto_compartilhado_com_formatacao_e_rph`
  - `test_r1_4_aba_pelo_alvo_das_relacoes` (aba `sheet2.xml` listada primeiro no workbook; alvo absoluto `/xl/worksheets/...`)
  - `test_r1_6_cell_count` (inteiros, `..` declarado, texto numérico, vazio com e sem `""` em `missing`, `20.5`, `-1`, `True`, marcador desconhecido)
- [x] **Passo 2: implementar** `spreadsheet.py`: leitura dos 8 primeiros bytes; XLSX com `zipfile`, `workbook.xml` e relações para achar a aba, textos compartilhados em lista, `iterparse` da aba com `elem.clear()` por linha; conversão de referência de coluna (`A` = 0, `AA` = 26); XLS levanta `FormatError` "XLS ainda não suportado" até a Task 2.
- [x] **Passo 3:** `uv run pytest -q` verde; commit "Lê XLSX com a biblioteca padrão (spec 003b, R1)".

### Task 2: leitor de XLS com `xlrd` 2.0.2

**Arquivos:**
- Modificar: `pyproject.toml`, `uv.lock`, `src/namescommons/spreadsheet.py`, `AGENTS.md`
- Criar: `tests/fixtures/planilhas/tipos.xls` (gerado pelo script abaixo), `tests/fixtures/es-ine-residentes/apellidos_frecuencia.xls` e `tests/fixtures/es-ine-residentes/nombres_por_edad_media.xlsx` (gerados pelo script da Task 3, que já entram aqui para o teste de R1.3)
- Teste: `tests/test_spreadsheet.py`

**Interfaces:**
- Consome: `xlrd.open_workbook(on_demand=True)`, tipos de célula `XL_CELL_*`.
- Produz: o mesmo `rows` e `sheet_names` da Task 1 para XLS.

- [x] **Passo 1: testes que falham:**
  - `test_r1_3_tipos_de_celula_xls` (texto, inteiro guardado como `float`, fração, booleano, vazio, linha esparsa)
  - `test_r1_3_erro_de_formula_xls`
  - `test_r1_3_mesmos_valores_nos_dois_formatos` (a mesma tabela em `tipos.xls` e num XLSX montado no teste)
  - `test_r1_3_amostras_do_ine` (cabeçalhos e primeiras linhas de dados das duas amostras, escritos à mão)
  - `test_r1_5_xls_corrompido` (cabeçalho OLE2 seguido de lixo)
  - `test_r1_5_xlrd_fixado` (`pyproject.toml` declara `xlrd==2.0.2`)
- [x] **Passo 2:** `uv add 'xlrd==2.0.2'`; implementar o caminho XLS em `spreadsheet.py` (`on_demand=True`, `sheet_by_name`, normalização de tipos, `release_resources()` no fim); `AGENTS.md` ganha `xlrd` na stack.
- [x] **Passo 3:** gerar `tipos.xls` com `uv run --with xlwt==1.3.0 python -I <script>`; o script grava a aba `Dados` com as mesmas células de `test_r1_3_mesmos_valores_nos_dois_formatos` e a aba `Erros` com uma célula `#N/A`.
- [x] **Passo 4:** `uv run pytest -q` verde; commit "Lê XLS com xlrd 2.0.2 (spec 003b, R1.5, ADR 0005)".

### Task 3: fonte `es-ine-residentes`

**Arquivos:**
- Criar: `src/namescommons/adapters/es_ine_residentes.py`, `tests/test_es_ine_residentes.py`
- Modificar: `sources.yaml`, `tests/fixtures/ATRIBUICAO.md`

**Interfaces:**
- Consome: `sheet_names`, `rows`, `cell_count`; `RawRecord`, `Resource`, `FormatError`, `parse_code`.
- Produz: `SOURCE_ID = "es-ine-residentes"`, `RESOURCES` com os dois arquivos do INE, `parse(files)`.

Amostra (spec, R3), gerada a partir dos arquivos reais baixados para fora do repositório:
- `nombres_por_edad_media.xlsx`: o XML original de `workbook.xml`, das relações e das abas, mantendo as linhas 1 a 7 e as linhas de dados `Hombres` 8 (ANTONIO), 152 (IÑIGO), 618 (ANDREA), 707 (LLORENÇ), 4812 (FRANCESC D'ASSIS) e 31126 (ZUNAIR), e `Mujeres` 8 (MARIA CARMEN), 47 (ANDREA), 129 (BEGOÑA), 3024 (FRANÇOISE), 30276 (JOANA D'ARC) e 32328 (ZULMA PATRICIA), com os textos compartilhados reindexados.
- `apellidos_frecuencia.xls`: as linhas 1 a 5 e as linhas de dados de `Apellidos >=100` 6 (GARCIA), 21 (MUÑOZ), 1705 (GONÇALVES), 7173 (O'BRIEN), 16097 (LYU) e 27666 (TUDORICA), e de `Apellidos >=20 y <=99` 6 (ANCHUSTEGUI), 43286 (NEL·LO) e 58856 (ZRHAIDA), nas mesmas linhas e colunas A a G.

- [x] **Passo 1: testes que falham** em `tests/test_es_ine_residentes.py`:
  - `test_parse_da_amostra_real` (os 21 registros esperados escritos à mão, na ordem dos arquivos)
  - `test_r2_1_uma_fonte_population_para_nomes_e_sobrenomes`
  - `test_r2_3_ano_da_edicao` (amostra com a frase trocada para 01/01/2026 dá 2026; sem a frase, `FormatError`)
  - `test_r2_4_aba_desconhecida_falha`
  - `test_r2_5_sobrenome_pelo_primeiro_apellido` (`LYU` e `TUDORICA` com `..` no segundo apellido ou no par entram com a contagem do primeiro)
  - `test_r2_7_marcador_na_coluna_lida` (`..` omitido; `<20` é `FormatError`)
  - `test_formato_inesperado_falha` (cabeçalho trocado, contagem fracionária, nome vazio, ordem não numérica)
- [x] **Passo 2:** implementar o adaptador; registrar a fonte em `sources.yaml` (`country: ES`, `count_type: population`, `primary: true`, `suppression: 20`, `uniform_case: true`, `retrieved: 2026-10-12`); acrescentar a linha em `ATRIBUICAO.md`.
- [x] **Passo 3:** `uv run pytest -q` verde, incluindo `tests/test_fontes_oficiais.py` com a fonte nova; commit "Adiciona a fonte do INE (spec 003b, R2)".

### Task 4: CI com a Espanha

**Arquivos:**
- Modificar: `.github/workflows/ci.yml`, `tests/test_ci.py`

- [x] **Passo 1: teste que falha:** `test_passo_das_fontes_oficiais_roda_localmente` passa a esperar 5 países e `by_country/ES.csv` igual ao texto escrito à mão, com `ANDREA` dos dois sexos e `female_share` 0,973084.
- [x] **Passo 2:** acrescentar `ES` à lista de países do passo da CI.
- [x] **Passo 3:** `uv run pytest -q` verde; commit "Confere a Espanha no passo das fontes oficiais da CI (spec 003b, R4)".

### Fechamento

- [x] Medição de R5: `namescommons run --offline` só com `es-ine-residentes` e os arquivos reais no cache, com `/usr/bin/time -l`; pico de memória da leitura do XLS.
- [x] Issues das fontes adiadas de R6 (DVV, Statbel).
- [x] Pull request com `Closes #13`.

---

### Apêndice: gerador das amostras

Rodado fora do repositório, com os arquivos reais baixados em `<dir_reais>`: `uv run --with xlwt==1.3.0 --with xlrd==2.0.2 python -I gera_amostras.py <dir_reais> tests/fixtures`.

```python
"""Gera as amostras da spec 003b a partir dos arquivos reais do INE.

Uso: uv run --with xlwt==1.3.0 --with xlrd==2.0.2 python -I gera_amostras.py <dir_reais> <dir_tests_fixtures>
"""
import re
import sys
import zipfile
from pathlib import Path

import xlrd
import xlwt

reais, fixtures = Path(sys.argv[1]), Path(sys.argv[2])

# --- nombres_por_edad_media.xlsx: XML original, só as linhas escolhidas --------------------------
LINHAS = {"sheet1.xml": [1, 2, 3, 4, 5, 6, 7, 8, 152, 618, 707, 4812, 31126],
          "sheet2.xml": [1, 2, 3, 4, 5, 6, 7, 8, 47, 129, 3024, 30276, 32328]}
orig = zipfile.ZipFile(reais / "nombres_por_edad_media.xlsx")
sst = orig.read("xl/sharedStrings.xml").decode("utf-8")
cab_sst, corpo = sst.split("<si>", 1)
sis = re.findall(r"<si>.*?</si>", "<si>" + corpo.rsplit("</sst>", 1)[0], flags=re.S)
novos, mapa = [], {}

def remapeia(linha: str) -> str:
    def troca(m):
        antigo = int(m.group(2))
        if antigo not in mapa:
            mapa[antigo] = len(novos)
            novos.append(sis[antigo])
        return f'{m.group(1)}<v>{mapa[antigo]}</v>'
    return re.sub(r'(<c [^>]*t="s"[^>]*>)<v>(\d+)</v>', troca, linha)

abas = {}
for membro, quais in LINHAS.items():
    xml = orig.read(f"xl/worksheets/{membro}").decode("utf-8")
    inicio, resto = xml.split("<sheetData>", 1)
    linhas = re.findall(r'<row r="(\d+)"[^>]*?(?:/>|>.*?</row>)', resto.split("</sheetData>", 1)[0], flags=re.S)
    blocos = re.findall(r'<row r="\d+"[^>]*?(?:/>|>.*?</row>)', resto.split("</sheetData>", 1)[0], flags=re.S)
    escolhidas = [remapeia(b) for n, b in zip(linhas, blocos) if int(n) in quais]
    assert len(escolhidas) == len(quais), membro
    inicio = re.sub(r'<dimension ref="[^"]*"/>', f'<dimension ref="A1:F{quais[-1]}"/>', inicio)
    abas[membro] = inicio + "<sheetData>" + "".join(escolhidas) + '</sheetData><mergeCells count="1"><mergeCell ref="A1:D1"/></mergeCells></worksheet>'

CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
      '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
      '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
      '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
      '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
      '</Types>')
RELS_PKG = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
rels_livro = re.sub(r'<Relationship Id="rId3"[^>]*/>', "", orig.read("xl/_rels/workbook.xml.rels").decode("utf-8"))
livro = orig.read("xl/workbook.xml").decode("utf-8")
livro = re.sub(r"<mc:AlternateContent.*?</mc:AlternateContent>", "", livro, flags=re.S)
livro = re.sub(r"<definedNames>.*?</definedNames>", "", livro, flags=re.S)
livro = re.sub(r"<extLst>.*?</extLst>", "", livro, flags=re.S)
novo_sst = (cab_sst.replace('count="63456" uniqueCount="62458"', f'count="{len(novos)}" uniqueCount="{len(novos)}"')
            + "".join(novos) + "</sst>")
destino = fixtures / "es-ine-residentes"
destino.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(destino / "nombres_por_edad_media.xlsx", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", CT)
    z.writestr("_rels/.rels", RELS_PKG)
    z.writestr("xl/workbook.xml", livro)
    z.writestr("xl/_rels/workbook.xml.rels", rels_livro)
    for membro, xml in abas.items():
        z.writestr(f"xl/worksheets/{membro}", xml)
    z.writestr("xl/styles.xml", orig.read("xl/styles.xml"))
    z.writestr("xl/sharedStrings.xml", novo_sst)

# --- apellidos_frecuencia.xls: mesmas linhas e colunas A a G, regravadas em BIFF8 -----------------
LINHAS_XLS = {"Apellidos >=100": [1, 2, 3, 4, 5, 6, 21, 1705, 7173, 16097, 27666],
              "Apellidos >=20 y <=99": [1, 2, 3, 4, 5, 6, 43286, 58856]}
livro_xls = xlrd.open_workbook(reais / "apellidos_frecuencia.xls")
saida = xlwt.Workbook(encoding="utf-8")
for nome, quais in LINHAS_XLS.items():
    origem, aba = livro_xls.sheet_by_name(nome), saida.add_sheet(nome)
    for n in quais:
        for c, celula in enumerate(origem.row(n - 1)):
            if celula.ctype == xlrd.XL_CELL_EMPTY or (celula.ctype == xlrd.XL_CELL_TEXT and celula.value == ""):
                continue
            aba.write(n - 1, c, celula.value)
saida.save(str(destino / "apellidos_frecuencia.xls"))

# --- planilhas/tipos.xls: as mesmas células de TIPOS_ESPERADO em tests/test_spreadsheet.py --------
tipos = xlwt.Workbook(encoding="utf-8")
d = tipos.add_sheet("Dados")
for c, v in enumerate(["Orden", "Nombre", "Frecuencia"]):
    d.write(0, c, v)
for c, v in enumerate(["ANTONIO", 590938, 58.7]):
    d.write(1, c, v)
d.write(2, 0, "IÑIGO"); d.write(2, 1, 1000.0)
d.write(4, 0, "JOANA D'ARC"); d.write(4, 1, True); d.write(4, 2); d.write(4, 3, False); d.write(4, 4)
d.write(6, 2, "..")
e = tipos.add_sheet("Erros")
e.write(0, 0, 1)
e.row(1).set_cell_error(1, 0x2A)  # #N/A
(fixtures / "planilhas").mkdir(exist_ok=True)
tipos.save(str(fixtures / "planilhas" / "tipos.xls"))
for p in sorted((fixtures / "es-ine-residentes").iterdir()) + [fixtures / "planilhas" / "tipos.xls"]:
    print(p.name, p.stat().st_size)
```
