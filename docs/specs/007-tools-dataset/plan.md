# 007. Adoção do kit de fontes do tools-dataset: plano de implementação

**Objetivo:** trocar as cópias locais do código genérico de fontes pelo pacote `benchcommons-tools-dataset` 0.1.0 (import `datasettool`), sem mudar CLI nem saídas.

**Arquitetura:** `datasettool` entra como dependência fixada na tag `v0.1.0`. `namescommons.adapters` vira uma camada fina: guarda `RawRecord`, `RawLink` e `DEFAULT_PACKAGE`, reexporta os objetos do kit e embrulha `load_adapter` e `check_adapter` com `optional=("links",)`. `namescommons.sources` passa a declarar um `RegistrySchema` com os campos de nomes, a lista de licenças e a regra de uma `primary`, e a fábrica do `Source` daqui. O pipeline chama `datasettool.sources.cache.fetch_resource` com o `User-Agent` deste projeto. O adaptador do INE lê planilhas por `datasettool.sources.spreadsheet`. `build_manifest` usa `datasettool.files.describe_files` com contadores para `.csv` e `.parquet`.

**Stack:** a mesma de antes, com `benchcommons-tools-dataset==0.1.0` no lugar de `pyyaml` e `xlrd` diretos ([ADR 0013](../../adr/0013-dependencia-do-tools-dataset.md)).

**Spec:** [`spec.md`](spec.md). Contrato do kit (dono: tools-dataset): [spec 004](https://github.com/BenchCommons/tools-dataset/blob/v0.1.0/docs/specs/004-source-toolkit/spec.md) e [plano](https://github.com/BenchCommons/tools-dataset/blob/v0.1.0/docs/specs/004-source-toolkit/plan.md) na tag `v0.1.0`. Acompanhamento: [tools-dataset#5](https://github.com/BenchCommons/tools-dataset/issues/5).

## Restrições globais

- Nenhuma cópia nem remendo local do kit. Se algo do kit não servir, a correção é uma issue no tools-dataset.
- Saídas idênticas byte a byte às de `master` (`0153007`) nos dois passos offline da CI e no cache real completo. Linha de base gravada antes de qualquer mudança de código: fixtures em 832 testes verdes, 8 observações no passo do exemplo, 109 no das fontes oficiais, 4.336.051 no cache real (123 s, 2,96 GB de pico).
- Mensagens de nomes continuam em português; só as do kit mudam para o inglês.
- Um arquivo ou teste só é removido depois que o substituto passa: o kit passa 360 testes na tag `v0.1.0` (conferido em 2026-10-12 com `uv run pytest -q` num clone da tag), e a suíte daqui passa com o kit antes de cada remoção.
- `SCHEMA_VERSION` continua `1.2.0`; nenhum campo de saída muda.

## Decisões de implementação

| Decisão | Motivo | Custo se estiver errada |
|---|---|---|
| `namescommons.adapters` reexporta os objetos do kit em vez de os adaptadores importarem de `datasettool` | Os nove adaptadores e os testes continuam com um só ponto de import; `FormatError` é o mesmo objeto, e `except FormatError` pega erros do leitor de planilhas | Uma camada a mais para ler; trocar os imports depois é mecânico |
| `load_adapter` e `check_adapter` embrulhados com `optional=("links",)` e pacote padrão | O kit não tem pacote padrão nem conhece `links`; sem o invólucro, cada chamada teria de repetir os dois | Nenhum: é o uso previsto no plano 2.1 do kit |
| `SourceError = RegistryError` | A CLI e os testes capturam `SourceError`; o nome continua válido e é a mesma classe | Nenhum além de um alias |
| Mensagens dos campos de nomes continuam em português | A spec aceita mudança de língua só no que vem do kit; os testes de nomes ficam iguais | Uma mensagem com vários erros pode misturar português e inglês; traduzir depois é uma issue |
| `parse_count` sem invólucro: o campo padrão vira `count` | Os adaptadores que não passam `field` passam a dizer `count '<5' is neither...`; é mensagem do kit | Nenhum para dados; só o texto do erro |
| `USER_AGENT` em `namescommons/__init__.py`, montado com `make_user_agent` | É o ponto único usado pelo pipeline e por `tools/amostra_wikidata.py`; o texto fica igual ao anterior | Nenhum |
| `pyyaml` e `xlrd` saem das dependências diretas | Nenhum módulo de `src/` os importa; o kit os fixa (ADR 0005 do kit) | Se um módulo daqui voltar a importá-los, precisa declarar de novo |
| `LocalServer` continua em `tests/conftest.py` | O kit não exporta utilidades de teste | Duplicação pequena de código de teste |
| Teste das amostras do INE pelo leitor vai para `tests/test_es_ine_residentes.py` | É o único teste do leitor que o kit não portou (dados CC BY 4.0 daqui, decisão D6 do kit) | Nenhum |
| Testes de registro com campos de nomes ficam; os genéricos saem | O esquema real daqui (pycountry, `strips_accents`) não é o `names_registry.py` de teste do kit | Alguns testes parecidos nos dois repositórios |

## Foco de revisão

1. **Saídas idênticas:** `diff -r` das saídas deste branch contra as de `master` nas fixtures e no cache real (Task 7).
2. **`FormatError` do leitor de planilhas** continua capturado pelo pipeline e pelos testes do INE como erro do domínio (Task 2: `test_reexporta_os_objetos_do_kit`; Task 3).
3. **`User-Agent`** igual ao anterior, byte a byte, no pedido real ao servidor local (Task 4: `test_pipeline_envia_o_user_agent_do_projeto`).
4. **`strips_accents`** continua campo de nomes, com padrão `false`, e as três fontes de `sources.yaml` continuam marcadas (Task 5).
5. **Ordem das mensagens do registro:** nenhum teste confere a ordem das linhas (Task 5).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `pyproject.toml`, `uv.lock` | Dependência fixada na tag | 1 |
| `tests/test_tools_dataset.py` | Integração com o kit (R5.3) | 1 a 6 |
| `src/namescommons/adapters/__init__.py` | `RawRecord`, `RawLink`, reexports, invólucros | 2 |
| `src/namescommons/adapters/es_ine_residentes.py` | Leitor de planilhas do kit | 3 |
| `src/namescommons/__init__.py` | `USER_AGENT` do projeto | 4 |
| `src/namescommons/pipeline.py` | `fetch_resource` do kit com `User-Agent` | 4 |
| `tools/amostra_wikidata.py` | `USER_AGENT` de `namescommons` | 4 |
| `src/namescommons/sources.py` | Esquema de nomes sobre o registro do kit | 5 |
| `src/namescommons/manifest.py` | `describe_files` com contadores CSV e Parquet | 6 |
| `.github/workflows/ci.yml` | Tira a exclusão de `tests/fixtures/planilhas` | 3 |
| `AGENTS.md`, `README.md`, `docs/specs/ROADMAP.md` | Documentação | 7 |

### Removidos (R2.6)

| Arquivo ou teste | Substituto no kit (tag `v0.1.0`) |
|---|---|
| `src/namescommons/cache.py` | `datasettool.sources.cache` |
| `src/namescommons/spreadsheet.py` | `datasettool.sources.spreadsheet` |
| `tests/test_cache.py` (22 testes) | `tests/test_cache.py` (28) |
| `tests/test_spreadsheet.py` (43 de 44 testes; `test_r1_3_amostras_do_ine` vai para `tests/test_es_ine_residentes.py`) | `tests/test_spreadsheet.py` (46) |
| `tests/fixtures/planilhas/tipos.xls` | `tests/fixtures/spreadsheets/types.xls`, cópia idêntica |
| `tests/test_manifest.py` (1 teste) | `tests/test_files.py` |
| Em `tests/test_adapters.py`: `test_nome_do_modulo`, `test_carrega_o_adaptador_de_exemplo`, `test_adaptador_inexistente`, `test_adaptador_valido`, `test_adaptador_invalido`, `test_adaptador_sem_atributo` | `tests/test_adapters.py` |
| Em `tests/test_contrato_adaptador.py`: `test_r2_2_parse_count`, `test_r2_2_parse_count_recusa_o_que_nao_conhece`, `test_r2_2_parse_code_traduz_e_recusa_codigo_desconhecido`, `test_r2_6_arquivo_fora_de_resources_lista_os_disponiveis`, `test_r2_6_adaptador_ausente_mostra_o_caminho_esperado`, `test_r2_6_adaptador_quebrado_nao_se_passa_por_ausente`, `test_r2_6_pacote_de_adaptadores_inexistente` | `tests/test_adapters.py` |
| Em `tests/test_sources.py`: `test_arquivo_sem_fontes`, `test_id_com_formato_invalido`, `test_campo_ausente`, `test_id_duplicado`, `test_licenca_nao_textual_vira_source_error`, `test_id_nao_textual_vira_source_error`, `test_entrada_que_nao_e_mapeamento`, `test_arquivo_inexistente`, `test_yaml_malformado`, `test_raiz_que_nao_e_mapeamento`, `test_sources_que_nao_e_lista`, e os casos `retrieved`, `url` e `extra` de `test_campo_invalido` | `tests/test_registry.py` |
| Em `tests/test_sources_extensoes.py`: `test_retrieved_com_hora_e_recusado`, `test_retrieved_com_hora_no_yaml_e_recusado`, `test_url_sem_esquema_http_e_recusada`, `test_url_http_e_https_aceitas`, `test_url_malformada_nomeia_a_fonte_em_vez_de_levantar_value_error`, e o caso `adapter` de `test_campo_opcional_nao_booleano` | `tests/test_registry.py` |
| Em `tests/test_robustez.py`: `test_manifesto_conta_registros_csv_e_nao_linhas_fisicas` | `tests/test_files.py` |

## Cobertura requisito -> tarefa

| Requisito | Tarefa |
|---|---|
| R1.1, R1.2 | 1 (dependência), 3 e 5 (saída de `xlrd` e `pyyaml` quando o último uso some) |
| R2.1, R3.3 | 4 |
| R2.2 | 3 |
| R2.3, R3.1 | 2 |
| R2.4, R3.2 | 5 |
| R2.5, R3.4 | 6 |
| R2.6 | 2 a 6, cada uma remove o que substituiu |
| R3.5, R4 | 7 (verificação), e cada tarefa roda a suíte inteira |
| R5 | 1 a 6 |
| R6 | 7 |
