# 003. Fontes oficiais: tarefas

> Roteiro histórico da implementação (PR #11). O código vigente está em `src/` e `tests/`; em divergência, vale o código.

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar todos os comandos na raiz do repositório, a partir de `master` com a spec 002. Antes da Task 1, rodar `uv sync` e conferir `uv run pytest -q` com `244 passed`.

Os arquivos de `src/` que já existem aparecem inteiros: substituir o conteúdo do arquivo pelo bloco. A linha **Mudanças** resume o que difere da versão anterior. Em `sources.yaml` e `tests/fixtures/ATRIBUICAO.md`, as Tasks 3 a 5 acrescentam linhas ao fim do arquivo criado na Task 2.

As amostras de `tests/fixtures/` são trechos dos arquivos reais (spec 003, R3). Os ZIPs e os CSVs com BOM são gerados por um script curto, para que os bytes de controle (BOM, CRLF) não dependam do editor.

---

### Task 1: regras do contrato do adaptador (issue #8)

**Arquivos:**
- Modificar: `src/namesio/adapters/__init__.py`, `src/namesio/pipeline.py`
- Modificar (teste): `tests/conftest.py`, `tests/test_pipeline.py`
- Teste: `tests/test_contrato_adaptador.py`

**Interfaces:**
- Consome: `RawRecord`, `Resource`, `AdapterError`, `load_adapter` (spec 002, Task 5); `to_observations`, `ingest_sources` (spec 002, Task 7); `is_country` (spec 001); `KINDS`, `GENDERS` de `namesio.schema`; fixture `servidor` (spec 002, Task 6).
- Produz: `namesio.adapters.FormatError(ValueError)`; `SourceFiles(dict)` com `AdapterError` para chave ausente; `parse_count(value, missing=(), field="contagem") -> int | None`; `parse_code(value, mapping, field) -> str`; `load_adapter` com mensagens "ausente (esperado em <caminho>)", "quebrado: <exceção>" e "pacote '<p>' não encontrado". `to_observations` recusa, na ordem de `parse`, `kind`, `gender` e `country` inválidos, `count` vazio em fonte com contagem e `count` em fonte `attested` (`RecordError` com `registro N: ...`). `FormatError` entra nas mensagens de domínio de `PipelineError`. Fixtures de teste `servir_fixtures(modulo) -> servidor` e `servidor.recusados: set[str]` (403).

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_contrato_adaptador.py`

```python
"""Spec 003, R2: regras do contrato do adaptador que a spec 002 deixou implícitas (issue #8)."""

import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

from namesio.adapters import (
    AdapterError, FormatError, RawRecord, SourceFiles, load_adapter, parse_code, parse_count,
)
from namesio.pipeline import PipelineError, RecordError, ingest_sources, select_sources, to_observations
from namesio.sources import load_sources, parse_sources

FIXTURES = Path(__file__).parent / "fixtures"


def _fonte(**campos):
    base = {"id": "pt-x", "name": "x", "url": "https://x.example", "license": "CC0-1.0",
            "attribution": "x", "country": "PT", "count_type": "births", "primary": True,
            "suppression": None, "retrieved": date(2026, 1, 1)}
    return next(iter(parse_sources([{**base, **campos}]).values()))


# R2.1: o adaptador converte os valores; o pipeline confere na ordem do arquivo -------------------

@pytest.mark.parametrize("campos, trecho", [
    ({"kind": "first"}, "registro 2: kind 'first' inválido; use 'given' ou 'family'"),
    ({"gender": "Mujer"}, "registro 2: gender 'Mujer' inválido; use 'F', 'M' ou vazio"),
    ({"gender": "1"}, "registro 2: gender '1' inválido"),
    ({"country": "PRT"}, "registro 2: country 'PRT' fora da ISO 3166-1 alfa-2"),
    ({"country": "pt"}, "registro 2: country 'pt' fora da ISO 3166-1 alfa-2"),
])
def test_r2_1_valor_nao_convertido_nomeia_a_posicao_no_arquivo(campos, trecho):
    ok = {"name": "Ana", "kind": "given", "country": "PT", "gender": "F", "year": 2020, "count": 1}
    ruim = RawRecord(**{**ok, "name": "Maria", **campos})
    with pytest.raises(RecordError) as e:
        to_observations([RawRecord(**ok), ruim], _fonte())
    assert str(e.value).startswith(trecho)


# R2.2: auxiliares de conversão ------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [("5", 5), (" 1532 ", 1532), ("0", 0), ("<5", None), ("..", None)])
def test_r2_2_parse_count(texto, esperado):
    assert parse_count(texto, {"<5", ".."}) == esperado


@pytest.mark.parametrize("texto", ["", "1.5", "-3", "x", "<3", "١٢"])
def test_r2_2_parse_count_recusa_o_que_nao_conhece(texto):
    with pytest.raises(FormatError, match="contagem"):
        parse_count(texto, {"<5"})


def test_r2_2_parse_code_traduz_e_recusa_codigo_desconhecido():
    sexo = {"1": "M", "2": "F"}
    assert parse_code(" 2 ", sexo, "sexo") == "F"
    with pytest.raises(FormatError, match=r"sexo 'M' desconhecido; esperado um de \['1', '2'\]"):
        parse_code("M", sexo, "sexo")


# R2.3: valores suprimidos são omitidos, nunca emitidos com count vazio ------------------------------

def test_r2_3_count_vazio_em_fonte_com_contagem_e_recusado():
    with pytest.raises(RecordError, match="registro 1: count vazio numa fonte 'population'; valor suprimido"):
        to_observations([RawRecord("Ana", "given", "PT", "F", 2020, None)], _fonte(count_type="population"))


def test_r2_3_count_em_fonte_attested_e_recusado():
    with pytest.raises(RecordError, match="registro 1: count 3 numa fonte 'attested'"):
        to_observations([RawRecord("Ana", "given", None, None, None, 3)],
                        _fonte(country=None, count_type="attested"))


# R2.5: teste de adaptador contra o servidor local ----------------------------------------------

def test_r2_5_servir_fixtures_baixa_do_servidor_local(servir_fixtures, tmp_path):
    import adaptadores.exemplo
    servidor = servir_fixtures(adaptadores.exemplo)
    fontes = load_sources(FIXTURES / "sources.yaml")
    obs = ingest_sources(select_sources(fontes, ["exemplo"]), fontes, tmp_path, adapters="adaptadores")
    assert len(obs) == 8
    assert sorted(servidor.caminhos()) == ["/exemplo/primeiros.csv", "/exemplo/sobrenomes.csv"]
    assert all(r.url.startswith("http://127.0.0.1:") for r in adaptadores.exemplo.RESOURCES)


# R2.6: mensagens de erro --------------------------------------------------------------------------

def test_r2_6_arquivo_fora_de_resources_lista_os_disponiveis():
    arquivos = SourceFiles({"a.csv": Path("a.csv")})
    with pytest.raises(AdapterError, match=r"parse pediu o arquivo 'b.csv', fora de RESOURCES; disponíveis: \['a.csv'\]"):
        arquivos["b.csv"]


def test_r2_6_ingest_com_chave_errada_nomeia_a_fonte(tmp_path, monkeypatch):
    import adaptadores.exemplo
    monkeypatch.setattr(adaptadores.exemplo, "parse", lambda arquivos: iter([arquivos["nomes.csv"]]))
    shutil.copytree(FIXTURES / "exemplo", tmp_path / "exemplo")
    fontes = load_sources(FIXTURES / "sources.yaml")
    with pytest.raises(PipelineError, match="fonte 'exemplo': parse pediu o arquivo 'nomes.csv'"):
        ingest_sources([fontes["exemplo"]], fontes, tmp_path, offline=True, adapters="adaptadores")


def test_r2_6_adaptador_ausente_mostra_o_caminho_esperado():
    with pytest.raises(AdapterError) as e:
        load_adapter("nao-existe", "adaptadores")
    mensagem = str(e.value)
    assert "adaptador adaptadores.nao_existe ausente" in mensagem
    assert str(Path(__file__).parent / "adaptadores" / "nao_existe.py") in mensagem


def test_r2_6_adaptador_quebrado_nao_se_passa_por_ausente(tmp_path, monkeypatch):
    pacote = tmp_path / "quebrados"
    pacote.mkdir()
    (pacote / "__init__.py").write_text("", encoding="utf-8")
    (pacote / "fonte_x.py").write_text("import modulo_que_nao_existe\n", encoding="utf-8")
    (pacote / "fonte_y.py").write_text("1/0\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(AdapterError, match="adaptador quebrados.fonte_x quebrado: ModuleNotFoundError: .*modulo_que_nao_existe"):
        load_adapter("fonte-x", "quebrados")
    with pytest.raises(AdapterError, match="adaptador quebrados.fonte_y quebrado: ZeroDivisionError"):
        load_adapter("fonte-y", "quebrados")
    for nome in ("quebrados", "quebrados.fonte_x", "quebrados.fonte_y"):
        sys.modules.pop(nome, None)


def test_r2_6_pacote_de_adaptadores_inexistente():
    with pytest.raises(AdapterError, match="pacote 'nao_ha_pacote' não encontrado"):
        load_adapter("x", "nao_ha_pacote")
```

- [ ] **Passo 2: substituir o conteúdo de** `tests/conftest.py`

**Mudanças:** importa `Path` e `Resource`; `ServidorLocal.recusados` responde 403; fixture `servir_fixtures`.

```python
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

from namesio.adapters import Resource
from namesio.schema import make_observation
from namesio.sources import parse_sources

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
```

- [ ] **Passo 3: ajustar** `tests/test_pipeline.py`

Trocar:

```python
def test_r1_4_repetidos_com_e_sem_contagem_sao_recusados():
    with pytest.raises(RecordError, match="R1.4"):
```

por:

```python
def test_r1_4_repetidos_com_e_sem_contagem_sao_recusados():
    # Desde a spec 003 (R2.3), count vazio numa fonte births é recusado já no registro.
    with pytest.raises(RecordError, match="registro 2: count vazio numa fonte 'births'"):
```

- [ ] **Passo 4: rodar e ver falhar**

Rodar: `uv run pytest -q`
Esperado: `1 error` na coleta (`ImportError: cannot import name 'FormatError'`)

- [ ] **Passo 5: substituir o conteúdo de** `src/namesio/adapters/__init__.py`

**Mudanças:** docstring com as regras da spec 003; importa `importlib.util`, `re`, `Iterable`, `Mapping`, `Path`; `FormatError`; `load_adapter` separa ausente de quebrado e mostra o caminho esperado (`_caminho_esperado`); `SourceFiles`, `parse_count`, `parse_code`.

```python
"""Contrato do adaptador de fonte (spec 002, R1, com as regras da spec 003, R2).

Cada fonte com adaptador tem um módulo <pacote>.<id_com_underscore> que expõe
SOURCE_ID, RESOURCES (lista de Resource) e parse(files) -> Iterator[RawRecord].
O adaptador converte os valores da fonte: year e count como int, gender como F ou M,
country em ISO 3166-1 alfa-2, kind como given ou family. Valores suprimidos são omitidos.
"""

import importlib
import importlib.util
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from urllib.parse import urlsplit

DEFAULT_PACKAGE = "namesio.adapters"


class AdapterError(Exception):
    """Adaptador ausente ou fora do contrato de R1."""


class FormatError(ValueError):
    """Arquivo da fonte fora do formato que o adaptador espera (spec 003, R2.2)."""


@dataclass(frozen=True)
class Resource:
    url: str
    filename: str


@dataclass(frozen=True)
class RawRecord:
    """Registro como a fonte publica; o pipeline o transforma em Observation."""

    name: str
    kind: str
    country: str | None = None
    gender: str | None = None
    year: int | None = None
    count: int | None = None


def module_name(source_id: str) -> str:
    return source_id.replace("-", "_")


def _filename_seguro(nome: object) -> bool:
    return (
        isinstance(nome, str) and nome not in ("", ".", "..") and not nome.startswith(".")
        and "/" not in nome and "\\" not in nome
        and not nome.endswith((".meta.json", ".part"))
    )


def check_adapter(mod: object, source_id: str) -> None:
    """Levanta AdapterError se o módulo não cumpre o contrato de R1."""
    for atributo in ("SOURCE_ID", "RESOURCES", "parse"):
        if not hasattr(mod, atributo):
            raise AdapterError(f"adaptador de '{source_id}' sem {atributo}")
    if mod.SOURCE_ID != source_id:
        raise AdapterError(f"SOURCE_ID '{mod.SOURCE_ID}' diverge do id '{source_id}' em sources.yaml")
    recursos = mod.RESOURCES
    if not isinstance(recursos, (list, tuple)) or not recursos or not all(
        isinstance(r, Resource) for r in recursos
    ):
        raise AdapterError(f"'{source_id}': RESOURCES deve ser uma lista não vazia de Resource")
    vistos: set[str] = set()
    for r in recursos:
        partes = urlsplit(r.url)
        if partes.scheme.lower() not in ("http", "https") or not partes.netloc:
            raise AdapterError(f"'{source_id}': url {r.url!r} deve usar http ou https")
        if not _filename_seguro(r.filename):
            raise AdapterError(f"'{source_id}': filename {r.filename!r} inválido")
        if r.filename in vistos:
            raise AdapterError(f"'{source_id}': filename {r.filename!r} repetido")
        vistos.add(r.filename)
    if not callable(mod.parse):
        raise AdapterError(f"'{source_id}': parse deve ser uma função")


def _caminho_esperado(package: str, modulo: str) -> str:
    try:
        spec = importlib.util.find_spec(package)
    except ImportError:
        spec = None
    if spec is None or not spec.submodule_search_locations:
        return f"pacote {package!r} não encontrado"
    return str(Path(list(spec.submodule_search_locations)[0]) / f"{modulo}.py")


def load_adapter(source_id: str, package: str = DEFAULT_PACKAGE) -> ModuleType:
    nome = f"{package}.{module_name(source_id)}"
    try:
        mod = importlib.import_module(nome)
    except ModuleNotFoundError as e:
        if e.name is not None and (nome == e.name or nome.startswith(e.name + ".")):
            esperado = _caminho_esperado(package, module_name(source_id))
            raise AdapterError(f"adaptador {nome} ausente (esperado em {esperado})") from e
        raise AdapterError(f"adaptador {nome} quebrado: {type(e).__name__}: {e}") from e
    except Exception as e:
        raise AdapterError(f"adaptador {nome} quebrado: {type(e).__name__}: {e}") from e
    check_adapter(mod, source_id)
    return mod


class SourceFiles(dict):
    """Arquivos baixados de uma fonte (chave = filename); chave fora de RESOURCES gera AdapterError."""

    def __missing__(self, chave):
        raise AdapterError(f"parse pediu o arquivo {chave!r}, fora de RESOURCES; disponíveis: {sorted(self)}")


_INTEIRO = re.compile(r"[0-9]+")


def parse_count(value: str, missing: Iterable[str] = (), field: str = "contagem") -> int | None:
    """Inteiro publicado (contagem ou ano); um marcador de `missing` (valor suprimido ou ausente) vira None.

    Qualquer outro texto levanta FormatError, para que um marcador novo da fonte não passe calado.
    """
    texto = value.strip()
    if texto in missing:
        return None
    if _INTEIRO.fullmatch(texto):
        return int(texto)
    raise FormatError(f"{field} {value!r} não é inteiro nem marcador conhecido {sorted(missing)}")


def parse_code(value: str, mapping: Mapping[str, str], field: str) -> str:
    """Traduz um código da fonte (ex.: sexo '1' e '2') pelo mapeamento; código desconhecido é FormatError."""
    try:
        return mapping[value.strip()]
    except KeyError:
        raise FormatError(f"{field} {value!r} desconhecido; esperado um de {sorted(mapping)}") from None
```

- [ ] **Passo 6: substituir o conteúdo de** `src/namesio/pipeline.py`

**Mudanças:** importa `FormatError`, `SourceFiles`, `GENDERS`, `KINDS` e `is_country`; `FormatError` em `_ERROS_DO_DOMINIO`; `_checar_valores` chamado por registro em `to_observations`; `ingest_sources` passa `SourceFiles` a `parse`.

```python
"""Pipeline de ingestão (spec 002, R1 e R5): fontes -> cache -> parse -> observações."""

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from namesio.adapters import (
    DEFAULT_PACKAGE, AdapterError, FormatError, RawRecord, SourceFiles, load_adapter,
)
from namesio.cache import FetchError, fetch_resource
from namesio.schema import GENDERS, KINDS, Observation, ValidationError, derive_name_fields, validate
from namesio.sources import Source, is_country


class PipelineError(Exception):
    """Falha de uma fonte em fetch ou ingest; a mensagem nomeia a fonte e a causa."""


class RecordError(ValueError):
    """Registros de uma fonte que violam R1.4 ou R1.5."""


# Exceções cuja mensagem já explica a causa; as demais ganham o nome do tipo.
_ERROS_DO_DOMINIO = (AdapterError, FetchError, ValidationError, RecordError, FormatError)


def _falha(fonte: Source, e: Exception) -> PipelineError:
    causa = str(e) if isinstance(e, _ERROS_DO_DOMINIO) else f"{type(e).__name__}: {e}"
    return PipelineError(f"fonte '{fonte.id}': {causa}")


def _vazio(valor: str | None) -> str | None:
    """R1.1: vazio e só espaços viram None; espaços em volta são removidos."""
    if valor is None:
        return None
    return valor.strip() or None


def _ordem(o: Observation) -> tuple:
    return (o.source_id, o.kind, o.country or "", o.name_key, -1 if o.year is None else o.year, o.gender or "")


def _somar(a: Observation, b: Observation) -> Observation:
    """R1.4: soma duas observações com a mesma chave; mantém a forma do primeiro registro."""
    if (a.count is None) != (b.count is None):
        raise RecordError(f"R1.4: registros repetidos com e sem count para {a.key()}")
    return a if a.count is None else replace(a, count=a.count + b.count)


def _checar_genero(observacoes: Iterable[Observation]) -> None:
    """R1.5: total sem gender e divisão por gender não podem coexistir no mesmo grupo."""
    com: set[tuple] = set()
    sem: set[tuple] = set()
    for o in observacoes:
        (com if o.gender is not None else sem).add((o.name_key, o.kind, o.country, o.year))
    conflitos = sorted(com & sem, key=repr)
    if conflitos:
        raise RecordError(
            f"R1.5: {len(conflitos)} grupo(s) com linhas com e sem gender, ex.: {conflitos[0]}"
        )


def _checar_tipos(r: RawRecord, posicao: int) -> None:
    """Rejeita tipos errados nos campos do registro, nomeando campo, valor e posição (1 = primeiro)."""
    for campo in ("year", "count"):
        v = getattr(r, campo)
        if v is not None and (type(v) is not int):
            raise RecordError(
                f"registro {posicao}: '{campo}' deve ser inteiro, recebeu {type(v).__name__} {v!r}"
            )
    for campo in ("name", "kind", "country", "gender"):
        v = getattr(r, campo)
        if v is not None and not isinstance(v, str):
            raise RecordError(
                f"registro {posicao}: '{campo}' deve ser texto, recebeu {type(v).__name__} {v!r}"
            )


def _checar_valores(o: Observation, posicao: int, paises: dict[str, bool]) -> None:
    """Spec 003, R2.1 e R2.3: valores convertidos pelo adaptador, conferidos na ordem do arquivo."""
    if o.kind not in KINDS:
        raise RecordError(f"registro {posicao}: kind {o.kind!r} inválido; use 'given' ou 'family'")
    if o.gender is not None and o.gender not in GENDERS:
        raise RecordError(f"registro {posicao}: gender {o.gender!r} inválido; use 'F', 'M' ou vazio")
    if o.country is not None:
        valido = paises.get(o.country)
        if valido is None:
            valido = paises[o.country] = is_country(o.country)
        if not valido:
            raise RecordError(f"registro {posicao}: country {o.country!r} fora da ISO 3166-1 alfa-2")
    if o.count is None and o.count_type != "attested":
        raise RecordError(
            f"registro {posicao}: count vazio numa fonte '{o.count_type}'; "
            "valor suprimido deve ser omitido pelo adaptador"
        )
    if o.count is not None and o.count_type == "attested":
        raise RecordError(f"registro {posicao}: count {o.count} numa fonte 'attested'")


def to_observations(records: Iterable[RawRecord], source: Source) -> list[Observation]:
    """Aplica R1.1 a R1.5 aos registros brutos de uma fonte."""
    derivados: dict[str, tuple[str, str, str, str]] = {}
    paises: dict[str, bool] = {}
    unicas: dict[tuple, Observation] = {}
    for posicao, r in enumerate(records, start=1):
        _checar_tipos(r, posicao)
        campos = derivados.get(r.name)
        if campos is None:
            campos = derivados[r.name] = derive_name_fields(r.name, source.uniform_case)
        nome, chave, forma_ascii, escrita = campos
        o = Observation(
            name=nome, name_key=chave, ascii=forma_ascii, script=escrita, kind=r.kind,
            country=_vazio(r.country), gender=_vazio(r.gender), year=r.year, count=r.count,
            count_type=source.count_type, source_id=source.id,
        )
        _checar_valores(o, posicao, paises)
        anterior = unicas.get(o.key())
        unicas[o.key()] = o if anterior is None else _somar(anterior, o)
    _checar_genero(unicas.values())
    return sorted(unicas.values(), key=_ordem)


def select_sources(sources: dict[str, Source], ids: list[str]) -> list[Source]:
    """Fontes indicadas, ou todas com adaptador se nenhuma for indicada."""
    if not ids:
        escolhidas = [f for f in sources.values() if f.adapter]
        if not escolhidas:
            raise PipelineError("nenhuma fonte com adaptador em sources.yaml")
        return sorted(escolhidas, key=lambda f: f.id)
    escolhidas = []
    for i in dict.fromkeys(ids):
        if i not in sources:
            raise PipelineError(f"fonte '{i}' ausente de sources.yaml")
        if not sources[i].adapter:
            raise PipelineError(f"fonte '{i}' tem adapter: false e não pode ser baixada nem ingerida")
        escolhidas.append(sources[i])
    return escolhidas


def fetch_sources(
    selected: list[Source],
    cache_dir: Path,
    *,
    refresh: bool = False,
    adapters: str = DEFAULT_PACKAGE,
    **opcoes,
) -> None:
    """Baixa os recursos de cada fonte para o cache (R4); para na primeira fonte que falhar."""
    for fonte in selected:
        try:
            mod = load_adapter(fonte.id, adapters)
            for recurso in mod.RESOURCES:
                fetch_resource(cache_dir, fonte.id, recurso, refresh=refresh, **opcoes)
        except Exception as e:
            raise _falha(fonte, e) from e


def ingest_sources(
    selected: list[Source],
    sources: dict[str, Source],
    cache_dir: Path,
    *,
    offline: bool = False,
    adapters: str = DEFAULT_PACKAGE,
    **opcoes,
) -> list[Observation]:
    """Roda parse sobre o cache, aplica R1 e valida cada fonte (spec 001 e R3)."""
    observacoes: list[Observation] = []
    for fonte in selected:
        try:
            mod = load_adapter(fonte.id, adapters)
            arquivos = SourceFiles(
                (r.filename, fetch_resource(cache_dir, fonte.id, r, offline=offline, **opcoes))
                for r in mod.RESOURCES
            )
            obs = to_observations(mod.parse(arquivos), fonte)
            if not obs:
                raise RecordError("nenhum registro produzido por parse")
            validate(obs, sources)
        except Exception as e:
            raise _falha(fonte, e) from e
        observacoes.extend(obs)
    return observacoes
```

- [ ] **Passo 7: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `269 passed`

- [ ] **Passo 8: commit**

```bash
git add src/namesio/adapters/__init__.py src/namesio/pipeline.py tests/conftest.py tests/test_pipeline.py tests/test_contrato_adaptador.py
git commit -m "Explicita no contrato do adaptador a conversão de valores, a supressão e as mensagens de erro" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: SSA (EUA), registro das fontes e mensagem do 403

**Arquivos:**
- Criar: `src/namesio/adapters/us_ssa_births.py`, `sources.yaml` (substitui `sources: []`)
- Modificar: `src/namesio/cache.py`
- Criar (teste): `tests/fixtures/us-ssa-births/names.zip`, `tests/fixtures/ATRIBUICAO.md`
- Teste: `tests/test_us_ssa_births.py`, `tests/test_fontes_oficiais.py`

**Interfaces:**
- Consome: `FormatError`, `parse_code`, `parse_count`, `servir_fixtures`, `servidor.recusados` (Task 1); `fetch_resource`, `FetchError` (spec 002).
- Produz: fonte `us-ssa-births` em `sources.yaml`; adaptador com `RESOURCES = [Resource("https://www.ssa.gov/oact/babynames/names.zip", "names.zip")]`; `FetchError` de HTTP 403 com `grave-o em <cache>/<id>/<filename> e rode com --offline`; `tests/test_fontes_oficiais.py`, que percorre toda fonte com adaptador de `sources.yaml`.

- [ ] **Passo 1: gerar a amostra** `tests/fixtures/us-ssa-births/names.zip`

Linhas copiadas de `yob1880.txt` e `yob2024.txt`.

```bash
uv run python - tests/fixtures/us-ssa-births/names.zip <<'PY'
import sys, zipfile
from pathlib import Path
destino = Path(sys.argv[1])
destino.parent.mkdir(parents=True, exist_ok=True)
anuais = {
    "yob1880.txt": ["Mary,F,7065", "Anna,F,2604", "John,M,9655", "William,M,9532"],
    "yob2024.txt": ["Olivia,F,14718", "Avery,F,5632", "Liam,F,34", "Liam,M,22164", "Avery,M,1348", "Zyre,M,5"],
}
with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
    for nome, linhas in anuais.items():
        info = zipfile.ZipInfo(nome, date_time=(2025, 5, 1, 0, 0, 0))
        z.writestr(info, "".join(l + "\r\n" for l in linhas).encode("ascii"), zipfile.ZIP_DEFLATED)
PY
```

- [ ] **Passo 2: substituir o conteúdo de** `sources.yaml`

```yaml
# Fontes do dataset (spec 001, R2; spec 002, R2). Licenças conferidas na spec 003, R1.
sources:
  - id: us-ssa-births
    name: Social Security Administration, Popular Baby Names (national data)
    url: https://www.ssa.gov/oact/babynames/limits.html
    license: public-domain
    attribution: "Social Security Administration (EUA), Baby Names from Social Security Card Applications, National Data"
    country: US
    count_type: births
    primary: true
    suppression: 5
    retrieved: 2026-10-12
```

- [ ] **Passo 3: criar** `tests/fixtures/ATRIBUICAO.md`

```markdown
# Amostras das fontes oficiais

Cada diretório guarda um trecho pequeno do arquivo real da fonte, só para os testes (spec 003, R3). As linhas foram copiadas sem alteração. Os ZIPs foram remontados só com as linhas copiadas. As amostras do SSB são a resposta real da API para uma consulta restrita a poucos nomes e anos.

| Fonte | Licença | Origem | Trecho |
|---|---|---|---|
| `us-ssa-births` | public-domain | Social Security Administration (EUA), https://www.ssa.gov/oact/babynames/limits.html | 10 linhas de `yob1880.txt` e `yob2024.txt`, copiadas de um espelho do `names.zip` porque `www.ssa.gov` recusou o download automático |
```

- [ ] **Passo 4: escrever os testes que falham** em `tests/test_us_ssa_births.py`

```python
"""Spec 003, R1.1 e R4: adaptador da SSA (EUA) sobre a amostra real em tests/fixtures/us-ssa-births/."""

import zipfile
from pathlib import Path

import pytest

from namesio.adapters import FormatError, RawRecord, Resource, load_adapter
from namesio.cache import FetchError, fetch_resource

FIXTURES = Path(__file__).parent / "fixtures" / "us-ssa-births"


@pytest.fixture
def ssa():
    return load_adapter("us-ssa-births")


def _zip(tmp_path, arquivos: dict[str, bytes]) -> dict[str, Path]:
    caminho = tmp_path / "names.zip"
    with zipfile.ZipFile(caminho, "w") as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)
    return {"names.zip": caminho}


def test_parse_da_amostra_real(ssa):
    registros = list(ssa.parse({"names.zip": FIXTURES / "names.zip"}))
    assert registros == [
        RawRecord("Mary", "given", "US", "F", 1880, 7065),
        RawRecord("Anna", "given", "US", "F", 1880, 2604),
        RawRecord("John", "given", "US", "M", 1880, 9655),
        RawRecord("William", "given", "US", "M", 1880, 9532),
        RawRecord("Olivia", "given", "US", "F", 2024, 14718),
        RawRecord("Avery", "given", "US", "F", 2024, 5632),
        RawRecord("Liam", "given", "US", "F", 2024, 34),
        RawRecord("Liam", "given", "US", "M", 2024, 22164),
        RawRecord("Avery", "given", "US", "M", 2024, 1348),
        RawRecord("Zyre", "given", "US", "M", 2024, 5),
    ]


def test_ignora_outros_membros_e_aceita_fim_de_linha_lf(ssa, tmp_path):
    arquivos = _zip(tmp_path, {"NationalReadMe.pdf": b"%PDF", "yob2000.txt": b"Ana,F,9\n"})
    assert list(ssa.parse(arquivos)) == [RawRecord("Ana", "given", "US", "F", 2000, 9)]


def test_anos_em_ordem_numerica(ssa, tmp_path):
    arquivos = _zip(tmp_path, {"yob2001.txt": b"B,M,5\r\n", "yob1999.txt": b"A,F,5\r\n"})
    assert [r.year for r in ssa.parse(arquivos)] == [1999, 2001]


@pytest.mark.parametrize("linha, trecho", [
    (b"Ana,X,9\r\n", "sexo 'X' desconhecido"),
    (b"Ana,F,<5\r\n", "contagem '<5'"),
    (b"Ana,F\r\n", "yob2000.txt, linha 1: esperava nome,sexo,contagem"),
])
def test_formato_inesperado_falha(ssa, tmp_path, linha, trecho):
    with pytest.raises(FormatError, match=trecho):
        list(ssa.parse(_zip(tmp_path, {"yob2000.txt": linha})))


def test_zip_sem_arquivos_anuais_falha(ssa, tmp_path):
    with pytest.raises(FormatError, match="sem arquivos yobAAAA.txt"):
        list(ssa.parse(_zip(tmp_path, {"leia.txt": b"x"})))


def test_403_explica_como_colocar_o_arquivo_no_cache(servidor, tmp_path):
    servidor.recusados.add("/oact/babynames/names.zip")
    recurso = Resource(servidor.url("/oact/babynames/names.zip"), "names.zip")
    with pytest.raises(FetchError) as e:
        fetch_resource(tmp_path, "us-ssa-births", recurso, espera=0)
    mensagem = str(e.value)
    assert "HTTP Error 403" in mensagem
    assert f"grave-o em {tmp_path / 'us-ssa-births' / 'names.zip'} e rode com --offline" in mensagem
    assert len(servidor.requisicoes) == 3
```

- [ ] **Passo 5: escrever o teste que percorre as fontes** em `tests/test_fontes_oficiais.py`

```python
"""Spec 003, R1 e R3: cada fonte de sources.yaml tem adaptador, amostra real e atribuição,
e passa por fetch (servidor local) e ingest sem rede."""

from pathlib import Path

import pytest

from namesio.adapters import load_adapter
from namesio.pipeline import fetch_sources, ingest_sources
from namesio.sources import load_sources

RAIZ = Path(__file__).resolve().parent.parent
FONTES = load_sources(RAIZ / "sources.yaml")
IDS = sorted(i for i, f in FONTES.items() if f.adapter)
ATRIBUICAO = (RAIZ / "tests" / "fixtures" / "ATRIBUICAO.md").read_text(encoding="utf-8")


def test_ha_fontes_com_adaptador():
    assert IDS


@pytest.mark.parametrize("source_id", IDS)
def test_amostra_e_atribuicao(source_id):
    mod = load_adapter(source_id)
    pasta = RAIZ / "tests" / "fixtures" / source_id
    arquivos = [p for p in pasta.iterdir() if not p.name.startswith(".")]
    assert sorted(p.name for p in arquivos) == sorted(r.filename for r in mod.RESOURCES)
    assert sum(p.stat().st_size for p in arquivos) < 20_000
    linha = next(l for l in ATRIBUICAO.splitlines() if l.startswith(f"| `{source_id}` |"))
    assert f"| {FONTES[source_id].license} |" in linha


@pytest.mark.parametrize("source_id", IDS)
def test_fetch_e_ingest_sobre_a_amostra(source_id, servir_fixtures, tmp_path):
    fonte = FONTES[source_id]
    servidor = servir_fixtures(load_adapter(source_id))
    fetch_sources([fonte], tmp_path)
    obs = ingest_sources([fonte], FONTES, tmp_path, offline=True)
    assert len(servidor.requisicoes) == len(load_adapter(source_id).RESOURCES)
    assert obs
    assert {(o.source_id, o.country, o.count_type) for o in obs} == {(source_id, fonte.country, fonte.count_type)}
```

- [ ] **Passo 6: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_us_ssa_births.py tests/test_fontes_oficiais.py`
Esperado: `3 failed, 1 passed, 7 errors` (o adaptador ainda não existe; o 403 ainda não traz o caminho do cache)

- [ ] **Passo 7: criar** `src/namesio/adapters/us_ssa_births.py`

```python
"""SSA, nomes de bebês dos EUA (spec 003, R1.1).

names.zip traz um arquivo yobAAAA.txt por ano de nascimento, com linhas nome,sexo,contagem.
A SSA omite nomes com menos de 5 ocorrências; não há marcador de supressão no arquivo.
"""

import csv
import io
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import FormatError, RawRecord, Resource, parse_code, parse_count

SOURCE_ID = "us-ssa-births"
RESOURCES = [Resource("https://www.ssa.gov/oact/babynames/names.zip", "names.zip")]

_ANO = re.compile(r"yob(\d{4})\.txt")
_SEXO = {"F": "F", "M": "M"}


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    with zipfile.ZipFile(files["names.zip"]) as z:
        anuais = sorted((int(m.group(1)), nome) for nome in z.namelist() if (m := _ANO.fullmatch(nome)))
        if not anuais:
            raise FormatError("names.zip sem arquivos yobAAAA.txt")
        for ano, nome in anuais:
            with z.open(nome) as bruto:
                texto = io.TextIOWrapper(bruto, encoding="ascii", newline="")
                for linha, campos in enumerate(csv.reader(texto), start=1):
                    if len(campos) != 3:
                        raise FormatError(f"{nome}, linha {linha}: esperava nome,sexo,contagem, veio {campos!r}")
                    yield RawRecord(
                        name=campos[0], kind="given", country="US",
                        gender=parse_code(campos[1], _SEXO, "sexo"), year=ano, count=parse_count(campos[2]),
                    )
```

- [ ] **Passo 8: substituir o conteúdo de** `src/namesio/cache.py`

**Mudanças:** importa `urllib.error`; a mensagem final de `fetch_resource` explica o 403.

```python
"""Cache de downloads das fontes (spec 002, R4).

Cada recurso fica em cache/<source_id>/<filename>, com <filename>.meta.json ao lado.
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from http.client import HTTPException
from importlib.metadata import version
from pathlib import Path

from namesio.adapters import Resource

REPOSITORIO = "https://github.com/webminas/names.io"
USER_AGENT = f"namesio/{version('namesio')} (+{REPOSITORIO})"
BLOCO = 1 << 16
ESPERA = 2.0  # segundos antes da segunda tentativa; dobra a cada nova tentativa


class FetchError(Exception):
    """Falha ao obter um recurso, da rede ou do cache."""


def cached_path(cache_dir: Path, source_id: str, filename: str) -> Path:
    return Path(cache_dir) / source_id / filename


def _gravar_atomico(destino: Path, conteudo: bytes) -> None:
    temporario = destino.with_name(destino.name + ".part")
    temporario.write_bytes(conteudo)
    os.replace(temporario, destino)


def _baixar(url: str, destino: Path, timeout: float) -> dict:
    """Baixa url para destino via arquivo temporário; devolve os metadados."""
    temporario = destino.with_name(destino.name + ".part")
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    h = hashlib.sha256()
    tamanho = 0
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta, open(temporario, "wb") as fh:
            anunciado = resposta.headers.get("Content-Length")
            while bloco := resposta.read(BLOCO):
                fh.write(bloco)
                h.update(bloco)
                tamanho += len(bloco)
        if anunciado is not None and tamanho != int(anunciado):
            raise FetchError(f"download incompleto de {url}: {tamanho} de {anunciado} bytes")
        meta = {
            "url": url,
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sha256": h.hexdigest(),
            "size": tamanho,
        }
        _gravar_atomico(
            destino.with_name(destino.name + ".meta.json"),
            (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        os.replace(temporario, destino)
        return meta
    finally:
        temporario.unlink(missing_ok=True)


def fetch_resource(
    cache_dir: Path,
    source_id: str,
    resource: Resource,
    *,
    refresh: bool = False,
    offline: bool = False,
    timeout: float = 60.0,
    tentativas: int = 3,
    espera: float | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> Path:
    """Caminho do recurso no cache, baixando-o se preciso (R4)."""
    espera = ESPERA if espera is None else espera
    if offline and refresh:
        raise ValueError("--offline e --refresh são incompatíveis")
    destino = cached_path(cache_dir, source_id, resource.filename)
    if destino.is_file() and not refresh:
        return destino
    if offline:
        raise FetchError(f"{destino} ausente do cache e --offline impede o download")
    destino.parent.mkdir(parents=True, exist_ok=True)
    ultimo: Exception | None = None
    for i in range(tentativas):
        try:
            _baixar(resource.url, destino, timeout)
            return destino
        except (OSError, HTTPException, FetchError) as e:
            ultimo = e
            if i + 1 < tentativas:
                dormir(espera * 2**i)
    mensagem = f"falha ao baixar {resource.url} após {tentativas} tentativa(s): {ultimo}"
    if isinstance(ultimo, urllib.error.HTTPError) and ultimo.code == 403:
        mensagem += (
            f"; o servidor recusou o download automático: baixe o arquivo pelo navegador, "
            f"grave-o em {destino} e rode com --offline"
        )
    raise FetchError(mensagem)
```

- [ ] **Passo 9: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `280 passed`

- [ ] **Passo 10: commit**

```bash
git add sources.yaml src/namesio/adapters/us_ssa_births.py src/namesio/cache.py tests/fixtures/us-ssa-births/names.zip tests/fixtures/ATRIBUICAO.md tests/test_us_ssa_births.py tests/test_fontes_oficiais.py
git commit -m "Adiciona a fonte da SSA e explica o download recusado com 403" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: INSEE (França)

**Arquivos:**
- Criar: `src/namesio/adapters/fr_insee_births.py`
- Modificar: `sources.yaml`, `tests/fixtures/ATRIBUICAO.md`
- Criar (teste): `tests/fixtures/fr-insee-births/prenoms-2025-nat_csv.zip`
- Teste: `tests/test_fr_insee_births.py`

**Interfaces:**
- Consome: `FormatError`, `parse_code`, `parse_count` (Task 1); `to_observations` (spec 002); `tests/test_fontes_oficiais.py` (Task 2).
- Produz: fonte `fr-insee-births` (`uniform_case: true`, `suppression: 3`); adaptador com `RESOURCES = [Resource(".../8595130/prenoms-2025-nat_csv.zip", "prenoms-2025-nat_csv.zip")]`.

- [ ] **Passo 1: gerar a amostra** `tests/fixtures/fr-insee-births/prenoms-2025-nat_csv.zip`

Linhas copiadas de `prenoms-2025-nat.csv`, com o fim de linha CRLF do original.

```bash
uv run python - tests/fixtures/fr-insee-births/prenoms-2025-nat_csv.zip <<'PY'
import sys, zipfile
from pathlib import Path
destino = Path(sys.argv[1])
destino.parent.mkdir(parents=True, exist_ok=True)
linhas = [
    "sexe;prenom;periode;valeur;rang",
    "1;GABRIEL;2025;4625;1",
    "1;LÉO;2025;3420;3",
    "1;CAMILLE;2025;915;61",
    "1;JEAN-BAPTISTE;2025;35;1054",
    "1;RARES;2025;15;2053",
    "1;N'GOLO;2025;5;6394",
    "2;LOUISE;2025;3070;1",
    "2;CAMILLE;2025;640;75",
    "1;JEAN;1900;14090;1",
    "2;MARIE;1900;48695;1",
]
with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
    info = zipfile.ZipInfo("prenoms-2025-nat.csv", date_time=(2026, 6, 18, 18, 3, 0))
    z.writestr(info, "".join(l + "\r\n" for l in linhas).encode("utf-8"), zipfile.ZIP_DEFLATED)
PY
```

- [ ] **Passo 2: acrescentar ao fim de** `sources.yaml`

```yaml
  - id: fr-insee-births
    name: INSEE, Fichier des prénoms (France, nível nacional)
    url: https://www.insee.fr/fr/statistiques/8595130
    license: etalab-2.0
    attribution: "Source : Insee, Fichier des prénoms, édition 2025"
    country: FR
    count_type: births
    primary: true
    suppression: 3
    retrieved: 2026-10-12
    uniform_case: true
```

- [ ] **Passo 3: acrescentar ao fim de** `tests/fixtures/ATRIBUICAO.md`

```markdown
| `fr-insee-births` | etalab-2.0 | Source : Insee, Fichier des prénoms, édition 2025, https://www.insee.fr/fr/statistiques/8595130 | cabeçalho e 10 linhas de `prenoms-2025-nat.csv` |
```

- [ ] **Passo 4: escrever os testes que falham** em `tests/test_fr_insee_births.py`

```python
"""Spec 003, R1.2: adaptador do INSEE (França) sobre a amostra real em tests/fixtures/fr-insee-births/."""

import zipfile
from pathlib import Path

import pytest

from namesio.adapters import FormatError, RawRecord, load_adapter
from namesio.pipeline import to_observations
from namesio.sources import load_sources

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
```

- [ ] **Passo 5: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_fr_insee_births.py tests/test_fontes_oficiais.py`
Esperado: `2 failed, 3 passed, 10 errors`

- [ ] **Passo 6: criar** `src/namesio/adapters/fr_insee_births.py`

```python
"""INSEE, Fichier des prénoms, edição 2025, nível nacional (spec 003, R1.2).

O ZIP traz um CSV separado por ponto e vírgula com sexe;prenom;periode;valeur;rang.
Sexo 1 é masculino e 2 é feminino. Os valores vêm arredondados ao múltiplo de 5 mais próximo.
"""

import csv
import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import FormatError, RawRecord, Resource, parse_code, parse_count

SOURCE_ID = "fr-insee-births"
RESOURCES = [
    Resource("https://www.insee.fr/fr/statistiques/fichier/8595130/prenoms-2025-nat_csv.zip",
             "prenoms-2025-nat_csv.zip"),
]

_SEXO = {"1": "M", "2": "F"}
_COLUNAS = {"sexe", "prenom", "periode", "valeur"}


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    with zipfile.ZipFile(files["prenoms-2025-nat_csv.zip"]) as z:
        membros = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(membros) != 1:
            raise FormatError(f"esperava um CSV no ZIP, encontrei {membros}")
        with z.open(membros[0]) as bruto:
            leitor = csv.DictReader(io.TextIOWrapper(bruto, encoding="utf-8-sig", newline=""), delimiter=";")
            faltando = _COLUNAS - set(leitor.fieldnames or ())
            if faltando:
                raise FormatError(f"{membros[0]}: colunas ausentes {sorted(faltando)}; cabeçalho {leitor.fieldnames}")
            for linha in leitor:
                prenom, periode = linha["prenom"], linha["periode"]
                # Edições anteriores agregavam nomes raros em _PRENOMS_RARES e anos ignorados em XXXX.
                if prenom.startswith("_") or periode == "XXXX":
                    continue
                yield RawRecord(
                    name=prenom, kind="given", country="FR",
                    gender=parse_code(linha["sexe"], _SEXO, "sexe"),
                    year=parse_count(periode, field="periode"), count=parse_count(linha["valeur"]),
                )
```

- [ ] **Passo 7: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `292 passed`

- [ ] **Passo 8: commit**

```bash
git add sources.yaml src/namesio/adapters/fr_insee_births.py tests/fixtures/fr-insee-births/prenoms-2025-nat_csv.zip tests/fixtures/ATRIBUICAO.md tests/test_fr_insee_births.py
git commit -m "Adiciona a fonte do INSEE" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: CSO (Irlanda)

**Arquivos:**
- Criar: `src/namesio/adapters/ie_cso_births.py`
- Modificar: `sources.yaml`, `tests/fixtures/ATRIBUICAO.md`
- Criar (teste): `tests/fixtures/ie-cso-births/VSA50.csv`, `tests/fixtures/ie-cso-births/VSA60.csv`
- Teste: `tests/test_ie_cso_births.py`

**Interfaces:**
- Consome: `FormatError`, `parse_count` (Task 1); `tests/test_fontes_oficiais.py` (Task 2).
- Produz: fonte `ie-cso-births` (`suppression: 3`); adaptador com dois recursos do PxStat, `VSA50.csv` (meninos) e `VSA60.csv` (meninas).

- [ ] **Passo 1: gerar as amostras** em `tests/fixtures/ie-cso-births/`

Linhas copiadas dos CSV do PxStat, com o BOM e o fim de linha CRLF do original.

```bash
uv run python - tests/fixtures/ie-cso-births <<'PY'
import sys
from pathlib import Path
pasta = Path(sys.argv[1])
pasta.mkdir(parents=True, exist_ok=True)
b = "Boys Names in Ireland with 3 or More Occurrences"
g = "Girls Names in Ireland with 3 or More Occurrences"
tabelas = {
    "VSA50.csv": [
        '"STATISTIC","Statistic Label","TLIST(A1)","Year","C02512V04117","Boys Names","UNIT","VALUE"',
        f'"VSA50C01","{b}","1964","1964","0001","Jack","Number",""',
        f'"VSA50C02","{b} Rank","2025","2025","0001","Jack","Number","2"',
        f'"VSA50C01","{b}","2025","2025","1232","A.J.","Number",""',
        f'"VSA50C01","{b}","2025","2025","0001","Jack","Number","475"',
        f'"VSA50C01","{b}","2025","2025","2481","Seán","Number","185"',
        f'"VSA50C01","{b}","2025","2025","2483","Seán Óg","Number","17"',
    ],
    "VSA60.csv": [
        '"STATISTIC","Statistic Label","TLIST(A1)","Year","C02514V04120","Girls Names","UNIT","VALUE"',
        f'"VSA60C02","{g} Rank","1964","1964","0057","Mary","Number","1"',
        f'"VSA60C01","{g}","1964","1964","0026","Saoirse","Number",""',
        f'"VSA60C01","{g}","1964","1964","0057","Mary","Number","3471"',
        f'"VSA60C01","{g}","2025","2025","0008","Emily","Number","246"',
        f'"VSA60C01","{g}","2025","2025","0057","Mary","Number","41"',
        f'"VSA60C01","{g}","2025","2025","0026","Saoirse","Number","176"',
    ],
}
for nome, linhas in tabelas.items():
    # Como o PxStat: UTF-8 com BOM e fim de linha CRLF.
    (pasta / nome).write_bytes(("﻿" + "".join(l + "\r\n" for l in linhas)).encode("utf-8"))
PY
```

- [ ] **Passo 2: acrescentar ao fim de** `sources.yaml`

```yaml
  - id: ie-cso-births
    name: Central Statistics Office, Irish Babies' Names (VSA50 e VSA60)
    url: https://data.gov.ie/dataset/vsa50-boys-names-in-ireland-with-3-or-more-occurrences
    license: CC-BY-4.0
    attribution: "Central Statistics Office (Irlanda), tabelas VSA50 e VSA60, CC BY 4.0"
    country: IE
    count_type: births
    primary: true
    suppression: 3
    retrieved: 2026-10-12
```

- [ ] **Passo 3: acrescentar ao fim de** `tests/fixtures/ATRIBUICAO.md`

```markdown
| `ie-cso-births` | CC-BY-4.0 | Central Statistics Office (Irlanda), tabelas VSA50 e VSA60, https://data.gov.ie/dataset/vsa50-boys-names-in-ireland-with-3-or-more-occurrences | cabeçalho e 6 linhas de cada CSV |
```

- [ ] **Passo 4: escrever os testes que falham** em `tests/test_ie_cso_births.py`

```python
"""Spec 003, R1.3: adaptador do CSO (Irlanda) sobre a amostra real em tests/fixtures/ie-cso-births/."""

from pathlib import Path

import pytest

from namesio.adapters import FormatError, RawRecord, load_adapter

FIXTURES = Path(__file__).parent / "fixtures" / "ie-cso-births"
CABECALHO = '﻿"STATISTIC","Statistic Label","TLIST(A1)","Year","C02512V04117","Boys Names","UNIT","VALUE"\r\n'


@pytest.fixture
def cso():
    return load_adapter("ie-cso-births")


def _arquivos(tmp_path, meninos: str) -> dict[str, Path]:
    (tmp_path / "VSA50.csv").write_text(meninos, encoding="utf-8", newline="")
    return {"VSA50.csv": tmp_path / "VSA50.csv", "VSA60.csv": FIXTURES / "VSA60.csv"}


def test_parse_da_amostra_real(cso):
    arquivos = {nome: FIXTURES / nome for nome in ("VSA50.csv", "VSA60.csv")}
    assert list(cso.parse(arquivos)) == [
        RawRecord("Jack", "given", "IE", "M", 2025, 475),
        RawRecord("Seán", "given", "IE", "M", 2025, 185),
        RawRecord("Seán Óg", "given", "IE", "M", 2025, 17),
        RawRecord("Mary", "given", "IE", "F", 1964, 3471),
        RawRecord("Emily", "given", "IE", "F", 2025, 246),
        RawRecord("Mary", "given", "IE", "F", 2025, 41),
        RawRecord("Saoirse", "given", "IE", "F", 2025, 176),
    ]


def test_valor_vazio_e_rank_sao_ignorados(cso, tmp_path):
    texto = CABECALHO + '"VSA50C01","x","2020","2020","1","Ola","Number",""\r\n' \
        '"VSA50C02","x","2020","2020","1","Ola","Number","7"\r\n'
    assert [r for r in cso.parse(_arquivos(tmp_path, texto)) if r.gender == "M"] == []


@pytest.mark.parametrize("texto, trecho", [
    ('"STATISTIC","TLIST(A1)","Nomes","VALUE"\r\n', "colunas ausentes \\['Boys Names'\\]"),
    (CABECALHO + '"VSA50C01","x","2020","2020","1","Ola","Number","<3"\r\n', "contagem '<3'"),
])
def test_formato_inesperado_falha(cso, tmp_path, texto, trecho):
    with pytest.raises(FormatError, match=trecho):
        list(cso.parse(_arquivos(tmp_path, texto)))
```

- [ ] **Passo 5: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_ie_cso_births.py tests/test_fontes_oficiais.py`
Esperado: `2 failed, 5 passed, 4 errors`

- [ ] **Passo 6: criar** `src/namesio/adapters/ie_cso_births.py`

```python
"""CSO, nomes de bebês da Irlanda, tabelas VSA50 (meninos) e VSA60 (meninas) do PxStat (spec 003, R1.3).

Cada CSV traz o cubo inteiro: todos os nomes em todos os anos, com a contagem (estatística C01)
e o rank (C02). Contagem vazia é nome com menos de 3 ocorrências naquele ano, ou ausente.
"""

import csv
from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import FormatError, RawRecord, Resource, parse_count

SOURCE_ID = "ie-cso-births"
_API = "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/{}/CSV/1.0/en"
RESOURCES = [Resource(_API.format("VSA50"), "VSA50.csv"), Resource(_API.format("VSA60"), "VSA60.csv")]

# arquivo -> (código da estatística de contagem, coluna do nome, gender)
_TABELAS = {
    "VSA50.csv": ("VSA50C01", "Boys Names", "M"),
    "VSA60.csv": ("VSA60C01", "Girls Names", "F"),
}


def _ler(caminho: Path, estatistica: str, coluna: str, genero: str) -> Iterator[RawRecord]:
    with open(caminho, encoding="utf-8-sig", newline="") as fh:
        leitor = csv.DictReader(fh)
        faltando = {"STATISTIC", "TLIST(A1)", coluna, "VALUE"} - set(leitor.fieldnames or ())
        if faltando:
            raise FormatError(f"{caminho.name}: colunas ausentes {sorted(faltando)}; cabeçalho {leitor.fieldnames}")
        for linha in leitor:
            if linha["STATISTIC"] != estatistica:
                continue
            contagem = parse_count(linha["VALUE"], missing={""})
            if contagem is None:
                continue
            yield RawRecord(
                name=linha[coluna], kind="given", country="IE", gender=genero,
                year=parse_count(linha["TLIST(A1)"], field="TLIST(A1)"), count=contagem,
            )


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    for arquivo, (estatistica, coluna, genero) in _TABELAS.items():
        yield from _ler(files[arquivo], estatistica, coluna, genero)
```

- [ ] **Passo 7: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `298 passed`

- [ ] **Passo 8: commit**

```bash
git add sources.yaml src/namesio/adapters/ie_cso_births.py tests/fixtures/ie-cso-births/VSA50.csv tests/fixtures/ie-cso-births/VSA60.csv tests/fixtures/ATRIBUICAO.md tests/test_ie_cso_births.py
git commit -m "Adiciona a fonte do CSO da Irlanda" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Statistics Norway, duas fontes do mesmo instituto, e país booleano no YAML

**Arquivos:**
- Criar: `src/namesio/adapters/_ssb.py`, `src/namesio/adapters/no_ssb_fornavn.py`, `src/namesio/adapters/no_ssb_etternavn.py`
- Modificar: `src/namesio/sources.py`, `sources.yaml`, `tests/fixtures/ATRIBUICAO.md`
- Criar (teste): `tests/fixtures/no-ssb-fornavn/10467.json`, `tests/fixtures/no-ssb-etternavn/12891.json`
- Teste: `tests/test_no_ssb.py`

**Interfaces:**
- Consome: `FormatError`, `parse_code` (Task 1); `tests/test_fontes_oficiais.py` (Task 2).
- Produz: `namesio.adapters._ssb`: `API` (modelo de URL), `MARCADORES = {".", ".."}`, `cells(caminho, dimensao) -> Iterator[(codigo, rotulo, ano, valor)]`; fontes `no-ssb-fornavn` (`births`, `suppression: 4`) e `no-ssb-etternavn` (`population`, `suppression: 200`); `parse_sources` recusa país booleano pedindo aspas.

- [ ] **Passo 1: criar** `tests/fixtures/no-ssb-fornavn/10467.json`

Resposta real da API para `valueCodes[Fornavn]=1NORA,1Z3SE,1KIM,2KIM,2JAKOB` e `valueCodes[Tid]=1944,1990,2025`.

```json
{"version":"2.0","class":"dataset","label":"10467: Born persons, by girls' or boys' name and year","source":"Statistics Norway","updated":"2026-01-28T07:00:00Z","note":["Figures under 4 persons are not published.","Name list include first name used by at least 200 persons previous year. The figures show people by year of birth (before 2021) or year of naming (from 2021 onwards).",". = Less than 4 persons.","Number of persons earlier than 1945 are not published.",".. = Data not available. Figures have not been entered into our databases or are too unreliable to be published.",". = Category not applicable. Figures do not exist at this time, because the category was not in use when the figures were collected."],"role":{"time":["Tid"],"metric":["ContentsCode"]},"id":["Fornavn","ContentsCode","Tid"],"size":[5,1,3],"dimension":{"Fornavn":{"label":"girls' or boys' name","category":{"index":{"1NORA":0,"1Z3SE":1,"1KIM":2,"2KIM":3,"2JAKOB":4},"label":{"1NORA":"Nora","1Z3SE":"Åse","1KIM":"Kim","2KIM":"Kim","2JAKOB":"Jakob"}},"extension":{"elimination":false,"show":"value"}},"ContentsCode":{"label":"contents","category":{"index":{"Personer":0},"label":{"Personer":"Born persons"},"unit":{"Personer":{"base":"persons","decimals":0}}},"extension":{"elimination":false,"refperiod":{"Personer":""},"show":"value","measuringType":{"Personer":"Flow"},"priceType":{"Personer":"NotApplicable"},"adjustment":{"Personer":"None"},"alternativeText":{"Personer":"Born persons"}}},"Tid":{"label":"year","category":{"index":{"1944":0,"1990":1,"2025":2},"label":{"1944":"1944","1990":"1990","2025":"2025"}},"extension":{"elimination":false,"show":"code"}}},"extension":{"noteMandatory":{"2":true},"px":{"infofile":"None","tableid":"10467","decimals":0,"official-statistics":true,"aggregallowed":true,"copyright":false,"language":"en","contents":"10467: Born persons,","descriptiondefault":false,"heading":["ContentsCode","Tid"],"stub":["Fornavn"],"matrix":"10467","subject-code":"be","subject-area":"Population"},"discontinued":null,"contact":[{"name":"Anders Sønstebø","organization":"Statistics Norway","phone":"46 66 37 74","mail":"son@ssb.no","raw":"Anders Sønstebø, Statistics Norway# +47 46 66 37 74#son@ssb.no"}]},"value":[null,75,357,null,29,64,null,21,null,null,401,null,null,32,297],"status":{"0":"..","3":"..","6":"..","8":".","9":"..","11":".","12":".."}}
```

- [ ] **Passo 2: criar** `tests/fixtures/no-ssb-etternavn/12891.json`

Resposta real da API para `valueCodes[Etternavn]=HANSEN,DA-SILVA,ABDO` e `valueCodes[Tid]=2020,2025`.

```json
{"version":"2.0","class":"dataset","label":"12891: Last names used by 200 persons or more, by last name and year","source":"Statistics Norway","updated":"2026-01-28T07:00:00Z","note":[". = Less than 200 persons.",". = Category not applicable. Figures do not exist at this time, because the category was not in use when the figures were collected."],"role":{"time":["Tid"],"metric":["ContentsCode"]},"id":["Etternavn","ContentsCode","Tid"],"size":[3,1,2],"dimension":{"Etternavn":{"label":"last name","category":{"index":{"HANSEN":0,"DA-SILVA":1,"ABDO":2},"label":{"HANSEN":"Hansen","DA-SILVA":"Da Silva","ABDO":"Abdo"}},"extension":{"elimination":false,"show":"value"}},"ContentsCode":{"label":"contents","category":{"index":{"Personer":0},"label":{"Personer":"Persons"},"unit":{"Personer":{"base":"number","decimals":0}}},"extension":{"elimination":false,"refperiod":{"Personer":"31.12."},"show":"value","measuringType":{"Personer":"Flow"},"priceType":{"Personer":"NotApplicable"},"adjustment":{"Personer":"None"},"alternativeText":{"Personer":"Persons"}}},"Tid":{"label":"year","category":{"index":{"2020":0,"2025":1},"label":{"2020":"2020","2025":"2025"}},"extension":{"elimination":false,"show":"code"}}},"extension":{"noteMandatory":{"0":true},"px":{"infofile":"None","tableid":"12891","decimals":0,"official-statistics":true,"aggregallowed":true,"copyright":false,"language":"en","contents":"12891: Last names used by 200 persons or more,","descriptiondefault":false,"heading":["ContentsCode","Tid"],"stub":["Etternavn"],"matrix":"12891","subject-code":"be","subject-area":"Population"},"discontinued":null,"contact":[{"name":"Anders Sønstebø","organization":"Statistics Norway","phone":"46 66 37 74","mail":"son@ssb.no","raw":"Anders Sønstebø, Statistics Norway# +47 46 66 37 74#son@ssb.no"}]},"value":[50582,47879,null,219,null,232],"status":{"2":".","4":"."}}
```

- [ ] **Passo 3: acrescentar ao fim de** `sources.yaml`

`"NO"` vai entre aspas: sem elas, o YAML lê `false`.

```yaml
  - id: no-ssb-fornavn
    name: Statistics Norway, nascidos por primeiro nome (tabela 10467)
    url: https://www.ssb.no/en/statbank/table/10467
    license: CC-BY-4.0
    attribution: "Statistics Norway (SSB), tabela 10467, CC BY 4.0"
    country: "NO"
    count_type: births
    primary: true
    suppression: 4
    retrieved: 2026-10-12
  - id: no-ssb-etternavn
    name: Statistics Norway, sobrenomes usados por 200 pessoas ou mais (tabela 12891)
    url: https://www.ssb.no/en/statbank/table/12891
    license: CC-BY-4.0
    attribution: "Statistics Norway (SSB), tabela 12891, CC BY 4.0"
    country: "NO"
    count_type: population
    primary: true
    suppression: 200
    retrieved: 2026-10-12
```

- [ ] **Passo 4: acrescentar ao fim de** `tests/fixtures/ATRIBUICAO.md`

```markdown
| `no-ssb-fornavn` | CC-BY-4.0 | Statistics Norway (SSB), tabela 10467, https://www.ssb.no/en/statbank/table/10467 | nomes 1NORA, 1Z3SE, 1KIM, 2KIM e 2JAKOB nos anos 1944, 1990 e 2025 |
| `no-ssb-etternavn` | CC-BY-4.0 | Statistics Norway (SSB), tabela 12891, https://www.ssb.no/en/statbank/table/12891 | sobrenomes HANSEN, DA-SILVA e ABDO nos anos 2020 e 2025 |
```

- [ ] **Passo 5: escrever os testes que falham** em `tests/test_no_ssb.py`

```python
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
```

- [ ] **Passo 6: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_no_ssb.py tests/test_fontes_oficiais.py`
Esperado: `12 failed, 8 passed`

- [ ] **Passo 7: substituir o conteúdo de** `src/namesio/sources.py`

**Mudanças:** `parse_sources` recusa `country` booleano com mensagem que pede aspas, antes da verificação ISO.

```python
"""Registro de fontes (sources.yaml), regras de licença do ADR 0001 e campos da spec 002 (R2)."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from urllib.parse import urlsplit

import pycountry
import yaml

LICENCAS_COMPATIVEIS = frozenset({
    "public-domain", "CC0-1.0", "CC-BY-3.0", "CC-BY-4.0",
    "ODC-By-1.0", "OGL-UK-3.0", "etalab-2.0",
})
ID_FORMATO = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
COUNT_TYPES = ("births", "population", "attested")
CAMPOS = (
    "id", "name", "url", "license", "attribution", "country",
    "count_type", "primary", "suppression", "retrieved",
)
# Campos opcionais da spec 002 (R2) e seus valores padrão.
OPCIONAIS = {"uniform_case": False, "adapter": True}


class SourceError(ValueError):
    """sources.yaml inválido. A mensagem lista todos os problemas encontrados."""


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str
    license: str
    attribution: str
    country: str | None
    count_type: str
    primary: bool
    suppression: int | None
    retrieved: date
    uniform_case: bool = False
    adapter: bool = True


def is_country(code: object) -> bool:
    """Código ISO 3166-1 alfa-2 em maiúsculas."""
    if not isinstance(code, str) or len(code) != 2 or code != code.upper():
        return False
    try:
        return pycountry.countries.get(alpha_2=code) is not None
    except (KeyError, LookupError):
        return False


def _url_http(url: str) -> bool:
    partes = urlsplit(url)
    return partes.scheme.lower() in ("http", "https") and bool(partes.netloc)


def load_sources(path: Path) -> dict[str, Source]:
    try:
        dados = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise SourceError(f"não foi possível ler {path}: {e}") from e
    except yaml.YAMLError as e:
        raise SourceError(f"{path}: YAML inválido: {e}") from e
    if dados is None:
        dados = {}
    if not isinstance(dados, dict):
        raise SourceError(f"{path}: a raiz deve ser um mapeamento com a chave 'sources'")
    entradas = dados.get("sources", [])
    if entradas is None:
        entradas = []
    if not isinstance(entradas, list):
        raise SourceError(f"{path}: 'sources' deve ser uma lista")
    return parse_sources(entradas)


def parse_sources(entradas: list[dict]) -> dict[str, Source]:
    erros: list[str] = []
    fontes: dict[str, Source] = {}
    for i, e in enumerate(entradas):
        if not isinstance(e, dict):
            erros.append(f"#{i}: entrada deve ser um mapeamento")
            continue
        rotulo = str(e.get("id") or f"#{i}")
        antes = len(erros)
        faltando = [c for c in CAMPOS if c not in e]
        if faltando:
            erros.append(f"{rotulo}: campos ausentes {faltando}")
            continue
        extras = sorted(set(e) - set(CAMPOS) - set(OPCIONAIS))
        if extras:
            erros.append(f"{rotulo}: campos desconhecidos {extras}")
        for campo in ("id", "name", "url", "attribution"):
            if not isinstance(e[campo], str) or not e[campo].strip():
                erros.append(f"{rotulo}: '{campo}' vazio")
        if isinstance(e["id"], str) and e["id"].strip() and not ID_FORMATO.fullmatch(e["id"]):
            erros.append(f"{rotulo}: 'id' com formato inválido (use [a-z0-9]+(-[a-z0-9]+)*)")
        if isinstance(e["url"], str) and e["url"].strip() and not _url_http(e["url"]):
            erros.append(f"{rotulo}: 'url' deve usar o esquema http ou https")
        if not isinstance(e["license"], str) or e["license"] not in LICENCAS_COMPATIVEIS:
            erros.append(f"{rotulo}: licença '{e['license']}' incompatível com o ADR 0001")
        if isinstance(e["country"], bool):
            erros.append(f"{rotulo}: país lido como booleano {e['country']}; escreva o código entre aspas, ex.: \"NO\"")
        elif e["country"] is not None and not is_country(e["country"]):
            erros.append(f"{rotulo}: país '{e['country']}' fora da ISO 3166-1 alfa-2")
        if e["count_type"] not in COUNT_TYPES:
            erros.append(f"{rotulo}: count_type '{e['count_type']}' inválido")
        if not isinstance(e["primary"], bool):
            erros.append(f"{rotulo}: 'primary' deve ser true ou false")
        s = e["suppression"]
        if s is not None and (isinstance(s, bool) or not isinstance(s, int) or s < 1):
            erros.append(f"{rotulo}: 'suppression' deve ser inteiro positivo ou vazio")
        if not isinstance(e["retrieved"], date) or isinstance(e["retrieved"], datetime):
            erros.append(f"{rotulo}: 'retrieved' deve ser uma data AAAA-MM-DD, sem hora")
        for campo in OPCIONAIS:
            if campo in e and not isinstance(e[campo], bool):
                erros.append(f"{rotulo}: '{campo}' deve ser true ou false")
        if len(erros) > antes:
            continue
        if e["id"] in fontes:
            erros.append(f"{rotulo}: id duplicado")
            continue
        opcionais = {c: e.get(c, padrao) for c, padrao in OPCIONAIS.items()}
        fontes[e["id"]] = Source(**{c: e[c] for c in CAMPOS}, **opcionais)

    grupos: dict[tuple, list[Source]] = {}
    for f in fontes.values():
        grupos.setdefault((f.country, f.count_type), []).append(f)
    for (pais, tipo), fs in sorted(grupos.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        if len(fs) > 1 and sum(f.primary is True for f in fs) != 1:
            ids = sorted(f.id for f in fs)
            erros.append(f"{pais}/{tipo}: fontes {ids}; exatamente uma deve ter primary: true")

    if erros:
        raise SourceError("\n".join(erros))
    return fontes
```

- [ ] **Passo 8: criar** `src/namesio/adapters/_ssb.py`

```python
"""Leitura das tabelas de nomes do Statistics Norway (SSB) em JSON-stat 2.0 (spec 003, R1.4 e R1.5).

Não é adaptador: o nome começa com _ e não corresponde a nenhum id de sources.yaml.
"""

import json
from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import FormatError

API = (
    "https://data.ssb.no/api/pxwebapi/v2/tables/{tabela}/data?lang=en&outputFormat=json-stat2"
    "&valueCodes%5B{dimensao}%5D=%2A&valueCodes%5BContentsCode%5D=Personer&valueCodes%5BTid%5D=%2A"
)
# "." = menos que o limite de divulgação (4 nascimentos ou 200 pessoas); ".." = dado indisponível.
MARCADORES = {".", ".."}


def _categorias(dados: dict, dimensao: str) -> list[tuple[str, str]]:
    categoria = dados["dimension"][dimensao]["category"]
    indice = categoria["index"]
    codigos = sorted(indice, key=indice.get) if isinstance(indice, dict) else list(indice)
    rotulos = categoria.get("label", {})
    return [(c, rotulos.get(c, c)) for c in codigos]


def cells(caminho: Path, dimensao: str) -> Iterator[tuple[str, str, int, int]]:
    """(código, rótulo, ano, valor) de cada célula publicada; células suprimidas são omitidas."""
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if dados.get("class") != "dataset" or dados.get("id") != [dimensao, "ContentsCode", "Tid"]:
        raise FormatError(f"{Path(caminho).name}: esperava dataset com dimensões [{dimensao}, ContentsCode, Tid], "
                          f"veio {dados.get('id')}")
    nomes, anos = _categorias(dados, dimensao), _categorias(dados, "Tid")
    medidas = _categorias(dados, "ContentsCode")
    if [c for c, _ in medidas] != ["Personer"]:
        raise FormatError(f"{Path(caminho).name}: esperava só a medida Personer, veio {medidas}")
    valores, status = dados["value"], dados.get("status") or {}
    if not isinstance(valores, list) or len(valores) != len(nomes) * len(anos):
        raise FormatError(f"{Path(caminho).name}: 'value' não é uma lista densa de {len(nomes) * len(anos)} células")
    if isinstance(status, list):
        status = {str(k): s for k, s in enumerate(status) if s is not None}
    for i, (codigo, rotulo) in enumerate(nomes):
        for j, (ano, _) in enumerate(anos):
            k = i * len(anos) + j
            valor = valores[k]
            if valor is None:
                if status.get(str(k)) not in MARCADORES:
                    raise FormatError(f"{Path(caminho).name}: célula {k} vazia sem marcador conhecido")
                continue
            if type(valor) is not int:
                raise FormatError(f"{Path(caminho).name}: célula {k} com valor {valor!r}, esperava inteiro")
            yield codigo, rotulo, int(ano), valor
```

- [ ] **Passo 9: criar** `src/namesio/adapters/no_ssb_fornavn.py`

```python
"""SSB, nascidos por primeiro nome, tabela 10467 (spec 003, R1.4).

O código de cada nome começa com 1 (meninas) ou 2 (meninos); o rótulo é o nome publicado.
Até 2020 o ano é o de nascimento; desde 2021, o de registro do nome.
"""

from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import RawRecord, Resource, parse_code
from namesio.adapters._ssb import API, cells

SOURCE_ID = "no-ssb-fornavn"
RESOURCES = [Resource(API.format(tabela="10467", dimensao="Fornavn"), "10467.json")]

_SEXO = {"1": "F", "2": "M"}


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    for codigo, nome, ano, contagem in cells(files["10467.json"], "Fornavn"):
        yield RawRecord(
            name=nome, kind="given", country="NO",
            gender=parse_code(codigo[:1], _SEXO, "prefixo de sexo"), year=ano, count=contagem,
        )
```

- [ ] **Passo 10: criar** `src/namesio/adapters/no_ssb_etternavn.py`

```python
"""SSB, pessoas por sobrenome usado por 200 ou mais, tabela 12891 (spec 003, R1.5).

Mesmo instituto de no-ssb-fornavn, mas outro count_type (population), por isso outra fonte (R2.4).
"""

from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import RawRecord, Resource
from namesio.adapters._ssb import API, cells

SOURCE_ID = "no-ssb-etternavn"
RESOURCES = [Resource(API.format(tabela="12891", dimensao="Etternavn"), "12891.json")]


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    for _, nome, ano, contagem in cells(files["12891.json"], "Etternavn"):
        yield RawRecord(name=nome, kind="family", country="NO", year=ano, count=contagem)
```

- [ ] **Passo 11: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `311 passed`

- [ ] **Passo 12: commit**

```bash
git add sources.yaml src/namesio/sources.py src/namesio/adapters/_ssb.py src/namesio/adapters/no_ssb_fornavn.py src/namesio/adapters/no_ssb_etternavn.py tests/fixtures/no-ssb-fornavn/10467.json tests/fixtures/no-ssb-etternavn/12891.json tests/fixtures/ATRIBUICAO.md tests/test_no_ssb.py
git commit -m "Adiciona as fontes do Statistics Norway e recusa país booleano em sources.yaml" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: CI com as fontes oficiais

**Arquivos:**
- Modificar: `.github/workflows/ci.yml`
- Modificar (teste): `tests/test_ci.py`

**Interfaces:**
- Consome: as cinco fontes de `sources.yaml` e as amostras (Tasks 2 a 5); `namesio run` (spec 002).
- Produz: passo da CI que roda `namesio run --offline` sobre `tests/fixtures/` com o `sources.yaml` da raiz.

- [ ] **Passo 1: acrescentar ao fim de** `tests/test_ci.py`

Valores de `NO.csv` conferidos à mão: `Kim` soma 21 (F) e 401 (M) em 1990, 422 no total, `female_share` 21 ÷ 422 = 0,049763; os sobrenomes usam só a edição 2025 (`population`, spec 001, R3.3).

```python
NO_CSV = """\
kind,name,name_key,ascii,script,count,count_type,rank,female_share,gender_basis,first_year,last_year
family,Hansen,hansen,hansen,Latn,47879,population,1,,0,2025,2025
family,Abdo,abdo,abdo,Latn,232,population,2,,0,2025,2025
family,Da Silva,da silva,da silva,Latn,219,population,3,,0,2025,2025
given,Nora,nora,nora,Latn,432,births,1,1.000000,432,1990,2025
given,Kim,kim,kim,Latn,422,births,2,0.049763,422,1990,1990
given,Jakob,jakob,jakob,Latn,329,births,3,0.000000,329,1990,2025
given,Åse,åse,ase,Latn,93,births,4,1.000000,93,1990,2025
"""


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv fora do PATH")
def test_passo_das_fontes_oficiais_roda_localmente(tmp_path):
    """Spec 003, R5: a CI roda as fontes de sources.yaml sobre um cache montado com as amostras."""
    passo = next(p for p in _workflow()["jobs"]["testes"]["steps"] if "cache-oficiais" in p.get("run", ""))
    ambiente = {**os.environ, **passo.get("env", {}), "RUNNER_TEMP": str(tmp_path)}
    r = subprocess.run(["bash", "-e", "-c", passo["run"]], cwd=RAIZ, env=ambiente,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert "OK: 39 observações, 4 países" in r.stdout
    assert (tmp_path / "dist-oficiais" / "by_country" / "NO.csv").read_text(encoding="utf-8") == NO_CSV
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_ci.py`
Esperado: `1 failed, 4 passed` (`StopIteration`: o passo ainda não existe)

- [ ] **Passo 3: acrescentar ao fim de** `.github/workflows/ci.yml`

```yaml
      - name: namesio run --offline sobre as amostras das fontes oficiais
        run: |
          mkdir -p "$RUNNER_TEMP/cache-oficiais"
          cp -R tests/fixtures/. "$RUNNER_TEMP/cache-oficiais/"
          uv run namesio run --offline --cache "$RUNNER_TEMP/cache-oficiais" \
            --out "$RUNNER_TEMP/dist-oficiais" --release 2026.10
          for pais in FR IE NO US; do test -s "$RUNNER_TEMP/dist-oficiais/by_country/$pais.csv"; done
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `312 passed`

- [ ] **Passo 5: commit**

```bash
git add .github/workflows/ci.yml tests/test_ci.py
git commit -m "Roda as fontes oficiais sobre as amostras na CI" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Fechamento

- [ ] Rodar `uv run pytest -q` e ver `312 passed`.
- [ ] Medir R6 com os arquivos reais (precisa de rede; não roda na CI):
  1. `uv run namesio fetch` baixa INSEE, CSO e SSB. Se a SSA responder 403, baixar `https://www.ssa.gov/oact/babynames/names.zip` pelo navegador e gravá-lo em `cache/us-ssa-births/names.zip`, como diz a mensagem.
  2. `/usr/bin/time -l uv run namesio run --offline --out /tmp/namesio-r6 --release 2026.10` (no Linux, `/usr/bin/time -v`).
  3. Esperado: `OK: ... observações, 4 países` em menos de 10 minutos e pico abaixo de 4 GB (no protótipo, num Apple M4 com 24 GB: 3.077.139 observações, 59 s, pico de 1,5 GB). Copiar a linha `OK:`, o tempo e o pico para a descrição do pull request (critério de aceite 7).
- [ ] Abrir o pull request com `Closes #8` na descrição; conferir a CI verde no pull request (critério de aceite 6).
