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
- **Fase 1, mesmo item:** os itens se juntam só por `other_gender` em sobrenomes (P5278: `Иванов` e `Иванова` são o mesmo sobrenome flexionado); em prenomes, `other_gender` (P1560: `Paulo` e `Paula`) não junta. Cada nó entra no grupo dos itens de que é rótulo (por `same_item`, como origem de transliteração ou, em sobrenomes, `other_gender`) só se todos esses itens já são um grupo. Um rótulo homógrafo de itens diferentes fica sozinho: na primeira versão desta regra, que juntava por `same_item` direto, `장` ligava `张` e `蒋`, `진` ligava `陈`, `秦` e `真`, e 61 grupos de prenomes e 162 de sobrenomes misturavam itens diferentes (revisão do PR #38).
- **Fase 2, anexação inequívoca,** calculada sobre os grupos da fase 1: a transliteração junta o destino ao grupo de origem só se todas as transliterações que chegam ao destino vêm do mesmo grupo, se o destino não é rótulo homógrafo e se o destino não é já nome de outro grupo ou rótulo de outro item com um nome na escrita da origem (`見` -> `현` não entra no grupo de `玄`, de que `현` é rótulo; `Герман` -> `Herman` entra no grupo latino de `Herman` e `Hermanová` quando `Герман` é rótulo de um item só). Romanização de han, kana ou hangul nunca se anexa a nome de outro grupo ou item (leitura homófona: `suk`/`suková` e `术`, na segunda revisão do PR #38), e as transliterações de um grupo que chegam a dois ou mais grupos de outros nomes não se anexam (`Кінаш` -> `Kinach` e `Kinasz`). A regra sem acento (ADR 0011) junta um nome sem acento aos nomes com o mesmo `ascii` só se todos eles estão no mesmo grupo e se o próprio grupo do nome, quando tem outros nomes, é esse.
- `said_to_be_the_same` (P460) não junta. Ela continua em `variant_links` para quem quiser cognatos.
- `different_from` (P1889) proíbe que dois nós fiquem no mesmo grupo. As junções são aplicadas em ordem fixa (fase, depois os dois `name_key` em ordem de código Unicode); a que violaria a proibição é pulada.
- `group_id` é o menor `name_key` do grupo em ordem de código Unicode; nome sem variante é seu próprio grupo.
- A transliteração publicada como qualificador de um rótulo, que a spec 004 liga a todos os rótulos do item, não é restrita: os rótulos do mesmo item e `kind` já estão no mesmo grupo pela fase 1, e a fase 2 só olha para o grupo.

## Consequências

- Os grupos são pequenos (no lote real, o maior tem 18 nomes, todos rótulos do mesmo item) e cada junção tem uma causa nomeável: mesmo item, mesmo sobrenome no outro gênero, transliteração não ambígua ou fonte que remove acentos. Medido: 2.310 rótulos homógrafos sem ponte, 2.820 transliterações anexadas (1.305 ambíguas, 27 concorrentes, 9 de CJK para outro item e 2 em leque de fora), 14.136 nomes sem acento anexados (3.099 ambíguos de fora) e 241 junções puladas por `different_from`. Restam 87 grupos de prenomes e 59 de sobrenomes com rótulos de itens diferentes, quase todos o mesmo nome em itens duplicados de línguas diferentes ligados pela transliteração do cirílico (`Алексей` e `Aleksei`, `Омельчук` e `Omelczuk`).
- Cognatos (`John`, `Johann`, `Juan`) e grafias alternativas ligadas só pela P460 (`Ivanov` e `Iwanow`) ficam em grupos separados. Quem precisar delas usa `variant_links`.
- Romanizações ambíguas, rótulos homógrafos e nomes sem acento ambíguos (`Ines` entre `Inès` e `Inés`) ficam fora de qualquer grupo com variantes, o que perde junções corretas em troca de não criar erradas.
- `group_id` muda quando entra no grupo um nome com `name_key` menor; ele identifica o grupo dentro de uma release, não entre releases.
- Uma relação nova do Wikidata, ou outra fonte com `links`, só passa a juntar nomes com mudança desta decisão.
