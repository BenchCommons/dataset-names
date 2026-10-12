# 0005. Leitor de planilhas: XLSX pela biblioteca padrão, XLS pelo xlrd 2.0.2

## Status

Aceito (2026-10-12)

## Contexto

Institutos de estatística publicam nomes em planilhas. O INE da Espanha publica os primeiros nomes em XLSX e os sobrenomes em XLS (spec 003b). A ONS publica um XLS por ano de 1996 a 2018 e um XLSX de 2019 em diante (spec 003c). O pipeline só lia texto (CSV, TXT, JSON) com a biblioteca padrão, e a spec 003 recusou dependência nova.

Os dois formatos são bem diferentes:

- **XLSX** é um ZIP com XML (Office Open XML). Ler valores de célula exige `xl/workbook.xml`, o arquivo de relações, `xl/sharedStrings.xml` e a aba. Isso cabe em cerca de 150 linhas com `zipfile` e `xml.etree.ElementTree.iterparse`, lendo linha a linha. Medido em 2026-10-12 sobre `nombres_por_edad_media.xlsx` do INE (2,5 MB, 63.454 linhas): 1,1 s e 29 MB de pico de memória.
- **XLS** é um documento composto OLE2 com registros BIFF8: setores encadeados por FAT e mini FAT, tabela de textos compartilhados com registros `CONTINUE` que cortam textos no meio, textos comprimidos ou em UTF-16, números em `RK` e `MULRK`. Reescrever isso é código binário delicado, sem nenhuma outra utilidade no projeto.

Opções avaliadas:

| Opção | XLSX | XLS | Dependências |
|---|---|---|---|
| `openpyxl` 3.1.5 | Sim | Não | `et-xmlfile`; última versão em 2024-06 |
| `pandas` | Via `openpyxl` | Via `xlrd` | `numpy` e mais; pesado para ler duas colunas |
| `python-calamine` | Sim | Sim | Extensão em Rust compilada por plataforma |
| `xlrd` 2.0.2 | Não (removido na 2.0) | Sim | Nenhuma; Python puro, licença BSD, versão 2.0.2 de 2025-06-14 |
| Leitor próprio de XLSX | Sim | Não | Nenhuma |

## Decisão

- O módulo `namescommons.spreadsheet` lê XLSX com a biblioteca padrão (`zipfile` e `iterparse`), em fluxo.
- XLS é lido com `xlrd`, fixado em `==2.0.2` em `pyproject.toml`. É a única dependência de runtime acrescentada.
- O formato é reconhecido pelos primeiros bytes do arquivo, e os dois caminhos devolvem valores do mesmo tipo (texto, inteiro, fração, booleano, vazio).
- Adaptadores não importam `xlrd` nem leem XML de planilha: usam só `namescommons.spreadsheet`.

## Consequências

- XLSX não depende de terceiros, e o pico de memória é o de uma linha mais os textos compartilhados.
- O `ElementTree` da biblioteca padrão não busca entidades externas, e o expat do Python 3.12 limita a expansão de entidades; por isso `defusedxml` não entra. Como defesa em profundidade, o leitor recusa com `FormatError` qualquer membro XML cujo prólogo contenha `<!DOCTYPE` ou `<!ENTITY`, inspecionando só os primeiros 64 KiB antes de repassar o fluxo ao parser.
- `xlrd` carrega o XLS inteiro na memória. Para o maior arquivo do INE (14,9 MB) o pico medido foi de 67 MB, muito abaixo do limite de 4 GB da spec 002 (R8).
- `xlrd` está em manutenção mínima: a 2.0.2 saiu quatro anos e meio depois da 2.0.1. A versão fixada evita mudança de comportamento silenciosa; se o projeto for abandonado, o XLS é um formato congelado, e trocar a implementação fica restrito a `namescommons.spreadsheet`.
- Só XLS gravado em documento composto (Excel 5 em diante) é reconhecido; XLS mais antigo, ODS e XLSB aparecem como erro de formato.
- Outra biblioteca de planilha só entra com novo ADR.
