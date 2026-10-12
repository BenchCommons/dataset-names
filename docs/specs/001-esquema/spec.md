# 001. Esquema do dataset

Parte do [roadmap](../ROADMAP.md). Licença dos dados: [ADR 0001](../../adr/0001-licenca-dos-dados.md).

Status: Implementada e mesclada (PR #1, 2026-10-12).

## Por quê

O repositório publica duas listas planas (`first_names.all.txt`, 164.432 linhas; `last_names.all.txt`, 98.393 linhas), em minúsculas, sem país, gênero, frequência, escrita ou origem. O pipeline de geração (`generate/index.sh`) depende de diretórios que não existem no repositório, baixa de URLs de 2017 a 2020 e descarta qualquer nome com espaço, o que elimina sobrenomes compostos (`da Silva`, `van der Berg`).

Esta spec define o formato de dados que todas as specs seguintes produzem e consomem: a tabela canônica de observações, as saídas agregadas, o layout do repositório e o versionamento.

## Requisitos

### R1. Tabela canônica de observações

Cada adaptador de fonte produz linhas de observação: "a fonte X atesta o nome Y no país Z, com tal gênero e tal contagem". Todas as saídas são derivadas dessa tabela.

| Campo | Tipo | Obrigatório | Exemplo | Regra |
|---|---|---|---|---|
| `name` | texto | sim | `Álvaro`, `Мария`, `李` | Forma publicada pela fonte, em Unicode NFC, sem espaços nas pontas e com espaços internos colapsados. Caixa preservada; se a fonte publica tudo em maiúsculas ou minúsculas, aplica-se capitalização por palavra. |
| `name_key` | texto | sim | `álvaro` | `casefold()` de `name`. Identidade do nome; preserva acentos. |
| `ascii` | texto | sim | `alvaro` | Transliteração para ASCII em minúsculas. O método é definido na spec 005; até lá, remoção de diacríticos via decomposição NFD para escrita latina e campo vazio para as demais (pendências: issue #4). |
| `script` | código | sim | `Latn` | ISO 15924 predominante entre as letras do nome. `Zyyy` quando não há letra. |
| `kind` | enum | sim | `given` | `given` (primeiro nome) ou `family` (sobrenome). Um nome atestado nos dois papéis gera linhas separadas. |
| `country` | código | não | `BR` | ISO 3166-1 alfa-2. Vazio quando a fonte não associa país. |
| `gender` | enum | não | `F` | `F` ou `M`, somente quando a fonte informa. Nunca inferido. |
| `year` | inteiro | não | `2010` | Ano de referência da contagem. Vazio para fontes sem série temporal. |
| `count` | inteiro | não | `1532` | Contagem publicada. Vazio quando a fonte apenas atesta o nome. |
| `count_type` | enum | sim | `births` | O que a contagem mede: `births` (registros de nascimento no ano), `population` (pessoas vivas com o nome numa data) ou `attested` (sem contagem). |
| `source_id` | texto | sim | `us-ssa-births` | Chave de uma entrada de `sources.yaml`. |

Regras:

- **R1.1** Se `count` está vazio, `count_type` é `attested`, e vice-versa. Valores suprimidos pela fonte são omitidos, não emitidos como vazio: ver [ADR 0002](../../adr/0002-valores-suprimidos.md).
- **R1.2** Nomes com espaço, hífen ou apóstrofo são mantidos como publicados.
- **R1.3** Contagens de tipos diferentes nunca são somadas.
- **R1.4** A chave de unicidade de uma observação é (`name_key`, `kind`, `country`, `gender`, `year`, `source_id`). Duplicatas na mesma fonte são somadas pelo adaptador antes da emissão.

### R2. Registro de fontes (`sources.yaml`)

Cada fonte tem: `id`, `name`, `url`, `license`, `attribution` (texto exigido pela licença), `country`, `count_type`, `primary` (booleano, ver R3.3), `suppression` (limite abaixo do qual a fonte omite nomes, ex.: `5` na SSA; vazio se não houver) e `retrieved` (data da coleta). Fonte sem licença compatível com o ADR 0001 não pode ser registrada. Quando houver mais de uma fonte para o mesmo par (`country`, `count_type`), exatamente uma delas tem `primary: true`.

### R3. Saídas agregadas

**R3.1 `observations.parquet`.** A tabela de R1 completa. Somente Parquet.

**R3.2 `given_names` e `family_names`** (`.csv` e `.parquet`). Uma linha por `name_key`:

| Campo | Derivação |
|---|---|
| `name` | Forma de exibição mais frequente entre as observações (por soma de `count`; empate ou sem contagem: a mais atestada; persistindo o empate, ordem lexicográfica) |
| `name_key`, `ascii`, `script` | Como em R1 |
| `country_count` | Número de países distintos que atestam o nome |
| `countries` | Lista de `{country, count, count_type, rank}`, uma por país, calculada como em R3.3. JSON no CSV, lista de structs no Parquet |
| `female_share` | F ÷ (F + M), somando, em todos os países, só as observações escolhidas em R3.3 que têm `count` e `gender`. Vazio sem base. É uma estimativa ponderada que combina países com tipos de contagem diferentes, por isso nunca é usada como contagem |
| `gender_basis` | F + M usados no cálculo de `female_share` |
| `group_id` | Grupo de variantes, preenchido pela spec 005. Vazio até lá |
| `sources` | Lista ordenada de `source_id` que atestam o nome |

**R3.3 `by_country/<CC>.csv`.** Uma linha por (`name_key`, `kind`) do país, com `name`, `ascii`, `script`, `count`, `count_type`, `rank`, `female_share`, `gender_basis`, `first_year`, `last_year`. Agregação:

- `births`: soma de todos os anos disponíveis; `first_year` e `last_year` delimitam a série.
- `population`: usa a edição mais recente da fonte no país (o maior `year` entre as observações da fonte); nomes ausentes dessa edição não usam edições antigas; `first_year` = `last_year` = ano da edição.
- Mais de uma fonte com o mesmo `count_type` no país: usa só a fonte `primary: true`. As demais apenas atestam (entram em `sources`), sem somar contagem.
- O mesmo nome com contagens de tipos diferentes no país: vale `population`; sem ela, `births`. `attested` só quando não há contagem.
- País só com `attested`: `count` e `rank` vazios.
- `rank` é denso, por `kind` e `count_type`, em ordem decrescente de `count`.

### R4. Layout do repositório

```
README.md                 inglês
LICENSE                   Apache-2.0 (código)
DATA_LICENSE              CC BY 4.0 (dados)
sources.yaml
pyproject.toml
src/<pacote>/schema.py    esquema de R1 e validação
src/<pacote>/adapters/    um módulo por fonte
src/<pacote>/aggregate.py saídas de R3
src/<pacote>/cli.py
tests/
data/by_country/*.csv     versionado no git
legacy/                   listas atuais, congeladas
docs/specs/, docs/adr/
```

`observations.parquet`, `given_names.*` e `family_names.*` são publicados nas GitHub Releases e não entram no git. O nome do pacote é `namescommons`.

### R5. Versionamento

- Releases em CalVer (`AAAA.MM`, com sufixo `.N` para mais de uma no mês).
- Cada release inclui `manifest.json` com `schema_version` (semver), fontes usadas com `retrieved`, número de linhas por arquivo e SHA-256 de cada arquivo.
- Remover ou renomear campo, ou mudar o significado de um valor, incrementa a versão maior de `schema_version`.

### R6. Legado

`first_names.all.txt`, `last_names.all.txt` e `generate/` vão para `legacy/` sem alteração de conteúdo e não são ingeridos no dataset novo (ADR 0001). A retirada é decidida na spec 006.

## Critérios de aceite

1. `schema.py` valida uma tabela de observações e rejeita: campo obrigatório vazio, `country` fora da ISO 3166-1, `gender` fora de `F`/`M`, `count` negativo, violação de R1.1, `source_id` ausente de `sources.yaml` e duplicata pela chave de R1.4.
2. `sources.yaml` é validado contra os campos de R2, e o build falha com licença fora da lista do ADR 0001.
3. Com uma tabela de observações de teste, cobrindo duas fontes `births` no mesmo país (uma `primary`), uma fonte `population`, uma fonte `attested`, nomes em escrita latina, cirílica e chinesa, e um nome com espaço, as saídas de R3 batem com valores esperados escritos à mão.
4. `female_share` fica vazio quando nenhuma observação do nome tem contagem e gênero.
5. Nenhum `count` ou `rank` soma contagens de `count_type` diferentes.
6. Os arquivos legados estão em `legacy/` com conteúdo idêntico ao do commit anterior.

## Fora de escopo

- Adaptadores de fontes (specs 003 e 004).
- Método de transliteração e agrupamento de variantes (spec 005).
- Publicação, README final e cartão do dataset (spec 006).
- Inferência de gênero, origem étnica ou nacionalidade a partir do nome.
- Ranking mundial único ou probabilidade de gênero global sem país.
