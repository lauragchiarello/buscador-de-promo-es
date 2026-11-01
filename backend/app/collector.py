"""Coletor de casa: busca nas lojas que bloqueiam acesso da nuvem e devolve pelo banco.

Rode no seu computador (com o mesmo DATABASE_URL do site no Render):
    cd backend
    python -m app.collector
ou pelo Docker:  docker compose up -d coletor

Ele:
- avisa a cada 15 s que está ligado (o site mostra "coletor desligado" se parar);
- pega pedidos da fila (remote_jobs), busca na loja pela internet de casa
  (respeitando robots.txt, rate limit e bloqueios, como sempre) e grava o resultado.
Não abre nenhuma porta no seu computador: só conversa com o banco.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import time

from .adapters.base import StoreError
from .adapters.http_policy import HttpPolicy
from .adapters.registry import build_adapters
from .config import get_settings
from .logging_setup import setup_logging
from .migrations import run_migrations
from .schemas import SearchQuery
from .services import remote

log = logging.getLogger("coletor")

HEARTBEAT_EVERY = 15.0
IDLE_SLEEP = 1.5


async def handle_job(job: dict, adapters: dict) -> None:
    adapter = adapters.get(job["store"])
    if adapter is None:
        await asyncio.to_thread(remote.finish, job["id"], error=f"loja {job['store']} não está ativa neste coletor")
        return
    query = SearchQuery(**job["request"])
    started = time.perf_counter()
    try:
        offers = await asyncio.wait_for(adapter.search(query), timeout=adapter.timeout_seconds or 30)
    except asyncio.TimeoutError:
        await asyncio.to_thread(remote.finish, job["id"], error=f"{adapter.name} demorou demais para responder")
        log.warning("%s: tempo esgotado em '%s'", adapter.name, query.raw)
        return
    except StoreError as exc:
        await asyncio.to_thread(remote.finish, job["id"], error=str(exc))
        log.warning("%s falhou (%s): %s", adapter.name, exc.status, exc.detail)
        return
    except Exception as exc:  # noqa: BLE001 - o coletor nunca pode cair por causa de uma loja
        log.exception("%s: erro inesperado", adapter.name)
        await asyncio.to_thread(remote.finish, job["id"], error=f"Erro inesperado no coletor: {type(exc).__name__}")
        return
    payload = [o.model_dump(mode="json") for o in offers]
    await asyncio.to_thread(remote.finish, job["id"], result=payload)
    log.info("%s: '%s' -> %d ofertas (%.1fs)", adapter.name, query.raw, len(offers), time.perf_counter() - started)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    stores = settings.collector_list
    run_migrations()

    http = HttpPolicy(settings)
    adapters = {k: v for k, v in build_adapters(settings, remote=False, http=http).items() if k in stores}
    if not adapters:
        raise SystemExit(f"Nenhuma loja válida em COLLECTOR_STORES={settings.collector_stores!r}")
    log.info("Coletor '%s' ligado. Lojas: %s", settings.collector_name, ", ".join(a.name for a in adapters.values()))

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, RuntimeError):  # Windows
            pass

    last_beat = 0.0
    last_purge = 0.0
    try:
        while not stop.is_set():
            now = time.monotonic()
            if now - last_beat >= HEARTBEAT_EVERY:
                try:
                    await asyncio.to_thread(remote.heartbeat, settings.collector_name, list(adapters))
                    last_beat = now
                except Exception:  # noqa: BLE001 - banco fora do ar: tenta de novo
                    log.exception("não consegui falar com o banco; tentando de novo")
            if now - last_purge >= 3600:
                await asyncio.to_thread(remote.purge_old)
                last_purge = now
            try:
                job = await asyncio.to_thread(remote.claim_next, list(adapters))
            except Exception:  # noqa: BLE001
                log.exception("erro ao ler a fila")
                job = None
            if job:
                await handle_job(job, adapters)
            else:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=IDLE_SLEEP)
                except asyncio.TimeoutError:
                    pass
    except KeyboardInterrupt:
        pass
    finally:
        await http.aclose()
        log.info("Coletor desligado.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
