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


def test_georgiano_nao_recebe_capital_errada():
    assert normalize_name("ნინო") == "ნინო"
