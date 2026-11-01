"""Rotas HTTP da aplicação."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..services import cache
from ..services.history import listing_history
from ..services.orchestrator import SearchFilters, parse_query

router = APIRouter(prefix="/api")


def _filters(
    stores: str | None, min_price: float | None, max_price: float | None,
    official_only: bool, include_used: bool, fresh: bool,
) -> SearchFilters:
    return SearchFilters(
        stores=[s for s in (stores or "").split(",") if s] or None,
        min_price=min_price, max_price=max_price,
        official_only=official_only, include_used=include_used, use_cache=not fresh,
    )


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.get("/stores")
def stores(request: Request) -> list[dict]:
    """Lojas disponíveis e se estão configuradas."""
    return [
        {
            "slug": a.slug, "name": a.name, "homepage": a.homepage, "strategy": a.strategy,
            "configured": a.is_configured(),
            "message": None if a.is_configured() else a.not_configured_message(),
        }
        for a in request.app.state.adapters.values()
    ]


@router.get("/parse")
def parse(q: str = Query(..., min_length=2, max_length=300)) -> dict:
    """Mostra como o texto foi entendido (útil para depurar o parser)."""
    specs, query = parse_query(q)
    return {"specs": specs.to_dict(), "terms": query.store_terms}


@router.get("/search/stream")
async def search_stream(
    request: Request,
    q: str = Query(..., min_length=2, max_length=300),
    stores: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    official_only: bool = False,
    include_used: bool = False,
    fresh: bool = False,
):
    """Busca com Server-Sent Events: cada loja chega assim que responde."""
    f = _filters(stores, min_price, max_price, official_only, include_used, fresh)
    orchestrator = request.app.state.orchestrator

    async def events():
        async for ev in orchestrator.stream(q, f):
            if await request.is_disconnected():
                break
            yield f"event: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/search")
async def search(
    request: Request,
    q: str = Query(..., min_length=2, max_length=300),
    stores: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    official_only: bool = False,
    include_used: bool = False,
    fresh: bool = False,
) -> dict:
    """Mesma busca, mas devolve tudo de uma vez (bom para testes e scripts)."""
    f = _filters(stores, min_price, max_price, official_only, include_used, fresh)
    result: dict = {"stores": [], "offers": []}
    async for ev in request.app.state.orchestrator.stream(q, f):
        if ev["type"] == "query":
            result["query"] = ev
        elif ev["type"] == "store_result":
            result["stores"].append({k: v for k, v in ev.items() if k != "offers"})
            result["offers"].extend(ev["offers"])
    result["offers"].sort(key=lambda o: o.get("price_cash") or o.get("price_installment") or 1e12)
    return result


@router.get("/history/{listing_id}")
def history(listing_id: int, days: int = 180) -> dict:
    data = listing_history(listing_id, days)
    if data is None:
        raise HTTPException(404, "Anúncio não encontrado")
    return data


@router.delete("/cache")
def clear_cache() -> dict:
    cache.clear_all()
    return {"ok": True}
