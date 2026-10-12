# Amostras das fontes oficiais

Cada diretório guarda um trecho pequeno do arquivo real da fonte, só para os testes (spec 003, R3). As linhas foram copiadas sem alteração. Os ZIPs foram remontados só com as linhas copiadas. As amostras do SSB são a resposta real da API para uma consulta restrita a poucos nomes e anos.

| Fonte | Licença | Origem | Trecho |
|---|---|---|---|
| `us-ssa-births` | public-domain | Social Security Administration (EUA), https://www.ssa.gov/oact/babynames/limits.html | 10 linhas de `yob1880.txt` e `yob2024.txt`, copiadas de um espelho do `names.zip` porque `www.ssa.gov` recusou o download automático |
| `fr-insee-births` | etalab-2.0 | Source : Insee, Fichier des prénoms, édition 2025, https://www.insee.fr/fr/statistiques/8595130 | cabeçalho e 10 linhas de `prenoms-2025-nat.csv` |
