from namescommons.normalize import ascii_form, detect_script, name_key, normalize_name


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


def test_forma_ascii_vazia_fora_das_escritas_transliteradas():
    assert ascii_form("李", "Hani") == ""
    assert ascii_form("Μαρία", "Grek") == ""


def test_georgiano_nao_recebe_capital_errada():
    assert normalize_name("ნინო") == "ნინო"


# Spec 005, R1 (issue #4): escrita.
import pytest


@pytest.mark.parametrize("nome, escrita", [
    ("佐々木", "Hani"),        # 々 conta como han (R1.2)
    ("ユーリ", "Kana"),        # ー não conta (R1.2)
    ("Ａｎｎａ", "Latn"),      # latim de largura total (R1.1)
    ("ｱｲ", "Kana"),            # katakana de meia largura (R1.1)
    ("さくら子", "Jpan"),      # kanji e hiragana (R1.3)
    ("ゆかりユカリ", "Jpan"),  # hiragana e katakana (R1.3)
    ("ゆかり", "Hira"),
    ("김金", "Kore"),          # hangul e hanja (R1.3)
    ("ଦାସ", "Orya"),            # R1.4
    ("ܡܝܟܐܝܠ", "Syrc"),
    ("ᏣᎳᎩ", "Cher"),
    ("ᱥᱟᱱᱛᱟᱲ", "Olck"),       # prefixo de duas palavras
    ("ꯃꯤꯇꯩ", "Mtei"),
])
def test_escrita_r1(nome, escrita):
    assert detect_script(nome) == escrita


def test_escrita_fora_da_tabela_continua_zzzz():
    assert detect_script("\U00010300\U00010301") == "Zzzz"  # itálico antigo (OLD ITALIC)


def test_empate_de_escrita_resolvido_pela_ordem_do_codigo():
    assert detect_script("Aб") == "Cyrl"
    assert detect_script("ーー") == "Zyyy"


# Spec 005, R2 (issue #4; ADR 0012): forma ASCII.
@pytest.mark.parametrize("nome, esperado", [
    ("Ǆenana", "dzenana"),      # dígrafo de compatibilidade (NFKD)
    ("ﬁona", "fiona"),          # ligadura
    ("Ａｎｎａ", "anna"),        # largura total
    ("O’Brien", "o'brien"),     # apóstrofo curvo vira reto
    ("Hawaiʻi", "hawai'i"),     # ʻokina
    ("Jo–Anne", "jo-anne"),     # meia-risca vira hífen
    ("Əliyev", "eliyev"),
    ("Ŋgozi", "ngozi"),
    ("Kɔfi", "kofi"),
    ("Ɛsi", "esi"),
    ("Llorenç", "llorenc"),
    ("Nel·lo", "nello"),
    ("Pel·leja", "pelleja"),
    ("Strauß", "strauss"),
    ("Søren", "soren"),
    ("Æsa", "aesa"),
    ("Łukasz", "lukasz"),
    ("Þóra", "thora"),
    ("Ðorđe", "dorde"),
    ("İrem", "irem"),
    ("Mi\u200dna", "mina"),    # ZWJ omitido
    ("Иванов", "ivanov"),
    ("Мария", "mariia"),
    ("Щукин", "shchukin"),
    ("Пьер", "per"),            # ь omitido
    ("Ђоковић", "dokovic"),
    ("Їжак", "izhak"),
    ("Ґанна", "ganna"),
    ("Љиљана", "ljiljana"),
])
def test_forma_ascii_r2(nome, esperado):
    assert ascii_form(nome, detect_script(nome)) == esperado


@pytest.mark.parametrize("nome", ["Μαρία", "李", "ଦାସ", "Aʃa", "Maria李", "민준"])
def test_forma_ascii_vazia_quando_algum_caractere_nao_tem_transliteracao(nome):
    assert ascii_form(nome, detect_script(nome)) == ""


def test_acento_agudo_isolado_vira_apostrofo():
    assert ascii_form("D´Arcy", "Latn") == "d'arcy"
    assert ascii_form("D`Arcy", "Latn") == "d'arcy"
