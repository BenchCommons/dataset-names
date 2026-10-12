# 003e. Nova Zelândia: plano de implementação

**Objetivo:** ingerir o CSV de nomes de bebês do Department of Internal Affairs (DIA) da Nova Zelândia sem deixar entrar nome corrompido na fonte, e fazer o download bloqueado pela Imperva falhar com a orientação de gravar o arquivo do navegador no cache.

**Arquitetura:** `cache._baixar` passa a recusar resposta `text/html` para recurso que não é HTML, com uma exceção `BlockedError(FetchError)` que `fetch_resource` não repete. O adaptador `nz_dia_births.py` lê o CSV em bytes, decodifica como UTF-8 se o arquivo inteiro for válido e, senão, pela tabela fechada de R2.2; descarta nomes com `?` ou U+FFFD, conta os descartes e avisa pelo `logging` ao fim do arquivo. Só biblioteca padrão.

**Stack:** a mesma da spec 003, sem dependência nova.

**Spec:** [`spec.md`](spec.md). ADRs: [`0001`](../../adr/0001-licenca-dos-dados.md), [`0002`](../../adr/0002-valores-suprimidos.md), [`0007`](../../adr/0007-nomes-corrompidos-na-fonte.md). Pendências herdadas: issue #10.

## Restrições globais

- Nenhuma dependência nova de runtime ou de desenvolvimento; nenhum navegador automatizado.
- Testes sem rede: o servidor de `tests/conftest.py` serve a amostra e a página HTML de bloqueio.
- Amostra com bytes copiados do arquivo real, gerada por script (os bytes `0x82`, `0x8D`, `0x8F`, `0xE9` e `0xF6` não podem depender do editor), menos de 20 KB.
- Nenhum nome com `?` ou U+FFFD sai do adaptador.
- `sources.yaml` e `tests/fixtures/ATRIBUICAO.md` ganham a fonte ao fim do arquivo (outras specs acrescentam fontes em paralelo).
- `SCHEMA_VERSION` continua `1.0.0`.

## Decisões de implementação

| Decisão | Motivo |
|---|---|
| Tabela fechada `{0x82: é, 0xE9: é, 0xF6: ö}` em vez de uma página de código | O arquivo mistura CP437/CP850 e Latin-1; qualquer página única corrompe parte dos nomes (`Zoé` em CP437 vira `ZoΘ`, `Amélie` em Windows-1252 vira `Am‚lie`) |
| `0x8D` e `0x8F` sem tradução, mesmo sabendo que os nomes são Nīkau e Kāwhai | As páginas de código leem esses bytes como outras letras (`ì`, `Å`, `ç`, `è`), nunca `ī` e `ā`; a tradução seria um palpite apoiado só no nome, e o ADR 0007 só aceita a leitura que forma o nome atestado |
| UTF-8 primeiro, para o arquivo inteiro | Uma edição corrigida pela fonte é lida sem mudança de código; um arquivo legado com bytes acentuados quase nunca forma UTF-8 válido por acaso |
| Decodificação por linha só depois de decidir a codificação do arquivo | A decisão por linha deixaria um arquivo meio UTF-8 e meio legado passar sem aviso |
| Aviso pelo `logging` (logger do módulo), e não um canal novo no contrato | O contrato de `parse` só produz registros; o `logging` aparece no `stderr` da CLI sem configuração (`lastResort`) e é testável com `caplog` |
| `BlockedError` sem novas tentativas | A página de desafio não some com nova tentativa; repetir só atrasa a mensagem |
| Regra do HTML em `cache.py`, para toda fonte | Uma página de erro HTML gravada com o nome do CSV corromperia o cache de qualquer fonte; o `filename` `.html` ou `.htm` fica de fora para não barrar uma fonte que publique HTML |
| Também `FormatError` no adaptador para arquivo que começa com `<` | Quem salva a página de desafio pelo navegador em vez do CSV recebe a mesma orientação |
| Ano e contagem por `parse_count` sem marcadores | A fonte omite a linha suprimida; um marcador novo tem de falhar, como na spec 003 |

## Foco de revisão

1. **Esmé em duas codificações** (`0x82` até 2023, `0xE9` em 2024 e 2025) vira um único nome (Task 2: `test_parse_da_amostra_real`).
2. **Nome com `?` ou byte sem leitura** nunca sai do adaptador, e o aviso conta linhas e registros (Task 2: `test_nomes_corrompidos_sao_descartados_e_avisados`).
3. **Página de desafio com status 200** não entra no cache (Task 1: `test_pagina_html_no_lugar_do_arquivo_nao_entra_no_cache`).
4. **Arquivo corrigido pela fonte em UTF-8** é lido sem tabela (Task 2: `test_arquivo_utf8_valido_e_lido_como_utf8`).
5. **Campo a mais ou a menos, sexo desconhecido ou contagem com marcador** falham com `FormatError` e número da linha (Task 2: `test_formato_inesperado_falha`).

## Arquivos

| Arquivo | Responsabilidade | Tarefa |
|---|---|---|
| `src/namescommons/cache.py`, `tests/conftest.py`, `tests/test_cache.py` | Recusa de `text/html` (R4.1); servidor local com `Content-Type` programável | 1 |
| `src/namescommons/adapters/nz_dia_births.py`, `tests/test_nz_dia_births.py`, `tests/fixtures/nz-dia-births/` | Adaptador (R1 a R3, R4.2, R4.4) e amostra (R5) | 2 |
| `sources.yaml`, `tests/fixtures/ATRIBUICAO.md` | Registro da fonte e atribuição da amostra | 2 |
| `.github/workflows/ci.yml`, `tests/test_ci.py` | `NZ` no passo das fontes oficiais (R6) | 3 |

## Cobertura da spec

| Requisito | Tarefa |
|---|---|
| R1, R1.1 a R1.5 | 2 |
| R2.1, R2.2 | 2 |
| R2.3 | Sem código: regra para edições futuras, no ADR 0007 e na docstring |
| R3.1, R3.2 | 2 |
| R3.3 | Fechamento (medição com o arquivo real) |
| R4.1 | 1 |
| R4.2, R4.4 | 2 |
| R4.3 | Todas (nenhum contorno, nenhuma dependência) |
| R5 | 2 (`tests/test_fontes_oficiais.py` passa a cobrir a fonte) |
| R6 | 3 |
| R7 | Fechamento |
| Critérios 1 a 4 | 2 |
| Critério 5 | 1 e 2 |
| Critério 6 | 3 e fechamento (CI verde) |
| Critério 7 | Fechamento |
| Critério 8 | Fechamento (`Closes #10`) |
