# 005. Variantes

Parte do [roadmap](../ROADMAP.md). Depende da [spec 003](../003-fontes-oficiais/spec.md) e da [spec 004](../004-wikidata/spec.md). Esquema: [spec 001](../001-esquema/spec.md). Decisões: [ADR 0010](../../adr/0010-regras-de-agrupamento.md) (regras de agrupamento), [ADR 0011](../../adr/0011-correspondencia-sem-acento.md) (correspondência sem acento), [ADR 0012](../../adr/0012-transliteracao-ascii.md) (transliteração para ASCII). Pendências herdadas: issues #4 e #31.

Status: Em implementação.

## Por quê

A spec 001 deixou três campos para esta spec: `ascii` (só remoção de diacríticos em escrita latina, vazio nas demais), `group_id` (sempre vazio) e a forma de exibição (`name`) do índice, escolhida somando contagens de tipos e edições diferentes. A revisão da 001 (issue #4) apontou falhas em `detect_script` (`々`, `ー` e latim de largura total viram `Zzzz`; nome japonês com kanji e kana vira `Hira`), em `ascii_form` (ligaduras e dígrafos, apóstrofo curvo descartado, `ə` e `ŋ` somem) e na capitalização das fontes de caixa uniforme (`Maria Del Carmen`, `Joana D'Arc`, `Van Der Berg`).

As fontes oficiais da Statistics Canada, do INE e da SSA publicam os nomes sem acento (`MARIE-EVE`, `JOSEE`, `JOSE`), e o Wikidata e o INSEE os publicam com acento (`Marie-Ève`, `José`). Sem agrupamento, o mesmo nome aparece em linhas sem relação entre si. A spec 004 gravou as ligações do Wikidata (`variant_links`), mas deixou para esta spec decidir quais delas juntam nomes e quais os separam.

## Requisitos

### R1. Escrita (`script`)

`detect_script` continua devolvendo o código ISO 15924 predominante entre as letras (spec 001, R1), com estas correções:

- **R1.1** Letras de largura total ou meia largura (`Ａ`, `ｱ`) contam pela escrita da letra (`Latn`, `Kana`).
- **R1.2** `々` (marca de iteração) conta como `Hani`. `ー` (marca de som longo) e `ゝ`, `ゞ`, `ヽ`, `ヾ` não contam: herdam a escrita das letras vizinhas.
- **R1.3** Nome cujas letras são só de `Hani`, `Hira` e `Kana`, com pelo menos uma de `Hira` ou `Kana` e pelo menos duas dessas três, é `Jpan` (`さくら子`, `ゆかり`/`ユカリ` misturados). Nome com `Hang` e `Hani` e nenhuma outra é `Kore`.
- **R1.4** A tabela de escritas cobre também as que apareceram como `Zzzz` nos dados reais (medição de 2026-10-12 sobre o lote completo, 100 nomes): oriá (`Orya`), batak (`Batk`), ol chiki (`Olck`), brahmi (`Brah`), fenício (`Phnx`), siríaco (`Syrc`), tifinagh (`Tfng`), gótico (`Goth`), cherokee (`Cher`), silabário canadense (`Cans`), mandaico (`Mand`), copta (`Copt`), rúnico (`Runr`), warang citi (`Wara`), meetei mayek (`Mtei`), syloti nagri (`Sylo`), hieróglifos egípcios (`Egyp`), thaana (`Thaa`), n'ko (`Nkoo`) e vai (`Vaii`). Letra de escrita fora da tabela continua `Zzzz`.

### R2. Forma ASCII (`ascii`)

`ascii` é a transliteração do nome para ASCII em minúsculas, caractere a caractere, pelo método do ADR 0012:

- **R2.1 Latim.** Decomposição NFKD (ligaduras e dígrafos de compatibilidade como `ǅ`, `ﬁ` e letras de largura total viram letras simples), remoção das marcas combinantes e a tabela de letras sem decomposição: `ß` `ss`, `ẞ` `ss`, `ø` `o`, `æ` `ae`, `œ` `oe`, `đ` `d`, `ð` `d`, `ł` `l`, `þ` `th`, `ı` `i`, `ħ` `h`, `ŧ` `t`, `ŋ` `n`, `ə` `e`, `ɛ` `e`, `ɔ` `o`, `ɣ` `g`, `ʙ` `b`. Os valores seguem a tabela A da seção 6 do ICAO Doc 9303 (parte 3, 8.ª edição, 2021) onde ela tem a letra, com a forma de uma letra só onde ela dá alternativa (`Ä` "AE or A" vira `a`), e as letras de alfabetos africanos ausentes do ICAO (`ə`, `ɛ`, `ɔ`, `ɣ`) usam a vogal ou consoante latina de mesma base.
- **R2.2 Cirílico.** A tabela B da mesma seção do ICAO Doc 9303, na forma padrão de cada letra (sem as exceções por língua, porque o dataset não sabe a língua do nome): `ж` `zh`, `х` `kh`, `ц` `ts`, `ч` `ch`, `ш` `sh`, `щ` `shch`, `ъ` `ie`, `ы` `y`, `э` `e`, `ю` `iu`, `я` `ia`, `ё` `e`, `й` `i`, `є` `ie`, `ї` `i`, `ђ` `d`, `ѕ` `dz`, `ј` `j`, `љ` `lj`, `њ` `nj`, `ќ` `k`, `ў` `u`, `џ` `dz`, `ґ` `g`, `ғ` `g`, `һ` `c`, `ѫ` `u`, `ѵ` `y` e as letras restantes do russo como na tabela. `ь` não tem transliteração e é omitido. `ћ`, ausente da tabela, vira `c`, como `ć` do alfabeto latino sérvio que lhe corresponde.
- **R2.3 Pontuação do nome.** Espaço, hífen e apóstrofo reto ficam. Apóstrofos tipográficos e modificadores (`’`, `‘`, `ʼ`, `ʻ`, `ʹ`, `ʾ`, `ʿ`, `` ` ``, `´`) viram `'`. Hífens e travessões Unicode (`‐`, `‑`, `‒`, `–`) viram `-`. O ponto médio (`·`, do catalão `l·l`) e caracteres de formatação (categoria `Cf`, como o ZWJ) são omitidos.
- **R2.4 Sem transliteração.** Se algum caractere não tem transliteração por R2.1 a R2.3 (letra de outra escrita, letra latina fora da tabela), `ascii` fica vazio: nunca se emite uma forma parcial. Grego, hangul, kana e as demais escritas ficam vazias por enquanto (issue de acompanhamento).
- **R2.5 Validação.** `validate` deixa de exigir `ascii` não vazio em escrita latina e passa a exigir que `ascii` só tenha caracteres ASCII sem maiúsculas.

### R3. Capitalização das fontes de caixa uniforme

Quando a fonte tem `uniform_case: true` (spec 002, R1.3), depois da capitalização por palavra:

- **R3.1** Palavra que não é a primeira do nome, separada por espaço, e que é uma das partículas `da`, `das`, `de`, `del`, `della`, `der`, `den`, `des`, `di`, `do`, `dos`, `du`, `van`, `von`, `y` vai para minúsculas: `Maria del Carmen`, `Van der Berg`, `Alves da Silva`, `Gabriel y Galan`.
- **R3.2** Os artigos `la`, `las`, `le`, `los` vão para minúsculas só logo depois de uma partícula de R3.1: `Abel de la Cruz`, `De la de las Heras`. Isolados ficam capitalizados, porque também são nomes (`Jia Le`, medido no INE).
- **R3.3** Palavra que não é a primeira e começa por `d'` ou `l'` fica com o prefixo em minúsculas e a letra seguinte em maiúscula: `Joana d'Arc`, `Francesc d'Assis`. Na primeira palavra o prefixo continua maiúsculo (`D'Arcy`).
- **R3.4** Partes ligadas por hífen não mudam (`Marie-Ève`, `Jean-De-Dieu` continua como a capitalização por palavra o deixa).
- **R3.5** Fontes com `uniform_case: false` continuam com a caixa publicada (`Da Silva` do Wikidata não muda).

### R4. Forma de exibição (`name` agregado)

A forma de exibição deixa de somar contagens de tipos, edições ou fontes que a agregação não usa (spec 001, R1.3 e R3.3). Entre as formas de um mesmo `name_key`:

- **R4.1 Caixa publicada primeiro.** Se alguma observação vem de fonte com `uniform_case: false`, só as formas dessas observações concorrem; a capitalização gerada pelo pipeline nas fontes de caixa uniforme só vale quando não há outra.
- **R4.2 Por país** (`by_country`): vence a forma de maior soma de `count` entre as observações contadas na linha do país (as do `count_type`, da fonte `primary` e da edição escolhidos por R3.3 da spec 001); empate ou sem contagem, a forma com mais observações no país; persistindo, a menor em ordem de código Unicode.
- **R4.3 No índice** (`given_names` e `family_names`): vence a forma que é a exibida em mais países (contando só os países em que a forma exibida vem de fonte de caixa publicada, ou todos se R4.1 não restringiu); empate, a forma com mais observações; persistindo, a menor em ordem de código Unicode. Nenhuma contagem é somada entre países.
- **R4.4 Deduplicação.** O índice continua com uma linha por `name_key` (spec 001, R3.2): formas que diferem só na caixa (`Jo-Anne` e `Jo-anne`, `McKenzie` e `Mckenzie`) já são a mesma linha, e R4 decide qual forma ela mostra. Formas com `name_key` diferentes (`Marie-Eve` e `Marie-Ève`) continuam linhas próprias e são deduplicadas pelo `group_id` (R5), sem fundir contagens.

### R5. Agrupamento de variantes (`group_id`)

Cada linha de `given_names` e `family_names` recebe `group_id`. O agrupamento é determinístico, por `kind`, sobre o grafo cujos nós são os pares (`kind`, `name_key`) com observação, conforme o ADR 0010:

- **R5.1 Junção pela chave.** Uma ligação de `variant_links` se liga às observações só por (`kind`, `name_key`) e (`target_kind`, `target_name_key`), nunca pelo texto de `name`: a ligação pode trazer uma forma que difere em caixa da forma exibida (`McKenzie` na ligação, `Mckenzie` no índice). Ligação com uma ponta sem observação (por exemplo, transliteração sem fonte que a ateste, 30.649 das 36.909 medidas) é ignorada. A direção publicada não importa: toda ligação usada é tratada como não dirigida.
- **R5.2 Tipos diferentes nunca se juntam.** Ligação com `kind` diferente de `target_kind` (`family_name_identical`, e as poucas `said_to_be_the_same`, `other_gender` e `different_from` entre prenome e sobrenome) não junta nada. `group_id` é único dentro de cada `kind`.
- **R5.3 Fase 1, mesmo nome.** Juntam: `same_item` (rótulos nativos do mesmo item) e, só em sobrenomes, `other_gender` (`Иванов` e `Иванова`; P5278). Em prenomes, `other_gender` (P1560, `Paulo` e `Paula`) não junta: são nomes distintos, com `female_share` próprio.
- **R5.4 Fase 2, anexação inequívoca.** Calculada sobre os grupos da fase 1:
  - `transliteration`: o nó de destino se junta ao grupo de origem só se todas as ligações de transliteração que chegam a ele vêm do mesmo grupo da fase 1. Uma romanização compartilhada por nomes diferentes (`Chen` de `陈` e de `沈`) não junta nada. A transliteração que o Wikidata publica como qualificador de um rótulo é atribuída pela spec 004 a todos os rótulos do item; isso não muda o resultado, porque os rótulos do mesmo item e `kind` já estão no mesmo grupo pela fase 1, e o adaptador não é alterado.
  - Sem acento (ADR 0011): um nó latino atestado por fonte com `strips_accents: true` (R6) se junta aos nós do mesmo `kind` com o mesmo `ascii` (R2) só se todos eles estão no mesmo grupo da fase 1. `Marie-Eve` (CA) se junta a `Marie-Ève`; `Ines` (US), com `Inès` e `Inés` em grupos diferentes, não se junta a nenhum.
- **R5.5 Não juntam.** `said_to_be_the_same` (P460) não junta: o fecho transitivo dessas ligações forma um componente de 14.039 nomes mesmo com os cortes de R5.6 (medido nos dados reais, ADR 0010). Nomes que só diferem em acento, sem fonte que remove acentos, também não juntam.
- **R5.6 `different_from` separa.** Uma ligação `different_from` (P1889) entre dois nós proíbe que eles fiquem no mesmo grupo. As junções das fases 1 e 2 são aplicadas em ordem fixa (fase, depois os dois `name_key` em ordem de código Unicode), e a junção que poria no mesmo grupo dois nós proibidos é pulada.
- **R5.7 Identificador.** `group_id` é o menor `name_key` do grupo em ordem de código Unicode (`marie-eve` para `Marie-Eve` e `Marie-Ève`). Nome sem variante forma um grupo sozinho, e seu `group_id` é o próprio `name_key`. Sem `variant_links` (`build` sem `--links`), só a regra sem acento junta nomes.
- **R5.8 Medição.** No lote real completo de 2026-10-12 (fontes oficiais das specs 003, 003b, 003d e 003e mais o Wikidata, 1.008.182 nós), a simulação destas regras anexa 3.347 transliterações (816 ambíguas ficam de fora) e 14.394 nomes sem acento (2.883 ambíguos ficam de fora), pula 292 junções por `different_from` e forma 35.759 grupos com mais de um nome, o maior com 31 (um sobrenome coreano escrito com hanjas diferentes no mesmo item do Wikidata). Os números finais da implementação vão para o pull request.

### R6. Fontes que removem acentos (`strips_accents`)

`sources.yaml` ganha o campo opcional `strips_accents` (booleano, padrão `false`): a fonte publica os nomes sem acento por regra própria, e não porque os nomes não têm acento. Só entra com evidência registrada aqui:

| Fonte | Evidência |
|---|---|
| `ca-statcan-births` | Nota 7 da tabela 17-10-0147-01: os nomes são publicados sem acento (`MARIE-EVE`, `JOSEE`); medido: 0 de 18.999 nomes com caractere fora do ASCII |
| `es-ine-residentes` | Nota metodológica do INE (`nota_nombres.pdf`): "eliminando los acentos y permitiendo como caracteres válidos el apóstrofo y la cedilla, pero no la diéresis"; medido: 143.578 nomes, só `ñ`, `ç` e `·` fora do ASCII |
| `us-ssa-births` | Medido: 0 de 104.819 nomes com caractere fora do ASCII, inclusive os de origem espanhola e francesa (`Jose`, `Andre`, `Rene`) |

As demais fontes publicam acentos (INSEE, CSO, SSB, DIA da Nova Zelândia, Wikidata) e ficam com `false`.

### R7. Contratos e manifesto

- **R7.1** A spec 002 (R1) recebe uma nota: o contrato do adaptador tem a função opcional `links(files)`, definida pela spec 004 (R4.1).
- **R7.2** A spec 001 recebe notas em R3 e R5: a release pode trazer `variant_links.parquet` (spec 004, R4.6), `group_id` é preenchido por esta spec, e `ascii` segue o ADR 0012.
- **R7.3** A spec 002 (R2) recebe uma nota apontando para `strips_accents` (R6).
- **R7.4** A lista `sources` do `manifest.json` é a união das fontes das observações e das fontes das ligações.

### R8. Versão

`group_id` preenchido, `ascii` em cirílico, `Jpan` e `Kore` em `script` e a nova capitalização mudam valores das saídas sem remover nem renomear campo: `SCHEMA_VERSION` passa a `1.2.0` (spec 001, R5).

### R9. Desempenho e memória

- **R9.1** O agrupamento trabalha sobre os nós (`kind`, `name_key`), um `kind` por vez, com inteiros e as chaves que o índice já tem; não cria outra cópia das observações nem das ligações.
- **R9.2** `run --offline` com o lote real completo, e num único `run` com as 3 milhões de observações sintéticas de `tools/bench_pipeline.py` mais o Wikidata real, fica dentro de R8 da spec 002 (menos de 10 minutos e de 4 GB), e o pico de memória não passa do medido na master nas mesmas condições. Se passar, esta spec reduz o pico (issue #31). A medição vai para o pull request.

### R10. Testes e CI

- Testes sem rede, com tabelas pequenas escritas à mão e as amostras de `tests/fixtures/`.
- Cada item da issue #4 tem teste: empate e mistura de escritas, `Zzzz`, `々`, `ー`, latim de largura total, NFKD, apóstrofo curvo, `ə`, `ŋ`, partículas e `D'Arc`, e a forma de exibição que não soma tipos diferentes.
- O passo da CI que roda as fontes de `sources.yaml` sobre as amostras confere que `given_names.csv` tem `group_id` preenchido em todas as linhas.

## Critérios de aceite

1. `detect_script` devolve `Hani` para `佐々木`, `Kana` para `ユーリ`, `Latn` para `Ａｎｎａ`, `Jpan` para `さくら子`, `Kore` para `김金` e `Orya` para `ଦାସ`.
2. `ascii_form` devolve `dzenana` para `Ǆenana`, `o'brien` para `O’Brien`, `aliyev` para `Əliyev`, `ngozi` para `Ŋgozi`, `ivanov` para `Иванов`, `mariia` para `Мария`, `dokovic` para `Ђоковић`, `pelleja` para `Pel·leja` e vazio para `Μαρία` e para um nome latino com letra fora da tabela.
3. Com `uniform_case: true`, `JOANA D'ARC` vira `Joana d'Arc`, `MARIA DEL CARMEN` vira `Maria del Carmen`, `VAN DER BERG` vira `Van der Berg`, `DE LA DE LAS HERAS` vira `De la de las Heras`, `JIA LE` vira `Jia Le` e `D'ARCY` vira `D'Arcy`.
4. Uma tabela de teste em que a forma `A` tem mais nascimentos somados de vários anos num país e a forma `a'` tem mais pessoas vivas em outro país mostra que a forma de exibição não soma `births` com `population`, e que a forma publicada vence a capitalização gerada.
5. Uma tabela de teste com ligações escritas à mão produz os grupos esperados: `Marie-Eve` (CA) com `Marie-Ève`; `Иванов`, `Иванова` e `Ivanov` (transliteração inequívoca) num grupo; `Paulo` e `Paula` separados; `Chen` sem grupo com `陈` e `沈`; `Ines` sem grupo; um par `different_from` separado mesmo ligado por `same_item` a um terceiro nome; nada junta prenome com sobrenome; P460 não junta.
6. `run --offline` sobre as amostras grava `given_names.csv` e `family_names.csv` com `group_id` em todas as linhas, `manifest.json` com `schema_version` `1.2.0` e a lista de fontes com as das ligações.
7. `strips_accents` é aceito em `sources.yaml` só como booleano, e as três fontes de R6 o têm `true`.
8. A medição de R9 é feita com os arquivos reais e vai para a descrição do pull request.
9. A CI roda verde no pull request, que fecha a issue #4.

## Fora de escopo

- Transliteração de grego, hangul, kana, árabe, hebraico, han e das demais escritas (issue de acompanhamento).
- Fundir linhas do índice ou contagens de nomes com `name_key` diferentes.
- Agrupar cognatos (`John`, `Johann`, `Juan`) pela P460, e qualquer comunidade ou corte por tamanho sobre ela (ADR 0010).
- `group_id` em `by_country/<CC>.csv` e um arquivo com as junções aplicadas.
- Restaurar acentos nos nomes das fontes que os removem.
