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
