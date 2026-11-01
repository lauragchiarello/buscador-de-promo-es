"""Adaptador "via coletor de casa".

Envolve uma loja que bloqueia acesso da nuvem (ex.: KaBuM!). No site, em vez de
acessar a loja, grava um pedido na fila e espera o coletor de casa responder.
Ative com REMOTE_STORES=kabum no ambiente do site (Render).
"""

from __future__ import annotations

import asyncio
import time

from ..schemas import Offer, SearchQuery
from ..services import remote
from .base import StoreAdapter, StoreError


class CollectorOffline(StoreError):
    status = "unavailable"


class RemoteStoreAdapter(StoreAdapter):
    via_collector = True

    def __init__(self, inner: StoreAdapter, wait_seconds: float):
        super().__init__(inner.settings, inner.http)
        self.inner = inner
        self.slug = inner.slug
        self.name = inner.name
        self.homepage = inner.homepage
        self.strategy = f"{inner.strategy} — via coletor no computador de casa"
        self.wait_seconds = wait_seconds
        self.timeout_seconds = wait_seconds + 5

    def is_configured(self) -> bool:
        return self.inner.is_configured()

    def not_configured_message(self) -> str:
        return self.inner.not_configured_message()

    async def search(self, query: SearchQuery) -> list[Offer]:
        if not await asyncio.to_thread(remote.collector_online, self.slug):
            raise CollectorOffline(
                "O coletor de casa está desligado",
                detail="nenhum coletor deu sinal de vida no último minuto",
            )
        job_id = await asyncio.to_thread(remote.enqueue, self.slug, query.raw, query.model_dump(mode="json"))
        deadline = time.monotonic() + self.wait_seconds
        while time.monotonic() < deadline:
            await asyncio.sleep(1.0)
            job = await asyncio.to_thread(remote.get_job, job_id)
            if job is None:
                break
            if job["status"] == "done":
                return [Offer(**o) for o in job["result"] or []]
            if job["status"] == "error":
                raise StoreError(job["error"] or "O coletor de casa não conseguiu buscar", detail=f"coletor: {job['error']}")
        raise StoreError(
            "O coletor de casa não respondeu a tempo",
            detail=f"pedido {job_id} sem resposta em {self.wait_seconds:.0f}s",
        )
