# Roadmap: dataset mundial de nomes

Transforma as listas planas de `first_names.all.txt` e `last_names.all.txt` num dataset mundial de primeiros nomes e sobrenomes, aberto e reproduzível, com país, frequência, gênero e escrita, construído só a partir de fontes oficiais e do Wikidata.

Cada spec abaixo passa pelo próprio ciclo spec → plano → implementação → revisão.

| Ordem | Spec | Depende de | Entrega |
|---|---|---|---|
| 1 | [`001-esquema`](001-esquema/spec.md) | nenhuma | Tabela canônica de observações, saídas agregadas, layout do repositório, versionamento |
| 2 | `002-pipeline` | 001 | Estrutura de adaptadores, cache de downloads, CLI, CI, testes |
| 3 | `003-fontes-oficiais` | 002 | Adaptadores de institutos de estatística (SSA, ONS, INSEE, INE, IBGE, Statistics Canada e outros) |
| 4 | `004-wikidata` | 002 | Adaptador do Wikidata: nomes, gênero, escrita e ligações entre variantes |
| 5 | `005-variantes` | 003, 004 | Transliteração para ASCII, agrupamento de variantes (`group_id`), deduplicação |
| 6 | `006-publicacao` | 005 | Releases, manifesto, README, cartão do dataset, retirada do legado |

Decisões transversais ficam em [`docs/adr/`](../adr/).
