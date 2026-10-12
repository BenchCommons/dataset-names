# 003. Fontes oficiais: primeiro lote

Parte do [roadmap](../ROADMAP.md). Depende da [spec 002](../002-pipeline/spec.md). Licença dos dados: [ADR 0001](../../adr/0001-licenca-dos-dados.md). Valores suprimidos: [ADR 0002](../../adr/0002-valores-suprimidos.md). Pendências herdadas: issue #8.

Status: Implementada e mesclada (PR #11, 2026-10-12).

## Por quê

A spec 002 entregou o contrato do adaptador, o cache e a CLI, mas `sources.yaml` ainda está vazio: o dataset não tem nenhum nome real. Esta spec registra o primeiro lote de institutos nacionais de estatística, com país, frequência e gênero, e escreve um adaptador para cada um.

Ao escrever um adaptador de teste contra o contrato da 002, a issue #8 levantou regras que o contrato deixou implícitas: quem converte os valores, o que fazer com valores suprimidos, como tratar um instituto que publica dois tipos de contagem, como testar contra um servidor local, mensagens de erro e margem de memória. Esta spec resolve cada uma antes que cinco adaptadores as resolvam de cinco jeitos.

O lote é pequeno de propósito. Ele cobre só fontes nacionais, publicadas em texto (CSV, TXT ou JSON) e com licença da lista do ADR 0001. Fontes em planilha, fontes que cobrem só parte de um país e fontes com licença fora da lista ficam para specs seguintes (ver "Fora de escopo").

## Requisitos

### R1. Fontes do primeiro lote

Cada linha vira uma entrada de `sources.yaml` com `primary: true` (nenhuma divide o par `country`, `count_type` com outra) e um adaptador em `src/namesio/adapters/`. Números medidos nos arquivos reais em 2026-10-12.

| `id` | Instituto | País | `kind` | `count_type` | Anos | Supressão (`suppression`) | Recurso e formato | Tamanho medido | Contagens |
|---|---|---|---|---|---|---|---|---|---|
| `us-ssa-births` | Social Security Administration | US | given | births | 1880 a 2024 | menos de 5 omitidos (5) | `names.zip` com um `yobAAAA.txt` por ano: `nome,sexo,contagem` | 9 MB compactado, 27 MB de texto | 2.149.477 |
| `fr-insee-births` | INSEE, Fichier des prénoms, edição 2025 | FR | given | births | 1900 a 2025 | só nomes dados ao menos 3 vezes desde 1900 (3) | `prenoms-2025-nat_csv.zip` com um CSV `sexe;prenom;periode;valeur;rang` | 4,3 MB compactado, 16,5 MB de CSV | 724.645 |
| `ie-cso-births` | Central Statistics Office, tabelas VSA50 e VSA60 | IE | given | births | 1964 a 2025 | menos de 3 em branco (3) | dois CSV do PxStat com o cubo inteiro (contagem e rank de todo nome em todo ano) | 38 MB e 51 MB | 82.952 |
| `no-ssb-fornavn` | Statistics Norway, tabela 10467 | NO | given | births | 1945 a 2025 | menos de 4 marcados com `.` (4) | JSON-stat 2.0 da PxWebApi v2 | 3,9 MB | 91.581 |
| `no-ssb-etternavn` | Statistics Norway, tabela 12891 | NO | family | population | 2018 a 2025 | menos de 200 marcados com `.` (200) | JSON-stat 2.0 da PxWebApi v2 | 266 KB | 28.484 |

Licenças, conferidas na página indicada:

| `id` | `license` | Evidência |
|---|---|---|
| `us-ssa-births` | `public-domain` | Obra do governo federal dos EUA (17 U.S.C. 105). O catálogo federal declara CC0: https://catalog.data.gov/dataset/baby-names-from-social-security-card-applications-national-data |
| `fr-insee-births` | `etalab-2.0` | Mentions légales do INSEE: informação pública do site sob a Licence Ouverte 2.0, com "Source : Insee": https://www.insee.fr/fr/information/2008466 |
| `ie-cso-births` | `CC-BY-4.0` | Campo de licença dos conjuntos no portal irlandês: https://data.gov.ie/dataset/vsa50-boys-names-in-ireland-with-3-or-more-occurrences e https://data.gov.ie/dataset/vsa60-girls-names-in-ireland-with-3-or-more-occurrences |
| `no-ssb-fornavn`, `no-ssb-etternavn` | `CC-BY-4.0` | Página da API do SSB: as APIs usam CC BY 4.0, como o resto do ssb.no: https://www.ssb.no/en/api |

Particularidades que o adaptador trata:

- **R1.1** `us-ssa-births`: o sexo é `F` ou `M`; o ano vem do nome do arquivo. Outros membros do ZIP (o PDF de leia-me) são ignorados.
- **R1.2** `fr-insee-births`: sexo `1` é masculino e `2` é feminino; nomes em maiúsculas (`uniform_case: true`). Os valores vêm arredondados ao múltiplo de 5 mais próximo, e o adaptador os usa como publicados. `RARES` é um nome real (Rareș sem diacrítico), não um agregado. Linhas de agregado de edições anteriores (`_PRENOMS_RARES`, ano `XXXX`) são puladas.
- **R1.3** `ie-cso-births`: só a estatística de contagem (`VSA50C01`, `VSA60C01`) é lida; o rank é ignorado. Valor vazio significa menos de 3 ou ausência e é omitido.
- **R1.4** `no-ssb-fornavn`: o prefixo do código do nome dá o sexo (`1` feminino, `2` masculino); o nome é o rótulo publicado. Até 2020 o ano é o de nascimento; desde 2021, o de registro do nome. A tabela só lista nomes usados por ao menos 200 pessoas no ano anterior. Células `.` e `..` são omitidas.
- **R1.5** `no-ssb-etternavn`: sobrenomes sem sexo; células `.` são omitidas. Pela regra de `population` da spec 001 (R3.3), o país usa só a edição mais recente.

### R2. Regras do contrato do adaptador (issue #8)

- **R2.1 O adaptador converte os valores.** `RawRecord` leva `year` e `count` como `int`, `gender` como `F`, `M` ou vazio, `country` em ISO 3166-1 alfa-2 e `kind` como `given` ou `family`. "Como a fonte publica" (spec 002, R1) vale para o nome, não para códigos. O adaptador preenche `country` mesmo quando `sources.yaml` declara o país. O pipeline confere `kind`, `gender` e `country` em cada registro, na ordem em que `parse` os produz, e recusa o primeiro inválido com `registro N: ...` (N começa em 1).
- **R2.2 Códigos da fonte só por mapeamento explícito.** O pacote oferece `parse_count(value, missing=(), field="contagem")` e `parse_code(value, mapping, field)`. Um código fora do mapeamento, ou um texto que não é inteiro nem marcador declarado, levanta `FormatError` com o valor e o esperado. Assim o `M` de "Mujer" nunca passa como masculino, e um marcador novo de supressão nunca vira zero.
- **R2.3 Valores suprimidos são omitidos** ([ADR 0002](../../adr/0002-valores-suprimidos.md)). O adaptador não emite registro para célula suprimida ou ausente (`<5`, `.`, `..`, vazio). Numa fonte `births` ou `population`, registro com `count` vazio é recusado pelo pipeline com `registro N: count vazio numa fonte '<tipo>'; valor suprimido deve ser omitido pelo adaptador`. Numa fonte `attested`, registro com `count` é recusado. O limite de supressão fica em `suppression` de `sources.yaml`.
- **R2.4 Um `count_type` por fonte.** Um instituto que publica, por exemplo, primeiros nomes como `births` e sobrenomes como `population` vira duas entradas em `sources.yaml` e dois módulos. Código comum aos dois fica num módulo privado `src/namesio/adapters/_<instituto>.py`, cujo nome não corresponde a nenhum `id`.
- **R2.5 Teste contra servidor local.** A fixture `servir_fixtures` de `tests/conftest.py` serve `tests/fixtures/<SOURCE_ID>/<filename>` no servidor HTTP local da spec 002 e aponta `RESOURCES` do módulo para ele durante o teste.
- **R2.6 Mensagens de erro.**
  - `parse` que pede um arquivo fora de `RESOURCES` recebe `AdapterError` com o nome pedido e a lista dos disponíveis, e não um `KeyError` solto.
  - Adaptador ausente: a mensagem traz o caminho esperado do arquivo (`.../adapters/<modulo>.py`). Adaptador que existe mas falha ao importar: a mensagem diz "quebrado" e traz a exceção original. Pacote de adaptadores inexistente: a mensagem diz que o pacote não foi encontrado.
  - `validate` continua numerando "observação N" na tabela já ordenada; os erros que um adaptador comete (R2.1 e R2.3) são pegos antes, com a posição no arquivo da fonte.
- **R2.7 País booleano no YAML.** `country: NO` sem aspas é lido pelo YAML como `false`. `sources.yaml` recusa país booleano com mensagem que pede aspas, em vez de "país 'False' fora da ISO 3166-1".

Compatibilidade: nenhum campo de `RawRecord`, `Observation` ou da saída muda, e `SCHEMA_VERSION` continua `1.0.0`. Um adaptador que já cumpria a spec 002 com valores convertidos continua válido. O único comportamento novo visível é que registros inválidos são recusados mais cedo e com outra mensagem.

### R3. Amostras e testes

- Cada fonte tem em `tests/fixtures/<id>/` um trecho pequeno do arquivo real, com os mesmos nomes de arquivo de `RESOURCES` e menos de 20 KB no total. ZIPs são remontados só com as linhas copiadas.
- `tests/fixtures/ATRIBUICAO.md` lista, por fonte, licença, origem e trecho copiado.
- Cada adaptador tem teste de `parse` sobre a amostra com os registros esperados escritos à mão, teste de cada regra de R1.1 a R1.5 que se aplica a ele e teste de formato inesperado (`FormatError`).
- Um teste percorre todas as fontes com adaptador de `sources.yaml` e, para cada uma, roda `fetch` contra o servidor local (R2.5) e `ingest --offline` sobre o cache resultante.
- Os testes nunca acessam a rede (spec 002, R7).

### R4. Download bloqueado

Em 2026-10-12, `www.ssa.gov` respondeu 403 a downloads automáticos, inclusive com `User-Agent` de navegador. Quando um download termina em HTTP 403, a mensagem de `fetch` diz que o servidor recusou o download automático e indica o caminho exato no cache onde gravar o arquivo baixado pelo navegador, para seguir com `--offline`. Nenhum contorno de bloqueio (troca de `User-Agent`, proxy) é feito.

### R5. CI

A CI ganha um passo que monta um cache com `tests/fixtures/`, roda `namesio run --offline` com o `sources.yaml` da raiz e confere que `by_country/` tem `FR`, `IE`, `NO` e `US`.

### R6. Desempenho com os dados reais

O lote inteiro, com os arquivos reais no cache, roda `namesio run --offline` dentro dos limites de R8 da spec 002 (menos de 10 minutos e menos de 4 GB). Medido num Apple M4 com 24 GB: 3.077.139 observações de 4 países, `run --offline` em 68 s com pico de 1,63 GB. O ZIP da SSA usado na medição foi um repack de espelho, porque o ZIP oficial não pôde ser baixado automaticamente (R4). A margem é suficiente; agregação fora da memória não entra nesta spec.

### R7. Fontes avaliadas e deixadas fora deste lote

| Instituto | Situação | Motivo e evidência |
|---|---|---|
| ONS (Inglaterra e País de Gales) | Adiada | OGL v3 (https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/livebirths/datasets/babynamesenglandandwalesbabynamesstatisticsboys). Um arquivo XLS (1996 a 2018) ou XLSX (2019 a 2025) por ano e sexo, que exige leitor de planilha. Cobre só parte do Reino Unido. |
| INE (Espanha) | Adiada | CC BY 4.0 no aviso legal (https://ine.es/dyngs/AYU/index.htm?cid=125). Tabelas em Excel; contagem de população com frequência de ao menos 20. |
| Statistics Canada | Adiada | Tabela 17-10-0147-01, CSV nacional de 1991 a 2025 (ZIP de 42 MB, CSV de 582 MB, 218.198 contagens, nomes sem acentos). Licença Statistics Canada Open Licence (https://www.statcan.gc.ca/en/reference/licence), fora da lista do ADR 0001. |
| Retraite Québec | Adiada | CC BY 4.0 no Données Québec (https://www.donneesquebec.ca/recherche/dataset/banque-de-prenoms-filles). Cobre só o Québec; marcadores `<5` e `.`; nomes sem acentos. |
| IBGE (Brasil) | Recusada | "Nomes no Brasil" não declara licença. A API devolve um nome ou um ranking por consulta, sem arquivo completo, e a do Censo 2010 publica nomes sem acentos (`JOSE`, `JOAO`). |
| Department of Internal Affairs (Nova Zelândia) | Não avaliada | O catálogo `catalogue.data.govt.nz` bloqueou o acesso automático; licença e formato não conferidos. |

## Critérios de aceite

1. `sources.yaml` tem as cinco fontes de R1, cada uma com licença da lista do ADR 0001, e `load_sources` o aceita.
2. Cada adaptador passa no teste de `parse` sobre a amostra real com os registros esperados escritos à mão, e cada particularidade de R1.1 a R1.5 tem teste.
3. Cada regra de R2.1 a R2.7 tem teste, inclusive: código de sexo fora do mapeamento, marcador de supressão desconhecido, `count` vazio numa fonte `births`, arquivo fora de `RESOURCES`, adaptador ausente com caminho esperado, adaptador quebrado e `country: NO` sem aspas.
4. `namesio run --offline` sobre um cache montado com `tests/fixtures/` gera `by_country/NO.csv` igual a valores escritos à mão, com sobrenomes `population` da edição 2025 e primeiros nomes `births` com `female_share`.
5. Um download que termina em 403 gera mensagem com o caminho do cache onde gravar o arquivo (R4).
6. A CI roda verde no pull request desta spec, com o passo de R5.
7. A medição de R6 é repetida com os arquivos reais e a linha de tempo e memória vai para a descrição do pull request.
8. Cada item da issue #8 está resolvido por um requisito desta spec, e a issue é fechada pelo pull request.

## Fora de escopo

- Fontes em planilha XLS ou XLSX (ONS, INE) e a escolha do leitor de planilha.
- Fontes que cobrem só parte de um país (ONS, Retraite Québec, Escócia, províncias) e a regra para combiná-las num país.
- Licenças fora da lista do ADR 0001 (Statistics Canada Open Licence).
- Atualização automática de edições: a URL do INSEE muda a cada edição anual e é trocada à mão no adaptador.
- Sobrenomes de outros países além da Noruega, transliteração e variantes (specs 004 e 005).
- Agregação fora da memória: R6 mostra que não é necessária neste lote.
