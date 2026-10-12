"""INE, primeiros nomes e sobrenomes dos residentes na Espanha com frequência de ao menos 20 (spec 003b, R2).

Dois arquivos da mesma edição, ambos population: nomes por sexo em XLSX (abas Hombres e Mujeres)
e sobrenomes em XLS (contagem pelo primeiro apellido). Só totais nacionais.
"""

import re
from collections.abc import Iterator
from pathlib import Path

from namescommons.adapters import FormatError, RawRecord, Resource, parse_code
from namescommons.spreadsheet import cell_count, rows, sheet_names

SOURCE_ID = "es-ine-residentes"
_BASE = "https://www.ine.es/daco/daco42/nombyapel/"
NOMES, APELLIDOS = "nombres_por_edad_media.xlsx", "apellidos_frecuencia.xls"
RESOURCES = [Resource(_BASE + NOMES, NOMES), Resource(_BASE + APELLIDOS, APELLIDOS)]

_SEXO = {"Hombres": "M", "Mujeres": "F"}
_DATA = re.compile(r"a fecha [0-9]{2}/[0-9]{2}/([0-9]{4})")
# ".." = menos de 5; na coluna lida não aparece, mas é o único marcador que o INE usa nestas tabelas.
MARCADORES = {".."}
_CABECALHO_NOMES = ["Orden", "Nombre", "Frecuencia"]
_CABECALHO_APELLIDOS = ["Orden", "Apellido", "Total"]


def _tabela(caminho: Path, aba: str, cabecalho: list[str], campo: str,
            acima: str | None = None) -> Iterator[tuple[int, str, int]]:
    """(ano, nome, contagem) de cada linha de dados da aba; contagem suprimida é omitida.

    O ano vem da frase 'a fecha DD/MM/AAAA' antes do cabeçalho. Com `acima`, a linha logo acima
    do cabeçalho precisa trazer esse texto na coluna da contagem (C).
    """
    onde = f"{caminho.name}, aba {aba!r}"
    ano, anterior, dentro, linhas = None, [], False, 0
    for numero, valores in rows(caminho, aba):
        if not dentro:
            if valores[:len(cabecalho)] == cabecalho:
                if ano is None:
                    raise FormatError(f"{onde}: frase 'a fecha DD/MM/AAAA' antes do cabeçalho não encontrada")
                if acima is not None and (anterior[2:3] != [acima]):
                    raise FormatError(f"{onde}, linha {numero}: esperava {acima!r} na coluna C da linha de cima, "
                                      f"veio {anterior}")
                dentro = True
                continue
            for valor in valores:
                m = _DATA.search(valor) if isinstance(valor, str) else None
                if m:
                    ano = int(m.group(1))
            anterior = valores
            continue
        valores = valores + [None] * (3 - len(valores))
        ordem, nome, contagem = valores[:3]
        if type(ordem) is not int:
            raise FormatError(f"{onde}, linha {numero}: ordem {ordem!r} não é inteiro")
        if not isinstance(nome, str) or not nome.strip():
            raise FormatError(f"{onde}, linha {numero}: nome vazio")
        try:
            n = cell_count(contagem, MARCADORES, campo)
        except FormatError as e:
            raise FormatError(f"{onde}, linha {numero}: {e}") from None
        linhas += 1
        if n is not None:
            yield ano, nome, n
    if not dentro:
        raise FormatError(f"{onde}: cabeçalho {cabecalho} não encontrado")
    if linhas == 0:
        raise FormatError(f"{onde}: nenhuma linha de dados depois do cabeçalho")


def _edicao(caminho: Path, aba: str) -> int | None:
    """Ano da frase 'a fecha DD/MM/AAAA' antes do primeiro dado da aba (None se ausente)."""
    for _, valores in rows(caminho, aba):
        if type(valores[0]) is int:
            break
        for valor in valores:
            m = _DATA.search(valor) if isinstance(valor, str) else None
            if m:
                return int(m.group(1))
    return None


def _confere_edicao(abas: list[tuple[Path, str]]) -> None:
    """Spec 003b, R2.3: as abas dos dois arquivos precisam ser da mesma edição.

    Com edições diferentes, a regra de population (spec 001, R3.3) ficaria só com a mais recente
    e apagaria as contagens do outro arquivo sem aviso.
    """
    anos = {(caminho.name, aba): _edicao(caminho, aba) for caminho, aba in abas}
    if len({a for a in anos.values() if a is not None}) > 1:
        lista = ", ".join(f"{arq}, aba {aba!r}: {ano}" for (arq, aba), ano in anos.items())
        raise FormatError(f"edições diferentes entre as abas: {lista}; o INE atualizou um arquivo e não o outro?")


def parse(files: dict[str, Path]) -> Iterator[RawRecord]:
    nomes, apellidos = Path(files[NOMES]), Path(files[APELLIDOS])
    abas_nomes, abas_apellidos = sheet_names(nomes), sheet_names(apellidos)
    _confere_edicao([(nomes, a) for a in abas_nomes] + [(apellidos, a) for a in abas_apellidos])
    for aba in abas_nomes:
        sexo = parse_code(aba, _SEXO, "aba de nomes")
        for ano, nome, n in _tabela(nomes, aba, _CABECALHO_NOMES, "Frecuencia"):
            yield RawRecord(name=nome, kind="given", country="ES", gender=sexo, year=ano, count=n)
    for aba in abas_apellidos:
        for ano, nome, n in _tabela(apellidos, aba, _CABECALHO_APELLIDOS, "Apellido 1º", acima="Apellido 1º"):
            yield RawRecord(name=nome, kind="family", country="ES", year=ano, count=n)
