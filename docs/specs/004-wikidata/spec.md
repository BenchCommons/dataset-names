# 004. Wikidata

Parte do [roadmap](../ROADMAP.md). Depende da [spec 002](../002-pipeline/spec.md) e segue o contrato do adaptador da [spec 003](../003-fontes-oficiais/spec.md) (R2). Licença dos dados: [ADR 0001](../../adr/0001-licenca-dos-dados.md). Acesso aos dados: [ADR 0007](../../adr/0007-acesso-ao-wikidata.md). Ligações entre variantes: [ADR 0008](../../adr/0008-ligacoes-entre-variantes.md). Pendências herdadas: issue #3.

Status: Em implementação.

## Por quê

As fontes oficiais da spec 003 trazem contagens de cinco países, quase todas em escrita latina. O Wikidata cataloga cerca de 136 mil itens de prenome e 723 mil de sobrenome, de todas as escritas, com rótulo nativo (`Мария`, `李`, `Иванов`), classe de gênero (prenome masculino, feminino ou unissex; sobrenome masculino ou feminino) e ligações entre itens que a spec 005 precisa para agrupar variantes. Os dados estruturados do Wikidata são CC0.

O Wikidata não tem contagem nem país confiável: ele atesta que o nome existe. A regra de `primary` da spec 001 (R2) foi escrita para fontes com contagem e, como aponta a issue #3, obrigaria a escolher uma `primary` entre duas fontes `attested` multinacionais, onde ela não tem efeito. Esta spec corrige essa regra.

## Requisitos

### R1. Fonte e licença

Uma entrada em `sources.yaml` e um adaptador em `src/namescommons/adapters/wikidata.py`:

| Campo | Valor |
|---|---|
| `id` | `wikidata` |
| `license` | `CC0-1.0` |
| `country` | vazio (fonte multinacional) |
| `count_type` | `attested` |
| `primary` | `false` (sem efeito em `attested`, ver R5) |
| `suppression` | vazio |
| `uniform_case` | `false` (a caixa publicada é preservada) |

Licença conferida em https://www.wikidata.org/wiki/Wikidata:Licensing: "All structured data (i.e. the main, Property, Lexeme, and EntitySchema namespaces) is released into the public domain under Creative Commons Zero". CC0 está na lista do ADR 0001.

### R2. Acesso aos dados

- **R2.1 Endpoint e formato.** Cada recurso é o resultado de uma consulta SPARQL ao QLever (`https://qlever.dev/api/wikidata`) no formato SPARQL 1.1 Query Results JSON, pedido por GET com a consulta no parâmetro `query` e o formato no parâmetro `action=sparql_json`, de modo que a URL sozinha determina a resposta (ADR 0007). O texto das consultas fica no módulo e usa só SPARQL 1.1 padrão. O `User-Agent` é o do pipeline (spec 002, R4), com a URL do repositório como contato, como pede a política de User-Agent da Wikimedia; hoje `https://github.com/BenchCommons/dataset-names`.
- **R2.2 Consultas.** Cada consulta é ordenada e paginada com `LIMIT 200000 OFFSET k`, num número fixo de páginas:

| Consulta | Variáveis | Conteúdo | Linhas medidas | Páginas | Arquivos |
|---|---|---|---|---|---|
| Prenomes | `item`, `name`, `gender` | itens `P31/P279*` de `Q202444` com rótulo nativo (P1705) e, quando houver, a classe de gênero alcançada por `P31/P279*` | 134.180 (26 MB) | 1 | `given-names-1.json` |
| Sobrenomes | `item`, `name`, `gender` | o mesmo para `Q101352` | 734.234 (104 MB) | 5 | `family-names-1.json` a `family-names-5.json` |
| P460 | `item`, `target` | "said to be the same as" de itens de nome | 333.225 (50 MB) | 3 | `links-P460-1.json` a `-3` |
| P1533 | `item`, `target` | "family name identical to this given name" | 21.879 (3,3 MB) | 1 | `links-P1533-1.json` |
| P1560 | `item`, `target` | "given name version for other gender" | 2.971 (0,4 MB) | 1 | `links-P1560-1.json` |
| P5278 | `item`, `target` | "surname for other gender" | 22.980 (3,5 MB) | 1 | `links-P5278-1.json` |
| P1889 | `item`, `target` | "different from" | 191.647 (29 MB) | 2 | `links-P1889-1.json` e `-2` |
| P2440 | `item`, `transliteration` | "transliteration or transcription", como afirmação do item ou qualificador do rótulo nativo | 33.820 (4,5 MB) | 1 | `transliterations-1.json` |

Medições de 2026-10-12, com o índice do QLever atualizado continuamente sobre o dump de 2026-08-10. Total: 15 arquivos, cerca de 220 MB.

- **R2.3 Falha alta na paginação.** Cada página tem no máximo 200.000 linhas. A última página de uma consulta cheia (200.000 linhas) é `FormatError` que pede mais páginas. Uma página incompleta seguida de página com linhas é `FormatError` que pede `fetch --refresh`. As variáveis do cabeçalho (`head.vars`) diferentes das esperadas são `FormatError`.
- **R2.4 Valores das ligações.** `item` e `target` têm de ser URIs de entidade (`http://www.wikidata.org/entity/Q<n>`); outro valor de `item` é `FormatError`. Um `target` fora desse padrão (valor desconhecido do Wikidata, publicado como URI `/.well-known/genid/`) é pulado.
- **R2.5 Propriedade descartada.** A P5279, citada no roadmap como transliteração, é "hyphenation" (separação silábica) e não entra.

### R3. Observações

- **R3.1 Nome.** `name` é o valor do rótulo nativo (P1705), como publicado. Rótulo que não é literal (valor desconhecido, URI `genid`) é pulado. Itens sem P1705 ficam fora (6.569 prenomes e 43.195 sobrenomes, cerca de 5%).
- **R3.2 Filtro de rótulos.** Rótulo com algarismo de qualquer escrita (categoria Unicode `N*`) ou com um dos caracteres `( ) [ ] { } / \ , ; : _ | ? ! @ # " = < > * + & % $ ~ ^` e crase é pulado: são desambiguações (`Ritwik (given name)`), identificadores colados no lugar do nome (`Q34147`), lacunas (`Dau__tsch`), formas invertidas (`Felbert,von`) e duas grafias num rótulo (`Asil/Aseel`). Medido: 90 de 134.180 rótulos de prenome e 84 de 734.234 de sobrenome. O mesmo filtro vale para transliterações (2.130 de 33.820, quase todas com tom numérico, como `Lei⁵`).
- **R3.3 Tipo.** `kind` é `given` para a consulta de prenomes e `family` para a de sobrenomes. Item das duas classes (439 itens) gera linhas nos dois.
- **R3.4 Gênero pela classe.** O gênero vem da classe do item, alcançada por `P31/P279*`:

| Classe | Rótulo | `gender` |
|---|---|---|
| `Q12308941` | male given name | `M` |
| `Q11879590` | female given name | `F` |
| `Q3409032` | unisex given name | `F` e `M` (duas linhas) |
| `Q18972245`, `Q136439710` | masculine family name, masculine surname | `M` |
| `Q18972207`, `Q136439688` | feminine family name, feminine surname | `F` |
| nenhuma das acima | | vazio |

Uma classe de gênero fora da tabela é `FormatError`. Item que é ao mesmo tempo masculino e feminino gera as duas linhas.
- **R3.5 Gênero vazio cede ao informado.** Para cumprir a spec 002 (R1.5), se o mesmo `name_key` e `kind` tem linha com gênero e linha sem gênero (de itens diferentes, como `Letha` sem classe de gênero e `Letha` feminino), o adaptador omite a linha sem gênero. Ela só atestava o nome, que continua atestado pelas linhas com gênero. Medido: 1.800 nomes de prenome nessa situação.
- **R3.6 País, ano e contagem vazios.** `country` fica vazio em toda linha. A P495 (país de origem) aparece em 424 dos 135.792 itens de prenome e em 484 dos 723.194 de sobrenome, e a P27 (cidadania) é propriedade de pessoas; nenhuma das duas é confiável para associar um nome a um país. `year` e `count` ficam vazios.
- **R3.7 Escrita.** `script` continua sendo a escrita detectada no nome (spec 001, R1), conferida por `validate`. A P282 (sistema de escrita) não é usada: ela descreve o item, e não cada rótulo, e um item pode declarar várias (142.927 declarações em 135.792 itens de prenome).

### R4. Ligações entre variantes

- **R4.1 Contrato.** `namescommons.adapters` ganha `RawLink(relation, qid, name, kind, target_qid, target_name, target_kind)` e a função opcional `links(files) -> Iterator[RawLink]` no módulo do adaptador. `check_adapter` recusa `links` que não seja função.
- **R4.2 Tabela `variant_links`.** O pipeline transforma `RawLink` em linhas da tabela abaixo, com `name` e `target_name` normalizados como `name` da spec 001 (R1) e a caixa conforme `uniform_case` da fonte:

| Campo | Tipo | Regra |
|---|---|---|
| `source_id` | texto | `id` da fonte |
| `relation` | enum | ver R4.3 |
| `qid` | texto | item de origem, `Q<n>` |
| `name`, `name_key`, `kind` | texto | nome de origem, como em `Observation` |
| `target_qid` | texto | item de destino, `Q<n>`; igual a `qid` em `same_item` e `transliteration` |
| `target_name`, `target_name_key`, `target_kind` | texto | nome de destino |

- **R4.3 Relações.**

| `relation` | Origem no Wikidata | Destino |
|---|---|---|
| `same_item` | dois rótulos nativos do mesmo item com `name_key` diferentes | outro rótulo do item, mesmo `kind` |
| `said_to_be_the_same` | P460 | rótulos do item de destino |
| `family_name_identical` | P1533 | rótulos do item de destino |
| `other_gender` | P1560 (prenome) e P5278 (sobrenome) | rótulos do item de destino |
| `different_from` | P1889 | rótulos do item de destino |
| `transliteration` | P2440 | o texto da transliteração, com o `kind` da origem |

- **R4.4 Regras.** Cada rótulo de origem (com cada `kind` do item) é ligado a cada rótulo de destino. Ligação cujo destino não é item de nome com rótulo aceito por R3 é descartada. Linha cujo nome de origem e de destino têm o mesmo `name_key` e o mesmo `kind` é descartada. A direção é a publicada (A P460 B e B P460 A geram duas linhas). Linhas repetidas são emitidas uma vez, e a tabela é ordenada por todas as colunas.
- **R4.5 Validação.** `relation` fora de R4.3, `qid` ou `target_qid` fora de `Q<n>`, `kind` inválido, nome vazio, `name_key` diferente do derivado de `name` e `source_id` ausente de `sources.yaml` são recusados.
- **R4.6 Comandos.** `ingest --links ARQUIVO` grava a tabela das fontes selecionadas. `build --links ARQUIVO` a valida e a copia para a release. `run` grava `variant_links.parquet` na release quando alguma fonte selecionada tem `links`. A spec 005 é quem usa a tabela para `group_id`; esta spec não agrupa.
- **R4.7 Versão.** A release ganha um arquivo: `SCHEMA_VERSION` passa a `1.1.0` (spec 001, R5: acréscimo compatível).

### R5. Regra de `primary` (issue #3)

A exigência de exatamente uma fonte `primary: true` por par (`country`, `count_type`) da spec 001 (R2) passa a valer só para `births` e `population`. Em `attested`, `primary` não tem efeito (nenhuma contagem é escolhida) e não é conferido: duas fontes `attested` sem país, ambas com `primary: false`, são aceitas. A spec 001 recebe uma nota em R2 apontando para este requisito.

### R6. Amostras e testes

- `tests/fixtures/wikidata/` tem os 15 arquivos de R2.2, com menos de 20 KB no total. Cada arquivo é a resposta real do QLever à mesma consulta, com a mesma paginação, restrita a poucos itens (`VALUES ?item { ... }`), gerada por `tools/amostra_wikidata.py`; páginas além do fim são a resposta real vazia. Nas ligações ficam só as linhas cujo alvo também está na amostra, mais uma por propriedade com alvo de fora. A atribuição vai em `tests/fixtures/ATRIBUICAO.md`.
- Testes de `parse` e `links` sobre a amostra com registros esperados escritos à mão, de cada regra de R2.3 a R2.5, R3 e R4, e de formato inesperado.
- Os testes nunca acessam a rede (spec 002, R7).

### R7. CI

O passo da CI que roda as fontes de `sources.yaml` sobre as amostras passa a incluir o Wikidata e confere que a release tem `variant_links.parquet`.

### R8. Desempenho com os dados reais

`namescommons run --offline` só com o Wikidata, com os 15 arquivos reais no cache, fica dentro dos limites de R8 da spec 002 (menos de 10 minutos e menos de 4 GB). A medição vai para o pull request.

Medido num Apple M4 com 24 GB, em 2026-10-12: `fetch` baixou os 15 arquivos (216 MB) em 54 s. `run --offline` só com o Wikidata gerou 816.771 observações e 436.971 ligações em 60 s, com pico de 2,01 GB. Somado às 3 milhões de observações sintéticas de `tools/bench_pipeline.py` (spec 002, R8), num único `run --offline`, gerou 3.816.771 observações em 99 s, com pico de 3,43 GB: dentro do limite, com margem pequena (issue #31).

## Critérios de aceite

1. `sources.yaml` tem a fonte `wikidata` de R1, e `load_sources` a aceita.
2. `parse` sobre a amostra produz os registros esperados escritos à mão, inclusive `Andrea` com `F` e `M` de três itens (masculino, feminino e unissex), `Letha` sem a linha sem gênero, `李` sem gênero e rótulos de R3.2 pulados.
3. `links` sobre a amostra produz as ligações esperadas escritas à mão, inclusive `Иванов` `other_gender` `Иванова`, `Мария` `transliteration` `Mariya` e nenhuma ligação de um nome com ele mesmo.
4. Cada regra de R2.3 tem teste: última página cheia, página com linhas depois de página incompleta e cabeçalho inesperado.
5. `run --offline` sobre um cache com as amostras grava `variant_links.parquet`, e o `manifest.json` traz `schema_version` `1.1.0` e a contagem de linhas do arquivo.
6. Duas fontes `attested` sem país, ambas com `primary: false`, passam em `load_sources`; duas fontes `births` do mesmo país sem `primary` continuam recusadas.
7. A CI roda verde no pull request desta spec, com o passo de R7.
8. A medição de R8 é feita com os arquivos reais e a linha de tempo e memória vai para a descrição do pull request.
9. A issue #3 é fechada pelo pull request.

## Fora de escopo

- Agrupamento de variantes, `group_id` e transliteração para ASCII (spec 005).
- Ingestão do dump completo do Wikidata e um endpoint alternativo ao QLever: ficam numa issue.
- Rótulos de itens sem P1705 (rótulos por língua, inclusive `mul`) e lexemas do Wikidata.
- País de origem (P495) e língua do nome (P407) como atributos do nome.
- Publicação da tabela de ligações no README e no cartão do dataset (spec 006).
