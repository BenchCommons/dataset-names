# 003d. Statistics Canada: plano de implementação

**Objetivo:** registrar a tabela 17-10-0147-01 da Statistics Canada e ingerir os primeiros nomes do Canadá por sexo e ano, com a licença aceita pelo ADR [`0004-licenca-statistics-canada.md`](../../adr/0004-licenca-statistics-canada.md).

**Arquitetura:** `statcan-open-licence` entra em `LICENCAS_COMPATIVEIS`. Um módulo novo, `src/namescommons/adapters/ca_statcan_births.py`, abre o membro `17100147.csv` do ZIP como fluxo (`zipfile.ZipFile.open` + `io.TextIOWrapper`), lê com `csv.reader`, localiza as colunas pelo cabeçalho e produz um `RawRecord` por célula `Frequency` nacional com valor. Nada muda no contrato da spec 003, no pipeline ou no esquema.

**Stack:** a mesma da spec 003, sem dependência nova.

**Spec:** [`spec.md`](spec.md). ADRs: [`0001`](../../adr/0001-licenca-dos-dados.md), [`0002`](../../adr/0002-valores-suprimidos.md), [`0004-licenca-statistics-canada.md`](../../adr/0004-licenca-statistics-canada.md). Issue: #15.

## Restrições globais

- Nenhuma dependência nova.
- Os testes nunca acessam a rede; a amostra fica em `tests/fixtures/ca-statcan-births/17100147-eng.zip`, menos de 20 KB, linhas copiadas do CSV real, membro com o mesmo nome.
- `parse` não guarda o CSV nem a lista de registros: é um gerador sobre o fluxo do ZIP.
- Valores suprimidos são omitidos (ADR 0002); marcador desconhecido é `FormatError`, nunca zero.
- Mensagem de formato: `FormatError` com `17100147.csv, linha N:` (N é a linha física do CSV, 1 para o cabeçalho), o valor recebido e o esperado.
- `SCHEMA_VERSION` continua `1.0.0`.

## Decisões de implementação

| Decisão | Motivo |
|---|---|
| `id` `ca-statcan-births` | Segue o padrão `<país>-<instituto>-<tipo>` das fontes da spec 003 |
| Identificador de licença `statcan-open-licence` | Não há identificador SPDX; minúsculas com hífen como `public-domain` |
| `csv.reader` com índices tirados do cabeçalho, e não `csv.DictReader` | 4,3 milhões de linhas: o `DictReader` monta um dicionário por linha; o índice fixo corta tempo sem perder a checagem de colunas |
| `GEO` diferente de `Canada` é pulado, sem erro | A spec pede só o nível nacional; uma geografia nova seria dado válido de outro nível, não formato quebrado. Ausência total de linhas nacionais é erro |
| `Grand Total` pulado em qualquer indicador | É agregado; hoje vazio, mas uma edição futura pode preenchê-lo |
| `SYMBOL` aceita `p` e `r` | A legenda da tabela os define como preliminar e revisado; o valor continua válido |
| `TERMINATED` e `DECIMALS` não são lidos | Não mudam o significado de uma contagem inteira de unidades |
| Medição de R6 com um `sources.yaml` temporário só com esta fonte | O ZIP da SSA não baixa automaticamente (spec 003, R4); a fonte é independente das demais e a soma com o lote da spec 003 (1,63 GB) continua abaixo de 4 GB |

## Foco de revisão

1. **Marcador novo** (`x`, `F`, `0s`) não pode virar zero nem sumir (Task 2: `test_status_ou_simbolo_desconhecido_falha`).
2. **Mudança de rótulo do indicador** não pode esvaziar a fonte em silêncio (Task 2: `test_indicador_desconhecido_falha` e `test_sem_linhas_nacionais_de_frequencia_falha`).
3. **`Grand Total`** não pode virar nome (Task 2: `test_grand_total_e_pulado_mesmo_com_valor`).
4. **Nome dos dois sexos** (`Riley`, `Noah`) gera `female_share` correto (Task 3: `test_passo_das_fontes_oficiais_roda_localmente`).
5. **Memória**: o gerador produz o primeiro registro sem ler o arquivo todo (Task 2: `test_parse_e_preguicoso`).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `src/namescommons/sources.py`, `tests/test_sources.py` | Licença aceita (R3) | 1 |
| `src/namescommons/adapters/ca_statcan_births.py`, `tests/test_ca_statcan_births.py`, `tests/fixtures/ca-statcan-births/17100147-eng.zip` | Adaptador e amostra (R1, R2, R4) | 2 |
| `sources.yaml`, `tests/fixtures/ATRIBUICAO.md`, `README.md` | Registro, atribuição, documentação (R1, R4, R7) | 2 |
| `.github/workflows/ci.yml`, `tests/test_ci.py` | Passo da CI com `CA` (R5) | 3 |

## Cobertura da spec

| Requisito | Tarefa |
|---|---|
| R1, R1.1 a R1.8 | 2 |
| R1.9 | Sem código: valores usados como publicados |
| R2 | 2 (`test_parse_e_preguicoso`, `test_membro_ausente_falha`, `test_coluna_ausente_falha`) |
| R3 | 1 |
| R4 | 2 e `tests/test_fontes_oficiais.py` |
| R5 | 3 |
| R6 | Fechamento (medição com o arquivo real) |
| R7 | 2 (README) e o commit da spec (roadmap) |
| Critério 1 | 1, 2 |
| Critérios 2 e 3 | 2 |
| Critério 4 | 3 |
| Critérios 5, 6 e 7 | Fechamento |
