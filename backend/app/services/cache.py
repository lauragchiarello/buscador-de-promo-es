"""Cache de resultados por loja + busca (padrão: 30 minutos)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from ..db import session_scope
from ..models import SearchCache
from ..parsing.normalize import normalize


def cache_key(store: str, raw_query: str) -> str:
    return hashlib.sha256(f"{store}|{normalize(raw_query)}".encode()).hexdigest()


def _aware(dt: datetime) -> datetime:
    # SQLite devolve datetime sem fuso; tratamos como UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_cached(store: str, raw_query: str) -> tuple[list[dict], datetime] | None:
    now = datetime.now(timezone.utc)
    with session_scope() as s:
        row = s.get(SearchCache, cache_key(store, raw_query))
        if row and _aware(row.expires_at) > now:
            return row.payload, _aware(row.created_at)
    return None


def set_cached(store: str, raw_query: str, payload: list[dict], ttl_minutes: int) -> None:
    now = datetime.now(timezone.utc)
    key = cache_key(store, raw_query)
    with session_scope() as s:
        row = s.get(SearchCache, key)
        if row is None:
            row = SearchCache(key=key, store=store)
            s.add(row)
        row.payload = payload
        row.created_at = now
        row.expires_at = now + timedelta(minutes=ttl_minutes)


def purge_expired() -> int:
    with session_scope() as s:
        res = s.execute(delete(SearchCache).where(SearchCache.expires_at < datetime.now(timezone.utc)))
        return res.rowcount or 0


def clear_all() -> None:
    with session_scope() as s:
        s.execute(delete(SearchCache))

