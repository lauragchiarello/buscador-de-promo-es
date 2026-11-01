"""Testes dos adaptadores usando HTML/JSON salvos (sem internet)."""

import json

import httpx
import pytest

from app.adapters.base import StoreBlocked, StoreError, StoreNotConfigured
from app.adapters.http_policy import HttpPolicy
from app.adapters.kabum import KabumAdapter, kabum_item_to_offer, parse_kabum_html
from app.adapters.mercadolivre import MercadoLivreAdapter, ml_item_to_offer
from app.adapters.utils import parse_brl, parse_installments
from app.config import Settings
from app.schemas import SearchQuery

from .conftest import fixture_json, fixture_text

QUERY = SearchQuery(raw="notebook 32gb ram i7 13th", specs={}, store_terms=["notebook i7 13 geracao 32gb", "notebook i7 32gb"])
ROBOTS_KABUM = "User-agent: *\nDisallow: /busca/*?\nDisallow: *?query=*\nDisallow: /\nAllow: /\n"


def test_parse_brl_and_installments():
    assert parse_brl("R$ 1.234,56") == 1234.56
    assert parse_brl("R$ 89,90") == 89.9
    assert parse_installments("10x de R$ 894,90") == (10, 894.9)
    assert parse_installments(None) == (None, None)


# --- KaBuM! ---------------------------------------------------------------


def test_kabum_parse_fixture():
    items = parse_kabum_html(fixture_text("kabum_busca_notebook_i7_32gb.html"))
    assert len(items) == 30
    offers = [kabum_item_to_offer(i) for i in items]
    offers = [o for o in offers if o]
    assert offers, "nenhuma oferta convertida"
    o = offers[0]
    assert o.store == "kabum"
    assert o.url.startswith("https://www.kabum.com.br/produto/640415/")
    assert o.price_cash == 6510.72  # Pix
    assert o.price_installment == 6926.3
    assert o.installments == 10 and o.installment_value == 692.63
    assert o.price_list is None  # oldPrice = 0 -> sem preço "de"
    assert o.seller == "PRIME SHOCK COMERCIO ELETRONICO"
    assert o.is_official is False  # marketplace


def test_kabum_item_with_old_price_and_sold_by_kabum():
    o = kabum_item_to_offer({
        "code": 1, "name": "Notebook X i7 13ª 32GB", "friendlyName": "notebook-x", "price": 5000,
        "priceWithDiscount": 4500, "oldPrice": 6000, "maxInstallment": "10x de R$ 500,00",
        "available": True, "flags": {"isMarketplace": False, "isFreeShipping": True},
    })
    assert o.price_list == 6000
    assert o.discount_pct == 25.0
    assert o.seller == "KaBuM!" and o.is_official is True
    assert o.shipping == 0.0


def test_kabum_unavailable_item_is_skipped():
    assert kabum_item_to_offer({"code": 1, "name": "x", "available": False}) is None


def test_kabum_empty_page():
    assert parse_kabum_html(fixture_text("kabum_sem_resultado.html")) == []


def _transport(routes: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        for prefix, response in routes.items():
            if str(request.url).startswith(prefix):
                return response(request) if callable(response) else response
        return httpx.Response(404)
    return httpx.MockTransport(handler)


async def test_kabum_adapter_search_with_mock_http():
    html = fixture_text("kabum_busca_notebook_i7_32gb.html")
    settings = Settings(request_delay_min=0, request_delay_max=0)
    http = HttpPolicy(settings, transport=_transport({
        "https://www.kabum.com.br/robots.txt": httpx.Response(200, text=ROBOTS_KABUM),
        "https://www.kabum.com.br/busca/": httpx.Response(200, text=html),
    }))
    offers = await KabumAdapter(settings, http=http).search(QUERY)
    await http.aclose()
    assert len(offers) == 30  # duas variações de termo, mesmos itens -> sem duplicar


async def test_kabum_adapter_detects_block():
    settings = Settings(request_delay_min=0, request_delay_max=0)
    http = HttpPolicy(settings, transport=_transport({
        "https://www.kabum.com.br/robots.txt": httpx.Response(200, text=ROBOTS_KABUM),
        "https://www.kabum.com.br/busca/": httpx.Response(403, text="Access denied"),
    }))
    with pytest.raises(StoreBlocked):
        await KabumAdapter(settings, http=http).search(QUERY)
    await http.aclose()


async def test_kabum_redirect_to_captcha_is_block():
    settings = Settings(request_delay_min=0, request_delay_max=0)
    http = HttpPolicy(settings, transport=_transport({
        "https://www.kabum.com.br/robots.txt": httpx.Response(200, text=ROBOTS_KABUM),
        "https://www.kabum.com.br/busca/": httpx.Response(302, headers={"location": "https://www.kabum.com.br/captcha?x=1"}),
    }))
    with pytest.raises(StoreBlocked):
        await KabumAdapter(settings, http=http).search(QUERY)
    await http.aclose()


# --- Mercado Livre --------------------------------------------------------


def test_ml_item_conversion():
    data = fixture_json("ml_search_notebook.json")
    o = ml_item_to_offer(data["results"][0])
    assert o.price_cash == 4899.0
    assert o.price_list == 5799.0
    assert o.discount_pct == 15.5
    assert o.installments == 10 and o.price_installment == 4899.0
    assert o.is_official is True and o.seller == "Dell"
    assert o.seller_reputation == "MercadoLíder Platinum"
    assert o.image_url.startswith("https://")
    assert "RAM 32 GB" in o.specs["_extra_text"]


async def test_ml_not_configured(settings):
    with pytest.raises(StoreNotConfigured):
        await MercadoLivreAdapter(settings).search(QUERY)


async def test_ml_search_with_mock_api():
    data = fixture_json("ml_search_notebook.json")
    settings = Settings(ml_client_id="abc", ml_client_secret="xyz", request_delay_min=0, request_delay_max=0)
    MercadoLivreAdapter._token = None
    http = HttpPolicy(settings, transport=_transport({
        "https://api.mercadolibre.com/oauth/token": httpx.Response(200, json={"access_token": "T", "expires_in": 21600}),
        "https://api.mercadolibre.com/sites/MLB/search": httpx.Response(200, text=json.dumps(data)),
    }))
    offers = await MercadoLivreAdapter(settings, http=http).search(QUERY)
    await http.aclose()
    assert {o.external_id for o in offers} == {r["id"] for r in data["results"]}


async def test_ml_403_everywhere_is_reported_as_blocked():
    # Busca de anúncios E catálogo recusados -> loja bloqueada (o modo catálogo é testado em test_ml_catalog.py)
    settings = Settings(ml_client_id="abc", ml_client_secret="xyz")
    MercadoLivreAdapter._token = None
    MercadoLivreAdapter._listing_search_blocked = False
    http = HttpPolicy(settings, transport=_transport({
        "https://api.mercadolibre.com/oauth/token": httpx.Response(200, json={"access_token": "T", "expires_in": 21600}),
        "https://api.mercadolibre.com/sites/MLB/search": httpx.Response(403, json={"message": "forbidden"}),
        "https://api.mercadolibre.com/products/search": httpx.Response(403, json={"message": "forbidden"}),
    }))
    with pytest.raises(StoreBlocked):
        await MercadoLivreAdapter(settings, http=http).search(QUERY)
    await http.aclose()
    MercadoLivreAdapter._token = None
    MercadoLivreAdapter._listing_search_blocked = False


# --- Fast Shop (VTEX) -----------------------------------------------------

from app.adapters.fastshop import FastShopAdapter  # noqa: E402
from app.adapters.vtex import vtex_product_to_offer  # noqa: E402

ROBOTS_FASTSHOP = "User-agent: *\nDisallow: /busca/\nDisallow: /checkout/\n"


def _fs(product):
    return vtex_product_to_offer(product, store="fastshop", store_name="Fast Shop",
                                 homepage="https://site.fastshop.com.br", house_seller="Fast Shop")


def test_fastshop_fixture_conversion():
    data = fixture_json("fastshop_busca_notebook_i7_32gb.json")
    o = _fs(data["products"][0])
    assert o.title.startswith("Notebook Lenovo IdeaPad Slim 3")
    assert o.price_cash == 5449.0  # spotPrice (à vista/Pix)
    assert o.price_list == 8709.0 and o.discount_pct == 37.4
    assert o.installments == 10 and o.installment_value == 605.44  # 10x sem juros
    assert o.url.startswith("https://site.fastshop.com.br/notebook-lenovo") and o.url.endswith("/p")
    assert o.seller == "Fast Shop" and o.is_official is True
    assert o.specs["_extra_text"] == "Notebook"


def test_fastshop_uses_cheapest_seller_with_stock():
    data = fixture_json("fastshop_busca_notebook_i7_32gb.json")
    # Produto em que a Fast Shop está sem estoque e a própria marca vende
    p = next(p for p in data["products"] if p["items"][0]["sellers"][0]["commertialOffer"]["AvailableQuantity"] == 0
             and len(p["items"][0]["sellers"]) > 1)
    o = _fs(p)
    assert o is not None and o.seller != "Fast Shop" and o.price_cash > 0


def test_fastshop_without_interest_free_uses_longest_installment():
    p = {
        "productId": "1", "productName": "Notebook X i7 13ª 32GB", "link": "/x/p", "brand": "X", "categories": ["/Informática/Notebook/"],
        "items": [{"itemId": "1", "images": [], "sellers": [{"sellerName": "Fast Shop", "commertialOffer": {
            "Price": 1000, "spotPrice": 950, "ListPrice": 1000, "AvailableQuantity": 5,
            "Installments": [
                {"NumberOfInstallments": 1, "InterestRate": 0, "Value": 1000, "TotalValuePlusInterestRate": 1000},
                {"NumberOfInstallments": 12, "InterestRate": 1.49, "Value": 91.6, "TotalValuePlusInterestRate": 1099.2},
            ]}}]}],
    }
    o = _fs(p)
    assert (o.installments, o.installment_value, o.price_installment) == (12, 91.6, 1099.2)


def test_fastshop_product_without_stock_is_skipped():
    p = {"productId": "1", "productName": "Notebook", "items": [{"itemId": "1", "sellers": [
        {"sellerName": "Fast Shop", "commertialOffer": {"Price": 0, "spotPrice": 0, "AvailableQuantity": 0}}]}]}
    assert _fs(p) is None


async def test_fastshop_adapter_with_mock_http():
    data = fixture_json("fastshop_busca_notebook_i7_32gb.json")
    settings = Settings(request_delay_min=0, request_delay_max=0)
    http = HttpPolicy(settings, transport=_transport({
        "https://site.fastshop.com.br/robots.txt": httpx.Response(200, text=ROBOTS_FASTSHOP),
        "https://site.fastshop.com.br/api/io/": httpx.Response(200, json=data),
    }))
    offers = await FastShopAdapter(settings, http=http).search(QUERY)
    await http.aclose()
    assert 10 <= len(offers) <= 20
    assert all(o.price_cash and o.price_cash > 0 for o in offers)


async def test_fastshop_html_instead_of_json_is_reported():
    settings = Settings(request_delay_min=0, request_delay_max=0)
    http = HttpPolicy(settings, transport=_transport({
        "https://site.fastshop.com.br/robots.txt": httpx.Response(200, text=ROBOTS_FASTSHOP),
        "https://site.fastshop.com.br/api/io/": httpx.Response(200, text="<html>manutenção</html>"),
    }))
    with pytest.raises(StoreError):
        await FastShopAdapter(settings, http=http).search(QUERY)
    await http.aclose()


# --- Terabyte (catálogo) ----------------------------------------------------

from app.adapters.http_policy import HttpPolicy as _HP  # noqa: E402,F401
from app.adapters.terabyte import TerabyteAdapter, parse_terabyte_listing  # noqa: E402
from app.services import catalog as catalog_service  # noqa: E402

ROBOTS_TERABYTE = "User-agent: *\nDisallow: /busca\nDisallow: /checkout\nAllow: /\n"
CF_CHALLENGE = '<!DOCTYPE html><html><head><title>Just a moment...</title></head><body>challenge-platform</body></html>'


def test_terabyte_parse_fixture():
    offers = parse_terabyte_listing(fixture_text("terabyte_notebooks.html"))
    assert len(offers) == 13  # 23 na página, 10 sem estoque ("Avise-me")
    o = next(o for o in offers if o.external_id == "43024")
    assert o.title.startswith("Notebook Acer Aspire Go 15 Intel Core i7-13620H")
    assert o.price_cash == 4829.99 and o.price_list == 8719.9
    assert (o.installments, o.installment_value) == (12, 473.53)
    assert o.url == "https://www.terabyteshop.com.br/produto/43024/" + o.url.split("/43024/")[1]
    assert o.image_url.startswith("https://img.terabyteshop.com.br/")
    assert o.seller == "Terabyte" and o.is_official


def test_terabyte_challenge_page_raises():
    with pytest.raises(StoreError):
        parse_terabyte_listing(CF_CHALLENGE)


def _tb_query(category):
    return SearchQuery(raw="x", specs={"category": category} if category else {}, store_terms=["x"])


async def test_terabyte_catalog_refresh_and_reuse():
    settings = Settings(request_delay_min=0, request_delay_max=0)
    calls = {"n": 0}

    def listing(request):
        calls["n"] += 1
        return httpx.Response(200, text=fixture_text("terabyte_notebooks.html"))

    http = HttpPolicy(settings, transport=_transport({
        "https://www.terabyteshop.com.br/robots.txt": httpx.Response(200, text=ROBOTS_TERABYTE),
        "https://www.terabyteshop.com.br/notebooks": listing,
    }))
    adapter = TerabyteAdapter(settings, http=http)
    catalog_service.save_page("terabyte", "/notebooks", [])  # garante estado conhecido...
    from app.db import session_scope
    from app.models import CatalogPage
    with session_scope() as s:  # ...e "envelhece" a página para forçar atualização
        s.query(CatalogPage).filter_by(store="terabyte", path="/notebooks").delete()

    first = await adapter.search(_tb_query("notebook"))
    second = await adapter.search(_tb_query("notebook"))  # dentro de 6 h: usa o catálogo salvo
    await http.aclose()
    assert len(first) == 13 and len(second) == 13
    assert calls["n"] == 1


async def test_terabyte_blocked_without_catalog_is_reported():
    settings = Settings(request_delay_min=0, request_delay_max=0)
    http = HttpPolicy(settings, transport=_transport({
        "https://www.terabyteshop.com.br/robots.txt": httpx.Response(403, text=CF_CHALLENGE, headers={"cf-mitigated": "challenge"}),
    }))
    adapter = TerabyteAdapter(settings, http=http)
    with pytest.raises(StoreBlocked):
        await adapter.search(_tb_query("monitor"))  # categoria nunca lida
    await http.aclose()


async def test_terabyte_blocked_uses_old_catalog():
    settings = Settings(request_delay_min=0, request_delay_max=0)
    old = parse_terabyte_listing(fixture_text("terabyte_notebooks.html"))
    catalog_service.save_page("terabyte", "/pc-gamer", old[:3])
    from app.db import session_scope
    from app.models import CatalogPage
    from datetime import datetime, timedelta, timezone
    with session_scope() as s:
        page = s.query(CatalogPage).filter_by(store="terabyte", path="/pc-gamer").one()
        page.refreshed_at = datetime.now(timezone.utc) - timedelta(hours=10)
    http = HttpPolicy(settings, transport=_transport({
        "https://www.terabyteshop.com.br/robots.txt": httpx.Response(200, text=ROBOTS_TERABYTE),
        "https://www.terabyteshop.com.br/pc-gamer": httpx.Response(403, text=CF_CHALLENGE, headers={"cf-mitigated": "challenge"}),
    }))
    offers = await TerabyteAdapter(settings, http=http).search(_tb_query("desktop"))
    await http.aclose()
    assert len(offers) == 3


def test_catalog_store_without_category_returns_nothing():
    # A Terabyte não tem página de tablets: não pode cair no catálogo de notebooks/PCs
    q = SearchQuery(raw="samsung tab", specs={"category": "tablet", "brand": "samsung"}, store_terms=["tablet samsung"])
    assert TerabyteAdapter(Settings()).paths_for(q) == []
    q2 = SearchQuery(raw="rtx 4060", specs={"gpu": "rtx 4060"}, store_terms=["rtx 4060"])
    assert "/hardware/placas-de-video/nvidia-geforce" in TerabyteAdapter(Settings()).paths_for(q2)
