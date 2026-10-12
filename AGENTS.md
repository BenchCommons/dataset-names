# AGENTS.md

Fonte canônica de stack, convenções e comandos do projeto.

## O que é

Dataset mundial de nomes: primeiros nomes e sobrenomes com país, frequência, gênero e escrita, construído só a partir de fontes oficiais e do Wikidata. As listas planas antigas ficam congeladas em `legacy/`.

## Stack

Python 3.12, `uv`, `pytest`, `pyarrow`, `pyyaml`, `pycountry`. Build com `hatchling`.

## Comandos

```sh
uv sync                      # instala as dependências
uv run pytest -q             # testes (nunca usam a rede)
uv run namescommons --help        # CLI do pipeline
```

A CI também roda o pipeline offline sobre as amostras de `tests/fixtures/`:

```sh
PYTHONPATH=tests uv run namescommons run --offline --sources tests/fixtures/sources.yaml \
  --adapters adaptadores --cache <cache> --out <saida> --release 2026.10
```

## Convenções

- Commits assinados com GPG, autor Matheus Breguêz `<matbrgz@gmail.com>`. Nunca `--no-gpg-sign` nem `--author`.
- Co-autoria de IA só como trailer no fim da mensagem: `Co-Authored-By: <Agente> <noreply@...>`.
- Spec-Driven Development: uma spec por feature em `docs/specs/<NNN>-<feature>/` (`spec.md`, `plan.md`, `tasks.md`). A ordem e as dependências ficam em [`docs/specs/ROADMAP.md`](docs/specs/ROADMAP.md). O plano antecede o código.
- Decisões arquiteturais em ADRs: [`docs/adr/`](docs/adr/) (uma decisão por arquivo).
- Pendências não ficam no texto: viram issues no GitHub, com checklist.
- Texto em português do Brasil, com acentos, sem travessão.
- Só entram em `sources.yaml` as licenças aceitas pelo [ADR 0001](docs/adr/0001-licenca-dos-dados.md). Valores suprimidos seguem o [ADR 0002](docs/adr/0002-valores-suprimidos.md).
- Os testes nunca acessam a rede: downloads usam o servidor local de `tests/conftest.py`.
- Nada é apagado sem listar antes e ter aprovação.
