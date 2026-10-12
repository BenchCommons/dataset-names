# 006. Publicação: tarefas

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar os comandos na raiz do repositório, a partir de `master` em `4cb2c5f`, com `uv sync --locked` e `uv run pytest -q` verdes antes da Task 1.

Cada tarefa segue TDD: escrever os testes, ver falhar com `uv run pytest -q <arquivo>`, mudar o código, ver passar, rodar a suíte inteira e fazer um commit.

---

### Task 1: canal de descarte

**Arquivos:** `src/namescommons/adapters/__init__.py`, `src/namescommons/adapters/nz_dia_births.py`, `src/namescommons/pipeline.py`, `src/namescommons/io.py`, `src/namescommons/cli.py`; testes `tests/test_descartes.py`, `tests/test_nz_dia_births.py`.

- [ ] Testes: `test_nz_emite_raw_drop_para_nomes_corrompidos` (três `RawDrop` da amostra, 49 registros) e `test_nz_nao_usa_logging`; `test_pipeline_conta_descartes_por_fonte` (linhas, registros, formas), `test_pipeline_avisa_descartes_no_logger`, `test_descarte_invalido_e_erro`, `test_numeracao_de_registros_ignora_descartes`; `test_ingest_grava_descartes_no_parquet` (inclusive zero), `test_parquet_sem_metadados_da_descartes_desconhecidos`.
- [ ] `RawDrop`; `Drops` e `ingest_sources(..., drops=)` no pipeline; `write_observations(..., dropped=)` e `read_dropped` em `io`; `ingest` grava.
- [ ] Suíte verde; commit `feat(pipeline): count records dropped by adapters per source`.

### Task 2: manifesto

**Arquivos:** `src/namescommons/manifest.py`, `src/namescommons/schema.py`, `src/namescommons/cli.py`; testes `tests/test_io.py`, `tests/test_descartes.py`, `tests/test_links.py`, `tests/test_cli_links.py`, `tests/test_cli_pipeline.py`.

- [ ] Testes: `test_manifest_traz_nome_observacoes_e_descartes`, `test_manifest_traz_data_license`, `test_build_le_descartes_do_parquet`, `test_build_sem_metadados_deixa_dropped_nulo`, `test_run_grava_descartes_no_manifesto`; versão `1.3.0` nos testes existentes.
- [ ] `build_manifest(..., observations=, dropped=)`; `SCHEMA_VERSION = "1.3.0"`.
- [ ] Suíte verde; commit `feat(manifest): record per-source observations and dropped records`.

### Task 3: licenças, atribuições e `DATA_LICENSE`

**Arquivos:** `src/namescommons/publication.py`, `DATA_LICENSE`; teste `tests/test_publicacao.py`.

- [ ] Testes: `test_tabela_cobre_as_licencas_aceitas`, `test_atribuicao_reproduz_o_texto_sem_edicao`, `test_atribuicao_em_ordem_de_id_so_com_fontes_usadas`, `test_aviso_de_condicoes_so_com_statcan`, `test_licenca_sem_entrada_falha`, `test_aviso_do_readme_igual_ao_da_tabela`, `test_data_license_tem_a_linha_de_atribuicao`, `test_sem_simbolos_da_statcan` (nenhum arquivo de `assets/` nem texto do README cita brasão ou logotipo da Statistics Canada).
- [ ] `LICENCAS`, `AVISOS`, `dataset_attribution(release)`, `attribution_text(release, sources, used)`; preâmbulo em `DATA_LICENSE`.
- [ ] Suíte verde; commit `feat(publication): generate the attribution file from sources.yaml`.

### Task 4: cartão do dataset

**Arquivos:** `src/namescommons/publication.py`; teste `tests/test_publicacao.py`.

- [ ] Testes: `test_cartao_tem_as_secoes`, `test_cartao_usa_os_numeros_do_manifesto`, `test_cartao_lista_fontes_sem_acento_e_descartes`, `test_cartao_traz_os_avisos_da_statcan`, `test_cartao_sem_statcan_nao_traz_avisos`, `test_cartao_data_do_wikidata`.
- [ ] `dataset_card(manifest, sources, countries, index_counts, links)`.
- [ ] Suíte verde; commit `feat(publication): generate the dataset card`.

### Task 5: pacote da release

**Arquivos:** `src/namescommons/publication.py`, `src/namescommons/cli.py`; testes `tests/test_publicacao.py`, `tests/test_cli.py`.

- [ ] Testes: `test_build_gera_todas_as_saidas` (lista nova), `test_sha256sums_verifica` (formato GNU, cobre o nível de cima, sem ele mesmo), `test_zip_tem_os_mesmos_bytes`, `test_dois_builds_iguais`, `test_copia_de_data_license_identica`, `test_data_license_ausente_falha_sem_saida`.
- [ ] `write_by_country_zip`, `write_sha256sums`; `_build` grava `DATA_LICENSE`, `ATTRIBUTION.txt`, `DATASET_CARD.md`, o zip e as somas; `--data-license` em `build` e `run`.
- [ ] Suíte verde; commit `feat(cli): write the publication files with every build`.

### Task 6: script e workflow de release

**Arquivos:** `tools/release.sh`, `.github/workflows/release.yml`, `.github/workflows/ci.yml`; teste `tests/test_release.py`.

- [ ] Testes (com `gh` falso no `PATH` que registra os argumentos): `test_build_local_sobre_as_amostras`, `test_release_fora_de_calver_e_recusada`, `test_fetch_cache_sem_rascunho_falha`, `test_upload_recusa_release_publicada`, `test_upload_sem_clobber_e_remove_o_cache_depois`, `test_upload_envia_so_os_arquivos_do_nivel_de_cima`; `test_workflow_nao_publica_nem_cria_tag`, `test_dispatch_e_ensaio`, `test_ci_roda_o_ensaio`.
- [ ] `tools/release.sh` com `build`, `fetch-cache` e `upload`; `release.yml`; passo de ensaio na CI.
- [ ] Suíte verde; commit `ci(release): build releases from a draft's source cache`.

### Task 7: `.gitignore`

**Arquivos:** `.gitignore`; teste `tests/test_ci.py`.

- [ ] Testes: `test_gitignore_sem_linhas_em_branco_duplas`, `test_parquet_de_fixture_nao_e_ignorado` (`git check-ignore`), `test_parquet_na_raiz_continua_ignorado`.
- [ ] Limpeza de R9.
- [ ] Suíte verde; commit `chore(gitignore): clean up leftovers and allow Parquet fixtures`.

### Task 8: documentação e verificação

**Arquivos:** `README.md`, `AGENTS.md`, `docs/specs/001-esquema/spec.md`, `docs/specs/ROADMAP.md`, esta pasta.

- [ ] README (layout, Releases, ensaio local); `AGENTS.md` (procedimento de release); notas na spec 001.
- [ ] Verificar: `uv sync --locked`, `uv run pytest -q`, os passos offline da CI, `tools/release.sh build` sobre as amostras com `sha256sum -c`, e dois builds com `SHA256SUMS` iguais.
- [ ] Commit `docs(release): document the release procedure`.

### Task 9: retirada de `legacy/` (aguarda aprovação)

Bloqueada: apaga arquivos versionados (ADR 0015). Não executar sem a aprovação explícita do dono sobre a lista da descrição do PR. Acompanhamento numa issue própria.

- [ ] `git rm -r legacy/`; `tests/test_legacy.py` confere a ausência; README e spec 001 atualizados.
