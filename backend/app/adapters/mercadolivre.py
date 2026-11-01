"""Mercado Livre — API oficial.

- Desde 2025 `GET /sites/MLB/search` responde 403 sem token, e a busca do site
  redireciona robôs para uma página de verificação de conta. Por isso usamos
  SOMENTE a API, com token OAuth do tipo `client_credentials`.
- Crie um app em https://developers.mercadolivre.com.br/devcenter e preencha
  ML_CLIENT_ID e ML_CLIENT_SECRET no .env.
- Os atributos do anúncio (RAM, processador...) são anexados ao texto usado na
  extração de specs, o que melhora muito a precisão no Mercado Livre.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from ..parsing.matcher import match
from ..parsing.specs import Specs, extract_specs
from ..schemas import Offer, SearchQuery
from .base import StoreAdapter, StoreBlocked, StoreError, StoreNotConfigured
from .registry import register
from .utils import detect_condition, discount

API = "https://api.mercadolibre.com"

# Atributos que ajudam a identificar specs (anexados ao título para o parser)
_SPEC_ATTRIBUTES = {
    "RAM": "RAM",
    "RAM_MEMORY": "RAM",
    "PROCESSOR_BRAND": "",
    "PROCESSOR_LINE": "",
    "PROCESSOR_MODEL": "",
    "PROCESSOR_GENERATION": "",
    "SSD_DATA_STORAGE_CAPACITY": "SSD",
    "HARD_DRIVE_CAPACITY": "HD",
    "GPU_MODEL": "",
    "GRAPHICS_CARD_MODEL": "",
    "DISPLAY_SIZE": "tela",
}


def ml_item_to_offer(item: dict) -> Offer | None:
    item_id = item.get("id")
    title = (item.get("title") or "").strip()
    price = item.get("price")
    if not item_id or not title or not price:
        return None

    original = item.get("original_price")
    inst = item.get("installments") or {}
    n_inst = inst.get("quantity")
    inst_amount = inst.get("amount")
    price_installment = round(n_inst * inst_amount, 2) if n_inst and inst_amount else None
    shipping = item.get("shipping") or {}
    seller = item.get("seller") or {}
    official_id = item.get("official_store_id")

    spec_text = []
    for attr in item.get("attributes") or []:
        if attr.get("id") in _SPEC_ATTRIBUTES and attr.get("value_name"):
            prefix = _SPEC_ATTRIBUTES[attr["id"]]
            spec_text.append(f"{prefix} {attr['value_name']}".strip())

    condition = {"used": "usado", "refurbished": "recondicionado"}.get(item.get("condition"), "novo")
    if condition == "novo":
        condition = detect_condition(title)

    image = item.get("thumbnail") or ""
    image = image.replace("http://", "https://").replace("-I.jpg", "-O.jpg")

    rep = (seller.get("seller_reputation") or {}).get("power_seller_status")
    return Offer(
        store="mercadolivre",
        store_name="Mercado Livre",
        external_id=str(item_id),
        title=title,
        url=item.get("permalink") or f"https://produto.mercadolivre.com.br/{item_id}",
        image_url=image or None,
        price_cash=float(price),
        price_installment=price_installment,
        installments=n_inst,
        installment_value=inst_amount,
        price_list=float(original) if original and original > price else None,
        discount_pct=discount(original, price),
        shipping=0.0 if shipping.get("free_shipping") else None,
        seller=item.get("official_store_name") or seller.get("nickname"),
        seller_reputation={"platinum": "MercadoLíder Platinum", "gold": "MercadoLíder Gold", "silver": "MercadoLíder"}.get(rep or ""),
        is_official=bool(official_id),
        condition=condition,
        specs={"_extra_text": " ".join(spec_text)} if spec_text else {},
    )


def catalog_attributes_text(product: dict) -> str:
    """Atributos úteis do produto de catálogo, como texto para o parser de specs."""
    parts = []
    for attr in product.get("attributes") or []:
        if attr.get("id") in _SPEC_ATTRIBUTES and attr.get("value_name"):
            parts.append(f"{_SPEC_ATTRIBUTES[attr['id']]} {attr['value_name']}".strip())
    return " ".join(parts)


def ml_catalog_to_offer(product: dict, items: list[dict]) -> Offer | None:
    """Produto de catálogo + seus anúncios -> oferta com o anúncio novo mais barato."""
    pid = product.get("id")
    name = (product.get("name") or "").strip()
    priced = [i for i in items if i.get("price") and i.get("condition", "new") == "new"] or [i for i in items if i.get("price")]
    if not pid or not name or not priced:
        return None
    best = min(priced, key=lambda i: i["price"])
    price = float(best["price"])
    original = best.get("original_price")
    shipping = best.get("shipping") or {}
    pictures = product.get("pictures") or []
    condition = {"used": "usado", "refurbished": "recondicionado"}.get(best.get("condition"), "novo")
    if condition == "novo":
        condition = detect_condition(name)
    extra = catalog_attributes_text(product)
    return Offer(
        store="mercadolivre",
        store_name="Mercado Livre",
        external_id=str(pid),
        title=name,
        url=product.get("permalink") or f"https://www.mercadolivre.com.br/p/{pid}",
        image_url=(pictures[0].get("url") or pictures[0].get("secure_url")) if pictures else None,
        price_cash=price,
        price_list=float(original) if original and original > price else None,
        discount_pct=discount(original, price),
        shipping=0.0 if shipping.get("free_shipping") else None,
        seller=f"{len(priced)} {'vendedor' if len(priced) == 1 else 'vendedores'} no catálogo",
        is_official=bool(best.get("official_store_id")),
        condition=condition,
        specs={"_extra_text": extra} if extra else {},
    )


@register
class MercadoLivreAdapter(StoreAdapter):
    slug = "mercadolivre"
    name = "Mercado Livre"
    homepage = "https://www.mercadolivre.com.br"
    strategy = "API oficial (OAuth client_credentials); usa o catálogo quando a busca de anúncios é recusada"

    _token: str | None = None
    _token_exp: float = 0.0

    def is_configured(self) -> bool:
        return bool(self.settings.ml_client_id and self.settings.ml_client_secret)

    def not_configured_message(self) -> str:
        return "Configure ML_CLIENT_ID e ML_CLIENT_SECRET no .env para buscar no Mercado Livre"

    @property
    def _client(self) -> httpx.AsyncClient:
        if self.http is None:
            raise StoreError("Cliente HTTP não configurado")
        return self.http.client

    async def _get_token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        resp = await self._client.post(
            f"{API}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.settings.ml_client_id,
                "client_secret": self.settings.ml_client_secret,
            },
            headers={"Accept": "application/json"},
        )
        if resp.status_code != 200:
            raise StoreError("Não foi possível autenticar na API do Mercado Livre", detail=f"oauth HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        type(self)._token = data["access_token"]
        type(self)._token_exp = time.time() + int(data.get("expires_in", 21600))
        return self._token  # type: ignore[return-value]

    #: Desde 2025 a busca de anúncios dá 403 para a maioria dos apps; quando isso
    #: acontece, passamos a usar só o catálogo (e lembramos disso até reiniciar).
    _listing_search_blocked: bool = False
    catalog_max_products: int = 12

    async def _api_get(self, path: str, token: str, params: dict | None = None) -> httpx.Response:
        try:
            return await self._client.get(
                f"{API}{path}", params=params,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise StoreError("Não foi possível conectar ao Mercado Livre", detail=str(exc)) from exc

    async def search(self, query: SearchQuery) -> list[Offer]:
        if not self.is_configured():
            raise StoreNotConfigured(self.not_configured_message())
        token = await self._get_token()
        if not self._listing_search_blocked:
            try:
                return await self._search_listings(query, token)
            except StoreBlocked as exc:
                self.log.warning("busca de anúncios recusada (%s); usando o catálogo", exc.detail)
                type(self)._listing_search_blocked = True
        return await self._search_catalog(query, token)

    async def _search_listings(self, query: SearchQuery, token: str) -> list[Offer]:
        """Busca normal de anúncios (/sites/MLB/search)."""
        offers: dict[str, Offer] = {}
        for term in query.store_terms[:2]:
            resp = await self._api_get("/sites/MLB/search", token, {"q": term, "limit": 50})
            if resp.status_code in (401, 403):
                raise StoreBlocked("A API de busca do Mercado Livre recusou o acesso",
                                   detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
            if resp.status_code != 200:
                raise StoreError("Mercado Livre respondeu com erro", detail=f"HTTP {resp.status_code}")
            results = resp.json().get("results") or []
            self.log.info("'%s' -> %d itens", term, len(results))
            for item in results:
                offer = ml_item_to_offer(item)
                if offer and offer.external_id not in offers:
                    offers[offer.external_id] = offer
        return list(offers.values())

    async def _search_catalog(self, query: SearchQuery, token: str) -> list[Offer]:
        """Busca no catálogo (/products/search) e preço dos anúncios de cada produto (/products/{id}/items).

        Para economizar requisições, só buscamos preço dos produtos cujo nome já é
        compatível com a busca (mesmo filtro usado no resto do app).
        """
        products: dict[str, dict] = {}
        for term in query.store_terms[:2]:
            resp = await self._api_get("/products/search", token, {"status": "active", "site_id": "MLB", "q": term, "limit": 50})
            if resp.status_code in (401, 403):
                raise StoreBlocked("O Mercado Livre recusou também a busca de catálogo",
                                   detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
            if resp.status_code != 200:
                raise StoreError("Mercado Livre respondeu com erro", detail=f"catálogo HTTP {resp.status_code}: {resp.text[:200]}")
            results = resp.json().get("results") or []
            self.log.info("catálogo '%s' -> %d produtos", term, len(results))
            for p in results:
                if p.get("id") and p["id"] not in products:
                    products[p["id"]] = p

        wanted = Specs(**{k: v for k, v in query.specs.items() if k in Specs.__dataclass_fields__})
        candidates = []
        for p in products.values():
            text = f"{p.get('name', '')} {catalog_attributes_text(p)}"
            if match(wanted, p.get("name", ""), extract_specs(text)).accepted:
                candidates.append(p)
        candidates = candidates[: self.catalog_max_products]
        self.log.info("catálogo: %d produtos, %d compatíveis pelo nome", len(products), len(candidates))

        sem = asyncio.Semaphore(4)

        async def price_of(product: dict) -> Offer | None:
            async with sem:
                resp = await self._api_get(f"/products/{product['id']}/items", token, {"limit": 20})
            if resp.status_code != 200:
                self.log.info("sem preço para %s (HTTP %s)", product["id"], resp.status_code)
                return None
            return ml_catalog_to_offer(product, resp.json().get("results") or [])

        found = await asyncio.gather(*(price_of(p) for p in candidates))
        return [o for o in found if o]
