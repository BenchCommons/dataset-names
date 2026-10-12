"""Spec 003, R1.2: adaptador do INSEE (França) sobre a amostra real em tests/fixtures/fr-insee-births/."""

import zipfile
from pathlib import Path

import pytest

from namescommons.adapters import FormatError, RawRecord, load_adapter
from namescommons.pipeline import to_observations
from namescommons.sources import load_sources

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = RAIZ / "tests" / "fixtures" / "fr-insee-births" / "prenoms-2025-nat_csv.zip"
ARQUIVO = "prenoms-2025-nat_csv.zip"


@pytest.fixture
def insee():
    return load_adapter("fr-insee-births")


def _zip(tmp_path, texto: str, membro: str = "prenoms-2025-nat.csv") -> dict[str, Path]:
    caminho = tmp_path / ARQUIVO
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr(membro, texto.encode("utf-8"))
    return {ARQUIVO: caminho}


def test_parse_da_amostra_real(insee):
    assert list(insee.parse({ARQUIVO: FIXTURE})) == [
        RawRecord("GABRIEL", "given", "FR", "M", 2025, 4625),
        RawRecord("LÉO", "given", "FR", "M", 2025, 3420),
        RawRecord("CAMILLE", "given", "FR", "M", 2025, 915),
        RawRecord("JEAN-BAPTISTE", "given", "FR", "M", 2025, 35),
        RawRecord("RARES", "given", "FR", "M", 2025, 15),
        RawRecord("N'GOLO", "given", "FR", "M", 2025, 5),
        RawRecord("LOUISE", "given", "FR", "F", 2025, 3070),
        RawRecord("CAMILLE", "given", "FR", "F", 2025, 640),
        RawRecord("JEAN", "given", "FR", "M", 1900, 14090),
        RawRecord("MARIE", "given", "FR", "F", 1900, 48695),
    ]


def test_rares_e_um_nome_real_e_nao_um_agregado(insee):
    # Rareș, sem diacrítico; o agregado das edições antigas se chamava _PRENOMS_RARES.
    assert RawRecord("RARES", "given", "FR", "M", 2025, 15) in list(insee.parse({ARQUIVO: FIXTURE}))


def test_caixa_uniforme_da_fonte_gera_nomes_capitalizados(insee):
    fonte = load_sources(RAIZ / "sources.yaml")["fr-insee-births"]
    nomes = sorted({o.name for o in to_observations(insee.parse({ARQUIVO: FIXTURE}), fonte)})
    assert nomes == ["Camille", "Gabriel", "Jean", "Jean-Baptiste", "Louise", "Léo", "Marie", "N'Golo", "Rares"]


def test_pula_agregados_de_edicoes_anteriores(insee, tmp_path):
    texto = "sexe;prenom;periode;valeur;rang\r\n1;_PRENOMS_RARES;2020;9000;\r\n1;ANA;XXXX;30;\r\n2;ANA;2020;10;5\r\n"
    assert list(insee.parse(_zip(tmp_path, texto))) == [RawRecord("ANA", "given", "FR", "F", 2020, 10)]


def test_aceita_bom(insee, tmp_path):
    texto = "﻿sexe;prenom;periode;valeur;rang\r\n2;ANA;2020;10;5\r\n"
    assert len(list(insee.parse(_zip(tmp_path, texto)))) == 1


@pytest.mark.parametrize("texto, trecho", [
    ("sexe;preusuel;annais;nombre\r\n1;ANA;2020;10\r\n", "colunas ausentes \\['periode', 'prenom', 'valeur'\\]"),
    ("sexe;prenom;periode;valeur;rang\r\nF;ANA;2020;10;5\r\n", "sexe 'F' desconhecido"),
    ("sexe;prenom;periode;valeur;rang\r\n2;ANA;2020;n.d.;5\r\n", "contagem 'n.d.'"),
    ("sexe;prenom;periode;valeur;rang\r\n2;ANA;19xx;10;5\r\n", "periode '19xx'"),
])
def test_formato_inesperado_falha(insee, tmp_path, texto, trecho):
    with pytest.raises(FormatError, match=trecho):
        list(insee.parse(_zip(tmp_path, texto)))


def test_zip_sem_um_unico_csv_falha(insee, tmp_path):
    with pytest.raises(FormatError, match="esperava um CSV no ZIP"):
        list(insee.parse(_zip(tmp_path, "x", membro="leia.txt")))


def test_nome_com_sublinhado_que_nao_e_o_agregado_conhecido_falha(insee, tmp_path):
    texto = "sexe;prenom;periode;valeur;rang\r\n1;_PRENOMS_NOVOS;2020;9000;\r\n"
    with pytest.raises(FormatError, match="prenom '_PRENOMS_NOVOS' começa com _ e não é o agregado conhecido"):
        list(insee.parse(_zip(tmp_path, texto)))


def test_valeur_vazio_falha(insee, tmp_path):
    texto = "sexe;prenom;periode;valeur;rang\r\n2;ANA;2020;;5\r\n"
    with pytest.raises(FormatError, match="contagem ''"):
        list(insee.parse(_zip(tmp_path, texto)))
