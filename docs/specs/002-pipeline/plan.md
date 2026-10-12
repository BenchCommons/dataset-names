# 002. Pipeline de ingestão: plano de implementação

**Objetivo:** implementar o contrato do adaptador, o cache de downloads, os comandos `fetch`, `ingest` e `run`, a validação cruzada com `sources.yaml`, a CI e a medição de desempenho da spec 002, e fechar as pendências de robustez da issue #2.

**Arquitetura:** três módulos novos no pacote `namescommons`. `adapters/__init__.py` define `Resource`, `RawRecord` e a carga de um módulo de adaptador por `source_id`; `cache.py` baixa cada recurso para `cache/<source_id>/<filename>` com `urllib`, metadados e escrita atômica; `pipeline.py` transforma `RawRecord` em `Observation` (R1.1 a R1.5), valida cada fonte e encadeia cache e `parse`. A CLI ganha `fetch`, `ingest` e `run` e reaproveita o `build` da spec 001. O adaptador de exemplo do critério de aceite 1 vive em `tests/adaptadores/` e é carregado com `--adapters adaptadores`, sem entrar no pacote publicado.

**Stack:** a mesma da spec 001 (Python 3.12 via `uv`, `pyarrow`, `pyyaml`, `pycountry`, `pytest`). Downloads com `urllib.request` da biblioteca padrão; testes de download com `http.server` local numa thread; CI no GitHub Actions com `astral-sh/setup-uv`.

**Spec:** [`spec.md`](spec.md). Depende da [spec 001](../001-esquema/spec.md). Pendências herdadas: issue #2.

## Restrições globais

- Nenhuma dependência nova de runtime ou de desenvolvimento.
- Os testes nunca acessam a rede: downloads usam o servidor de `tests/conftest.py` em `127.0.0.1`.
- Cache em `cache/<source_id>/<filename>` e `cache/<source_id>/<filename>.meta.json` (`url`, `downloaded_at` em ISO 8601 UTC, `sha256`, `size`); `/cache/` no `.gitignore`.
- `User-Agent`: `namescommons/<versão do pacote> (+https://github.com/BenchCommons/dataset-names)`. Timeout de 60 s, 3 tentativas, espera de 2 s e 4 s entre elas.
- Faixa de `year`: 1800 até o ano corrente mais um, calculado na hora da validação.
- Mensagem de falha de fonte: `fonte '<id>': <causa>`, código de saída 1, sem traceback e sem saída parcial.
- `SCHEMA_VERSION` continua `1.0.0`: nenhum campo de saída muda.

## Decisões de implementação

| Decisão | Motivo |
|---|---|
| Adaptador de exemplo em `tests/adaptadores/exemplo.py`; a CLI aceita `--adapters PACOTE` (padrão `namescommons.adapters`) | O critério 1 pede um adaptador "escrito só para teste"; fora de `src/` ele não vai para o pacote, e a CI o usa com `PYTHONPATH=tests` |
| O pipeline não preenche `country` com o país da fonte | R1.2 só tira `count_type` e `source_id` de `sources.yaml`; a recusa de R3 pega o adaptador que esquecer o país |
| R1.1 também remove espaços em volta de `country` e `gender` preenchidos (`" PT "` vira `"PT"`) | Mesmo tratamento do vazio; o valor só com espaços já vira `None` |
| Repetidos pela chave (R1.4) mantêm a forma de exibição de maior `count` (empate: a do primeiro registro); repetidos com e sem `count` são erro | Mesmo critério de `display_name` na agregação, determinístico pela ordem do arquivo; somar contagem com ausência não tem significado. Revisada na manutenção das issues #6 e #12: antes valia sempre a forma do primeiro registro |
| `uniform_case: false` preserva a caixa publicada; `make_observation` sem o parâmetro mantém a heurística da spec 001 | O pipeline sempre passa o valor da fonte; testes e chamadas da 001 continuam válidos |
| País ou `count_type` fora do domínio não gera também o erro de divergência com a fonte | Uma causa por campo; preserva `test_lista_todos_os_erros` da 001 |
| `ingest` valida cada fonte separadamente e converte qualquer exceção de `parse` em `PipelineError` | R5 exige mensagem que nomeia a fonte e a causa; um CSV corrompido não pode virar traceback |
| `ingest` sem `--offline` baixa só o que falta no cache; `run --offline` pula o `fetch`; `--offline` com `--refresh` é erro | Coerente com R4: sem `--refresh` nada é rebaixado, com `--offline` nada é baixado |
| Arquivo presente no cache significa arquivo de dados presente; o `.meta.json` antigo é removido, os dados entram por `rename` e só então o `.meta.json` novo é gravado | O cache montado a partir das fixtures na CI (e o arquivo baixado à mão, ver spec 003 R4) funciona sem metadados; uma queda entre as gravações deixa o arquivo sem meta, nunca um meta descrevendo outro arquivo. Revisada na manutenção da issue #6: antes o meta era gravado primeiro |
| Download incompleto é detectado comparando os bytes recebidos com `Content-Length`; falha de rede, 5xx, 408 e 429 são tentadas de novo; os demais 4xx (400, 401, 403, 404, 410...) são respostas definitivas e falham na primeira tentativa | `http.client` não acusa resposta truncada em leituras por bloco. Revisada na manutenção das issues #6 e #12: antes toda falha era tentada de novo, e um 404 ou 403 custava 6 s de espera sem chance de mudar |
| `ingest --out` grava num `.part` ao lado e renomeia, avisando em stderr quando substitui um arquivo; `build` e `run` montam a release num diretório temporário ao lado de `--out` e o renomeiam no fim | Uma falha (disco, agregação) não deixa arquivo nem release parciais. Adicionada na manutenção da issue #6 |
| Observações de `ingest` ordenadas por (`source_id`, `kind`, `country`, `name_key`, `year`, `gender`) | R6: duas execuções produzem Parquet com as mesmas linhas na mesma ordem, independente da ordem do arquivo da fonte |
| `run` não aceita IDs; `fetch` e `ingest` aceitam; nenhuma fonte com adaptador é erro | Segue a tabela de R5; uma release sempre usa todas as fontes com adaptador |
| `Observation` com `slots=True` e Parquet lido e gravado por colunas, com textos repetidos compartilhados | Na medição de R8 do protótipo, o tempo caiu de 240 s para 140 s; o pico de memória ficou em 1,4 GB (após a Task 10; a issue #8 mediu antes da otimização), sem dicionário por linha. Com o bench realista da manutenção da issue #6 (25 mil nomes distintos em vez de 5 mil), o pipeline anterior à manutenção mediu ingest 41 s e pico de 2,7 GB; com a manutenção (caminho rápido para repetidos de mesma forma, resolução da forma de maior peso só nas chaves com duas formas) ficou ingest 37 s, build 32 s e pico de 2,7 GB, dentro do limite de 4 GB |
| O script de R8 roda `ingest` e `build` pela CLI, com um adaptador sintético gerado num diretório temporário | Mede os comandos reais, inclusive leitura do CSV, validação e escrita, e não só a agregação |

## Foco de revisão

Casos que a spec implica e que um usuário vai encontrar. Cada um tem teste na tarefa dona do código.

1. **Sigla numa fonte de caixa mista** (`DJ`) continua `DJ`, e a mesma sigla numa fonte só em maiúsculas vira `Dj` (Task 2: `test_fonte_de_caixa_mista_preserva_a_caixa_publicada`, `test_fonte_de_caixa_uniforme_capitaliza_todos`; Task 7: `test_r1_3_fonte_de_caixa_mista_preserva`).
2. **Fonte que publica o total e a divisão por gênero no mesmo ano** falha a ingestão nomeando a fonte, em vez de dobrar `count` (Task 7: `test_r1_5_total_e_divisao_por_genero_juntos_sao_recusados`, `test_ingest_recusa_violacao_de_r1_5`).
3. **Conexão que cai no meio de um `--refresh`** não apaga nem corrompe a versão que já estava no cache (Task 6: `test_refresh_interrompido_preserva_a_versao_anterior`, `test_download_interrompido_nao_fica_no_cache`).
4. **Arquivo da fonte com formato inesperado** termina com código 1, mensagem `fonte 'exemplo': KeyError: 'nome'` e nenhum `observations.parquet` gravado (Task 7: `test_ingest_arquivo_corrompido_nomeia_a_fonte_e_a_causa`; Task 8: `test_ingest_com_arquivo_corrompido_falha_sem_saida`).
5. **A mesma fonte com linhas em outra ordem** gera as mesmas observações, e dois `run --offline` geram CSVs idênticos byte a byte (Task 7: `test_saida_independe_da_ordem_dos_registros`; Task 8: `test_criterio_4_dois_runs_offline_identicos`).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `src/namescommons/sources.py` | `uniform_case`, `adapter`; recusa de `retrieved` com hora e `url` sem `http`/`https` | 1 |
| `src/namescommons/normalize.py`, `src/namescommons/schema.py` | `normalize_name(..., uniform_case)`, `derive_name_fields`; validação cruzada com a fonte e faixa de `year`; `Observation` com `slots` | 2, 3, 10 |
| `src/namescommons/aggregate.py`, `src/namescommons/io.py`, `src/namescommons/manifest.py` | Robustez da issue #2; leitura e escrita colunares | 4, 10 |
| `src/namescommons/adapters/__init__.py` | `Resource`, `RawRecord`, `AdapterError`, `check_adapter`, `load_adapter` | 5 |
| `tests/adaptadores/`, `tests/fixtures/` | Adaptador de exemplo, amostra da fonte e `sources.yaml` de teste | 5 |
| `src/namescommons/cache.py`, `tests/conftest.py` | `fetch_resource`, `FetchError`; servidor HTTP local dos testes | 6 |
| `src/namescommons/pipeline.py` | `to_observations`, `select_sources`, `fetch_sources`, `ingest_sources`, `PipelineError` | 7 |
| `src/namescommons/cli.py` | `namescommons fetch`, `ingest` e `run` | 8 |
| `.github/workflows/ci.yml`, `.gitignore` | CI em todo push e pull request; cache fora do git | 9 |
| `tools/bench_pipeline.py` | Medição de R8 com 3 milhões de observações sintéticas | 10 |

## Cobertura da spec

| Requisito | Tarefa |
|---|---|
| R1 (contrato do adaptador) | 5, 7 |
| R1.1, R1.2, R1.4, R1.5 | 7 |
| R1.3 | 2, 7 |
| R2 | 1 |
| R3 (observação contra a fonte e faixa de `year`) | 3 |
| R3 (`retrieved` e `url`) | 1 |
| R4 | 6, 9 |
| R5 | 7, 8 |
| R6 | 7, 8 |
| R7 | 5, 6, 9 |
| R8 | 10 |
| R9 | 4 |
| Critério de aceite 1 | 5, 8 (`test_criterio_1_fetch_ingest_build`) |
| Critério 2 | 2, 3, 7 |
| Critério 3 | 6, 8 |
| Critério 4 | 8 (`test_criterio_4_dois_runs_offline_identicos`) |
| Critério 5 | 9 e fechamento (CI verde no pull request) |
| Critério 6 | 10 (passo de medição) |
| Critério 7 | 4 e fechamento (`Closes #2` no pull request) |
