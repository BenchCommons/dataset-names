# 0008. Ligações entre variantes numa tabela própria, fora das observações

## Status

Aceito (2026-10-12)

## Contexto

A spec 005 vai preencher `group_id` (spec 001, R3.2) agrupando variantes de um nome: `Мария` e `Maria`, `Иванов` e `Ivanov`, `Ivanov` e `Ivanova`. O Wikidata publica essas relações entre itens: "said to be the same as" (P460), "family name identical to this given name" (P1533), versões para o outro gênero (P1560, P5278), "different from" (P1889) e transliterações (P2440).

A tabela de observações (spec 001, R1) descreve um nome atestado numa fonte; ela não tem lugar para uma relação entre dois nomes. Codificar a ligação num campo existente (por exemplo, `ascii`) mudaria o significado do campo, o que exige versão maior. Acrescentar colunas de ligação a `Observation` duplicaria cada nome por ligação e quebraria a chave de unicidade (R1.4).

## Decisão

- As ligações formam uma tabela própria, `variant_links`, com uma linha por par de nomes ligados e as colunas `source_id`, `relation`, `qid`, `name`, `name_key`, `kind`, `target_qid`, `target_name`, `target_name_key`, `target_kind`. O formato está na spec 004 (R4).
- O contrato do adaptador (spec 002, R1) ganha uma função opcional, `links(files) -> Iterator[RawLink]`. Só o adaptador do Wikidata a implementa por enquanto.
- `ingest` grava a tabela num arquivo à parte (`--links`), `build` a recebe (`--links`) e `run` a grava na release como `variant_links.parquet`.
- A tabela registra as relações como a fonte as publica. Agrupar, decidir quais relações juntam variantes e quais as separam é trabalho da spec 005.
- Acrescentar um arquivo à release é mudança compatível: `SCHEMA_VERSION` passa de `1.0.0` para `1.1.0` (versão menor, spec 001, R5).

## Consequências

- A tabela de observações e as saídas agregadas não mudam; quem lê só `given_names.csv` não percebe a novidade.
- A spec 005 lê as ligações de um único arquivo, com os nomes já normalizados (`name_key`), sem consultar o Wikidata de novo.
- Outras fontes com relações entre nomes (por exemplo, listas oficiais de grafias equivalentes) podem implementar `links` sem mudar o esquema.
- A release ganha um arquivo de cerca de um milhão de linhas, contado no `manifest.json`.
