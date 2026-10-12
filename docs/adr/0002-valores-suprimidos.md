# 0002. Valores suprimidos pelas fontes são omitidos

## Status

Proposto (2026-10-12)

## Contexto

Institutos de estatística escondem contagens pequenas para proteger a privacidade. Cada um marca isso de um jeito: `<5` (Retraite Québec), `.` e `..` (Statistics Norway), célula vazia (CSO da Irlanda), ou simplesmente não publica a linha (SSA dos EUA, INSEE).

A spec 001 (R1.1) amarra contagem vazia a `count_type: attested`. Uma fonte `births` não pode emitir `count` vazio sem violar essa regra, e trocar o tipo linha a linha misturaria `attested` e `births` na mesma fonte, contra a regra de um `count_type` por fonte. Converter o marcador num número (zero, ou metade do limite) inventaria uma contagem que a fonte não publicou.

## Decisão

- O adaptador omite a célula suprimida ou ausente: nenhum registro é emitido para ela.
- O limite de supressão de cada fonte fica registrado em `suppression` de `sources.yaml`.
- O adaptador declara os marcadores que conhece; qualquer outro texto não numérico é erro de formato, e não zero.
- O pipeline recusa registro com `count` vazio numa fonte `births` ou `population`.

## Consequências

- Nenhuma contagem é inventada, e `count` e `rank` continuam somando só valores publicados.
- Um nome que aparece só como suprimido numa fonte não é atestado por ela. A lista de nomes perde a cauda rara dessas fontes; quem precisa do limite consulta `suppression`.
- Somas por série (`births` de vários anos) subestimam nomes raros, porque os anos suprimidos contam zero. Isso vale igualmente para todas as fontes.
- Uma fonte que muda o marcador de supressão quebra a ingestão com mensagem clara, em vez de produzir zeros silenciosos.
