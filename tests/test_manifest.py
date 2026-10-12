"""Spec 001, R5: contagem de linhas do manifest."""

import pytest

from namescommons.manifest import _linhas


@pytest.mark.parametrize("conteudo, esperado", [
    ("", 0),
    ("a,b\n", 0),
    ("a,b\n1,2\n", 1),
    ("a,b\n1,2\n\n", 1),
    ("a,b\n1,2\n\n\n3,4\n", 2),
    ('a,b\n"x\ny",2\n', 1),
])
def test_linhas_de_csv_nao_contam_cabecalho_nem_linhas_em_branco(tmp_path, conteudo, esperado):
    caminho = tmp_path / "t.csv"
    caminho.write_text(conteudo, encoding="utf-8")
    assert _linhas(caminho) == esperado
