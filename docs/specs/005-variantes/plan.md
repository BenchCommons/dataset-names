# 005. Variantes: plano de implementação

**Objetivo:** corrigir a escrita, a forma ASCII, a capitalização e a forma de exibição dos nomes (issue #4) e preencher `group_id` com um agrupamento determinístico sobre `variant_links` e as fontes que removem acentos.

**Arquitetura:** `normalize.py` concentra as regras por nome: `detect_script` (R1), `ascii_form` com as tabelas do ADR 0012 (R2) e `normalize_name` com partículas (R3). `sources.py` aceita `strips_accents` (R6). `aggregate.py` escolhe a forma de exibição por país e no índice (R4) e recebe as fontes e as ligações em `name_index`. O módulo novo `variants.py` tem a função pura `group_ids(keys, ascii, unaccented, links, kind)` que devolve o `group_id` de cada chave (R5), com união e busca sobre inteiros. `cli._build` passa fontes e ligações a `name_index` e monta a lista de fontes do manifesto com as das ligações (R7.4).

**Stack:** a mesma da spec 004, sem dependência nova.

**Spec:** [`spec.md`](spec.md). ADRs: [`0009`](../../adr/0009-ligacoes-entre-variantes.md), [`0010`](../../adr/0010-regras-de-agrupamento.md), [`0011`](../../adr/0011-correspondencia-sem-acento.md), [`0012`](../../adr/0012-transliteracao-ascii.md). Pendências herdadas: issues #4 e #31.

## Restrições globais

- Nenhuma dependência nova; tabelas de transliteração no código, com a fonte (ICAO Doc 9303, parte 3, seção 6) citada no módulo.
- Testes sem rede, com tabelas escritas à mão e as amostras existentes de `tests/fixtures/`; nenhuma amostra nova é necessária.
- O agrupamento não copia observações nem ligações: trabalha com índices inteiros sobre as chaves ordenadas do índice e percorre as ligações uma vez por `kind`.
- `SCHEMA_VERSION` passa a `1.2.0`.

## Decisões de implementação

| Decisão | Motivo |
|---|---|
| `group_ids` recebe listas paralelas (chaves ordenadas, `ascii`, marca de sem acento) e devolve uma lista | Função pura, testável com poucos nomes, e sem objeto por nó; o índice já tem as chaves ordenadas |
| União e busca com `list[int]` e compressão de caminho; proibições de `different_from` num `dict[int, set[int]]` só para as raízes que têm proibição | 191 mil P1889 viram 8 mil pares entre nós com observação; o resto do grafo não paga nada |
| A checagem de proibição percorre o menor conjunto e confere a raiz de cada nó | Mantém o custo proporcional às proibições, sem recalcular os conjuntos a cada junção |
| `group_id` é a primeira chave do grupo na lista ordenada | A lista já está em ordem de código Unicode; menor chave sem outra ordenação |
| A forma ASCII do nó é a de `ascii_form` sobre a forma exibida | Observações lidas de um Parquet antigo podem ter `ascii` da regra anterior; a forma exibida é a mesma que vai para o índice |
| `CountryRow` ganha o campo interno `published_case` (não sai no CSV) | O índice precisa saber se a forma exibida no país veio de fonte de caixa publicada (R4.3) sem reler as observações |
| `name_index(observations, country_rows, kind, sources=None, links=None)` | Chamadas existentes sem fontes e sem ligações continuam válidas: tratam toda fonte como de caixa publicada e sem remoção de acento, e não usam ligações |
| `validate` confere `ascii` só como ASCII sem maiúsculas | Recalcular `ascii_form` para 4 milhões de observações custaria tempo e memória; a coerência vem de `derive_name_fields` |
| Partículas só depois de espaço e fora da primeira palavra | Medido no INE: 1.449 `De`, 432 `La`, 121 `Del`; `Jia Le` mostra que artigo isolado também é nome |

## Foco de revisão

1. **Junções erradas por romanização ou acento ambíguos** (`Chen`, `Ines`) e por `other_gender` em prenomes (Task 6: `test_romanizacao_ambigua_nao_junta`, `test_sem_acento_ambiguo_nao_junta`, `test_other_gender_so_em_sobrenomes`).
2. **`different_from` precisa separar** mesmo quando outra ligação aproxima os nomes (Task 6: `test_different_from_separa`).
3. **Ordem das junções** não pode depender da ordem das ligações no arquivo (Task 6: `test_resultado_nao_depende_da_ordem`).
4. **Forma de exibição** sem soma de tipos e com caixa publicada primeiro (Task 5).
5. **Memória** do `run` com o lote real e com o sintético mais o Wikidata (Fechamento).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `src/namescommons/normalize.py`, `tests/test_normalize.py` | `detect_script` (R1) | 1 |
| `src/namescommons/normalize.py`, `src/namescommons/schema.py`, `tests/test_normalize.py`, `tests/test_schema.py` | `ascii_form` (R2) e validação de `ascii` (R2.5) | 2 |
| `src/namescommons/normalize.py`, `tests/test_normalize.py`, `tests/test_ci.py` | Partículas (R3) | 3 |
| `src/namescommons/sources.py`, `sources.yaml`, `tests/test_sources_extensoes.py`, `docs/specs/002-pipeline/spec.md` | `strips_accents` (R6, R7.3) | 4 |
| `src/namescommons/aggregate.py`, `tests/test_aggregate.py` | Forma de exibição (R4) | 5 |
| `src/namescommons/variants.py`, `tests/test_variants.py` | `group_ids` (R5) | 6 |
| `src/namescommons/aggregate.py`, `src/namescommons/cli.py`, `tests/test_cli_links.py` | `group_id` no índice, manifesto com as fontes das ligações (R5, R7.4) | 7 |
| `src/namescommons/schema.py`, `tests/test_manifest.py`, `.github/workflows/ci.yml`, `tests/test_ci.py`, `docs/specs/001-esquema/spec.md`, `docs/specs/002-pipeline/spec.md` | Versão (R8), notas de contrato (R7.1, R7.2) e CI (R10) | 8 |

## Cobertura da spec

| Requisito | Tarefa |
|---|---|
| R1 | 1 |
| R2 | 2 |
| R3 | 3 |
| R4 | 5 |
| R5 | 6, 7 |
| R6 | 4 |
| R7.1, R7.2 | 8 |
| R7.3 | 4 |
| R7.4 | 7 |
| R8 | 8 |
| R9 | Fechamento |
| R10 | 1 a 8 |
| Critério de aceite 1 | 1 |
| Critério 2 | 2 |
| Critério 3 | 3 |
| Critério 4 | 5 |
| Critério 5 | 6 |
| Critério 6 | 7, 8 |
| Critério 7 | 4 |
| Critérios 8, 9 | Fechamento |
