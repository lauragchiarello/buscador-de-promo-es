"""Catálogo local de lojas que não permitem busca direta (robots.txt proíbe a página de busca).

Cada loja lê periodicamente algumas páginas de categoria (liberadas no robots.txt)
e guarda as ofertas aqui. A busca do usuário é feita sobre esse catálogo.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select

from ..db import session_scope
from ..models import CatalogItem, CatalogPage
from ..schemas import Offer


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def page_age_hours(store: str, path: str) -> float | None:
    """Há quantas horas a página foi lida (None = nunca)."""
    with session_scope() as s:
        page = s.execute(select(CatalogPage).where(CatalogPage.store == store, CatalogPage.path == path)).scalar_one_or_none()
        if page is None:
            return None
        return (datetime.now(timezone.utc) - _aware(page.refreshed_at)).total_seconds() / 3600


def save_page(store: str, path: str, offers: list[Offer]) -> None:
    """Substitui os itens da página pelos recém-lidos."""
    now = datetime.now(timezone.utc)
    with session_scope() as s:
        s.execute(delete(CatalogItem).where(CatalogItem.store == store, CatalogItem.path == path))
        seen: set[str] = set()
        for o in offers:
            if o.external_id in seen:
                continue
            seen.add(o.external_id)
            o.collected_at = now
            s.add(CatalogItem(store=store, path=path, external_id=o.external_id, payload=o.model_dump(mode="json"), refreshed_at=now))
        page = s.execute(select(CatalogPage).where(CatalogPage.store == store, CatalogPage.path == path)).scalar_one_or_none()
        if page is None:
            page = CatalogPage(store=store, path=path)
            s.add(page)
        page.refreshed_at = now
        page.item_count = len(seen)


def load_items(store: str, paths: list[str]) -> list[Offer]:
    """Ofertas guardadas dessas páginas (sem repetir o mesmo produto)."""
    with session_scope() as s:
        rows = s.execute(select(CatalogItem).where(CatalogItem.store == store, CatalogItem.path.in_(paths))).scalars().all()
        out: dict[str, Offer] = {}
        for r in rows:
            out.setdefault(r.external_id, Offer(**r.payload))
        return list(out.values())
