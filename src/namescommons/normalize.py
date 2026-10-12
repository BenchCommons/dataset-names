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
    # Spec 005, R1.4: escritas medidas como Zzzz nos dados reais.
    "ORIYA": "Orya", "BATAK": "Batk", "BRAHMI": "Brah", "PHOENICIAN": "Phnx",
    "SYRIAC": "Syrc", "TIFINAGH": "Tfng", "GOTHIC": "Goth", "CHEROKEE": "Cher",
    "MANDAIC": "Mand", "COPTIC": "Copt", "RUNIC": "Runr", "THAANA": "Thaa",
    "NKO": "Nkoo", "VAI": "Vaii",
}
# Escritas cujo nome Unicode tem duas palavras.
_ESCRITAS_DUPLAS = {
    "OL CHIKI": "Olck", "CANADIAN SYLLABICS": "Cans", "WARANG CITI": "Wara",
    "MEETEI MAYEK": "Mtei", "SYLOTI NAGRI": "Sylo", "EGYPTIAN HIEROGLYPH": "Egyp",
}
# R1.2: 々 é han; as marcas de som longo e de iteração do kana herdam a escrita vizinha.
# 々 e 〆 têm Script=Han no Unicode, mas o nome deles não começa por CJK.
_HAN_EXTRA = frozenset("々〆")
_SEM_ESCRITA = frozenset("ーｰゝゞヽヾ")
_JAPONES = frozenset({"Hani", "Hira", "Kana"})

# Separadores que iniciam uma nova palavra na capitalização.
_SEPARADORES = re.compile(r"([ \-'’])")

# Spec 005, R3: partículas em minúsculas fora da primeira palavra (fontes de caixa uniforme).
_PARTICULAS = frozenset({
    "da", "das", "de", "del", "della", "der", "den", "des", "di", "do", "dos", "du", "van", "von", "y",
})
_ARTIGOS = frozenset({"la", "las", "le", "los"})  # só logo depois de uma partícula (R3.2)
_ELISOES = ("d'", "l'")  # R3.3

# Spec 005, R2 (ADR 0012): transliteração para ASCII pelo ICAO Doc 9303, parte 3, seção 6
# (8.ª edição, 2021). Tabelas em minúsculas; o nome passa por casefold antes.
# Latim (tabela A): letras sem decomposição NFKD. Onde o ICAO dá alternativa ("AE or A"),
# fica a letra só; ə, ɛ, ɔ, ɣ e ʙ, ausentes do ICAO, usam a letra latina de mesma base.
_LATIM = {
    "ß": "ss", "ø": "o", "æ": "ae", "œ": "oe", "đ": "d", "ð": "d", "ł": "l",
    "þ": "th", "ı": "i", "ħ": "h", "ŧ": "t", "ŋ": "n", "ĳ": "ij",
    "ə": "e", "ɛ": "e", "ɔ": "o", "ɣ": "g", "ʙ": "b",
}
# Cirílico (tabela B), na forma padrão de cada letra, sem as exceções por língua.
# ь não tem transliteração no ICAO e é omitido; ћ, ausente da tabela, segue o ć sérvio.
_CIRILICO = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh",
    "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "ie", "ы": "y", "ь": "", "э": "e", "ю": "iu",
    "я": "ia", "ђ": "d", "є": "ie", "ѕ": "dz", "і": "i", "ї": "i", "ј": "j", "љ": "lj",
    "њ": "nj", "ќ": "k", "ў": "u", "џ": "dz", "ѫ": "u", "ѵ": "y", "ґ": "g", "ғ": "g",
    "һ": "c", "ћ": "c",
}
# R2.3: pontuação do nome.
_APOSTROFOS = frozenset("'’‘ʼʻʹʾʿ`´′")
_HIFENS = frozenset("-‐‑‒–")
_OMITIDOS = frozenset("·")
_TRANSLITERACAO = {**_LATIM, **_CIRILICO}
# Aplicada antes da NFKD, que decomporia ´ em espaço e acento.
_PONTUACAO = str.maketrans({**{c: "'" for c in _APOSTROFOS}, **{c: "-" for c in _HIFENS}})


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
        nome = _particulas("".join(p[:1].title() + p[1:] for p in partes))
    return unicodedata.normalize("NFC", nome)


def _particulas(nome: str) -> str:
    """Spec 005, R3.1 a R3.3: só palavras separadas por espaço e fora da primeira."""
    palavras = nome.split(" ")
    for i in range(1, len(palavras)):
        minuscula = palavras[i].lower()
        anterior = palavras[i - 1].lower()
        tem_seguinte = i + 1 < len(palavras)  # partícula no fim do nome é o próprio nome (John Van)
        if tem_seguinte and (minuscula in _PARTICULAS or (minuscula in _ARTIGOS and anterior in _PARTICULAS)):
            palavras[i] = minuscula
        elif minuscula[:2] in _ELISOES and len(minuscula) > 2:
            palavras[i] = minuscula[:2] + palavras[i][2:]
    return " ".join(palavras)


def name_key(name: str) -> str:
    """Identidade do nome: casefold em NFC, com acentos preservados."""
    return unicodedata.normalize("NFC", name.casefold())


def _escrita_da_letra(c: str) -> str:
    if c in _HAN_EXTRA:
        return "Hani"
    palavras = unicodedata.name(c, "").split(" ")
    if palavras[0] in ("FULLWIDTH", "HALFWIDTH"):
        palavras = palavras[1:]
    dupla = _ESCRITAS_DUPLAS.get(" ".join(palavras[:2]))
    return dupla or _ESCRITAS.get(palavras[0] if palavras else "", "Zzzz")


def detect_script(name: str) -> str:
    """Código ISO 15924 predominante entre as letras; Zyyy sem letras, Zzzz se desconhecido.

    Spec 005, R1: Jpan para han com kana, Hrkt para hiragana com katakana, Kore para hangul com han.
    """
    contagem: dict[str, int] = {}
    for c in name:
        if not c.isalpha() or c in _SEM_ESCRITA:
            continue
        codigo = _escrita_da_letra(c)
        contagem[codigo] = contagem.get(codigo, 0) + 1
    if not contagem:
        return "Zyyy"
    escritas = set(contagem)
    if len(escritas) > 1 and escritas <= _JAPONES and escritas & {"Hira", "Kana"}:
        # ISO 15924: Jpan é han com kana; Hrkt, hiragana com katakana sem han.
        return "Jpan" if "Hani" in escritas else "Hrkt"
    if escritas == {"Hang", "Hani"}:
        return "Kore"
    return max(sorted(contagem), key=lambda codigo: contagem[codigo])


def _ascii_do_caractere(c: str) -> str | None:
    """Transliteração de um caractere já em casefold e NFKD; None se não houver (R2.4)."""
    if c.isascii():
        return c
    if c in _OMITIDOS or unicodedata.category(c) in ("Mn", "Mc", "Me", "Cf"):
        return ""
    return _TRANSLITERACAO.get(c)


def ascii_form(name: str, script: str | None = None) -> str:
    """Forma ASCII em minúsculas (spec 005, R2; ADR 0012); vazia se algum caractere não tem transliteração.

    `script` não decide mais nada; fica na assinatura por compatibilidade.
    """
    partes = []
    # A NFKD pode criar maiúsculas (™ vira TM, ℳ vira M): casefold de novo depois dela.
    base = unicodedata.normalize("NFKD", name.casefold().translate(_PONTUACAO))
    for c in unicodedata.normalize("NFKD", base.casefold()):
        t = _ascii_do_caractere(c)
        if t is None:
            return ""
        partes.append(t)
    return "".join(partes)
