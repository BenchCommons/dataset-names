# 0012. Transliteração para ASCII pelo ICAO Doc 9303, sem forma parcial

## Status

Aceito (2026-10-12)

## Contexto

O campo `ascii` (spec 001, R1) era a remoção de diacríticos em escrita latina e vazio nas demais. A revisão da spec 001 (issue #4) mostrou que ligaduras (`ǅ`), apóstrofos curvos e letras sem decomposição (`ə`, `ŋ`) eram descartados em silêncio, gerando formas que não correspondem ao nome. O agrupamento sem acento (ADR 0011) depende de `ascii`, e o Wikidata traz 14.682 nomes em cirílico e 2.645 em grego.

Uma biblioteca de transliteração genérica (Unidecode, ICU) seria dependência nova de runtime e daria resultados sem norma citável. O ICAO Doc 9303 (parte 3, seção 6, 8.ª edição, 2021) tem tabelas recomendadas para nomes em documentos de viagem: latim multinacional (tabela A) e cirílico (tabela B); não tem grego.

## Decisão

- Latim: NFKD, remoção das marcas combinantes e tabela fechada das letras sem decomposição, com os valores da tabela A do ICAO e uma letra só onde ela dá alternativa (`Ä` vira `a`, não `ae`), para que a forma sem acento das fontes que removem acentos coincida.
- Cirílico: tabela B do ICAO na forma padrão de cada letra, sem as exceções por língua (o dataset não sabe a língua do nome); `ь` omitido; `ћ`, ausente, vira `c` como o `ć` sérvio.
- Apóstrofos e hífens tipográficos viram `'` e `-`; ponto médio e caracteres de formatação são omitidos.
- Se algum caractere não tem transliteração, `ascii` fica vazio. Não se emite forma parcial.
- Grego, hangul, kana e as demais escritas ficam vazias até uma spec própria escolher a norma (ELOT 743 para o grego, romanização revisada para o coreano, Hepburn para o japonês).
- Nenhuma dependência nova.

## Consequências

- `ascii` passa a ter valor para nomes em cirílico (`Иванов` vira `ivanov`, `Мария` vira `mariia`), e a forma difere de transliterações de outras normas publicadas no Wikidata (`Mariya`).
- Nome latino com letra fora da tabela tem `ascii` vazio; `validate` deixa de exigir `ascii` em escrita latina e passa a exigir só caracteres ASCII sem maiúsculas.
- Ucraniano e sérvio ficam com a forma russa das letras comuns (`Г` vira `g`, não `h`), como o ICAO faz quando a língua não é conhecida.
- Mudar a norma de uma escrita muda valores de `ascii` e pede versão menor de `SCHEMA_VERSION`.
