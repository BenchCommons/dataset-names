"""Critério de aceite 6: as listas legadas foram movidas sem alteração de conteúdo."""

import hashlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

ESPERADO = {
    "legacy/first_names.all.txt": "223d155b278dfccae6cfb04322d2c635bdce75206fc97424866e5e5d1b0e5624",
    "legacy/last_names.all.txt": "7c67486942cddc63f6fd03b418bc54e2f6c59aafc02dcf8d14bc367c21d466a6",
}


def test_listas_legadas_intactas():
    for caminho, sha in ESPERADO.items():
        assert hashlib.sha256((RAIZ / caminho).read_bytes()).hexdigest() == sha, caminho


def test_listas_nao_estao_mais_na_raiz():
    assert not (RAIZ / "first_names.all.txt").exists()
    assert not (RAIZ / "last_names.all.txt").exists()
    assert (RAIZ / "legacy" / "generate" / "index.sh").exists()
