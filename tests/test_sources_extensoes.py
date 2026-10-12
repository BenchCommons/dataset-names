"""Spec 002, R2 (campos opcionais) e a última recusa de R3 (retrieved e url)."""

from datetime import date, datetime

import pytest

from namescommons.sources import SourceError, load_sources, parse_sources


def fonte(**campos):
    base = {
        "id": "pt-exemplo", "name": "Exemplo", "url": "https://example.org/nomes",
        "license": "CC-BY-4.0", "attribution": "Exemplo", "country": "PT",
        "count_type": "births", "primary": True, "suppression": None,
        "retrieved": date(2026, 10, 1),
    }
    return {**base, **campos}


def test_campos_opcionais_tem_padrao():
    f = parse_sources([fonte()])["pt-exemplo"]
    assert (f.uniform_case, f.adapter) == (False, True)


def test_campos_opcionais_declarados():
    f = parse_sources([fonte(uniform_case=True, adapter=False)])["pt-exemplo"]
    assert (f.uniform_case, f.adapter) == (True, False)


@pytest.mark.parametrize("campo", ["uniform_case", "adapter", "strips_accents"])
@pytest.mark.parametrize("valor", ["sim", 1, None])
def test_campo_opcional_nao_booleano(campo, valor):
    with pytest.raises(SourceError, match=f"'{campo}' deve ser true ou false"):
        parse_sources([fonte(**{campo: valor})])


def test_retrieved_com_hora_e_recusado():
    with pytest.raises(SourceError, match="'retrieved' deve ser uma data AAAA-MM-DD"):
        parse_sources([fonte(retrieved=datetime(2026, 10, 1, 12, 30))])


def test_retrieved_com_hora_no_yaml_e_recusado(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(
        "sources:\n"
        "  - id: pt-exemplo\n"
        "    name: Exemplo\n"
        "    url: https://example.org/nomes\n"
        "    license: CC-BY-4.0\n"
        "    attribution: Exemplo\n"
        "    country: PT\n"
        "    count_type: births\n"
        "    primary: true\n"
        "    suppression: null\n"
        "    retrieved: 2026-10-01T10:00:00\n",
        encoding="utf-8",
    )
    with pytest.raises(SourceError, match="retrieved"):
        load_sources(p)


@pytest.mark.parametrize("url", [
    "ftp://example.org/nomes", "example.org/nomes", "file:///tmp/nomes.csv", "https://", "mailto:a@b.c",
    "http://[::1", " https://example.org/nomes", "https://example.org/nomes\n", "https://exam ple.org/",
])
def test_url_sem_esquema_http_e_recusada(url):
    with pytest.raises(SourceError, match="http ou https"):
        parse_sources([fonte(url=url)])


@pytest.mark.parametrize("url", ["http://example.org/a.csv", "HTTPS://example.org/"])
def test_url_http_e_https_aceitas(url):
    assert parse_sources([fonte(url=url)])["pt-exemplo"].url == url


def test_url_malformada_nomeia_a_fonte_em_vez_de_levantar_value_error():
    with pytest.raises(SourceError, match="pt-exemplo: 'url' deve usar o esquema http ou https"):
        parse_sources([fonte(url="http://[::1")])


def test_strips_accents_tem_padrao_false_e_aceita_true():
    """Spec 005, R6."""
    assert parse_sources([fonte()])["pt-exemplo"].strips_accents is False
    assert parse_sources([fonte(strips_accents=True)])["pt-exemplo"].strips_accents is True


def test_fontes_que_removem_acentos_em_sources_yaml():
    """Spec 005, R6: só as fontes com evidência registrada na spec."""
    from pathlib import Path
    fontes = load_sources(Path(__file__).resolve().parent.parent / "sources.yaml")
    assert sorted(f.id for f in fontes.values() if f.strips_accents) == [
        "ca-statcan-births", "es-ine-residentes", "us-ssa-births",
    ]
