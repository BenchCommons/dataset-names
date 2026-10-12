# 002. Pipeline de ingestão

Parte do [roadmap](../ROADMAP.md). Depende da [spec 001](../001-esquema/spec.md). Pendências herdadas: issue #2.

Status: Implementada e mesclada (PR #7, 2026-10-12).

## Por quê

A spec 001 definiu o esquema e a CLI que valida e agrega um `observations.parquet` já pronto, mas não há caminho reproduzível da fonte publicada até esse arquivo. As specs 003 (fontes oficiais) e 004 (Wikidata) vão escrever dezenas de adaptadores; sem um contrato comum, cada um baixaria, faria cache e trataria erros de um jeito, e as regras que a revisão da 001 deixou em aberto (vazio como `""`, total e divisão por gênero emitidos juntos, caixa decidida nome a nome) seriam resolvidas de formas diferentes em cada fonte.

Esta spec define o contrato do adaptador, o cache de downloads, os comandos que encadeiam download, ingestão e build, e a CI.

## Requisitos

### R1. Contrato do adaptador

Cada fonte de `sources.yaml` com adaptador tem um módulo `src/namescommons/adapters/<id_com_underscore>.py` que expõe:

| Nome | Tipo | Regra |
|---|---|---|
| `SOURCE_ID` | `str` | Igual ao `id` em `sources.yaml` |
| `RESOURCES` | lista de `Resource(url, filename)` | Arquivos que o adaptador precisa baixar |
| `parse(files: dict[str, Path]) -> Iterator[RawRecord]` | função | Lê os arquivos já baixados (chave = `filename`) e produz registros brutos, sem acessar a rede |

`RawRecord` tem `name`, `kind`, `country`, `gender`, `year` e `count` como a fonte publica. O pipeline, e não o adaptador, transforma `RawRecord` em `Observation`, aplicando:

- **R1.1** `""` e espaços em `country` e `gender` viram vazio (`None`).
- **R1.2** `count_type` e `source_id` vêm de `sources.yaml`, nunca do adaptador.
- **R1.3** A capitalização segue `uniform_case` da fonte (R2), e não a caixa de cada nome isolado.
- **R1.4** Registros repetidos pela chave de unicidade da 001 (R1.4) são somados.
- **R1.5** Uma fonte não pode emitir, para o mesmo (`name_key`, `kind`, `country`, `year`), linhas com `gender` informado e linhas sem `gender`. A violação falha a ingestão daquela fonte.

Nota (spec 004, R4.1): o módulo pode expor também a função opcional `links(files) -> Iterator[RawLink]`, com as ligações entre variantes; o contrato dela é da spec 004.

Nota: a spec 003 (R2.1) esclarece que o adaptador converte os valores; "como a fonte publica" vale só para o nome.

### R2. Extensões de `sources.yaml`

Campos novos, opcionais:

- `uniform_case` (booleano, padrão `false`): a fonte publica todos os nomes na mesma caixa e a capitalização por palavra da 001 se aplica a todos.
- `adapter` (booleano, padrão `true`): `false` registra uma fonte usada só manualmente.

Nota (spec 005, R6): `strips_accents` (booleano, padrão `false`) marca a fonte que publica os nomes sem acento por regra própria; ele decide a correspondência sem acento do agrupamento de variantes ([ADR 0011](../../adr/0011-correspondencia-sem-acento.md)).

### R3. Validação cruzada com a fonte

`validate` passa a recusar, além do que a 001 recusa:

- `count_type` da observação diferente do `count_type` da fonte.
- `country` da observação diferente do `country` da fonte, quando a fonte tem país.
- `year` fora de 1800 até o ano corrente mais um.
- `retrieved` em `sources.yaml` que não seja data pura (sem hora) e `url` sem esquema `http` ou `https`.

### R4. Cache de downloads

- Arquivos baixados ficam em `cache/<source_id>/<filename>`, fora do git.
- Ao lado de cada arquivo, `cache/<source_id>/<filename>.meta.json` guarda `url`, data e hora do download, SHA-256 e tamanho.
- Sem `--refresh`, um arquivo presente no cache não é baixado de novo.
- Com `--offline`, nenhum acesso à rede acontece e a falta de um arquivo é erro.
- Download com timeout, até três tentativas com espera crescente (não se repete resposta 4xx, exceto 408 e 429) e `User-Agent` que identifica o projeto e o repositório.
- Download parcial nunca fica no cache: grava em arquivo temporário e renomeia só ao concluir.

### R5. Comandos

| Comando | Faz |
|---|---|
| `namescommons fetch [ID ...] [--refresh]` | Baixa os recursos das fontes indicadas (todas com adaptador, se nenhuma) |
| `namescommons ingest [ID ...] --out observations.parquet [--offline]` | Roda `parse` sobre o cache, aplica R1, valida (001 e R3) e grava as observações |
| `namescommons validate` e `namescommons build` | Como na 001 |
| `namescommons run --out DIR --release AAAA.MM [--offline] [--refresh]` | `fetch`, `ingest` e `build` em sequência |

Uma fonte que falha em `fetch` ou `ingest` interrompe o comando com código 1 e mensagem que nomeia a fonte e a causa. Não há ingestão parcial silenciosa.

### R6. Reprodutibilidade

Com o mesmo cache, a mesma versão do pacote e o mesmo `sources.yaml`, dois `run --offline` produzem `by_country/*.csv`, `given_names.csv` e `family_names.csv` idênticos byte a byte, e Parquet com as mesmas linhas.

### R7. Testes e CI

- Cada adaptador tem uma amostra pequena do arquivo real da fonte em `tests/fixtures/<source_id>/` e testes que rodam `parse` sobre ela, sem rede.
- Os testes nunca acessam a rede. Downloads são testados com um servidor HTTP local.
- A CI (GitHub Actions) roda `uv sync`, `uv run pytest -q` e `namescommons run --offline` sobre um cache montado a partir das fixtures, em todo push e pull request.

### R8. Desempenho

`ingest` e `build` de 3 milhões de observações sintéticas terminam em menos de 10 minutos e usam menos de 4 GB de memória num notebook comum. A medição fica num script em `tools/` e não roda na CI.

### R9. Robustez herdada da revisão da 001 (issue #2)

- `source_id` desconhecido em agregação e manifesto gera erro do domínio, não `KeyError`.
- `write_observations` e `write_index` criam o diretório pai.
- A contagem de linhas do manifesto usa um leitor de CSV, não linhas físicas.
- Testes de rank denso com empate, duas fontes `primary`, `population` sem ano e round-trip Parquet com campos vazios.

## Critérios de aceite

1. Um adaptador de exemplo, escrito só para teste, com fixture própria, passa por `fetch` (servidor local), `ingest` e `build`, e o resultado bate com valores esperados escritos à mão.
2. Os casos de R1.1, R1.3 e R1.5 e cada recusa de R3 têm teste.
3. `fetch` sem `--refresh` não faz requisição quando o arquivo está no cache; `--offline` sem cache falha com mensagem; download interrompido não deixa arquivo no cache.
4. Dois `run --offline` seguidos geram saídas idênticas conforme R6.
5. A CI roda verde no pull request desta spec.
6. O script de R8 roda e registra tempo e memória para 3 milhões de observações dentro dos limites.
7. Cada item de R9 tem teste, e a issue #2 é fechada pelo pull request.

## Fora de escopo

- Adaptadores reais de fontes (specs 003 e 004).
- Transliteração e variantes (spec 005).
- Publicação de releases, README e cópia de `by_country/` para `data/` (spec 006).
- Paralelismo de downloads e agregação fora da memória: só se R8 falhar.
