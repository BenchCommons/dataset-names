# 005. Variantes: tarefas

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar os comandos na raiz do repositório. Antes da Task 1, rodar `uv sync` e conferir que `uv run pytest -q` passa. Cada tarefa começa pelo teste que falha e termina com `uv run pytest -q` verde e um commit.

---

### Task 1: escrita (R1)

**Arquivos:** `src/namescommons/normalize.py`, `tests/test_normalize.py`.

- [x] Testes que falham: `佐々木` é `Hani`; `ユーリ` é `Kana`; `Ａｎｎａ` é `Latn`; `さくら子` e `ゆかりユカリ` são `Jpan`; `김金` é `Kore`; `ଦାସ` é `Orya`, `ܡܝܟܐܝܠ` é `Syrc`, `ᏣᎳᎩ` é `Cher`; letra de escrita fora da tabela continua `Zzzz`; empate entre duas escritas continua resolvido pela ordem do código.
- [x] `detect_script`: nome Unicode sem os prefixos `FULLWIDTH` e `HALFWIDTH`; prefixos de duas palavras (`OL CHIKI`, `CANADIAN SYLLABICS`, `WARANG CITI`, `MEETEI MAYEK`, `SYLOTI NAGRI`, `EGYPTIAN HIEROGLYPH`); `々` como `Hani`; `ー`, `ゝ`, `ゞ`, `ヽ`, `ヾ` ignorados; `Jpan` e `Kore` pelas combinações de R1.3.
- [x] `uv run pytest -q` e commit.

### Task 2: forma ASCII (R2)

**Arquivos:** `src/namescommons/normalize.py`, `src/namescommons/schema.py`, `tests/test_normalize.py`, `tests/test_schema.py`.

- [x] Testes que falham: os exemplos do critério de aceite 2; `ß`, `ø`, `æ`, `ł`, `þ` como antes; `Llorenç` vira `llorenc`; `Nel·lo` vira `nello`; `Jo–Anne` vira `jo-anne`; ZWJ omitido; `Μαρία`, `李`, `ଦାସ` e `Aʃa` vazios; `validate` aceita nome latino com `ascii` vazio e recusa `ascii` com maiúscula ou caractere fora do ASCII.
- [x] `ascii_form(name, script)`: `script` deixa de decidir (mantido na assinatura por compatibilidade); transliteração caractere a caractere pelas tabelas do ADR 0012, vazio se algum caractere ficar sem transliteração.
- [x] `uv run pytest -q` e commit.

### Task 3: capitalização com partículas (R3)

**Arquivos:** `src/namescommons/normalize.py`, `tests/test_normalize.py`, `tests/test_ci.py`.

- [x] Testes que falham: os exemplos do critério de aceite 3; `ALVES DA SILVA` vira `Alves da Silva`; `GABRIEL Y GALAN` vira `Gabriel y Galan`; `JEAN-DE-DIEU` continua `Jean-De-Dieu`; fonte de caixa mista não muda `Da Silva`.
- [x] `normalize_name` com `uniform_case` verdadeiro aplica R3.1 a R3.3 depois da capitalização por palavra.
- [x] Atualizar `ES_CSV` em `tests/test_ci.py` (`Francesc d'Assis`, `Joana d'Arc`).
- [x] `uv run pytest -q` e commit.

### Task 4: fontes que removem acentos (R6, R7.3)

**Arquivos:** `src/namescommons/sources.py`, `sources.yaml`, `tests/test_sources_extensoes.py`, `docs/specs/002-pipeline/spec.md`.

- [x] Testes que falham: `strips_accents` padrão `false`; `true` aceito; valor não booleano recusado; em `sources.yaml`, exatamente `ca-statcan-births`, `es-ine-residentes` e `us-ssa-births` têm `true`.
- [x] `OPCIONAIS` e `Source` ganham `strips_accents`; nota em R2 da spec 002.
- [x] `uv run pytest -q` e commit.

### Task 5: forma de exibição (R4)

**Arquivos:** `src/namescommons/aggregate.py`, `tests/test_aggregate.py`.

- [x] Testes que falham: a forma com mais nascimentos somados num país e a com mais pessoas vivas em outro não somam contagens no índice (o critério é o número de países); por país, só as observações contadas pesam (fonte não `primary` e edição antiga não pesam); forma publicada vence a gerada por caixa uniforme, no país e no índice; sem fontes (`sources=None`), comportamento por contagens dentro do país continua.
- [x] `display_name` recebe as observações candidatas, os pesos contados e devolve a forma; `by_country` e `name_index` aplicam R4.1 a R4.3; `CountryRow.published_case` interno.
- [x] `uv run pytest -q` e commit.

### Task 6: agrupamento (R5)

**Arquivos:** `src/namescommons/variants.py` (novo), `tests/test_variants.py` (novo).

**Produz:** `group_ids(keys: list[str], ascii: list[str], unaccented: list[bool], links: Iterable[VariantLink] | None, kind: str) -> list[str]`, com `keys` ordenadas e sem repetição.

- [x] Testes que falham, com ligações escritas à mão: `test_nome_sozinho_e_seu_grupo`; `test_same_item_junta_e_e_nao_dirigido`; `test_other_gender_so_em_sobrenomes`; `test_transliteracao_inequivoca_junta`; `test_romanizacao_ambigua_nao_junta`; `test_sem_acento_junta_marie_eve`; `test_sem_acento_ambiguo_nao_junta`; `test_acentuados_nao_se_juntam_sem_fonte_sem_acento`; `test_different_from_separa`; `test_tipos_diferentes_nunca_juntam`; `test_p460_nao_junta`; `test_ligacao_sem_observacao_e_ignorada`; `test_juncao_pela_chave_e_nao_pelo_texto`; `test_resultado_nao_depende_da_ordem`; `test_group_id_e_a_menor_chave`.
- [x] Implementação e commit.

### Task 7: `group_id` no índice e manifesto (R5, R7.4)

**Arquivos:** `src/namescommons/aggregate.py`, `src/namescommons/cli.py`, `tests/test_cli_links.py`, `tests/test_aggregate.py`.

- [x] Testes que falham: `name_index` com ligações e fontes preenche `group_id` em todas as linhas; `build --links` com uma ligação `same_item` grava o mesmo `group_id` nas duas linhas de `given_names.csv`; o `manifest.json` lista a fonte de uma ligação mesmo sem observação dela.
- [x] `name_index` monta `keys`, `ascii` e a marca de sem acento e chama `group_ids`; `_build` passa fontes e ligações e usa a união das fontes.
- [x] `uv run pytest -q` e commit.

### Task 8: versão, notas de contrato e CI (R7.1, R7.2, R8, R10)

**Arquivos:** `src/namescommons/schema.py`, `tests/test_manifest.py`, `tests/test_io.py`, `.github/workflows/ci.yml`, `tests/test_ci.py`, `docs/specs/001-esquema/spec.md`, `docs/specs/002-pipeline/spec.md`.

- [x] Testes que falham: `schema_version` `1.2.0`; o passo da CI das fontes oficiais confere `group_id` em todas as linhas de `given_names.csv`.
- [x] Notas na spec 001 (R3 e R5) e na spec 002 (R1).
- [x] `uv run pytest -q` e commit.

### Task 9: memória do `run` (R9.3, R9.4; issue #31)

**Arquivos:** `src/namescommons/io.py`, `tools/bench_pipeline.py`, `tests/test_benchmark.py`.

- [x] Testes que falham: `write_observations` com lote de 2 grava e relê as mesmas observações, em vários grupos de linhas; arquivo vazio continua com o esquema; `bench_pipeline --wikidata` com a amostra de `tests/fixtures/wikidata` mede e grava `variant_links.parquet`.
- [x] `write_observations` com `pq.ParquetWriter` e `LOTE_DE_ESCRITA = 250_000`; `--wikidata` no bench.
- [x] `uv run pytest -q` e commit.

### Task 10: correções da revisão do PR #38

**Arquivos:** `src/namescommons/variants.py`, `src/namescommons/aggregate.py`, `src/namescommons/normalize.py`, `src/namescommons/schema.py`, `tests/test_variants.py`, `tests/test_normalize.py`, spec, ADR 0010, spec 001 e roadmap.

- [x] Testes que falham: `장` de `张` e `蒋` não faz ponte; rótulo de dois itens do mesmo grupo junta; `見` -> `현` não entra no grupo de `玄`, nem quando `현` fica sozinho; `Герман` -> `Herman` junta com `Hermanová`; nome sem acento já em outro grupo não junta; ordem embaralhada com transliteração e sem acento; `™`, `ℳ`, `℡` e `𝓜` sem maiúscula em `ascii`; `ｰ`, `〆` e `Hrkt`; partícula na última palavra.
- [x] Fase 1 por itens (R5.3), concorrência na fase 2 (R5.4), `casefold` depois da NFKD (R2.1), `Hrkt` (R1.3), partícula só com palavra seguinte (R3).
- [x] Medição do agrupamento no lote real (R5.8) e `uv run pytest -q`.

### Fechamento

- [x] Medição de R9 com os arquivos reais: `run --offline` com o lote completo e com o sintético mais o Wikidata, na master e nesta branch, nas mesmas condições.
- [x] Números reais do agrupamento (R5.8) no pull request.
- [x] Issues para o que ficou fora: transliteração de grego, hangul, kana e demais escritas (#35); `group_id` em `by_country` e junções aplicadas (#36); cognatos pela P460 (#37).
- [x] Pull request #38 com `Closes #4` e `Closes #31`.
