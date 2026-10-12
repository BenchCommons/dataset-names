# 003b. Fontes em planilha: leitor de XLS e XLSX e INE

Parte do [roadmap](../ROADMAP.md). Depende da [spec 003](../003-fontes-oficiais/spec.md), cujo contrato do adaptador (R2) vale aqui sem mudança. Licença dos dados: [ADR 0001](../../adr/0001-licenca-dos-dados.md). Valores suprimidos: [ADR 0002](../../adr/0002-valores-suprimidos.md). Leitor de planilha: [ADR 0005](../../adr/0005-leitor-de-planilhas.md). Contagem de sobrenomes: [ADR 0006](../../adr/0006-contagem-de-sobrenomes.md). Pendência herdada: issue #13.

Status: Implementada e mesclada (PR #27, 2026-10-12).

## Por quê

A spec 003 deixou de fora os institutos que publicam nomes só em planilha (R7). O INE da Espanha é o maior deles: todos os primeiros nomes e sobrenomes de residentes com frequência de ao menos 20, com licença CC BY 4.0. Sem um leitor de planilha, a Espanha fica fora do dataset, e a spec 003c (ONS, Inglaterra e País de Gales) também não anda, porque a ONS publica um XLS ou XLSX por ano.

Esta spec entrega o leitor comum de XLS e XLSX e a fonte nacional do INE. A ONS cobre só parte do Reino Unido e depende da regra de fontes subnacionais, que é da spec 003c; daqui ela só herda o leitor.

## Requisitos

### R1. Leitor de planilha

Módulo `namescommons.spreadsheet`, usado por adaptadores de fontes em planilha.

- **R1.1 Interface.** `sheet_names(path) -> list[str]` devolve as abas na ordem do arquivo. `rows(path, sheet) -> Iterator[tuple[int, list]]` devolve `(número da linha, valores)` de cada linha não vazia, com o número da linha como o Excel mostra (a partir de 1) e os valores na posição da coluna (A = 0). Uma aba fora de `sheet_names` levanta `FormatError` com o nome pedido e a lista das abas.
- **R1.2 Formato pelo conteúdo.** O formato é reconhecido pelos primeiros bytes, não pela extensão: `PK\x03\x04` é XLSX (ZIP do Office Open XML) e `D0 CF 11 E0` é XLS (documento composto do Excel, da versão 5 em diante). Outro conteúdo, inclusive uma página HTML de erro gravada no lugar do arquivo, levanta `FormatError`.
- **R1.3 Valores iguais nos dois formatos.** Texto vira `str` sem alteração, número inteiro vira `int`, número com fração vira `float`, booleano vira `bool` e célula vazia vira `None`. Valores `None` no fim da linha são cortados, e linhas sem nenhum valor são puladas. Datas chegam como o número de série do Excel (nenhuma fonte de nomes usa datas em célula); a célula XLSX de tipo `d` (data ISO 8601, rara) não é aceita e levanta `FormatError` com o tipo. Em células mescladas, o valor fica só na célula do canto superior esquerdo, e as demais chegam vazias (`None`), como estão gravadas no arquivo. Célula com erro de fórmula (`#N/A`, `#REF!`) levanta `FormatError` com a aba e a referência da célula.
- **R1.4 XLSX com a biblioteca padrão.** O XLSX é lido com `zipfile` e `xml.parsers.expat` com `xml.etree.ElementTree.TreeBuilder`, em eventos como o `iterparse`, linha a linha, sem carregar a aba inteira na memória. São aceitos os tipos de célula `s` (texto compartilhado, inclusive com trechos de formatação; o texto fonético `rPh` é ignorado), `inlineStr`, `str`, `n` (ou sem tipo), `b` e `e`. A aba é localizada pelo nome em `xl/workbook.xml` e pelo alvo em `xl/_rels/workbook.xml.rels`. Cada linha lida sai da árvore XML, e a memória fica plana na aba inteira. Viram `FormatError`, com o arquivo e a aba ou a célula: membro XML com DTD no prólogo (`<!DOCTYPE` ou `<!ENTITY` antes do elemento raiz, conferido nos primeiros 64 KiB sem perder a leitura em fluxo; prólogo maior que isso também é recusado; o próprio parser expat também recusa DTD, em qualquer codificação), membro cujo prefixo não é UTF-8 nem UTF-16 válido (inclui UTF-32 e EBCDIC) ou cuja declaração XML pede codificação diferente de UTF-8 e UTF-16, membro do ZIP ausente (inclusive a aba apontada pelas relações), membro que descompacta mais de 1 GiB ou mais de 1 MiB com taxa de compressão acima de 100:1, referência de célula malformada ou além da coluna `XFD` (16.384 colunas), número de linha não numérico e índice de texto compartilhado que não é inteiro ou está fora da tabela.
- **R1.5 XLS com `xlrd` fixado.** O XLS é lido com `xlrd` 2.0.2 ([ADR 0005](../../adr/0005-leitor-de-planilhas.md)), única dependência nova de runtime. Arquivo XLS que `xlrd` não consegue abrir levanta `FormatError` com a mensagem original.
- **R1.6 Contagem em célula.** `cell_count(value, missing=(), field="contagem") -> int | None` converte uma célula numa contagem pelo mesmo critério de `parse_count` (spec 003, R2.2): `int` não negativo passa, `float` com fração, negativo ou `bool` é `FormatError`, texto passa por `parse_count` com os marcadores de `missing`, e célula vazia só é aceita se `""` estiver em `missing`.

O que a spec 003c vai precisar do leitor, conferido em 2026-10-12 nos arquivos reais da ONS de 2025 (`2025boysbabynames.xlsx`, 11 abas, 233 KB) e de 2018 (`2018boysnames.xls`, 774 KB): várias abas por arquivo escolhidas pelo nome, cabeçalho em linhas variáveis e marcadores de texto em células numéricas. R1.1, R1.3 e R1.6 cobrem esses casos; a regra subnacional e o adaptador da ONS ficam na 003c.

### R2. Fonte do INE

Uma entrada em `sources.yaml` e um adaptador em `src/namescommons/adapters/es_ine_residentes.py`. Números medidos nos arquivos reais em 2026-10-12, edição de 01/01/2025 publicada em 23/04/2026.

| `id` | Instituto | País | `kind` | `count_type` | Ano | Supressão (`suppression`) | Recursos e formato | Tamanho medido | Contagens |
|---|---|---|---|---|---|---|---|---|---|
| `es-ine-residentes` | INE, Apellidos y nombres más frecuentes | ES | given e family | population | 2025 (01/01/2025) | frequência menor que 20 não publicada (20) | `nombres_por_edad_media.xlsx` (abas `Hombres` e `Mujeres`) e `apellidos_frecuencia.xls` (abas `Apellidos >=100` e `Apellidos >=20 y <=99`) | 2,5 MB e 14,9 MB | 63.440 nomes (31.119 M, 32.321 F) e 86.512 sobrenomes |

URLs: `https://www.ine.es/daco/daco42/nombyapel/nombres_por_edad_media.xlsx` e `https://www.ine.es/daco/daco42/nombyapel/apellidos_frecuencia.xls`, listados na página de resultados https://ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736177009&menu=resultados&idp=1254735572981 como "Todos los nombres con frecuencia igual o mayor a 20 personas" e "Lista de apellidos con frecuencia igual o mayor a 20 personas".

Licença, conferida na página indicada:

| `id` | `license` | Evidência |
|---|---|---|
| `es-ine-residentes` | `CC-BY-4.0` | Aviso legal do INE: "La licencia de uso general a aplicar a la información estadística de este sitio web, salvo que se indique lo contrario, es la Creative Commons Reconocimiento 4.0 (CC BY 4.0)", com citação "Elaboración propia con datos extraídos del sitio web del INE: www.ine.es" e a data da última atualização: https://www.ine.es/dyngs/AYU/index.htm?cid=125 |

O rodapé de todas as páginas do INE, inclusive a página de resultados, tem um selo com a dica "Este sitio web y su contenido están bajo licencia CC BY-SA 4.0". O mesmo selo aponta para `creativecommons.org/licenses/by/4.0/` e mostra só os ícones CC e BY. Vale a cláusula do aviso legal sobre reutilização, por três motivos: ela é específica para a informação estatística, enquanto o selo descreve o site e seu conteúdo em geral; ela é o texto que o INE publica como condição de reutilização, com o modo de citar; e o próprio selo aponta para a CC BY 4.0. Se valesse a CC BY-SA 4.0, o ADR 0001 recusaria a fonte (ShareAlike obrigaria o dataset inteiro a adotar a mesma licença).

Particularidades que o adaptador trata:

- **R2.1 Uma fonte, dois arquivos.** Nomes e sobrenomes são ambos `population` do mesmo instituto e da mesma edição, por isso são uma fonte só (spec 003, R2.4 separa por `count_type`, não por `kind`). Duas fontes `population` da Espanha exigiriam `primary: true` em só uma (spec 001, R2), e a outra deixaria de contar.
- **R2.2 Só totais nacionais.** Os dois arquivos lidos têm só a frequência nacional. As tabelas por província (`nombres_mas_frecuentes.xlsx`, `apellidos_mas_frecuentes.xls`), por década e por nacionalidade não são lidas.
- **R2.3 Ano da edição.** O ano vem da frase "Datos procedentes de Censos de población anuales a fecha 01/01/2025", acima do cabeçalho de cada aba (linha 2 no XLSX, linha 3 no XLS). Aba sem essa frase acima do cabeçalho levanta `FormatError`. Todas as abas dos dois arquivos (`Hombres`, `Mujeres` e as duas de sobrenomes) precisam ter o mesmo ano; se diferirem, `parse` levanta `FormatError` antes de emitir qualquer registro, com o ano de cada aba. Pela regra de `population` da spec 001 (R3.3), o país usa só a edição mais recente da fonte: se o INE atualizasse um arquivo antes do outro, os registros do arquivo antigo perderiam a contagem sem aviso (cerca de 86 mil sobrenomes).
- **R2.4 Nomes por sexo.** A aba `Hombres` dá `M` e `Mujeres` dá `F`, por mapeamento explícito (`parse_code`); outra aba é `FormatError`. Colunas: `Orden`, `Nombre`, `Frecuencia`, `Edad Media (*)`, com o cabeçalho na linha 7; a idade média é ignorada.
- **R2.5 Sobrenomes pelo primeiro apellido** ([ADR 0006](../../adr/0006-contagem-de-sobrenomes.md)). A planilha traz três contagens: pessoas com o sobrenome como primeiro apellido (`Apellido 1º`), como segundo (`Apellido 2º`) e nos dois (`Ambos apellidos`); quem tem o mesmo sobrenome nas duas posições está nas três colunas. Para os sobrenomes da Espanha, `count` é o número de residentes com o sobrenome como **primeiro** apellido. É a posição pela qual o INE ordena e corta a lista (frequência de ao menos 20 no primeiro apellido) e a que se transmite aos filhos, nunca está suprimida, e conta cada pessoa uma vez. O número de portadores seria `Apellido 1º + Apellido 2º - Ambos apellidos`, mas o segundo apellido e o par trazem `..` (menos de 5) em boa parte da cauda, e a conta não fecha ali; por isso o número de portadores não vai para `count`. Cabeçalho nas linhas 4 e 5 (`Apellido 1º` sobre `Total` na coluna C). As colunas F e G, ocultas na planilha e com o valor auxiliar `9999999`, são ignoradas.
- **R2.6 Grafia.** Nomes e sobrenomes vêm em maiúsculas, sem acentos e sem trema, com `Ñ`, `Ç`, apóstrofo e `·` (`uniform_case: true`). O INE normaliza a grafia antes de contar (notas metodológicas `nota_nombres.pdf` e `nota_apellidos.pdf`): tira acentos e trema, e nos sobrenomes descarta as partículas copulativas `Y` e `I` que às vezes separam os dois apellidos (`Y GARCIA` é contado em `GARCIA`); as demais partículas ficam (`DE LA TORRE` e `TORRE` são sobrenomes distintos). O adaptador usa a grafia publicada, sem tentar recuperar os acentos.
- **R2.7 Supressão.** Os arquivos não publicam nomes abaixo de 20 pessoas; o limite fica em `suppression: 20`. Na coluna lida, `..` é o único marcador aceito e, se aparecer, a célula é omitida (ADR 0002); outro texto é `FormatError`.

### R3. Amostras e testes

- `tests/fixtures/es-ine-residentes/` tem os dois arquivos com os mesmos nomes de `RESOURCES`, menos de 20 KB no total, remontados só com o cabeçalho e linhas copiadas do arquivo real: o XLSX com a mesma estrutura de abas e de textos compartilhados, o XLS em BIFF8 com as mesmas abas. O gerador usa `xlwt` só no momento de montar a amostra; `xlwt` não é dependência do projeto.
- `tests/fixtures/ATRIBUICAO.md` ganha a linha da fonte.
- O leitor tem testes sobre as duas amostras e sobre planilhas pequenas montadas no teste para cada caso de R1.2 a R1.6 (tipos de célula, linhas e colunas esparsas, aba ausente, erro de fórmula, conteúdo que não é planilha).
- O adaptador tem teste de `parse` sobre a amostra com os registros esperados escritos à mão, teste de R2.3 a R2.7 e teste de formato inesperado.
- O teste da spec 003 que percorre todas as fontes de `sources.yaml` (fetch no servidor local e `ingest --offline`) passa a incluir a fonte nova sem mudança.
- Os testes nunca acessam a rede.

### R4. CI

O passo da CI das fontes oficiais (spec 003, R5) passa a conferir também `by_country/ES.csv`.

### R5. Desempenho

A fonte do INE com os arquivos reais no cache roda `namescommons run --offline` dentro dos limites de R8 da spec 002 (menos de 10 minutos e menos de 4 GB). Medido num Apple M4 com 24 GB, com os arquivos baixados do INE em 2026-10-12: 149.952 observações, `run --offline` em 16,6 s com pico de 332 MB (com a conferência de edição de R2.3). Só a leitura, que o `xlrd` faz carregando o XLS inteiro: `apellidos_frecuencia.xls` em 1,6 s com pico de 67 MB, e `nombres_por_edad_media.xlsx` em 1,2 s com pico de 33 MB. Somadas ao lote da spec 003 (R6: 3.077.139 observações, 68 s, 1,63 GB), as 150 mil observações da Espanha deixam a margem de R8 folgada.

### R6. Outras fontes avaliadas

| Instituto | Situação | Motivo e evidência |
|---|---|---|
| ONS (Inglaterra e País de Gales) | Spec 003c | OGL v3. Cobre só parte do Reino Unido; a regra para fonte subnacional é da 003c (issue #14). O leitor desta spec abre os arquivos de 2018 (XLS) e 2025 (XLSX). |
| INE, nomes de recém-nascidos (`nomnac24.xlsx`) | Fora | Só os 100 nomes mais frequentes do país por ano (desde 2002), não a distribuição completa. Uma fonte `births` truncada no topo distorceria `rank` e `female_share`. |
| DVV (Finlândia), nomes no sistema de informação populacional | Adiada (#25) | XLSX no avoindata.fi com primeiros nomes (5 ou mais) e sobrenomes (20 ou mais) de cidadãos vivos. Licença não declarada no recurso; precisa ser conferida antes do adaptador. |
| Statbel (Bélgica), primeiros nomes da população e de recém-nascidos | Adiada (#26) | Dados abertos por município; formato e licença do arquivo nacional não conferidos. |

## Critérios de aceite

1. `sources.yaml` tem `es-ine-residentes` com `CC-BY-4.0`, `primary: true`, `suppression: 20` e `uniform_case: true`, e `load_sources` o aceita.
2. `rows` e `sheet_names` devolvem os mesmos valores (tipos de R1.3) para a amostra XLSX e para a amostra XLS do INE, conferidos contra valores escritos à mão.
3. Cada regra de R1.1 a R1.6 tem teste, inclusive: aba ausente com a lista das abas, arquivo HTML no lugar da planilha, texto compartilhado com formatação e com `rPh`, célula `inlineStr`, linha esparsa, erro de fórmula e contagem fracionária.
4. O adaptador passa no teste de `parse` sobre a amostra real com os registros esperados escritos à mão, e cada particularidade de R2.3 a R2.7 tem teste.
5. `namescommons run --offline` sobre um cache montado com `tests/fixtures/` gera `by_country/ES.csv` igual a valores escritos à mão, com nomes e sobrenomes `population` de 2025.
6. A CI roda verde no pull request desta spec, com o passo de R4.
7. A medição de R5 com os arquivos reais vai para a descrição do pull request.
8. `xlrd` entra em `pyproject.toml` com versão fixada (`==2.0.2`), justificada no ADR 0005, e o `uv.lock` é atualizado.
9. As fontes adiadas de R6 viram issues, e a issue #13 é fechada pelo pull request.

## Fora de escopo

- O adaptador da ONS e a regra para fontes subnacionais (spec 003c, issue #14).
- Tabelas do INE por província, década de nascimento e nacionalidade, e os nomes de recém-nascidos (R6).
- Formatos de planilha além de XLS e XLSX: ODS, XLSB e XLS anterior ao Excel 5.
- Conversão de datas em célula e avaliação de fórmulas: o leitor devolve o valor guardado.
- Atualização automática de edições: as URLs do INE não mudam entre edições, e o ano vem do conteúdo (R2.3).
