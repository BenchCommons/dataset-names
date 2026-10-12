"""Spec 002, R4: cache de downloads, testado contra um servidor HTTP local."""

import hashlib
import json
from datetime import datetime

import pytest

from namescommons.adapters import Resource
from namescommons.cache import FetchError, cached_path, fetch_resource

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
    assert agente.startswith("namescommons/")
    assert "https://github.com/OpenSoftwareAlliance/names-commons-dataset" in agente


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


def _falha(servidor, caminho, *codigos):
    servidor.respostas[caminho] = list(codigos)
    return _recurso(servidor, caminho)


@pytest.mark.parametrize("codigo", [400, 401, 403, 404, 410])
def test_4xx_nao_e_tentado_de_novo(servidor, tmp_path, codigo):
    r = _falha(servidor, "/a.csv", codigo, codigo, codigo)
    esperas = []
    with pytest.raises(FetchError, match=f"após 1 tentativa.*{codigo}"):
        fetch_resource(tmp_path, "exemplo", r, espera=1.0, dormir=esperas.append)
    assert len(servidor.requisicoes) == 1
    assert esperas == []


@pytest.mark.parametrize("codigo", [408, 429, 500, 503])
def test_408_429_e_5xx_sao_tentados_de_novo(servidor, tmp_path, codigo):
    r = _falha(servidor, "/a.csv", codigo, codigo)
    assert fetch_resource(tmp_path, "exemplo", r, espera=0).read_bytes() == CORPO
    assert len(servidor.requisicoes) == 3


def test_erro_diferente_de_403_nao_traz_a_dica_do_cache(servidor, tmp_path):
    r = _falha(servidor, "/a.csv", 404)
    with pytest.raises(FetchError) as e:
        fetch_resource(tmp_path, "exemplo", r, espera=0)
    assert "navegador" not in str(e.value) and "--offline" not in str(e.value)


def test_403_traz_a_dica_do_cache(servidor, tmp_path):
    r = _falha(servidor, "/a.csv", 403)
    with pytest.raises(FetchError, match="baixe o arquivo pelo navegador"):
        fetch_resource(tmp_path, "exemplo", r, espera=0)


def test_content_length_malformado_vira_fetch_error(servidor, tmp_path):
    r = _recurso(servidor)
    servidor.cabecalho_tamanho["/a.csv"] = "abc"
    with pytest.raises(FetchError, match="Content-Length 'abc' inválido"):
        fetch_resource(tmp_path, "exemplo", r, espera=0, tentativas=1)
    assert list((tmp_path / "exemplo").iterdir()) == []


@pytest.mark.parametrize("n", [0, -1])
def test_tentativas_menor_que_um_e_recusada(servidor, tmp_path, n):
    with pytest.raises(ValueError, match="tentativas"):
        fetch_resource(tmp_path, "exemplo", _recurso(servidor), tentativas=n)
    assert servidor.requisicoes == []


def test_refresh_nao_deixa_meta_antigo_descrevendo_o_arquivo_novo(servidor, tmp_path, monkeypatch):
    """Se a gravação do meta falha, o meta antigo não pode continuar ao lado do arquivo novo."""
    r = _recurso(servidor)
    fetch_resource(tmp_path, "exemplo", r)
    servidor.arquivos["/a.csv"] = b"versao nova\n"

    def falha(destino, conteudo):
        raise OSError("disco cheio")

    monkeypatch.setattr("namescommons.cache._gravar_atomico", falha)
    with pytest.raises(FetchError, match="disco cheio"):
        fetch_resource(tmp_path, "exemplo", r, refresh=True, tentativas=1)
    meta = tmp_path / "exemplo" / "a.csv.meta.json"
    assert not meta.exists() or json.loads(meta.read_text(encoding="utf-8"))["size"] == (tmp_path / "exemplo" / "a.csv").stat().st_size
