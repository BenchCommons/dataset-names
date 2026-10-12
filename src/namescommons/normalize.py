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
