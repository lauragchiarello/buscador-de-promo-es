"""Fila entre o site na nuvem e o coletor de casa.

O site (Render) grava um pedido em `remote_jobs`; o coletor (seu computador) pega
o pedido, busca na loja pela internet de casa e grava o resultado. Os dois lados
só conversam pelo banco (Supabase), então o computador não abre nenhuma porta.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from ..db import session_scope
from ..models import CollectorHeartbeat, RemoteJob
from ..parsing.normalize import normalize

HEARTBEAT_ONLINE_SECONDS = 60
STALE_WORKING_SECONDS = 120  # pedido "pegando" há muito tempo volta para a fila


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def query_key(store: str, raw: str) -> str:
    return hashlib.sha256(f"{store}|{normalize(raw)}".encode()).hexdigest()


# ---- lado do site -----------------------------------------------------------


def collector_online(store: str) -> bool:
    """Algum coletor que atende esta loja deu sinal de vida no último minuto?"""
    limit = _now() - timedelta(seconds=HEARTBEAT_ONLINE_SECONDS)
    with session_scope() as s:
        for hb in s.execute(select(CollectorHeartbeat)).scalars():
            if _aware(hb.last_seen) >= limit and store in (hb.stores or []):
                return True
    return False


def enqueue(store: str, raw: str, request: dict) -> int:
    """Cria um pedido (ou reaproveita um igual que ainda está na fila)."""
    key = query_key(store, raw)
    with session_scope() as s:
        existing = s.execute(
            select(RemoteJob).where(
                RemoteJob.store == store, RemoteJob.query_key == key, RemoteJob.status.in_(("pending", "working"))
            )
        ).scalars().first()
        if existing:
            return existing.id
        job = RemoteJob(store=store, query_key=key, raw_query=raw[:300], request=request, status="pending")
        s.add(job)
        s.flush()
        return job.id


def get_job(job_id: int) -> dict | None:
    with session_scope() as s:
        job = s.get(RemoteJob, job_id)
        if job is None:
            return None
        return {"status": job.status, "result": job.result, "error": job.error}


# ---- lado do coletor --------------------------------------------------------


def heartbeat(name: str, stores: list[str]) -> None:
    with session_scope() as s:
        hb = s.get(CollectorHeartbeat, name)
        if hb is None:
            hb = CollectorHeartbeat(name=name)
            s.add(hb)
        hb.stores = stores
        hb.last_seen = _now()


def claim_next(stores: list[str]) -> dict | None:
    """Pega o pedido mais antigo destas lojas. Seguro com vários coletores (UPDATE condicional)."""
    stale = _now() - timedelta(seconds=STALE_WORKING_SECONDS)
    with session_scope() as s:
        # Pedidos abandonados (coletor caiu no meio) voltam para a fila.
        s.execute(
            update(RemoteJob)
            .where(RemoteJob.status == "working", RemoteJob.claimed_at < stale)
            .values(status="pending", claimed_at=None)
        )
        candidates = s.execute(
            select(RemoteJob.id).where(RemoteJob.status == "pending", RemoteJob.store.in_(stores))
            .order_by(RemoteJob.created_at).limit(5)
        ).scalars().all()
        for job_id in candidates:
            took = s.execute(
                update(RemoteJob).where(RemoteJob.id == job_id, RemoteJob.status == "pending")
                .values(status="working", claimed_at=_now())
            ).rowcount
            if took:
                job = s.get(RemoteJob, job_id)
                return {"id": job.id, "store": job.store, "request": job.request}
    return None


def finish(job_id: int, *, result: list[dict] | None = None, error: str | None = None) -> None:
    with session_scope() as s:
        job = s.get(RemoteJob, job_id)
        if job is None:
            return
        job.status = "error" if error else "done"
        job.result = result
        job.error = error[:500] if error else None
        job.finished_at = _now()


def purge_old(days: int = 2) -> int:
    """Apaga pedidos antigos (o resultado útil já foi para o cache e o histórico)."""
    from sqlalchemy import delete

    with session_scope() as s:
        res = s.execute(delete(RemoteJob).where(RemoteJob.created_at < _now() - timedelta(days=days)))
        return res.rowcount or 0
