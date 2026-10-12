"""Issue #16: a edição do INSEE aparece em vários lugares; o passo anual (AGENTS.md) é conferido aqui.

O INSEE publica cada edição numa página nova (id novo), sem listagem estável da edição mais recente
(nem o data.gouv.fr a acompanha), então a URL é trocada à mão uma vez por ano. Estes testes falham
se algum dos lugares ficar para trás.
"""

import re
from pathlib import Path

from namescommons.adapters import load_adapter
from namescommons.sources import load_sources

RAIZ = Path(__file__).resolve().parent.parent


def test_adaptador_deriva_url_e_arquivo_da_edicao_e_da_pagina():
    mod = load_adapter("fr-insee-births")
    [recurso] = mod.RESOURCES
    assert recurso.filename == f"prenoms-{mod.EDICAO}-nat_csv.zip"
    assert recurso.url == f"https://www.insee.fr/fr/statistiques/fichier/{mod.PAGINA}/{recurso.filename}"


def test_sources_yaml_e_amostra_acompanham_a_edicao_do_adaptador():
    mod = load_adapter("fr-insee-births")
    fonte = load_sources(RAIZ / "sources.yaml")["fr-insee-births"]
    assert fonte.url == f"https://www.insee.fr/fr/statistiques/{mod.PAGINA}"
    assert fonte.attribution.endswith(f"édition {mod.EDICAO}")
    assert (RAIZ / "tests" / "fixtures" / "fr-insee-births" / mod.RESOURCES[0].filename).is_file()
    atribuicao = (RAIZ / "tests" / "fixtures" / "ATRIBUICAO.md").read_text(encoding="utf-8")
    linha = next(l for l in atribuicao.splitlines() if "fr-insee-births" in l)
    assert f"édition {mod.EDICAO}" in linha and str(mod.PAGINA) in linha and f"prenoms-{mod.EDICAO}-nat.csv" in linha


def test_agents_md_documenta_o_passo_anual():
    texto = (RAIZ / "AGENTS.md").read_text(encoding="utf-8")
    assert "Passo anual do INSEE" in texto
    for item in ("EDICAO", "PAGINA", "sources.yaml", "ATRIBUICAO.md", "git mv"):
        assert item in texto
    assert re.search(r"fr_insee_births\.py", texto)
