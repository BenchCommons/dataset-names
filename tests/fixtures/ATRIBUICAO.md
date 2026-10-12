# Amostras das fontes oficiais

Cada diretório guarda um trecho pequeno do arquivo real da fonte, só para os testes (spec 003, R3). As linhas foram copiadas sem alteração. Os ZIPs foram remontados só com as linhas copiadas. As amostras do SSB são a resposta real da API para uma consulta restrita a poucos nomes e anos.

| Fonte | Licença | Origem | Trecho |
|---|---|---|---|
| `us-ssa-births` | public-domain | Social Security Administration (EUA), https://www.ssa.gov/oact/babynames/limits.html | 10 linhas de `yob1880.txt` e `yob2024.txt`, copiadas de um espelho do `names.zip` porque `www.ssa.gov` recusou o download automático |
| `fr-insee-births` | etalab-2.0 | Source : Insee, Fichier des prénoms, édition 2025, https://www.insee.fr/fr/statistiques/8595130 | cabeçalho e 10 linhas de `prenoms-2025-nat.csv` |
| `ie-cso-births` | CC-BY-4.0 | Central Statistics Office (Irlanda), tabelas VSA50 e VSA60, https://data.gov.ie/dataset/vsa50-boys-names-in-ireland-with-3-or-more-occurrences | cabeçalho e 6 linhas de cada CSV |
| `no-ssb-fornavn` | CC-BY-4.0 | Statistics Norway (SSB), tabela 10467, https://www.ssb.no/en/statbank/table/10467 | nomes 1NORA, 1Z3SE, 1KIM, 2KIM e 2JAKOB nos anos 1944, 1990 e 2025 |
| `no-ssb-etternavn` | CC-BY-4.0 | Statistics Norway (SSB), tabela 12891, https://www.ssb.no/en/statbank/table/12891 | sobrenomes HANSEN, DA-SILVA e ABDO nos anos 2020 e 2025 |
| `nz-dia-births` | CC-BY-4.0 | Department of Internal Affairs (Nova Zelândia), Baby Name popularity over time, https://catalogue.data.govt.nz/dataset/baby-name-popularity-over-time | cabeçalho e 18 linhas de `baby-names-1900-to-2025.csv`, bytes copiados sem alteração (inclusive os acentos em CP437 e Latin-1 e os nomes corrompidos na origem), baixado pelo navegador porque o catálogo recusa o download automático |
