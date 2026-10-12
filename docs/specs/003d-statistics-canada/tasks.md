# 003d. Statistics Canada: tarefas

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar todos os comandos na raiz do repositório, a partir de `master`. Antes da Task 1, rodar `uv sync` e conferir que `uv run pytest -q` passa.

Cada tarefa é um commit: primeiro o teste, que falha pelo motivo esperado; depois o código, até o teste passar; por fim a suíte inteira.

---

### Task 1: licença `statcan-open-licence` (R3)

**Arquivos:**
- Modificar: `src/namescommons/sources.py`
- Teste: `tests/test_sources.py`

**Interfaces:**
- Consome: `parse_sources`, `SourceError`, `LICENCAS_COMPATIVEIS` (spec 001).
- Produz: `"statcan-open-licence" in LICENCAS_COMPATIVEIS`.

- [x] **Passo 1: teste que falha.** `test_statcan_open_licence_e_aceita_pelo_adr_0004`: `parse_sources([fonte(license="statcan-open-licence")])` devolve a fonte. A parametrização de `test_licenca_incompativel_e_recusada` continua igual (ShareAlike, NonCommercial e desconhecida recusadas).
- [x] **Passo 2: rodar** `uv run pytest -q tests/test_sources.py` e ver a falha `licença 'statcan-open-licence' incompatível com o ADR 0001`.
- [x] **Passo 3: código.** Acrescentar `"statcan-open-licence"` a `LICENCAS_COMPATIVEIS`, com comentário apontando o ADR `0004-licenca-statistics-canada.md`.
- [x] **Passo 4: rodar** `uv run pytest -q` e commitar.

### Task 2: adaptador `ca-statcan-births` (R1, R2, R4, R7)

**Arquivos:**
- Criar: `src/namescommons/adapters/ca_statcan_births.py`, `tests/fixtures/ca-statcan-births/17100147-eng.zip`
- Modificar: `sources.yaml`, `tests/fixtures/ATRIBUICAO.md`, `README.md`
- Teste: `tests/test_ca_statcan_births.py`; ajuste da contagem em `tests/test_ci.py`

**Interfaces:**
- Consome: `RawRecord`, `Resource`, `FormatError`, `parse_code`, `parse_count` (spec 003, R2.2); `to_observations` (spec 003, R2.1); `servir_fixtures` (spec 003, R2.5).
- Produz: `SOURCE_ID = "ca-statcan-births"`, `RESOURCES = [Resource("https://www150.statcan.gc.ca/n1/tbl/csv/17100147-eng.zip", "17100147-eng.zip")]`, `parse(files) -> Iterator[RawRecord]` (gerador).

- [x] **Passo 1: amostra.** Gerar `17100147-eng.zip` com um script fora do repositório que lê o ZIP real em fluxo e copia, sem alteração, o cabeçalho e as 20 linhas listadas em R4 da spec, gravando-as no membro `17100147.csv` (ZIP deflate, 707 bytes).
- [x] **Passo 2: testes que falham** em `tests/test_ca_statcan_births.py`:
  - `test_parse_da_amostra_real`: os 12 registros escritos à mão, na ordem do arquivo.
  - `test_so_frequencia_gera_registro` (R1.1), `test_indicador_desconhecido_falha` (R1.1).
  - `test_geografia_nao_nacional_e_pulada` e `test_sem_linhas_nacionais_de_frequencia_falha` (R1.2).
  - `test_sexo_por_mapeamento` e `test_sexo_desconhecido_falha` (R1.3).
  - `test_grand_total_e_pulado_mesmo_com_valor` (R1.4).
  - `test_celula_suprimida_e_omitida` e `test_status_ou_simbolo_desconhecido_falha`, parametrizado com `x`, `F`, `E`, `0s`, valor sem `STATUS` vazio e vazio sem `..` (R1.5).
  - `test_simbolos_de_revisao_sao_aceitos` com `p` e `r` (R1.6).
  - `test_escala_diferente_de_unidades_falha` (R1.7), `test_ano_invalido_falha` (R1.8).
  - `test_membro_ausente_falha`, `test_coluna_ausente_falha`, `test_linha_com_numero_de_campos_errado_falha` (R2).
  - `test_parse_e_preguicoso`: com um CSV cuja segunda linha de dados é inválida, `next(parse(...))` devolve o primeiro registro e só o segundo `next` levanta `FormatError`.
  - `test_caixa_uniforme_gera_nomes_capitalizados`: `D'Arcy`, `Jean-Philippe`, `Marie-Eve`, `Noah`, `Olivia`, `Riley`.
- [x] **Passo 3: rodar** `uv run pytest -q tests/test_ca_statcan_births.py` e ver a falha de adaptador ausente.
- [x] **Passo 4: código.** Escrever o adaptador conforme o plano; registrar a fonte em `sources.yaml` (`suppression: 5`, `uniform_case: true`, `retrieved: 2026-10-12`); acrescentar a linha em `tests/fixtures/ATRIBUICAO.md` e no README.
- [x] **Passo 5: rodar** `uv run pytest -q`; `tests/test_fontes_oficiais.py` passa a cobrir a fonte nova. O passo da CI das fontes oficiais lê `sources.yaml`, então a contagem esperada em `test_passo_das_fontes_oficiais_roda_localmente` muda para `OK: 51 observações, 5 países` neste mesmo commit, para a suíte continuar verde. Commitar.

### Task 3: CI confere o Canadá (R5)

**Arquivos:**
- Modificar: `.github/workflows/ci.yml`
- Teste: `tests/test_ci.py`

- [x] **Passo 1: teste que falha.** `test_passo_das_fontes_oficiais_roda_localmente` passa a conferir também o conteúdo de `by_country/CA.csv` escrito à mão (`Noah` com `female_share` 0.015645, `Riley` com 0.388451). `test_passo_das_fontes_oficiais_confere_todos_os_paises` confere que o laço do passo lista `CA FR IE NO US`.
- [x] **Passo 2: rodar** `uv run pytest -q tests/test_ci.py` e ver a falha.
- [x] **Passo 3: código.** Trocar `for pais in FR IE NO US` por `for pais in CA FR IE NO US` no passo da CI.
- [x] **Passo 4: rodar** `uv run pytest -q` e commitar.

### Fechamento

- [x] Baixar o ZIP real para um diretório do scratchpad, montar um cache só com ele e um `sources.yaml` só com `ca-statcan-births`, rodar `/usr/bin/time -l uv run namescommons run --offline` e registrar tempo e pico de memória na spec (R6) e no pull request.
- [x] Abrir o pull request com `Closes #15`.
