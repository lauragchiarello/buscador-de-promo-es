"""Amazon Brasil — Creators API (substituta oficial da PA-API 5, descontinuada em 2026).

Requisitos (no .env):
  AMAZON_CLIENT_ID, AMAZON_CLIENT_SECRET  -> credenciais da Creators API (Associados)
  AMAZON_PARTNER_TAG                      -> seu ID de associado (ex.: meutag-20)
A Amazon só libera a API para associados com vendas qualificadas recentes.

Fluxo:
  1. Token OAuth (Login with Amazon, região NA, que inclui o Brasil):
     POST https://api.amazon.com/auth/o2/token  {grant_type, client_id, client_secret, scope}
  2. POST https://creatorsapi.amazon/catalog/v1/searchItems
     cabeçalho x-marketplace: www.amazon.com.br ; até 10 itens por página.
Não fazemos scraping da Amazon (captcha frequente; não contornamos).
"""

from __future__ import annotations

import asyncio
import time

import httpx

from ..schemas import Offer, SearchQuery
from .base import StoreAdapter, StoreBlocked, StoreError, StoreNotConfigured
from .registry import register
from .utils import detect_condition, discount

TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SEARCH_URL = "https://creatorsapi.amazon/catalog/v1/searchItems"
RESOURCES = [
    "itemInfo.title",
    "images.primary.medium",
    "offersV2.listings.price",
    "offersV2.listings.condition",
    "offersV2.listings.merchantInfo",
    "offersV2.listings.availability",
    "offersV2.listings.isBuyBoxWinner",
]
_CONDITION = {"new": "novo", "used": "usado", "refurbished": "recondicionado", "collectible": "usado"}


def amazon_item_to_offer(item: dict) -> Offer | None:
    asin = item.get("asin")
    title = ((item.get("itemInfo") or {}).get("title") or {}).get("displayValue")
    listings = (item.get("offersV2") or {}).get("listings") or []
    # Preferimos a oferta "vencedora" (botão Comprar); senão, a mais barata.
    listings = [l for l in listings if ((l.get("price") or {}).get("money") or {}).get("amount")]
    if not asin or not title or not listings:
        return None
    listing = next((l for l in listings if l.get("isBuyBoxWinner")), None) or min(
        listings, key=lambda l: l["price"]["money"]["amount"]
    )
    price = float(listing["price"]["money"]["amount"])
    basis = ((listing["price"].get("savingBasis") or {}).get("money") or {}).get("amount")
    merchant = (listing.get("merchantInfo") or {}).get("name")
    cond_raw = ((listing.get("condition") or {}).get("value") or "New").lower()
    condition = _CONDITION.get(cond_raw, "novo")
    if condition == "novo":
        condition = detect_condition(title)
    image = (((item.get("images") or {}).get("primary") or {}).get("medium") or {}).get("url")

    return Offer(
        store="amazon",
        store_name="Amazon",
        external_id=asin,
        title=title.strip(),
        url=item.get("detailPageURL") or f"https://www.amazon.com.br/dp/{asin}",
        image_url=image,
        price_cash=price,
        price_list=float(basis) if basis and basis > price else None,
        discount_pct=discount(basis, price),
        seller=merchant,
        # "Vendido e entregue pela Amazon" conta como oficial.
        is_official=bool(merchant and merchant.lower().startswith("amazon")),
        condition=condition,
    )


@register
class AmazonAdapter(StoreAdapter):
    slug = "amazon"
    name = "Amazon"
    homepage = "https://www.amazon.com.br"
    strategy = "Creators API oficial (Associados Amazon)"
    pages_per_term = 2  # 10 itens por página
    min_interval = 1.1  # a API permite ~1 requisição/s para contas novas

    _token: str | None = None
    _token_exp: float = 0.0

    def is_configured(self) -> bool:
        s = self.settings
        return bool(s.amazon_client_id and s.amazon_client_secret and s.amazon_partner_tag)

    def not_configured_message(self) -> str:
        return "Configure AMAZON_CLIENT_ID, AMAZON_CLIENT_SECRET e AMAZON_PARTNER_TAG no .env (requer conta no Associados)"

    @property
    def _client(self) -> httpx.AsyncClient:
        if self.http is None:
            raise StoreError("Cliente HTTP não configurado")
        return self.http.client

    async def _get_token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        resp = await self._client.post(
            TOKEN_URL,
            json={
                "grant_type": "client_credentials",
                "client_id": self.settings.amazon_client_id,
                "client_secret": self.settings.amazon_client_secret,
                "scope": "creatorsapi::default",
            },
        )
        if resp.status_code != 200:
            raise StoreError("Não foi possível autenticar na API da Amazon", detail=f"token HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        type(self)._token = data["access_token"]
        type(self)._token_exp = time.time() + int(data.get("expires_in", 3600))
        return self._token  # type: ignore[return-value]

    async def search(self, query: SearchQuery) -> list[Offer]:
        if not self.is_configured():
            raise StoreNotConfigured(self.not_configured_message())
        token = await self._get_token()
        marketplace = self.settings.amazon_marketplace
        offers: dict[str, Offer] = {}
        first = True
        for term in query.store_terms[:2]:
            for page in range(1, self.pages_per_term + 1):
                if not first:
                    await asyncio.sleep(self.min_interval)
                first = False
                body = {
                    "keywords": term,
                    "partnerTag": self.settings.amazon_partner_tag,
                    "marketplace": marketplace,
                    "searchIndex": "All",
                    "itemCount": 10,
                    "itemPage": page,
                    "condition": "Any",
                    "resources": RESOURCES,
                }
                try:
                    resp = await self._client.post(
                        SEARCH_URL, json=body,
                        headers={"Authorization": f"Bearer {token}", "x-marketplace": marketplace},
                    )
                except httpx.HTTPError as exc:
                    raise StoreError("Não foi possível conectar à Amazon", detail=str(exc)) from exc
                if resp.status_code in (401, 403):
                    raise StoreBlocked("A API da Amazon recusou o acesso (confira as credenciais e as vendas do Associados)",
                                       detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
                if resp.status_code == 429:
                    self.log.warning("limite de requisições da Amazon atingido; parando")
                    break
                if resp.status_code != 200:
                    raise StoreError("A Amazon respondeu com erro", detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
                result = resp.json().get("searchResult") or {}
                items = result.get("items") or []
                self.log.info("'%s' p%d -> %d itens", term, page, len(items))
                for item in items:
                    offer = amazon_item_to_offer(item)
                    if offer and offer.external_id not in offers:
                        offers[offer.external_id] = offer
                if len(items) < 10:
                    break
        return list(offers.values())
