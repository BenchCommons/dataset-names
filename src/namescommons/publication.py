"""Arquivos de publicação da release (spec 006): atribuições, cartão do dataset, zip e somas.

Os textos são em inglês, como o README; ver ADR 0001 (licença dos dados) e ADR 0004 (avisos da
Statistics Canada).
"""

import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path

from datasettool.files import sha256_file

from namescommons.sources import Source

REPOSITORIO = "https://github.com/BenchCommons/dataset-names"
NOME_DO_DATASET = "Names Commons Dataset"

# Spec 006, R3.4: nome e URL de cada licença aceita pelo ADR 0001 (ampliado pelo 0004).
LICENCAS: dict[str, tuple[str, str | None]] = {
    "public-domain": ("Public domain", None),
    "CC0-1.0": ("CC0 1.0 Universal", "https://creativecommons.org/publicdomain/zero/1.0/"),
    "CC-BY-3.0": ("Creative Commons Attribution 3.0", "https://creativecommons.org/licenses/by/3.0/"),
    "CC-BY-4.0": ("Creative Commons Attribution 4.0 International", "https://creativecommons.org/licenses/by/4.0/"),
    "ODC-By-1.0": ("Open Data Commons Attribution License 1.0", "https://opendatacommons.org/licenses/by/1-0/"),
    "OGL-UK-3.0": (
        "Open Government Licence v3.0", "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
    ),
    "etalab-2.0": ("Licence Ouverte / Open Licence 2.0 (Etalab)", "https://www.etalab.gouv.fr/licence-ouverte-open-licence/"),
    "statcan-open-licence": ("Statistics Canada Open Licence", "https://www.statcan.gc.ca/en/reference/licence"),
}

# Spec 006, R3.3: avisos que a licença exige além da atribuição, sem tradução (ADR 0004).
AVISOS: dict[str, str] = {
    "statcan-open-licence": (
        "Data adapted from Statistics Canada remain subject to the Statistics Canada Open Licence "
        "(https://www.statcan.gc.ca/en/reference/licence); users must not use them to identify individuals, "
        "imply endorsement, misrepresent them, or use Statistics Canada or Government of Canada symbols."
    ),
}


def dataset_attribution(release: str) -> str:
    """Linha de atribuição do próprio dataset (spec 006, R4.1)."""
    return (
        f"{NOME_DO_DATASET}, release {release}, BenchCommons ({REPOSITORIO}), licensed under CC BY 4.0. "
        "Upstream sources and notices: see ATTRIBUTION.txt."
    )


def _licenca(fonte: Source) -> tuple[str, str | None]:
    try:
        return LICENCAS[fonte.license]
    except KeyError:
        raise ValueError(
            f"licença '{fonte.license}' da fonte '{fonte.id}' sem entrada em LICENCAS de namescommons.publication"
        ) from None


def _usadas(sources: Mapping[str, Source], used: Iterable[str]) -> list[Source]:
    return [sources[i] for i in sorted(set(used))]


def notices(sources: Mapping[str, Source], used: Iterable[str]) -> list[str]:
    """Avisos das licenças usadas, na ordem das fontes, sem repetição."""
    return list(dict.fromkeys(AVISOS[f.license] for f in _usadas(sources, used) if f.license in AVISOS))


def attribution_text(release: str, sources: Mapping[str, Source], used: Iterable[str]) -> str:
    """ATTRIBUTION.txt (spec 006, R3): linha do dataset, um bloco por fonte usada e os avisos."""
    fontes = _usadas(sources, used)
    linhas = [
        f"Attribution for the {NOME_DO_DATASET}, release {release}",
        "",
        "Cite the dataset as:",
        "",
        f"  {dataset_attribution(release)}",
        "",
        "The dataset is licensed under CC BY 4.0 (see DATA_LICENSE). It contains data adapted from the",
        "sources below. The attribution each source requires is reproduced verbatim and must be kept",
        "when the data is redistributed.",
        "",
        "Sources",
        "=======",
    ]
    for f in fontes:
        nome, url = _licenca(f)
        linhas += ["", f.name, f"Id: {f.id}", f"URL: {f.url}", f"Licence: {nome}" + (f" ({url})" if url else ""),
                   f"Attribution: {f.attribution}"]
    linhas += ["", "Notices", "======="]
    avisos = notices(sources, [f.id for f in fontes])
    for aviso in avisos:
        linhas += ["", aviso]
    if not avisos:
        linhas += ["", "No additional notices."]
    return "\n".join(linhas) + "\n"


# Cartão do dataset (spec 006, R6) ------------------------------------------------------------------

_DESCRICOES = {
    "observations.parquet": "Canonical observation table: one row per source, name, kind, country, gender and year.",
    "given_names.csv": "One row per given name across all countries.",
    "given_names.parquet": "Same as `given_names.csv`, with typed nested columns.",
    "family_names.csv": "One row per family name across all countries.",
    "family_names.parquet": "Same as `family_names.csv`, with typed nested columns.",
    "variant_links.parquet": "Links between name variants published by Wikidata.",
    "by_country.zip": "`by_country/<CC>.csv`, one file per country (ISO 3166-1 alpha-2).",
    "manifest.json": "Release, schema version, sources, drop counts, and row count and SHA-256 of each table.",
    "DATA_LICENSE": "CC BY 4.0 licence text and the dataset's attribution line.",
    "ATTRIBUTION.txt": "Attribution text and licence of every upstream source, and required notices.",
    "DATASET_CARD.md": "This card.",
    "SHA256SUMS": "SHA-256 of every release asset, for `sha256sum -c SHA256SUMS`.",
}

_CAMPOS = """### `given_names` and `family_names`

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Display form: the most frequent published form, in Unicode NFC |
| `name_key` | string | `casefold()` of `name`; the identity of the name, accents preserved |
| `ascii` | string | Lowercase ASCII transliteration (ICAO Doc 9303 tables); may be empty for scripts without a table |
| `script` | string | Predominant ISO 15924 script of the letters (`Latn`, `Cyrl`, `Hani`, `Jpan` ...) |
| `country_count` | integer | Number of countries that attest the name |
| `countries` | list | One `{country, count, count_type, rank}` per country; JSON in the CSV |
| `female_share` | decimal | F / (F + M) over the counts with gender; empty without a basis |
| `gender_basis` | integer | F + M used for `female_share` |
| `group_id` | string | Variant group: the smallest `name_key` in the group |
| `sources` | list | Sorted ids of the sources that attest the name; JSON in the CSV |

### `by_country/<CC>.csv`

| Field | Type | Meaning |
|---|---|---|
| `kind` | string | `given` or `family` |
| `name`, `name_key`, `ascii`, `script` | string | As above |
| `count` | integer | Births summed over all years, or population in the latest edition; empty when only attested |
| `count_type` | string | `births`, `population` or `attested`; counts of different types are never added |
| `rank` | integer | Dense rank by `kind` and `count_type`, highest count first |
| `female_share`, `gender_basis` | decimal, integer | As above, for this country |
| `first_year`, `last_year` | integer | Years covered by the count |

### `observations.parquet`

`name`, `name_key`, `ascii`, `script`, `kind`, `country`, `gender` (`F`, `M` or empty, never inferred), `year`, `count`, `count_type` and `source_id`: what one source publishes for one name, kind, country, gender and year.

### `variant_links.parquet`

`source_id`, `relation`, `qid`, `name`, `name_key`, `kind`, `target_qid`, `target_name`, `target_name_key` and `target_kind`: one link between two Wikidata name items.

The schema is defined in [spec 001](https://github.com/BenchCommons/dataset-names/blob/master/docs/specs/001-esquema/spec.md), with the links of spec 004 and the variant rules of spec 005."""


def _n(valor: int) -> str:
    return f"{valor:,}"


def _arquivos(files: Mapping[str, dict]) -> list[tuple[str, int | None]]:
    por_pais = sum(v["rows"] for k, v in files.items() if k.startswith("by_country/"))
    linhas = [(k, v["rows"]) for k, v in files.items() if not k.startswith("by_country/")]
    linhas.append(("by_country.zip", por_pais))
    linhas += [(nome, None) for nome in ("manifest.json", "DATA_LICENSE", "ATTRIBUTION.txt", "DATASET_CARD.md", "SHA256SUMS")]
    return linhas


def _descarte(d: Mapping[str, int] | None) -> str:
    if d is None:
        return "unknown"
    if not d["lines"]:
        return "0"
    return f"{_n(d['lines'])} lines, {_n(d['records'])} records"


def _cobertura(linhas: list) -> list[str]:
    saida = []
    for kind in ("given", "family"):
        daqui = [r for r in linhas if r.kind == kind]
        tipos = ", ".join(sorted({r.count_type for r in daqui}))
        saida.append(f"{_n(len(daqui))} ({tipos})" if daqui else "")
    anos = [a for r in linhas for a in (r.first_year, r.last_year) if a is not None]
    saida.append(f"{min(anos)} to {max(anos)}" if anos else "")
    return saida


def _lista(fontes: list[Source]) -> str:
    return ", ".join(f.name for f in fontes)


def _limitacoes(manifest: Mapping, usadas: list[Source]) -> list[str]:
    itens = []
    sem_acento = [f for f in usadas if f.strips_accents]
    if sem_acento:
        itens.append(
            f"Sources that publish names without accents: {_lista(sem_acento)}. Their names are grouped with "
            "accented forms only when the match is unambiguous (ADR 0011), and their own rows keep the "
            "unaccented form."
        )
    caixa = [f for f in usadas if f.uniform_case]
    if caixa:
        itens.append(
            f"Sources that publish names in a single case, recapitalised by the pipeline: {_lista(caixa)}. "
            "The display name prefers forms from sources that publish mixed case."
        )
    por_id = {s["id"]: s for s in manifest["sources"]}
    com_descarte = [f for f in usadas if (por_id[f.id].get("dropped") or {}).get("lines")]
    if com_descarte:
        linhas = sum(por_id[f.id]["dropped"]["lines"] for f in com_descarte)
        registros = sum(por_id[f.id]["dropped"]["records"] for f in com_descarte)
        itens.append(
            f"{_n(linhas)} lines ({_n(registros)} records) were dropped because the source published corrupted "
            f"names, such as lost diacritics or macrons (ADR 0007): {_lista(com_descarte)}. Country totals "
            "exclude them."
        )
    desconhecidos = [f for f in usadas if por_id[f.id].get("dropped") is None]
    if desconhecidos:
        itens.append(f"Drop counts are unknown for: {_lista(desconhecidos)}.")
    itens.append(
        "`group_id` identifies a variant group only within one release: it can change between releases when a "
        "name with a smaller key joins the group or the links change."
    )
    for f in usadas:
        if f.id == "wikidata":
            itens.append(
                f"Wikidata names and links are a snapshot of the QLever Wikidata endpoint taken on "
                f"{f.retrieved.isoformat()}, not on the release date."
            )
    itens.append(
        "`female_share` is a weighted estimate that combines countries and count types; it is never a count, "
        "and gender is never inferred from the name."
    )
    return itens


def dataset_card(manifest: Mapping, sources: Mapping[str, Source], countries: Mapping[str, list]) -> str:
    """DATASET_CARD.md a partir do manifesto, de sources.yaml e das linhas por país (spec 006, R6)."""
    release = manifest["release"]
    files = manifest["files"]
    usadas = _usadas(sources, (s["id"] for s in manifest["sources"]))
    por_id = {s["id"]: s for s in manifest["sources"]}

    def linhas(nome: str) -> int:
        return files.get(nome, {}).get("rows", 0)

    out = [
        f"# {NOME_DO_DATASET}, release {release}",
        "",
        "Given names and family names from around the world, with the country that attests each name, its "
        "frequency, its gender (only when the source publishes it) and its writing script. Built only from "
        "official statistics and Wikidata.",
        "",
        "## Summary",
        "",
        f"- Release: {release}",
        f"- Schema version: {manifest['schema_version']}",
        f"- Observations: {_n(linhas('observations.parquet'))}",
        f"- Given names: {_n(linhas('given_names.csv'))}",
        f"- Family names: {_n(linhas('family_names.csv'))}",
        f"- Countries: {_n(len(countries))}",
        f"- Variant links: {_n(linhas('variant_links.parquet'))}",
        f"- Sources: {_n(len(usadas))}",
        "",
        "## Files",
        "",
        "| File | Rows | Description |",
        "|---|---|---|",
    ]
    for nome, n in _arquivos(files):
        out.append(f"| `{nome}` | {'' if n is None else _n(n)} | {_DESCRICOES.get(nome, '')} |")
    out += ["", "## Fields", "", _CAMPOS, "", "## Sources", "",
            "| Source | Id | Country | Count type | Licence | Suppression | Retrieved | Observations | Dropped |",
            "|---|---|---|---|---|---|---|---|---|"]
    for f in usadas:
        s = por_id[f.id]
        supressao = f"below {_n(f.suppression)}" if f.suppression else "none"
        out.append(
            f"| {f.name} | `{f.id}` | {f.country or 'all'} | {f.count_type} | {f.license} | {supressao} | "
            f"{f.retrieved.isoformat()} | {_n(s.get('observations', 0))} | {_descarte(s.get('dropped'))} |"
        )
    out += ["", "## Coverage", "", "| Country | Given names | Family names | Years |", "|---|---|---|---|"]
    for pais in sorted(countries):
        out.append("| " + " | ".join([pais, *_cobertura(countries[pais])]) + " |")
    out += [
        "", "## Suppression", "",
        "National statistics offices hide small counts to protect privacy. Suppressed values are omitted, never "
        "replaced by zero or an estimate (ADR 0002): a name that a source only publishes as suppressed is not "
        "attested by that source. The threshold of each source is in the Suppression column above. Sums over "
        "years of births treat suppressed years as zero, so they underestimate rare names.",
        "", "## Known limitations", "",
    ]
    out += [f"- {item}" for item in _limitacoes(manifest, usadas)]
    out += [
        "", "## Licence", "",
        "The data is licensed under CC BY 4.0 (`DATA_LICENSE`). Attribute it as:", "",
        f"> {dataset_attribution(release)}", "",
        "`ATTRIBUTION.txt` reproduces the attribution text and licence of every upstream source; keep it when "
        "you redistribute the data.",
    ]
    for f in usadas:
        if f.license in AVISOS:
            out += ["", f"> {f.attribution}"]
    for aviso in notices(sources, [f.id for f in usadas]):
        out += ["", f"> {aviso}"]
    out += [
        "", "## How to cite", "",
        f"> {dataset_attribution(release)}", "",
        f"Release page: {REPOSITORIO}/releases/tag/{release}",
    ]
    return "\n".join(out) + "\n"


# Pacote da release (spec 006, R5) -----------------------------------------------------------------

SOMAS = "SHA256SUMS"
ZIP_POR_PAIS = "by_country.zip"
_DATA_FIXA = (1980, 1, 1, 0, 0, 0)


def write_by_country_zip(out_dir: Path) -> None:
    """by_country.zip com os CSV de by_country/, em ordem, com data e permissões fixas (R5.2)."""
    with zipfile.ZipFile(out_dir / ZIP_POR_PAIS, "w") as z:
        for csv_ in sorted((out_dir / "by_country").glob("*.csv")):
            info = zipfile.ZipInfo(f"by_country/{csv_.name}", date_time=_DATA_FIXA)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            info.create_system = 3  # Unix, para external_attr valer igual em qualquer sistema
            z.writestr(info, csv_.read_bytes(), compresslevel=9)


def write_sha256sums(out_dir: Path) -> None:
    """SHA256SUMS no formato do GNU sha256sum, sobre os arquivos do nível de cima (R5.3)."""
    nomes = sorted(p.name for p in out_dir.iterdir() if p.is_file() and p.name != SOMAS)
    linhas = "".join(f"{sha256_file(out_dir / n)}  {n}\n" for n in nomes)
    (out_dir / SOMAS).write_bytes(linhas.encode("utf-8"))


def write_text(path: Path, texto: str) -> None:
    """Texto UTF-8 sem BOM, com LF em qualquer sistema."""
    path.write_bytes(texto.encode("utf-8"))
