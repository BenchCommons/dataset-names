# 003e. Nova Zelândia: tarefas

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar os comandos na raiz do repositório, a partir de `master` com a spec 003. Antes da Task 1, rodar `uv sync` e conferir `uv run pytest -q` com `318 passed`.

Cada tarefa segue TDD: escrever os testes, ver que falham pelo motivo certo, escrever o código, ver que passam, commit.

---

### Task 1: página HTML no lugar do arquivo (R4.1)

**Arquivos:**
- Modificar: `src/namescommons/cache.py`
- Modificar (teste): `tests/conftest.py`, `tests/test_cache.py`

**Interfaces:**
- Consome: `fetch_resource`, `_baixar`, `FetchError` (spec 002); servidor local (spec 002, R7).
- Produz: `namescommons.cache.BlockedError(FetchError)`; `ServidorLocal.tipos: dict[str, str]` (caminho -> `Content-Type`).

- [x] **Passo 1: testes que falham** em `tests/test_cache.py`
  - `test_pagina_html_no_lugar_do_arquivo_nao_entra_no_cache`: o servidor responde 200 com `text/html; charset=UTF-8` e a página "Pardon Our Interruption" para `/a.csv`; `fetch_resource` levanta `BlockedError` cuja mensagem tem "página HTML", a URL, o caminho `tmp_path/exemplo/a.csv` e `--offline`; o servidor recebeu uma única requisição; nem `a.csv`, nem `a.csv.part`, nem `a.csv.meta.json` existem.
  - `test_html_e_aceito_quando_o_recurso_e_html`: recurso `pagina.html` servido como `text/html` é gravado.
  - `test_csv_servido_como_text_csv_continua_aceito`: `text/csv` não muda nada.
- [x] **Passo 2: código.** `ServidorLocal` envia `Content-Type` quando o caminho está em `tipos`. Em `_baixar`, depois de abrir a resposta e antes de gravar, se o tipo de mídia (antes do `;`, sem caixa) for `text/html` e o `destino` não terminar em `.html` ou `.htm`, levantar `BlockedError`. Em `fetch_resource`, `BlockedError` sai do laço sem nova tentativa e a mensagem final é `falha ao baixar <url>: o servidor devolveu uma página HTML (text/html) no lugar de <filename>, provável bloqueio de download automático: baixe o arquivo pelo navegador, grave-o em <destino> e rode com --offline`.
- [x] **Passo 3:** `uv run pytest -q` verde; commit.

### Task 2: adaptador `nz-dia-births` (R1 a R3, R4.2, R5)

**Arquivos:**
- Criar: `src/namescommons/adapters/nz_dia_births.py`, `tests/fixtures/nz-dia-births/baby-names-1900-to-2025.csv`
- Modificar: `sources.yaml`, `tests/fixtures/ATRIBUICAO.md` (linha nova ao fim)
- Teste: `tests/test_nz_dia_births.py`

**Interfaces:**
- Consome: `FormatError`, `RawRecord`, `Resource`, `parse_code`, `parse_count` (spec 003); `servir_fixtures` e `tests/test_fontes_oficiais.py` (spec 003).
- Produz: fonte `nz-dia-births` (`country: NZ`, `count_type: births`, `suppression: 10`, `license: CC-BY-4.0`); `parse(files)` que avisa os descartes no logger `namescommons.adapters.nz_dia_births`.

- [x] **Passo 1: gerar a amostra** com um script que copia do arquivo real, sem alteração e na ordem original, o cabeçalho e as linhas: `2022,F,Aadhya,13` (primeira), `2003,M,Andr\x82,20`, `1967,F,Anne-Marie,24`, `2025,F,Aroha,22`, `2025,M,Bj\xf6rn,10`, `2022,F,Esm\x82,25`, `2025,F,Esm\xe9,20`, `1900,M,John,636`, `2023,F,K\x8fwhai,11`, `2025,F,M?ia,25`, `1900,F,Mary,410`, `2023,M,N\x8dkau,13`, `2025,M,Nikau,36`, `2024,F,Te Ao,15`, `2024,M,Te Ao,12`, `2025,M,Te Ariki,34`, `2007,F,Zo\xe9,26` e `2015,F,Zoya,11` (última), cada uma terminada em CRLF.
- [x] **Passo 2: testes que falham** em `tests/test_nz_dia_births.py`
  - `test_parse_da_amostra_real`: os 15 registros esperados, escritos à mão, com `André`, `Björn`, `Esmé` (2022 e 2025) e `Zoé`.
  - `test_nomes_corrompidos_sao_descartados_e_avisados`: nenhum nome com `?` ou U+FFFD; um aviso com `3 linha(s)`, `49 registro(s)` e as formas `K�whai`, `M?ia`, `N�kau`.
  - `test_sem_descarte_nao_avisa`.
  - `test_arquivo_utf8_valido_e_lido_como_utf8`: `Māia` e `Zoé` em UTF-8 saem como estão.
  - `test_byte_fora_da_tabela_descarta_o_nome` (ex.: `0xE1`).
  - `test_formato_inesperado_falha`: cabeçalho diferente, sexo `U`, contagem `<10`, ano `20x5`, linha com três ou cinco campos, arquivo vazio, cada um com `FormatError` e número da linha quando houver.
  - `test_pagina_html_no_cache_explica_o_que_fazer`: arquivo que começa com `<!DOCTYPE html>` gera `FormatError` com "página HTML" e o caminho do arquivo.
- [x] **Passo 3: código.** Adaptador com `RESOURCES` apontando para a URL de download do catálogo, decodificação de R2, `csv.reader` sobre o texto decodificado, `parse_code` para o sexo e `parse_count` para ano e contagem. Acrescentar ao fim de `sources.yaml` a entrada `nz-dia-births` (`url` da página do conjunto, `attribution` "Department of Internal Affairs (Nova Zelândia), Baby Name popularity over time, CC BY 4.0", `retrieved: 2026-10-12`) e ao fim de `ATRIBUICAO.md` a linha da amostra.
- [x] **Passo 4:** atualizar em `tests/test_ci.py` o total esperado do passo das fontes oficiais (`54 observações, 5 países`), consequência direta da fonte nova; `uv run pytest -q` verde (inclui `test_amostra_e_atribuicao` e `test_fetch_e_ingest_sobre_a_amostra` para a fonte nova); commit.

### Task 3: CI (R6)

**Arquivos:**
- Modificar: `.github/workflows/ci.yml`, `tests/test_ci.py`

- [x] **Passo 1: teste que falha.** `test_passo_das_fontes_oficiais_roda_localmente` confere que o laço do passo inclui `NZ`, que o `stderr` traz o aviso de descarte e `by_country/NZ.csv` escrito à mão.
- [x] **Passo 2:** acrescentar `NZ` ao laço `for pais in ...` do passo das fontes oficiais.
- [x] **Passo 3:** `uv run pytest -q` verde; commit.

### Fechamento

- [ ] Rodar `namescommons ingest nz-dia-births --offline` com o arquivo real num cache do scratchpad; conferir 74.006 observações e o aviso de 13 linhas e 164 registros; anotar tempo na descrição do pull request.
- [ ] Conferir os critérios de aceite da spec, um a um.
- [ ] Pull request com `Closes #10`.
