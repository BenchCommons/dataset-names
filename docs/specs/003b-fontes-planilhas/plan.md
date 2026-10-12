# 003b. Fontes em planilha: plano de implementação

**Objetivo:** ler XLS e XLSX com uma interface única e registrar a fonte nacional do INE (primeiros nomes e sobrenomes de residentes na Espanha).

**Arquitetura:** um módulo novo, `namescommons.spreadsheet`, reconhece o formato pelos primeiros bytes e devolve as linhas de uma aba como `(número, valores)`. O XLSX é lido em fluxo com `zipfile` e `iterparse`; o XLS, com `xlrd` 2.0.2 aberto sob demanda. Os dois caminhos normalizam os valores para `str`, `int`, `float`, `bool` ou `None`. `cell_count` estende o `parse_count` da spec 003 para células já tipadas. O adaptador `es_ine_residentes` lê os dois arquivos do INE só pela interface do leitor, valida cabeçalhos e o ano da edição e emite `RawRecord` de `given` (com sexo pela aba) e de `family` (pelo primeiro apellido).

**Stack:** a mesma da spec 003, mais `xlrd==2.0.2` em runtime ([ADR 0005](../../adr/0005-leitor-de-planilhas.md)). As amostras XLS são geradas com `xlwt` 1.3.0 executado à parte (`uv run --with xlwt==1.3.0`), sem entrar em `pyproject.toml`.

**Spec:** [`spec.md`](spec.md). ADRs: [`0001`](../../adr/0001-licenca-dos-dados.md), [`0002`](../../adr/0002-valores-suprimidos.md), [`0005`](../../adr/0005-leitor-de-planilhas.md). Pendência herdada: issue #13.

## Restrições globais

- Única dependência nova: `xlrd==2.0.2`, versão exata. Adaptadores não importam `xlrd` nem `zipfile` para ler planilha.
- Os testes nunca acessam a rede; as amostras ficam em `tests/fixtures/es-ine-residentes/` (menos de 20 KB no total) e as planilhas sintéticas do leitor em `tests/fixtures/planilhas/`.
- O contrato da spec 003 vale sem mudança: `FormatError` com o valor e o esperado, `parse_count`, `parse_code`, `SourceFiles`, valores suprimidos omitidos, marcador desconhecido falha.
- Mensagens de erro do leitor e do adaptador nomeiam o arquivo, a aba e a linha (ou a célula).
- `SCHEMA_VERSION` continua `1.0.0`; nenhum campo de saída muda.

## Decisões de implementação

| Decisão | Motivo |
|---|---|
| XLSX pela biblioteca padrão, XLS pelo `xlrd` | ADR 0005: o XLSX é XML simples e cabe em poucas linhas; o BIFF8 é binário delicado e o `xlrd` é Python puro e sem dependências |
| Formato pelos primeiros bytes | Um servidor que devolve HTML de erro com status 200 grava uma página no lugar da planilha; a extensão não diz nada |
| Valores normalizados (`int` para número inteiro, inclusive o `1446937.0` do XLS) | O adaptador não precisa saber de qual formato veio a célula; R1.3 da spec |
| Linhas vazias puladas e `None` do fim cortado nos dois formatos | O XLSX omite linhas e células vazias, e o `xlrd` preenche até `ncols`; cortar dá o mesmo resultado nos dois |
| Número da linha do Excel junto com os valores | As mensagens de `FormatError` apontam a linha que o usuário abre na planilha |
| Texto compartilhado: concatena `t` diretos e de `r`, ignora `rPh` | `rPh` é a leitura fonética (japonês); juntar daria um nome que não está na célula |
| `xlrd` com `on_demand=True` e `release_resources()` no fim | Carrega só a aba pedida e libera o arquivo |
| INE como uma fonte com dois arquivos (`es-ine-residentes`) | Nomes e sobrenomes são `population`; duas fontes ES `population` exigiriam uma só `primary` (spec 001, R2), e a outra não contaria |
| Sobrenome conta pelo `Apellido 1º` | Critério da lista, sem supressão, cada pessoa contada uma vez (spec, R2.5) |
| Ano pela frase "a fecha DD/MM/AAAA" acima do cabeçalho de cada aba | As URLs do INE não mudam entre edições; o ano no conteúdo evita trocar o código a cada maio |
| Abas de nomes por `parse_code({"Hombres": "M", "Mujeres": "F"})`; abas de sobrenomes validadas pelo cabeçalho | Uma aba nova ou renomeada falha alto em vez de virar outro sexo |
| Amostra XLSX remontada com o XML do INE (mesmos números de linha, textos compartilhados só das linhas copiadas) | Linhas esparsas e tipos de célula reais entram no teste sem arquivo grande |
| Amostra XLS gerada com `xlwt` a partir das linhas reais, preservando os números de linha e as colunas ocultas F e G | Não há como recortar um XLS sem regravar; `xlwt` grava BIFF8, o mesmo formato do INE |
| CI: só a lista de países do passo existente ganha `ES` | O passo já copia `tests/fixtures/` inteiro como cache e roda todas as fontes de `sources.yaml` |

## Foco de revisão

1. **HTML no lugar da planilha** (servidor que responde 200 com página de erro) precisa falhar com `FormatError` dizendo que não é XLS nem XLSX (Task 1: `test_r1_2_conteudo_que_nao_e_planilha`).
2. **Número inteiro guardado como fração no XLS** (`1446937.0`) precisa virar `int`, e uma contagem fracionária de verdade precisa falhar (Task 1: `test_r1_6_cell_count`; Task 2: `test_r1_3_mesmos_valores_nos_dois_formatos`).
3. **Texto compartilhado com formatação ou leitura fonética** não pode perder nem ganhar caracteres (Task 1: `test_r1_4_texto_compartilhado_com_formatacao_e_rph`).
4. **`..` no segundo apellido** não pode derrubar a fonte nem virar zero; só a coluna do primeiro apellido é lida (Task 3: `test_r2_5_sobrenome_pelo_primeiro_apellido`).
5. **Nome dos dois sexos** (`ANDREA`) gera linhas F e M e `female_share` correto em `ES.csv` (Task 4: `test_passo_das_fontes_oficiais_roda_localmente`).
6. **Edição nova com outro ano ou sem a frase da data** precisa ser lida pelo ano novo, ou falhar alto (Task 3: `test_r2_3_ano_da_edicao`).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `pyproject.toml`, `uv.lock` | `xlrd==2.0.2` | 2 |
| `src/namescommons/spreadsheet.py` | `sheet_names`, `rows`, `cell_count`; XLSX pela biblioteca padrão (Task 1) e XLS pelo `xlrd` (Task 2) | 1, 2 |
| `tests/test_spreadsheet.py`, `tests/fixtures/planilhas/` | Testes de R1.1 a R1.6; planilha sintética de tipos em XLS | 1, 2 |
| `src/namescommons/adapters/es_ine_residentes.py`, `tests/test_es_ine_residentes.py`, `tests/fixtures/es-ine-residentes/` | Fonte do INE (R2) | 3 |
| `sources.yaml`, `tests/fixtures/ATRIBUICAO.md` | Registro da fonte e atribuição da amostra | 3 |
| `.github/workflows/ci.yml`, `tests/test_ci.py` | Passo da CI com `ES` (R4) | 4 |
| `AGENTS.md` | `xlrd` na lista da stack | 2 |

## Cobertura da spec

| Requisito | Tarefa |
|---|---|
| R1.1, R1.2, R1.3, R1.4, R1.6 | 1 |
| R1.3 (XLS), R1.5 | 2 |
| R2, R2.1 a R2.7 | 3 |
| R3 | 1, 2, 3 (`tests/test_fontes_oficiais.py` já percorre a fonte nova) |
| R4 | 4 |
| R5 | Fechamento (medição com os arquivos reais) |
| R6 | Sem código: registro na spec e issues de acompanhamento |
| Critério de aceite 1 | 3 |
| Critério 2 | 2 (`test_r1_3_amostras_do_ine`) |
| Critério 3 | 1, 2 |
| Critério 4 | 3 |
| Critério 5 | 4 |
| Critério 6 | 4 e fechamento (CI verde no pull request) |
| Critério 7 | Fechamento |
| Critério 8 | 2 |
| Critério 9 | Fechamento (issues e `Closes #13`) |
