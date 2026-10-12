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
_HAN_EXTRA = frozenset("々〆")
_SEM_ESCRITA = frozenset("ーゝゞヽヾ")
_JAPONES = frozenset({"Hani", "Hira", "Kana"})

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

    Spec 005, R1: Jpan para han com kana, Kore para hangul com han.
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
        return "Jpan"
    if escritas == {"Hang", "Hani"}:
        return "Kore"
    return max(sorted(contagem), key=lambda codigo: contagem[codigo])


def ascii_form(name: str, script: str) -> str:
    """Forma ASCII em minúsculas para escrita latina; vazia para as demais (spec 005 define o resto)."""
    if script != "Latn":
        return ""
    base = name.casefold().translate(_LATINAS_ESPECIAIS)
    base = unicodedata.normalize("NFD", base)
    return "".join(c for c in base if not unicodedata.combining(c) and c.isascii())
