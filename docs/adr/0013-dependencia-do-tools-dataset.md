# 0013. Dependência do kit de fontes do tools-dataset por tag git

## Status

Aceito (2026-10-12). Spec [007](../specs/007-tools-dataset/spec.md). Substitui em parte o [ADR 0005](0005-leitor-de-planilhas.md): a decisão sobre o leitor de planilhas continua valendo, mas o código e a versão fixada do `xlrd` passam a viver no tools-dataset.

## Contexto

O cache de downloads, o leitor de planilhas, a base do adaptador, o registro de fontes e os auxiliares de arquivo do manifesto nasceram neste repositório (specs 002, 003, 003b e 003e). Outros repositórios `dataset-*` da BenchCommons precisam do mesmo código. Em 2026-10-12 o dono decidiu mover a parte genérica para o [tools-dataset](https://github.com/BenchCommons/tools-dataset), como o pacote Python `benchcommons-tools-dataset` (import `datasettool`), definido pela [spec 004 de lá](https://github.com/BenchCommons/tools-dataset/blob/v0.1.0/docs/specs/004-source-toolkit/spec.md). O tools-dataset é o dono desse contrato; este repositório só o consome.

O build precisa continuar reproduzível: o mesmo commit deste repositório deve rodar sempre o mesmo código do kit. O [ADR 0004 do tools-dataset](https://github.com/BenchCommons/tools-dataset/blob/v0.1.0/docs/adr/0004-dataset-repos-depend-on-a-git-tag.md) já compara as opções (PyPI, wheel em release, submódulo ou cópia, branch, tag git) e escolhe a tag git para todos os consumidores.

## Decisão

- Este repositório depende do kit pela versão exata e fixa a origem na tag correspondente, com `uv`:

  ```toml
  [project]
  dependencies = ["benchcommons-tools-dataset==0.1.0", ...]

  [tool.uv.sources]
  benchcommons-tools-dataset = { git = "https://github.com/BenchCommons/tools-dataset", tag = "v0.1.0" }
  ```

  O `uv.lock` versionado registra o commit da tag. Uma branch nunca é usada como origem.
- `pyyaml` e `xlrd` saem das dependências diretas: o código daqui não os importa mais, e o kit os traz fixados (`pyyaml==6.0.3`, `xlrd==2.0.2`, [ADR 0005 do tools-dataset](https://github.com/BenchCommons/tools-dataset/blob/v0.1.0/docs/adr/0005-source-toolkit-runtime-dependencies.md)).
- Correções no código genérico são feitas no tools-dataset, numa versão nova, e chegam aqui por atualização da dependência. Este repositório não guarda cópia nem remendo local do kit.

### Procedimento de atualização

1. Confirmar que a tag nova existe: `gh api repos/BenchCommons/tools-dataset/tags --jq '.[].name'`.
2. Ler as notas da versão e a spec do tools-dataset na tag nova. Enquanto a versão maior for 0, uma versão menor pode quebrar a API.
3. Numa branch, trocar as duas linhas juntas em `pyproject.toml` (`==X.Y.Z` e `tag = "vX.Y.Z"`) e rodar `uv lock --upgrade-package benchcommons-tools-dataset` e `uv sync`.
4. Rodar `uv run pytest -q` e os dois passos offline da CI, e comparar as saídas com as da versão anterior (`diff -r`). Diferença em saída é mudança de comportamento e precisa de spec ou ADR.
5. Abrir o PR com as duas linhas, o `uv.lock` e a evidência do passo 4. `tests/test_tools_dataset.py` falha se a versão e a tag divergirem.

## Consequências

- `uv sync` precisa de acesso ao GitHub quando não há cache, como já precisava ao PyPI.
- As mensagens de erro do kit são em inglês; as deste repositório continuam em português. Uma mensagem com várias linhas do registro de fontes pode misturar as duas línguas.
- Uma falha no código genérico só se corrige com uma versão nova do kit (tag de correção), nunca editando a tag existente.
- Os testes do comportamento genérico vivem no tools-dataset; aqui ficam só os testes do que é de nomes e da integração com o kit.
