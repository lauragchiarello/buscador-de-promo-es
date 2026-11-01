"""Uma loja com problema nunca pode derrubar a busca inteira."""

import asyncio

from app.adapters.base import StoreAdapter, StoreBlocked
from app.config import Settings
from app.schemas import Offer
from app.services import cache
from app.services.orchestrator import SearchFilters, SearchOrchestrator


def _offer(store, ext, title, price, **kw):
    return Offer(store=store, store_name=store, external_id=ext, title=title, url=f"https://x/{ext}", price_cash=price, **kw)


class GoodStore(StoreAdapter):
    slug, name = "boa", "Loja Boa"
    calls = 0

    async def search(self, query):
        type(self).calls += 1
        return [
            _offer("boa", "1", "Notebook Dell i7-13620H 32GB SSD 1TB", 5000),
            _offer("boa", "2", "Notebook Dell i7-13620H 16GB SSD 1TB", 3000),  # RAM errada
            _offer("boa", "3", "Notebook Asus i7 13ª geração 32GB 512GB", 4500, is_official=True),
            _offer("boa", "4", "Capa para notebook 15.6", 50),  # acessório
            _offer("boa", "5", "Usado - Notebook Lenovo i7-1355U 32GB", 2500),
        ]


class BlockedStore(StoreAdapter):
    slug, name = "bloqueada", "Loja Bloqueada"

    async def search(self, query):
        raise StoreBlocked("A loja pediu verificação (captcha/login)")


class CrashingStore(StoreAdapter):
    slug, name = "quebrada", "Loja Quebrada"

    async def search(self, query):
        raise ValueError("bug no parser da loja")


class SlowStore(StoreAdapter):
    slug, name = "lenta", "Loja Lenta"
    timeout_seconds = 0.2

    async def search(self, query):
        await asyncio.sleep(5)
        return []


class NeedsKeyStore(StoreAdapter):
    slug, name = "semchave", "Loja Sem Chave"

    def is_configured(self):
        return False

    async def search(self, query):  # pragma: no cover
        raise AssertionError("não deveria ser chamada")


async def _collect(orch, q, f):
    return [ev async for ev in orch.stream(q, f)]


async def test_failures_are_isolated_and_results_filtered():
    cache.clear_all()
    settings = Settings()
    adapters = {c.slug: c(settings) for c in (GoodStore, BlockedStore, CrashingStore, SlowStore, NeedsKeyStore)}
    events = await _collect(SearchOrchestrator(settings, adapters), "notebook 32gb ram i7 13th", SearchFilters())

    assert events[0]["type"] == "query"
    assert events[0]["specs"]["ram_gb"] == 32
    assert events[-1]["type"] == "done"
    results = {e["store"]: e for e in events if e["type"] == "store_result"}
    assert set(results) == set(adapters)

    assert results["bloqueada"]["status"] == "blocked"
    assert results["quebrada"]["status"] == "unavailable"
    assert results["lenta"]["status"] == "unavailable"
    assert results["semchave"]["status"] == "not_configured"

    good = results["boa"]
    assert good["status"] == "ok"
    titles = [o["title"] for o in good["offers"]]
    # só os 2 compatíveis e novos, do mais barato para o mais caro
    assert titles == ["Notebook Asus i7 13ª geração 32GB 512GB", "Notebook Dell i7-13620H 32GB SSD 1TB"]
    assert good["excluded_count"] == 2
    assert all(o["listing_id"] for o in good["offers"])  # salvo no histórico


async def test_cache_avoids_hitting_store_again():
    cache.clear_all()
    settings = Settings()
    GoodStore.calls = 0
    orch = SearchOrchestrator(settings, {"boa": GoodStore(settings)})
    await _collect(orch, "notebook 32gb ram i7 13th", SearchFilters())
    events = await _collect(orch, "Notebook 32GB RAM i7 13th", SearchFilters())
    result = next(e for e in events if e["type"] == "store_result")
    assert GoodStore.calls == 1
    assert result["cached"] is True
    assert len(result["offers"]) == 2


async def test_filters_price_official_and_used():
    cache.clear_all()
    settings = Settings()
    orch = SearchOrchestrator(settings, {"boa": GoodStore(settings)})
    ev = await _collect(orch, "notebook 32gb ram i7 13th", SearchFilters(max_price=4800))
    offers = next(e for e in ev if e["type"] == "store_result")["offers"]
    assert [o["external_id"] for o in offers] == ["3"]

    ev = await _collect(orch, "notebook 32gb ram i7 13th", SearchFilters(include_used=True))
    offers = next(e for e in ev if e["type"] == "store_result")["offers"]
    assert offers[0]["external_id"] == "5" and offers[0]["condition"] == "usado"
