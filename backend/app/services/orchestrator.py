"""Roda a busca em todas as lojas em paralelo e devolve eventos conforme cada uma responde.

Eventos (dicts) emitidos, nesta ordem:
  {"type": "query", ...}                      -> como a busca foi entendida
  {"type": "store_status", "status": "loading"} (um por loja)
  {"type": "store_result", ...}               -> um por loja, na ordem em que terminam
  {"type": "done", ...}
Uma loja que falha vira um store_result com status "unavailable"/"blocked"/"not_configured";
as outras continuam normalmente.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator

from pydantic import BaseModel

from ..adapters.base import StoreAdapter, StoreError
from ..adapters.utils import detect_condition
from ..config import Settings
from ..db import session_scope
from ..models import Search
from ..parsing.matcher import match
from ..parsing.specs import Specs, extract_specs
from ..schemas import Offer, SearchQuery, build_store_terms
from . import cache, history

log = logging.getLogger("orchestrator")


class SearchFilters(BaseModel):
    stores: list[str] | None = None
    min_price: float | None = None
    max_price: float | None = None
    official_only: bool = False
    include_used: bool = False
    use_cache: bool = True


def parse_query(raw: str) -> tuple[Specs, SearchQuery]:
    specs = extract_specs(raw, is_query=True)
    return specs, SearchQuery(raw=raw, specs=specs.to_dict(), store_terms=build_store_terms(raw, specs))


def evaluate_offers(specs: Specs, offers: list[Offer]) -> tuple[list[Offer], list[dict]]:
    """Aplica o matcher. Retorna (aceitas, amostra de excluídas com motivo)."""
    accepted: list[Offer] = []
    excluded: list[dict] = []
    for offer in offers:
        extra = offer.specs.get("_extra_text", "")
        offer_specs = extract_specs(f"{offer.title} {extra}".strip())
        result = match(specs, offer.title, offer_specs)
        offer.specs = {**offer_specs.to_dict(), **({"_extra_text": extra} if extra else {})}
        if offer.condition == "novo":
            offer.condition = detect_condition(offer.title)
        if result.accepted:
            offer.match_score = result.score
            offer.match_level = result.level
            offer.match_reasons = result.reasons
            if offer.condition != "novo":
                offer.match_reasons = [f"Produto {offer.condition}", *offer.match_reasons]
            accepted.append(offer)
        else:
            excluded.append({"title": offer.title, "reason": result.rejected_because})
    return accepted, excluded


def apply_filters(offers: list[Offer], f: SearchFilters) -> list[Offer]:
    out = []
    for o in offers:
        price = o.best_price
        if f.min_price is not None and (price is None or price < f.min_price):
            continue
        if f.max_price is not None and (price is None or price > f.max_price):
            continue
        if f.official_only and o.is_official is False:
            continue
        if not f.include_used and o.condition != "novo":
            continue
        out.append(o)
    return out


def attach_history(offers: list[Offer]) -> None:
    """Adiciona resumo do histórico e um veredito sobre o desconto."""
    ids = [o.listing_id for o in offers if o.listing_id]
    summary = history.history_summary(ids)
    for o in offers:
        h = summary.get(o.listing_id or -1)
        if not h:
            continue
        verdict = None
        price = o.best_price
        if h["count"] >= 3 and price:
            if price <= h["median"] * 0.95:
                verdict = "real"  # abaixo da mediana dos últimos 30 dias
            elif o.discount_pct and price >= h["median"]:
                verdict = "suspeito"  # "desconto" mas preço igual/maior que o normal
        o.history = {**h, "verdict": verdict}


def _offer_payload(o: Offer) -> dict:
    return o.model_dump(mode="json")


class SearchOrchestrator:
    def __init__(self, settings: Settings, adapters: dict[str, StoreAdapter]):
        self.settings = settings
        self.adapters = adapters

    async def _fetch_store(self, adapter: StoreAdapter, query: SearchQuery, specs: Specs, f: SearchFilters) -> dict:
        started = time.perf_counter()
        base = {"type": "store_result", "store": adapter.slug, "name": adapter.name}

        if not adapter.is_configured():
            return {**base, "status": "not_configured", "message": adapter.not_configured_message(), "offers": []}

        cached_at = None
        try:
            hit = await asyncio.to_thread(cache.get_cached, adapter.slug, query.raw) if f.use_cache else None
            if hit:
                payload, cached_at = hit
                raw_offers = [Offer(**o) for o in payload]
            else:
                timeout = adapter.timeout_seconds or self.settings.store_timeout_seconds
                raw_offers = await asyncio.wait_for(adapter.search(query), timeout=timeout)

            accepted, excluded = evaluate_offers(specs, raw_offers)
            if not hit:
                await asyncio.to_thread(history.save_offers, accepted)
                await asyncio.to_thread(
                    cache.set_cached, adapter.slug, query.raw,
                    [_offer_payload(o) for o in raw_offers], self.settings.cache_ttl_minutes,
                )
            filtered = apply_filters(accepted, f)
            await asyncio.to_thread(attach_history, filtered)
            filtered.sort(key=lambda o: (o.best_price is None, o.best_price or 0))
            elapsed = int((time.perf_counter() - started) * 1000)
            log.info(
                "%s: %d encontrados, %d compatíveis, %d após filtros (%d ms%s)",
                adapter.name, len(raw_offers), len(accepted), len(filtered), elapsed, ", cache" if hit else "",
            )
            return {
                **base, "status": "ok", "cached": bool(hit),
                "cached_at": cached_at.isoformat() if cached_at else None,
                "elapsed_ms": elapsed, "total_found": len(raw_offers), "excluded_count": len(excluded),
                "excluded_samples": excluded[:8], "offers": [_offer_payload(o) for o in filtered],
            }
        except asyncio.TimeoutError:
            log.warning("%s: tempo esgotado", adapter.name)
            return {**base, "status": "unavailable", "message": f"{adapter.name} demorou demais para responder", "offers": []}
        except StoreError as exc:
            log.warning("%s falhou (%s): %s", adapter.name, exc.status, exc.detail)
            # "detail" ajuda a diagnosticar (ex.: corpo do 403); nunca contém chaves.
            return {**base, "status": exc.status, "message": str(exc), "detail": exc.detail[:300], "offers": []}
        except Exception as exc:  # noqa: BLE001 - uma loja nunca derruba a busca
            log.exception("%s: erro inesperado", adapter.name)
            return {**base, "status": "unavailable", "message": f"Erro inesperado: {type(exc).__name__}", "offers": []}

    async def stream(self, raw: str, f: SearchFilters) -> AsyncIterator[dict]:
        specs, query = parse_query(raw)
        await asyncio.to_thread(_record_search, raw, specs)
        selected = [a for slug, a in self.adapters.items() if not f.stores or slug in f.stores]
        yield {"type": "query", "raw": raw, "specs": specs.to_dict(), "terms": query.store_terms}
        for a in selected:
            yield {"type": "store_status", "store": a.slug, "name": a.name, "status": "loading"}

        started = time.perf_counter()
        tasks = [asyncio.create_task(self._fetch_store(a, query, specs, f)) for a in selected]
        try:
            for fut in asyncio.as_completed(tasks):
                yield await fut
        finally:
            for t in tasks:
                t.cancel()
        yield {"type": "done", "elapsed_ms": int((time.perf_counter() - started) * 1000)}


def _record_search(raw: str, specs: Specs) -> None:
    try:
        with session_scope() as s:
            s.add(Search(raw_query=raw[:300], parsed_specs=specs.to_dict()))
    except Exception:  # noqa: BLE001 - estatística não pode quebrar a busca
        log.exception("não foi possível registrar a busca")
