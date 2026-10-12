# Amostras das fontes oficiais

Cada diretório guarda um trecho pequeno do arquivo real da fonte, só para os testes (spec 003, R3; spec 003b, R3). As linhas foram copiadas sem alteração. Os ZIPs foram remontados só com as linhas copiadas. As amostras do SSB são a resposta real da API para uma consulta restrita a poucos nomes e anos. As planilhas do INE mantêm os números de linha do arquivo real. `planilhas/tipos.xls` é sintética, para os testes do leitor de planilhas.

| Fonte | Licença | Origem | Trecho |
|---|---|---|---|
| `us-ssa-births` | public-domain | Social Security Administration (EUA), https://www.ssa.gov/oact/babynames/limits.html | 10 linhas de `yob1880.txt` e `yob2024.txt`, copiadas de um espelho do `names.zip` porque `www.ssa.gov` recusou o download automático |
| `fr-insee-births` | etalab-2.0 | Source : Insee, Fichier des prénoms, édition 2025, https://www.insee.fr/fr/statistiques/8595130 | cabeçalho e 10 linhas de `prenoms-2025-nat.csv` |
| `ie-cso-births` | CC-BY-4.0 | Central Statistics Office (Irlanda), tabelas VSA50 e VSA60, https://data.gov.ie/dataset/vsa50-boys-names-in-ireland-with-3-or-more-occurrences | cabeçalho e 6 linhas de cada CSV |
| `no-ssb-fornavn` | CC-BY-4.0 | Statistics Norway (SSB), tabela 10467, https://www.ssb.no/en/statbank/table/10467 | nomes 1NORA, 1Z3SE, 1KIM, 2KIM e 2JAKOB nos anos 1944, 1990 e 2025 |
| `no-ssb-etternavn` | CC-BY-4.0 | Statistics Norway (SSB), tabela 12891, https://www.ssb.no/en/statbank/table/12891 | sobrenomes HANSEN, DA-SILVA e ABDO nos anos 2020 e 2025 |
| `es-ine-residentes` | CC-BY-4.0 | Elaboración propia con datos extraídos del sitio web del INE: www.ine.es, Apellidos y nombres más frecuentes, datos a 01/01/2025, https://ine.es/dyngs/INEbase/operacion.htm?c=Estadistica_C&cid=1254736177009&menu=resultados&idp=1254735572981 | cabeçalho e 6 linhas de cada aba de `nombres_por_edad_media.xlsx` (XML original, textos compartilhados reindexados); cabeçalho e 9 linhas de `apellidos_frecuencia.xls`, regravadas em BIFF8 nas mesmas linhas e colunas |
