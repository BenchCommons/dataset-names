# 004. Wikidata: tarefas

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar os comandos na raiz do repositório. Antes da Task 1, rodar `uv sync` e conferir que `uv run pytest -q` passa. Cada tarefa começa pelo teste que falha e termina com `uv run pytest -q` verde e um commit.

---

### Task 1: regra de `primary` só para fontes com contagem (R5, issue #3)

**Arquivos:** `src/namescommons/sources.py`, `tests/test_sources.py`.

- [x] Teste que falha: `test_attested_nao_exige_primary` (duas fontes `attested` sem país, ambas `primary: false`, e duas `attested` do mesmo país, ambas `primary: true`, são aceitas) e `test_births_continua_exigindo_uma_primary`.
- [x] Em `parse_sources`, o agrupamento por (`country`, `count_type`) ignora `count_type == "attested"`.
- [x] `uv run pytest -q` e commit.

### Task 2: tabela `variant_links` no contrato e no pipeline (R4.1, R4.2, R4.4, R4.5, R4.7)

**Arquivos:** `src/namescommons/adapters/__init__.py`, `src/namescommons/links.py` (novo), `src/namescommons/pipeline.py`, `src/namescommons/io.py`, `src/namescommons/schema.py`, `tests/test_links.py` (novo), `tests/test_io.py`.

**Produz:** `RawLink(relation, qid, name, kind, target_qid, target_name, target_kind)`; `VariantLink` com os campos de R4.2; `RELATIONS`; `validate_links(links, sources)` que levanta `ValidationError`; `to_links(records, source) -> list[VariantLink]` (normaliza, descarta auto-ligação, remove repetidas, ordena; `RecordError` com `ligação N:` para tipo ou valor inválido); `ingest_links(selected, sources, cache_dir, offline, adapters) -> list[VariantLink] | None`; `write_links(links, path)` e `read_links(path)`.

- [x] Testes que falham em `tests/test_links.py`: normalização e `name_key`; auto-ligação descartada; repetidas emitidas uma vez e ordem estável; `ligação 2: relation 'x' inválida`; `kind` e QID inválidos; `validate_links` recusando cada caso de R4.5; ida e volta em Parquet; `check_adapter` recusando `links` que não é função; `ingest_links` com um módulo de teste com e sem `links`.
- [x] `test_manifest` passa a esperar `schema_version` `1.1.0`.
- [x] Implementação e commit.

### Task 3: adaptador do Wikidata, `parse` (R1, R2, R3)

**Arquivos:** `src/namescommons/adapters/wikidata.py` (novo), `tools/amostra_wikidata.py` (novo), `tests/fixtures/wikidata/` (15 arquivos), `tests/fixtures/ATRIBUICAO.md`, `sources.yaml`, `tests/test_wikidata.py` (novo).

- [x] Gerar a amostra com `uv run python tools/amostra_wikidata.py tests/fixtures/wikidata` (única etapa com rede; os testes não a rodam). Itens: prenomes `Maria` (F e M), `Мария`, `Andrea` (M, F e unissex), `Kim`, `Иван` (três línguas, mesmo texto), `Ivan`, `John`, `李`, `Letha` (sem gênero e F), `Ritwik (given name)` e um valor desconhecido; sobrenomes `Иванов`, `Иванова`, `Ivanov`, `Ivanova`, `Silva`, `李`, `Kim`, `John`, `Q34147` e `Felbert,von`.
- [x] Testes que falham em `tests/test_wikidata.py`: `test_recursos_e_consultas` (15 recursos, URL do QLever com `action=sparql_json`, `ORDER BY`, `LIMIT 200000 OFFSET k`); `test_parse_da_amostra_real` com os registros escritos à mão; `test_genero_vazio_cede_ao_informado`; `test_rotulos_que_nao_sao_nomes_sao_pulados`; `test_ultima_pagina_cheia_falha`; `test_pagina_com_linhas_depois_de_incompleta_falha`; `test_cabecalho_inesperado_falha`; `test_classe_de_genero_desconhecida_falha`; `test_item_que_nao_e_entidade_falha`.
- [x] Registrar a fonte em `sources.yaml` e a amostra em `ATRIBUICAO.md`.
- [x] Implementação e commit.

### Task 4: adaptador do Wikidata, `links` (R4.3)

**Arquivos:** `src/namescommons/adapters/wikidata.py`, `tests/test_wikidata.py`.

- [x] Testes que falham: `test_links_da_amostra_real` (ligações escritas à mão, por relação); `test_transliteracao_filtrada`; `test_alvo_desconhecido_e_pulado`; `test_ingest_links_da_amostra` (sem auto-ligação, com `name_key`).
- [x] Implementação e commit.

### Task 5: CLI e CI (R4.6, R7)

**Arquivos:** `src/namescommons/cli.py`, `tests/test_cli_pipeline.py`, `.github/workflows/ci.yml`, `tests/test_ci.py`.

- [x] Testes que falham: `ingest --links` grava a tabela; `build --links` a copia para a release e o `manifest.json` conta suas linhas; `run` com o Wikidata grava `variant_links.parquet`; `run` só com fontes sem `links` não grava; o passo da CI das fontes de `sources.yaml` confere `variant_links.parquet`.
- [x] Implementação e commit.

### Fechamento

- [x] Medição de R8 com os 15 arquivos reais no cache: `/usr/bin/time -l uv run namescommons run --offline` só com o Wikidata (`sources.yaml` temporário).
- [x] Issues para o que ficou fora: ingestão do dump e endpoint alternativo (#29); rótulos sem P1705 (#30); margem de memória com o Wikidata (#31).
- [x] Pull request com `Closes #3`.
