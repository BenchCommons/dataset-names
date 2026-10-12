# 0003. Nome do projeto e do pacote

## Status

Aceito (2026-10-12)

## Contexto

O repositório nasceu como hard fork de [Debdut/names.io](https://github.com/Debdut/names.io), que publicava listas planas de nomes. O projeto virou um dataset mundial de nomes com país, frequência, gênero e escrita, construído por um pipeline próprio (specs 001 a 003).

Em 2026-10-12 o repositório foi transferido de `webminas/names.io` para a organização OpenSoftwareAlliance. O nome `names.io` e o pacote `namesio` herdavam a identidade do projeto original, que já não descreve o que o repositório faz. A issue #17 registra a decisão de renomear.

Nota de transferência: depois deste ADR o repositório passou para a organização BenchCommons e hoje é `github.com/BenchCommons/dataset-names`. O texto abaixo guarda o slug e o `User-Agent` da época; o `User-Agent` atual aponta para o novo endereço (`src/namescommons/cache.py`).

## Decisão

- Nome do projeto: **Names Commons Dataset**.
- Slug do repositório: `names-commons-dataset` (`github.com/OpenSoftwareAlliance/names-commons-dataset`).
- Pacote Python e comando de linha de comando: `namescommons` (distribuição `names-commons-dataset`).
- O `User-Agent` dos downloads passa a ser `namescommons/<versão> (+https://github.com/OpenSoftwareAlliance/names-commons-dataset)`.
- O crédito ao projeto de origem continua no README.

## Consequências

- Imports (`namesio.*` vira `namescommons.*`) e o comando (`namesio` vira `namescommons`) mudam. Não há alias de compatibilidade: o pacote nunca foi publicado e não tem consumidores externos.
- Os `tasks.md` das specs 001 a 003 são roteiros históricos e mantêm `namesio`. Specs e planos que descrevem o código vigente usam o nome novo.
- Servidores que filtram por `User-Agent` passam a ver a identificação nova.
- As URLs antigas de `webminas/names.io` continuam redirecionando pelo GitHub, mas links no repositório apontam para a URL nova.
