"""Shopee — API de Afiliados (GraphQL), endpoint do Brasil.

Requisitos (no .env): SHOPEE_APP_ID e SHOPEE_APP_SECRET, obtidos no painel
"Open API" depois da aprovação em https://affiliate.shopee.com.br.

Autenticação de cada requisição:
  Authorization: SHA256 Credential={AppId}, Timestamp={ts}, Signature={sha256(AppId + ts + payload + Secret)}
  (payload = o corpo JSON exatamente como enviado; ts = Unix em segundos)

Consulta usada: productOfferV2(keyword, sortType, page, limit).
  shopType: 1 = Loja oficial (Shopee Mall), 2 = Indicada, 4 = Indicada+.
  priceDiscountRate: % de desconto (o preço "de" é estimado a partir dele).
Não fazemos scraping da Shopee (a busca do site exige login e tem anti-robô).
"""

from __future__ import annotations

import hashlib
import json
import time

import httpx

from ..schemas import Offer, SearchQuery
from .base import StoreAdapter, StoreBlocked, StoreError, StoreNotConfigured
from .registry import register
from .utils import detect_condition

ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

QUERY = """query($keyword: String, $page: Int, $limit: Int, $sortType: Int) {
  productOfferV2(keyword: $keyword, page: $page, limit: $limit, sortType: $sortType) {
    nodes {
      itemId productName priceMin priceMax priceDiscountRate
      imageUrl shopName shopId shopType ratingStar sales
      productLink offerLink
    }
    pageInfo { page limit hasNextPage }
  }
}"""

OFFICIAL_SHOP_TYPES = {1}


def sign(app_id: str, secret: str, timestamp: int, payload: str) -> str:
    return hashlib.sha256(f"{app_id}{timestamp}{payload}{secret}".encode()).hexdigest()


def _num(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def shopee_node_to_offer(node: dict) -> Offer | None:
    item_id = node.get("itemId")
    title = (node.get("productName") or "").strip()
    price = _num(node.get("priceMin"))
    if not item_id or not title or not price:
        return None
    rate = _num(node.get("priceDiscountRate")) or 0
    price_list = round(price / (1 - rate / 100), 2) if 0 < rate < 95 else None
    shop_types = node.get("shopType") or []
    if isinstance(shop_types, int):
        shop_types = [shop_types]
    return Offer(
        store="shopee",
        store_name="Shopee",
        external_id=str(item_id),
        title=title,
        url=node.get("offerLink") or node.get("productLink") or f"https://shopee.com.br/product/{node.get('shopId')}/{item_id}",
        image_url=node.get("imageUrl"),
        price_cash=price,
        price_list=price_list,
        discount_pct=round(rate, 1) if price_list else None,
        seller=node.get("shopName"),
        seller_reputation="Loja indicada" if set(shop_types) & {2, 4} else None,
        is_official=bool(set(shop_types) & OFFICIAL_SHOP_TYPES),
        condition=detect_condition(title),
        rating=_num(node.get("ratingStar")),
    )


@register
class ShopeeAdapter(StoreAdapter):
    slug = "shopee"
    name = "Shopee"
    homepage = "https://shopee.com.br"
    strategy = "API oficial de Afiliados (GraphQL)"
    page_limit = 50

    def is_configured(self) -> bool:
        return bool(self.settings.shopee_app_id and self.settings.shopee_app_secret)

    def not_configured_message(self) -> str:
        return "Configure SHOPEE_APP_ID e SHOPEE_APP_SECRET no .env (requer aprovação no programa de afiliados)"

    async def _post(self, variables: dict) -> dict:
        if self.http is None:
            raise StoreError("Cliente HTTP não configurado")
        payload = json.dumps({"query": QUERY, "variables": variables}, separators=(",", ":"), ensure_ascii=False)
        ts = int(time.time())
        auth = (
            f"SHA256 Credential={self.settings.shopee_app_id}, Timestamp={ts}, "
            f"Signature={sign(self.settings.shopee_app_id, self.settings.shopee_app_secret, ts, payload)}"
        )
        try:
            resp = await self.http.client.post(
                ENDPOINT, content=payload.encode(), headers={"Authorization": auth, "Content-Type": "application/json"}
            )
        except httpx.HTTPError as exc:
            raise StoreError("Não foi possível conectar à Shopee", detail=str(exc)) from exc
        if resp.status_code in (401, 403):
            raise StoreBlocked("A API da Shopee recusou o acesso", detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code != 200:
            raise StoreError("A Shopee respondeu com erro", detail=f"HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if data.get("errors"):
            err = data["errors"][0]
            code = (err.get("extensions") or {}).get("code")
            if code in (10020, 10031, 10032, 10033, 10034, 10035):  # assinatura/credencial inválida
                raise StoreBlocked("A Shopee recusou as credenciais", detail=json.dumps(err, ensure_ascii=False)[:300])
            if code == 10030:
                raise StoreError("Limite de requisições da Shopee atingido, tente em instantes", detail=str(err))
            raise StoreError("A Shopee respondeu com erro", detail=json.dumps(err, ensure_ascii=False)[:300])
        return data.get("data") or {}

    async def search(self, query: SearchQuery) -> list[Offer]:
        if not self.is_configured():
            raise StoreNotConfigured(self.not_configured_message())
        offers: dict[str, Offer] = {}
        for term in query.store_terms[:2]:
            # sortType 1 = relevância
            data = await self._post({"keyword": term, "page": 1, "limit": self.page_limit, "sortType": 1})
            nodes = ((data.get("productOfferV2") or {}).get("nodes")) or []
            self.log.info("'%s' -> %d itens", term, len(nodes))
            for node in nodes:
                offer = shopee_node_to_offer(node)
                if offer and offer.external_id not in offers:
                    offers[offer.external_id] = offer
        return list(offers.values())
