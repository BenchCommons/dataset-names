# Names Commons Dataset

[![CI](https://github.com/BenchCommons/dataset-names/actions/workflows/ci.yml/badge.svg)](https://github.com/BenchCommons/dataset-names/actions/workflows/ci.yml)

<img src='assets/logo.png' alt='Names Commons Dataset logo'/>

An open, reproducible dataset of given names and family names from around the world. Each name comes with the country that attests it, how frequent it is, its gender (only when the source publishes it) and its writing script. It is built only from official statistics and Wikidata, and every source and licence is declared in [`sources.yaml`](sources.yaml).

Originally forked from [Debdut/names.io](https://github.com/Debdut/names.io).

## Sources

| Source | Country | Names | Count type | Licence |
|---|---|---|---|---|
| [Social Security Administration](https://www.ssa.gov/oact/babynames/limits.html) | US | given | births | Public domain |
| [INSEE, Fichier des prénoms](https://www.insee.fr/fr/statistiques/8595130) | FR | given | births | Etalab 2.0 |
| [CSO, Irish Babies' Names](https://data.gov.ie/dataset/vsa50-boys-names-in-ireland-with-3-or-more-occurrences) | IE | given | births | CC BY 4.0 |
| [Statistics Norway, table 10467](https://www.ssb.no/en/statbank/table/10467) | NO | given | births | CC BY 4.0 |
| [Statistics Norway, table 12891](https://www.ssb.no/en/statbank/table/12891) | NO | family | population | CC BY 4.0 |

Attribution text for each source is in `sources.yaml`.

## Output layout

A release contains:

```
by_country/<CC>.csv       one file per country (ISO 3166-1 alpha-2)
given_names.csv           one row per given name, all countries
family_names.csv          one row per family name, all countries
observations.parquet      the full observation table
manifest.json             schema version, sources, row counts, SHA-256 of each file
```

`given_names` and `family_names` are also written as Parquet. Counts of different types (`births`, `population`, `attested`) are never added together. The schema is defined in [spec 001](docs/specs/001-esquema/spec.md).

## Quick start

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run namescommons fetch                                  # download the sources into cache/
uv run namescommons ingest --out observations.parquet      # parse the cache into observations
uv run namescommons validate observations.parquet          # check the observation table
uv run namescommons build observations.parquet --out dist --release 2026.10
uv run namescommons run --out dist --release 2026.10       # fetch, ingest and build in sequence
```

Add `--offline` to `ingest` or `run` to use only files already in the cache. Use `--help` on any command for its options.

The SSA server refuses automated downloads (HTTP 403). Download the national data ZIP in a browser and save it where the error message of `fetch` says, then continue with `--offline` ([spec 003, R4](docs/specs/003-fontes-oficiais/spec.md)).

## Licences

- Code: Apache-2.0, see [`LICENSE`](LICENSE).
- Data: CC BY 4.0, see [`DATA_LICENSE`](DATA_LICENSE). Only sources whose licence allows redistribution under CC BY 4.0 are accepted ([ADR 0001](docs/adr/0001-licenca-dos-dados.md)).
- [`legacy/`](legacy/README.md) holds the original flat lists and scripts. It is not part of the dataset and is not covered by these licences.

## Contributing

Work is driven by specifications. The order and dependencies are in [`docs/specs/ROADMAP.md`](docs/specs/ROADMAP.md); each feature has a `spec.md`, a `plan.md` and a `tasks.md` under [`docs/specs/`](docs/specs/). Architectural decisions are recorded in [`docs/adr/`](docs/adr/). Open issues track what is still to be done. Conventions and commands for the codebase are in [`AGENTS.md`](AGENTS.md). Texts in the repository are in Brazilian Portuguese, except this README.
