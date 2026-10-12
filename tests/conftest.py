"""Fixture do critério de aceite 3 da spec 001: duas fontes births no mesmo país (uma primary),
uma population, uma attested; escritas latina, cirílica e chinesa; nome com espaço.
Servidor HTTP local da spec 002 (R7): downloads testados sem rede."""

import sys
import threading
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from namescommons.adapters import Resource
from namescommons.schema import make_observation
from namescommons.sources import parse_sources

FONTES = [
    {"id": "us-ssa", "name": "SSA", "url": "https://www.ssa.gov/oact/babynames/",
     "license": "public-domain", "attribution": "SSA", "country": "US",
     "count_type": "births", "primary": True, "suppression": 5, "retrieved": date(2026, 10, 1)},
    {"id": "us-births-b", "name": "Outra fonte de nascimentos dos EUA", "url": "https://example.org/b",
     "license": "CC-BY-4.0", "attribution": "Exemplo", "country": "US",
     "count_type": "births", "primary": False, "suppression": None, "retrieved": date(2026, 10, 1)},
    {"id": "br-ibge-censo", "name": "IBGE Censo", "url": "https://censo2022.ibge.gov.br/nomes/",
     "license": "CC-BY-4.0", "attribution": "IBGE", "country": "BR",
     "count_type": "population", "primary": True, "suppression": None, "retrieved": date(2026, 10, 1)},
    {"id": "wikidata", "name": "Wikidata", "url": "https://www.wikidata.org/",
     "license": "CC0-1.0", "attribution": "Wikidata", "country": None,
     "count_type": "attested", "primary": False, "suppression": None, "retrieved": date(2026, 10, 1)},
]


def _obs():
    g, f = "given", "family"
    us = dict(country="US", count_type="births")
    br = dict(country="BR", count_type="population", source_id="br-ibge-censo")
    wd = dict(count_type="attested", source_id="wikidata")
    return [
        make_observation("Maria", kind=g, source_id="us-ssa", gender="F", year=2020, count=100, **us),
        make_observation("Maria", kind=g, source_id="us-ssa", gender="F", year=2021, count=50, **us),
        make_observation("Maria", kind=g, source_id="us-ssa", gender="M", year=2021, count=5, **us),
        make_observation("James", kind=g, source_id="us-ssa", gender="M", year=2021, count=200, **us),
        make_observation("Deshawn", kind=g, source_id="us-ssa", gender="M", year=2021, count=30, **us),
        make_observation("Maria", kind=g, source_id="us-births-b", gender="F", year=2021, count=999, **us),
        make_observation("DeShawn", kind=g, source_id="us-births-b", gender="M", year=2021, count=40, **us),
        make_observation("Ana Clara", kind=g, source_id="us-births-b", gender="F", year=2021, count=7, **us),
        make_observation("MARIA", kind=g, gender="F", year=2010, count=11000, **br),
        make_observation("MARIA", kind=g, gender="M", year=2010, count=300, **br),
        make_observation("MARIA", kind=g, gender="F", year=2022, count=12000, **br),
        make_observation("ANA CLARA", kind=g, gender="F", year=2022, count=800, **br),
        make_observation("SILVA", kind=f, year=2022, count=5000, **br),
        make_observation("Мария", kind=g, **wd),
        make_observation("Maria", kind=g, **wd),
        make_observation("李", kind=f, **wd),
    ]


@pytest.fixture
def fontes():
    return parse_sources(FONTES)


@pytest.fixture
def observacoes():
    return _obs()


class ServidorLocal:
    """Servidor HTTP em 127.0.0.1 com respostas programáveis por caminho."""

    def __init__(self):
        self.arquivos: dict[str, bytes] = {}
        self.falhas: dict[str, int] = {}  # caminho -> quantas respostas 500 antes de servir
        self.truncados: set[str] = set()  # caminhos que anunciam o dobro do tamanho e fecham
        self.lentos: dict[str, float] = {}  # caminho -> segundos de espera antes de responder
        self.recusados: set[str] = set()  # caminhos que respondem 403, como um servidor que bloqueia robôs
        self.requisicoes: list[tuple[str, str]] = []  # (caminho, User-Agent)
        servidor = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                servidor.requisicoes.append((self.path, self.headers.get("User-Agent", "")))
                if self.path in servidor.recusados:
                    self.send_error(403)
                    return
                if servidor.falhas.get(self.path, 0) > 0:
                    servidor.falhas[self.path] -= 1
                    self.send_error(500)
                    return
                time.sleep(servidor.lentos.get(self.path, 0))
                corpo = servidor.arquivos.get(self.path)
                if corpo is None:
                    self.send_error(404)
                    return
                anunciado = len(corpo) * 2 if self.path in servidor.truncados else len(corpo)
                self.send_response(200)
                self.send_header("Content-Length", str(anunciado))
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, *args):
                pass

        class Servidor(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                # Cliente que desiste (timeout) fecha a conexão; isso não é falha do teste.
                if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
                    return
                super().handle_error(request, client_address)

        self.httpd = Servidor(("127.0.0.1", 0), Handler)

    def url(self, caminho: str) -> str:
        return f"http://127.0.0.1:{self.httpd.server_port}{caminho}"

    def caminhos(self) -> list[str]:
        return [caminho for caminho, _ in self.requisicoes]


@pytest.fixture
def servidor():
    s = ServidorLocal()
    thread = threading.Thread(target=s.httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield s
    s.httpd.shutdown()
    s.httpd.server_close()


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def servir_fixtures(servidor, monkeypatch):
    """Spec 003, R2.5: serve tests/fixtures/<SOURCE_ID>/<filename> no servidor local e aponta
    RESOURCES do módulo do adaptador para ele. Uso: servir_fixtures(modulo) -> servidor."""

    def servir(modulo):
        recursos = []
        for r in modulo.RESOURCES:
            caminho = f"/{modulo.SOURCE_ID}/{r.filename}"
            servidor.arquivos[caminho] = (FIXTURES / modulo.SOURCE_ID / r.filename).read_bytes()
            recursos.append(Resource(servidor.url(caminho), r.filename))
        monkeypatch.setattr(modulo, "RESOURCES", recursos)
        return servidor

    return servir
