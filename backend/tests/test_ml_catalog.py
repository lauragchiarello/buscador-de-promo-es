"""Mercado Livre: quando /sites/MLB/search dá 403, usa o catálogo (/products)."""

import httpx
import pytest

from app.adapters.base import StoreBlocked
from app.adapters.http_policy import HttpPolicy
from app.adapters.mercadolivre import MercadoLivreAdapter, ml_catalog_to_offer
from app.config import Settings
from app.parsing.specs import extract_specs
from app.schemas import SearchQuery

SPECS = extract_specs("notebook 32gb ram i7 13th", is_query=True).to_dict()
QUERY = SearchQuery(raw="notebook 32gb ram i7 13th", specs=SPECS, store_terms=["notebook i7 13 geracao 32gb", "notebook i7 32gb"])

CATALOG = {
    "paging": {"total": 3, "limit": 50, "offset": 0},
    "results": [
        {"id": "MLB1001", "name": "Notebook Lenovo IdeaPad Slim 3 i7-13620H 32GB 1TB SSD 15.3",
         "pictures": [{"id": "x", "url": "https://http2.mlstatic.com/D_1.jpg"}],
         "attributes": [{"id": "RAM", "value_name": "32 GB"}]},
        {"id": "MLB1002", "name": "Notebook Dell Inspiron 15 i7-1355U 16GB 512GB SSD", "pictures": [], "attributes": []},
        {"id": "MLB1003", "name": "Notebook Asus Vivobook i7 13ª Geração",  # RAM só nos atributos
         "pictures": [], "attributes": [{"id": "RAM", "value_name": "32 GB"}]},
    ],
}
ITEMS = {
    "MLB1001": {"results": [
        {"item_id": "MLB9001", "price": 5299.0, "original_price": 6199.0, "condition": "new", "seller_id": 1,
         "official_store_id": 55, "shipping": {"free_shipping": True}},
        {"item_id": "MLB9002", "price": 4999.0, "condition": "used", "seller_id": 2, "shipping": {}},
        {"item_id": "MLB9003", "price": 5499.0, "condition": "new", "seller_id": 3, "shipping": {}},
    ]},
    "MLB1003": {"results": [{"item_id": "MLB9010", "price": 4899.0, "condition": "new", "seller_id": 4, "shipping": {}}]},
}


def test_catalog_offer_uses_cheapest_new_listing():
    o = ml_catalog_to_offer(CATALOG["results"][0], ITEMS["MLB1001"]["results"])
    assert o.price_cash == 5299.0  # o usado de 4999 é ignorado quando há novos
    assert o.price_list == 6199.0 and o.discount_pct == 14.5
    assert o.is_official is True and o.shipping == 0.0
    assert o.url == "https://www.mercadolivre.com.br/p/MLB1001"
    assert o.seller == "2 vendedores no catálogo"
    assert "RAM 32 GB" in o.specs["_extra_text"]


def test_catalog_product_without_listings_is_skipped():
    assert ml_catalog_to_offer(CATALOG["results"][0], []) is None


def _transport(item_calls: list):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.startswith("https://api.mercadolibre.com/oauth/token"):
            return httpx.Response(200, json={"access_token": "T", "expires_in": 21600})
        if url.startswith("https://api.mercadolibre.com/sites/MLB/search"):
            return httpx.Response(403, json={"message": "forbidden"})
        if url.startswith("https://api.mercadolibre.com/products/search"):
            return httpx.Response(200, json=CATALOG)
        if "/items" in url and "/products/" in url:
            pid = url.split("/products/")[1].split("/")[0]
            item_calls.append(pid)
            return httpx.Response(200, json=ITEMS.get(pid, {"results": []}))
        return httpx.Response(404)
    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def _reset_ml_state():
    MercadoLivreAdapter._token = None
    MercadoLivreAdapter._listing_search_blocked = False
    yield
    MercadoLivreAdapter._token = None
    MercadoLivreAdapter._listing_search_blocked = False


async def test_falls_back_to_catalog_and_only_prices_compatible_products():
    calls: list = []
    settings = Settings(ml_client_id="a", ml_client_secret="b")
    http = HttpPolicy(settings, transport=_transport(calls))
    offers = await MercadoLivreAdapter(settings, http=http).search(QUERY)
    await http.aclose()
    # MLB1002 (16GB) é descartado pelo nome, sem gastar requisição de preço
    assert sorted(calls) == ["MLB1001", "MLB1003"]
    assert {o.external_id for o in offers} == {"MLB1001", "MLB1003"}
    assert MercadoLivreAdapter._listing_search_blocked is True


async def test_catalog_also_forbidden_is_reported():
    def handler(request):
        if "oauth" in str(request.url):
            return httpx.Response(200, json={"access_token": "T", "expires_in": 21600})
        return httpx.Response(403, json={"message": "forbidden"})

    settings = Settings(ml_client_id="a", ml_client_secret="b")
    http = HttpPolicy(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(StoreBlocked):
        await MercadoLivreAdapter(settings, http=http).search(QUERY)
    await http.aclose()
