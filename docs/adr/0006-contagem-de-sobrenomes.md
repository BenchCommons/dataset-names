# 0006. Contagem de sobrenomes: cada pessoa uma vez, pela posição transmitida

## Status

Aceito (2026-10-12)

## Contexto

Em países com mais de um sobrenome por pessoa, a fonte pode publicar várias contagens para o mesmo sobrenome. O INE da Espanha publica, para cada sobrenome, quantas pessoas o têm como primeiro apellido, como segundo e nos dois (spec 003b, R2.5). Quem tem o mesmo sobrenome nas duas posições aparece nas três colunas.

Há três leituras possíveis:

- **Soma das colunas.** Conta duas ou três vezes a mesma pessoa.
- **Portadores** (`1º + 2º - ambos`). É o número de pessoas que carregam o sobrenome em qualquer posição. Exige as três colunas publicadas, e a cauda tem `..` (menos de 5) no segundo apellido e no par. Além disso, somado entre sobrenomes, dá cerca de duas vezes a população, o que deixa `count` incomparável com o de países de sobrenome único.
- **Uma posição.** Conta cada pessoa uma vez, e a soma entre sobrenomes não passa da população.

A mesma questão volta em Portugal, na América Latina e em qualquer fonte que publique sobrenomes por posição.

## Decisão

- Em `count` de um sobrenome, cada pessoa conta uma vez, pela posição do sobrenome que a fonte usa para ordenar e cortar a lista e que é transmitida aos filhos. Na Espanha é o primeiro apellido.
- Contagens de portadores (em qualquer posição) nunca vão para `count`, nem a soma de posições.
- Se a fonte ordena por uma posição e transmite outra, a spec da fonte escolhe uma delas, registra o motivo e cita este ADR.
- A spec de cada fonte registra a posição usada.

## Consequências

- `count` de sobrenomes soma no máximo a população do país e fica comparável com o de países de sobrenome único (Noruega).
- Sobrenomes frequentes como segundo sobrenome e raros como primeiro ficam subestimados, e os que só aparecem como segundo ficam fora da fonte.
- Quem precisar do número de portadores consulta a fonte original; o dataset não o publica.
