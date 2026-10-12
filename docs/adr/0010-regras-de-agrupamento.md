# 0010. Agrupamento de variantes em duas fases, sem a P460 e com a P1889 como corte

## Status

Aceito (2026-10-12)

## Contexto

A spec 005 preenche `group_id` (spec 001, R3.2) a partir da tabela `variant_links` (ADR 0009) e das próprias observações. O agrupamento precisa ser determinístico e explicável: quem lê `given_names.csv` deve conseguir dizer por que dois nomes estão no mesmo grupo.

O fecho transitivo das ligações publicadas pelo Wikidata não serve como grupo. Medido em 2026-10-12 sobre os nós com observação no lote real (811.117 nós do Wikidata):

- Com `same_item` e `transliteration`, o maior componente tem 1.124 nomes: romanizações como `Chen`, `Chan` e `Ang` são transliteração de vários caracteres han diferentes e os ligam entre si.
- Somando `said_to_be_the_same` (P460), o maior componente tem 15.892 nomes (de `Aadne` a `Zygmunt`), e 14.039 mesmo pulando as junções proibidas por `different_from` (P1889). A P460 liga cognatos de línguas diferentes, e nomes como `Elisa`, `Lisa` e `Ελισάβετ` têm mais de 500 ligações cada.
- Limitar a P460 a nomes com poucas ligações não estabiliza: com até 8 ligações o maior grupo tem 30 nomes e `Ivanov` fica sozinho; com até 16, o maior tem 2.976.

## Decisão

- Os nós são os pares (`kind`, `name_key`) com observação. As ligações se juntam aos nós pela chave, nunca pelo texto do nome, e são tratadas como não dirigidas. Ligação com ponta sem observação é ignorada.
- Prenome e sobrenome nunca se juntam; `group_id` é único dentro de cada `kind`.
- **Fase 1, mesmo nome:** `same_item` e, só em sobrenomes, `other_gender` (P5278: `Иванов` e `Иванова` são o mesmo sobrenome flexionado). Em prenomes, `other_gender` (P1560: `Paulo` e `Paula`) não junta.
- **Fase 2, anexação inequívoca,** calculada sobre os grupos da fase 1: a transliteração junta o destino ao grupo de origem só se todas as transliterações que chegam ao destino vêm do mesmo grupo; a regra sem acento (ADR 0011) junta um nome sem acento aos nomes com o mesmo `ascii` só se todos eles estão no mesmo grupo.
- `said_to_be_the_same` (P460) não junta. Ela continua em `variant_links` para quem quiser cognatos.
- `different_from` (P1889) proíbe que dois nós fiquem no mesmo grupo. As junções são aplicadas em ordem fixa (fase, depois os dois `name_key` em ordem de código Unicode); a que violaria a proibição é pulada.
- `group_id` é o menor `name_key` do grupo em ordem de código Unicode; nome sem variante é seu próprio grupo.
- A transliteração publicada como qualificador de um rótulo, que a spec 004 liga a todos os rótulos do item, não é restrita: os rótulos do mesmo item e `kind` já estão no mesmo grupo pela fase 1, e a fase 2 só olha para o grupo.

## Consequências

- Os grupos são pequenos (o maior, na simulação sobre o lote real, tem 31 nomes) e cada junção tem uma causa nomeável: mesmo item, mesmo sobrenome no outro gênero, transliteração não ambígua ou fonte que remove acentos.
- Cognatos (`John`, `Johann`, `Juan`) e grafias alternativas ligadas só pela P460 (`Ivanov` e `Iwanow`) ficam em grupos separados. Quem precisar delas usa `variant_links`.
- Romanizações ambíguas e nomes sem acento ambíguos (`Ines` entre `Inès` e `Inés`) ficam fora de qualquer grupo com variantes, o que perde junções corretas em troca de não criar erradas.
- `group_id` muda quando entra no grupo um nome com `name_key` menor; ele identifica o grupo dentro de uma release, não entre releases.
- Uma relação nova do Wikidata, ou outra fonte com `links`, só passa a juntar nomes com mudança desta decisão.
