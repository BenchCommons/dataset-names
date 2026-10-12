# Roadmap: dataset mundial de nomes

Transforma as listas planas de `first_names.all.txt` e `last_names.all.txt` num dataset mundial de primeiros nomes e sobrenomes, aberto e reproduzível, com país, frequência, gênero e escrita, construído só a partir de fontes oficiais e do Wikidata.

Cada spec abaixo passa pelo próprio ciclo spec → plano → implementação → revisão.

| Ordem | Spec | Depende de | Entrega | Status |
|---|---|---|---|---|
| 1 | [`001-esquema`](001-esquema/spec.md) | nenhuma | Tabela canônica de observações, saídas agregadas, layout do repositório, versionamento | Mesclada |
| 2 | [`002-pipeline`](002-pipeline/spec.md) | 001 | Estrutura de adaptadores, cache de downloads, CLI, CI, testes | Mesclada |
| 3 | [`003-fontes-oficiais`](003-fontes-oficiais/spec.md) | 002 | Primeiro lote de institutos nacionais em texto (SSA, INSEE, CSO, Statistics Norway) e regras do contrato do adaptador da issue #8 | Mesclada |
| 3b | `003b-fontes-planilhas` | 003 | Leitor de XLS e XLSX e institutos que publicam em planilha (INE e outros) | Planejada |
| 3c | `003c-fontes-subnacionais` | 003b | Regra para fontes que cobrem parte de um país e seus adaptadores (ONS, Retraite Québec e outros) | Planejada |
| 3d | `003d-statistics-canada` | 003 | Decisão sobre a Statistics Canada Open Licence e o adaptador da tabela 17-10-0147-01 | Planejada |
| 4 | `004-wikidata` | 002 | Adaptador do Wikidata: nomes, gênero, escrita e ligações entre variantes | Planejada |
| 5 | `005-variantes` | 003, 004 | Transliteração para ASCII, agrupamento de variantes (`group_id`), deduplicação | Planejada |
| 6 | `006-publicacao` | 005 | Releases, manifesto, README, cartão do dataset, retirada do legado | Planejada |

Decisões transversais ficam em [`docs/adr/`](../adr/): [0001 licença dos dados](../adr/0001-licenca-dos-dados.md), [0002 valores suprimidos](../adr/0002-valores-suprimidos.md), [0003 nome do projeto e do pacote](../adr/0003-nome-do-projeto-e-do-pacote.md).
