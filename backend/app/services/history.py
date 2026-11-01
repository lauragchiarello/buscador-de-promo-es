"""Grava cada coleta no banco e calcula o resumo do histórico de preços."""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from ..db import session_scope
from ..models import Listing, PriceSnapshot
from ..schemas import Offer


def product_key(specs: dict, title: str) -> str | None:
    """Impressão digital do produto, para agrupar o mesmo modelo entre anúncios."""
    parts = [
        specs.get("brand"), specs.get("cpu_line"), specs.get("cpu_model") or specs.get("cpu_generation"),
        specs.get("ram_gb"), specs.get("storage_gb"), specs.get("gpu"),
    ]
    filled = [str(p) for p in parts if p]
    return "|".join(filled) if len(filled) >= 3 else None


def save_offers(offers: list[Offer]) -> None:
    """Upsert dos anúncios + um snapshot de preço por oferta. Preenche offer.listing_id."""
    if not offers:
        return
    now = datetime.now(timezone.utc)
    with session_scope() as s:
        for offer in offers:
            listing = s.execute(
                select(Listing).where(Listing.store == offer.store, Listing.external_id == offer.external_id)
            ).scalar_one_or_none()
            specs = {k: v for k, v in offer.specs.items() if not k.startswith("_")}
            if listing is None:
                listing = Listing(store=offer.store, external_id=offer.external_id, first_seen=now)
                s.add(listing)
            listing.url = offer.url
            listing.title = offer.title
            listing.image_url = offer.image_url
            listing.seller = offer.seller
            listing.seller_reputation = offer.seller_reputation
            listing.is_official = offer.is_official
            listing.specs = specs
            listing.product_key = product_key(specs, offer.title)
            listing.last_seen = now
            s.flush()
            offer.listing_id = listing.id
            # Lojas de catálogo devolvem a mesma coleta várias vezes: não duplicar o snapshot.
            already = s.execute(
                select(PriceSnapshot.id).where(
                    PriceSnapshot.listing_id == listing.id, PriceSnapshot.collected_at == offer.collected_at
                )
            ).first()
            if already:
                continue
            s.add(
                PriceSnapshot(
                    listing_id=listing.id,
                    price_cash=offer.price_cash,
                    price_installment=offer.price_installment,
                    installments=offer.installments,
                    price_list=offer.price_list,
                    discount_pct=offer.discount_pct,
                    shipping=offer.shipping,
                    collected_at=offer.collected_at,
                )
            )
            offer.listing_id = listing.id


def history_summary(listing_ids: list[int], days: int = 30) -> dict[int, dict]:
    """{listing_id: {"min": .., "median": .., "count": ..}} dos últimos N dias."""
    if not listing_ids:
        return {}
    since = datetime.now(timezone.utc) - timedelta(days=days)
    out: dict[int, list[float]] = {}
    with session_scope() as s:
        rows = s.execute(
            select(PriceSnapshot.listing_id, PriceSnapshot.price_cash)
            .where(PriceSnapshot.listing_id.in_(listing_ids), PriceSnapshot.collected_at >= since)
        ).all()
    for lid, price in rows:
        if price:
            out.setdefault(lid, []).append(price)
    return {
        lid: {"min": min(p), "median": statistics.median(p), "count": len(p)}
        for lid, p in out.items()
    }


def listing_history(listing_id: int, days: int = 180) -> dict | None:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with session_scope() as s:
        listing = s.get(Listing, listing_id)
        if listing is None:
            return None
        snaps = s.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.listing_id == listing_id, PriceSnapshot.collected_at >= since)
            .order_by(PriceSnapshot.collected_at)
        ).scalars().all()
        return {
            "listing": {
                "id": listing.id, "store": listing.store, "title": listing.title, "url": listing.url,
                "image_url": listing.image_url,
            },
            "points": [
                {
                    "at": sn.collected_at.isoformat(), "price_cash": sn.price_cash,
                    "price_installment": sn.price_installment, "price_list": sn.price_list,
                }
                for sn in snaps
            ],
        }
