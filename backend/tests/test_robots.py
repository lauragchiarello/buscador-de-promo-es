"""O leitor de robots.txt precisa seguir as regras do Google (curingas, regra mais longa)."""

from app.adapters.robots import RobotsRules

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130"

KABUM = """
User-agent: *
Allow: /.css
Disallow: /carrinho*
Disallow: *sort=price
Disallow: /busca/*?
Disallow: *?query=*
Disallow: /
Allow: /

User-agent: ia_archiver
Disallow: /
"""

PICHAU = """
User-Agent: *
Allow: /
Disallow: /api/
Disallow: /*?*
"""


def test_kabum_search_path_allowed_but_query_blocked():
    r = RobotsRules(KABUM)
    assert r.can_fetch(UA, "https://www.kabum.com.br/busca/notebook-i7-32gb")
    assert not r.can_fetch(UA, "https://www.kabum.com.br/busca/notebook?page_number=2")
    assert not r.can_fetch(UA, "https://www.kabum.com.br/?query=notebook")
    assert not r.can_fetch(UA, "https://www.kabum.com.br/carrinho")
    assert r.can_fetch(UA, "https://www.kabum.com.br/produto/123/notebook")


def test_specific_agent_group():
    r = RobotsRules(KABUM)
    assert not r.can_fetch("ia_archiver", "https://www.kabum.com.br/produto/1")


def test_pichau_blocks_any_query_string():
    r = RobotsRules(PICHAU)
    assert not r.can_fetch(UA, "https://www.pichau.com.br/search?q=notebook")
    assert r.can_fetch(UA, "https://www.pichau.com.br/notebooks")
    assert not r.can_fetch(UA, "https://www.pichau.com.br/api/catalog")


def test_empty_robots_allows_everything():
    assert RobotsRules("").can_fetch(UA, "https://example.com/qualquer")


async def test_challenged_robots_blocks_instead_of_proceeding():
    import httpx
    import pytest
    from app.adapters.base import StoreBlocked
    from app.adapters.http_policy import HttpPolicy
    from app.config import Settings

    def handler(request):
        return httpx.Response(403, text="<title>Just a moment...</title>", headers={"cf-mitigated": "challenge"})

    http = HttpPolicy(Settings(request_delay_min=0, request_delay_max=0), transport=httpx.MockTransport(handler))
    with pytest.raises(StoreBlocked):
        await http.get("https://loja.exemplo.com.br/categoria")
    await http.aclose()
