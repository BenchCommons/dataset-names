# 0006. Nomes corrompidos na fonte são descartados, e só se recupera o que é inequívoco

## Status

Aceito (2026-10-12)

## Contexto

Algumas fontes publicam nomes com caracteres perdidos antes de o arquivo chegar ao dataset. O CSV do Department of Internal Affairs da Nova Zelândia (spec 003e) é o primeiro caso: acentos vêm em bytes de páginas de código diferentes no mesmo arquivo (`0x82` de CP437 e `0xE9` de Latin-1 para o mesmo `é`), e as vogais com macron do te reo Māori viram `?` ou bytes que nenhuma página de código lê como `ā` ou `ī`.

Ingerir esses nomes como vieram criaria formas falsas (`M?ia`, `KÅwhai`) que nunca foram registradas, com contagem e `female_share` próprios, e que a etapa de variantes (spec 005) agruparia com nomes reais por acaso. Adivinhar a letra perdida (`?` vira `ā`) também inventaria dado: o mesmo `?` substitui `ā` em `M?ia` e `ī` em `N?kau`, no mesmo arquivo. Decodificar com uma única página de código escolhida a dedo troca uma corrupção por outra (`Zoé` lido em CP437 vira `ZoΘ`).

## Decisão

- Um nome que, depois da decodificação, contém `?` ou U+FFFD (caractere de substituição) não entra no dataset: o adaptador não emite registro para a linha.
- Um byte só é traduzido para um caractere quando a leitura é inequívoca: uma página de código o lê como letra, as outras candidatas o leem como pontuação, símbolo ou nada, e os nomes do arquivo real em que ele ocorre confirmam a letra. A tradução fica numa tabela fechada no adaptador, com a evidência registrada na spec da fonte. Byte fora da tabela vira U+FFFD e cai na regra anterior.
- Se o arquivo inteiro for UTF-8 válido, ele é lido como UTF-8, e a tabela não se aplica.
- O adaptador conta as linhas descartadas, a soma das contagens delas e as formas distintas, e avisa no log ao fim do arquivo. A spec da fonte registra os números medidos no arquivo real.

## Consequências

- Nenhuma forma de nome que a fonte não registrou entra no dataset; a contagem do país perde as linhas descartadas (na Nova Zelândia, 13 de 74.019 linhas e 164 de 4.516.506 registros).
- Nomes com macron ficam de fora da fonte até que ela corrija o arquivo. Como um arquivo UTF-8 válido é lido sem tabela, a correção na origem passa a valer sem mudança de código.
- Uma edição nova com um byte desconhecido não quebra a ingestão: o nome é descartado e aparece no aviso, e quem atualiza a fonte decide se o byte merece entrar na tabela.
- Toda fonte nova precisa ter os bytes não ASCII inspecionados antes do adaptador.
