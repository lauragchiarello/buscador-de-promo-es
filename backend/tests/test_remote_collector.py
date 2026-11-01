"""Site na nuvem + coletor de casa conversando pela fila do banco."""

import asyncio

import pytest

from app.adapters.base import StoreAdapter, StoreBlocked, StoreError
from app.adapters.registry import build_adapters
from app.adapters.remote import CollectorOffline, RemoteStoreAdapter
from app.collector import handle_job
from app.config import Settings
from app.db import session_scope
from app.models import CollectorHeartbeat, RemoteJob
from app.schemas import Offer, SearchQuery
from app.services import remote

QUERY = SearchQuery(raw="notebook 32gb ram i7 13th", specs={"category": "notebook"}, store_terms=["notebook i7 32gb"])


class FakeKabum(StoreAdapter):
    slug, name = "kabum", "KaBuM!"
    fail: Exception | None = None

    async def search(self, query):
        if self.fail:
            raise self.fail
        return [Offer(store="kabum", store_name="KaBuM!", external_id="1", title="Notebook i7-13620H 32GB", url="https://k/1", price_cash=4999.0)]


@pytest.fixture(autouse=True)
def clean_tables():
    with session_scope() as s:
        s.query(RemoteJob).delete()
        s.query(CollectorHeartbeat).delete()
    FakeKabum.fail = None
    yield


def _remote(wait=5.0):
    return RemoteStoreAdapter(FakeKabum(Settings()), wait_seconds=wait)


async def _fake_collector(adapters, rounds=50):
    """Simula o coletor: dá sinal de vida e atende os pedidos."""
    for _ in range(rounds):
        job = remote.claim_next(["kabum"])
        if job:
            await handle_job(job, adapters)
            return
        await asyncio.sleep(0.1)


async def test_collector_offline_is_reported():
    with pytest.raises(CollectorOffline) as exc:
        await _remote().search(QUERY)
    assert "desligado" in str(exc.value)


async def test_site_gets_result_from_collector():
    remote.heartbeat("pc-teste", ["kabum"])
    collector = asyncio.create_task(_fake_collector({"kabum": FakeKabum(Settings())}))
    offers = await _remote().search(QUERY)
    await collector
    assert [o.external_id for o in offers] == ["1"] and offers[0].price_cash == 4999.0


async def test_store_block_on_collector_side_is_reported():
    remote.heartbeat("pc-teste", ["kabum"])
    FakeKabum.fail = StoreBlocked("A loja bloqueou o acesso no momento")
    collector = asyncio.create_task(_fake_collector({"kabum": FakeKabum(Settings())}))
    with pytest.raises(StoreError) as exc:
        await _remote().search(QUERY)
    await collector
    assert "bloqueou" in str(exc.value)


async def test_timeout_when_collector_never_answers():
    remote.heartbeat("pc-teste", ["kabum"])  # "ligado", mas não atende
    with pytest.raises(StoreError) as exc:
        await _remote(wait=1.5).search(QUERY)
    assert "não respondeu a tempo" in str(exc.value)


def test_same_query_reuses_pending_job_and_claim_is_exclusive():
    a = remote.enqueue("kabum", "Notebook i7", {"raw": "x", "specs": {}, "store_terms": []})
    b = remote.enqueue("kabum", "notebook  i7", {"raw": "x", "specs": {}, "store_terms": []})
    assert a == b
    first = remote.claim_next(["kabum"])
    second = remote.claim_next(["kabum"])
    assert first["id"] == a and second is None  # um pedido vai para um coletor só


def test_heartbeat_only_counts_for_its_stores():
    remote.heartbeat("pc", ["kabum"])
    assert remote.collector_online("kabum")
    assert not remote.collector_online("terabyte")


def test_registry_wraps_remote_stores_only_on_site():
    settings = Settings(remote_stores="kabum")
    site = build_adapters(settings)
    collector = build_adapters(settings, remote=False)
    assert isinstance(site["kabum"], RemoteStoreAdapter) and site["kabum"].via_collector
    assert not isinstance(collector["kabum"], RemoteStoreAdapter)
    assert not isinstance(site["fastshop"], RemoteStoreAdapter)
