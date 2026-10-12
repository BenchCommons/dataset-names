# 003e. Nova Zelândia: nomes de bebês do Department of Internal Affairs

Parte do [roadmap](../ROADMAP.md). Depende da [spec 003](../003-fontes-oficiais/spec.md). Licença dos dados: [ADR 0001](../../adr/0001-licenca-dos-dados.md). Valores suprimidos: [ADR 0002](../../adr/0002-valores-suprimidos.md). Nomes corrompidos na fonte: [ADR 0007](../../adr/0007-nomes-corrompidos-na-fonte.md). Pendências herdadas: issue #10.

Status: Implementada e mesclada (PR #28, 2026-10-12).

## Por quê

A spec 003 (R7) deixou a Nova Zelândia "não avaliada", porque o catálogo `catalogue.data.govt.nz` bloqueia o acesso automático. A issue #10 avaliou a fonte pelo navegador: a licença é CC BY 4.0 e o arquivo é um CSV nacional de 1900 a 2025, com sexo e contagem por ano. A fonte tem duas ressalvas que nenhum adaptador da 003 enfrentou:

1. **Codificação misturada.** O CSV não é UTF-8 nem uma única codificação legada. Alguns acentos vêm num byte de uma página de código, outros noutra, e as vogais com macron do te reo Māori (ā, ī) vêm como `?` ou como bytes sem correspondência em nenhuma página de código conhecida.
2. **Bloqueio sem 403.** O host (Imperva) responde ao cliente HTTP comum com status 200 e uma página HTML de desafio ("Pardon Our Interruption"), e não com 403. A mensagem da spec 003 (R4) não dispara, e o cache gravaria a página HTML com o nome do CSV.

Esta spec registra a fonte, decide byte a byte o que pode ser recuperado e o que é descartado, e faz o download bloqueado falhar com a mesma orientação da SSA.

## Requisitos

### R1. Fonte

Uma entrada nova em `sources.yaml` com `primary: true` (nenhuma outra fonte tem o par `NZ`, `births`) e um adaptador em `src/namescommons/adapters/nz_dia_births.py`. Números medidos no arquivo real baixado pelo navegador em 2026-10-12.

| Campo | Valor |
|---|---|
| `id` | `nz-dia-births` |
| Instituto | Department of Internal Affairs (DIA), conjunto "Baby Name popularity over time" |
| País | NZ |
| `kind` | given |
| `count_type` | births (registros de nascimento por ano) |
| Anos | 1900 a 2025, ano do registro do nascimento e não da data de nascimento |
| Supressão (`suppression`) | nomes com menos de 10 registros no ano são omitidos pela fonte (10) |
| Recurso | `baby-names-1900-to-2025.csv`, https://catalogue.data.govt.nz/dataset/01ee87cd-ecf8-44a1-ad33-b376a689e597/resource/0b0b326c-d720-480f-8f86-bf2d221c7d3f/download/baby-names-1900-to-2025.csv |
| Formato | CSV `Year,Sex,Name,Count`, fim de linha CRLF, sem BOM, sem aspas, quatro campos em toda linha |
| Tamanho medido | 1.326.413 bytes (igual ao `size` do catálogo), SHA-256 `dccaa0ac0b46725cf355174b42ffce5b8e92f9ed0e26c6d5841412f95999e102` |
| Contagens | 74.019 linhas (40.204 F, 33.815 M), 4.516.506 registros somados; contagens de 10 a 1.628 |

Licença, conferida na página e na API do catálogo (`package_show`): `license_id` `CC-BY-4.0`, "Creative Commons Attribution 4.0 International", organização Department of Internal Affairs. Página: https://catalogue.data.govt.nz/dataset/baby-name-popularity-over-time

Particularidades que o adaptador trata:

- **R1.1** O cabeçalho é exatamente `Year,Sex,Name,Count`; outro cabeçalho é `FormatError` com o cabeçalho recebido.
- **R1.2** Sexo `F` é feminino e `M` é masculino, por `parse_code`; outro código é `FormatError`. A fonte exclui registros com sexo indeterminado.
- **R1.3** Ano e contagem por `parse_count`, sem marcador de supressão: a fonte não publica a linha suprimida, então qualquer texto não inteiro é `FormatError`.
- **R1.4** Linha com número de campos diferente de quatro é `FormatError` com o número da linha.
- **R1.5** Nomes com espaço (`Te Ariki`, `Te Ao`) e hífen (`Anne-Marie`) são emitidos como publicados. A fonte separa o primeiro nome dos nomes do meio por um processo automático; o adaptador não tenta corrigir essa separação.

### R2. Codificação do arquivo

Bytes acima de 0x7F medidos no arquivo real (71 linhas, todas na coluna `Name`), com a leitura de cada página de código candidata (CP437, CP850, Windows-1252, Latin-1 e Mac Roman). Toda página lê algum desses bytes como letra; o que decide a tradução é a posição do byte nos nomes do arquivo real: a letra só é aceita quando toda ocorrência do byte forma um nome atestado.

| Byte | Linhas | Exemplos | Leituras candidatas | Decisão |
|---|---|---|---|---|
| `0x82` | 38 | `Am_lie`, `Andr_`, `Esm_` (2009 a 2023), `Ren_e` | `é` em CP437 e CP850; `‚` (aspa) em Windows-1252; `Ç` em Mac Roman; controle em Latin-1 | `é`: só essa leitura forma Amélie, André, Danté, Esmé, Renée e Reneé em todas as ocorrências |
| `0xE9` | 25 | `Zo_`, `Esm_` (2024 e 2025) | `é` em Latin-1 e Windows-1252; `Ú` em CP850; `Θ` em CP437; `È` em Mac Roman | `é`: só essa leitura forma Zoé e Esmé; `ZoÚ`, `ZoΘ` e `ZoÈ` não são nomes atestados |
| `0xF6` | 1 | `Bj_rn` | `ö` em Latin-1 e Windows-1252; `÷` em CP437 e CP850; `ˆ` em Mac Roman | `ö`: forma Björn; as outras leituras não são letras |
| `0x8D` | 4 | `N_kau` | `ì` em CP437 e CP850; `ç` em Mac Roman; indefinido em Windows-1252; controle em Latin-1 | Sem tradução: o nome é Nīkau, e nenhuma leitura dá `ī` (`Nìkau` e `Nçkau` não são atestados) |
| `0x8F` | 3 | `K_whai` | `Å` em CP437 e CP850; `è` em Mac Roman; indefinido em Windows-1252; controle em Latin-1 | Sem tradução: o nome é Kāwhai, e nenhuma leitura dá `ā` (`KÅwhai` e `Kèwhai` não são atestados) |

Nenhuma codificação única lê o arquivo: `Esmé` aparece com `0x82` até 2023 e com `0xE9` em 2024 e 2025, e o arquivo não é UTF-8 válido (byte `0x82` na posição 54.334).

- **R2.1** Se o arquivo inteiro for UTF-8 válido, o adaptador o lê como UTF-8 (uma edição corrigida da fonte passa a valer sem mudança de código).
- **R2.2** Senão, o adaptador lê os bytes até 0x7F como ASCII e traduz os bytes acima de 0x7F por uma tabela fechada: `0x82` e `0xE9` viram `é`, `0xF6` vira `ö`. Qualquer outro byte acima de 0x7F vira U+FFFD, o que torna o nome corrompido (R3).
- **R2.3** A tabela só ganha um byte novo com evidência do arquivo real registrada nesta spec (leituras candidatas e nomes atestados em todas as ocorrências), conforme o ADR 0007.

### R3. Nomes corrompidos na fonte

- **R3.1** Nome que, depois de R2, contém `?` ou U+FFFD é descartado: nenhum registro é emitido para a linha ([ADR 0007](../../adr/0007-nomes-corrompidos-na-fonte.md)).
- **R3.2** Ao terminar o arquivo, se houve descarte, o adaptador registra um aviso no logger `namescommons.adapters.nz_dia_births` com o número de linhas descartadas, a soma das contagens delas e as formas distintas, por exemplo `nz-dia-births: 13 linha(s) com nome corrompido na fonte descartada(s), 164 registro(s): '?io', ...`. O aviso aparece no `stderr` da CLI sem configuração de logging.
- **R3.3** Medido no arquivo real: 64 linhas recuperadas por R2.2 (`Amélie`, `André`, `Björn`, `Danté`, `Esmé`, `Reneé`, `Renée`, `Zoé`) e 13 linhas descartadas, com 164 registros: `?io` (2), `?ria`, `M?hina`, `M?ia`, `N?kau`, `K�whai` (3) e `N�kau` (4), em que `�` é U+FFFD. Restam 74.006 linhas e 2.856 nomes distintos. O `ingest` produz 73.991 observações e 2.854 nomes: 15 pares de linhas do mesmo ano e sexo diferem só na caixa (`Jo-Anne` e `Jo-anne`, `MacKenzie` e `Mackenzie`, `McKenzie` e `Mckenzie`) e são somados pela chave da spec 002 (R1.4), com 4.516.342 registros no total; a forma exibida de cada par é a de maior contagem (spec 002, R1.4, como ajustada no PR #21).

### R4. Download bloqueado com status 200

- **R4.1** Quando a resposta de um download tem `Content-Type` `text/html` e o `filename` do recurso não termina em `.html` ou `.htm`, `fetch` não grava nada no cache e falha sem novas tentativas, com uma mensagem que diz que o servidor devolveu uma página HTML no lugar do arquivo (provável bloqueio de download automático), traz a URL e o caminho exato no cache onde gravar o arquivo baixado pelo navegador, para seguir com `--offline`. A regra vale para todas as fontes, como o 403 da spec 003 (R4).
- **R4.2** Se o arquivo no cache começar com `<` (por exemplo, a página de desafio gravada à mão pelo navegador), o adaptador levanta `FormatError` dizendo que o arquivo parece uma página HTML e indicando o caminho a substituir pelo CSV.
- **R4.3** Nenhum contorno de bloqueio é feito: sem troca de `User-Agent`, sem navegador automatizado, sem dependência nova.
- **R4.4** O procedimento manual (abrir a página do conjunto no navegador, baixar o CSV e gravá-lo em `<cache>/nz-dia-births/baby-names-1900-to-2025.csv`) fica na docstring do adaptador.

### R5. Amostra e testes

- `tests/fixtures/nz-dia-births/baby-names-1900-to-2025.csv` tem o cabeçalho e linhas copiadas byte a byte do arquivo real, com CRLF, menos de 20 KB, incluindo: nomes com `0x82`, `0xE9` e `0xF6`; `Esmé` nas duas codificações; um nome com `?` e dois com bytes sem leitura; nomes Māori sem macron (`Aroha`, `Nikau`, `Te Ariki`); um nome nos dois sexos (`Te Ao`); a primeira e a última linha do arquivo.
- `tests/fixtures/ATRIBUICAO.md` ganha a linha da fonte, ao fim da tabela.
- Testes de `parse` sobre a amostra com os registros esperados escritos à mão, de cada regra de R1.1 a R1.4, R2.1, R2.2, R3.1, R3.2, R4.1 e R4.2, todos sem rede.

### R6. CI

O passo da CI que roda as fontes oficiais sobre as amostras confere também `by_country/NZ.csv`.

### R7. Desempenho

Com o arquivo real no cache, `namescommons ingest nz-dia-births --offline` termina em poucos segundos (medido num Apple M4: 1,2 s e 114 MB de pico). A fonte é 2,4% do volume medido na spec 003 (R6) e não muda a margem de memória.

## Critérios de aceite

1. `sources.yaml` tem `nz-dia-births` com `license: CC-BY-4.0`, `country: NZ`, `count_type: births`, `suppression: 10`, e `load_sources` o aceita.
2. `parse` sobre a amostra real produz exatamente os registros escritos à mão no teste, com `Esmé` das duas codificações, `Björn` e `Zoé` corretos, e sem nenhum nome com `?` ou U+FFFD.
3. O descarte de nomes corrompidos gera um aviso com o número de linhas, a soma das contagens e as formas descartadas (teste com `caplog`).
4. Um arquivo UTF-8 válido com `Māia` é lido como UTF-8 e emite `Māia`.
5. Um download respondido com 200 e `text/html` falha sem tentar de novo, não deixa arquivo no cache e diz onde gravar o arquivo baixado pelo navegador; um arquivo HTML já no cache gera `FormatError` com o caminho.
6. `namescommons run --offline` sobre o cache montado com `tests/fixtures/` gera `by_country/NZ.csv`, e a CI roda verde no pull request.
7. Com o arquivo real, o adaptador emite 74.006 registros, `ingest --offline` da fonte produz 73.991 observações (R3.3) e avisa 13 linhas descartadas com 164 registros; tempo e memória medidos na descrição do pull request.
8. A issue #10 é fechada pelo pull request.

## Fora de escopo

- Recuperar as vogais com macron (`ā`, `ī`) a partir de `?`, `0x8D` ou `0x8F`: não há página de código que as leia, e `?` perde a informação. Fica a cargo da fonte corrigir o arquivo; R2.1 o aceita sem mudança de código.
- A planilha `top-names-by-year-1900-2025.xlsx` do mesmo conjunto: traz os mesmos nomes ordenados por ano e exige leitor de planilha (spec 003b).
- Corrigir a separação automática do primeiro nome feita pela fonte (R1.5).
- Download automatizado por navegador ou qualquer contorno do bloqueio da Imperva.
