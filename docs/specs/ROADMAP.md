# Roadmap: dataset mundial de nomes

Transforma as listas planas de `first_names.all.txt` e `last_names.all.txt` num dataset mundial de primeiros nomes e sobrenomes, aberto e reproduzível, com país, frequência, gênero e escrita, construído só a partir de fontes oficiais e do Wikidata.

Cada spec abaixo passa pelo próprio ciclo spec → plano → implementação → revisão.

| Ordem | Spec | Depende de | Entrega | Status |
|---|---|---|---|---|
| 1 | [`001-esquema`](001-esquema/spec.md) | nenhuma | Tabela canônica de observações, saídas agregadas, layout do repositório, versionamento | Mesclada |
| 2 | [`002-pipeline`](002-pipeline/spec.md) | 001 | Estrutura de adaptadores, cache de downloads, CLI, CI, testes | Mesclada |
| 3 | [`003-fontes-oficiais`](003-fontes-oficiais/spec.md) | 002 | Primeiro lote de institutos nacionais em texto (SSA, INSEE, CSO, Statistics Norway) e regras do contrato do adaptador da issue #8 | Mesclada |
| 3b | [`003b-fontes-planilhas`](003b-fontes-planilhas/spec.md) | 003 | Leitor de XLS e XLSX e institutos que publicam em planilha (INE e outros) | Mesclada |
| 3c | `003c-fontes-subnacionais` | 003b | Regra para fontes que cobrem parte de um país e seus adaptadores (ONS, Retraite Québec e outros) | Planejada |
| 3d | [`003d-statistics-canada`](003d-statistics-canada/spec.md) | 003 | Decisão sobre a Statistics Canada Open Licence e o adaptador da tabela 17-10-0147-01 | Mesclada |
| 3e | [`003e-nova-zelandia`](003e-nova-zelandia/spec.md) | 003 | Nomes de bebês do Department of Internal Affairs da Nova Zelândia e regra para nomes corrompidos na fonte | Em PR |
| 4 | [`004-wikidata`](004-wikidata/spec.md) | 002 | Adaptador do Wikidata: nomes, gênero, escrita, ligações entre variantes (`variant_links`) e regra de `primary` em `attested` (issue #3) | Em PR |
| 5 | [`005-variantes`](005-variantes/spec.md) | 003, 004 | Escrita, transliteração para ASCII, capitalização, forma de exibição, agrupamento de variantes (`group_id`) e deduplicação (issue #4), PR #38 | Em PR |
| 6 | `006-publicacao` | 005 | Releases, manifesto, README, cartão do dataset, retirada do legado | Planejada |

Decisões transversais ficam em [`docs/adr/`](../adr/): [0001 licença dos dados](../adr/0001-licenca-dos-dados.md), [0002 valores suprimidos](../adr/0002-valores-suprimidos.md), [0003 nome do projeto e do pacote](../adr/0003-nome-do-projeto-e-do-pacote.md), [0004 Statistics Canada Open Licence](../adr/0004-licenca-statistics-canada.md), [0005 leitor de planilhas](../adr/0005-leitor-de-planilhas.md), [0006 contagem de sobrenomes](../adr/0006-contagem-de-sobrenomes.md), [0007 nomes corrompidos na fonte](../adr/0007-nomes-corrompidos-na-fonte.md), [0008 acesso ao Wikidata](../adr/0008-acesso-ao-wikidata.md), [0009 ligações entre variantes](../adr/0009-ligacoes-entre-variantes.md), [0010 regras de agrupamento](../adr/0010-regras-de-agrupamento.md), [0011 correspondência sem acento](../adr/0011-correspondencia-sem-acento.md), [0012 transliteração para ASCII](../adr/0012-transliteracao-ascii.md).
