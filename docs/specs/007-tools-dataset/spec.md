# 007. Adoção do kit de fontes do tools-dataset

Parte do [roadmap](../ROADMAP.md). Contrato adotado (dono: tools-dataset): [spec 004 do tools-dataset, o kit de fontes](https://github.com/BenchCommons/tools-dataset/blob/v0.1.0/docs/specs/004-source-toolkit/spec.md), na tag `v0.1.0`. Acompanhamento: [BenchCommons/tools-dataset#5](https://github.com/BenchCommons/tools-dataset/issues/5). Dependência: [ADR 0013](../../adr/0013-dependencia-do-tools-dataset.md). Licença dos dados: [ADR 0001](../../adr/0001-licenca-dos-dados.md), ampliado pelo [ADR 0004](../../adr/0004-licenca-statistics-canada.md).

Status: Implementada e mesclada (PR #41, 2026-10-12).

## Por quê

O cache de downloads, o leitor de planilhas, a base do adaptador, o registro de fontes e os auxiliares de arquivo do manifesto foram escritos aqui (specs 002, 003, 003b e 003e) e endurecidos em várias revisões. Eles não têm nada de nomes: qualquer repositório `dataset-*` precisa deles. O tools-dataset portou essa parte genérica, com os mesmos vetores de teste, para o pacote `benchcommons-tools-dataset` 0.1.0 (import `datasettool`). Enquanto este repositório mantiver as suas cópias, as duas versões vão divergir, e cada correção terá de ser feita duas vezes.

Esta spec troca as cópias locais pelo pacote e deixa aqui só o que é de nomes. O comportamento genérico (requisitos R2 a R6 da spec 004 do tools-dataset) não é redefinido aqui: vale o texto de lá, na tag fixada.

## Requisitos

### R1. Dependência

- **R1.1** `pyproject.toml` declara `benchcommons-tools-dataset==0.1.0` e fixa a origem em `[tool.uv.sources]` como git `https://github.com/BenchCommons/tools-dataset`, tag `v0.1.0` (ADR 0013, que segue o ADR 0004 do tools-dataset). O `uv.lock` versionado registra o commit da tag.
- **R1.2** `pyyaml` e `xlrd` deixam de ser dependências diretas, porque nenhum módulo de `src/namescommons` os importa mais; chegam fixados pelo kit. `pyarrow` e `pycountry` continuam. Nenhuma outra dependência de runtime entra.

### R2. O que sai deste repositório

- **R2.1** `src/namescommons/cache.py` é removido. Os downloads usam `datasettool.sources.cache.fetch_resource` (spec 004 do tools-dataset, R2).
- **R2.2** `src/namescommons/spreadsheet.py` é removido. O adaptador `es-ine-residentes` usa `datasettool.sources.spreadsheet` (R3 de lá), que já traz a correção do PR #39.
- **R2.3** A parte genérica de `src/namescommons/adapters/__init__.py` (erros, `Resource`, `SourceFiles`, `module_name`, conferência de URL e de nome de arquivo, `check_adapter`, `load_adapter`, `parse_count`, `parse_code`) é substituída por `datasettool.sources.adapters` (R4 de lá).
- **R2.4** A parte genérica de `src/namescommons/sources.py` (leitura do YAML, campos genéricos, formato do id, URL, licença, `retrieved`, `adapter`, ids repetidos, coleta de todos os erros) é substituída por `datasettool.sources.registry` (R5 de lá).
- **R2.5** O cálculo de SHA-256 e a contagem de registros CSV de `src/namescommons/manifest.py` são substituídos por `datasettool.files` (R6 de lá).
- **R2.6** Os testes deste repositório que só exercitam o comportamento portado são removidos depois que o kit, na tag fixada, passa nos equivalentes (mapa de portabilidade da seção 3 do [plano da spec 004 do tools-dataset](https://github.com/BenchCommons/tools-dataset/blob/v0.1.0/docs/specs/004-source-toolkit/plan.md)). A lista exata fica no plano desta spec e na descrição do PR.

### R3. O que fica neste repositório

- **R3.1 Adaptadores.** `namescommons.adapters` mantém `RawRecord`, `RawLink` e `DEFAULT_PACKAGE`, e reexporta do kit, como os mesmos objetos, `AdapterError`, `FormatError`, `Resource`, `SourceFiles`, `module_name`, `parse_count` e `parse_code`. Assim um `except FormatError` daqui pega também os erros do leitor de planilhas. `load_adapter(source_id, package=DEFAULT_PACKAGE)` e `check_adapter(mod, source_id)` chamam os do kit com `optional=("links",)`: o protocolo de nomes aceita a função opcional `links` (spec 004 daqui, R4.1). Os oito adaptadores de fontes oficiais e o do Wikidata não mudam de interface.
- **R3.2 Registro de fontes.** `namescommons.sources` declara o esquema do registro com a API do kit:
  - campos obrigatórios de nomes `country`, `count_type`, `primary` e `suppression`, e opcionais `uniform_case` e `strips_accents` (padrão `false`, spec 005, R6), cada um com a sua conferência;
  - licenças aceitas `ATTRIBUTION_ONLY_LICENSES` do kit mais `statcan-open-licence` (ADR 0004 daqui), com a política "ADR 0001" na mensagem de licença recusada;
  - a regra entre entradas de exatamente uma `primary` por par (país, `count_type`) com contagem, sem conferir `attested` (spec 004 daqui, R5);
  - uma fábrica que constrói o `Source` daqui, com os mesmos campos e padrões de hoje.
  `load_sources(path)`, `parse_sources(entradas)`, `is_country`, `COUNT_TYPES` e `Source` mantêm nome e assinatura. `SourceError` passa a ser o `RegistryError` do kit.
- **R3.3 Downloads.** O pipeline passa ao kit o `User-Agent` deste projeto, `namescommons/<versão> (+https://github.com/BenchCommons/dataset-names)`, igual byte a byte ao enviado antes. As opções de tentativas e espera passam com os nomes do kit (`attempts`, `backoff`, `sleep`).
- **R3.4 Manifesto.** `build_manifest` continua dono do formato da release, de `schema_version` e da lista `sources`; a lista `files` vem de `describe_files` do kit, com contador de registros para `.csv` (o do kit) e para `.parquet` (pelos metadados do Parquet).
- **R3.5 O resto.** Esquema e `Observation`, normalização, agregação, variantes, o pipeline de `RawRecord` e `RawLink` para `Observation` e `VariantLink`, a gravação em lotes, `sources.yaml` com os campos de nomes, as saídas e a CLI não mudam.

### R4. Comportamento preservado

- **R4.1** A CLI tem os mesmos comandos, opções, padrões e códigos de saída.
- **R4.2** Os dois passos offline da CI produzem saídas idênticas byte a byte às de `master` antes desta spec, e o mesmo vale para `namescommons run --offline` sobre um cache com os arquivos reais completos das fontes.
- **R4.3** Diferenças aceitas, e só elas:
  1. mensagens que vêm do kit ficam em inglês (cache, leitor de planilhas, contrato do adaptador, `parse_count`, `parse_code`, campos genéricos do registro); as mensagens de nomes continuam em português;
  2. a ordem das linhas numa mensagem do registro com vários erros: o kit confere `retrieved` e `adapter` antes dos campos de nomes (plano da spec 004 do tools-dataset, seção 2.4); o conjunto de mensagens é o mesmo;
  3. o cache recusa com `ValueError` id de fonte fora de `[a-z0-9]+(-[a-z0-9]+)*` e nome de arquivo inseguro antes de qualquer acesso; pela CLI isso não é alcançável, porque o registro e `check_adapter` já recusam os dois;
  4. o manifesto recusa arquivo de saída sem contador registrado em vez de contá-lo como CSV; as saídas daqui só têm `.csv` e `.parquet`;
  5. o cache recusa com `ValueError` uma entrada que resolve fora do diretório do cache, o que inclui um link simbólico para um arquivo ou diretório em outro lugar, mesmo com `--offline` e o arquivo presente; antes o arquivo era lido. Encontrado na implementação: `tools/bench_pipeline.py --wikidata` passa a pôr os arquivos no cache por link físico ou cópia, e a decisão sobre aceitar links simbólicos é do tools-dataset ([tools-dataset#9](https://github.com/BenchCommons/tools-dataset/issues/9)).

### R5. Testes

- **R5.1** Testes que conferem mensagens em português do código movido passam a conferir as mensagens em inglês do kit, sem mudar entradas nem valores esperados.
- **R5.2** Nenhum teste depende da ordem das linhas de uma mensagem do registro com vários erros.
- **R5.3** Testes novos cobrem a integração: os reexports de `namescommons.adapters` são os objetos do kit; `load_adapter` usa o pacote padrão e confere `links`; o `User-Agent` enviado pelo pipeline; os campos de nomes do registro, inclusive `strips_accents`; a versão e a tag fixadas em `pyproject.toml` e no `uv.lock`; e que `namescommons.cache` e `namescommons.spreadsheet` não existem mais.
- **R5.4** Os testes continuam sem rede: downloads só do servidor local de `tests/conftest.py`.

### R6. Documentação

`AGENTS.md` (stack e regra de atualização do kit), a seção de desenvolvimento do `README.md`, o `ROADMAP.md` (linha da spec e lista de ADRs) e o status do ADR 0005 apontam o kit e o ADR 0013.

## Critérios de aceite

1. `uv sync --locked` instala `benchcommons-tools-dataset` 0.1.0 a partir da tag `v0.1.0`, e o `uv.lock` registra o commit dela.
2. `src/namescommons/cache.py` e `src/namescommons/spreadsheet.py` não existem, e nenhum módulo de `src/namescommons` define `Resource`, `SourceFiles`, `parse_count`, `parse_code`, `check_adapter` (fora do invólucro de R3.1) ou lê YAML.
3. `uv run pytest -q` passa sem rede.
4. Os dois passos offline da CI passam, e `diff -r` entre as saídas deste branch e as de `master` sobre as mesmas fixtures não mostra diferença.
5. `namescommons run --offline` sobre o cache completo das fontes reais produz saídas idênticas às de `master`.
6. `tools/bench_pipeline.py` roda numa medição pequena sem erro.
7. A lista de testes e arquivos removidos está no plano e na descrição do PR.
8. Os itens da issue tools-dataset#5 cumpridos estão marcados, e o que ficar para depois virou issue.

## Fora de escopo

- Qualquer mudança no tools-dataset; uma correção no kit vira issue lá e chega aqui por versão nova (ADR 0013).
- Traduzir para o inglês as mensagens que são de nomes (registro, pipeline, adaptadores, CLI).
- O servidor de teste `LocalServer` de `tests/conftest.py`: o kit não o exporta, e ele continua aqui.
- A publicação (spec 006).
