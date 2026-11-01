"""Objetos trocados entre adaptadores, serviços e API."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .parsing.specs import Specs


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class SearchQuery(BaseModel):
    """A busca já interpretada, entregue a cada adaptador."""

    raw: str
    specs: dict
    # Termos para mandar à loja, do mais específico ao mais amplo.
    store_terms: list[str]

    model_config = {"arbitrary_types_allowed": True}


class Offer(BaseModel):
    """Uma oferta encontrada em uma loja."""

    store: str
    store_name: str
    external_id: str
    title: str
    url: str
    image_url: str | None = None

    price_cash: float | None = Field(None, description="Preço à vista / Pix")
    price_installment: float | None = Field(None, description="Preço total parcelado")
    installments: int | None = None
    installment_value: float | None = None
    price_list: float | None = Field(None, description='Preço "de" (antes do desconto)')
    discount_pct: float | None = None

    shipping: float | None = Field(None, description="Valor do frete; 0 = grátis; None = desconhecido")
    seller: str | None = None
    seller_reputation: str | None = None
    is_official: bool | None = None
    condition: str = "novo"  # novo | usado | recondicionado
    rating: float | None = None
    rating_count: int | None = None

    specs: dict = Field(default_factory=dict)
    match_score: int = 0
    match_level: str = ""
    match_reasons: list[str] = Field(default_factory=list)

    listing_id: int | None = None
    history: dict | None = None  # {min, median, points} quando houver histórico
    collected_at: datetime = Field(default_factory=now_utc)

    @property
    def best_price(self) -> float | None:
        return self.price_cash or self.price_installment


def build_store_terms(raw: str, specs: Specs) -> list[str]:
    """Monta termos de busca "limpos" para as lojas a partir das specs.

    Ex.: "notebook 32gb ram i713th" -> ["notebook i7 13 geracao 32gb", "notebook i7 32gb"]
    """
    parts_specific: list[str] = []
    parts_broad: list[str] = []
    if specs.category in ("notebook", "tablet", "monitor"):
        parts_specific.append(specs.category)
        parts_broad.append(specs.category)
    elif specs.category == "desktop":
        parts_specific.append("pc")
        parts_broad.append("pc")
    elif specs.category == "placa_video":
        parts_specific.append("placa de video")
        parts_broad.append("placa de video")
    if specs.brand:
        parts_specific.append(specs.brand)
    if specs.cpu_line:
        line = specs.cpu_line
        human = (
            line.replace("ryzen_ai", "ryzen ai ").replace("ryzen", "ryzen ")
            .replace("ultra", "core ultra ").replace("core", "core ").strip()
        )
        human = " ".join(human.split())
        if specs.cpu_model:
            parts_specific.append(f"{human} {specs.cpu_model}")
        elif specs.cpu_generation and line.startswith("i"):
            parts_specific.append(f"{human} {specs.cpu_generation} geracao")
        else:
            parts_specific.append(human)
        parts_broad.append(human)
    if specs.gpu:
        parts_specific.append(specs.gpu)
        parts_broad.append(specs.gpu)
    if specs.ram_gb:
        parts_specific.append(f"{specs.ram_gb}gb")
        parts_broad.append(f"{specs.ram_gb}gb")
    parts_specific += specs.keywords[:2]

    terms: list[str] = []
    for t in (" ".join(parts_specific), " ".join(parts_broad)):
        t = t.strip()
        if t and t not in terms and len(t.split()) >= 2:
            terms.append(t)
    if not terms:
        terms.append(raw.strip())
    return terms
