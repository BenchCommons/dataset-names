# 0004. Statistics Canada Open Licence entra na lista de licenças aceitas

## Status

Aceito (2026-10-12). Amplia a lista de licenças do [ADR 0001](0001-licenca-dos-dados.md).

## Contexto

A tabela 17-10-0147-01 da Statistics Canada ("First names at birth by sex at birth, selected indicators") publica a frequência de cada primeiro nome por sexo e ano de 1991 a 2025, em nível nacional. É a única fonte nacional de nomes do Canadá avaliada até agora (spec 003, R7; issue #15).

A tabela é distribuída sob a Statistics Canada Open Licence (https://www.statcan.gc.ca/en/reference/licence, versão com "Date modified: 2025-07-10", lida em 2026-10-12). Essa licença não está na lista do ADR 0001, que aceita domínio público, CC0, CC BY, OGL, Licence Ouverte "e equivalentes" e recusa ShareAlike, NonCommercial e fontes sem licença. A pergunta é se ela permite redistribuir dados derivados sob CC BY 4.0.

Cláusulas relevantes, citadas da página da licença:

- **Concessão.** "Statistics Canada grants you a worldwide, royalty-free, non-exclusive licence to: use, reproduce, publish, freely distribute, or sell the Information; use, reproduce, publish, freely distribute, or sell Value-added Products; and, sublicence any or all such rights, under terms consistent with this licence."
- **Produto derivado.** "'Value-added Products' means any products you have produced by adapting or incorporating the Information, in whole or in part, in accordance with this licence." E: "Intellectual property rights [...] in Value-added Products, shall vest in you, in such person as you shall decide or as determined by law."
- **Atribuição.** "(b) Where any Information is contained within a Value-added Product, you shall include on such Value-added Product the following notice: Adapted from Statistics Canada, name of product, reference date. This does not constitute an endorsement by Statistics Canada of this product."
- **Condições de uso.** "In doing any of the above, you shall: reproduce the Information accurately; not use the Information in a way that suggests that Statistics Canada endorses you or your use of the Information; not misrepresent the Information or its source; use the Information in a manner that does not breach or infringe any applicable laws; not merge or link the Information with any other databases for the purpose of attempting to identify an individual person, business or organization; not present the Information in such a manner that gives the appearance that you may have received, or had access to, information held by Statistics Canada about any identifiable individual person, business or organization; and not disassemble, decompile or in any way attempt to reverse engineer any software provided as part of the Information."
- **Símbolos oficiais.** A cláusula "Advertising and Publicity" proíbe usar nome, brasão, logotipos ou domínios da Statistics Canada e símbolos do Governo do Canadá sem autorização, e qualquer anotação que sugira endosso.
- **Terceiros recebem o produto.** "individuals or entities who have received Value-added Products or reproductions of the Information from you pursuant to this licence will not have their licences terminated provided they remain in full compliance with those licences."
- **Alteração.** "Statistics Canada may modify this licence at any time [...]. Your use of the Information will be governed by the terms of the licence in force as of the date and time you accessed the Information."

Leitura dessas cláusulas:

1. A licença permite uso comercial, redistribuição e sublicença, sem cláusula ShareAlike nem NonCommercial. As duas exclusões do ADR 0001 não se aplicam.
2. O dataset é um "Value-added Product": os nomes são adaptados (capitalização, agregação com outras fontes) e incorporados. Os direitos sobre o produto ficam com quem o produz, que pode licenciá-lo sob CC BY 4.0.
3. A obrigação positiva é a atribuição com o texto fixo de (b). A CC BY 4.0 já exige atribuição do dataset, e o aviso da fonte entra na atribuição que acompanha o dataset, como os textos "Source : Insee" e "CC BY 4.0" das fontes do ADR 0001.
4. As demais condições não são só atribuição: proíbem sugerir endosso, deturpar a informação ou a fonte, e cruzar os dados para identificar pessoas. A CC BY 4.0 também proíbe sugerir endosso (seção 2(a)(6)). Contagens de nomes por ano, com supressão abaixo de 5 já aplicada pela fonte, não identificam pessoas. Essas condições restringem condutas, não o uso ou a redistribuição, e são as mesmas da Open Government Licence do Canadá, modelada na OGL do Reino Unido que o ADR 0001 já aceita.

## Decisão

- A Statistics Canada Open Licence entra na lista de licenças aceitas do ADR 0001, com o identificador `statcan-open-licence` em `LICENCAS_COMPATIVEIS` (`src/namescommons/sources.py`). Não há identificador SPDX para essa licença; o nome segue o padrão em minúsculas de `public-domain`.
- Toda fonte com essa licença registra em `attribution` de `sources.yaml` o aviso de (b), em inglês e sem tradução: "Adapted from Statistics Canada, <nome do produto>, <data de referência>. This does not constitute an endorsement by Statistics Canada of this product."
- O repositório não usa nome, logotipo ou símbolos da Statistics Canada além da citação da fonte, e nenhum texto sugere endosso.
- O dado é usado como publicado: contagens não são alteradas, só omitidas quando suprimidas (ADR 0002).
- A versão da licença lida (data de modificação 2025-07-10) fica registrada na spec da fonte. Uma mudança de termos exige reavaliar este ADR antes da próxima release.

## Consequências

- O Canadá entra no dataset com primeiros nomes por sexo e ano, de 1991 a 2025 (spec `003d-statistics-canada`).
- O aviso fixo da Statistics Canada tem de acompanhar o dataset: a página de atribuições gerada de `sources.yaml` (spec 006) precisa reproduzir `attribution` sem edição.
- Quem recebe o dataset sob CC BY 4.0 continua sujeito, quanto à parte canadense, às condições de conduta da licença (não identificar pessoas, não sugerir endosso). O cartão do dataset (spec 006) deve dizer isso junto da atribuição.
- A Statistics Canada pode mudar a licença a qualquer momento; vale a versão em vigor no acesso. A data de `retrieved` em `sources.yaml` documenta qual versão vale para cada edição baixada.
- Outras licenças governamentais com o mesmo desenho (Open Government Licence do Canadá e das províncias) podem entrar por um ADR curto que cite este como precedente.
