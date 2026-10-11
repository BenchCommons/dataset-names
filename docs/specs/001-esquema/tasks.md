# 001. Esquema do dataset: tarefas

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar todos os comandos na raiz do repositório.

---

### Task 1: estrutura do projeto, licença dos dados e legado

**Arquivos:**
- Criar: `pyproject.toml`, `src/namesio/__init__.py`, `DATA_LICENSE`, `sources.yaml`, `tests/test_legacy.py`
- Mover: `first_names.all.txt`, `last_names.all.txt`, `generate/` → `legacy/`
- Modificar: `.gitignore` (remover as linhas `*out*` e `*.json`; acrescentar `.venv/`)

**Interfaces:**
- Produz: pacote importável `namesio`; comando `uv run pytest`; arquivos legados em `legacy/`.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_legacy.py`

```python
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
```

- [ ] **Passo 2: criar `pyproject.toml`**

```toml
[project]
name = "namesio"
version = "0.1.0"
description = "Dataset mundial de primeiros nomes e sobrenomes a partir de fontes oficiais e do Wikidata"
requires-python = ">=3.12"
license = "Apache-2.0"
dependencies = [
    "pyarrow>=17",
    "pycountry>=24.6",
    "pyyaml>=6.0",
]

[project.scripts]
namesio = "namesio.cli:main"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Passo 3: criar o pacote vazio e o registro de fontes vazio**

```bash
mkdir -p src/namesio
: > src/namesio/__init__.py
printf 'sources: []\n' > sources.yaml
```

- [ ] **Passo 4: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_legacy.py`
Esperado: `2 failed` (`FileNotFoundError` em `legacy/first_names.all.txt` e `AssertionError` porque as listas ainda estão na raiz)

- [ ] **Passo 5: mover o legado, corrigir o `.gitignore` e baixar a licença dos dados**

```bash
mkdir -p legacy
git mv first_names.all.txt last_names.all.txt generate legacy/
sed -i.bak -e '/^\*out\*$/d' -e '/^\*\.json$/d' .gitignore && rm .gitignore.bak
printf '.venv/\n' >> .gitignore
curl -sSfL https://creativecommons.org/licenses/by/4.0/legalcode.txt -o DATA_LICENSE
head -3 DATA_LICENSE
```

Esperado no `head`: texto começando com `Attribution 4.0 International`.

- [ ] **Passo 6: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `2 passed`

- [ ] **Passo 7: commit**

```bash
git add pyproject.toml uv.lock src/namesio/__init__.py sources.yaml DATA_LICENSE .gitignore legacy tests/test_legacy.py
git commit -m "Cria estrutura do pacote namesio e move listas para legacy/" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: normalização de nomes

**Arquivos:**
- Criar: `src/namesio/normalize.py`
- Teste: `tests/test_normalize.py`

**Interfaces:**
- Produz: `normalize_name(raw: str) -> str`, `name_key(name: str) -> str`, `detect_script(name: str) -> str`, `ascii_form(name: str, script: str) -> str`.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_normalize.py`

```python
from namesio.normalize import ascii_form, detect_script, name_key, normalize_name


def test_caixa_uniforme_vira_capitalizada_por_palavra():
    assert normalize_name("  MARIA   DA  SILVA ") == "Maria Da Silva"
    assert normalize_name("jean-luc") == "Jean-Luc"
    assert normalize_name("o'neil") == "O'Neil"


def test_caixa_mista_e_preservada():
    assert normalize_name("McDonald") == "McDonald"
    assert normalize_name("DeShawn") == "DeShawn"


def test_escrita_sem_caixa_fica_intacta():
    assert normalize_name("李") == "李"


def test_entrada_decomposta_vira_nfc():
    decomposto = "Jose\u0301"
    assert normalize_name(decomposto) == "José"
    assert len(normalize_name(decomposto)) == 4


def test_maiusculas_decompostas_tem_a_mesma_chave_que_a_forma_composta():
    assert name_key(normalize_name("JOSE\u0301")) == name_key("José") == "josé"


def test_i_turco_maiusculo():
    assert normalize_name("İREM") == "İrem"
    assert name_key("İrem") == name_key(normalize_name("İREM"))


def test_nome_so_com_espacos_vira_vazio():
    assert normalize_name("   ") == ""


def test_chave_preserva_acento():
    assert name_key("Álvaro") == "álvaro"


def test_deteccao_de_escrita():
    assert detect_script("Álvaro") == "Latn"
    assert detect_script("Мария") == "Cyrl"
    assert detect_script("李") == "Hani"
    assert detect_script("민준") == "Hang"
    assert detect_script("محمد") == "Arab"
    assert detect_script("-'") == "Zyyy"


def test_forma_ascii_latina():
    assert ascii_form("Álvaro", "Latn") == "alvaro"
    assert ascii_form("Łukasz", "Latn") == "lukasz"
    assert ascii_form("Strauß", "Latn") == "strauss"
    assert ascii_form("Søren", "Latn") == "soren"
    assert ascii_form("Maria Da Silva", "Latn") == "maria da silva"


def test_forma_ascii_vazia_fora_da_escrita_latina():
    assert ascii_form("Мария", "Cyrl") == ""
    assert ascii_form("李", "Hani") == ""
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_normalize.py`
Esperado: FALHA com `ModuleNotFoundError: No module named 'namesio.normalize'`

- [ ] **Passo 3: implementar** `src/namesio/normalize.py`

```python
"""Normalização de nomes: forma de exibição, chave, sistema de escrita e forma ASCII."""

import re
import unicodedata

# Primeira palavra do nome Unicode do caractere -> código ISO 15924.
_ESCRITAS = {
    "LATIN": "Latn", "CYRILLIC": "Cyrl", "GREEK": "Grek", "ARABIC": "Arab",
    "HEBREW": "Hebr", "CJK": "Hani", "HANGUL": "Hang", "HIRAGANA": "Hira",
    "KATAKANA": "Kana", "DEVANAGARI": "Deva", "BENGALI": "Beng", "TAMIL": "Taml",
    "TELUGU": "Telu", "KANNADA": "Knda", "MALAYALAM": "Mlym", "GUJARATI": "Gujr",
    "GURMUKHI": "Guru", "SINHALA": "Sinh", "THAI": "Thai", "LAO": "Laoo",
    "KHMER": "Khmr", "MYANMAR": "Mymr", "TIBETAN": "Tibt", "GEORGIAN": "Geor",
    "ARMENIAN": "Armn", "ETHIOPIC": "Ethi", "MONGOLIAN": "Mong",
}

# Separadores que iniciam uma nova palavra na capitalização.
_SEPARADORES = re.compile(r"([ \-'’])")

# Letras latinas que não se decompõem em base + diacrítico.
_LATINAS_ESPECIAIS = str.maketrans({
    "ß": "ss", "ø": "o", "æ": "ae", "œ": "oe", "đ": "d", "ð": "d",
    "ł": "l", "þ": "th", "ı": "i", "ħ": "h",
})


def normalize_name(raw: str) -> str:
    """Forma de exibição: NFC, espaços colapsados, capitalização se a caixa for uniforme."""
    nome = " ".join(unicodedata.normalize("NFC", raw).split())
    tem_caixa = any(c.isupper() or c.islower() for c in nome)
    if tem_caixa and nome in (nome.upper(), nome.lower()):
        partes = _SEPARADORES.split(nome.lower())
        nome = "".join(p[:1].upper() + p[1:] for p in partes)
    return unicodedata.normalize("NFC", nome)


def name_key(name: str) -> str:
    """Identidade do nome: casefold em NFC, com acentos preservados."""
    return unicodedata.normalize("NFC", name.casefold())


def detect_script(name: str) -> str:
    """Código ISO 15924 predominante entre as letras; Zyyy sem letras, Zzzz se desconhecido."""
    contagem: dict[str, int] = {}
    for c in name:
        if not c.isalpha():
            continue
        primeira = unicodedata.name(c, "").split(" ")[0]
        codigo = _ESCRITAS.get(primeira, "Zzzz")
        contagem[codigo] = contagem.get(codigo, 0) + 1
    if not contagem:
        return "Zyyy"
    return max(sorted(contagem), key=lambda codigo: contagem[codigo])


def ascii_form(name: str, script: str) -> str:
    """Forma ASCII em minúsculas para escrita latina; vazia para as demais (spec 005 define o resto)."""
    if script != "Latn":
        return ""
    base = name.casefold().translate(_LATINAS_ESPECIAIS)
    base = unicodedata.normalize("NFD", base)
    return "".join(c for c in base if not unicodedata.combining(c) and c.isascii())
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: todos os testes passam

- [ ] **Passo 5: commit**

```bash
git add tests/test_normalize.py src/namesio/normalize.py
git commit -m "Adiciona normalização de nomes, escrita e forma ASCII" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: registro de fontes

**Arquivos:**
- Criar: `src/namesio/sources.py`
- Teste: `tests/test_sources.py`

**Interfaces:**
- Produz: `Source` (dataclass imutável com `id, name, url, license, attribution, country, count_type, primary, suppression, retrieved`), `load_sources(path: Path) -> dict[str, Source]`, `parse_sources(entradas: list[dict]) -> dict[str, Source]`, `is_country(code) -> bool`, `SourceError`, `COUNT_TYPES`, `LICENCAS_COMPATIVEIS`.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_sources.py`

```python
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
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_sources.py`
Esperado: FALHA com `ModuleNotFoundError: No module named 'namesio.sources'`

- [ ] **Passo 3: implementar** `src/namesio/sources.py`

```python
"""Registro de fontes (sources.yaml) e regras de licença do ADR 0001."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pycountry
import yaml

LICENCAS_COMPATIVEIS = frozenset({
    "public-domain", "CC0-1.0", "CC-BY-3.0", "CC-BY-4.0",
    "ODC-By-1.0", "OGL-UK-3.0", "etalab-2.0",
})
COUNT_TYPES = ("births", "population", "attested")
CAMPOS = (
    "id", "name", "url", "license", "attribution", "country",
    "count_type", "primary", "suppression", "retrieved",
)


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


def is_country(code: object) -> bool:
    """Código ISO 3166-1 alfa-2 em maiúsculas."""
    if not isinstance(code, str) or len(code) != 2 or code != code.upper():
        return False
    try:
        return pycountry.countries.get(alpha_2=code) is not None
    except (KeyError, LookupError):
        return False


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
        extras = sorted(set(e) - set(CAMPOS))
        if extras:
            erros.append(f"{rotulo}: campos desconhecidos {extras}")
        for campo in ("id", "name", "url", "attribution"):
            if not isinstance(e[campo], str) or not e[campo].strip():
                erros.append(f"{rotulo}: '{campo}' vazio")
        if not isinstance(e["license"], str) or e["license"] not in LICENCAS_COMPATIVEIS:
            erros.append(f"{rotulo}: licença '{e['license']}' incompatível com o ADR 0001")
        if e["country"] is not None and not is_country(e["country"]):
            erros.append(f"{rotulo}: país '{e['country']}' fora da ISO 3166-1 alfa-2")
        if e["count_type"] not in COUNT_TYPES:
            erros.append(f"{rotulo}: count_type '{e['count_type']}' inválido")
        if not isinstance(e["primary"], bool):
            erros.append(f"{rotulo}: 'primary' deve ser true ou false")
        s = e["suppression"]
        if s is not None and (isinstance(s, bool) or not isinstance(s, int) or s < 1):
            erros.append(f"{rotulo}: 'suppression' deve ser inteiro positivo ou vazio")
        if not isinstance(e["retrieved"], date):
            erros.append(f"{rotulo}: 'retrieved' deve ser uma data AAAA-MM-DD")
        if len(erros) > antes:
            continue
        if e["id"] in fontes:
            erros.append(f"{rotulo}: id duplicado")
            continue
        fontes[e["id"]] = Source(**{c: e[c] for c in CAMPOS})

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

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: todos os testes passam

- [ ] **Passo 5: commit**

```bash
git add tests/test_sources.py src/namesio/sources.py
git commit -m "Adiciona registro de fontes com regras de licença do ADR 0001" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: esquema de observações e validação

**Arquivos:**
- Criar: `src/namesio/schema.py`, `tests/conftest.py` (fixture do critério 3, usada também nas Tasks 5 a 7)
- Teste: `tests/test_schema.py`

**Interfaces:**
- Consome: `normalize_name`, `name_key`, `detect_script`, `ascii_form` (Task 2); `Source`, `COUNT_TYPES`, `is_country` (Task 3).
- Produz: `Observation` (dataclass imutável com os 11 campos de R1 e `key() -> tuple`), `make_observation(raw_name, *, kind, source_id, count_type, country=None, gender=None, year=None, count=None) -> Observation`, `validate(observations, sources) -> None`, `ValidationError` (atributo `erros: list[str]`), `SCHEMA_VERSION`, `KINDS`, `GENDERS`. Fixtures `fontes` e `observacoes` e a constante `FONTES` em `tests/conftest.py`.

- [ ] **Passo 1: criar a fixture compartilhada** em `tests/conftest.py`

```python
"""Fixture do critério de aceite 3: duas fontes births no mesmo país (uma primary),
uma population, uma attested; escritas latina, cirílica e chinesa; nome com espaço."""

from datetime import date

import pytest

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
```

- [ ] **Passo 1b: escrever o teste que falha** em `tests/test_schema.py`

```python
from dataclasses import replace

import pytest

from namesio.schema import ValidationError, make_observation, validate


def test_make_observation_deriva_campos():
    o = make_observation("ÁLVARO", kind="given", source_id="us-ssa", count_type="births",
                         country="US", gender="M", year=2021, count=12)
    assert (o.name, o.name_key, o.ascii, o.script) == ("Álvaro", "álvaro", "alvaro", "Latn")


def test_fixture_valida(observacoes, fontes):
    validate(observacoes, fontes)


@pytest.mark.parametrize("campos, trecho", [
    ({"name": ""}, "'name' vazio"),
    ({"kind": "middle"}, "kind"),
    ({"country": "XX"}, "ISO 3166-1"),
    ({"gender": "X"}, "gender"),
    ({"count": -1}, "negativo"),
    ({"count": None}, "R1.1"),
    ({"count_type": "attested"}, "R1.1"),
    ({"count_type": "deaths"}, "count_type"),
    ({"source_id": "inexistente"}, "sources.yaml"),
    ({"ascii": ""}, "ascii"),
])
def test_observacao_invalida(observacoes, fontes, campos, trecho):
    ruim = replace(observacoes[0], **campos)
    with pytest.raises(ValidationError, match=trecho):
        validate([ruim], fontes)


def test_nome_so_com_espacos_e_recusado(fontes):
    o = make_observation("   ", kind="given", source_id="wikidata", count_type="attested")
    with pytest.raises(ValidationError, match="'name' vazio"):
        validate([o], fontes)


def test_duplicata_pela_chave(observacoes, fontes):
    with pytest.raises(ValidationError, match="duplicata"):
        validate([observacoes[0], replace(observacoes[0], count=1)], fontes)


def test_mesma_chave_em_kind_diferente_nao_e_duplicata(fontes):
    a = make_observation("Thomas", kind="given", source_id="wikidata", count_type="attested")
    b = make_observation("Thomas", kind="family", source_id="wikidata", count_type="attested")
    validate([a, b], fontes)


def test_lista_todos_os_erros(observacoes, fontes):
    ruim = replace(observacoes[0], gender="X", country="XX")
    with pytest.raises(ValidationError) as e:
        validate([ruim], fontes)
    assert len(e.value.erros) == 2
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_schema.py`
Esperado: FALHA com `ModuleNotFoundError: No module named 'namesio.schema'`

- [ ] **Passo 3: implementar** `src/namesio/schema.py`

```python
"""Tabela canônica de observações (spec 001, R1) e sua validação."""

from dataclasses import dataclass

from namesio.normalize import ascii_form, detect_script, name_key, normalize_name
from namesio.sources import COUNT_TYPES, Source, is_country

SCHEMA_VERSION = "1.0.0"
KINDS = ("given", "family")
GENDERS = ("F", "M")


@dataclass(frozen=True)
class Observation:
    name: str
    name_key: str
    ascii: str
    script: str
    kind: str
    country: str | None
    gender: str | None
    year: int | None
    count: int | None
    count_type: str
    source_id: str

    def key(self) -> tuple:
        """Chave de unicidade (R1.4)."""
        return (self.name_key, self.kind, self.country, self.gender, self.year, self.source_id)


class ValidationError(ValueError):
    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__(f"{len(erros)} erro(s) de validação:\n" + "\n".join(erros[:50]))


def make_observation(
    raw_name: str,
    *,
    kind: str,
    source_id: str,
    count_type: str,
    country: str | None = None,
    gender: str | None = None,
    year: int | None = None,
    count: int | None = None,
) -> Observation:
    """Constrói uma observação derivando name, name_key, ascii e script do nome publicado."""
    name = normalize_name(raw_name)
    script = detect_script(name)
    return Observation(
        name=name, name_key=name_key(name), ascii=ascii_form(name, script), script=script,
        kind=kind, country=country, gender=gender, year=year, count=count,
        count_type=count_type, source_id=source_id,
    )


def validate(observations: list[Observation], sources: dict[str, Source]) -> None:
    """Levanta ValidationError com todos os problemas encontrados."""
    erros: list[str] = []
    vistas: set[tuple] = set()
    for i, o in enumerate(observations):
        r = f"observação {i} ({o.name!r})"
        for campo in ("name", "name_key", "script", "kind", "count_type", "source_id"):
            if not getattr(o, campo):
                erros.append(f"{r}: '{campo}' vazio")
        if o.script == "Latn" and not o.ascii:
            erros.append(f"{r}: 'ascii' vazio em escrita latina")
        if o.kind and o.kind not in KINDS:
            erros.append(f"{r}: kind '{o.kind}' inválido")
        if o.country is not None and not is_country(o.country):
            erros.append(f"{r}: país '{o.country}' fora da ISO 3166-1 alfa-2")
        if o.gender is not None and o.gender not in GENDERS:
            erros.append(f"{r}: gender '{o.gender}' inválido")
        if o.count is not None and o.count < 0:
            erros.append(f"{r}: count negativo")
        if o.count_type and o.count_type not in COUNT_TYPES:
            erros.append(f"{r}: count_type '{o.count_type}' inválido")
        if (o.count is None) != (o.count_type == "attested"):
            erros.append(f"{r}: count vazio exige count_type 'attested' e vice-versa (R1.1)")
        if o.source_id and o.source_id not in sources:
            erros.append(f"{r}: source_id '{o.source_id}' ausente de sources.yaml")
        if o.key() in vistas:
            erros.append(f"{r}: duplicata pela chave (R1.4) {o.key()}")
        vistas.add(o.key())
    if erros:
        raise ValidationError(erros)
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: todos os testes passam

- [ ] **Passo 5: commit**

```bash
git add tests/test_schema.py src/namesio/schema.py tests/conftest.py
git commit -m "Adiciona esquema canônico de observações e validação" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: agregação por país e índice mundial

**Arquivos:**
- Criar: `src/namesio/aggregate.py`
- Teste: `tests/test_aggregate.py`

**Interfaces:**
- Consome: `Observation`, `make_observation` (Task 4); `Source`, `parse_sources` (Task 3); `detect_script`, `ascii_form` (Task 2); fixtures da Task 4.
- Produz: `by_country(observations, sources) -> dict[str, list[CountryRow]]` (chaves em ordem alfabética), `name_index(observations, country_rows, kind) -> list[IndexRow]` (ordenado por `name_key`), `display_name(obs) -> str`, `CountryRow`, `CountryEntry`, `IndexRow`, `AggregationError`, `PRECEDENCIA`.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_aggregate.py`

```python
"""Critério de aceite 3: valores esperados calculados à mão a partir de tests/conftest.py."""

from dataclasses import replace
from datetime import date

import pytest

from namesio.aggregate import AggregationError, CountryEntry, by_country, display_name, name_index
from namesio.schema import make_observation
from namesio.sources import parse_sources


def _linha(rows, kind, chave):
    return next(r for r in rows if r.kind == kind and r.name_key == chave)


def test_paises_presentes(observacoes, fontes):
    assert list(by_country(observacoes, fontes)) == ["BR", "US"]


def test_us_births_soma_anos_so_da_fonte_primary(observacoes, fontes):
    us = by_country(observacoes, fontes)["US"]
    maria = _linha(us, "given", "maria")
    assert (maria.count, maria.count_type, maria.first_year, maria.last_year) == (155, "births", 2020, 2021)
    assert maria.female_share == pytest.approx(150 / 155)
    assert maria.gender_basis == 155


def test_us_rank_denso_decrescente(observacoes, fontes):
    us = by_country(observacoes, fontes)["US"]
    assert [(r.name_key, r.rank) for r in us] == [
        ("james", 1), ("maria", 2), ("deshawn", 3), ("ana clara", None),
    ]


def test_nome_so_na_fonte_secundaria_fica_sem_contagem(observacoes, fontes):
    ana = _linha(by_country(observacoes, fontes)["US"], "given", "ana clara")
    assert (ana.count, ana.count_type, ana.rank, ana.female_share, ana.gender_basis) == (
        None, "attested", None, None, 0,
    )


def test_forma_de_exibicao_usa_todas_as_fontes(observacoes, fontes):
    deshawn = _linha(by_country(observacoes, fontes)["US"], "given", "deshawn")
    assert deshawn.name == "DeShawn"  # 40 (us-births-b) > 30 (us-ssa)
    assert deshawn.count == 30  # mas a contagem vem só da primary


def test_br_population_usa_a_edicao_mais_recente(observacoes, fontes):
    br = by_country(observacoes, fontes)["BR"]
    maria = _linha(br, "given", "maria")
    assert (maria.name, maria.count, maria.first_year, maria.last_year) == ("Maria", 12000, 2022, 2022)
    assert (maria.female_share, maria.gender_basis) == (1.0, 12000)


def test_br_nome_com_espaco_e_sobrenome(observacoes, fontes):
    br = by_country(observacoes, fontes)["BR"]
    ana = _linha(br, "given", "ana clara")
    silva = _linha(br, "family", "silva")
    assert (ana.name, ana.count, ana.rank) == ("Ana Clara", 800, 2)
    assert (silva.name, silva.count, silva.rank, silva.female_share) == ("Silva", 5000, 1, None)


def test_population_tem_precedencia_sobre_births_no_mesmo_pais():
    fontes = parse_sources([
        {"id": "pop", "name": "p", "url": "https://p", "license": "CC0-1.0", "attribution": "p",
         "country": "FR", "count_type": "population", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
        {"id": "nas", "name": "n", "url": "https://n", "license": "CC0-1.0", "attribution": "n",
         "country": "FR", "count_type": "births", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
    ])
    obs = [
        make_observation("Léa", kind="given", source_id="pop", count_type="population",
                         country="FR", gender="F", year=2020, count=90000),
        make_observation("Léa", kind="given", source_id="nas", count_type="births",
                         country="FR", gender="F", year=2020, count=4000),
    ]
    lea = by_country(obs, fontes)["FR"][0]
    assert (lea.count, lea.count_type) == (90000, "population")


def test_rank_separado_por_count_type():
    fontes = parse_sources([
        {"id": "pop", "name": "p", "url": "https://p", "license": "CC0-1.0", "attribution": "p",
         "country": "FR", "count_type": "population", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
        {"id": "nas", "name": "n", "url": "https://n", "license": "CC0-1.0", "attribution": "n",
         "country": "FR", "count_type": "births", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
    ])
    obs = [
        make_observation("Léa", kind="given", source_id="pop", count_type="population",
                         country="FR", year=2020, count=90000),
        make_observation("Jade", kind="given", source_id="nas", count_type="births",
                         country="FR", year=2020, count=4000),
    ]
    assert {(r.name, r.count_type, r.rank) for r in by_country(obs, fontes)["FR"]} == {
        ("Léa", "population", 1), ("Jade", "births", 1),
    }


def test_indice_given(observacoes, fontes):
    indice = name_index(observacoes, by_country(observacoes, fontes), "given")
    assert [r.name_key for r in indice] == ["ana clara", "deshawn", "james", "maria", "мария"]
    maria = indice[3]
    assert maria.country_count == 2
    assert maria.countries == (
        CountryEntry("BR", 12000, "population", 1),
        CountryEntry("US", 155, "births", 2),
    )
    assert maria.female_share == pytest.approx(12150 / 12155)
    assert maria.gender_basis == 12155
    assert maria.sources == ("br-ibge-censo", "us-births-b", "us-ssa", "wikidata")
    assert maria.group_id is None


def test_indice_nome_so_atestado(observacoes, fontes):
    maria_cirilico = name_index(observacoes, by_country(observacoes, fontes), "given")[4]
    assert (maria_cirilico.name, maria_cirilico.script, maria_cirilico.ascii) == ("Мария", "Cyrl", "")
    assert (maria_cirilico.country_count, maria_cirilico.countries) == (0, ())
    assert (maria_cirilico.female_share, maria_cirilico.gender_basis) == (None, 0)


def test_indice_family(observacoes, fontes):
    indice = name_index(observacoes, by_country(observacoes, fontes), "family")
    assert [(r.name, r.script, r.country_count) for r in indice] == [("Silva", "Latn", 1), ("李", "Hani", 0)]


def test_empate_na_forma_de_exibicao_vai_para_ordem_lexicografica():
    a = make_observation("Mcdonald", kind="family", source_id="x", count_type="attested")
    b = make_observation("McDonald", kind="family", source_id="y", count_type="attested")
    assert display_name([a, b]) == "McDonald"


def test_fontes_ambiguas_sem_primary():
    fontes = parse_sources([
        {"id": "a", "name": "a", "url": "https://a", "license": "CC0-1.0", "attribution": "a",
         "country": "FR", "count_type": "births", "primary": True, "suppression": None,
         "retrieved": date(2026, 1, 1)},
        {"id": "b", "name": "b", "url": "https://b", "license": "CC0-1.0", "attribution": "b",
         "country": None, "count_type": "births", "primary": False, "suppression": None,
         "retrieved": date(2026, 1, 1)},
    ])
    obs = [
        make_observation("Léa", kind="given", source_id="b", count_type="births",
                         country="FR", year=2020, count=1),
        make_observation("Jade", kind="given", source_id="b", count_type="births",
                         country="FR", year=2020, count=1),
    ]
    obs.append(make_observation("Léa", kind="given", source_id="a", count_type="births",
                                country="FR", year=2020, count=2))
    fr = by_country(obs, fontes)["FR"]
    assert {(r.name, r.count) for r in fr} == {("Léa", 2), ("Jade", None)}
    fontes_sem_primary = dict(fontes)
    fontes_sem_primary["a"] = replace(fontes["a"], primary=False)
    with pytest.raises(AggregationError, match="primary"):
        by_country(obs, fontes_sem_primary)
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_aggregate.py`
Esperado: FALHA com `ModuleNotFoundError: No module named 'namesio.aggregate'`

- [ ] **Passo 3: implementar** `src/namesio/aggregate.py`

```python
"""Saídas agregadas (spec 001, R3): listas por país e índice mundial."""

from collections import defaultdict
from dataclasses import dataclass, replace

from namesio.normalize import ascii_form, detect_script
from namesio.schema import Observation
from namesio.sources import Source

# Ordem de preferência quando o mesmo nome tem contagens de tipos diferentes no país.
PRECEDENCIA = ("population", "births")


class AggregationError(ValueError):
    """Dados que impedem uma agregação inequívoca."""


@dataclass(frozen=True)
class CountryRow:
    country: str
    kind: str
    name: str
    name_key: str
    ascii: str
    script: str
    count: int | None
    count_type: str
    rank: int | None
    female_share: float | None
    gender_basis: int
    female: int  # interno: alimenta o índice mundial; não sai no CSV
    first_year: int | None
    last_year: int | None


@dataclass(frozen=True)
class CountryEntry:
    country: str
    count: int | None
    count_type: str
    rank: int | None


@dataclass(frozen=True)
class IndexRow:
    name: str
    name_key: str
    ascii: str
    script: str
    country_count: int
    countries: tuple[CountryEntry, ...]
    female_share: float | None
    gender_basis: int
    group_id: str | None
    sources: tuple[str, ...]


def display_name(obs: list[Observation]) -> str:
    """Forma mais frequente por soma de count; empate: mais atestada; depois ordem lexicográfica."""
    peso: dict[str, int] = defaultdict(int)
    atestacoes: dict[str, int] = defaultdict(int)
    for o in obs:
        peso[o.name] += o.count or 0
        atestacoes[o.name] += 1
    return min(peso, key=lambda n: (-peso[n], -atestacoes[n], n))


def _fontes_oficiais(observations: list[Observation], sources: dict[str, Source]) -> dict[tuple, str]:
    """(país, count_type) -> source_id cuja contagem vale (R3.3)."""
    ids: dict[tuple, set[str]] = defaultdict(set)
    for o in observations:
        if o.count is not None and o.country is not None:
            ids[(o.country, o.count_type)].add(o.source_id)
    oficiais = {}
    for par, fs in ids.items():
        if len(fs) == 1:
            oficiais[par] = next(iter(fs))
            continue
        primarias = sorted(f for f in fs if sources[f].primary)
        if len(primarias) != 1:
            raise AggregationError(f"{par}: fontes {sorted(fs)} sem exatamente uma primary")
        oficiais[par] = primarias[0]
    return oficiais


def _contagem(obs: list[Observation], oficiais: dict[tuple, str]):
    """-> (count_type, observações contadas, first_year, last_year) para um nome num país."""
    pais = obs[0].country
    for tipo in PRECEDENCIA:
        fonte = oficiais.get((pais, tipo))
        contadas = [o for o in obs if o.count_type == tipo and o.source_id == fonte]
        if not contadas:
            continue
        anos = [o.year for o in contadas if o.year is not None]
        if tipo == "population" and anos:
            ultimo = max(anos)
            contadas = [o for o in contadas if o.year == ultimo]
            return tipo, contadas, ultimo, ultimo
        return tipo, contadas, (min(anos) if anos else None), (max(anos) if anos else None)
    return "attested", [], None, None


def _ranquear(linhas: list[CountryRow]) -> list[CountryRow]:
    """Rank denso por (kind, count_type), decrescente por count."""
    valores: dict[tuple, list[int]] = defaultdict(list)
    for r in linhas:
        if r.count is not None:
            valores[(r.kind, r.count_type)].append(r.count)
    posicao = {
        grupo: {v: i + 1 for i, v in enumerate(sorted(set(vs), reverse=True))}
        for grupo, vs in valores.items()
    }
    ranqueadas = [
        r if r.count is None else replace(r, rank=posicao[(r.kind, r.count_type)][r.count])
        for r in linhas
    ]
    return sorted(ranqueadas, key=lambda r: (r.kind, r.rank is None, r.count_type, r.rank or 0, r.name_key))


def by_country(observations: list[Observation], sources: dict[str, Source]) -> dict[str, list[CountryRow]]:
    oficiais = _fontes_oficiais(observations, sources)
    grupos: dict[tuple, list[Observation]] = defaultdict(list)
    for o in observations:
        if o.country is not None:
            grupos[(o.country, o.kind, o.name_key)].append(o)
    linhas: dict[str, list[CountryRow]] = defaultdict(list)
    for (pais, kind, chave), obs in grupos.items():
        tipo, contadas, primeiro, ultimo = _contagem(obs, oficiais)
        f = sum(o.count for o in contadas if o.gender == "F")
        m = sum(o.count for o in contadas if o.gender == "M")
        nome = display_name(obs)
        escrita = detect_script(nome)
        linhas[pais].append(CountryRow(
            country=pais, kind=kind, name=nome, name_key=chave,
            ascii=ascii_form(nome, escrita), script=escrita,
            count=sum(o.count for o in contadas) if contadas else None,
            count_type=tipo, rank=None,
            female_share=f / (f + m) if f + m else None, gender_basis=f + m, female=f,
            first_year=primeiro, last_year=ultimo,
        ))
    return {pais: _ranquear(rows) for pais, rows in sorted(linhas.items())}


def name_index(
    observations: list[Observation],
    country_rows: dict[str, list[CountryRow]],
    kind: str,
) -> list[IndexRow]:
    obs_por_chave: dict[str, list[Observation]] = defaultdict(list)
    for o in observations:
        if o.kind == kind:
            obs_por_chave[o.name_key].append(o)
    linhas_por_chave: dict[str, list[CountryRow]] = defaultdict(list)
    for rows in country_rows.values():
        for r in rows:
            if r.kind == kind:
                linhas_por_chave[r.name_key].append(r)
    indice = []
    for chave in sorted(obs_por_chave):
        obs = obs_por_chave[chave]
        rows = sorted(linhas_por_chave.get(chave, []), key=lambda r: r.country)
        nome = display_name(obs)
        escrita = detect_script(nome)
        female = sum(r.female for r in rows)
        base = sum(r.gender_basis for r in rows)
        indice.append(IndexRow(
            name=nome, name_key=chave, ascii=ascii_form(nome, escrita), script=escrita,
            country_count=len(rows),
            countries=tuple(CountryEntry(r.country, r.count, r.count_type, r.rank) for r in rows),
            female_share=female / base if base else None, gender_basis=base,
            group_id=None, sources=tuple(sorted({o.source_id for o in obs})),
        ))
    return indice
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: todos os testes passam

- [ ] **Passo 5: commit**

```bash
git add tests/test_aggregate.py src/namesio/aggregate.py
git commit -m "Adiciona agregação por país e índice mundial de nomes" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Parquet, CSV e manifesto

**Arquivos:**
- Criar: `src/namesio/io.py`, `src/namesio/manifest.py`
- Teste: `tests/test_io.py`

**Interfaces:**
- Consome: `Observation` (Task 4); `CountryRow`, `IndexRow`, `by_country`, `name_index` (Task 5); `SCHEMA_VERSION` (Task 4); `Source` (Task 3).
- Produz: `write_observations(observations, path)`, `read_observations(path) -> list[Observation]`, `write_index(rows, csv_path, parquet_path)`, `write_by_country(rows_by_country, directory)`, `build_manifest(release, out_dir, sources, used) -> dict`, `OBSERVATION_SCHEMA`, `INDEX_SCHEMA`.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_io.py`

```python
import csv
import json

import pyarrow.parquet as pq
import pytest

from namesio.aggregate import by_country, name_index
from namesio.io import read_observations, write_by_country, write_index, write_observations
from namesio.manifest import build_manifest


def test_observacoes_ida_e_volta(observacoes, tmp_path):
    p = tmp_path / "observations.parquet"
    write_observations(observacoes, p)
    assert read_observations(p) == observacoes


def test_indice_csv_e_parquet(observacoes, fontes, tmp_path):
    indice = name_index(observacoes, by_country(observacoes, fontes), "given")
    write_index(indice, tmp_path / "g.csv", tmp_path / "g.parquet")
    linhas = list(csv.DictReader(open(tmp_path / "g.csv", encoding="utf-8")))
    maria = next(l for l in linhas if l["name_key"] == "maria")
    assert json.loads(maria["countries"])[0] == {"country": "BR", "count": 12000, "count_type": "population", "rank": 1}
    assert json.loads(maria["sources"])[-1] == "wikidata"
    assert maria["female_share"] == "0.999589"
    assert next(l for l in linhas if l["name_key"] == "мария")["female_share"] == ""
    tabela = pq.read_table(tmp_path / "g.parquet").to_pylist()
    assert [t["name_key"] for t in tabela] == [l["name_key"] for l in linhas]
    assert next(t for t in tabela if t["name_key"] == "maria")["countries"][1]["count"] == 155


def test_by_country_csv(observacoes, fontes, tmp_path):
    write_by_country(by_country(observacoes, fontes), tmp_path / "by_country")
    assert sorted(p.name for p in (tmp_path / "by_country").iterdir()) == ["BR.csv", "US.csv"]
    us = list(csv.DictReader(open(tmp_path / "by_country" / "US.csv", encoding="utf-8")))
    assert us[0] == {
        "kind": "given", "name": "James", "name_key": "james", "ascii": "james", "script": "Latn",
        "count": "200", "count_type": "births", "rank": "1", "female_share": "0.000000",
        "gender_basis": "200", "first_year": "2021", "last_year": "2021",
    }
    assert "female" not in us[0]


def test_manifest(observacoes, fontes, tmp_path):
    write_by_country(by_country(observacoes, fontes), tmp_path / "by_country")
    write_observations(observacoes, tmp_path / "observations.parquet")
    m = build_manifest("2026.10", tmp_path, fontes, {o.source_id for o in observacoes})
    assert m["schema_version"] == "1.0.0"
    assert [s["id"] for s in m["sources"]] == ["br-ibge-censo", "us-births-b", "us-ssa", "wikidata"]
    assert m["files"]["observations.parquet"]["rows"] == len(observacoes)
    assert m["files"]["by_country/US.csv"]["rows"] == 4
    assert len(m["files"]["by_country/BR.csv"]["sha256"]) == 64


@pytest.mark.parametrize("release", ["2026-10", "2026.13", "26.10", "2026.10.0", "2026.1"])
def test_release_fora_do_formato(release, fontes, tmp_path):
    with pytest.raises(ValueError, match="AAAA.MM"):
        build_manifest(release, tmp_path, fontes, set())
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_io.py`
Esperado: FALHA com `ModuleNotFoundError: No module named 'namesio.io'`

- [ ] **Passo 3: implementar** `src/namesio/io.py`

```python
"""Leitura e escrita das tabelas em Parquet e CSV."""

import csv
import json
from dataclasses import asdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from namesio.aggregate import CountryRow, IndexRow
from namesio.schema import Observation

OBSERVATION_SCHEMA = pa.schema([
    ("name", pa.string()), ("name_key", pa.string()), ("ascii", pa.string()),
    ("script", pa.string()), ("kind", pa.string()), ("country", pa.string()),
    ("gender", pa.string()), ("year", pa.int32()), ("count", pa.int64()),
    ("count_type", pa.string()), ("source_id", pa.string()),
])

INDEX_SCHEMA = pa.schema([
    ("name", pa.string()), ("name_key", pa.string()), ("ascii", pa.string()),
    ("script", pa.string()), ("country_count", pa.int32()),
    ("countries", pa.list_(pa.struct([
        ("country", pa.string()), ("count", pa.int64()),
        ("count_type", pa.string()), ("rank", pa.int32()),
    ]))),
    ("female_share", pa.float64()), ("gender_basis", pa.int64()),
    ("group_id", pa.string()), ("sources", pa.list_(pa.string())),
])

INDEX_CSV_COLUMNS = [f.name for f in INDEX_SCHEMA]
COUNTRY_CSV_COLUMNS = [
    "kind", "name", "name_key", "ascii", "script", "count", "count_type", "rank",
    "female_share", "gender_basis", "first_year", "last_year",
]


def write_observations(observations: list[Observation], path: Path) -> None:
    tabela = pa.Table.from_pylist([asdict(o) for o in observations], schema=OBSERVATION_SCHEMA)
    pq.write_table(tabela, path)


def read_observations(path: Path) -> list[Observation]:
    return [Observation(**linha) for linha in pq.read_table(path).to_pylist()]


def _celula(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor:.6f}"
    return str(valor)


def _index_dict(r: IndexRow) -> dict:
    return {
        **asdict(r),
        "countries": [asdict(c) for c in r.countries],
        "sources": list(r.sources),
    }


def write_index(rows: list[IndexRow], csv_path: Path, parquet_path: Path) -> None:
    dados = [_index_dict(r) for r in rows]
    pq.write_table(pa.Table.from_pylist(dados, schema=INDEX_SCHEMA), parquet_path)
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(INDEX_CSV_COLUMNS)
        for d in dados:
            w.writerow([
                json.dumps(d[c], ensure_ascii=False, separators=(",", ":"))
                if c in ("countries", "sources") else _celula(d[c])
                for c in INDEX_CSV_COLUMNS
            ])


def write_by_country(rows_by_country: dict[str, list[CountryRow]], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for pais, rows in rows_by_country.items():
        with open(directory / f"{pais}.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(COUNTRY_CSV_COLUMNS)
            for r in rows:
                w.writerow([_celula(getattr(r, c)) for c in COUNTRY_CSV_COLUMNS])
```

- [ ] **Passo 4: implementar** `src/namesio/manifest.py`

```python
"""manifest.json de uma release (spec 001, R5)."""

import hashlib
import re
from pathlib import Path

import pyarrow.parquet as pq

from namesio.schema import SCHEMA_VERSION
from namesio.sources import Source

RELEASE = re.compile(r"\d{4}\.(0[1-9]|1[0-2])(\.[1-9]\d*)?")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _linhas(path: Path) -> int:
    if path.suffix == ".parquet":
        return pq.ParquetFile(path).metadata.num_rows
    with open(path, encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1  # desconta o cabeçalho


def build_manifest(release: str, out_dir: Path, sources: dict[str, Source], used: set[str]) -> dict:
    if not RELEASE.fullmatch(release):
        raise ValueError(f"release '{release}' fora do formato AAAA.MM[.N]")
    arquivos = {}
    for p in sorted(out_dir.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            arquivos[p.relative_to(out_dir).as_posix()] = {"sha256": _sha256(p), "rows": _linhas(p)}
    return {
        "release": release,
        "schema_version": SCHEMA_VERSION,
        "sources": [
            {"id": s.id, "license": s.license, "retrieved": s.retrieved.isoformat()}
            for s in sorted((sources[i] for i in used), key=lambda s: s.id)
        ],
        "files": arquivos,
    }
```

- [ ] **Passo 5: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: todos os testes passam

- [ ] **Passo 6: commit**

```bash
git add tests/test_io.py src/namesio/io.py src/namesio/manifest.py
git commit -m "Adiciona escrita em Parquet e CSV e manifesto da release" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: CLI

**Arquivos:**
- Criar: `src/namesio/cli.py`
- Teste: `tests/test_cli.py`

**Interfaces:**
- Consome: tudo das Tasks 3 a 6.
- Produz: `main(argv: list[str] | None = None) -> int`; comando `uv run namesio validate <obs.parquet> [--sources sources.yaml]` e `uv run namesio build <obs.parquet> --out <dir> --release AAAA.MM [--sources sources.yaml]`.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_cli.py`

```python
import json
from dataclasses import replace

import yaml

from namesio.cli import main
from namesio.io import write_observations

from conftest import FONTES


def _preparar(tmp_path, observacoes):
    fontes = tmp_path / "sources.yaml"
    fontes.write_text(yaml.safe_dump({"sources": FONTES}, allow_unicode=True), encoding="utf-8")
    obs = tmp_path / "obs.parquet"
    write_observations(observacoes, obs)
    return obs, fontes


def test_validate_ok(observacoes, tmp_path, capsys):
    obs, fontes = _preparar(tmp_path, observacoes)
    assert main(["validate", str(obs), "--sources", str(fontes)]) == 0
    assert "16 observações válidas" in capsys.readouterr().out


def test_validate_falha_com_mensagem(observacoes, tmp_path, capsys):
    obs, fontes = _preparar(tmp_path, [replace(observacoes[0], gender="X")])
    assert main(["validate", str(obs), "--sources", str(fontes)]) == 1
    assert "gender 'X'" in capsys.readouterr().err


def test_build_gera_todas_as_saidas(observacoes, tmp_path):
    obs, fontes = _preparar(tmp_path, observacoes)
    out = tmp_path / "dist"
    assert main(["build", str(obs), "--sources", str(fontes), "--out", str(out), "--release", "2026.10"]) == 0
    arquivos = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert arquivos == [
        "by_country/BR.csv", "by_country/US.csv", "family_names.csv", "family_names.parquet",
        "given_names.csv", "given_names.parquet", "manifest.json", "observations.parquet",
    ]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["release"] == "2026.10"
    assert "manifest.json" not in manifest["files"]


def test_build_recusa_release_invalida(observacoes, tmp_path, capsys):
    obs, fontes = _preparar(tmp_path, observacoes)
    assert main(["build", str(obs), "--sources", str(fontes), "--out", str(tmp_path / "d"), "--release", "out"]) == 1
    assert "AAAA.MM" in capsys.readouterr().err
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_cli.py`
Esperado: FALHA com `ModuleNotFoundError: No module named 'namesio.cli'`

- [ ] **Passo 3: implementar** `src/namesio/cli.py`

```python
"""Linha de comando: namesio validate | namesio build."""

import argparse
import json
import sys
from pathlib import Path

from namesio.aggregate import AggregationError, by_country, name_index
from namesio.io import read_observations, write_by_country, write_index, write_observations
from namesio.manifest import build_manifest
from namesio.schema import ValidationError, validate
from namesio.sources import SourceError, load_sources


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="namesio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("validate", "build"):
        p = sub.add_parser(nome)
        p.add_argument("observations", type=Path, help="observations.parquet")
        p.add_argument("--sources", type=Path, default=Path("sources.yaml"))
        if nome == "build":
            p.add_argument("--out", type=Path, required=True)
            p.add_argument("--release", required=True, help="AAAA.MM[.N]")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        fontes = load_sources(args.sources)
        obs = read_observations(args.observations)
        validate(obs, fontes)
        if args.cmd == "validate":
            print(f"OK: {len(obs)} observações válidas.")
            return 0
        paises = by_country(obs, fontes)
        args.out.mkdir(parents=True, exist_ok=True)
        write_observations(obs, args.out / "observations.parquet")
        for kind, base in (("given", "given_names"), ("family", "family_names")):
            write_index(name_index(obs, paises, kind), args.out / f"{base}.csv", args.out / f"{base}.parquet")
        write_by_country(paises, args.out / "by_country")
        manifest = build_manifest(args.release, args.out, fontes, {o.source_id for o in obs})
    except (SourceError, ValidationError, AggregationError, ValueError) as e:
        print(e, file=sys.stderr)
        return 1
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OK: {len(obs)} observações, {len(paises)} países em {args.out}.")
    return 0
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: todos os testes passam

- [ ] **Passo 5: commit**

```bash
git add tests/test_cli.py src/namesio/cli.py
git commit -m "Adiciona CLI namesio validate e build" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Passo 6: conferir o comando instalado**

Rodar: `uv run namesio --help`
Esperado: uso com os subcomandos `validate` e `build`.

- [ ] **Passo 7: suíte completa e push**

Rodar: `uv run pytest -q`
Esperado: `75 passed`

```bash
git push
```
