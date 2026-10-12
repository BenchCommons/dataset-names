# 0014. Release montada por workflow a partir de um rascunho com o cache das fontes

## Status

Aceito (2026-10-12). Spec [006](../specs/006-publicacao/spec.md).

## Contexto

Uma release do dataset é um conjunto de arquivos gerados a partir do cache das fontes (spec 002) e anexados a uma GitHub Release com tag CalVer (spec 001, R5). Duas fontes bloqueiam o download automático: a SSA responde 403 (spec 003, R4) e o catálogo da Nova Zelândia devolve uma página de desafio (spec 003e, R4). O cache completo, portanto, só pode ser montado por uma pessoa com navegador, e um workflow que baixa as fontes sozinho não consegue montar a release.

As opções avaliadas:

1. **Build e envio na máquina do dono** (`namescommons run` e `gh release upload`). Simples, mas o resultado depende do ambiente local, e nada garante que o commit da tag foi o que gerou os arquivos.
2. **Workflow que baixa as fontes.** Falha na SSA e na Nova Zelândia.
3. **Workflow que lê o cache de um rascunho de release.** O dono monta o cache, empacota (`source-cache.tar.gz`) e o anexa a um rascunho com o nome da tag. O push da tag dispara o workflow, que baixa o cache do rascunho, roda o build offline no commit da tag, verifica as somas e envia os assets ao rascunho. Rascunhos não são públicos, e a publicação continua um ato do dono.
4. **Cache como artefato ou cache do Actions.** Não há como o dono enviar um arquivo ao cache do Actions pelo navegador, e artefatos expiram.

## Decisão

- Opção 3. O workflow `.github/workflows/release.yml` roda no push de uma tag CalVer, baixa `source-cache.tar.gz` do rascunho da release com o mesmo nome, roda `tools/release.sh build` (que chama `namescommons run --offline` e verifica `SHA256SUMS`) e envia os assets com `tools/release.sh upload`.
- O envio nunca usa `--clobber`, recusa release publicada (releases são imutáveis, spec 001 do tools-dataset, R6.2) e remove `source-cache.tar.gz` do rascunho só depois de enviar os assets, para que os arquivos brutos das fontes nunca sejam publicados junto com o dataset.
- O workflow nunca publica a release nem cria ou move tag. O disparo manual (`workflow_dispatch`) é sempre ensaio, sobre as amostras de `tests/fixtures/`, e a CI roda o mesmo ensaio em todo PR.
- A lógica fica em `tools/release.sh`, e não no YAML, para ser testada com um `gh` falso e rodada localmente.

## Consequências

- A release é reproduzível a partir do commit da tag e do cache anexado ao rascunho; o cache não fica público.
- O dono continua tendo de baixar a SSA e a Nova Zelândia pelo navegador antes de cada release, e de revisar o rascunho antes de publicar.
- Se o envio falhar no meio, o rascunho fica com parte dos assets e com o cache; uma nova execução recusa sobrescrever, e o dono apaga os assets do rascunho antes de repetir.
- O caminho real (baixar do rascunho e enviar) só é exercitado com o `gh` falso dos testes até a primeira release; o comportamento do `gh` com rascunhos é o documentado pelo GitHub CLI.
