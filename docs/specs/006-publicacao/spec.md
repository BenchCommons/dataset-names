# 006. Publicação

Parte do [roadmap](../ROADMAP.md). Depende da [spec 005](../005-variantes/spec.md) e da [spec 007](../007-tools-dataset/spec.md). Esquema e versionamento: [spec 001](../001-esquema/spec.md) (R4, R5 e R6). Decisões: [ADR 0001](../../adr/0001-licenca-dos-dados.md) (licença dos dados), [ADR 0004](../../adr/0004-licenca-statistics-canada.md) (Statistics Canada), [ADR 0007](../../adr/0007-nomes-corrompidos-na-fonte.md) (nomes corrompidos), [ADR 0014](../../adr/0014-processo-de-release.md) (processo de release) e [ADR 0015](../../adr/0015-retirada-do-legado.md) (retirada do legado). Contrato de entradas de benchmark (dono: tools-dataset): [spec 001 do tools-dataset](https://github.com/BenchCommons/tools-dataset/blob/main/docs/specs/001-input-contract/spec.md). Issues: #5, #22 e #32.

Status: Em implementação.

## Por quê

O pipeline já gera as saídas da spec 001 num diretório, mas nada disso chega a um usuário. Faltam:

1. **Atribuições.** O ADR 0001 promete uma página de atribuições gerada de `sources.yaml`, e o ADR 0004 exige que o aviso fixo da Statistics Canada e o aviso de condições acompanhem o dataset (issue #22). Hoje os textos só existem em `sources.yaml` e no README.
2. **Licença do dataset.** `DATA_LICENSE` traz o texto da CC BY 4.0, mas nenhuma linha diz como atribuir o próprio dataset (issue #5).
3. **Descartes.** O adaptador da Nova Zelândia descarta nomes corrompidos na fonte (ADR 0007) e só avisa no log; o número some depois da execução (issue #32).
4. **Cartão do dataset.** Quem baixa uma release não tem onde ler campos, fontes, cobertura, supressão e limitações conhecidas.
5. **Release.** Não há procedimento nem workflow que transforme um cache de fontes numa GitHub Release com as saídas, o manifesto e as somas de verificação. Duas fontes (SSA e Nova Zelândia) bloqueiam o download automático e exigem o navegador, então o build da release não pode baixar tudo sozinho.
6. **Contrato de entradas.** O tools-dataset definiu o contrato de entradas de benchmark (spec 001 de lá), que espera `DATA_LICENSE`, `ATTRIBUTION.txt` e `SHA256SUMS` na release do dataset (R5, R6 e R9 de lá, e a seção 5 do plano de lá).
7. **Pendências da 001.** `.gitignore` com sobras e a decisão sobre `legacy/` (issue #5).

## Requisitos

### R1. Canal de descarte do adaptador

- **R1.1** O protocolo do adaptador de nomes ganha o tipo `RawDrop(name, count)`, em `namescommons.adapters`: um registro que a fonte publicou e que o adaptador descartou por regra documentada (hoje só a do ADR 0007). `parse` pode emitir `RawDrop` no mesmo iterador dos `RawRecord`. `count` é a contagem publicada da linha descartada, ou vazio se a fonte não traz contagem.
- **R1.2** O pipeline separa os `RawDrop` dos `RawRecord` e conta, por fonte, as linhas descartadas (número de `RawDrop`), os registros descartados (soma de `count`) e as formas distintas (`name`). A numeração `registro N` das mensagens continua contando só os `RawRecord`. `RawDrop` com `name` que não é texto ou `count` que não é inteiro não negativo é erro (`descarte N: ...`).
- **R1.3** O pipeline avisa os descartes no logger `namescommons.pipeline`, uma linha por fonte com descarte, com linhas, registros e formas. O adaptador `nz-dia-births` deixa de usar `logging` e emite `RawDrop`.
- **R1.4** `namescommons ingest` grava os descartes de todas as fontes ingeridas (inclusive zero) nos metadados chave-valor do `observations.parquet`, na chave `namescommons.dropped`, como JSON `{source_id: {"lines": n, "records": n}}`. `namescommons build` os lê de lá; `namescommons run` os passa em memória. Um `observations.parquet` sem a chave (gravado antes desta spec) é aceito, e os descartes ficam desconhecidos.

### R2. Manifesto

- **R2.1** Cada item de `sources` em `manifest.json` ganha `name` (de `sources.yaml`), `observations` (linhas de `observations.parquet` da fonte) e `dropped` (`{"lines": n, "records": n}`, ou `null` quando desconhecido, R1.4).
- **R2.2** O manifesto ganha `data_license` com o identificador SPDX da licença dos dados, `CC-BY-4.0`.
- **R2.3** `files` continua descrevendo só as tabelas de dados (observações, índices, `by_country/<CC>.csv` e `variant_links.parquet`), com o mesmo significado. Os arquivos de publicação de R5 não entram em `files`; entram em `SHA256SUMS`.
- **R2.4** Pela regra da spec 001 (R5), campo novo e arquivo novo na release não mudam o significado de nada: `SCHEMA_VERSION` passa a `1.3.0`.

### R3. Atribuições (`ATTRIBUTION.txt`)

- **R3.1** O build gera `ATTRIBUTION.txt`, em inglês, UTF-8 sem BOM, fim de linha LF, a partir de `sources.yaml`.
- **R3.2** Abre com a linha de atribuição do próprio dataset (R4.1) e segue com um bloco por fonte usada na release (fontes das observações e das ligações, como em spec 005, R7.4), em ordem de `id`: nome, `id`, URL, licença (nome e URL da licença) e o texto de `attribution` reproduzido sem nenhuma edição.
- **R3.3** Depois das fontes vem a seção de avisos (`Notices`): para cada licença usada que exige aviso além da atribuição, o texto do aviso sem tradução. Hoje só `statcan-open-licence`, com o aviso de condições do ADR 0004: "Data adapted from Statistics Canada remain subject to the Statistics Canada Open Licence (https://www.statcan.gc.ca/en/reference/licence); users must not use them to identify individuals, imply endorsement, misrepresent them, or use Statistics Canada or Government of Canada symbols."
- **R3.4** O nome e a URL de cada licença e os avisos ficam numa só tabela no código, com uma entrada para cada licença aceita (`LICENCAS_COMPATIVEIS`). Licença sem entrada nessa tabela faz o build falhar. O aviso de condições do README é igual, byte a byte, ao da tabela.
- **R3.5** Nenhum logotipo, brasão ou símbolo da Statistics Canada ou do Governo do Canadá aparece nas páginas do projeto nem nos arquivos da release (issue #22).

### R4. Licença dos dados

- **R4.1** A linha de atribuição do dataset é: `Names Commons Dataset, release <AAAA.MM[.N]>, BenchCommons (https://github.com/BenchCommons/dataset-names), licensed under CC BY 4.0. Upstream sources and notices: see ATTRIBUTION.txt.`
- **R4.2** `DATA_LICENSE` ganha, antes do texto da CC BY 4.0, um preâmbulo com o nome do dataset, a forma de atribuição de R4.1 (com `<release>` no lugar da versão), a remissão a `ATTRIBUTION.txt` e o aviso de que o código está sob Apache-2.0 e `legacy/` não é coberto. O texto da licença não muda.
- **R4.3** A release leva uma cópia de `DATA_LICENSE` idêntica byte a byte ao arquivo do repositório no commit do build. O caminho vem da opção `--data-license` de `build` e `run` (padrão: `DATA_LICENSE`); arquivo ausente faz o build falhar antes de gravar a saída.

### R5. Pacote da release

- **R5.1** Além das saídas da spec 001, o diretório da release passa a ter: `DATA_LICENSE` (R4.3), `ATTRIBUTION.txt` (R3), `DATASET_CARD.md` (R6), `by_country.zip` e `SHA256SUMS`. Tudo é gravado no mesmo diretório temporário e só então renomeado: falha em qualquer etapa não deixa saída parcial (spec 002).
- **R5.2** GitHub Releases não aceitam diretórios. `by_country.zip` traz `by_country/<CC>.csv` com os mesmos bytes do diretório, em ordem de nome, com data fixa (1980-01-01 00:00:00), permissões fixas e compressão `deflate`, de modo que o mesmo conteúdo gera o mesmo zip.
- **R5.3** `SHA256SUMS` segue o formato do GNU `sha256sum` (`<64 hex minúsculos>  <nome>`, um por linha, LF) e cobre todo arquivo regular do nível de cima do diretório da release, exceto ele mesmo, em ordem de nome. `sha256sum -c SHA256SUMS` passa no diretório da release e num diretório com os assets baixados da GitHub Release.
- **R5.4** Os assets publicados são exatamente os arquivos de R5.3 mais `SHA256SUMS`; o diretório `by_country/` não é publicado solto.
- **R5.5** O layout é compatível com a release descrita na seção 5 do plano da spec 001 do tools-dataset: `manifest.json`, as tabelas, `DATA_LICENSE`, `ATTRIBUTION.txt` (um bloco por fonte com nome, licença e texto exigido, e depois os avisos) e `SHA256SUMS` no nível de cima, e a tag da release em CalVer. Este repositório não gera entradas de benchmark (`*.input.json` e amostras); isso é a issue #24, sobre o contrato de lá.
- **R5.6** O build é determinístico: duas execuções sobre o mesmo cache, as mesmas fontes e o mesmo commit produzem `SHA256SUMS` idênticos.

### R6. Cartão do dataset (`DATASET_CARD.md`)

O build gera `DATASET_CARD.md`, em inglês (como o README), a partir do manifesto, de `sources.yaml` e das saídas da release, com:

- **R6.1 Resumo.** Release, `schema_version`, número de observações, de primeiros nomes, de sobrenomes, de países e de ligações entre variantes.
- **R6.2 Arquivos.** Cada arquivo da release com uma linha de descrição e, para as tabelas, o número de linhas do manifesto.
- **R6.3 Campos.** Os campos de `given_names` e `family_names`, de `by_country/<CC>.csv`, de `observations.parquet` e de `variant_links.parquet`, com tipo e significado, remetendo às specs 001, 004 e 005.
- **R6.4 Fontes.** Uma linha por fonte usada: nome, país, `count_type`, licença, limite de supressão, `retrieved`, observações e descartes (linhas e registros, ou "unknown").
- **R6.5 Cobertura.** Uma linha por país de `by_country`: primeiros nomes e sobrenomes (com o `count_type` de cada um) e o intervalo de anos.
- **R6.6 Supressão.** O ADR 0002 em linguagem de usuário: valores suprimidos são omitidos, o limite de cada fonte está na tabela de fontes, e somas de séries subestimam nomes raros.
- **R6.7 Limitações conhecidas.** No mínimo: fontes que publicam sem acento (`strips_accents`), listadas pelo nome; fontes de caixa uniforme recapitalizadas (`uniform_case`); total de linhas e registros descartados por nome corrompido (ADR 0007); `group_id` estável só dentro de uma release (spec 001, R3.2); o Wikidata como retrato do QLever na data de `retrieved` da fonte, não da data da release; e `female_share` como estimativa que combina tipos de contagem (spec 001, R3.2). Itens que dependem de uma fonte só aparecem se a fonte estiver na release.
- **R6.8 Licença e citação.** CC BY 4.0, a linha de R4.1, a remissão a `ATTRIBUTION.txt`, e, se a Statistics Canada estiver na release, o aviso (b) e o aviso de condições, sem tradução. Uma seção "How to cite" com a linha de R4.1 e a URL da release.

### R7. Workflow de release

- **R7.1 Comando local.** `tools/release.sh build <release> <cache> <saída>` roda `namescommons run --offline` sobre o cache, confere que a saída tem os arquivos de R5.1 e roda a verificação de `SHA256SUMS` (`sha256sum -c` ou `shasum -a 256 -c`). É o mesmo comando que o workflow usa, e qualquer pessoa o roda sem publicar nada.
- **R7.2 Gatilho.** `.github/workflows/release.yml` roda em push de tag CalVer (`AAAA.MM` ou `AAAA.MM.N`) e em `workflow_dispatch`. O disparo manual é sempre ensaio (R7.5).
- **R7.3 Cache.** Na tag, o cache vem do asset `source-cache.tar.gz` de um rascunho (draft) de release com o mesmo nome da tag, preparado pelo dono (ADR 0014). Sem rascunho, ou com a release já publicada, o workflow falha antes do build com mensagem que diz o que fazer.
- **R7.4 Envio.** Depois do build e da verificação, o workflow envia os assets de R5.4 ao rascunho sem sobrescrever asset existente, e só então remove `source-cache.tar.gz` do rascunho, para que os arquivos brutos das fontes nunca sejam publicados. O workflow nunca publica a release, nunca cria nem move tag e nunca envia a uma release publicada: publicar é ato do dono.
- **R7.5 Ensaio.** No `workflow_dispatch`, o cache são as amostras de `tests/fixtures/` com o `sources.yaml` real (como o segundo passo offline da CI), e a saída vai como artefato do workflow. Nenhum comando `gh` de release roda. A CI roda o mesmo ensaio em todo PR.
- **R7.6 Validação da entrada.** O nome da release é conferido contra CalVer antes de qualquer outro passo, e só passa ao shell por variável de ambiente.

### R8. Documentação

- **R8.1** README: layout da release (R5), seção "Releases" (como verificar, como citar, onde ficam o cartão e as atribuições) e o comando de ensaio local.
- **R8.2** `AGENTS.md`: o procedimento de release passo a passo (atualizar `retrieved`, conferir se a licença da Statistics Canada mudou desde a versão "Date modified: 2025-07-10" e, se mudou, reavaliar o ADR 0004, montar o cache, ensaiar, preparar o rascunho, criar e enviar a tag assinada, revisar e publicar).
- **R8.3** `ROADMAP.md`, lista de ADRs, e notas na spec 001 (R5 e R6) apontando esta spec.

### R9. `.gitignore`

Pendências da issue #5: tirar a linha em branco dupla, tirar `.venv/` da seção do mypy (a seção de virtualenv já ignora `.venv`) e permitir Parquet versionado em `tests/fixtures/` (`!tests/fixtures/**/*.parquet`), mantendo `*.parquet` ignorado no resto.

### R10. Legado

Decisão no [ADR 0015](../../adr/0015-retirada-do-legado.md): `legacy/` sai da árvore do repositório (continua no histórico do git). A remoção apaga arquivos versionados e por isso só acontece com aprovação explícita do dono sobre a lista exata dos arquivos; até lá `legacy/` fica como está, congelado, e o README continua dizendo que ele não faz parte do dataset.

## Critérios de aceite

1. Um adaptador que emite `RawDrop` tem os descartes contados por fonte (linhas, registros, formas), avisados no logger do pipeline, gravados no `observations.parquet` por `ingest` e lidos por `build`; o `nz-dia-births` não importa `logging`.
2. `manifest.json` tem `data_license`, e cada fonte tem `name`, `observations` e `dropped`; `SCHEMA_VERSION` é `1.3.0`; `files` não lista os arquivos de publicação.
3. `ATTRIBUTION.txt` contém, para cada fonte usada, o `attribution` de `sources.yaml` sem edição, e contém o aviso de condições da Statistics Canada se e somente se uma fonte `statcan-open-licence` estiver na release; licença sem entrada na tabela faz o build falhar; o aviso do README é igual ao da tabela.
4. `DATA_LICENSE` tem a linha de atribuição do dataset, e a cópia na release é idêntica ao arquivo do repositório.
5. `DATASET_CARD.md` tem as seções de R6, com os números do manifesto, as fontes sem acento, os descartes, a nota sobre `group_id`, a data do Wikidata e, com a Statistics Canada, os dois avisos.
6. `sha256sum -c SHA256SUMS` passa no diretório da release; `by_country.zip` tem os mesmos bytes de `by_country/`; dois builds iguais dão `SHA256SUMS` iguais.
7. `tools/release.sh build` roda localmente sobre as amostras das fontes e produz a release verificada; o passo de envio, testado com um `gh` falso, recusa release fora de CalVer, release publicada e ausência de rascunho, envia sem `--clobber` só os assets de R5.4 e remove `source-cache.tar.gz` depois do envio; nenhum teste chama o `gh` real.
8. O workflow de release não contém publicação de release nem push de tag; o disparo manual é ensaio; a CI roda o ensaio em todo PR.
9. `.gitignore` sem as sobras da issue #5, e um Parquet em `tests/fixtures/` não é ignorado.
10. A decisão sobre `legacy/` está no ADR 0015, e a lista exata dos arquivos a remover está na descrição do PR, aguardando aprovação.

## Fora de escopo

- Publicar uma release ou criar uma tag: a primeira release real precisa da aprovação explícita do dono e do download manual da SSA e da Nova Zelândia.
- Entradas de benchmark (`*.input.json`, amostras por tamanho): issue #24, sobre o contrato da spec 001 do tools-dataset.
- Versionar `data/by_country/*.csv` no git (spec 001, R4): depende da primeira release real e vira issue própria.
- Remover `legacy/` sem a aprovação do dono (R10).
- `CITATION.cff` e DOI (Zenodo).
