from datetime import date

import pytest

from namesio.sources import SourceError, load_sources, parse_sources


def fonte(**campos):
    base = {
        "id": "us-ssa-births", "name": "SSA Baby Names", "url": "https://www.ssa.gov/oact/babynames/",
        "license": "public-domain", "attribution": "U.S. Social Security Administration",
        "country": "US", "count_type": "births", "primary": True, "suppression": 5,
        "retrieved": date(2026, 10, 1),
    }
    return {**base, **campos}


def test_fonte_valida():
    fontes = parse_sources([fonte()])
    assert fontes["us-ssa-births"].suppression == 5


def test_carrega_yaml(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(
        "sources:\n"
        "  - id: wikidata\n"
        "    name: Wikidata\n"
        "    url: https://www.wikidata.org/\n"
        "    license: CC0-1.0\n"
        "    attribution: Wikidata\n"
        "    country: null\n"
        "    count_type: attested\n"
        "    primary: false\n"
        "    suppression: null\n"
        "    retrieved: 2026-10-01\n",
        encoding="utf-8",
    )
    assert load_sources(p)["wikidata"].retrieved == date(2026, 10, 1)


def test_arquivo_sem_fontes(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text("sources: []\n", encoding="utf-8")
    assert load_sources(p) == {}


@pytest.mark.parametrize("licenca", ["CC-BY-SA-4.0", "ODbL-1.0", "CC-BY-NC-4.0", "desconhecida"])
def test_licenca_incompativel_e_recusada(licenca):
    with pytest.raises(SourceError, match="ADR 0001"):
        parse_sources([fonte(license=licenca)])


@pytest.mark.parametrize("campos, trecho", [
    ({"country": "XX"}, "ISO 3166-1"),
    ({"country": "br"}, "ISO 3166-1"),
    ({"count_type": "deaths"}, "count_type"),
    ({"primary": "sim"}, "primary"),
    ({"suppression": 0}, "suppression"),
    ({"retrieved": "ontem"}, "retrieved"),
    ({"url": ""}, "'url' vazio"),
    ({"extra": 1}, "desconhecidos"),
])
def test_campo_invalido(campos, trecho):
    with pytest.raises(SourceError, match=trecho):
        parse_sources([fonte(**campos)])


def test_campo_ausente():
    entrada = fonte()
    del entrada["license"]
    with pytest.raises(SourceError, match="ausentes"):
        parse_sources([entrada])


def test_id_duplicado():
    with pytest.raises(SourceError, match="duplicado"):
        parse_sources([fonte(), fonte()])


def test_duas_fontes_no_mesmo_par_exigem_uma_primary():
    with pytest.raises(SourceError, match="exatamente uma"):
        parse_sources([fonte(id="a"), fonte(id="b")])
    with pytest.raises(SourceError, match="exatamente uma"):
        parse_sources([fonte(id="a", primary=False), fonte(id="b", primary=False)])
    assert set(parse_sources([fonte(id="a"), fonte(id="b", primary=False)])) == {"a", "b"}


def test_todos_os_erros_sao_listados():
    with pytest.raises(SourceError) as e:
        parse_sources([fonte(license="ODbL-1.0", country="XX")])
    assert "ADR 0001" in str(e.value) and "ISO 3166-1" in str(e.value)


def test_licenca_nao_textual_vira_source_error():
    with pytest.raises(SourceError, match="ADR 0001"):
        parse_sources([fonte(license=["CC0-1.0"])])


def test_id_nao_textual_vira_source_error():
    with pytest.raises(SourceError, match="'id' vazio"):
        parse_sources([fonte(id=["us-ssa-births"])])


@pytest.mark.parametrize("campos, trecho", [
    ({"country": ["US"]}, "ISO 3166-1"),
    ({"count_type": ["births"]}, "count_type"),
])
def test_campo_nao_textual_vira_source_error(campos, trecho):
    with pytest.raises(SourceError, match=trecho):
        parse_sources([fonte(**campos)])


def test_entrada_que_nao_e_mapeamento():
    with pytest.raises(SourceError, match="#0: entrada deve ser um mapeamento") as e:
        parse_sources(["foo", None])
    assert "#1: entrada deve ser um mapeamento" in str(e.value)


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(SourceError, match="não foi possível ler"):
        load_sources(tmp_path / "nao-existe.yaml")


def test_yaml_malformado(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text("sources: [\n", encoding="utf-8")
    with pytest.raises(SourceError, match="YAML inválido"):
        load_sources(p)


def test_raiz_que_nao_e_mapeamento(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text("- foo\n", encoding="utf-8")
    with pytest.raises(SourceError, match="a raiz deve ser um mapeamento"):
        load_sources(p)


@pytest.mark.parametrize("conteudo", ["sources: 5\n", "sources: texto\n"])
def test_sources_que_nao_e_lista(tmp_path, conteudo):
    p = tmp_path / "sources.yaml"
    p.write_text(conteudo, encoding="utf-8")
    with pytest.raises(SourceError, match="'sources' deve ser uma lista"):
        load_sources(p)
