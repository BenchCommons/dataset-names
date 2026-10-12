# 004. Wikidata: plano de implementação

**Objetivo:** ingerir os prenomes e sobrenomes do Wikidata como fonte `attested`, gravar as ligações entre variantes numa tabela própria para a spec 005 e corrigir a regra de `primary` em fontes `attested` (issue #3).

**Arquitetura:** o adaptador `src/namescommons/adapters/wikidata.py` declara as consultas SPARQL (texto, variáveis, ordem e número de páginas) e deriva delas os 15 `Resource` com URL fixa no QLever. `parse` lê as páginas de rótulos com `json` da biblioteca padrão, uma de cada vez, e emite `RawRecord` sem país, ano nem contagem. A função opcional `links` lê de novo os rótulos, monta o mapa item -> rótulos e cruza com as páginas de ligação e de transliteração, emitindo `RawLink`. O módulo novo `src/namescommons/links.py` define `VariantLink`, `RELATIONS` e `validate_links`; `pipeline.py` ganha `to_links` e `ingest_links`; `io.py` ganha `LINK_SCHEMA`, `write_links` e `read_links`; a CLI ganha `--links` em `ingest` e `build`, e `run` grava `variant_links.parquet`. `sources.py` deixa de conferir `primary` em `attested`.

**Stack:** a mesma da spec 003 (Python 3.12 via `uv`, `pyarrow`, `pyyaml`, `pycountry`, `pytest`), sem dependência nova. Formato lido: SPARQL 1.1 Query Results JSON.

**Spec:** [`spec.md`](spec.md). ADRs: [`0001`](../../adr/0001-licenca-dos-dados.md), [`0004`](../../adr/0004-acesso-ao-wikidata.md), [`0005`](../../adr/0005-ligacoes-entre-variantes.md). Pendências herdadas: issue #3.

## Restrições globais

- Nenhuma dependência nova de runtime ou de desenvolvimento.
- Os testes nunca acessam a rede. A amostra fica em `tests/fixtures/wikidata/`, com os mesmos 15 nomes de arquivo de `RESOURCES` e menos de 20 KB no total.
- Mensagens: `FormatError` com o arquivo e o esperado; `ligação N: <causa>` para erros de `RawLink`, com N a partir de 1 na ordem de `links`.
- A tabela de observações não muda. `SCHEMA_VERSION` passa a `1.1.0` porque a release ganha `variant_links.parquet`.
- `User-Agent` com o repositório transferido: `https://github.com/BenchCommons/names-commons-dataset`.

## Decisões de implementação

| Decisão | Motivo |
|---|---|
| QLever em vez de WDQS ou dump (ADR 0004) | O WDQS estourou o tempo nas consultas de sobrenome; o dump tem mais de 100 GB |
| Páginas de 200.000 linhas, número fixo por consulta (1, 5, 3, 1, 1, 1, 2, 1) | Cerca de 500 MB por página lida; o arquivo de sobrenomes inteiro passava de 1,8 GB. A folga sobre o medido é de 36% a 49% nos sobrenomes e prenomes |
| URL com `action=sparql_json` | O cache baixa só com `User-Agent`; o formato fica determinado pela URL e não pelo cabeçalho `Accept` |
| Uma consulta por propriedade de ligação | A consulta única com `VALUES ?property` estourou memória e tempo no QLever |
| Alvo da ligação não é restrito a itens de nome na consulta; o filtro é feito em Python | A restrição no SPARQL estourou o tempo; o mapa de rótulos já diz quais itens são nomes |
| `parse` agrupa por (`name_key`, `kind`) e emite uma linha por gênero informado, ou uma sem gênero | Cumpre R1.5 da spec 002 dentro do adaptador, sem perder atestação (R3.5) |
| Unissex vira `F` e `M` | A classe diz que o nome é usado pelos dois gêneros; uma linha vazia conflitaria com o mesmo nome em itens masculinos ou femininos |
| `links` lê os rótulos de novo, em vez de dividir estado com `parse` | O contrato da spec 002 trata `parse` como função pura sobre os arquivos; ler 130 MB de JSON duas vezes custa segundos |
| Auto-ligação por `name_key` e `kind` descartada no pipeline (`to_links`), recusada em `validate_links` | `Andrea` masculino P1889 `Andrea` feminino é a mesma chave e não informa nada para agrupar chaves |
| `ingest_links` devolve `None` quando nenhuma fonte selecionada tem `links` | `run` só grava `variant_links.parquet` quando há fonte de ligações; a release das fontes de teste da spec 002 não muda |
| Amostra gerada por `tools/amostra_wikidata.py`, que roda as consultas do módulo com `VALUES ?item` | Reproduz a amostra a partir do código, e as consultas da amostra são as mesmas de produção |
| `REPOSITORIO` de `cache.py` aponta para `BenchCommons` | O repositório foi transferido; o contato no `User-Agent` precisa funcionar (política da Wikimedia) |

## Foco de revisão

1. **Nome dos dois gêneros vindo de itens diferentes** (`Andrea` masculino, feminino e unissex; `Letha` sem gênero e feminino) não pode quebrar R1.5 nem perder gênero (Task 3: `test_parse_da_amostra_real`, `test_genero_vazio_cede_ao_informado`).
2. **Wikidata cresce além das páginas** e a última página vem cheia: falha alta, não perda silenciosa (Task 3: `test_ultima_pagina_cheia_falha`).
3. **Páginas de momentos diferentes do índice** (Task 3: `test_pagina_com_linhas_depois_de_incompleta_falha`).
4. **Rótulos que não são nomes** (`Q34147`, `Ritwik (given name)`, `Felbert,von`, valor desconhecido) não entram nem como observação nem como ligação (Task 3: `test_rotulos_que_nao_sao_nomes_sao_pulados`; Task 4: `test_links_da_amostra_real`).
5. **Duas fontes `attested` sem país** passam sem `primary`; duas `births` no mesmo país continuam exigindo uma (Task 1).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `src/namescommons/sources.py`, `tests/test_sources.py` | Regra de `primary` só para `births` e `population` (R5) | 1 |
| `src/namescommons/adapters/__init__.py` | `RawLink`; `check_adapter` confere `links` | 2 |
| `src/namescommons/links.py` | `VariantLink`, `RELATIONS`, `validate_links` (R4.2, R4.5) | 2 |
| `src/namescommons/pipeline.py` | `to_links`, `ingest_links` (R4.4) | 2 |
| `src/namescommons/io.py` | `LINK_SCHEMA`, `write_links`, `read_links` | 2 |
| `src/namescommons/schema.py`, `tests/test_io.py` | `SCHEMA_VERSION` 1.1.0 (R4.7) | 2 |
| `tests/test_links.py` | Testes de R4.1, R4.2, R4.4 e R4.5 | 2 |
| `src/namescommons/adapters/wikidata.py` | Consultas, recursos, leitura paginada, `parse` (R1 a R3) e `links` (R4.3) | 3, 4 |
| `tools/amostra_wikidata.py` | Gera a amostra a partir das consultas do módulo | 3 |
| `tests/fixtures/wikidata/`, `tests/fixtures/ATRIBUICAO.md`, `sources.yaml` | Amostra, atribuição e registro da fonte | 3 |
| `src/namescommons/cache.py`, `tests/test_cache.py` | `User-Agent` com o repositório transferido | 3 |
| `tests/test_wikidata.py` | Testes do adaptador | 3, 4 |
| `src/namescommons/cli.py`, `tests/test_cli_pipeline.py` | `--links` em `ingest` e `build`; `variant_links.parquet` em `run` (R4.6) | 5 |
| `.github/workflows/ci.yml`, `tests/test_ci.py` | Passo da CI com o Wikidata (R7) | 5 |

## Cobertura da spec

| Requisito | Tarefa |
|---|---|
| R1 | 3 |
| R2.1, R2.2 | 3 (`test_recursos_e_consultas`) |
| R2.3 | 3 |
| R2.4, R2.5 | 3, 4 |
| R3.1 a R3.7 | 3 |
| R4.1, R4.2, R4.4, R4.5, R4.7 | 2 |
| R4.3 | 4 |
| R4.6 | 5 |
| R5 | 1 |
| R6 | 3, 4 (`tests/test_fontes_oficiais.py` percorre a nova fonte) |
| R7 | 5 |
| R8 | Fechamento (medição com os arquivos reais) |
| Critério de aceite 1 | 3 |
| Critério 2 | 3 |
| Critério 3 | 4 |
| Critério 4 | 3 |
| Critério 5 | 5 |
| Critério 6 | 1 |
| Critérios 7, 8, 9 | Fechamento |
