# 0011. Nome sem acento só se junta ao acentuado quando a fonte remove acentos

## Status

Aceito (2026-10-12)

## Contexto

A Statistics Canada publica `MARIE-EVE` e `JOSEE` (nota 7 da tabela 17-10-0147-01), o INE remove acentos por norma ("eliminando los acentos", nota metodológica dos nomes) e a SSA não tem nenhum caractere fora do ASCII em 104.819 nomes. Os mesmos nomes aparecem com acento no Wikidata e no INSEE. Sem regra, `Marie-Eve` (CA) e `Marie-Ève` ficam em grupos diferentes (issue #4).

Juntar quaisquer dois nomes com a mesma forma sem acento erra em línguas em que o acento distingue nomes: `Đức` e `Đúc` em vietnamita, `Aleš` e `Alés`, `Abrahám` e `Ábrahám`. Esses pares vêm de fontes que publicam acentos, e a falta de acento num deles não é perda de informação.

## Decisão

- `sources.yaml` ganha o campo opcional `strips_accents` (padrão `false`). Ele só é `true` com evidência registrada na spec: documentação da fonte que diz que os acentos são removidos, ou medição no arquivo completo de que nenhum nome tem letra acentuada apesar de nomes de línguas que a usam.
- A correspondência sem acento só parte de um nome latino atestado por fonte com `strips_accents: true`. Ele se junta aos nomes do mesmo `kind` com o mesmo `ascii` (ADR 0012) apenas se todos esses nomes já estão no mesmo grupo (ADR 0010, fase 2).
- Nomes acentuados nunca se juntam entre si só por terem o mesmo `ascii`.
- Hoje: `ca-statcan-births`, `es-ine-residentes` e `us-ssa-births`.

## Consequências

- `Marie-Eve` e `Marie-Ève`, `Josee` e `Josée`, `Garcia` e `García` ficam no mesmo grupo; as contagens continuam em linhas separadas.
- Nome sem acento com mais de uma leitura acentuada em grupos diferentes (`Ines`: `Inès`, `Inés`) não se junta a nenhuma; medido na simulação: 2.883 casos contra 14.394 junções.
- O INE mantém `ñ` e `ç`; como `ascii` também os remove, `Begoña` do INE se junta a `Begona` quando esta é a única leitura, o que é aceito como variante.
- Se a SSA tiver nomes sem acento por escolha de quem registrou e não por limitação do sistema, a junção ainda liga grafias do mesmo nome; o custo de errar é baixo.
- Fonte nova que remove acentos precisa da evidência na spec para entrar na regra; sem ela, seus nomes ficam sem junção por acento.
