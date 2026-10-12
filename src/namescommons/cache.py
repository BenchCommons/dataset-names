"""Cache de downloads das fontes (spec 002, R4).

Cada recurso fica em cache/<source_id>/<filename>, com <filename>.meta.json ao lado.
"""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from http.client import HTTPException
from importlib.metadata import version
from pathlib import Path

from namescommons.adapters import Resource

REPOSITORIO = "https://github.com/OpenSoftwareAlliance/names-commons-dataset"
USER_AGENT = f"namescommons/{version('names-commons-dataset')} (+{REPOSITORIO})"
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
    mensagem = f"falha ao baixar {resource.url} após {tentativas} tentativa(s): {ultimo}"
    if isinstance(ultimo, urllib.error.HTTPError) and ultimo.code == 403:
        mensagem += (
            f"; o servidor recusou o download automático: baixe o arquivo pelo navegador, "
            f"grave-o em {destino} e rode com --offline"
        )
    raise FetchError(mensagem)
