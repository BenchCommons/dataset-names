# 003. Fontes oficiais: plano de implementação

**Objetivo:** registrar e ingerir o primeiro lote de fontes oficiais (SSA, INSEE, CSO e Statistics Norway) e fechar no contrato do adaptador as regras levantadas na issue #8.

**Arquitetura:** o contrato da spec 002 ganha, em `namescommons.adapters`, os auxiliares `parse_count` e `parse_code`, a exceção `FormatError` e o dicionário `SourceFiles`, que explica a chave pedida fora de `RESOURCES`. `load_adapter` separa adaptador ausente de adaptador quebrado. `pipeline.to_observations` confere `kind`, `gender`, `country` e `count` em cada registro, na ordem do arquivo, antes de ordenar. Cada fonte é um módulo em `src/namescommons/adapters/` que lê o arquivo baixado só com a biblioteca padrão (`zipfile`, `csv`, `json`); as duas tabelas do SSB dividem o leitor de JSON-stat num módulo privado `_ssb.py`. `cache.py` explica o 403. A CI ganha um passo que roda as fontes reais sobre as amostras.

**Stack:** a mesma da spec 002 (Python 3.12 via `uv`, `pyarrow`, `pyyaml`, `pycountry`, `pytest`), sem dependência nova. Formatos lidos: ZIP com TXT ou CSV, CSV com BOM e CRLF, JSON-stat 2.0.

**Spec:** [`spec.md`](spec.md). ADRs: [`0001`](../../adr/0001-licenca-dos-dados.md), [`0002`](../../adr/0002-valores-suprimidos.md). Pendências herdadas: issue #8.

## Restrições globais

- Nenhuma dependência nova de runtime ou de desenvolvimento.
- Os testes nunca acessam a rede: downloads usam o servidor de `tests/conftest.py`, e cada adaptador lê a amostra em `tests/fixtures/<id>/`.
- Amostras com os mesmos nomes de arquivo de `RESOURCES`, menos de 20 KB por fonte, linhas copiadas do arquivo real e atribuição em `tests/fixtures/ATRIBUICAO.md`.
- Licenças só da lista do ADR 0001; `primary: true` em todas as fontes do lote; `retrieved: 2026-10-12`.
- `country: "NO"` sempre entre aspas em YAML.
- Valores suprimidos são omitidos pelo adaptador (ADR 0002); registro com `count` vazio numa fonte `births` ou `population` é erro.
- Mensagem de erro de registro: `registro N: <causa>`, com N a partir de 1 na ordem de `parse`. Mensagem de formato: `FormatError` com o valor recebido e o esperado.
- `SCHEMA_VERSION` continua `1.0.0`: nenhum campo de saída muda.

## Decisões de implementação

| Decisão | Motivo |
|---|---|
| Primeiro lote só com fontes nacionais em texto: SSA, INSEE, CSO, SSB (duas tabelas) | Cabe numa revisão, não exige leitor de planilha nem regra de fonte subnacional, e as licenças estão todas na lista do ADR 0001 |
| Conferência de `kind`, `gender`, `country` e `count` em `to_observations`, registro a registro | A posição no arquivo da fonte é o que o autor do adaptador precisa; `validate` só vê a tabela ordenada |
| `count` vazio numa fonte com contagem é recusado no registro; o teste `test_r1_4_repetidos_com_e_sem_contagem_sao_recusados` da 002 passa a esperar essa mensagem | É o único teste da 002 cujo caminho deixa de ser alcançável: a recusa acontece antes da soma de R1.4 |
| `parse_count` aceita só `[0-9]+` e os marcadores declarados | `str.isdigit` aceitaria dígitos de outras escritas; marcador novo tem de falhar, não virar zero |
| Validade de país guardada num dicionário por chamada de `to_observations` | 3 milhões de registros com poucos países distintos; `pycountry` a cada registro custaria tempo à toa |
| SSA: o ano vem do nome do membro `yobAAAA.txt`; membros fora desse padrão são ignorados | O ZIP traz também o PDF de leia-me |
| INSEE: `RARES` é emitido; só nomes começando com `_` e o ano `XXXX` são pulados | `RARES` é o nome Rareș sem diacrítico (15 meninos em 2025); o agregado das edições antigas era `_PRENOMS_RARES` |
| INSEE: arquivo do cache com o nome da edição (`prenoms-2025-nat_csv.zip`) | Uma edição nova muda URL e nome do arquivo, e o cache não serve a edição antiga por engano |
| CSO: filtro pelo código exato da estatística (`VSA50C01`, `VSA60C01`) e pela coluna do nome de cada tabela | O CSV traz contagem e rank misturados, ambos com unidade `Number` |
| SSB: PxWebApi v2 por GET com colchetes codificados (`%5B`, `%5D`) e `outputFormat=json-stat2` | `Resource` só faz GET; o JSON-stat traz código e rótulo do nome e o status de cada célula, e o CSV perde o sexo |
| SSB: leitor comum em `src/namescommons/adapters/_ssb.py` | Duas fontes do mesmo instituto (R2.4); o `_` impede colisão com um `id` |
| 403 explicado em `fetch_resource`, sem contornar o bloqueio e sem repetir a requisição (4xx é definitivo, ver plano da spec 002) | O site da SSA recusa robôs; a saída honesta é dizer onde gravar o arquivo baixado à mão |
| `servir_fixtures` como fixture de `conftest.py`, e não como função do pacote | Só os testes precisam dela; o pacote publicado não carrega código de teste |
| Passo novo na CI copia como cache só os diretórios de `tests/fixtures/` das fontes oficiais (todos menos `exemplo`) | Os diretórios das amostras já têm os nomes de `RESOURCES`. Revisada na manutenção da issue #12: antes copiava `tests/fixtures/` inteiro, levando `exemplo/` e arquivos soltos para o cache |

## Foco de revisão

Casos que a spec implica e que um usuário vai encontrar. Cada um tem teste na tarefa dona do código.

1. **`country: NO` sem aspas** vira `false` no YAML e a Noruega some com uma mensagem confusa; precisa falhar pedindo aspas (Task 5: `test_country_no_sem_aspas_tem_mensagem_clara`).
2. **`RARES` no INSEE** parece o agregado de nomes raros, mas é um nome real; precisa ser emitido (Task 3: `test_rares_e_um_nome_real_e_nao_um_agregado`).
3. **Marcador de supressão novo** (`<3` no CSO, `<5` na SSA) não pode virar zero nem ser pulado em silêncio (Task 1: `test_r2_2_parse_count_recusa_o_que_nao_conhece`; Task 2: `test_formato_inesperado_falha`; Task 4: `test_formato_inesperado_falha`).
4. **Nome dos dois sexos** (`Kim` na Noruega, `Liam` e `Avery` nos EUA, `Camille` na França) gera linhas F e M e um `female_share` correto (Task 5: `test_fornavn_da_amostra_real`; Task 6: `test_passo_das_fontes_oficiais_roda_localmente`, que confere `Kim` com 0,049763).
5. **Site que bloqueia o download** (SSA, 403) termina com o caminho exato onde gravar o arquivo (Task 2: `test_403_explica_como_colocar_o_arquivo_no_cache`).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `src/namescommons/adapters/__init__.py` | `FormatError`, `SourceFiles`, `parse_count`, `parse_code`; `load_adapter` com ausente, quebrado e caminho esperado | 1 |
| `src/namescommons/pipeline.py` | Conferência por registro (R2.1, R2.3); `SourceFiles` no `ingest` | 1 |
| `tests/conftest.py`, `tests/test_contrato_adaptador.py`, `tests/test_pipeline.py` | `servir_fixtures`, `servidor.recusados`; testes de R2; ajuste de um teste da 002 | 1 |
| `src/namescommons/cache.py` | Mensagem do 403 (R4) | 2 |
| `src/namescommons/adapters/us_ssa_births.py`, `tests/test_us_ssa_births.py`, `tests/fixtures/us-ssa-births/` | Fonte SSA (R1.1) | 2 |
| `sources.yaml`, `tests/fixtures/ATRIBUICAO.md`, `tests/test_fontes_oficiais.py` | Registro das fontes, atribuição das amostras, teste que percorre todas as fontes | 2, 3, 4, 5 |
| `src/namescommons/adapters/fr_insee_births.py`, `tests/test_fr_insee_births.py`, `tests/fixtures/fr-insee-births/` | Fonte INSEE (R1.2) | 3 |
| `src/namescommons/adapters/ie_cso_births.py`, `tests/test_ie_cso_births.py`, `tests/fixtures/ie-cso-births/` | Fonte CSO (R1.3) | 4 |
| `src/namescommons/sources.py` | País booleano no YAML (R2.7) | 5 |
| `src/namescommons/adapters/_ssb.py`, `no_ssb_fornavn.py`, `no_ssb_etternavn.py`, `tests/test_no_ssb.py`, `tests/fixtures/no-ssb-*/` | Fontes do SSB (R1.4, R1.5, R2.4) | 5 |
| `.github/workflows/ci.yml`, `tests/test_ci.py` | Passo da CI com as fontes oficiais (R5) | 6 |

## Cobertura da spec

| Requisito | Tarefa |
|---|---|
| R1 (cinco fontes e licenças) | 2, 3, 4, 5 |
| R1.1 | 2 |
| R1.2 | 3 |
| R1.3 | 4 |
| R1.4, R1.5 | 5 |
| R2.1, R2.2, R2.3, R2.5, R2.6 | 1 |
| R2.4 | 5 (`test_um_instituto_dois_count_types_sao_duas_fontes`) |
| R2.7 | 5 |
| R3 | 2, 3, 4, 5 (`tests/test_fontes_oficiais.py`) |
| R4 | 2 |
| R5 | 6 |
| R6 | Fechamento (medição com os arquivos reais) |
| R7 | Sem código: registro na spec e no roadmap |
| Critério de aceite 1 | 2, 3, 4, 5 (`test_amostra_e_atribuicao`) |
| Critério 2 | 2, 3, 4, 5 |
| Critério 3 | 1, 5 |
| Critério 4 | 6 (`test_passo_das_fontes_oficiais_roda_localmente`) |
| Critério 5 | 2 |
| Critério 6 | 6 e fechamento (CI verde no pull request) |
| Critério 7 | Fechamento |
| Critério 8 | Fechamento (`Closes #8`), conforme a tabela abaixo |

Itens da issue #8:

| Item | Requisito |
|---|---|
| O adaptador converte os valores | R2.1 |
| Códigos de sexo de outras línguas colidem | R2.2 |
| O adaptador preenche `country` mesmo com país em `sources.yaml` | R2.1 |
| Valores suprimidos | R2.3 e ADR 0002 |
| Um instituto com dois `count_type` vira duas fontes | R2.4 |
| Teste contra servidor local | R2.5 |
| Mensagens (`KeyError`, módulo ausente, "observação N") | R2.6 |
| Margem de memória do R8 | R6 |
