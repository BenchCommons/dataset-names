"""Spec 004: adaptador do Wikidata sobre a amostra real em tests/fixtures/wikidata/."""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from namescommons.adapters import FormatError, RawRecord, load_adapter
from namescommons.sources import load_sources

RAIZ = Path(__file__).resolve().parent.parent
AMOSTRA = RAIZ / "tests" / "fixtures" / "wikidata"
wd = load_adapter("wikidata")


def _arquivos(pasta: Path = AMOSTRA) -> dict[str, Path]:
    return {r.filename: pasta / r.filename for r in wd.RESOURCES}


def test_fonte_registrada():
    f = load_sources(RAIZ / "sources.yaml")["wikidata"]
    assert (f.license, f.country, f.count_type, f.primary, f.suppression, f.uniform_case) == (
        "CC0-1.0", None, "attested", False, None, False)


def test_recursos_e_consultas():
    """R2.1 e R2.2: 15 páginas de consultas ordenadas no QLever, com o formato na URL."""
    assert [r.filename for r in wd.RESOURCES] == [
        "given-names-1.json", *(f"family-names-{k}.json" for k in range(1, 6)),
        *(f"links-P460-{k}.json" for k in range(1, 4)), "links-P1533-1.json", "links-P1560-1.json",
        "links-P5278-1.json", "links-P1889-1.json", "links-P1889-2.json", "transliterations-1.json",
    ]
    for r in wd.RESOURCES:
        partes = urlsplit(r.url)
        assert f"{partes.scheme}://{partes.netloc}{partes.path}" == "https://qlever.dev/api/wikidata"
        params = parse_qs(partes.query)
        assert params["action"] == ["sparql_json"]
        [texto] = params["query"]
        k = int(r.filename.rsplit("-", 1)[1].removesuffix(".json"))
        assert texto.endswith(f" LIMIT 200000 OFFSET {(k - 1) * 200000}")
        assert " ORDER BY ?item " in texto and "SELECT DISTINCT ?item " in texto
    [prenomes] = [r for r in wd.RESOURCES if r.filename == "given-names-1.json"]
    texto = parse_qs(urlsplit(prenomes.url).query)["query"][0]
    assert "?item wdt:P31/wdt:P279* wd:Q202444 . ?item wdt:P1705 ?name ." in texto
    assert "VALUES ?gender { wd:Q12308941 wd:Q11879590 wd:Q3409032 }" in texto
    assert "P5279" not in " ".join(r.url for r in wd.RESOURCES)  # R2.5: hyphenation não entra


def test_parse_da_amostra_real():
    """R3: um registro por gênero informado, sem país, ano nem contagem; rótulos inválidos pulados."""
    g, f = "given", "family"
    assert list(wd.parse(_arquivos())) == [
        RawRecord("Letha", g, None, "F"),
        RawRecord("Kadek", g, None, "F"), RawRecord("Kadek", g, None, "M"),
        RawRecord("Andrea", g, None, "F"), RawRecord("Andrea", g, None, "M"),
        RawRecord("Иван", g, None, "M"),
        RawRecord("Maria", g, None, "F"), RawRecord("Maria", g, None, "M"),
        RawRecord("Мария", g, None, "F"),
        RawRecord("John", g, None, "M"),
        RawRecord("Kim", g, None, "F"), RawRecord("Kim", g, None, "M"),
        RawRecord("Ivan", g, None, "M"),
        RawRecord("李", g),
        RawRecord("Kim", f),
        RawRecord("Иванов", f, None, "M"),
        RawRecord("Иванова", f, None, "F"),
        RawRecord("Ivanova", f), RawRecord("Ivanov", f), RawRecord("John", f), RawRecord("Silva", f),
        RawRecord("李", f),
    ]


def _pagina(pasta: Path, consulta, k: int, linhas: list[dict], variaveis=None) -> None:
    dados = {"head": {"vars": list(variaveis or consulta.variaveis)}, "results": {"bindings": linhas}}
    (pasta / consulta.arquivo(k)).write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


def _copia(tmp_path: Path) -> Path:
    for r in wd.RESOURCES:
        (tmp_path / r.filename).write_bytes((AMOSTRA / r.filename).read_bytes())
    return tmp_path


def _rotulo(qid: str, nome: str, genero: str | None = None, tipo: str = "literal") -> dict:
    linha = {"item": {"type": "uri", "value": f"http://www.wikidata.org/entity/{qid}"},
             "name": {"type": tipo, "value": nome, "xml:lang": "mul"}}
    if genero:
        linha["gender"] = {"type": "uri", "value": f"http://www.wikidata.org/entity/{genero}"}
    return linha


def test_genero_vazio_cede_ao_informado(tmp_path):
    """R3.5: sem gênero e com gênero no mesmo name_key e kind: a linha sem gênero é omitida."""
    pasta = _copia(tmp_path)
    _pagina(pasta, wd.PRENOMES, 1, [
        _rotulo("Q1", "Jan"), _rotulo("Q2", "JAN", "Q11879590"), _rotulo("Q3", "Jan ", "Q12308941"),
        _rotulo("Q4", "Eden"), _rotulo("Q5", "Eden"),
    ])
    assert [r for r in wd.parse(_arquivos(pasta)) if r.kind == "given"] == [
        RawRecord("Jan", "given", None, "F"), RawRecord("Jan", "given", None, "M"),
        RawRecord("Eden", "given"),
    ]


@pytest.mark.parametrize("nome", [
    "Q34147", "Ritwik (given name)", "Felbert,von", "Asil/Aseel", "Dau__tsch", "K8", "Lei⁵", "Li`", "  ",
])
def test_rotulos_que_nao_sao_nomes_sao_pulados(nome):
    assert not wd.nome_aceito(nome)


@pytest.mark.parametrize("nome", ["St. Simon", "D´Amici", "Camil·la", "O'Brien", "Jean-Luc", "সুভাষ", "ཚེ་དབང་"])
def test_nomes_aceitos(nome):
    assert wd.nome_aceito(nome)


def test_valor_desconhecido_e_pulado(tmp_path):
    pasta = _copia(tmp_path)
    _pagina(pasta, wd.PRENOMES, 1, [_rotulo("Q1", "http://www.wikidata.org/.well-known/genid/x", tipo="uri"),
                                    _rotulo("Q2", "Ana")])
    assert [r.name for r in wd.parse(_arquivos(pasta)) if r.kind == "given"] == ["Ana"]


def test_ultima_pagina_cheia_falha(tmp_path, monkeypatch):
    """R2.3: o Wikidata cresceu além das páginas fixas; falha alta, não perda silenciosa."""
    monkeypatch.setattr(wd, "LINHAS_POR_PAGINA", 2)
    pasta = _copia(tmp_path)
    _pagina(pasta, wd.PRENOMES, 1, [_rotulo("Q1", "Ana"), _rotulo("Q2", "Bia")])
    with pytest.raises(FormatError, match=r"given-names-1.json: última página cheia \(2 linhas\); aumente as páginas de 'given-names'"):
        list(wd.parse(_arquivos(pasta)))


def test_pagina_com_linhas_depois_de_incompleta_falha(tmp_path, monkeypatch):
    monkeypatch.setattr(wd, "LINHAS_POR_PAGINA", 2)
    pasta = _copia(tmp_path)
    _pagina(pasta, wd.PRENOMES, 1, [_rotulo("Q1", "Ana")])
    _pagina(pasta, wd.SOBRENOMES, 1, [_rotulo("Q1", "Silva"), _rotulo("Q2", "Souza")])
    _pagina(pasta, wd.SOBRENOMES, 2, [_rotulo("Q3", "Lima")])
    _pagina(pasta, wd.SOBRENOMES, 4, [_rotulo("Q4", "Costa")])
    with pytest.raises(FormatError, match="family-names-4.json: página com linhas depois da página incompleta "
                                          "family-names-2.json; .* fetch --refresh wikidata"):
        list(wd.parse(_arquivos(pasta)))


def test_pagina_acima_do_limite_falha(tmp_path, monkeypatch):
    monkeypatch.setattr(wd, "LINHAS_POR_PAGINA", 1)
    pasta = _copia(tmp_path)
    _pagina(pasta, wd.PRENOMES, 1, [_rotulo("Q1", "Ana"), _rotulo("Q2", "Bia")])
    with pytest.raises(FormatError, match="no máximo 1 linhas"):
        list(wd.parse(_arquivos(pasta)))


def test_cabecalho_inesperado_falha(tmp_path):
    pasta = _copia(tmp_path)
    _pagina(pasta, wd.PRENOMES, 1, [], variaveis=["item", "label", "gender"])
    with pytest.raises(FormatError, match=r"given-names-1.json: variáveis \['item', 'label', 'gender'\], esperava"):
        list(wd.parse(_arquivos(pasta)))
    (pasta / "given-names-1.json").write_text("<html>erro</html>", encoding="utf-8")
    with pytest.raises(FormatError, match="given-names-1.json: não é um resultado SPARQL JSON"):
        list(wd.parse(_arquivos(pasta)))


def test_classe_de_genero_desconhecida_falha(tmp_path):
    pasta = _copia(tmp_path)
    _pagina(pasta, wd.SOBRENOMES, 1, [_rotulo("Q1", "Silva", "Q12308941")])
    with pytest.raises(FormatError, match="family-names: classe de gênero .*Q12308941' desconhecida"):
        list(wd.parse(_arquivos(pasta)))


@pytest.mark.parametrize("item", [
    {"type": "literal", "value": "Q1"},
    {"type": "uri", "value": "http://www.wikidata.org/entity/P31"},
    {"type": "uri", "value": "https://example.org/Q1"},
])
def test_item_que_nao_e_entidade_falha(tmp_path, item):
    pasta = _copia(tmp_path)
    _pagina(pasta, wd.PRENOMES, 1, [{**_rotulo("Q1", "Ana"), "item": item}])
    with pytest.raises(FormatError, match="given-names: item .* não é entidade do Wikidata"):
        list(wd.parse(_arquivos(pasta)))


def test_nome_que_nao_e_literal_nem_desconhecido_falha(tmp_path):
    pasta = _copia(tmp_path)
    _pagina(pasta, wd.PRENOMES, 1, [{**_rotulo("Q1", "Ana"), "name": {"type": "typed-literal"}}])
    with pytest.raises(FormatError, match="given-names: name .* não é literal"):
        list(wd.parse(_arquivos(pasta)))
