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

REPOSITORIO = "https://github.com/BenchCommons/dataset-names"
USER_AGENT = f"namescommons/{version('names-commons-dataset')} (+{REPOSITORIO})"
BLOCO = 1 << 16
ESPERA = 2.0  # segundos antes da segunda tentativa; dobra a cada nova tentativa


class FetchError(Exception):
    """Falha ao obter um recurso, da rede ou do cache."""


class BlockedError(FetchError):
    """O servidor devolveu uma página HTML no lugar do arquivo (spec 003e, R4.1); repetir não adianta."""


_PAGINAS = (".html", ".htm")


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
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            tipo = resposta.headers.get_content_type()  # sem parâmetros e em minúsculas
            if tipo == "text/html" and not destino.name.lower().endswith(_PAGINAS):
                raise BlockedError(f"o servidor devolveu uma página HTML ({tipo}) no lugar de {destino.name}")
            with open(temporario, "wb") as fh:
                anunciado = resposta.headers.get("Content-Length")
                while bloco := resposta.read(BLOCO):
                    fh.write(bloco)
                    h.update(bloco)
                    tamanho += len(bloco)
        if anunciado is not None:
            try:
                esperado = int(anunciado)
            except ValueError:
                raise FetchError(f"Content-Length {anunciado!r} inválido em {url}") from None
            if tamanho != esperado:
                raise FetchError(f"download incompleto de {url}: {tamanho} de {anunciado} bytes")
        meta = {
            "url": url,
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sha256": h.hexdigest(),
            "size": tamanho,
        }
        # O meta antigo sai antes do arquivo novo entrar: uma falha no meio deixa o arquivo sem meta
        # (o mesmo estado de um arquivo gravado à mão), nunca um meta descrevendo outro arquivo.
        arquivo_meta = destino.with_name(destino.name + ".meta.json")
        arquivo_meta.unlink(missing_ok=True)
        os.replace(temporario, destino)
        _gravar_atomico(
            arquivo_meta,
            (json.dumps(meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        return meta
    finally:
        temporario.unlink(missing_ok=True)


def _definitivo(e: Exception) -> bool:
    """4xx (exceto 408 e 429) é resposta definitiva do servidor: tentar de novo não muda nada."""
    return isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code not in (408, 429)


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
    if tentativas < 1:
        raise ValueError(f"tentativas deve ser pelo menos 1, recebeu {tentativas}")
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
        except BlockedError as e:
            raise BlockedError(
                f"falha ao baixar {resource.url}: {e}, provável bloqueio de download automático: "
                f"baixe o arquivo pelo navegador, grave-o em {destino} e rode com --offline"
            ) from e
        except (OSError, HTTPException, FetchError) as e:
            ultimo = e
            feitas = i + 1
            if _definitivo(e):
                break
            if feitas < tentativas:
                dormir(espera * 2**i)
    mensagem = f"falha ao baixar {resource.url} após {feitas} tentativa(s): {ultimo}"
    if isinstance(ultimo, urllib.error.HTTPError) and ultimo.code == 403:
        mensagem += (
            "; o servidor recusou o download automático: baixe o arquivo pelo navegador, "
            f"grave-o em {destino} e rode com --offline"
        )
    raise FetchError(mensagem)
