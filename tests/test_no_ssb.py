"""Spec 003, R1.4, R1.5, R2.4 e R2.7: adaptadores do SSB (Noruega) sobre as amostras reais em tests/fixtures/no-ssb-*/."""

import json
from pathlib import Path

import pytest

from namesio.adapters import FormatError, RawRecord, load_adapter
from namesio.sources import SourceError, load_sources

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
FORNAVN = FIXTURES / "no-ssb-fornavn" / "10467.json"


def test_fornavn_da_amostra_real():
    mod = load_adapter("no-ssb-fornavn")
    assert list(mod.parse({"10467.json": FORNAVN})) == [
        RawRecord("Nora", "given", "NO", "F", 1990, 75),
        RawRecord("Nora", "given", "NO", "F", 2025, 357),
        RawRecord("Åse", "given", "NO", "F", 1990, 29),
        RawRecord("Åse", "given", "NO", "F", 2025, 64),
        RawRecord("Kim", "given", "NO", "F", 1990, 21),
        RawRecord("Kim", "given", "NO", "M", 1990, 401),
        RawRecord("Jakob", "given", "NO", "M", 1990, 32),
        RawRecord("Jakob", "given", "NO", "M", 2025, 297),
    ]


def test_etternavn_da_amostra_real():
    mod = load_adapter("no-ssb-etternavn")
    arquivo = FIXTURES / "no-ssb-etternavn" / "12891.json"
    assert list(mod.parse({"12891.json": arquivo})) == [
        RawRecord("Hansen", "family", "NO", None, 2020, 50582),
        RawRecord("Hansen", "family", "NO", None, 2025, 47879),
        RawRecord("Da Silva", "family", "NO", None, 2025, 219),
        RawRecord("Abdo", "family", "NO", None, 2025, 232),
    ]


def test_um_instituto_dois_count_types_sao_duas_fontes():
    fontes = load_sources(RAIZ / "sources.yaml")
    assert (fontes["no-ssb-fornavn"].count_type, fontes["no-ssb-etternavn"].count_type) == ("births", "population")


def test_country_no_sem_aspas_tem_mensagem_clara(tmp_path):
    texto = (RAIZ / "sources.yaml").read_text(encoding="utf-8").replace('country: "NO"', "country: NO")
    (tmp_path / "sources.yaml").write_text(texto, encoding="utf-8")
    with pytest.raises(SourceError, match='no-ssb-fornavn: país lido como booleano False; escreva o código entre aspas'):
        load_sources(tmp_path / "sources.yaml")


def _alterado(tmp_path, **mudancas) -> dict[str, Path]:
    dados = json.loads(FORNAVN.read_text(encoding="utf-8"))
    for chave, valor in mudancas.items():
        alvo = dados
        *caminho, ultimo = chave.split("__")
        for parte in caminho:
            alvo = alvo[parte]
        alvo[ultimo] = valor
    destino = tmp_path / "10467.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return {"10467.json": destino}


@pytest.mark.parametrize("mudancas, trecho", [
    ({"id": ["Fornavn", "Tid"]}, "esperava dataset com dimensões"),
    ({"status": {}}, "célula 0 vazia sem marcador conhecido"),
    ({"value": [1.5] * 15}, "célula 0 com valor 1.5"),
    ({"value": [1] * 14}, "lista densa de 15 células"),
])
def test_formato_inesperado_falha(tmp_path, mudancas, trecho):
    mod = load_adapter("no-ssb-fornavn")
    with pytest.raises(FormatError, match=trecho):
        list(mod.parse(_alterado(tmp_path, **mudancas)))


def test_prefixo_de_sexo_desconhecido_falha(tmp_path):
    dados = json.loads(FORNAVN.read_text(encoding="utf-8"))
    categoria = dados["dimension"]["Fornavn"]["category"]
    categoria["index"] = {("9" + c[1:] if c == "1NORA" else c): i for c, i in categoria["index"].items()}
    categoria["label"] = {("9" + c[1:] if c == "1NORA" else c): v for c, v in categoria["label"].items()}
    (tmp_path / "10467.json").write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    mod = load_adapter("no-ssb-fornavn")
    with pytest.raises(FormatError, match="prefixo de sexo '9' desconhecido"):
        list(mod.parse({"10467.json": tmp_path / "10467.json"}))
