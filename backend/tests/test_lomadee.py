"""Lomadee: conversão de produtos e busca com a API simulada (formato de docs.lomadee.com.br)."""

import httpx
import pytest

from app.adapters.base import StoreBlocked, StoreNotConfigured
from app.adapters.http_policy import HttpPolicy
from app.adapters.lomadee import LomadeeAdapter, lomadee_product_to_offer
from app.config import Settings
from app.schemas import SearchQuery

ORG = "e36f5bbb-3e5f-42e2-be4c-6c32dac101c2"
BRANDS = {"data": [{"organizationId": ORG, "name": "Loja Exemplo"}], "pagination": {"page": 1, "limit": 20, "total": 1, "totalPages": 1}}
PRODUCTS = {
    "count": 2,
    "data": [
        {
            "organizationId": ORG, "id": "1027452", "available": True,
            "name": "Notebook Lenovo IdeaPad Slim 3 Intel Core i7-13620H 32GB 1TB SSD",
            "url": "https://www.lojaexemplo.com.br/notebook-lenovo-1027452/p",
            "images": [{"url": "https://img.lojaexemplo.com.br/1.jpg"}],
            "options": [
                {"id": "a", "available": True, "pricing": [{"listPrice": 649900, "price": 549900}]},
                {"id": "b", "available": False, "pricing": [{"listPrice": 499900, "price": 399900}]},  # indisponível
            ],
        },
        {"organizationId": ORG, "id": "2", "available": True, "name": "Sem preço", "url": "https://x/2", "options": []},
    ],
}


def test_product_conversion_cents():
    o = lomadee_product_to_offer(PRODUCTS["data"][0], {ORG: "Loja Exemplo"})
    assert o.price_cash == 5499.0 and o.price_list == 6499.0  # centavos -> reais
    assert o.discount_pct == 15.4
    assert o.store == "lomadee" and o.store_name == "Loja Exemplo"
    assert o.url.endswith("/p") and o.image_url.endswith("1.jpg")
    assert lomadee_product_to_offer(PRODUCTS["data"][1], {}) is None


def test_product_conversion_reais_when_configured():
    o = lomadee_product_to_offer(PRODUCTS["data"][0], {}, in_cents=False)
    assert o.price_cash == 549900 and o.store_name == "Loja parceira"


async def test_not_configured(settings):
    with pytest.raises(StoreNotConfigured):
        await LomadeeAdapter(settings).search(SearchQuery(raw="x", specs={}, store_terms=["x"]))


async def test_search_with_mock_api():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.setdefault("keys", set()).add(request.headers.get("x-api-key"))
        if request.url.path == "/affiliate/brands":
            return httpx.Response(200, json=BRANDS)
        if request.url.path == "/affiliate/products":
            seen["search"] = request.url.params.get("search")
            return httpx.Response(200, json=PRODUCTS)
        return httpx.Response(404)

    LomadeeAdapter._brands, LomadeeAdapter._brands_at = {}, 0.0
    settings = Settings(lomadee_api_key="chave-teste")
    http = HttpPolicy(settings, transport=httpx.MockTransport(handler))
    offers = await LomadeeAdapter(settings, http=http).search(
        SearchQuery(raw="notebook", specs={"category": "notebook"}, store_terms=["notebook i7 32gb"])
    )
    await http.aclose()
    assert seen["keys"] == {"chave-teste"} and seen["search"] == "notebook i7 32gb"
    assert len(offers) == 1 and offers[0].store_name == "Loja Exemplo"


async def test_invalid_key_is_blocked():
    LomadeeAdapter._brands, LomadeeAdapter._brands_at = {"x": "y"}, 9e18  # pula a lista de lojas
    settings = Settings(lomadee_api_key="errada")
    http = HttpPolicy(settings, transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"message": "API key is required"})))
    with pytest.raises(StoreBlocked):
        await LomadeeAdapter(settings, http=http).search(SearchQuery(raw="x", specs={}, store_terms=["x"]))
    await http.aclose()
    LomadeeAdapter._brands, LomadeeAdapter._brands_at = {}, 0.0
