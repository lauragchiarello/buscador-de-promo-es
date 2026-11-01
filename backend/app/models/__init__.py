"""Modelos do banco de dados."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Search(Base):
    """Cada busca feita (útil para estatística e debug do parser)."""

    __tablename__ = "searches"
    id: Mapped[int] = mapped_column(primary_key=True)
    raw_query: Mapped[str] = mapped_column(String(300))
    parsed_specs: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchCache(Base):
    """Resultado de uma loja para uma busca, guardado por alguns minutos."""

    __tablename__ = "search_cache"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    store: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Listing(Base):
    """Um anúncio em uma loja. O mesmo anúncio aparece em várias coletas."""

    __tablename__ = "listings"
    __table_args__ = (UniqueConstraint("store", "external_id", name="uq_listing_store_ext"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    seller: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seller_reputation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_official: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    specs: Mapped[dict] = mapped_column(JSON, default=dict)
    product_key: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    snapshots: Mapped[list[PriceSnapshot]] = relationship(back_populates="listing", cascade="all, delete-orphan")


class PriceSnapshot(Base):
    """Preço de um anúncio em um momento (base do histórico de preços)."""

    __tablename__ = "price_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    price_cash: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_installment: Mapped[float | None] = mapped_column(Float, nullable=True)
    installments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_list: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    shipping: Mapped[float | None] = mapped_column(Float, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    listing: Mapped[Listing] = relationship(back_populates="snapshots")


class WatchItem(Base):
    """Produto monitorado (fase 3)."""

    __tablename__ = "watchlist"
    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str | None] = mapped_column(String(300), nullable=True)
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id"), nullable=True)
    target_price: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    """Alerta disparado quando um monitorado fica abaixo do preço-alvo (fase 3)."""

    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    watch_id: Mapped[int] = mapped_column(ForeignKey("watchlist.id", ondelete="CASCADE"), index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("price_snapshots.id", ondelete="CASCADE"))
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    seen: Mapped[bool] = mapped_column(Boolean, default=False)


class CatalogPage(Base):
    """Uma página de categoria de uma loja "de catálogo" (Terabyte...) e quando foi lida."""

    __tablename__ = "catalog_pages"
    __table_args__ = (UniqueConstraint("store", "path", name="uq_catalog_page"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store: Mapped[str] = mapped_column(String(40), index=True)
    path: Mapped[str] = mapped_column(String(300))
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    item_count: Mapped[int] = mapped_column(Integer, default=0)


class CatalogItem(Base):
    """Oferta guardada do catálogo de uma loja (a busca é feita localmente sobre isto)."""

    __tablename__ = "catalog_items"
    __table_args__ = (UniqueConstraint("store", "path", "external_id", name="uq_catalog_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store: Mapped[str] = mapped_column(String(40), index=True)
    path: Mapped[str] = mapped_column(String(300), index=True)
    external_id: Mapped[str] = mapped_column(String(120))
    payload: Mapped[dict] = mapped_column(JSON)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
