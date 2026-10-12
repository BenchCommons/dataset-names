# 0015. Retirada de `legacy/` da árvore do repositório

## Status

Proposto (2026-10-12), aguardando aprovação do dono para a remoção dos arquivos. Spec [006](../specs/006-publicacao/spec.md), R10.

## Contexto

A spec 001 (R6) moveu as listas planas originais (`first_names.all.txt`, `last_names.all.txt`) e os scripts `generate/` para `legacy/`, sem alteração, e deixou a retirada para a spec 006. São 22 arquivos e 2.091.482 bytes.

O conteúdo de `legacy/` não tem licença declarada: veio de sites, gists e repositórios sem licença, e inclui nomes dos datasets do IMDb, com termos não comerciais (ADR 0001). O dataset novo não o ingere, e o contrato de entradas do tools-dataset (spec 001 de lá, R1.3) o exclui explicitamente. Mantê-lo na árvore tem custo:

- o repositório distribui, na versão atual, material sem concessão de licença ao lado de `LICENSE` e `DATA_LICENSE`, e cada leitor precisa achar o `legacy/README.md` para saber que nenhuma das duas vale ali;
- `legacy/generate/` depende de diretórios e URLs que não existem mais, então não reproduz as listas;
- buscas, clones e ferramentas de licença passam pelos 2 MB de listas sem metadados.

O benefício de manter é a conveniência de quem usava as listas antigas por caminho no repositório.

## Decisão

- `legacy/` sai da árvore do repositório num commit próprio. O conteúdo continua acessível no histórico do git e no repositório de origem do fork (Debdut/names.io).
- A remoção só acontece com aprovação explícita do dono sobre a lista exata dos arquivos (caminho e tamanho), registrada na descrição do PR da spec 006 e na issue de acompanhamento. Até lá `legacy/` fica congelado como está.
- No mesmo commit da remoção: `tests/test_legacy.py` passa a conferir que `legacy/` não existe, o README troca a linha de `legacy/` por uma nota que aponta o último commit que o contém, e a spec 001 (R4 e R6) ganha nota remetendo a este ADR.

## Consequências

- O repositório passa a ter só código Apache-2.0, dados CC BY 4.0 e documentação; nenhum arquivo sem licença.
- Quem dependia de `legacy/first_names.all.txt` por caminho perde o arquivo em `master`, mas pode fixar o último commit que o contém.
- Os testes de integridade da spec 001 (critério 6) deixam de fazer sentido e são trocados pelo teste de ausência.
