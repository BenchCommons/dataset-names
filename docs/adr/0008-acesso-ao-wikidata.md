# 0008. Acesso ao Wikidata: consultas SPARQL no QLever, paginadas e guardadas no cache

## Status

Aceito (2026-10-12)

## Contexto

A spec 004 lê do Wikidata os itens de prenome (`Q202444` e subclasses) e de sobrenome (`Q101352` e subclasses), com rótulo nativo, classe e ligações entre itens. O contrato da spec 002 exige recursos com URL fixa (`Resource(url, filename)`), baixados uma vez para o cache e lidos depois com `--offline`.

Há três caminhos para os dados:

- **Wikidata Query Service (WDQS, `query.wikidata.org`).** Serviço oficial da Wikimedia, com limite de 60 s por consulta. Em 2026-10-12, contar os sobrenomes com rótulo nativo (`?i wdt:P31 wd:Q101352 . ?i wdt:P1705 ?l`) estourou o tempo duas vezes ("upstream request timeout"), e a consulta das subclasses de prenome com contagem também. Uma consulta por letra inicial ou por faixa de identificador continuaria perto do limite, e a lista de páginas mudaria conforme o Wikidata cresce.
- **Dump JSON completo (`dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.bz2`).** Reproduzível, mas tem mais de 100 GB compactado para extrair menos de 1 milhão de itens. Ler o dump inteiro excede o orçamento de tempo e disco da spec 002 (R8) e da CI.
- **QLever (`qlever.dev/api/wikidata`).** Motor SPARQL da Universidade de Freiburg sobre o dump completo do Wikidata, com atualização contínua (a página de estatísticas do índice informa "Complete Wikidata ... updated LIVE"). As mesmas consultas que estouraram no WDQS responderam em 1 a 12 s: 734.234 linhas de sobrenome em 11 s, 134.180 de prenome em 6 s. Os dados são os do Wikidata, sob CC0.

## Decisão

- Os recursos do adaptador `wikidata` são resultados de consultas SPARQL ao endpoint `https://qlever.dev/api/wikidata`, no formato SPARQL 1.1 Query Results JSON, pedidos por GET com a consulta inteira na URL e o formato no parâmetro `action=sparql_json`. O texto de cada consulta fica no módulo do adaptador.
- Cada consulta é ordenada (`ORDER BY`) e paginada com `LIMIT 200000 OFFSET k`. O número de páginas de cada consulta é fixo no módulo, com folga sobre o tamanho medido. Uma página de 200.000 linhas de JSON ocupa cerca de 28 MB e cerca de 500 MB depois de lida pelo `json` da biblioteca padrão; o arquivo inteiro de sobrenomes (104 MB) passava de 1,8 GB.
- A última página de uma consulta não pode vir cheia: se vier, o adaptador falha com a instrução de aumentar o número de páginas. Uma página incompleta seguida de página com linhas também é erro (o índice mudou entre os downloads), com a instrução de baixar de novo com `--refresh`.
- As consultas usam só SPARQL 1.1 padrão (sem o serviço de rótulos do WDQS), com `PREFIX` explícitos, para rodar em qualquer endpoint com o Wikidata completo.
- O `User-Agent` é o do pipeline (spec 002, R4), que identifica o projeto e o repositório como pede a política de User-Agent da Wikimedia. Os downloads são sequenciais.

## Consequências

- `fetch` baixa 15 arquivos (216 MB, em 54 s na medição de 2026-10-12), e `ingest --offline` lê o cache sem rede, como as outras fontes.
- O projeto depende de um serviço acadêmico sem acordo de nível de serviço. Se o QLever sair do ar, as consultas valem no WDQS só para as classes pequenas; a ingestão do dump completo fica registrada como alternativa na issue #29.
- O resultado reflete o índice do QLever no momento do download, que pode estar alguns dias atrás do Wikidata. O `.meta.json` do cache registra a data e a hora de cada página.
- Se o índice mudar entre o download de duas páginas da mesma consulta, linhas podem se repetir (inofensivo: o pipeline soma observações repetidas de fonte `attested` sem alterar nada) ou faltar na fronteira. A falta não é detectável pela página; o risco é pequeno porque as páginas de uma consulta são baixadas em segundos.
- Quando o Wikidata crescer além da folga, a ingestão falha alto e a correção é mudar um número no módulo.
