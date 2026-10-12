# 007. Adoção do kit de fontes do tools-dataset: tarefas

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar os comandos na raiz do repositório, a partir de `master` em `0153007`. Antes da Task 1, `uv sync` e `uv run pytest -q` verdes, e as saídas de linha de base gravadas (plano, restrições globais).

Cada tarefa segue TDD: escrever ou ajustar os testes, ver falhar com `uv run pytest -q <arquivo>`, mudar o código, ver passar, rodar a suíte inteira e fazer um commit. Uma remoção só acontece na tarefa em que o substituto já passa.

---

### Task 1: dependência do kit fixada na tag

**Arquivos:** `pyproject.toml`, `uv.lock`; teste novo `tests/test_tools_dataset.py`.

- [x] Testes: `test_dependencia_fixada_na_versao_e_na_tag` (versão `==0.1.0` em `dependencies` e `tag = "v0.1.0"` em `[tool.uv.sources]`, com a mesma versão), `test_uv_lock_aponta_a_tag` (fonte git com `tag=v0.1.0` no `uv.lock`), `test_kit_instalado_na_versao_fixada` (`datasettool.__version__ == "0.1.0"`).
- [x] `uv add` da dependência com a origem git na tag; `uv sync`.
- [x] Suíte verde; commit `build(deps): depend on benchcommons-tools-dataset 0.1.0 by git tag`.

### Task 2: base do adaptador do kit

**Arquivos:** `src/namescommons/adapters/__init__.py`; testes `tests/test_tools_dataset.py`, `tests/test_adapters.py`, `tests/test_contrato_adaptador.py`, `tests/test_links.py` e os de adaptadores que conferem mensagens do contrato.

- [x] Testes: `test_reexporta_os_objetos_do_kit` (identidade de `AdapterError`, `FormatError`, `Resource`, `SourceFiles`, `module_name`, `parse_count`, `parse_code`), `test_load_adapter_usa_o_pacote_padrao`, `test_check_adapter_confere_links` (com `links` não chamável, falha; sem `links`, passa).
- [x] Trocar a parte genérica pelos reexports e invólucros; `RawRecord`, `RawLink` e `DEFAULT_PACKAGE` ficam.
- [x] Ajustar para o inglês as mensagens conferidas nos testes que continuam (R5.1).
- [x] Remover de `tests/test_adapters.py` e `tests/test_contrato_adaptador.py` os testes listados no plano.
- [x] Suíte verde; commit `refactor(adapters): use the datasettool adapter base`.

### Task 3: leitor de planilhas do kit

**Arquivos:** `src/namescommons/adapters/es_ine_residentes.py`, `tests/test_es_ine_residentes.py`, `.github/workflows/ci.yml`, `tests/fixtures/ATRIBUICAO.md`, `pyproject.toml`, `uv.lock`.

- [x] Teste: `test_leitor_do_kit_le_as_amostras_do_ine` (o antigo `test_r1_3_amostras_do_ine`, com as mesmas entradas e valores esperados) e `test_namescommons_spreadsheet_nao_existe`.
- [x] O adaptador importa de `datasettool.sources.spreadsheet`.
- [x] Remover `src/namescommons/spreadsheet.py`, `tests/test_spreadsheet.py` e `tests/fixtures/planilhas/tipos.xls`; tirar `! -name planilhas` da CI e a frase de `ATRIBUICAO.md`; tirar `xlrd` das dependências diretas.
- [x] Suíte verde; commit `refactor(spreadsheet): read spreadsheets with datasettool`.

### Task 4: cache de downloads do kit

**Arquivos:** `src/namescommons/__init__.py`, `src/namescommons/pipeline.py`, `tools/amostra_wikidata.py`; testes `tests/test_tools_dataset.py`, `tests/test_pipeline.py`, `tests/test_cli_pipeline.py`, `tests/test_us_ssa_births.py`.

- [x] Testes: `test_user_agent_igual_ao_anterior` (texto exato), `test_pipeline_envia_o_user_agent_do_projeto` (cabeçalho recebido pelo servidor local) e `test_namescommons_cache_nao_existe`.
- [x] `USER_AGENT` com `make_user_agent`; o pipeline chama `fetch_resource` do kit com ele; opções `backoff`, `attempts`, `sleep`.
- [x] Ajustar para o inglês as mensagens de download conferidas.
- [x] Encontrado na implementação: o cache do kit recusa links simbólicos (spec, R4.3, item 5); `tools/bench_pipeline.py --wikidata` passa a usar link físico ou cópia, e a decisão foi para [tools-dataset#9](https://github.com/BenchCommons/tools-dataset/issues/9).
- [x] Remover `src/namescommons/cache.py` e `tests/test_cache.py`.
- [x] Suíte verde; commit `refactor(cache): download through datasettool with the project User-Agent`.

### Task 5: registro de fontes sobre o kit

**Arquivos:** `src/namescommons/sources.py`, `pyproject.toml`, `uv.lock`; testes `tests/test_sources.py`, `tests/test_sources_extensoes.py`, `tests/test_tools_dataset.py`.

- [x] Testes: `test_campo_de_nomes_ausente` (`country` ausente), `test_source_error_e_o_registry_error_do_kit`, `test_licencas_aceitas` (lista do kit mais `statcan-open-licence`), e os de `strips_accents` que já existem.
- [x] `SCHEMA` com os campos de nomes, `checks` com a regra de uma `primary`, fábrica do `Source`; `load_sources` e `parse_sources` chamam o kit.
- [x] Remover os testes genéricos listados no plano; nenhum teste confere ordem de linhas.
- [x] Tirar `pyyaml` das dependências diretas.
- [x] Suíte verde; commit `refactor(sources): build the names registry on datasettool`.

### Task 6: auxiliares de arquivo do manifesto

**Arquivos:** `src/namescommons/manifest.py`; testes `tests/test_robustez.py`, `tests/test_tools_dataset.py`.

- [x] Teste: `test_manifesto_usa_describe_files` (CSV e Parquet contados; arquivo de outra extensão é `ValueError`).
- [x] `build_manifest` com `describe_files(out_dir, counters={".csv": count_csv_records, ".parquet": ...})`.
- [x] Remover `tests/test_manifest.py` e `test_manifesto_conta_registros_csv_e_nao_linhas_fisicas`.
- [x] Suíte verde; commit `refactor(manifest): checksums and row counts from datasettool.files`.

### Task 7: documentação e verificação

**Arquivos:** `AGENTS.md`, `README.md`, `docs/specs/ROADMAP.md`, esta pasta.

- [x] `AGENTS.md`: stack com o kit e a regra de atualização (ADR 0013). `README.md`: seção de desenvolvimento.
- [x] Verificar: `uv sync --locked`, `uv run pytest -q`, os dois passos offline da CI com `diff -r` contra a linha de base, `namescommons run --offline` sobre o cache real com `diff -r`, e `tools/bench_pipeline.py --observacoes 200000`.
- [x] Commit `docs(toolkit): document the tools-dataset dependency`.

## Verificação (2026-10-12)

| Critério | Evidência |
|---|---|
| 1 | `uv sync --locked` instala `benchcommons-tools-dataset==0.1.0` de `git+https://github.com/BenchCommons/tools-dataset@f3251d8` (tag `v0.1.0`); `test_uv_lock_aponta_a_tag` |
| 2 | `cache.py` e `spreadsheet.py` removidos; `test_namescommons_cache_nao_existe`, `test_namescommons_spreadsheet_nao_existe`; nenhum `import yaml` em `src/` |
| 3 | `uv run pytest -q`: 585 testes verdes (eram 832; os removidos têm equivalentes entre os 360 testes do kit, verdes na tag) |
| 4 | Os dois passos offline da CI passam; `diff -r` contra `master` (`0153007`) sem diferença: 8 observações no exemplo, 109 nas fontes oficiais |
| 5 | `namescommons run --offline` no cache real completo: 4.336.051 observações, `diff -r` sem diferença (89 s e 2,84 GB de pico, contra 123 s e 2,96 GB em `master`) |
| 6 | `tools/bench_pipeline.py --observacoes 200000`: 199.920 observações, ingest 1,5 s, build 1,3 s, 261 MB; com `--wikidata`: 1.016.691 observações e 436.971 ligações, 1.765 MB |
| 7 | Lista no plano (seção Removidos) e na descrição do PR |
| 8 | Checklist da issue tools-dataset#5 marcado; pendências em issues |
