"""Testes dos adaptadores via API oficial com chave (Amazon e Shopee), sem internet."""

import hashlib
import json
import re

import httpx
import pytest

from app.adapters.amazon import AmazonAdapter, amazon_item_to_offer
from app.adapters.base import StoreBlocked, StoreNotConfigured
from app.adapters.http_policy import HttpPolicy
from app.adapters.shopee import ShopeeAdapter, shopee_node_to_offer, sign
from app.config import Settings
from app.schemas import SearchQuery

from .conftest import fixture_json

QUERY = SearchQuery(raw="notebook 32gb ram i7 13th", specs={}, store_terms=["notebook i7 13 geracao 32gb", "notebook i7 32gb"])


def _transport(routes: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        for prefix, response in routes.items():
            if str(request.url).startswith(prefix):
                return response(request) if callable(response) else response
        return httpx.Response(404)
    return httpx.MockTransport(handler)


# --- Amazon (Creators API) --------------------------------------------------


def test_amazon_item_conversion():
    items = fixture_json("amazon_search_notebook.json")["searchResult"]["items"]
    o = amazon_item_to_offer(items[0])
    assert o.external_id == "B0TEST0001" and o.price_cash == 5199.0
    assert o.price_list == 6499.0 and o.discount_pct == 20.0
    assert o.is_official is True and o.seller == "Amazon.com.br"
    assert "tag=meutag-20" in o.url
    # Usa a oferta vencedora (nova), não a usada mais barata
    o2 = amazon_item_to_offer(items[1])
    assert o2.price_cash == 3899.0 and o2.condition == "novo" and o2.is_official is False
    assert amazon_item_to_offer(items[2]) is None  # sem oferta


async def test_amazon_not_configured(settings):
    with pytest.raises(StoreNotConfigured):
        await AmazonAdapter(settings).search(QUERY)


async def test_amazon_search_with_mock_api():
    data = fixture_json("amazon_search_notebook.json")
    settings = Settings(amazon_client_id="id", amazon_client_secret="sec", amazon_partner_tag="meutag-20")
    AmazonAdapter._token = None
    seen = {}

    def search(request):
        seen["marketplace"] = request.headers.get("x-marketplace")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=data)

    http = HttpPolicy(settings, transport=_transport({
        "https://api.amazon.com/auth/o2/token": httpx.Response(200, json={"access_token": "A", "expires_in": 3600}),
        "https://creatorsapi.amazon/catalog/v1/searchItems": search,
    }))
    adapter = AmazonAdapter(settings, http=http)
    adapter.min_interval = 0
    offers = await adapter.search(QUERY)
    await http.aclose()
    AmazonAdapter._token = None
    assert {o.external_id for o in offers} == {"B0TEST0001", "B0TEST0002"}
    assert seen["marketplace"] == "www.amazon.com.br"
    assert seen["body"]["partnerTag"] == "meutag-20" and seen["body"]["itemCount"] == 10


async def test_amazon_forbidden_is_blocked():
    settings = Settings(amazon_client_id="id", amazon_client_secret="sec", amazon_partner_tag="t-20")
    AmazonAdapter._token = None
    http = HttpPolicy(settings, transport=_transport({
        "https://api.amazon.com/auth/o2/token": httpx.Response(200, json={"access_token": "A", "expires_in": 3600}),
        "https://creatorsapi.amazon/catalog/v1/searchItems": httpx.Response(403, json={"message": "not eligible"}),
    }))
    with pytest.raises(StoreBlocked):
        await AmazonAdapter(settings, http=http).search(QUERY)
    await http.aclose()
    AmazonAdapter._token = None


# --- Shopee (Afiliados) -----------------------------------------------------


def test_shopee_signature_is_sha256_hex():
    assert sign("123", "seg", 1700000000, '{"q":1}') == hashlib.sha256(b'1231700000000{"q":1}seg').hexdigest()


def test_shopee_node_conversion():
    nodes = fixture_json("shopee_productofferv2_notebook.json")["data"]["productOfferV2"]["nodes"]
    o = shopee_node_to_offer(nodes[0])
    assert o.price_cash == 4699.0 and o.discount_pct == 25
    assert o.price_list == round(4699 / 0.75, 2)
    assert o.is_official is True  # Shopee Mall
    assert o.url == "https://s.shopee.com.br/afiliado1"
    o2 = shopee_node_to_offer(nodes[1])
    assert o2.price_list is None and o2.is_official is False and o2.seller_reputation == "Loja indicada"


async def test_shopee_not_configured(settings):
    with pytest.raises(StoreNotConfigured):
        await ShopeeAdapter(settings).search(QUERY)


async def test_shopee_search_signs_request():
    data = fixture_json("shopee_productofferv2_notebook.json")
    settings = Settings(shopee_app_id="111", shopee_app_secret="abc")
    seen = {}

    def gql(request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.content.decode()
        return httpx.Response(200, json=data)

    http = HttpPolicy(settings, transport=_transport({"https://open-api.affiliate.shopee.com.br/graphql": gql}))
    offers = await ShopeeAdapter(settings, http=http).search(QUERY)
    await http.aclose()
    assert len(offers) == 3
    ts = int(re.search(r"Timestamp=(\d+)", seen["auth"]).group(1))
    assert seen["auth"].startswith("SHA256 Credential=111, Timestamp=")
    assert seen["auth"].endswith(f"Signature={sign('111', 'abc', ts, seen['body'])}")


async def test_shopee_invalid_credentials_reported_as_blocked():
    settings = Settings(shopee_app_id="111", shopee_app_secret="errado")
    http = HttpPolicy(settings, transport=_transport({"https://open-api.affiliate.shopee.com.br/graphql":
        httpx.Response(200, json={"errors": [{"message": "Invalid Signature", "extensions": {"code": 10020}}]})}))
    with pytest.raises(StoreBlocked):
        await ShopeeAdapter(settings, http=http).search(QUERY)
    await http.aclose()
