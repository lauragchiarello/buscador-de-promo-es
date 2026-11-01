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

import time

import httpx

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


@register
class MercadoLivreAdapter(StoreAdapter):
    slug = "mercadolivre"
    name = "Mercado Livre"
    homepage = "https://www.mercadolivre.com.br"
    strategy = "API oficial (OAuth client_credentials)"

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

    async def search(self, query: SearchQuery) -> list[Offer]:
        if not self.is_configured():
            raise StoreNotConfigured(self.not_configured_message())
        token = await self._get_token()
        offers: dict[str, Offer] = {}
        for term in query.store_terms[:2]:
            try:
                resp = await self._client.get(
                    f"{API}/sites/MLB/search",
                    params={"q": term, "limit": 50},
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
            except httpx.HTTPError as exc:
                raise StoreError("Não foi possível conectar ao Mercado Livre", detail=str(exc)) from exc
            if resp.status_code in (401, 403):
                raise StoreBlocked(
                    "A API de busca do Mercado Livre recusou o acesso",
                    detail=f"HTTP {resp.status_code}: {resp.text[:200]}",
                )
            if resp.status_code != 200:
                raise StoreError("Mercado Livre respondeu com erro", detail=f"HTTP {resp.status_code}")
            results = resp.json().get("results") or []
            self.log.info("'%s' -> %d itens", term, len(results))
            for item in results:
                offer = ml_item_to_offer(item)
                if offer and offer.external_id not in offers:
                    offers[offer.external_id] = offer
        return list(offers.values())
