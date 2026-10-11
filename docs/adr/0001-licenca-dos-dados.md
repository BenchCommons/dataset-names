# 0001. Licença dos dados: CC BY 4.0 com fontes compatíveis

## Status

Proposto (2026-10-11)

## Contexto

O dataset combina nomes de várias fontes, cada uma com sua licença: domínio público (SSA e Census dos EUA), Open Government Licence (Reino Unido), Licence Ouverte (França), CC0 (Wikidata), CC BY e outras. As listas legadas (`first_names.all.txt`, `last_names.all.txt`) vieram de sites, gists e repositórios sem licença declarada.

Uma única fonte ShareAlike (CC BY-SA, ODbL) obrigaria o dataset inteiro a adotar a mesma licença. Uma fonte NonCommercial impediria o uso comercial do conjunto. O código continua sob Apache-2.0, que não se aplica bem a dados.

## Decisão

- Os dados publicados usam **CC BY 4.0**, em `DATA_LICENSE`. O código continua sob Apache-2.0.
- Uma fonte só entra se sua licença permitir redistribuição sob CC BY 4.0: domínio público, CC0, CC BY, OGL, Licence Ouverte e equivalentes.
- Fontes ShareAlike (CC BY-SA, ODbL), NonCommercial ou sem licença declarada são recusadas.
- Cada fonte aceita é registrada em `sources.yaml` com a licença e o texto de atribuição exigido. A página de atribuições é gerada a partir desse arquivo.
- As listas legadas não são ingeridas no dataset novo.

## Consequências

- Usuários podem usar o dataset, inclusive comercialmente, com atribuição.
- Algumas fontes ricas ficam de fora (OpenStreetMap e qualquer base ODbL), e o volume inicial é menor que o das listas legadas.
- Toda fonte nova exige verificação de licença antes do adaptador.
