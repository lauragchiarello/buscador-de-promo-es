"""KaBuM! — scraping educado da página de busca.

Estratégia:
- URL `https://www.kabum.com.br/busca/<termo-com-hifens>` (o robots.txt libera
  este formato; bloqueia `?query=`, ordenação e paginação `/busca/*?`).
- A página é Next.js e traz os produtos em JSON dentro de
  `<script id="__NEXT_DATA__">`, então não dependemos de classes CSS.
- Até 2 variações de termo por busca (específica e ampla), com espera entre elas.

Campos do JSON usados:
  code, name, friendlyName, image/thumbnail, price (parcelado), priceWithDiscount (Pix),
  oldPrice ("de"), maxInstallment ("10x de R$ 894,90"), sellerName,
  flags.isMarketplace / flags.isFreeShipping, available, averageRating, ratingCount
"""

from __future__ import annotations

import json
import re

from ..schemas import Offer, SearchQuery
from .base import StoreAdapter, StoreError
from .registry import register
from .utils import detect_condition, discount, parse_installments, slugify_term

_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def parse_kabum_html(html: str) -> list[dict]:
    """Extrai a lista de produtos crua do HTML da busca."""
    m = _NEXT_DATA.search(html)
    if not m:
        raise StoreError("Formato da página do KaBuM! mudou", detail="__NEXT_DATA__ não encontrado")
    data = json.loads(m.group(1))
    page = data.get("props", {}).get("pageProps", {}).get("data", {})
    # Páginas de categoria (a busca às vezes redireciona para elas) mandam os dados como texto JSON.
    if isinstance(page, str):
        page = json.loads(page)
    if not isinstance(page, dict):
        return []
    catalog = page.get("catalogServer")
    if isinstance(catalog, str):  # versões antigas mandavam como string JSON
        catalog = json.loads(catalog)
    if not isinstance(catalog, dict):
        # Busca sem resultado ou redirecionada para uma categoria sem catálogo
        return []
    items = catalog.get("data") or []
    return [i for i in items if isinstance(i, dict)]


def kabum_item_to_offer(item: dict) -> Offer | None:
    if not item.get("available", True):
        return None
    code = item.get("code")
    name = (item.get("name") or "").strip()
    if not code or not name:
        return None

    price_installment = item.get("price") or None
    price_cash = item.get("priceWithDiscount") or price_installment
    offer_block = item.get("offer") or {}
    if offer_block.get("priceWithDiscount"):
        price_cash = offer_block["priceWithDiscount"]
    if offer_block.get("price"):
        price_installment = offer_block["price"]

    old = item.get("oldPrice") or None
    price_list = old if old and price_installment and old > price_installment else None
    n_inst, inst_value = parse_installments(item.get("maxInstallment"))
    flags = item.get("flags") or {}
    is_marketplace = bool(flags.get("isMarketplace"))
    seller = item.get("sellerName") if is_marketplace else "KaBuM!"

    return Offer(
        store="kabum",
        store_name="KaBuM!",
        external_id=str(code),
        title=name,
        url=f"https://www.kabum.com.br/produto/{code}/{item.get('friendlyName') or ''}".rstrip("/"),
        image_url=item.get("thumbnail") or item.get("image"),
        price_cash=float(price_cash) if price_cash else None,
        price_installment=float(price_installment) if price_installment else None,
        installments=n_inst,
        installment_value=inst_value,
        price_list=float(price_list) if price_list else None,
        discount_pct=discount(price_list, price_cash),
        shipping=0.0 if flags.get("isFreeShipping") else None,
        seller=seller,
        seller_reputation=None,
        # Vendido e entregue pelo KaBuM! conta como "loja oficial" para o filtro.
        is_official=not is_marketplace,
        condition=detect_condition(name),
        rating=item.get("averageRating") or None,
        rating_count=item.get("ratingCount") or None,
    )


@register
class KabumAdapter(StoreAdapter):
    slug = "kabum"
    name = "KaBuM!"
    homepage = "https://www.kabum.com.br"
    strategy = "Scraping da busca (JSON embutido na página), respeitando robots.txt"
    max_terms = 2

    async def search(self, query: SearchQuery) -> list[Offer]:
        if self.http is None:
            raise StoreError("Cliente HTTP não configurado")
        offers: dict[str, Offer] = {}
        errors: list[StoreError] = []
        for term in query.store_terms[: self.max_terms]:
            url = f"{self.homepage}/busca/{slugify_term(term)}"
            try:
                resp = await self.http.get(url)
            except StoreError as exc:
                errors.append(exc)
                if exc.status == "blocked":
                    break  # bloqueou: não insistir
                continue
            items = parse_kabum_html(resp.text)
            self.log.info("'%s' -> %d itens", term, len(items))
            for item in items:
                offer = kabum_item_to_offer(item)
                if offer and offer.external_id not in offers:
                    offers[offer.external_id] = offer
        if not offers and errors:
            raise errors[0]
        return list(offers.values())
