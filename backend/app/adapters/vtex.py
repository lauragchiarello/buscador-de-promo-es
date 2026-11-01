"""Base para lojas na plataforma VTEX (usa a busca pública "Intelligent Search").

É a mesma API JSON que a página de busca da própria loja usa no navegador:
    GET https://<loja>/api/io/_v/api/intelligent-search/product_search/?query=...&count=50
Não precisa de chave nem de navegador. Respeitamos robots.txt, rate limit e
detecção de bloqueio através do HttpPolicy.

Para uma nova loja VTEX basta herdar e definir slug, name, homepage
(e, se quiser, o nome do vendedor "da casa" em `house_seller`).

Campos usados de cada produto:
  productName, link, brand, categories, items[].images[].imageUrl,
  items[].sellers[].sellerName / commertialOffer:
    Price (cartão), spotPrice (à vista/Pix), ListPrice ("de"),
    AvailableQuantity, Installments (pega a maior parcela sem juros)
"""

from __future__ import annotations

from urllib.parse import quote

from ..schemas import Offer, SearchQuery
from .base import StoreAdapter, StoreError
from .utils import detect_condition, discount


def _best_installment(installments: list[dict]) -> tuple[int | None, float | None, float | None]:
    """Maior parcelamento SEM juros; se não houver, o maior COM juros -> (n, valor da parcela, total)."""
    best_free = best_any = None
    for inst in installments or []:
        n = inst.get("NumberOfInstallments") or 0
        if n < 2:
            continue
        if best_any is None or n > best_any["NumberOfInstallments"]:
            best_any = inst
        if not (inst.get("InterestRate") or 0) and (best_free is None or n > best_free["NumberOfInstallments"]):
            best_free = inst
    best = best_free or best_any
    if not best:
        return None, None, None
    return best["NumberOfInstallments"], best.get("Value"), best.get("TotalValuePlusInterestRate")


def _cheapest_available_seller(product: dict) -> tuple[dict, dict, dict] | None:
    """(item, seller, commertialOffer) mais barato com estoque, entre todos os SKUs e vendedores."""
    best = None
    for item in product.get("items") or []:
        for seller in item.get("sellers") or []:
            co = seller.get("commertialOffer") or {}
            price = co.get("spotPrice") or co.get("Price") or 0
            if not price or not co.get("AvailableQuantity"):
                continue
            if best is None or price < best[0]:
                best = (price, item, seller, co)
    return best[1:] if best else None


def vtex_product_to_offer(product: dict, *, store: str, store_name: str, homepage: str, house_seller: str) -> Offer | None:
    found = _cheapest_available_seller(product)
    title = (product.get("productName") or "").strip()
    if not found or not title:
        return None
    item, seller, co = found

    price = float(co.get("Price") or 0) or None
    spot = float(co.get("spotPrice") or 0) or price
    list_price = float(co.get("ListPrice") or 0) or None
    n_inst, inst_value, inst_total = _best_installment(co.get("Installments"))
    images = item.get("images") or []
    seller_name = seller.get("sellerName") or None
    brand = (product.get("brand") or "").lower()
    is_official = bool(
        seller_name
        and (seller_name == house_seller or "oficial" in seller_name.lower() or (brand and seller_name.lower() == brand))
    )
    # Última categoria (ex.: "Notebook", "Tablets") ajuda quando o título não diz o tipo do produto.
    categories = product.get("categories") or []
    category_leaf = categories[0].strip("/").split("/")[-1] if categories else ""

    return Offer(
        store=store,
        store_name=store_name,
        external_id=str(product.get("productId") or item.get("itemId")),
        title=title,
        url=f"{homepage}{product.get('link') or '/' + quote(product.get('linkText', '')) + '/p'}",
        image_url=images[0].get("imageUrl") if images else None,
        price_cash=spot,
        price_installment=float(inst_total) if inst_total else price,
        installments=n_inst,
        installment_value=float(inst_value) if inst_value else None,
        price_list=list_price if list_price and spot and list_price > spot else None,
        discount_pct=discount(list_price, spot),
        shipping=None,  # a busca da VTEX não informa frete (depende do CEP)
        seller=seller_name,
        is_official=is_official,
        condition=detect_condition(title),
        specs={"_extra_text": category_leaf} if category_leaf else {},
    )


class VtexAdapter(StoreAdapter):
    """Adaptador genérico para lojas VTEX. Herde e defina slug/name/homepage."""

    house_seller: str = ""
    page_size: int = 50
    max_terms: int = 2

    def search_url(self, term: str) -> str:
        return (
            f"{self.homepage}/api/io/_v/api/intelligent-search/product_search/"
            f"?query={quote(term)}&count={self.page_size}&page=1&locale=pt-BR&hideUnavailableItems=true"
        )

    async def search(self, query: SearchQuery) -> list[Offer]:
        if self.http is None:
            raise StoreError("Cliente HTTP não configurado")
        offers: dict[str, Offer] = {}
        errors: list[StoreError] = []
        for term in query.store_terms[: self.max_terms]:
            try:
                resp = await self.http.get(self.search_url(term), headers={"Accept": "application/json"})
                data = resp.json()
            except StoreError as exc:
                errors.append(exc)
                if exc.status == "blocked":
                    break
                continue
            except ValueError as exc:  # JSON inválido: provavelmente uma página de bloqueio
                errors.append(StoreError(f"{self.name} respondeu em formato inesperado", detail=str(exc)))
                continue
            products = data.get("products") or []
            self.log.info("'%s' -> %d itens (de %s)", term, len(products), data.get("recordsFiltered"))
            for p in products:
                offer = vtex_product_to_offer(
                    p, store=self.slug, store_name=self.name, homepage=self.homepage, house_seller=self.house_seller
                )
                if offer and offer.external_id not in offers:
                    offers[offer.external_id] = offer
        if not offers and errors:
            raise errors[0]
        return list(offers.values())
