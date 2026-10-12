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

- [ ] **Passo 1: testes que falham** em `tests/test_spreadsheet.py`, com um auxiliar `_xlsx(tmp_path, abas)` que grava um XLSX mínimo (workbook, relações, textos compartilhados e abas em XML escrito à mão):
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
- [ ] **Passo 2: implementar** `spreadsheet.py`: leitura dos 8 primeiros bytes; XLSX com `zipfile`, `workbook.xml` e relações para achar a aba, textos compartilhados em lista, `iterparse` da aba com `elem.clear()` por linha; conversão de referência de coluna (`A` = 0, `AA` = 26); XLS levanta `FormatError` "XLS ainda não suportado" até a Task 2.
- [ ] **Passo 3:** `uv run pytest -q` verde; commit "Lê XLSX com a biblioteca padrão (spec 003b, R1)".

### Task 2: leitor de XLS com `xlrd` 2.0.2

**Arquivos:**
- Modificar: `pyproject.toml`, `uv.lock`, `src/namescommons/spreadsheet.py`, `AGENTS.md`
- Criar: `tests/fixtures/planilhas/tipos.xls` (gerado pelo script abaixo), `tests/fixtures/es-ine-residentes/apellidos_frecuencia.xls` e `tests/fixtures/es-ine-residentes/nombres_por_edad_media.xlsx` (gerados pelo script da Task 3, que já entram aqui para o teste de R1.3)
- Teste: `tests/test_spreadsheet.py`

**Interfaces:**
- Consome: `xlrd.open_workbook(on_demand=True)`, tipos de célula `XL_CELL_*`.
- Produz: o mesmo `rows` e `sheet_names` da Task 1 para XLS.

- [ ] **Passo 1: testes que falham:**
  - `test_r1_3_tipos_de_celula_xls` (texto, inteiro guardado como `float`, fração, booleano, vazio, linha esparsa)
  - `test_r1_3_erro_de_formula_xls`
  - `test_r1_3_mesmos_valores_nos_dois_formatos` (a mesma tabela em `tipos.xls` e num XLSX montado no teste)
  - `test_r1_3_amostras_do_ine` (cabeçalhos e primeiras linhas de dados das duas amostras, escritos à mão)
  - `test_r1_5_xls_corrompido` (cabeçalho OLE2 seguido de lixo)
  - `test_r1_5_xlrd_fixado` (`pyproject.toml` declara `xlrd==2.0.2`)
- [ ] **Passo 2:** `uv add 'xlrd==2.0.2'`; implementar o caminho XLS em `spreadsheet.py` (`on_demand=True`, `sheet_by_name`, normalização de tipos, `release_resources()` no fim); `AGENTS.md` ganha `xlrd` na stack.
- [ ] **Passo 3:** gerar `tipos.xls` com `uv run --with xlwt==1.3.0 python -I <script>`; o script grava a aba `Dados` com as mesmas células de `test_r1_3_mesmos_valores_nos_dois_formatos` e a aba `Erros` com uma célula `#N/A`.
- [ ] **Passo 4:** `uv run pytest -q` verde; commit "Lê XLS com xlrd 2.0.2 (spec 003b, R1.5, ADR 0004)".

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

- [ ] **Passo 1: testes que falham** em `tests/test_es_ine_residentes.py`:
  - `test_parse_da_amostra_real` (os 21 registros esperados escritos à mão, na ordem dos arquivos)
  - `test_r2_1_uma_fonte_population_para_nomes_e_sobrenomes`
  - `test_r2_3_ano_da_edicao` (amostra com a frase trocada para 01/01/2026 dá 2026; sem a frase, `FormatError`)
  - `test_r2_4_aba_desconhecida_falha`
  - `test_r2_5_sobrenome_pelo_primeiro_apellido` (`LYU` e `TUDORICA` com `..` no segundo apellido ou no par entram com a contagem do primeiro)
  - `test_r2_7_marcador_na_coluna_lida` (`..` omitido; `<20` é `FormatError`)
  - `test_formato_inesperado_falha` (cabeçalho trocado, contagem fracionária, nome vazio, ordem não numérica)
- [ ] **Passo 2:** implementar o adaptador; registrar a fonte em `sources.yaml` (`country: ES`, `count_type: population`, `primary: true`, `suppression: 20`, `uniform_case: true`, `retrieved: 2026-10-12`); acrescentar a linha em `ATRIBUICAO.md`.
- [ ] **Passo 3:** `uv run pytest -q` verde, incluindo `tests/test_fontes_oficiais.py` com a fonte nova; commit "Adiciona a fonte do INE (spec 003b, R2)".

### Task 4: CI com a Espanha

**Arquivos:**
- Modificar: `.github/workflows/ci.yml`, `tests/test_ci.py`

- [ ] **Passo 1: teste que falha:** `test_passo_das_fontes_oficiais_roda_localmente` passa a esperar 5 países e `by_country/ES.csv` igual ao texto escrito à mão, com `ANDREA` dos dois sexos e `female_share` 0,973084.
- [ ] **Passo 2:** acrescentar `ES` à lista de países do passo da CI.
- [ ] **Passo 3:** `uv run pytest -q` verde; commit "Confere a Espanha no passo das fontes oficiais da CI (spec 003b, R4)".

### Fechamento

- [ ] Medição de R5: `namescommons run --offline` só com `es-ine-residentes` e os arquivos reais no cache, com `/usr/bin/time -l`; pico de memória da leitura do XLS.
- [ ] Issues das fontes adiadas de R6 (DVV, Statbel).
- [ ] Pull request com `Closes #13`.
