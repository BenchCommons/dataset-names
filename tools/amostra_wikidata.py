"""Gera a amostra de tests/fixtures/wikidata/ com as consultas do adaptador (spec 004, R6).

Cada arquivo é a resposta real do QLever à mesma consulta do adaptador, restrita aos itens abaixo
(VALUES ?item) e com a mesma paginação; páginas além do fim vêm vazias. A chave "meta" (tempo de
consulta, varia a cada execução) é removida. Nas ligações, só ficam as linhas cujo alvo também está
na amostra, mais a primeira de cada propriedade com alvo fora dela (para testar o descarte de R4.4).
Acessa a rede: não roda nos testes.

Uso: uv run python tools/amostra_wikidata.py tests/fixtures/wikidata
"""

import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

from namescommons import USER_AGENT
from namescommons.adapters import wikidata

PRENOMES = (
    "Q325872 Q25413386 Q39897333 Q18177306 Q18177321 Q493293 Q637123 Q21104340 Q830350 "
    "Q4925477 Q96209920 Q104829915 Q102313297 Q100275460 Q112158404"
).split()
SOBRENOMES = (
    "Q16654835 Q21447935 Q40711158 Q37456871 Q6327150 Q686223 Q157414 Q5281981 Q110770321 Q111757901"
).split()
TRANSLITERADOS = "Q16654835 Q21447935 Q39897333 Q4925477 Q493293 Q686223".split()


def itens(consulta: wikidata.Consulta) -> tuple[str, ...]:
    if consulta is wikidata.PRENOMES:
        return tuple(PRENOMES)
    if consulta is wikidata.SOBRENOMES:
        return tuple(SOBRENOMES)
    if consulta is wikidata.TRANSLITERACOES:
        return tuple(TRANSLITERADOS)
    return tuple(PRENOMES + SOBRENOMES)


def _filtrar_alvos(linhas: list[dict]) -> list[dict]:
    amostra = {f"http://www.wikidata.org/entity/{q}" for q in PRENOMES + SOBRENOMES}
    fora = [l for l in linhas if l["target"]["value"] not in amostra][:1]
    return [l for l in linhas if l["target"]["value"] in amostra or l in fora]


def main(destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    for consulta in wikidata.CONSULTAS:
        for k in range(1, consulta.paginas + 1):
            texto = consulta.sparql(k, itens(consulta))
            endereco = f"{wikidata.ENDPOINT}?{urlencode({'query': texto, 'action': 'sparql_json'})}"
            pedido = urllib.request.Request(endereco, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(pedido, timeout=120) as resposta:
                dados = json.load(resposta)
            dados.pop("meta", None)
            if consulta.nome.startswith("links-"):
                dados["results"]["bindings"] = _filtrar_alvos(dados["results"]["bindings"])
            (destino / consulta.arquivo(k)).write_text(
                json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
            )
            print(consulta.arquivo(k), len(dados["results"]["bindings"]))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
