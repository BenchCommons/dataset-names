# 001. Esquema do dataset: plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para executar [`tasks.md`](tasks.md) tarefa por tarefa. Os passos usam checkbox (`- [ ]`).

**Objetivo:** implementar o esquema canônico de observações, o registro de fontes, as saídas agregadas e o manifesto da spec 001, com uma CLI que valida e gera as saídas a partir de um `observations.parquet`.

**Arquitetura:** pacote Python `namesio` em `src/`, com um módulo por responsabilidade: normalização de nomes, registro de fontes, esquema e validação, agregação, entrada e saída, manifesto, CLI. As observações são `dataclass` imutáveis em memória; a agregação usa Python puro (dicionários), e o pyarrow só entra na leitura e na escrita de Parquet. Os adaptadores de fonte (specs 003 e 004) produzirão `list[Observation]` com `make_observation`.

**Stack:** Python 3.12 via `uv`, `pyarrow` (Parquet), `pyyaml` (`sources.yaml`), `pycountry` (ISO 3166-1), `pytest`, build com `hatchling`.

**Spec:** [`spec.md`](spec.md). ADR: [`0001-licenca-dos-dados.md`](../../adr/0001-licenca-dos-dados.md).

## Restrições globais

- Python `>=3.12`; dependências de runtime só `pyarrow>=17`, `pycountry>=24.6`, `pyyaml>=6.0`; dev só `pytest>=8`.
- Nome do pacote e do comando: `namesio` (provisório, R4).
- `SCHEMA_VERSION = "1.0.0"`.
- Licenças aceitas em `sources.yaml`: `public-domain`, `CC0-1.0`, `CC-BY-3.0`, `CC-BY-4.0`, `ODC-By-1.0`, `OGL-UK-3.0`, `etalab-2.0`.
- `count_type`: `births`, `population`, `attested`. `kind`: `given`, `family`. `gender`: `F`, `M` ou vazio.
- Release: `AAAA.MM` ou `AAAA.MM.N` (N ≥ 1).
- `female_share` no CSV com 6 casas decimais; células vazias para `None`.
- Commits assinados com GPG, autor `Matheus Breguêz <matbrgz@gmail.com>`, trailer `Co-Authored-By` no rodapé. Nunca `--no-gpg-sign`.

## Decisões de implementação

| Decisão | Motivo |
|---|---|
| Ordem de cada `by_country/<CC>.csv`: `kind`, linhas com rank antes das sem rank, `count_type`, `rank`, `name_key` | Diffs estáveis entre releases; os nomes mais frequentes aparecem primeiro |
| A fonte cuja contagem vale é escolhida por par (país da observação, `count_type`): única fonte, ou a única `primary` entre várias; caso contrário `AggregationError` | Fontes multinacionais (`country: null`) também disputam o par; a validação de `sources.yaml` não cobre esse caso |
| Um nome presente só numa fonte não primary fica `attested` naquele país | R3.3: as demais fontes só atestam, sem somar contagem |
| `CountryRow.female` é um campo interno que não sai no CSV | O índice mundial soma F e M dos países sem recalcular a partir de `female_share` arredondado |
| A forma de exibição considera todas as observações do nome, inclusive de fontes não primary | R3.2 fala em "observações", sem restringir à fonte oficial |
| Capitalização por palavra usa espaço, hífen e apóstrofo como separadores; partículas (`da`, `van`) também são capitalizadas | Regra simples e previsível; tratamento de partículas fica para a spec 005 |
| `.gitignore` perde `*out*` e `*.json` | Ignoravam `manifest.json`, fixtures e qualquer arquivo com "out" no nome |

## Foco de revisão

Casos que a spec implica e que um usuário vai encontrar. Cada um tem teste na tarefa dona do código.

1. **Nome publicado em NFD** (`Jose` + acento combinante) precisa ter a mesma chave que `José` (Task 2: `test_entrada_decomposta_vira_nfc`, `test_maiusculas_decompostas_tem_a_mesma_chave_que_a_forma_composta`).
2. **Nome só com espaços** precisa ser recusado na validação, e não virar uma linha vazia (Task 2: `test_nome_so_com_espacos_vira_vazio`; Task 4: `test_nome_so_com_espacos_e_recusado`).
3. **Mesmo nome como primeiro nome e sobrenome** (`Thomas`) não pode ser tratado como duplicata (Task 4: `test_mesma_chave_em_kind_diferente_nao_e_duplicata`).
4. **Mesmo país com `population` e `births` para o mesmo nome** usa `population`, e o rank não mistura os dois tipos (Task 5: `test_population_tem_precedencia_sobre_births_no_mesmo_pais`, `test_rank_separado_por_count_type`).
5. **I turco maiúsculo** (`İREM`) precisa capitalizar para `İrem` e manter a mesma chave (Task 2: `test_i_turco_maiusculo`).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `pyproject.toml`, `src/namesio/__init__.py`, `.gitignore`, `DATA_LICENSE`, `sources.yaml`, `legacy/` | Estrutura, licença dos dados, legado | 1 |
| `src/namesio/normalize.py` | `normalize_name`, `name_key`, `detect_script`, `ascii_form` | 2 |
| `src/namesio/sources.py` | `Source`, `load_sources`, `parse_sources`, `is_country`, `SourceError` | 3 |
| `src/namesio/schema.py` | `Observation`, `make_observation`, `validate`, `ValidationError`, `SCHEMA_VERSION` | 4 |
| `src/namesio/aggregate.py` | `by_country`, `name_index`, `display_name`, `CountryRow`, `CountryEntry`, `IndexRow`, `AggregationError` | 5 |
| `src/namesio/io.py`, `src/namesio/manifest.py` | Parquet e CSV; `build_manifest` | 6 |
| `src/namesio/cli.py` | `namesio validate` e `namesio build` | 7 |

## Cobertura da spec

| Requisito | Tarefa |
|---|---|
| R1 e R1.1 a R1.4 | 2, 4 |
| R2 | 3 |
| R3.1, R3.2, R3.3 | 5, 6 |
| R4 | 1, 7 |
| R5 | 6 |
| R6 | 1 |
| Critérios de aceite 1 e 2 | 3, 4 |
| Critérios 3, 4 e 5 | 5, 6 |
| Critério 6 | 1 |
