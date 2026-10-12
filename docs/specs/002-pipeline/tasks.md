# 002. Pipeline de ingestão: tarefas

Plano: [`plan.md`](plan.md). Spec: [`spec.md`](spec.md). Rodar todos os comandos na raiz do repositório, a partir da branch da spec 001. Antes da Task 1, rodar `uv sync` e conferir `uv run pytest -q` com `97 passed`.

Os arquivos de `src/` que já existem aparecem inteiros: substituir o conteúdo do arquivo pelo bloco. A linha **Mudanças** resume o que difere da versão anterior.

---

### Task 1: campos novos de `sources.yaml` e validação de `retrieved` e `url`

**Arquivos:**
- Modificar: `src/namesio/sources.py`
- Teste: `tests/test_sources_extensoes.py`

**Interfaces:**
- Consome: `parse_sources`, `load_sources`, `Source` (spec 001).
- Produz: `Source.uniform_case: bool = False` e `Source.adapter: bool = True` (campos opcionais no fim da dataclass), `OPCIONAIS`; `parse_sources` recusa `retrieved` com hora, `url` sem esquema `http`/`https` e opcionais não booleanos.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_sources_extensoes.py`

```python
"""Spec 002, R2 (campos opcionais) e a última recusa de R3 (retrieved e url)."""

from datetime import date, datetime

import pytest

from namesio.sources import SourceError, load_sources, parse_sources


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


@pytest.mark.parametrize("campo", ["uniform_case", "adapter"])
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
])
def test_url_sem_esquema_http_e_recusada(url):
    with pytest.raises(SourceError, match="http ou https"):
        parse_sources([fonte(url=url)])


@pytest.mark.parametrize("url", ["http://example.org/a.csv", "HTTPS://example.org/"])
def test_url_http_e_https_aceitas(url):
    assert parse_sources([fonte(url=url)])["pt-exemplo"].url == url
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_sources_extensoes.py`
Esperado: `15 failed, 2 passed` (os campos opcionais são recusados como desconhecidos; `datetime` e URLs sem `http` são aceitos)

- [ ] **Passo 3: substituir o conteúdo de** `src/namesio/sources.py`

**Mudanças:** importa `datetime` e `urlsplit`; `OPCIONAIS`; dois campos com padrão em `Source`; `_url_http`; recusas de `url`, `retrieved` com hora e opcionais não booleanos; `Source` recebe os opcionais com o padrão.

```python
"""Registro de fontes (sources.yaml), regras de licença do ADR 0001 e campos da spec 002 (R2)."""

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
        if isinstance(e["url"], str) and e["url"].strip() and not _url_http(e["url"]):
            erros.append(f"{rotulo}: 'url' deve usar o esquema http ou https")
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

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `114 passed`

- [ ] **Passo 5: commit**

```bash
git add tests/test_sources_extensoes.py src/namesio/sources.py
git commit -m "Adiciona uniform_case e adapter ao sources.yaml e valida retrieved e url" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: capitalização decidida pela fonte

**Arquivos:**
- Modificar: `src/namesio/normalize.py`, `src/namesio/schema.py`
- Teste: `tests/test_caixa_da_fonte.py`

**Interfaces:**
- Consome: `normalize_name`, `make_observation` (spec 001).
- Produz: `normalize_name(raw, uniform_case: bool | None = None)`; `derive_name_fields(raw_name, uniform_case=None) -> (name, name_key, ascii, script)`; `make_observation(..., uniform_case=None)`. `None` mantém a regra da spec 001.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_caixa_da_fonte.py`

```python
"""Spec 002, R1.3: a capitalização segue uniform_case da fonte, não a caixa de cada nome."""

import pytest

from namesio.normalize import normalize_name
from namesio.schema import derive_name_fields, make_observation


@pytest.mark.parametrize("bruto, esperado", [
    ("DJ", "DJ"),
    ("MARIA", "MARIA"),
    ("maria", "maria"),
    ("McDonald", "McDonald"),
    ("  ana   CLARA ", "ana CLARA"),
])
def test_fonte_de_caixa_mista_preserva_a_caixa_publicada(bruto, esperado):
    assert normalize_name(bruto, uniform_case=False) == esperado


@pytest.mark.parametrize("bruto, esperado", [
    ("DJ", "Dj"),
    ("MARIA", "Maria"),
    ("maria", "Maria"),
    ("McDonald", "Mcdonald"),
    ("JEAN-PIERRE", "Jean-Pierre"),
    ("O'NEILL", "O'Neill"),
    ("DA SILVA", "Da Silva"),
    ("李", "李"),
])
def test_fonte_de_caixa_uniforme_capitaliza_todos(bruto, esperado):
    assert normalize_name(bruto, uniform_case=True) == esperado


def test_sem_uniform_case_mantem_a_regra_da_001():
    assert normalize_name("MARIA") == "Maria"
    assert normalize_name("DJ") == "Dj"
    assert normalize_name("McDonald") == "McDonald"


def test_derive_name_fields():
    assert derive_name_fields("ÁLVARO", uniform_case=True) == ("Álvaro", "álvaro", "alvaro", "Latn")
    assert derive_name_fields("DJ", uniform_case=False) == ("DJ", "dj", "dj", "Latn")


def test_make_observation_aceita_uniform_case():
    o = make_observation("DJ", kind="given", source_id="x", count_type="attested", uniform_case=False)
    assert (o.name, o.name_key) == ("DJ", "dj")
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_caixa_da_fonte.py`
Esperado: FALHA na coleta com `ImportError: cannot import name 'derive_name_fields' from 'namesio.schema'`

- [ ] **Passo 3: substituir o conteúdo de** `src/namesio/normalize.py`

**Mudanças:** `normalize_name` ganha `uniform_case`; a heurística da 001 só roda quando ele é `None`.

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


def normalize_name(raw: str, uniform_case: bool | None = None) -> str:
    """Forma de exibição: NFC, espaços colapsados e capitalização por palavra.

    uniform_case=True capitaliza todo nome (a fonte publica tudo na mesma caixa);
    False preserva a caixa publicada; None decide pelo próprio nome (regra da spec 001).
    """
    nome = " ".join(unicodedata.normalize("NFC", raw).split())
    if uniform_case is None:
        tem_caixa = any(c.isupper() or c.islower() for c in nome)
        uniform_case = tem_caixa and nome in (nome.upper(), nome.lower())
    if uniform_case:
        partes = _SEPARADORES.split(nome.lower())
        nome = "".join(p[:1].title() + p[1:] for p in partes)
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

- [ ] **Passo 4: substituir o conteúdo de** `src/namesio/schema.py`

**Mudanças:** nova `derive_name_fields`; `make_observation` aceita `uniform_case` e usa `derive_name_fields`.

```python
"""Tabela canônica de observações (spec 001, R1) e sua validação."""

import unicodedata
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


def derive_name_fields(raw_name: str, uniform_case: bool | None = None) -> tuple[str, str, str, str]:
    """(name, name_key, ascii, script) derivados do nome publicado."""
    name = normalize_name(raw_name, uniform_case)
    script = detect_script(name)
    return name, name_key(name), ascii_form(name, script), script


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
    uniform_case: bool | None = None,
) -> Observation:
    """Constrói uma observação derivando name, name_key, ascii e script do nome publicado."""
    name, chave, forma_ascii, script = derive_name_fields(raw_name, uniform_case)
    return Observation(
        name=name, name_key=chave, ascii=forma_ascii, script=script,
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
        if o.name != " ".join(unicodedata.normalize("NFC", o.name).split()):
            erros.append(f"{r}: 'name' fora de NFC ou com espaços não colapsados (R1)")
        if o.name_key != name_key(o.name):
            erros.append(f"{r}: 'name_key' {o.name_key!r} diverge de name_key(name) (R1)")
        if o.script != detect_script(o.name):
            erros.append(f"{r}: 'script' {o.script!r} diverge da escrita detectada em name (R1)")
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

- [ ] **Passo 5: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `130 passed`

- [ ] **Passo 6: commit**

```bash
git add tests/test_caixa_da_fonte.py src/namesio/normalize.py src/namesio/schema.py
git commit -m "Decide a capitalização pela caixa declarada da fonte" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: validação cruzada com a fonte

**Arquivos:**
- Modificar: `src/namesio/schema.py`
- Teste: `tests/test_validacao_cruzada.py`

**Interfaces:**
- Consome: `Source.country`, `Source.count_type`; `validate` (spec 001).
- Produz: `validate` recusa `count_type` e `country` divergentes da fonte e `year` fora de `ANO_MINIMO = 1800` até o ano corrente mais um. País ou `count_type` inválidos não geram também o erro de divergência.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_validacao_cruzada.py`

```python
"""Spec 002, R3: validate confere a observação contra a fonte registrada e a faixa de year."""

from dataclasses import replace
from datetime import date

import pytest

from namesio.schema import ValidationError, make_observation, validate


def _ssa(**campos):
    base = dict(kind="given", source_id="us-ssa", count_type="births", country="US",
                gender="F", year=2020, count=10)
    return make_observation("Maria", **{**base, **campos})


def test_count_type_diferente_do_da_fonte(fontes):
    o = _ssa(count_type="population")
    with pytest.raises(ValidationError, match="count_type 'population' diverge da fonte 'us-ssa' \\('births'\\)"):
        validate([o], fontes)


def test_country_diferente_do_da_fonte(fontes):
    with pytest.raises(ValidationError, match="país 'BR' diverge da fonte 'us-ssa' \\('US'\\)"):
        validate([_ssa(country="BR")], fontes)


def test_country_vazio_em_fonte_nacional(fontes):
    with pytest.raises(ValidationError, match="país None diverge da fonte 'us-ssa'"):
        validate([_ssa(country=None)], fontes)


def test_fonte_sem_pais_aceita_qualquer_pais(fontes):
    o = make_observation("Maria", kind="given", source_id="wikidata", count_type="attested", country="PT")
    validate([o], fontes)


@pytest.mark.parametrize("ano", [1799, date.today().year + 2])
def test_year_fora_da_faixa(fontes, ano):
    with pytest.raises(ValidationError, match="year .* fora de 1800 a"):
        validate([_ssa(year=ano)], fontes)


@pytest.mark.parametrize("ano", [1800, date.today().year + 1, None])
def test_year_dentro_da_faixa(fontes, ano):
    validate([_ssa(year=ano)], fontes)


def test_pais_invalido_nao_gera_erro_duplicado(observacoes, fontes):
    with pytest.raises(ValidationError) as e:
        validate([replace(observacoes[0], country="XX")], fontes)
    assert len(e.value.erros) == 1
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_validacao_cruzada.py`
Esperado: `5 failed, 5 passed`

- [ ] **Passo 3: substituir o conteúdo de** `src/namesio/schema.py`

**Mudanças:** importa `date`; `ANO_MINIMO`; em `validate`, a fonte da observação é consultada para as divergências de país e `count_type`, e `year` é conferido contra a faixa.

```python
"""Tabela canônica de observações (spec 001, R1) e sua validação."""

import unicodedata
from dataclasses import dataclass
from datetime import date

from namesio.normalize import ascii_form, detect_script, name_key, normalize_name
from namesio.sources import COUNT_TYPES, Source, is_country

SCHEMA_VERSION = "1.0.0"
KINDS = ("given", "family")
GENDERS = ("F", "M")
ANO_MINIMO = 1800


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


def derive_name_fields(raw_name: str, uniform_case: bool | None = None) -> tuple[str, str, str, str]:
    """(name, name_key, ascii, script) derivados do nome publicado."""
    name = normalize_name(raw_name, uniform_case)
    script = detect_script(name)
    return name, name_key(name), ascii_form(name, script), script


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
    uniform_case: bool | None = None,
) -> Observation:
    """Constrói uma observação derivando name, name_key, ascii e script do nome publicado."""
    name, chave, forma_ascii, script = derive_name_fields(raw_name, uniform_case)
    return Observation(
        name=name, name_key=chave, ascii=forma_ascii, script=script,
        kind=kind, country=country, gender=gender, year=year, count=count,
        count_type=count_type, source_id=source_id,
    )


def validate(observations: list[Observation], sources: dict[str, Source]) -> None:
    """Levanta ValidationError com todos os problemas encontrados."""
    ano_maximo = date.today().year + 1
    erros: list[str] = []
    vistas: set[tuple] = set()
    for i, o in enumerate(observations):
        r = f"observação {i} ({o.name!r})"
        for campo in ("name", "name_key", "script", "kind", "count_type", "source_id"):
            if not getattr(o, campo):
                erros.append(f"{r}: '{campo}' vazio")
        if o.name != " ".join(unicodedata.normalize("NFC", o.name).split()):
            erros.append(f"{r}: 'name' fora de NFC ou com espaços não colapsados (R1)")
        if o.name_key != name_key(o.name):
            erros.append(f"{r}: 'name_key' {o.name_key!r} diverge de name_key(name) (R1)")
        if o.script != detect_script(o.name):
            erros.append(f"{r}: 'script' {o.script!r} diverge da escrita detectada em name (R1)")
        if o.script == "Latn" and not o.ascii:
            erros.append(f"{r}: 'ascii' vazio em escrita latina")
        if o.kind and o.kind not in KINDS:
            erros.append(f"{r}: kind '{o.kind}' inválido")
        fonte = sources.get(o.source_id)
        if o.country is not None and not is_country(o.country):
            erros.append(f"{r}: país '{o.country}' fora da ISO 3166-1 alfa-2")
        elif fonte is not None and fonte.country is not None and o.country != fonte.country:
            erros.append(f"{r}: país {o.country!r} diverge da fonte '{fonte.id}' ('{fonte.country}')")
        if o.gender is not None and o.gender not in GENDERS:
            erros.append(f"{r}: gender '{o.gender}' inválido")
        if o.count is not None and o.count < 0:
            erros.append(f"{r}: count negativo")
        if o.count_type and o.count_type not in COUNT_TYPES:
            erros.append(f"{r}: count_type '{o.count_type}' inválido")
        elif fonte is not None and o.count_type != fonte.count_type:
            erros.append(
                f"{r}: count_type '{o.count_type}' diverge da fonte '{fonte.id}' ('{fonte.count_type}')"
            )
        if o.year is not None and not ANO_MINIMO <= o.year <= ano_maximo:
            erros.append(f"{r}: year {o.year} fora de {ANO_MINIMO} a {ano_maximo}")
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
Esperado: `140 passed`

- [ ] **Passo 5: commit**

```bash
git add tests/test_validacao_cruzada.py src/namesio/schema.py
git commit -m "Valida observações contra a fonte registrada e a faixa de anos" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: robustez herdada da issue #2

**Arquivos:**
- Modificar: `src/namesio/aggregate.py`, `src/namesio/io.py`, `src/namesio/manifest.py`
- Teste: `tests/test_robustez.py`

**Interfaces:**
- Consome: `by_country`, `name_index`, `write_observations`, `write_index`, `build_manifest` (spec 001).
- Produz: `AggregationError` e `ValueError` com `source_id desconhecido` em vez de `KeyError`; escritas criam o diretório pai; `rows` do manifesto conta registros CSV.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_robustez.py`

```python
"""Spec 002, R9: robustez herdada da revisão da spec 001 (issue #2)."""

from datetime import date

import pytest

from namesio.aggregate import AggregationError, by_country, name_index
from namesio.io import read_observations, write_by_country, write_index, write_observations
from namesio.manifest import build_manifest
from namesio.schema import make_observation
from namesio.sources import parse_sources


def _fonte(id, country, count_type, primary=True):
    return {"id": id, "name": id, "url": f"https://{id}.example", "license": "CC0-1.0",
            "attribution": id, "country": country, "count_type": count_type, "primary": primary,
            "suppression": None, "retrieved": date(2026, 1, 1)}


def _nasc(nome, source_id="fr", count=1, **campos):
    return make_observation(nome, kind="given", source_id=source_id, count_type="births",
                            country="FR", year=2020, count=count, **campos)


def test_source_id_desconhecido_na_agregacao_e_erro_do_dominio():
    fontes = parse_sources([_fonte("fr", "FR", "births")])
    with pytest.raises(AggregationError, match="source_id desconhecido.*'outra'"):
        by_country([_nasc("Léa"), _nasc("Léa", source_id="outra")], fontes)


def test_source_id_desconhecido_no_manifesto_e_erro_do_dominio(tmp_path):
    fontes = parse_sources([_fonte("fr", "FR", "births")])
    with pytest.raises(ValueError, match="source_id desconhecido.*'outra'"):
        build_manifest("2026.10", tmp_path, fontes, {"fr", "outra"})


def test_escritas_criam_o_diretorio_pai(observacoes, fontes, tmp_path):
    write_observations(observacoes, tmp_path / "a" / "b" / "observations.parquet")
    indice = name_index(observacoes, by_country(observacoes, fontes), "given")
    write_index(indice, tmp_path / "c" / "g.csv", tmp_path / "d" / "g.parquet")
    assert (tmp_path / "a" / "b" / "observations.parquet").is_file()
    assert (tmp_path / "c" / "g.csv").is_file()
    assert (tmp_path / "d" / "g.parquet").is_file()


def test_manifesto_conta_registros_csv_e_nao_linhas_fisicas(tmp_path):
    (tmp_path / "x.csv").write_text('name,nota\n"Ana","linha 1\nlinha 2"\nBia,ok\n', encoding="utf-8")
    m = build_manifest("2026.10", tmp_path, {}, set())
    assert m["files"]["x.csv"]["rows"] == 2


def test_manifesto_conta_linhas_dos_indices(observacoes, fontes, tmp_path):
    paises = by_country(observacoes, fontes)
    write_index(name_index(observacoes, paises, "given"), tmp_path / "given_names.csv",
                tmp_path / "given_names.parquet")
    m = build_manifest("2026.10", tmp_path, fontes, {o.source_id for o in observacoes})
    assert m["files"]["given_names.csv"]["rows"] == 5
    assert m["files"]["given_names.parquet"]["rows"] == 5


def test_rank_denso_com_empate():
    fontes = parse_sources([_fonte("fr", "FR", "births")])
    obs = [_nasc("Léa", count=50), _nasc("Jade", count=50), _nasc("Emma", count=20), _nasc("Zoé", count=90)]
    fr = by_country(obs, fontes)["FR"]
    assert [(r.name, r.rank) for r in fr] == [("Zoé", 1), ("Jade", 2), ("Léa", 2), ("Emma", 3)]


def test_duas_fontes_primary_no_mesmo_par_e_erro():
    fontes = parse_sources([_fonte("fr", "FR", "births"), _fonte("mundo", None, "births")])
    obs = [_nasc("Léa"), _nasc("Léa", source_id="mundo")]
    with pytest.raises(AggregationError, match="sem exatamente uma primary"):
        by_country(obs, fontes)


def test_population_sem_ano():
    fontes = parse_sources([_fonte("pop", "FR", "population")])
    obs = [
        make_observation("Léa", kind="given", source_id="pop", count_type="population",
                         country="FR", gender="F", count=900),
        make_observation("Jade", kind="given", source_id="pop", count_type="population",
                         country="FR", gender="F", count=400),
    ]
    fr = by_country(obs, fontes)["FR"]
    assert [(r.name, r.count, r.rank, r.first_year, r.last_year) for r in fr] == [
        ("Léa", 900, 1, None, None), ("Jade", 400, 2, None, None),
    ]


def test_parquet_ida_e_volta_com_campos_vazios(tmp_path):
    obs = [
        make_observation("李", kind="family", source_id="wikidata", count_type="attested"),
        make_observation("Maria", kind="given", source_id="wikidata", count_type="attested",
                         country="PT"),
    ]
    assert (obs[0].country, obs[0].gender, obs[0].year, obs[0].count, obs[0].ascii) == (None, None, None, None, "")
    p = tmp_path / "observations.parquet"
    write_observations(obs, p)
    assert read_observations(p) == obs


def test_nome_de_exibicao_no_indice(observacoes, fontes):
    indice = name_index(observacoes, by_country(observacoes, fontes), "given")
    maria = next(r for r in indice if r.name_key == "maria")
    assert maria.name == "Maria"


def test_csv_por_pais_sem_contagem(observacoes, fontes, tmp_path):
    write_by_country(by_country(observacoes, fontes), tmp_path / "x" / "by_country")
    linhas = (tmp_path / "x" / "by_country" / "US.csv").read_text(encoding="utf-8").splitlines()
    assert linhas[-1] == "given,Ana Clara,ana clara,ana clara,Latn,,attested,,,0,,"
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_robustez.py`
Esperado: `4 failed, 7 passed` (`KeyError: 'outra'` na agregação e no manifesto, `FileNotFoundError` no diretório pai e `rows == 3` no CSV com quebra de linha)

- [ ] **Passo 3: substituir o conteúdo de** `src/namesio/aggregate.py`

**Mudanças:** `_fontes_oficiais` recusa `source_id` ausente de `sources` antes de qualquer consulta.

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
    desconhecidas = sorted({o.source_id for o in observations} - set(sources))
    if desconhecidas:
        raise AggregationError(f"source_id desconhecido em sources.yaml: {desconhecidas}")
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


def _edicoes(observations: list[Observation], oficiais: dict[tuple, str]) -> dict[str, int]:
    """país -> edição mais recente (maior year) da fonte population oficial (R3.3)."""
    edicoes: dict[str, int] = {}
    for o in observations:
        if (
            o.count_type == "population" and o.year is not None and o.country is not None
            and o.source_id == oficiais.get((o.country, "population"))
        ):
            edicoes[o.country] = max(edicoes.get(o.country, o.year), o.year)
    return edicoes


def _contagem(obs: list[Observation], oficiais: dict[tuple, str], edicoes: dict[str, int]):
    """-> (count_type, observações contadas, first_year, last_year) para um nome num país."""
    pais = obs[0].country
    for tipo in PRECEDENCIA:
        fonte = oficiais.get((pais, tipo))
        contadas = [o for o in obs if o.count_type == tipo and o.source_id == fonte]
        if not contadas:
            continue
        if tipo == "population" and pais in edicoes:
            ultimo = edicoes[pais]
            contadas = [o for o in contadas if o.year == ultimo]
            if not contadas:
                continue
            return tipo, contadas, ultimo, ultimo
        anos = [o.year for o in contadas if o.year is not None]
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
    edicoes = _edicoes(observations, oficiais)
    grupos: dict[tuple, list[Observation]] = defaultdict(list)
    for o in observations:
        if o.country is not None:
            grupos[(o.country, o.kind, o.name_key)].append(o)
    linhas: dict[str, list[CountryRow]] = defaultdict(list)
    for (pais, kind, chave), obs in grupos.items():
        tipo, contadas, primeiro, ultimo = _contagem(obs, oficiais, edicoes)
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

- [ ] **Passo 4: substituir o conteúdo de** `src/namesio/io.py`

**Mudanças:** `write_observations` e `write_index` criam o diretório pai.

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
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(tabela, path)


def read_observations(path: Path) -> list[Observation]:
    tabela = pq.read_table(path).select(OBSERVATION_SCHEMA.names).cast(OBSERVATION_SCHEMA)
    return [Observation(**linha) for linha in tabela.to_pylist()]


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
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
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

- [ ] **Passo 5: substituir o conteúdo de** `src/namesio/manifest.py`

**Mudanças:** `_linhas` usa `csv.reader`; `build_manifest` recusa `source_id` desconhecido.

```python
"""manifest.json de uma release (spec 001, R5)."""

import csv
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
    with open(path, encoding="utf-8", newline="") as fh:
        return max(sum(1 for _ in csv.reader(fh)) - 1, 0)  # desconta o cabeçalho


def build_manifest(release: str, out_dir: Path, sources: dict[str, Source], used: set[str]) -> dict:
    if not RELEASE.fullmatch(release):
        raise ValueError(f"release '{release}' fora do formato AAAA.MM[.N]")
    desconhecidas = sorted(used - set(sources))
    if desconhecidas:
        raise ValueError(f"source_id desconhecido em sources.yaml: {desconhecidas}")
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

- [ ] **Passo 6: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `151 passed`

- [ ] **Passo 7: commit**

```bash
git add tests/test_robustez.py src/namesio/aggregate.py src/namesio/io.py src/namesio/manifest.py
git commit -m "Trata fonte desconhecida, cria diretórios e conta registros CSV no manifesto" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: contrato do adaptador e adaptador de exemplo

**Arquivos:**
- Criar: `src/namesio/adapters/__init__.py`
- Criar (só teste): `tests/adaptadores/__init__.py`, `tests/adaptadores/exemplo.py`, `tests/fixtures/exemplo/primeiros.csv`, `tests/fixtures/exemplo/sobrenomes.csv`, `tests/fixtures/sources.yaml`
- Teste: `tests/test_adapters.py`

**Interfaces:**
- Consome: nada novo.
- Produz: `namesio.adapters`: `Resource(url, filename)`, `RawRecord(name, kind, country=None, gender=None, year=None, count=None)`, `AdapterError`, `DEFAULT_PACKAGE = "namesio.adapters"`, `module_name(source_id)`, `check_adapter(mod, source_id)`, `load_adapter(source_id, package=DEFAULT_PACKAGE)`. Pacote de teste `adaptadores` (importável porque o pytest põe `tests/` no `sys.path`) com o adaptador `exemplo`; `tests/fixtures/sources.yaml` com `exemplo` (`uniform_case: true`) e `manual` (`adapter: false`).

- [ ] **Passo 1: criar** `tests/fixtures/exemplo/primeiros.csv`

```csv
nome,sexo,ano,quantidade
MARIA,F,2020,100
MARIA,F,2020,20
MARIA,F,2021,80
JOÃO,M,2020,90
JOÃO,M,2021,110
ANA CLARA,F,2021,15
JOSÉ,M,2021,15
```

- [ ] **Passo 2: criar** `tests/fixtures/exemplo/sobrenomes.csv`

```csv
nome,sexo,ano,quantidade
SILVA,,2020,500
SANTOS, ,2020,300
```

- [ ] **Passo 3: criar** `tests/fixtures/sources.yaml`

```yaml
sources:
  - id: exemplo
    name: Fonte de exemplo para testes
    url: https://example.org/exemplo/
    license: CC0-1.0
    attribution: Exemplo
    country: PT
    count_type: births
    primary: true
    suppression: null
    retrieved: 2026-10-01
    uniform_case: true
  - id: manual
    name: Lista mantida à mão
    url: https://example.org/manual/
    license: CC0-1.0
    attribution: Exemplo
    country: null
    count_type: attested
    primary: false
    suppression: null
    retrieved: 2026-10-01
    adapter: false
```

- [ ] **Passo 4: criar** `tests/adaptadores/__init__.py`

```python
"""Adaptadores escritos só para teste (spec 002, critério de aceite 1)."""
```

- [ ] **Passo 5: criar** `tests/adaptadores/exemplo.py`

```python
"""Adaptador de exemplo, escrito só para teste (spec 002, critério de aceite 1).

Lê dois CSV no formato de um instituto fictício de Portugal: nomes em maiúsculas,
sexo em branco nos sobrenomes e uma linha repetida que o pipeline soma.
"""

import csv
from collections.abc import Iterator
from pathlib import Path

from namesio.adapters import RawRecord, Resource

SOURCE_ID = "exemplo"
RESOURCES = [
    Resource("https://example.org/exemplo/primeiros.csv", "primeiros.csv"),
    Resource("https://example.org/exemplo/sobrenomes.csv", "sobrenomes.csv"),
]


def _ler(path: Path, kind: str) -> Iterator[RawRecord]:
    with open(path, encoding="utf-8", newline="") as fh:
        for linha in csv.DictReader(fh):
            yield RawRecord(
                name=linha["nome"], kind=kind, country="PT", gender=linha["sexo"],
                year=int(linha["ano"]), count=int(linha["quantidade"]),
            )


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    yield from _ler(files["primeiros.csv"], "given")
    yield from _ler(files["sobrenomes.csv"], "family")
```

- [ ] **Passo 6: escrever o teste que falha** em `tests/test_adapters.py`

```python
"""Spec 002, R1 e R7: contrato do adaptador e parse do adaptador de exemplo sobre a fixture."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from namesio.adapters import AdapterError, RawRecord, Resource, check_adapter, load_adapter, module_name

FIXTURES = Path(__file__).parent / "fixtures"


def _parse(files):
    return iter(())


def _adaptador(**campos):
    base = dict(SOURCE_ID="x", RESOURCES=[Resource("https://example.org/a.csv", "a.csv")], parse=_parse)
    return SimpleNamespace(**{**base, **campos})


def test_nome_do_modulo():
    assert module_name("us-ssa-births") == "us_ssa_births"


def test_carrega_o_adaptador_de_exemplo():
    mod = load_adapter("exemplo", "adaptadores")
    assert mod.SOURCE_ID == "exemplo"
    assert [r.filename for r in mod.RESOURCES] == ["primeiros.csv", "sobrenomes.csv"]


def test_parse_da_fixture_sem_rede():
    mod = load_adapter("exemplo", "adaptadores")
    pasta = FIXTURES / "exemplo"
    registros = list(mod.parse({r.filename: pasta / r.filename for r in mod.RESOURCES}))
    assert registros == [
        RawRecord("MARIA", "given", "PT", "F", 2020, 100),
        RawRecord("MARIA", "given", "PT", "F", 2020, 20),
        RawRecord("MARIA", "given", "PT", "F", 2021, 80),
        RawRecord("JOÃO", "given", "PT", "M", 2020, 90),
        RawRecord("JOÃO", "given", "PT", "M", 2021, 110),
        RawRecord("ANA CLARA", "given", "PT", "F", 2021, 15),
        RawRecord("JOSÉ", "given", "PT", "M", 2021, 15),
        RawRecord("SILVA", "family", "PT", "", 2020, 500),
        RawRecord("SANTOS", "family", "PT", " ", 2020, 300),
    ]


def test_adaptador_inexistente():
    with pytest.raises(AdapterError, match="adaptadores.nao_existe"):
        load_adapter("nao-existe", "adaptadores")


def test_pacote_padrao_ainda_nao_tem_adaptadores():
    with pytest.raises(AdapterError, match="namesio.adapters.us_ssa"):
        load_adapter("us-ssa")


def test_adaptador_valido():
    check_adapter(_adaptador(), "x")


@pytest.mark.parametrize("campos, trecho", [
    ({"SOURCE_ID": "y"}, "SOURCE_ID 'y' diverge"),
    ({"RESOURCES": []}, "RESOURCES"),
    ({"RESOURCES": [("https://example.org/a.csv", "a.csv")]}, "RESOURCES"),
    ({"RESOURCES": [Resource("ftp://example.org/a.csv", "a.csv")]}, "http ou https"),
    ({"RESOURCES": [Resource("https://example.org/a.csv", "../a.csv")]}, "filename"),
    ({"RESOURCES": [Resource("https://example.org/a.csv", "a.csv.meta.json")]}, "filename"),
    ({"RESOURCES": [Resource("https://example.org/a.csv", "a.csv"),
                    Resource("https://example.org/b.csv", "a.csv")]}, "repetido"),
    ({"parse": None}, "parse"),
])
def test_adaptador_invalido(campos, trecho):
    with pytest.raises(AdapterError, match=trecho):
        check_adapter(_adaptador(**campos), "x")


def test_adaptador_sem_atributo():
    with pytest.raises(AdapterError, match="SOURCE_ID"):
        check_adapter(SimpleNamespace(RESOURCES=[], parse=_parse), "x")
```

- [ ] **Passo 7: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_adapters.py`
Esperado: FALHA na coleta com `ModuleNotFoundError: No module named 'namesio.adapters'`

- [ ] **Passo 8: implementar** `src/namesio/adapters/__init__.py`

```python
"""Contrato do adaptador de fonte (spec 002, R1).

Cada fonte com adaptador tem um módulo <pacote>.<id_com_underscore> que expõe
SOURCE_ID, RESOURCES (lista de Resource) e parse(files) -> Iterator[RawRecord].
"""

import importlib
from dataclasses import dataclass
from types import ModuleType
from urllib.parse import urlsplit

DEFAULT_PACKAGE = "namesio.adapters"


class AdapterError(Exception):
    """Adaptador ausente ou fora do contrato de R1."""


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


def load_adapter(source_id: str, package: str = DEFAULT_PACKAGE) -> ModuleType:
    nome = f"{package}.{module_name(source_id)}"
    try:
        mod = importlib.import_module(nome)
    except ImportError as e:
        raise AdapterError(f"não foi possível importar o adaptador {nome}: {e}") from e
    check_adapter(mod, source_id)
    return mod
```

- [ ] **Passo 9: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `166 passed`

- [ ] **Passo 10: commit**

```bash
git add tests/fixtures/exemplo/primeiros.csv tests/fixtures/exemplo/sobrenomes.csv tests/fixtures/sources.yaml tests/adaptadores/__init__.py tests/adaptadores/exemplo.py tests/test_adapters.py src/namesio/adapters/__init__.py
git commit -m "Define o contrato do adaptador e o adaptador de exemplo dos testes" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: cache de downloads

**Arquivos:**
- Criar: `src/namesio/cache.py`
- Modificar: `tests/conftest.py` (servidor HTTP local)
- Teste: `tests/test_cache.py`

**Interfaces:**
- Consome: `Resource` (Task 5).
- Produz: `namesio.cache`: `FetchError`, `USER_AGENT`, `ESPERA = 2.0`, `cached_path(cache_dir, source_id, filename)`, `fetch_resource(cache_dir, source_id, resource, *, refresh=False, offline=False, timeout=60.0, tentativas=3, espera=None, dormir=time.sleep) -> Path`. Fixture `servidor` (`ServidorLocal` com `arquivos`, `falhas`, `truncados`, `lentos`, `requisicoes`, `url()`, `caminhos()`).

- [ ] **Passo 1: substituir o conteúdo de `tests/conftest.py` (mantém as fontes e observações da 001 e acrescenta `ServidorLocal` e a fixture `servidor`)**

```python
"""Fixture do critério de aceite 3 da spec 001: duas fontes births no mesmo país (uma primary),
uma population, uma attested; escritas latina, cirílica e chinesa; nome com espaço.
Servidor HTTP local da spec 002 (R7): downloads testados sem rede."""

import threading
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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


class ServidorLocal:
    """Servidor HTTP em 127.0.0.1 com respostas programáveis por caminho."""

    def __init__(self):
        self.arquivos: dict[str, bytes] = {}
        self.falhas: dict[str, int] = {}  # caminho -> quantas respostas 500 antes de servir
        self.truncados: set[str] = set()  # caminhos que anunciam o dobro do tamanho e fecham
        self.lentos: dict[str, float] = {}  # caminho -> segundos de espera antes de responder
        self.requisicoes: list[tuple[str, str]] = []  # (caminho, User-Agent)
        servidor = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                servidor.requisicoes.append((self.path, self.headers.get("User-Agent", "")))
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

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)

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
```

- [ ] **Passo 2: escrever o teste que falha** em `tests/test_cache.py`

```python
"""Spec 002, R4: cache de downloads, testado contra um servidor HTTP local."""

import hashlib
import json
from datetime import datetime

import pytest

from namesio.adapters import Resource
from namesio.cache import FetchError, cached_path, fetch_resource

CORPO = "nome,sexo,ano,quantidade\nMARIA,F,2020,100\n".encode()


def _recurso(servidor, caminho="/a.csv", corpo=CORPO):
    servidor.arquivos[caminho] = corpo
    return Resource(servidor.url(caminho), caminho.lstrip("/"))


def test_baixa_e_grava_metadados(servidor, tmp_path):
    destino = fetch_resource(tmp_path, "exemplo", _recurso(servidor))
    assert destino == tmp_path / "exemplo" / "a.csv" == cached_path(tmp_path, "exemplo", "a.csv")
    assert destino.read_bytes() == CORPO
    meta = json.loads((tmp_path / "exemplo" / "a.csv.meta.json").read_text(encoding="utf-8"))
    assert set(meta) == {"url", "downloaded_at", "sha256", "size"}
    assert meta["url"] == servidor.url("/a.csv")
    assert meta["sha256"] == hashlib.sha256(CORPO).hexdigest()
    assert meta["size"] == len(CORPO)
    assert datetime.fromisoformat(meta["downloaded_at"]).tzinfo is not None


def test_user_agent_identifica_projeto_e_repositorio(servidor, tmp_path):
    fetch_resource(tmp_path, "exemplo", _recurso(servidor))
    agente = servidor.requisicoes[0][1]
    assert agente.startswith("namesio/")
    assert "https://github.com/webminas/names.io" in agente


def test_arquivo_no_cache_nao_e_baixado_de_novo(servidor, tmp_path):
    r = _recurso(servidor)
    fetch_resource(tmp_path, "exemplo", r)
    fetch_resource(tmp_path, "exemplo", r)
    assert servidor.caminhos() == ["/a.csv"]


def test_refresh_baixa_de_novo(servidor, tmp_path):
    r = _recurso(servidor)
    fetch_resource(tmp_path, "exemplo", r)
    servidor.arquivos["/a.csv"] = b"novo\n"
    destino = fetch_resource(tmp_path, "exemplo", r, refresh=True)
    assert servidor.caminhos() == ["/a.csv", "/a.csv"]
    assert destino.read_bytes() == b"novo\n"
    meta = json.loads((tmp_path / "exemplo" / "a.csv.meta.json").read_text(encoding="utf-8"))
    assert meta["size"] == 5


def test_offline_usa_o_cache_sem_rede(servidor, tmp_path):
    r = _recurso(servidor)
    fetch_resource(tmp_path, "exemplo", r)
    assert fetch_resource(tmp_path, "exemplo", r, offline=True).read_bytes() == CORPO
    assert servidor.caminhos() == ["/a.csv"]


def test_offline_sem_cache_falha_sem_rede(servidor, tmp_path):
    with pytest.raises(FetchError, match="a.csv ausente do cache e --offline"):
        fetch_resource(tmp_path, "exemplo", _recurso(servidor), offline=True)
    assert servidor.requisicoes == []


def test_offline_e_refresh_juntos_sao_recusados(servidor, tmp_path):
    with pytest.raises(ValueError, match="incompatíveis"):
        fetch_resource(tmp_path, "exemplo", _recurso(servidor), offline=True, refresh=True)


def test_download_interrompido_nao_fica_no_cache(servidor, tmp_path):
    r = _recurso(servidor)
    servidor.truncados.add("/a.csv")
    with pytest.raises(FetchError, match="incompleto"):
        fetch_resource(tmp_path, "exemplo", r, espera=0)
    assert list((tmp_path / "exemplo").iterdir()) == []


def test_refresh_interrompido_preserva_a_versao_anterior(servidor, tmp_path):
    r = _recurso(servidor)
    fetch_resource(tmp_path, "exemplo", r)
    servidor.arquivos["/a.csv"] = b"versao nova que nao chega inteira\n"
    servidor.truncados.add("/a.csv")
    with pytest.raises(FetchError):
        fetch_resource(tmp_path, "exemplo", r, refresh=True, espera=0)
    assert (tmp_path / "exemplo" / "a.csv").read_bytes() == CORPO
    assert sorted(p.name for p in (tmp_path / "exemplo").iterdir()) == ["a.csv", "a.csv.meta.json"]


def test_tres_tentativas_com_espera_crescente(servidor, tmp_path):
    r = _recurso(servidor)
    servidor.falhas["/a.csv"] = 2
    esperas = []
    destino = fetch_resource(tmp_path, "exemplo", r, espera=1.0, dormir=esperas.append)
    assert destino.read_bytes() == CORPO
    assert esperas == [1.0, 2.0]
    assert servidor.caminhos() == ["/a.csv"] * 3


def test_desiste_depois_de_tres_tentativas(servidor, tmp_path):
    r = _recurso(servidor)
    servidor.falhas["/a.csv"] = 5
    esperas = []
    with pytest.raises(FetchError, match="após 3 tentativa.*500"):
        fetch_resource(tmp_path, "exemplo", r, espera=1.0, dormir=esperas.append)
    assert esperas == [1.0, 2.0]
    assert len(servidor.requisicoes) == 3
    assert not (tmp_path / "exemplo" / "a.csv").exists()


def test_timeout(servidor, tmp_path):
    r = _recurso(servidor)
    servidor.lentos["/a.csv"] = 1.0
    with pytest.raises(FetchError, match="após 1 tentativa"):
        fetch_resource(tmp_path, "exemplo", r, timeout=0.2, tentativas=1)
    assert not (tmp_path / "exemplo" / "a.csv").exists()
```

- [ ] **Passo 3: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_cache.py`
Esperado: FALHA na coleta com `ModuleNotFoundError: No module named 'namesio.cache'`

- [ ] **Passo 4: implementar** `src/namesio/cache.py`

```python
"""Cache de downloads das fontes (spec 002, R4).

Cada recurso fica em cache/<source_id>/<filename>, com <filename>.meta.json ao lado.
"""

import hashlib
import json
import os
import time
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
    raise FetchError(f"falha ao baixar {resource.url} após {tentativas} tentativa(s): {ultimo}")
```

- [ ] **Passo 5: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `178 passed`

- [ ] **Passo 6: commit**

```bash
git add tests/conftest.py tests/test_cache.py src/namesio/cache.py
git commit -m "Adiciona cache de downloads com metadados, tentativas e escrita atômica" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: pipeline: de `RawRecord` a `Observation`, `fetch` e `ingest` por fonte

**Arquivos:**
- Criar: `src/namesio/pipeline.py`
- Teste: `tests/test_pipeline.py`

**Interfaces:**
- Consome: `derive_name_fields` (Task 2), `validate` (Task 3), `load_adapter` e `RawRecord` (Task 5), `fetch_resource` e `FetchError` (Task 6), fixture `servidor` (Task 6).
- Produz: `namesio.pipeline`: `PipelineError` (mensagem `fonte '<id>': <causa>`), `RecordError`, `to_observations(records, source) -> list[Observation]`, `select_sources(sources, ids) -> list[Source]`, `fetch_sources(selected, cache_dir, *, refresh=False, adapters=DEFAULT_PACKAGE, **opcoes)`, `ingest_sources(selected, sources, cache_dir, *, offline=False, adapters=DEFAULT_PACKAGE, **opcoes) -> list[Observation]`.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_pipeline.py`

```python
"""Spec 002, R1 e R5: transformação de RawRecord em Observation, fetch e ingest por fonte."""

import random
import shutil
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

import adaptadores.exemplo
from namesio.adapters import RawRecord, Resource
from namesio.pipeline import (
    PipelineError, RecordError, fetch_sources, ingest_sources, select_sources, to_observations,
)
from namesio.sources import load_sources, parse_sources

FIXTURES = Path(__file__).parent / "fixtures"


def _fonte(**campos):
    base = {"id": "pt-x", "name": "x", "url": "https://x.example", "license": "CC0-1.0",
            "attribution": "x", "country": "PT", "count_type": "births", "primary": True,
            "suppression": None, "retrieved": date(2026, 1, 1)}
    return next(iter(parse_sources([{**base, **campos}]).values()))


@pytest.fixture
def fontes_exemplo():
    return load_sources(FIXTURES / "sources.yaml")


def _cache_das_fixtures(destino: Path) -> Path:
    shutil.copytree(FIXTURES / "exemplo", destino / "exemplo")
    return destino


def _campos(obs):
    return [(o.name, o.kind, o.country, o.gender, o.year, o.count) for o in obs]


# R1.1 a R1.5 -------------------------------------------------------------------------------------

@pytest.mark.parametrize("vazio", ["", "   ", None])
def test_r1_1_country_e_gender_vazios_viram_none(vazio):
    fonte = _fonte(country=None, count_type="attested")
    [o] = to_observations([RawRecord("Maria", "given", country=vazio, gender=vazio)], fonte)
    assert (o.country, o.gender) == (None, None)


def test_r1_1_espacos_em_volta_sao_removidos():
    [o] = to_observations([RawRecord("Maria", "given", " PT ", " F ", 2020, 1)], _fonte())
    assert (o.country, o.gender) == ("PT", "F")


def test_r1_2_count_type_e_source_id_vem_da_fonte():
    [o] = to_observations([RawRecord("Maria", "given", "PT", "F", 2020, 1)], _fonte(count_type="births"))
    assert (o.count_type, o.source_id) == ("births", "pt-x")


def test_r1_3_fonte_de_caixa_uniforme_capitaliza():
    obs = to_observations([RawRecord("DJ", "given", "PT", "M", 2020, 3)], _fonte(uniform_case=True))
    assert obs[0].name == "Dj"


def test_r1_3_fonte_de_caixa_mista_preserva():
    obs = to_observations([RawRecord("DJ", "given", "PT", "M", 2020, 3),
                           RawRecord("MARIA", "given", "PT", "F", 2020, 3)], _fonte(uniform_case=False))
    assert sorted(o.name for o in obs) == ["DJ", "MARIA"]


def test_r1_4_repetidos_sao_somados():
    obs = to_observations([
        RawRecord("MARIA", "given", "PT", "F", 2020, 100),
        RawRecord("Maria", "given", "PT", "F", 2020, 20),
        RawRecord("MARIA", "given", "PT", "F", 2021, 80),
    ], _fonte(uniform_case=True))
    assert _campos(obs) == [("Maria", "given", "PT", "F", 2020, 120), ("Maria", "given", "PT", "F", 2021, 80)]


def test_r1_4_repetidos_sem_contagem_viram_uma_linha():
    fonte = _fonte(country=None, count_type="attested")
    obs = to_observations([RawRecord("Maria", "given"), RawRecord("Maria", "given")], fonte)
    assert _campos(obs) == [("Maria", "given", None, None, None, None)]


def test_r1_4_repetidos_com_e_sem_contagem_sao_recusados():
    with pytest.raises(RecordError, match="R1.4"):
        to_observations([RawRecord("Maria", "given", "PT", "F", 2020, 1),
                         RawRecord("Maria", "given", "PT", "F", 2020, None)], _fonte())


def test_r1_5_total_e_divisao_por_genero_juntos_sao_recusados():
    with pytest.raises(RecordError, match="R1.5.*'maria', 'given', 'PT', 2020"):
        to_observations([
            RawRecord("Maria", "given", "PT", "F", 2020, 100),
            RawRecord("Maria", "given", "PT", "", 2020, 100),
        ], _fonte())


def test_r1_5_anos_diferentes_nao_conflitam():
    obs = to_observations([
        RawRecord("Maria", "given", "PT", "F", 2020, 100),
        RawRecord("Maria", "given", "PT", None, 2021, 100),
    ], _fonte())
    assert len(obs) == 2


def test_saida_independe_da_ordem_dos_registros():
    registros = [RawRecord(n, k, "PT", g, a, 1) for n in ("Ana", "Bia", "Rui") for k in ("given", "family")
                 for g in ("F", "M") for a in (2020, 2021)]
    embaralhados = registros[:]
    random.Random(4).shuffle(embaralhados)
    assert to_observations(embaralhados, _fonte()) == to_observations(registros, _fonte())


# Seleção de fontes -----------------------------------------------------------------------------

def test_sem_ids_seleciona_as_fontes_com_adaptador(fontes_exemplo):
    assert [f.id for f in select_sources(fontes_exemplo, [])] == ["exemplo"]


def test_id_desconhecido(fontes_exemplo):
    with pytest.raises(PipelineError, match="fonte 'nao-existe' ausente de sources.yaml"):
        select_sources(fontes_exemplo, ["nao-existe"])


def test_id_sem_adaptador(fontes_exemplo):
    with pytest.raises(PipelineError, match="fonte 'manual' tem adapter: false"):
        select_sources(fontes_exemplo, ["manual"])


def test_nenhuma_fonte_com_adaptador():
    with pytest.raises(PipelineError, match="nenhuma fonte com adaptador"):
        select_sources({}, [])


# fetch e ingest -------------------------------------------------------------------------------

def test_ingest_offline_sobre_o_cache(fontes_exemplo, tmp_path):
    cache = _cache_das_fixtures(tmp_path)
    obs = ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, cache,
                         offline=True, adapters="adaptadores")
    assert _campos(obs) == [
        ("Santos", "family", "PT", None, 2020, 300),
        ("Silva", "family", "PT", None, 2020, 500),
        ("Ana Clara", "given", "PT", "F", 2021, 15),
        ("José", "given", "PT", "M", 2021, 15),
        ("João", "given", "PT", "M", 2020, 90),
        ("João", "given", "PT", "M", 2021, 110),
        ("Maria", "given", "PT", "F", 2020, 120),
        ("Maria", "given", "PT", "F", 2021, 80),
    ]
    assert {(o.count_type, o.source_id) for o in obs} == {("births", "exemplo")}


def test_ingest_offline_sem_cache_nomeia_a_fonte(fontes_exemplo, tmp_path):
    with pytest.raises(PipelineError, match="fonte 'exemplo': .*primeiros.csv ausente do cache"):
        ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, tmp_path,
                       offline=True, adapters="adaptadores")


def test_ingest_arquivo_corrompido_nomeia_a_fonte_e_a_causa(fontes_exemplo, tmp_path):
    cache = _cache_das_fixtures(tmp_path)
    (cache / "exemplo" / "sobrenomes.csv").write_text("nome,sexo,ano,quantidade\nSILVA,,2020,muitos\n",
                                                      encoding="utf-8")
    with pytest.raises(PipelineError, match="fonte 'exemplo': ValueError: .*'muitos'"):
        ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, cache,
                       offline=True, adapters="adaptadores")


def test_ingest_recusa_violacao_de_r1_5(fontes_exemplo, tmp_path):
    cache = _cache_das_fixtures(tmp_path)
    with open(cache / "exemplo" / "sobrenomes.csv", "a", encoding="utf-8") as fh:
        fh.write("SILVA,F,2020,200\n")
    with pytest.raises(PipelineError, match="fonte 'exemplo': R1.5"):
        ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, cache,
                       offline=True, adapters="adaptadores")


def test_ingest_valida_contra_a_fonte(fontes_exemplo, tmp_path):
    cache = _cache_das_fixtures(tmp_path)
    fontes = {**fontes_exemplo, "exemplo": replace(fontes_exemplo["exemplo"], country="BR")}
    erro = "(?s)fonte 'exemplo': .*erro\\(s\\) de validação.*diverge da fonte"
    with pytest.raises(PipelineError, match=erro):
        ingest_sources(select_sources(fontes, []), fontes, cache, offline=True, adapters="adaptadores")


@pytest.fixture
def exemplo_no_servidor(servidor, monkeypatch):
    for nome in ("primeiros.csv", "sobrenomes.csv"):
        servidor.arquivos[f"/exemplo/{nome}"] = (FIXTURES / "exemplo" / nome).read_bytes()
    monkeypatch.setattr(adaptadores.exemplo, "RESOURCES", [
        Resource(servidor.url("/exemplo/primeiros.csv"), "primeiros.csv"),
        Resource(servidor.url("/exemplo/sobrenomes.csv"), "sobrenomes.csv"),
    ])
    return servidor


def test_fetch_baixa_todos_os_recursos(fontes_exemplo, exemplo_no_servidor, tmp_path):
    fetch_sources(select_sources(fontes_exemplo, []), tmp_path, adapters="adaptadores")
    for nome in ("primeiros.csv", "sobrenomes.csv"):
        assert (tmp_path / "exemplo" / nome).read_bytes() == (FIXTURES / "exemplo" / nome).read_bytes()
        assert (tmp_path / "exemplo" / f"{nome}.meta.json").is_file()


def test_fetch_com_falha_nomeia_a_fonte(fontes_exemplo, exemplo_no_servidor, tmp_path):
    del exemplo_no_servidor.arquivos["/exemplo/sobrenomes.csv"]
    with pytest.raises(PipelineError, match="fonte 'exemplo': falha ao baixar .*sobrenomes.csv.*404"):
        fetch_sources(select_sources(fontes_exemplo, []), tmp_path, adapters="adaptadores", espera=0)


def test_ingest_sem_offline_baixa_o_que_falta(fontes_exemplo, exemplo_no_servidor, tmp_path):
    obs = ingest_sources(select_sources(fontes_exemplo, []), fontes_exemplo, tmp_path, adapters="adaptadores")
    assert len(obs) == 8
    assert sorted(exemplo_no_servidor.caminhos()) == ["/exemplo/primeiros.csv", "/exemplo/sobrenomes.csv"]
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_pipeline.py`
Esperado: FALHA na coleta com `ModuleNotFoundError: No module named 'namesio.pipeline'`

- [ ] **Passo 3: implementar** `src/namesio/pipeline.py`

```python
"""Pipeline de ingestão (spec 002, R1 e R5): fontes -> cache -> parse -> observações."""

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from namesio.adapters import DEFAULT_PACKAGE, AdapterError, RawRecord, load_adapter
from namesio.cache import FetchError, fetch_resource
from namesio.schema import Observation, ValidationError, derive_name_fields, validate
from namesio.sources import Source


class PipelineError(Exception):
    """Falha de uma fonte em fetch ou ingest; a mensagem nomeia a fonte e a causa."""


class RecordError(ValueError):
    """Registros de uma fonte que violam R1.4 ou R1.5."""


# Exceções cuja mensagem já explica a causa; as demais ganham o nome do tipo.
_ERROS_DO_DOMINIO = (AdapterError, FetchError, ValidationError, RecordError)


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


def to_observations(records: Iterable[RawRecord], source: Source) -> list[Observation]:
    """Aplica R1.1 a R1.5 aos registros brutos de uma fonte."""
    derivados: dict[str, tuple[str, str, str, str]] = {}
    unicas: dict[tuple, Observation] = {}
    for r in records:
        campos = derivados.get(r.name)
        if campos is None:
            campos = derivados[r.name] = derive_name_fields(r.name, source.uniform_case)
        nome, chave, forma_ascii, escrita = campos
        o = Observation(
            name=nome, name_key=chave, ascii=forma_ascii, script=escrita, kind=r.kind,
            country=_vazio(r.country), gender=_vazio(r.gender), year=r.year, count=r.count,
            count_type=source.count_type, source_id=source.id,
        )
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
            arquivos = {
                r.filename: fetch_resource(cache_dir, fonte.id, r, offline=offline, **opcoes)
                for r in mod.RESOURCES
            }
            obs = to_observations(mod.parse(arquivos), fonte)
            validate(obs, sources)
        except Exception as e:
            raise _falha(fonte, e) from e
        observacoes.extend(obs)
    return observacoes
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `203 passed`

- [ ] **Passo 5: commit**

```bash
git add tests/test_pipeline.py src/namesio/pipeline.py
git commit -m "Adiciona pipeline que transforma registros brutos em observações por fonte" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: comandos `fetch`, `ingest` e `run`

**Arquivos:**
- Modificar: `src/namesio/cli.py`
- Teste: `tests/test_cli_pipeline.py`

**Interfaces:**
- Consome: `select_sources`, `fetch_sources`, `ingest_sources`, `PipelineError` (Task 7); `DEFAULT_PACKAGE` (Task 5).
- Produz: `namesio fetch [ID ...] [--refresh]`, `namesio ingest [ID ...] --out ARQ [--offline]`, `namesio run --out DIR --release AAAA.MM [--offline] [--refresh]`; todos com `--sources`, `--cache` (padrão `cache`) e `--adapters` (padrão `namesio.adapters`). `validate` e `build` como na 001.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_cli_pipeline.py`

```python
"""Spec 002, R5 e R6, critérios de aceite 1, 3 e 4: fetch, ingest, build e run pela CLI."""

import csv
import json
import shutil
from pathlib import Path

import pyarrow.parquet as pq
import pytest

import adaptadores.exemplo
from namesio.adapters import Resource
from namesio.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
FONTES = str(FIXTURES / "sources.yaml")
ADAPTADORES = ["--sources", FONTES, "--adapters", "adaptadores"]

PT_CSV = """\
kind,name,name_key,ascii,script,count,count_type,rank,female_share,gender_basis,first_year,last_year
family,Silva,silva,silva,Latn,500,births,1,,0,2020,2020
family,Santos,santos,santos,Latn,300,births,2,,0,2020,2020
given,João,joão,joao,Latn,200,births,1,0.000000,200,2020,2021
given,Maria,maria,maria,Latn,200,births,1,1.000000,200,2020,2021
given,Ana Clara,ana clara,ana clara,Latn,15,births,2,1.000000,15,2021,2021
given,José,josé,jose,Latn,15,births,2,0.000000,15,2021,2021
"""


@pytest.fixture
def exemplo_no_servidor(servidor, monkeypatch):
    for nome in ("primeiros.csv", "sobrenomes.csv"):
        servidor.arquivos[f"/exemplo/{nome}"] = (FIXTURES / "exemplo" / nome).read_bytes()
    monkeypatch.setattr(adaptadores.exemplo, "RESOURCES", [
        Resource(servidor.url("/exemplo/primeiros.csv"), "primeiros.csv"),
        Resource(servidor.url("/exemplo/sobrenomes.csv"), "sobrenomes.csv"),
    ])
    return servidor


@pytest.fixture
def cache_das_fixtures(tmp_path):
    shutil.copytree(FIXTURES / "exemplo", tmp_path / "cache" / "exemplo")
    return tmp_path / "cache"


def test_criterio_1_fetch_ingest_build(exemplo_no_servidor, tmp_path, capsys):
    cache = str(tmp_path / "cache")
    obs = tmp_path / "trabalho" / "observations.parquet"
    assert main(["fetch", "--cache", cache, *ADAPTADORES]) == 0
    assert sorted(exemplo_no_servidor.caminhos()) == ["/exemplo/primeiros.csv", "/exemplo/sobrenomes.csv"]
    assert main(["ingest", "--out", str(obs), "--offline", "--cache", cache, *ADAPTADORES]) == 0
    assert "OK: 8 observações de 1 fonte(s)" in capsys.readouterr().out
    dist = tmp_path / "dist"
    assert main(["build", str(obs), "--sources", FONTES, "--out", str(dist), "--release", "2026.10"]) == 0
    assert (dist / "by_country" / "PT.csv").read_text(encoding="utf-8") == PT_CSV
    given = {l["name_key"]: l for l in csv.DictReader(open(dist / "given_names.csv", encoding="utf-8"))}
    assert list(given) == ["ana clara", "josé", "joão", "maria"]
    assert json.loads(given["maria"]["countries"]) == [
        {"country": "PT", "count": 200, "count_type": "births", "rank": 1},
    ]
    assert (given["maria"]["female_share"], given["maria"]["sources"]) == ("1.000000", '["exemplo"]')
    family = list(csv.DictReader(open(dist / "family_names.csv", encoding="utf-8")))
    assert [(l["name"], l["female_share"], l["gender_basis"]) for l in family] == [
        ("Santos", "", "0"), ("Silva", "", "0"),
    ]
    manifest = json.loads((dist / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sources"] == [{"id": "exemplo", "license": "CC0-1.0", "retrieved": "2026-10-01"}]


def test_criterio_3_fetch_sem_refresh_nao_repete_requisicao(exemplo_no_servidor, tmp_path):
    cache = str(tmp_path / "cache")
    assert main(["fetch", "exemplo", "--cache", cache, *ADAPTADORES]) == 0
    assert main(["fetch", "exemplo", "--cache", cache, *ADAPTADORES]) == 0
    assert len(exemplo_no_servidor.requisicoes) == 2
    assert main(["fetch", "exemplo", "--refresh", "--cache", cache, *ADAPTADORES]) == 0
    assert len(exemplo_no_servidor.requisicoes) == 4


def test_criterio_3_offline_sem_cache_falha_com_mensagem(tmp_path, capsys):
    out = tmp_path / "dist"
    args = ["run", "--offline", "--out", str(out), "--release", "2026.10", "--cache", str(tmp_path / "vazio")]
    assert main([*args, *ADAPTADORES]) == 1
    err = capsys.readouterr().err
    assert "fonte 'exemplo'" in err and "ausente do cache" in err
    assert "Traceback" not in err
    assert not out.exists()


def test_criterio_4_dois_runs_offline_identicos(cache_das_fixtures, tmp_path):
    saidas = []
    for n in (1, 2):
        out = tmp_path / f"dist{n}"
        args = ["run", "--offline", "--out", str(out), "--release", "2026.10", "--cache", str(cache_das_fixtures)]
        assert main([*args, *ADAPTADORES]) == 0
        saidas.append(out)
    a, b = saidas
    csvs = sorted(p.relative_to(a).as_posix() for p in a.rglob("*.csv"))
    assert csvs == ["by_country/PT.csv", "family_names.csv", "given_names.csv"]
    for nome in csvs:
        assert (a / nome).read_bytes() == (b / nome).read_bytes(), nome
    for nome in ("observations.parquet", "given_names.parquet", "family_names.parquet"):
        assert pq.read_table(a / nome).equals(pq.read_table(b / nome)), nome
    assert (a / "by_country" / "PT.csv").read_text(encoding="utf-8") == PT_CSV


def test_run_com_rede_baixa_e_gera_a_release(exemplo_no_servidor, tmp_path, capsys):
    out = tmp_path / "dist"
    args = ["run", "--out", str(out), "--release", "2026.10", "--cache", str(tmp_path / "cache")]
    assert main([*args, *ADAPTADORES]) == 0
    assert (out / "by_country" / "PT.csv").read_text(encoding="utf-8") == PT_CSV
    assert "OK: 8 observações, 1 países" in capsys.readouterr().out
    assert len(exemplo_no_servidor.requisicoes) == 2


def test_run_refresh_baixa_de_novo(exemplo_no_servidor, cache_das_fixtures, tmp_path):
    args = ["run", "--refresh", "--out", str(tmp_path / "dist"), "--release", "2026.10",
            "--cache", str(cache_das_fixtures)]
    assert main([*args, *ADAPTADORES]) == 0
    assert len(exemplo_no_servidor.requisicoes) == 2


def test_run_offline_e_refresh_sao_incompativeis(tmp_path, capsys):
    args = ["run", "--offline", "--refresh", "--out", str(tmp_path / "d"), "--release", "2026.10"]
    assert main([*args, *ADAPTADORES]) == 1
    assert "incompatíveis" in capsys.readouterr().err


def test_run_valida_release_antes_de_baixar(exemplo_no_servidor, tmp_path, capsys):
    args = ["run", "--out", str(tmp_path / "d"), "--release", "2026.13", "--cache", str(tmp_path / "c")]
    assert main([*args, *ADAPTADORES]) == 1
    assert "AAAA.MM" in capsys.readouterr().err
    assert exemplo_no_servidor.requisicoes == []


def test_run_recusa_out_nao_vazio(cache_das_fixtures, tmp_path, capsys):
    out = tmp_path / "dist"
    out.mkdir()
    (out / "guardado.txt").write_text("x", encoding="utf-8")
    args = ["run", "--offline", "--out", str(out), "--release", "2026.10", "--cache", str(cache_das_fixtures)]
    assert main([*args, *ADAPTADORES]) == 1
    assert "não está vazio" in capsys.readouterr().err


def test_fetch_com_falha_nomeia_a_fonte(exemplo_no_servidor, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("namesio.cache.ESPERA", 0)
    del exemplo_no_servidor.arquivos["/exemplo/primeiros.csv"]
    assert main(["fetch", "--cache", str(tmp_path / "cache"), *ADAPTADORES]) == 1
    err = capsys.readouterr().err
    assert "fonte 'exemplo'" in err and "404" in err
    assert "Traceback" not in err


def test_ingest_com_arquivo_corrompido_falha_sem_saida(cache_das_fixtures, tmp_path, capsys):
    (cache_das_fixtures / "exemplo" / "primeiros.csv").write_text("cabecalho,errado\n1,2\n", encoding="utf-8")
    obs = tmp_path / "observations.parquet"
    args = ["ingest", "--out", str(obs), "--offline", "--cache", str(cache_das_fixtures)]
    assert main([*args, *ADAPTADORES]) == 1
    err = capsys.readouterr().err
    assert "fonte 'exemplo': KeyError: 'nome'" in err
    assert not obs.exists()


def test_fonte_desconhecida_ou_manual(tmp_path, capsys):
    assert main(["fetch", "nao-existe", "--cache", str(tmp_path), *ADAPTADORES]) == 1
    assert "fonte 'nao-existe' ausente de sources.yaml" in capsys.readouterr().err
    assert main(["ingest", "manual", "--out", str(tmp_path / "o.parquet"), "--cache", str(tmp_path),
                 *ADAPTADORES]) == 1
    assert "adapter: false" in capsys.readouterr().err


def test_ajuda_lista_os_comandos(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    saida = capsys.readouterr().out
    for comando in ("fetch", "ingest", "validate", "build", "run"):
        assert comando in saida
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_cli_pipeline.py`
Esperado: `13 failed` (o argparse recusa `fetch`, `ingest` e `run` com `SystemExit: 2`)

- [ ] **Passo 3: substituir o conteúdo de** `src/namesio/cli.py`

**Mudanças:** subcomandos `fetch`, `ingest` e `run`; opções `--cache` e `--adapters`; `_saida_invalida` e `_build` compartilhados por `build` e `run`; `PipelineError` tratado como os demais erros do domínio.

```python
"""Linha de comando: namesio fetch | ingest | validate | build | run."""

import argparse
import json
import sys
from pathlib import Path

from pyarrow import ArrowException

from namesio.adapters import DEFAULT_PACKAGE
from namesio.aggregate import AggregationError, by_country, name_index
from namesio.io import read_observations, write_by_country, write_index, write_observations
from namesio.manifest import RELEASE, build_manifest
from namesio.pipeline import PipelineError, fetch_sources, ingest_sources, select_sources
from namesio.schema import Observation, ValidationError, validate
from namesio.sources import Source, SourceError, load_sources


def _opcoes_de_fonte(p: argparse.ArgumentParser, com_ids: bool = True) -> None:
    if com_ids:
        p.add_argument("ids", nargs="*", metavar="ID", help="fontes de sources.yaml (padrão: todas com adaptador)")
    p.add_argument("--cache", type=Path, default=Path("cache"), help="diretório do cache de downloads")
    p.add_argument("--adapters", default=DEFAULT_PACKAGE, help="pacote Python dos adaptadores")


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="namesio")
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="{fetch,ingest,validate,build,run}")
    p = sub.add_parser("fetch", help="baixa os recursos das fontes para o cache")
    _opcoes_de_fonte(p)
    p.add_argument("--refresh", action="store_true", help="baixa de novo mesmo com o arquivo no cache")
    p = sub.add_parser("ingest", help="roda os adaptadores sobre o cache e grava observations.parquet")
    _opcoes_de_fonte(p)
    p.add_argument("--out", type=Path, required=True, help="observations.parquet")
    p.add_argument("--offline", action="store_true", help="não acessa a rede; arquivo ausente do cache é erro")
    ajuda = {
        "validate": "valida um observations.parquet (spec 001)",
        "build": "gera as saídas da release a partir de um observations.parquet (spec 001)",
    }
    for nome in ("validate", "build"):
        p = sub.add_parser(nome, help=ajuda[nome])
        p.add_argument("observations", type=Path, help="observations.parquet")
        if nome == "build":
            p.add_argument("--out", type=Path, required=True)
            p.add_argument("--release", required=True, help="AAAA.MM[.N]")
    p = sub.add_parser("run", help="fetch, ingest e build em sequência")
    _opcoes_de_fonte(p, com_ids=False)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--release", required=True, help="AAAA.MM[.N]")
    p.add_argument("--offline", action="store_true", help="pula o fetch e não acessa a rede")
    p.add_argument("--refresh", action="store_true", help="baixa de novo mesmo com o arquivo no cache")
    for p in sub.choices.values():
        p.add_argument("--sources", type=Path, default=Path("sources.yaml"))
    return ap


def _erro(mensagem: str) -> int:
    print(mensagem, file=sys.stderr)
    return 1


def _saida_invalida(release: str, out: Path) -> str | None:
    if not RELEASE.fullmatch(release):
        return f"release '{release}' fora do formato AAAA.MM[.N]"
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        return f"--out {out} já existe e não está vazio; use um diretório novo"
    return None


def _build(obs: list[Observation], fontes: dict[str, Source], out: Path, release: str) -> int:
    """Grava as saídas da spec 001 em out; devolve o número de países."""
    paises = by_country(obs, fontes)
    out.mkdir(parents=True, exist_ok=True)
    write_observations(obs, out / "observations.parquet")
    for kind, base in (("given", "given_names"), ("family", "family_names")):
        write_index(name_index(obs, paises, kind), out / f"{base}.csv", out / f"{base}.parquet")
    write_by_country(paises, out / "by_country")
    manifest = build_manifest(release, out, fontes, {o.source_id for o in obs})
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(paises)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd in ("build", "run"):
        problema = _saida_invalida(args.release, args.out)
        if problema:
            return _erro(problema)
    if args.cmd == "run" and args.offline and args.refresh:
        return _erro("--offline e --refresh são incompatíveis")
    try:
        fontes = load_sources(args.sources)
        if args.cmd in ("fetch", "ingest", "run"):
            selecionadas = select_sources(fontes, getattr(args, "ids", []))
            if args.cmd == "fetch" or (args.cmd == "run" and not args.offline):
                fetch_sources(selecionadas, args.cache, refresh=args.refresh, adapters=args.adapters)
            if args.cmd == "fetch":
                print(f"OK: {len(selecionadas)} fonte(s) em {args.cache}.")
                return 0
            obs = ingest_sources(selecionadas, fontes, args.cache, offline=args.offline, adapters=args.adapters)
            if args.cmd == "ingest":
                write_observations(obs, args.out)
                print(f"OK: {len(obs)} observações de {len(selecionadas)} fonte(s) em {args.out}.")
                return 0
        else:
            try:
                obs = read_observations(args.observations)
            except (OSError, ArrowException, TypeError, KeyError) as e:
                return _erro(f"não foi possível ler {args.observations}: {e}")
            validate(obs, fontes)
            if args.cmd == "validate":
                print(f"OK: {len(obs)} observações válidas.")
                return 0
        paises = _build(obs, fontes, args.out, args.release)
    except (
        PipelineError, SourceError, ValidationError, AggregationError, ValueError, OSError, ArrowException,
    ) as e:
        return _erro(str(e))
    print(f"OK: {len(obs)} observações, {paises} países em {args.out}.")
    return 0
```

- [ ] **Passo 4: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `216 passed`

- [ ] **Passo 5: commit**

```bash
git add tests/test_cli_pipeline.py src/namesio/cli.py
git commit -m "Adiciona comandos fetch, ingest e run à CLI" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Passo 6: conferir**

Rodar: `uv run namesio --help`
Esperado: uso com os subcomandos `fetch`, `ingest`, `validate`, `build` e `run`.

---

### Task 9: CI no GitHub Actions e cache fora do git

**Arquivos:**
- Criar: `.github/workflows/ci.yml`
- Modificar: `.gitignore` (acrescentar `/cache/`)
- Teste: `tests/test_ci.py`

**Interfaces:**
- Consome: CLI da Task 8, adaptador e fixtures da Task 5.
- Produz: workflow `CI` em todo push e pull request: `uv sync`, `uv run pytest -q` e `namesio run --offline` sobre um cache copiado de `tests/fixtures/exemplo/`.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_ci.py`

```python
"""Spec 002, R7: o workflow da CI roda uv sync, pytest e namesio run --offline sobre as fixtures."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parent.parent
WORKFLOW = RAIZ / ".github" / "workflows" / "ci.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _comandos() -> list[str]:
    passos = _workflow()["jobs"]["testes"]["steps"]
    return [p["run"] for p in passos if "run" in p]


def test_roda_em_todo_push_e_pull_request():
    dados = _workflow()
    gatilhos = dados.get("on", dados.get(True))  # PyYAML lê a chave "on" como True
    assert set(gatilhos) == {"push", "pull_request"}


def test_passos_da_ci():
    comandos = _comandos()
    assert comandos[0] == "uv sync"
    assert comandos[1] == "uv run pytest -q"
    assert "namesio run --offline" in comandos[2]


def test_cache_fica_fora_do_git():
    assert "/cache/" in (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv fora do PATH")
def test_passo_offline_da_ci_roda_localmente(tmp_path):
    passo = next(p for p in _workflow()["jobs"]["testes"]["steps"] if "namesio run" in p.get("run", ""))
    ambiente = {**os.environ, **passo["env"], "RUNNER_TEMP": str(tmp_path)}
    r = subprocess.run(["bash", "-e", "-c", passo["run"]], cwd=RAIZ, env=ambiente,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "dist" / "by_country" / "PT.csv").is_file()
    assert "OK: 8 observações, 1 países" in r.stdout
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_ci.py`
Esperado: `4 failed` (`FileNotFoundError` em `.github/workflows/ci.yml` e `/cache/` ausente do `.gitignore`)

- [ ] **Passo 3: acrescentar o cache ao `.gitignore`**

```bash
cat >> .gitignore <<'EOF'

# Cache de downloads das fontes (spec 002, R4)
/cache/
EOF
```

- [ ] **Passo 4: implementar** `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  testes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - name: Instalar dependências
        run: uv sync
      - name: Testes
        run: uv run pytest -q
      - name: namesio run --offline sobre o cache montado a partir das fixtures
        env:
          PYTHONPATH: tests
        run: |
          mkdir -p "$RUNNER_TEMP/cache"
          cp -R tests/fixtures/exemplo "$RUNNER_TEMP/cache/exemplo"
          uv run namesio run --offline --sources tests/fixtures/sources.yaml --adapters adaptadores \
            --cache "$RUNNER_TEMP/cache" --out "$RUNNER_TEMP/dist" --release 2026.10
          test -s "$RUNNER_TEMP/dist/by_country/PT.csv"
```

- [ ] **Passo 5: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `220 passed`

- [ ] **Passo 6: commit**

```bash
git add .gitignore .github/workflows/ci.yml tests/test_ci.py
git commit -m "Adiciona CI com testes e run offline sobre as fixtures" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: medição de R8 e leitura e escrita colunares

**Arquivos:**
- Criar: `tools/bench_pipeline.py`
- Modificar: `src/namesio/io.py`, `src/namesio/schema.py`
- Teste: `tests/test_benchmark.py`

**Interfaces:**
- Consome: CLI da Task 8 (`ingest --offline` e `build`), contrato de adaptador da Task 5.
- Produz: `tools/bench_pipeline.py` (`main(argv)`, `total_de_observacoes(n)`), que gera N observações sintéticas, roda `ingest` e `build` pela CLI e registra tempo e pico de memória; `Observation` com `slots=True`; `write_observations` e `read_observations` colunares, com textos repetidos compartilhados.

- [ ] **Passo 1: escrever o teste que falha** em `tests/test_benchmark.py`

```python
"""Spec 002, R8: o script de medição roda de ponta a ponta, e as observações ocupam pouca memória."""

import importlib.util
import json
from pathlib import Path

from namesio.io import read_observations, write_observations

RAIZ = Path(__file__).resolve().parent.parent


def _bench():
    spec = importlib.util.spec_from_file_location("bench_pipeline", RAIZ / "tools" / "bench_pipeline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bench_com_poucas_observacoes(tmp_path, capsys):
    registro = tmp_path / "r8.json"
    assert _bench().main(["--observacoes", "1200", "--dir", str(tmp_path / "b"), "--registro", str(registro)]) == 0
    saida = capsys.readouterr().out
    assert "1200 observações" in saida and "dentro dos limites" in saida
    dados = json.loads(registro.read_text(encoding="utf-8"))
    assert dados["observacoes"] == 1200
    assert dados["ingest_s"] >= 0 and dados["build_s"] >= 0 and dados["memoria_pico_mb"] > 0
    assert (tmp_path / "b" / "dist" / "given_names.csv").is_file()


def test_numero_de_observacoes_e_multiplo_do_bloco(tmp_path):
    assert _bench().total_de_observacoes(3_000_000) == 3_000_000
    assert _bench().total_de_observacoes(1000) == 600


def test_observacao_sem_dicionario_por_instancia(observacoes):
    assert not hasattr(observacoes[0], "__dict__")


def test_leitura_compartilha_textos_repetidos(observacoes, tmp_path):
    p = tmp_path / "observations.parquet"
    write_observations(observacoes, p)
    lidas = read_observations(p)
    assert lidas == observacoes
    assert lidas[0].source_id is lidas[1].source_id
    assert lidas[0].name is lidas[1].name
```

- [ ] **Passo 2: rodar e ver falhar**

Rodar: `uv run pytest -q tests/test_benchmark.py`
Esperado: `4 failed` (`FileNotFoundError` em `tools/bench_pipeline.py`, `Observation` com `__dict__` e textos lidos sem compartilhamento)

- [ ] **Passo 3: implementar** `tools/bench_pipeline.py`

```python
"""Medição de R8 (spec 002): namesio ingest e build sobre observações sintéticas.

Gera um CSV sintético num cache, um adaptador temporário e um sources.yaml, e roda
os comandos reais da CLI. Registra tempo de cada etapa e pico de memória do processo.
Não roda na CI.

Uso: uv run python tools/bench_pipeline.py [--observacoes 3000000] [--dir DIR] [--registro r8.json]
"""

import argparse
import csv
import json
import platform
import resource
import sys
import tempfile
import time
from pathlib import Path

from namesio.cli import main as namesio

LIMITE_SEGUNDOS = 600
LIMITE_MB = 4096
PAISES = ("AR", "BR", "CA", "DE", "ES", "FR", "IT", "MX", "PT", "US")
ANOS = range(1990, 2020)
GENEROS = ("F", "M")
BLOCO = len(PAISES) * len(ANOS) * len(GENEROS)  # observações por nome
SILABAS = ("ma", "ri", "an", "jo", "se", "lu", "ca", "el", "in", "ra",
           "to", "ne", "li", "sa", "be", "do", "vi", "ga", "ru", "te")

FONTES_YAML = """\
sources:
  - id: sintetica
    name: Fonte sintética da medição de R8
    url: https://example.org/sintetica/
    license: CC0-1.0
    attribution: namesio
    country: null
    count_type: births
    primary: true
    suppression: null
    retrieved: 2026-10-01
    uniform_case: true
"""

ADAPTADOR = '''\
import csv
from namesio.adapters import RawRecord, Resource

SOURCE_ID = "sintetica"
RESOURCES = [Resource("https://example.org/sintetica/dados.csv", "dados.csv")]


def parse(files):
    with open(files["dados.csv"], encoding="utf-8", newline="") as fh:
        for nome, pais, genero, ano, contagem in csv.reader(fh):
            yield RawRecord(nome, "given", pais, genero, int(ano), int(contagem))
'''


def total_de_observacoes(pedidas: int) -> int:
    """Maior múltiplo de BLOCO que não passa de pedidas (no mínimo um bloco)."""
    return max(1, pedidas // BLOCO) * BLOCO


def _nome(i: int) -> str:
    silabas = []
    for _ in range(3):
        i, resto = divmod(i, len(SILABAS))
        silabas.append(SILABAS[resto])
    return "".join(silabas).upper()


def _gerar(base: Path, total: int) -> None:
    (base / "cache" / "sintetica").mkdir(parents=True)
    (base / "bench_adaptadores").mkdir()
    (base / "bench_adaptadores" / "__init__.py").write_text("", encoding="utf-8")
    (base / "bench_adaptadores" / "sintetica.py").write_text(ADAPTADOR, encoding="utf-8")
    (base / "sources.yaml").write_text(FONTES_YAML, encoding="utf-8")
    with open(base / "cache" / "sintetica" / "dados.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        for i in range(total // BLOCO):
            nome = _nome(i)
            for pais in PAISES:
                for ano in ANOS:
                    for g, genero in enumerate(GENEROS):
                        w.writerow((nome, pais, genero, ano, (i * 7919 + ano * 31 + g) % 5000 + 5))


def _memoria_pico_mb() -> float:
    pico = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return pico / (1024 * 1024) if sys.platform == "darwin" else pico / 1024


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--observacoes", type=int, default=3_000_000)
    ap.add_argument("--dir", type=Path, help="diretório de trabalho (padrão: temporário)")
    ap.add_argument("--registro", type=Path, help="grava o resultado em JSON")
    args = ap.parse_args(argv)
    total = total_de_observacoes(args.observacoes)
    base = args.dir or Path(tempfile.mkdtemp(prefix="namesio-r8-"))
    base.mkdir(parents=True, exist_ok=True)

    inicio = time.perf_counter()
    _gerar(base, total)
    geracao = time.perf_counter() - inicio
    comum = ["--sources", str(base / "sources.yaml")]
    sys.path.insert(0, str(base))
    try:
        inicio = time.perf_counter()
        codigo = namesio(["ingest", "--offline", "--out", str(base / "observations.parquet"),
                          "--cache", str(base / "cache"), "--adapters", "bench_adaptadores", *comum])
        ingest = time.perf_counter() - inicio
        if codigo != 0:
            return codigo
        inicio = time.perf_counter()
        codigo = namesio(["build", str(base / "observations.parquet"), "--out", str(base / "dist"),
                          "--release", "2026.10", *comum])
        build = time.perf_counter() - inicio
        if codigo != 0:
            return codigo
    finally:
        sys.path.remove(str(base))
        for modulo in [m for m in sys.modules if m.split(".")[0] == "bench_adaptadores"]:
            del sys.modules[modulo]

    memoria = _memoria_pico_mb()
    dentro = ingest + build < LIMITE_SEGUNDOS and memoria < LIMITE_MB
    resultado = {
        "observacoes": total, "geracao_s": round(geracao, 1), "ingest_s": round(ingest, 1),
        "build_s": round(build, 1), "memoria_pico_mb": round(memoria), "python": platform.python_version(),
        "maquina": f"{platform.system()} {platform.machine()}", "dentro_dos_limites": dentro,
    }
    print(
        f"R8: {total} observações; ingest {ingest:.1f} s, build {build:.1f} s, "
        f"pico de memória {memoria:.0f} MB; "
        + ("dentro dos limites" if dentro else f"FORA dos limites ({LIMITE_SEGUNDOS} s, {LIMITE_MB} MB)")
    )
    if args.registro:
        args.registro.write_text(json.dumps(resultado, indent=2) + "\n", encoding="utf-8")
    return 0 if dentro else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Passo 4: substituir o conteúdo de** `src/namesio/io.py`

**Mudanças:** `write_observations` monta a tabela por colunas; `_valores` decodifica colunas de texto por dicionário; `read_observations` monta as observações a partir das colunas.

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
    # Colunar: evita um dicionário por observação (R8, spec 002).
    colunas = {campo: [getattr(o, campo) for o in observations] for campo in OBSERVATION_SCHEMA.names}
    tabela = pa.Table.from_pydict(colunas, schema=OBSERVATION_SCHEMA)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(tabela, path)


def _valores(coluna: pa.ChunkedArray) -> list:
    """Valores Python da coluna; textos repetidos compartilham o mesmo objeto."""
    if not pa.types.is_string(coluna.type):
        return coluna.to_pylist()
    codificada = coluna.combine_chunks().dictionary_encode()
    textos = codificada.dictionary.to_pylist()
    return [None if i is None else textos[i] for i in codificada.indices.to_pylist()]


def read_observations(path: Path) -> list[Observation]:
    tabela = pq.read_table(path).select(OBSERVATION_SCHEMA.names).cast(OBSERVATION_SCHEMA)
    colunas = [_valores(tabela.column(campo)) for campo in OBSERVATION_SCHEMA.names]
    return [Observation(*valores) for valores in zip(*colunas)]


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
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
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

- [ ] **Passo 5: substituir o conteúdo de** `src/namesio/schema.py`

**Mudanças:** `Observation` passa a `@dataclass(frozen=True, slots=True)`.

```python
"""Tabela canônica de observações (spec 001, R1) e sua validação."""

import unicodedata
from dataclasses import dataclass
from datetime import date

from namesio.normalize import ascii_form, detect_script, name_key, normalize_name
from namesio.sources import COUNT_TYPES, Source, is_country

SCHEMA_VERSION = "1.0.0"
KINDS = ("given", "family")
GENDERS = ("F", "M")
ANO_MINIMO = 1800


@dataclass(frozen=True, slots=True)
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


def derive_name_fields(raw_name: str, uniform_case: bool | None = None) -> tuple[str, str, str, str]:
    """(name, name_key, ascii, script) derivados do nome publicado."""
    name = normalize_name(raw_name, uniform_case)
    script = detect_script(name)
    return name, name_key(name), ascii_form(name, script), script


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
    uniform_case: bool | None = None,
) -> Observation:
    """Constrói uma observação derivando name, name_key, ascii e script do nome publicado."""
    name, chave, forma_ascii, script = derive_name_fields(raw_name, uniform_case)
    return Observation(
        name=name, name_key=chave, ascii=forma_ascii, script=script,
        kind=kind, country=country, gender=gender, year=year, count=count,
        count_type=count_type, source_id=source_id,
    )


def validate(observations: list[Observation], sources: dict[str, Source]) -> None:
    """Levanta ValidationError com todos os problemas encontrados."""
    ano_maximo = date.today().year + 1
    erros: list[str] = []
    vistas: set[tuple] = set()
    for i, o in enumerate(observations):
        r = f"observação {i} ({o.name!r})"
        for campo in ("name", "name_key", "script", "kind", "count_type", "source_id"):
            if not getattr(o, campo):
                erros.append(f"{r}: '{campo}' vazio")
        if o.name != " ".join(unicodedata.normalize("NFC", o.name).split()):
            erros.append(f"{r}: 'name' fora de NFC ou com espaços não colapsados (R1)")
        if o.name_key != name_key(o.name):
            erros.append(f"{r}: 'name_key' {o.name_key!r} diverge de name_key(name) (R1)")
        if o.script != detect_script(o.name):
            erros.append(f"{r}: 'script' {o.script!r} diverge da escrita detectada em name (R1)")
        if o.script == "Latn" and not o.ascii:
            erros.append(f"{r}: 'ascii' vazio em escrita latina")
        if o.kind and o.kind not in KINDS:
            erros.append(f"{r}: kind '{o.kind}' inválido")
        fonte = sources.get(o.source_id)
        if o.country is not None and not is_country(o.country):
            erros.append(f"{r}: país '{o.country}' fora da ISO 3166-1 alfa-2")
        elif fonte is not None and fonte.country is not None and o.country != fonte.country:
            erros.append(f"{r}: país {o.country!r} diverge da fonte '{fonte.id}' ('{fonte.country}')")
        if o.gender is not None and o.gender not in GENDERS:
            erros.append(f"{r}: gender '{o.gender}' inválido")
        if o.count is not None and o.count < 0:
            erros.append(f"{r}: count negativo")
        if o.count_type and o.count_type not in COUNT_TYPES:
            erros.append(f"{r}: count_type '{o.count_type}' inválido")
        elif fonte is not None and o.count_type != fonte.count_type:
            erros.append(
                f"{r}: count_type '{o.count_type}' diverge da fonte '{fonte.id}' ('{fonte.count_type}')"
            )
        if o.year is not None and not ANO_MINIMO <= o.year <= ano_maximo:
            erros.append(f"{r}: year {o.year} fora de {ANO_MINIMO} a {ano_maximo}")
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

- [ ] **Passo 6: rodar e ver passar**

Rodar: `uv run pytest -q`
Esperado: `224 passed`

- [ ] **Passo 7: commit**

```bash
git add tests/test_benchmark.py tools/bench_pipeline.py src/namesio/io.py src/namesio/schema.py
git commit -m "Adiciona medição de R8 e leitura e escrita colunares de observações" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Passo 8: conferir**

Rodar: `uv run python tools/bench_pipeline.py`
Esperado: em alguns minutos, a linha `R8: 3000000 observações; ingest ... s, build ... s, pico de memória ... MB; dentro dos limites` e código de saída 0 (no protótipo, num Apple M4 com 24 GB: ingest 80 s, build 59 s, pico de 1400 MB). Copiar a linha `R8:` para a descrição do pull request (critério de aceite 6).

---

### Fechamento

- [ ] Rodar `uv run pytest -q` e ver `224 passed`.
- [ ] Abrir o pull request com `Closes #2` na descrição e a linha `R8:` da Task 10; conferir a CI verde no pull request (critério de aceite 5).
