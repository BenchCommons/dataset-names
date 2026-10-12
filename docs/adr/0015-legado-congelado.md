# 0015. `legacy/` fica no repositório como arquivo histórico congelado

## Status

Aceito (2026-10-12), por decisão do dono do repositório. Spec [006](../specs/006-publicacao/spec.md), R10.

## Contexto

A spec 001 (R6) moveu as listas planas originais (`first_names.all.txt`, `last_names.all.txt`) e os scripts `generate/` para `legacy/`, sem alteração, e deixou para a spec 006 decidir o destino do diretório. São 22 arquivos e 2.091.482 bytes.

O conteúdo de `legacy/` não tem licença declarada: veio de sites, gists e repositórios sem licença, e inclui nomes dos datasets do IMDb, com termos não comerciais (ADR 0001). O dataset novo não o ingere, e o contrato de entradas do tools-dataset (spec 001 de lá, R1.3) o exclui.

As opções eram tirar o diretório da árvore (o conteúdo continuaria no histórico do git) ou mantê-lo congelado. A primeira versão deste ADR propôs a remoção; o dono decidiu manter.

## Decisão

- `legacy/` fica no repositório como arquivo histórico congelado: nenhum arquivo é alterado, acrescentado ou removido.
- `legacy/` não é ingerido pelo pipeline, não entra em nenhum arquivo das releases e está fora do contrato de entradas do tools-dataset (R1.3 de lá).
- `legacy/README.md`, o preâmbulo de `DATA_LICENSE` e o README dizem que o diretório não faz parte do dataset e não é coberto por `DATA_LICENSE` nem por `LICENSE`.
- `tests/test_legacy.py` continua conferindo que as listas estão intactas (spec 001, critério 6).

## Consequências

- Quem usava as listas antigas por caminho no repositório continua encontrando os arquivos.
- O repositório segue distribuindo, ao lado de `LICENSE` e `DATA_LICENSE`, material sem concessão de licença; o aviso em `legacy/README.md`, no README e em `DATA_LICENSE` é a única barreira contra o uso equivocado.
- Os 2 MB das listas continuam em clones, buscas e ferramentas de verificação de licença, que podem apontar o diretório.
- Rever a decisão exige um ADR novo que substitua este.
