# 006. Publicação: plano de implementação

**Objetivo:** fazer o build gerar uma release publicável (atribuições, licença, cartão, zip por país e somas de verificação), registrar os descartes por fonte no manifesto e criar o workflow que monta a release a partir do cache sem publicá-la.

**Arquitetura:** o canal de descarte é um tipo novo do protocolo do adaptador (`RawDrop`), contado pelo pipeline e guardado nos metadados do `observations.parquet`. Um módulo novo, `namescommons.publication`, gera os textos e arquivos de publicação (tabela de licenças e avisos, `ATTRIBUTION.txt`, `DATASET_CARD.md`, `by_country.zip`, `SHA256SUMS`) a partir do manifesto, de `sources.yaml` e das linhas por país. `cli._build` chama esse módulo dentro do mesmo diretório temporário de hoje. A release no GitHub é montada por `tools/release.sh`, chamado por `.github/workflows/release.yml` e pela CI.

**Stack:** a mesma; nenhuma dependência nova (`zipfile`, `hashlib` e `json` da biblioteca padrão; `datasettool.files.sha256_file` do kit).

**Spec:** [`spec.md`](spec.md). ADRs: [0014](../../adr/0014-processo-de-release.md), [0015](../../adr/0015-legado-congelado.md).

## Restrições globais

- As saídas da spec 001 não mudam de conteúdo, exceto `manifest.json` (R2) e os metadados chave-valor do `observations.parquet` (R1.4).
- `SCHEMA_VERSION = "1.3.0"`.
- Textos da release (`ATTRIBUTION.txt`, `DATASET_CARD.md`, preâmbulo de `DATA_LICENSE`) em inglês, como o README; mensagens da CLI e do script em português.
- Nenhum teste chama o `gh` real nem a rede; o script de release é testado com um `gh` falso no `PATH`.
- Nenhuma tag, release ou rascunho é criado no GitHub por esta spec.
- `legacy/` não é tocado: fica congelado (R10, ADR 0015).

## Decisões de implementação

| Decisão | Motivo | Custo se estiver errada |
|---|---|---|
| Descarte como `RawDrop` no iterador de `parse`, e não uma função extra do módulo | O adaptador decide o descarte linha a linha, no mesmo laço; não precisa de estado global nem de segunda leitura do arquivo | Se um adaptador futuro precisar descartar após ler tudo, emite os `RawDrop` no fim; nada muda no pipeline |
| Descartes do `ingest` para o `build` nos metadados do Parquet (`namescommons.dropped`) | `ingest` e `build` são comandos separados; um arquivo lateral se perderia ao mover o Parquet | Metadados chave-valor não aparecem em leitores que só mostram colunas; o manifesto e o cartão os expõem |
| `dropped: null` quando o Parquet não traz a chave | Zero seria afirmar que não houve descarte | Um consumidor precisa tratar `null` |
| `files` do manifesto só com as tabelas | O significado de `files` fica igual (R2.3) e o cartão, gerado depois do manifesto, não cria dependência circular | Os arquivos de publicação só têm soma em `SHA256SUMS` |
| `by_country.zip` além do diretório `by_country/` | Releases do GitHub não aceitam diretórios; o diretório continua para quem usa a saída local | Os CSV por país aparecem duas vezes no disco |
| Zip com data, permissões e ordem fixas e `deflate` nível 9 | Reprodutibilidade (R5.6) | Outra versão do zlib pode comprimir diferente; o conteúdo descompactado continua idêntico ao do diretório |
| `ATTRIBUTION.txt` em texto puro, e não Markdown | É o nome e o formato que a seção 5 do plano da spec 001 do tools-dataset espera | Sem links clicáveis no GitHub |
| Tabela de licenças com uma entrada por licença aceita, conferida por teste contra `LICENCAS_COMPATIVEIS` | Licença nova no ADR 0001 sem nome e URL quebra o teste antes de quebrar uma release | Uma entrada a mais para manter por licença |
| Cartão e atribuições gerados no build, não versionados no repositório | Não podem divergir de `sources.yaml` nem dos números da release | Quem lê o repositório sem release não vê o cartão; o README remete à release |
| `--data-license` com padrão `DATA_LICENSE` relativo ao diretório atual | Mesmo padrão de `--sources`; a CI e o script rodam da raiz | Rodar de outro diretório exige a opção |
| Lógica de release em `tools/release.sh`, com o YAML só chamando subcomandos | Testável com `gh` falso e reproduzível localmente (ADR 0014) | Um script de shell a mais para manter |

## Foco de revisão

1. **Atribuição sem edição:** o `attribution` da Statistics Canada aparece byte a byte em `ATTRIBUTION.txt` e no cartão (Task 3: `test_atribuicao_reproduz_o_texto_sem_edicao`; Task 4: `test_cartao_traz_os_avisos_da_statcan`).
2. **Aviso de condições só com a Statistics Canada:** presente com a fonte, ausente sem ela (Task 3: `test_aviso_de_condicoes_so_com_statcan`).
3. **Descartes desconhecidos versus zero:** Parquet antigo dá `null`, fonte sem descarte dá zero (Task 2: `test_build_sem_metadados_deixa_dropped_nulo`).
4. **Envio nunca sobrescreve nem publica:** o `gh` falso registra os argumentos (Task 6: `test_upload_sem_clobber_e_remove_o_cache_depois`, `test_upload_recusa_release_publicada`).
5. **Determinismo:** dois builds com `SHA256SUMS` iguais (Task 5: `test_dois_builds_iguais`).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `src/namescommons/adapters/__init__.py` | `RawDrop` | 1 |
| `src/namescommons/adapters/nz_dia_births.py` | Emite `RawDrop` em vez de logar | 1 |
| `src/namescommons/pipeline.py` | Conta e avisa os descartes (`Drops`) | 1 |
| `src/namescommons/io.py` | Descartes nos metadados do Parquet | 1 |
| `src/namescommons/manifest.py`, `src/namescommons/schema.py` | Campos novos do manifesto, `SCHEMA_VERSION` | 2 |
| `src/namescommons/cli.py` | Descartes de `ingest` para `build`, `--data-license`, arquivos de publicação | 1, 2, 5 |
| `src/namescommons/publication.py` | Licenças, avisos, atribuições, cartão, zip, somas | 3, 4, 5 |
| `DATA_LICENSE` | Preâmbulo com a linha de atribuição | 3 |
| `tools/release.sh`, `.github/workflows/release.yml`, `.github/workflows/ci.yml` | Release e ensaio | 6 |
| `.gitignore` | Limpeza | 7 |
| `README.md`, `AGENTS.md`, `docs/specs/001-esquema/spec.md`, `docs/specs/ROADMAP.md` | Documentação | 8 |
| Testes: `tests/test_descartes.py`, `tests/test_publicacao.py`, `tests/test_release.py` e ajustes em `tests/test_nz_dia_births.py`, `tests/test_cli.py`, `tests/test_io.py`, `tests/test_links.py`, `tests/test_cli_links.py`, `tests/test_cli_pipeline.py`, `tests/test_ci.py` | | 1 a 7 |

## Cobertura requisito -> tarefa

| Requisito | Tarefa |
|---|---|
| R1 | 1 |
| R2 | 2 |
| R3, R4 | 3 |
| R6 | 4 |
| R5 | 5 |
| R7 | 6 |
| R9 | 7 |
| R8 | 8 |
| R10 | 9 |
| Critérios 1 e 2 | 1, 2 |
| Critérios 3 e 4 | 3 |
| Critério 5 | 4 |
| Critério 6 | 5 |
| Critérios 7 e 8 | 6 |
| Critério 9 | 7 |
| Critério 10 | 9 |
