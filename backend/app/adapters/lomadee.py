"""Lomadee — rede de afiliados (API de afiliados, docs.lomadee.com.br).

Uma busca traz produtos de TODAS as lojas parceiras da rede às quais você tem acesso.
Funciona na nuvem (Render), porque os dados vêm da API da rede, não do site da loja.

Requisitos (no .env): LOMADEE_API_KEY (chave "affiliate", header x-api-key).

Endpoints usados:
  GET /affiliate/products?search=<termo>&limit=100&isAvailable=true
      -> data[]: name, url, images[].url, organizationId,
                 options[].pricing[].price / listPrice, options[].available
  GET /affiliate/brands?page=N   (nome da loja de cada organizationId; cache de 6 h)
Limite: 60 requisições/minuto por chave.

Atenção aos preços: a documentação diz "em centavos", mas o exemplo oficial parece
estar em reais. Seguimos a documentação (LOMADEE_PRICE_IN_CENTS=true) e há uma checagem
de sanidade no log. Se os preços aparecerem 100x menores, use LOMADEE_PRICE_IN_CENTS=false.
"""

from __future__ import annotations

import time

import httpx

from ..schemas import Offer, SearchQuery
from .base import StoreAdapter, StoreBlocked, StoreError, StoreNotConfigured
from .registry import register
from .utils import detect_condition, discount


def _cheapest_option(product: dict) -> tuple[dict, dict] | None:
    """(opção, preço) mais barata e disponível entre as variações do produto."""
    best = None
    for opt in product.get("options") or []:
        if opt.get("available") is False:
            continue
        for pricing in opt.get("pricing") or []:
            price = pricing.get("price")
            if price and (best is None or price < best[1]["price"]):
                best = (opt, pricing)
    return best


def lomadee_product_to_offer(product: dict, brands: dict[str, str], *, in_cents: bool = True) -> Offer | None:
    found = _cheapest_option(product)
    name = (product.get("name") or "").strip()
    url = product.get("url")
    if not found or not name or not url or product.get("available") is False:
        return None
    opt, pricing = found
    factor = 100 if in_cents else 1
    price = pricing["price"] / factor
    list_price = (pricing.get("listPrice") or 0) / factor or None
    images = product.get("images") or opt.get("images") or []
    store_name = brands.get(product.get("organizationId", ""), "Loja parceira")
    return Offer(
        store="lomadee",
        store_name=store_name,
        external_id=f"{product.get('organizationId', '')}:{product.get('id')}",
        title=name,
        url=url,
        image_url=images[0].get("url") if images else None,
        price_cash=round(price, 2),
        price_list=round(list_price, 2) if list_price and list_price > price else None,
        discount_pct=discount(list_price, price),
        seller=store_name,
        is_official=True,  # a loja parceira vende o próprio produto
        condition=detect_condition(name),
    )


@register
class LomadeeAdapter(StoreAdapter):
    slug = "lomadee"
    name = "Lomadee (lojas parceiras)"
    homepage = "https://www.lomadee.com.br"
    strategy = "API oficial de afiliados da Lomadee (várias lojas numa busca só)"

    _brands: dict[str, str] = {}
    _brands_at: float = 0.0

    def is_configured(self) -> bool:
        return bool(self.settings.lomadee_api_key)

    def not_configured_message(self) -> str:
        return "Configure LOMADEE_API_KEY no .env (chave de afiliado da Lomadee)"

    async def _get(self, path: str, params: dict) -> dict:
        if self.http is None:
            raise StoreError("Cliente HTTP não configurado")
        try:
            resp = await self.http.client.get(
                f"{self.settings.lomadee_base_url}{path}", params=params,
                headers={"x-api-key": self.settings.lomadee_api_key, "Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise StoreError("Não foi possível conectar à Lomadee", detail=str(exc)) from exc
        if resp.status_code in (401, 403):
            raise StoreBlocked("A Lomadee recusou a chave (confira a chave e as permissões/scopes)",
                               detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code == 429:
            raise StoreError("Limite de requisições da Lomadee atingido, tente em instantes",
                             detail=f"Retry-After: {resp.headers.get('retry-after')}")
        if resp.status_code != 200:
            raise StoreError("A Lomadee respondeu com erro", detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    async def _load_brands(self) -> dict[str, str]:
        """organizationId -> nome da loja (cache de 6 h; no máximo 10 páginas de 20)."""
        if self._brands and time.time() - self._brands_at < 6 * 3600:
            return self._brands
        brands: dict[str, str] = {}
        try:
            for page in range(1, 11):
                data = await self._get("/affiliate/brands", {"page": page, "limit": 20})
                for b in data.get("data") or []:
                    org = b.get("organizationId") or b.get("id")
                    if org and b.get("name"):
                        brands[org] = b["name"]
                pag = data.get("pagination") or {}
                if page >= (pag.get("totalPages") or 1):
                    break
        except StoreError as exc:
            self.log.warning("não consegui listar as lojas da Lomadee: %s", exc.detail)
        type(self)._brands, type(self)._brands_at = brands, time.time()
        return brands

    async def search(self, query: SearchQuery) -> list[Offer]:
        if not self.is_configured():
            raise StoreNotConfigured(self.not_configured_message())
        brands = await self._load_brands()
        in_cents = self.settings.lomadee_price_in_cents
        offers: dict[str, Offer] = {}
        for term in query.store_terms[:2]:
            data = await self._get("/affiliate/products", {"search": term, "limit": 100, "isAvailable": "true"})
            products = data.get("data") or []
            self.log.info("'%s' -> %d produtos (de %s)", term, len(products), data.get("count"))
            for p in products:
                offer = lomadee_product_to_offer(p, brands, in_cents=in_cents)
                if offer and offer.external_id not in offers:
                    offers[offer.external_id] = offer
        prices = [o.price_cash for o in offers.values() if o.price_cash]
        if prices and query.specs.get("category") == "notebook" and max(prices) < 300:
            self.log.warning("preços de notebook abaixo de R$ 300: confira LOMADEE_PRICE_IN_CENTS")
        return list(offers.values())
