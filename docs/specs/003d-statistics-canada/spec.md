# 003d. Statistics Canada: primeiros nomes no nascimento

Parte do [roadmap](../ROADMAP.md). Depende da [spec 003](../003-fontes-oficiais/spec.md). Licença: [ADR 0001](../../adr/0001-licenca-dos-dados.md), ampliado por [`0004-licenca-statistics-canada.md`](../../adr/0004-licenca-statistics-canada.md). Valores suprimidos: [ADR 0002](../../adr/0002-valores-suprimidos.md). Issue: #15.

Status: Em implementação.

## Por quê

A spec 003 avaliou a tabela 17-10-0147-01 da Statistics Canada e a deixou fora do primeiro lote só porque a Statistics Canada Open Licence não estava na lista do ADR 0001 (spec 003, R7). O ADR [`0004-licenca-statistics-canada.md`](../../adr/0004-licenca-statistics-canada.md) aceita essa licença. Esta spec registra a fonte e escreve o adaptador, e o Canadá entra no dataset com primeiros nomes por sexo e ano.

O arquivo é o maior lido até agora (CSV de 582 MB dentro de um ZIP de 42 MB, 4,3 milhões de linhas). O adaptador precisa ler em fluxo, sem carregar o CSV na memória, e a execução precisa caber nos limites de R8 da spec 002.

## Requisitos

### R1. Fonte

Uma entrada em `sources.yaml` e um adaptador em `src/namescommons/adapters/ca_statcan_births.py`. Números medidos no arquivo real baixado em 2026-10-12.

| Campo | Valor |
|---|---|
| `id` | `ca-statcan-births` |
| Instituto e produto | Statistics Canada, tabela 17-10-0147-01, "First names at birth by sex at birth, selected indicators" (pesquisa 3231, Vital Statistics, Birth Database) |
| Página | https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1710014701 (DOI https://doi.org/10.25318/1710014701-eng, usado em `url` de `sources.yaml`) |
| Recurso | https://www150.statcan.gc.ca/n1/tbl/csv/17100147-eng.zip, gravado como `17100147-eng.zip` |
| Formato | ZIP com `17100147.csv` (dados) e `17100147_MetaData.csv` (metadados). CSV UTF-8 com BOM, separado por vírgula, todos os campos entre aspas, fim de linha LF, 17 colunas: `REF_DATE`, `GEO`, `DGUID`, `Sex at birth`, `First name at birth`, `Indicator`, `UOM`, `UOM_ID`, `SCALAR_FACTOR`, `SCALAR_ID`, `VECTOR`, `COORDINATE`, `VALUE`, `STATUS`, `SYMBOL`, `TERMINATED`, `DECIMALS` |
| Tamanho | 41.740.086 bytes compactado; 581.606.635 bytes de CSV |
| Linhas | 4.302.270: 35 anos x 2 sexos x 20.487 membros de nome (inclusive `Grand Total`) x 3 indicadores (`Frequency`, `Rank`, `Proportion (%)`) |
| Contagens | 218.198 células `Frequency` com valor; 1.215.892 com `VALUE` vazio e `STATUS` `..` |
| País, tipo, anos | CA, `given`, `births`, 1991 a 2025 |
| `GEO` | só `Canada` (DGUID `2021A000011124`) |
| Supressão (`suppression`) | 5. Nota 7 da tabela: nomes com frequência menor que 5 são excluídos; nota 6: `..` marca nome ausente no ano ou sexo, ou suprimido |
| Caixa | maiúsculas sem acento (nota 7: letra acentuada é trocada pela letra sem acento); `uniform_case: true` |
| Licença | `statcan-open-licence`, https://www.statcan.gc.ca/en/reference/licence (data de modificação 2025-07-10), aceita pelo ADR [`0004-licenca-statistics-canada.md`](../../adr/0004-licenca-statistics-canada.md) |
| Atribuição | "Adapted from Statistics Canada, First names at birth by sex at birth, selected indicators (table 17-10-0147-01), 1991 to 2025. This does not constitute an endorsement by Statistics Canada of this product." |
| `primary` | `true`: nenhuma outra fonte tem o par (`CA`, `births`) |

Particularidades que o adaptador trata:

- **R1.1 Só a frequência.** Só linhas com `Indicator` igual a `Frequency` geram registro. `Rank` e `Proportion (%)` são ignorados. Um indicador fora desses três é `FormatError`, para que uma mudança de rótulo não esvazie a fonte em silêncio.
- **R1.2 Só o nível nacional.** Só linhas com `GEO` igual a `Canada` geram registro; outra geografia é pulada. Se o arquivo não tiver nenhuma linha `Frequency` nacional, é `FormatError`.
- **R1.3 Sexo.** `Male` é `M` e `Female` é `F`, por `parse_code`; outro valor é `FormatError`.
- **R1.4 Agregado.** A linha `Grand Total` é um agregado, não um nome, e é pulada em qualquer indicador. No arquivo de 2026-10-12 todas as suas células são `..`.
- **R1.5 Valores suprimidos** (ADR 0002). `VALUE` vazio com `STATUS` `..` é omitido. `VALUE` inteiro exige `STATUS` vazio. Qualquer outra combinação (`STATUS` `x`, `F`, `E`, `<LOD` ou `0s` da legenda de símbolos da tabela, ou valor vazio sem `..`) é `FormatError` com `linha N` do CSV.
- **R1.6 Símbolos de revisão.** `SYMBOL` vazio, `p` (preliminar) ou `r` (revisado) é aceito, porque não muda o valor; a nota 2 diz que o ano mais recente é preliminar. Outro símbolo é `FormatError`.
- **R1.7 Escala.** Linha `Frequency` com `SCALAR_ID` diferente de `0` (unidades) é `FormatError`, para que uma contagem em milhares não entre como unidades.
- **R1.8 Ano.** `REF_DATE` é o ano, lido por `parse_count` com `field="REF_DATE"`.
- **R1.9 Contagens do Québec.** A nota 3 diz que, para o Québec, frequências de 1 a 4 da Retraite Québec foram trocadas por um número aleatório de 1 a 4 e somadas às das outras províncias. O adaptador usa os valores como publicados, como faz com o arredondamento do INSEE (spec 003, R1.2).
- **R1.10 Escopo da validação.** `STATUS`, `SYMBOL`, sexo, escala e ano são conferidos só nas linhas que podem virar registro: `Frequency`, `GEO` `Canada`, nome diferente de `Grand Total`. Marcadores em linhas descartadas (`Rank`, `Proportion (%)`, outra geografia, o agregado) não são conferidos de propósito, porque nenhum valor delas entra no dataset. O indicador é conferido em todas as linhas (R1.1).

### R2. Leitura em fluxo

`parse` lê o membro `17100147.csv` direto do ZIP, linha a linha (`zipfile` e `csv` da biblioteca padrão), e produz cada registro sem guardar o CSV nem a lista de registros. O membro de metadados é ignorado. Membro de dados ausente é `FormatError` com a lista de membros. Coluna exigida ausente no cabeçalho é `FormatError` com o cabeçalho lido.

### R3. Licença

`statcan-open-licence` entra em `LICENCAS_COMPATIVEIS` de `src/namescommons/sources.py`, como decide o ADR [`0004-licenca-statistics-canada.md`](../../adr/0004-licenca-statistics-canada.md). `load_sources` aceita uma fonte com essa licença.

### R4. Amostra e testes

- `tests/fixtures/ca-statcan-births/17100147-eng.zip`: ZIP remontado com o cabeçalho e 20 linhas copiadas sem alteração de `17100147.csv`, no membro de mesmo nome, menos de 20 KB. As linhas cobrem: nome com apóstrofo (`D'ARCY`), com hífen (`JEAN-PHILIPPE`, `MARIE-EVE`), nome dos dois sexos (`RILEY`, `NOAH`), célula `..`, linhas `Rank` e `Proportion (%)`, `Grand Total`, e os anos 1991 e 2025.
- `tests/fixtures/ATRIBUICAO.md` ganha a linha da fonte, com o aviso de atribuição.
- Teste de `parse` sobre a amostra com os registros esperados escritos à mão; teste de cada particularidade de R1.1 a R1.8; teste de formato inesperado (`FormatError`); teste de que `parse` é um gerador que não lê o arquivo inteiro antes do primeiro registro.
- Os testes de `tests/test_fontes_oficiais.py` (amostra, atribuição, `fetch` contra o servidor local e `ingest --offline`) passam a incluir a fonte, sem mudança no teste.
- Os testes nunca acessam a rede.

### R5. CI

O passo da CI que roda `namescommons run --offline` sobre as amostras das fontes oficiais passa a conferir também `by_country/CA.csv`.

### R6. Desempenho com o arquivo real

Com o ZIP real no cache, `namescommons run --offline` só com esta fonte termina dentro dos limites de R8 da spec 002 (menos de 10 minutos e menos de 4 GB). O tempo, o pico de memória e a máquina vão para a descrição do pull request e para esta spec.

Medido num Apple M4 com 24 GB, com o ZIP baixado em 2026-10-12: `run --offline` em 11,4 s, pico de memória (RSS máximo) de 197 MB, 218.198 observações e 18.999 nomes em `by_country/CA.csv`. Somado ao lote da spec 003 (68 s e 1,63 GB, R6 daquela spec), o total continua dentro dos limites.

### R7. Documentação

O README lista a fonte na tabela de fontes. O roadmap marca a linha 3d e lista o ADR novo.

## Critérios de aceite

1. `sources.yaml` tem `ca-statcan-births` com `license: statcan-open-licence` e o aviso de atribuição de R1, e `load_sources` o aceita; um teste mostra que `statcan-open-licence` é aceita e que licenças recusadas pelo ADR 0001 continuam recusadas.
2. O adaptador passa no teste de `parse` sobre a amostra real com os registros escritos à mão, e cada particularidade de R1.1 a R1.8 tem teste.
3. Um `STATUS` ou `SYMBOL` desconhecido, um indicador desconhecido, uma escala diferente de unidades e um sexo desconhecido falham com `FormatError` e a linha do CSV.
4. `namescommons run --offline` sobre o cache montado com `tests/fixtures/` gera `by_country/CA.csv` igual a valores escritos à mão, com `Riley` e `Noah` com `female_share` dos dois sexos.
5. A CI roda verde no pull request, com o passo de R5 conferindo `CA`.
6. A medição de R6 com o arquivo real fica dentro dos limites, e a linha de tempo e memória está na descrição do pull request.
7. A issue #15 é fechada pelo pull request.

## Fora de escopo

- Tabelas provinciais e outras tabelas da Statistics Canada; a regra para fontes subnacionais (como a Retraite Québec, que também é fonte desta tabela) é da spec `003c-fontes-subnacionais`.
- Restaurar acentos dos nomes (`MARIE-EVE` em vez de `Marie-Ève`): transliteração e variantes são da spec 005.
- `Rank` e `Proportion (%)`: o pipeline calcula rank e proporções a partir das contagens (spec 001).
- Página de atribuições e cartão do dataset com o aviso da Statistics Canada: spec 006.
- Atualização automática de edições: a URL do recurso é fixa e o arquivo é trocado a cada `--refresh`.
