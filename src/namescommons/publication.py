"""Arquivos de publicação da release (spec 006): atribuições, cartão do dataset, zip e somas.

Os textos são em inglês, como o README; ver ADR 0001 (licença dos dados) e ADR 0004 (avisos da
Statistics Canada).
"""

from collections.abc import Iterable, Mapping

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
