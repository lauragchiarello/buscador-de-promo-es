"""Acesso "educado" às lojas, compartilhado por todos os adaptadores de scraping.

- Respeita robots.txt (com cache de 6 h).
- Limita a taxa por domínio, com espera aleatória entre requisições.
- User-Agent realista e cabeçalhos de navegador.
- Detecta captcha / verificação / bloqueio e PARA (sem tentar contornar).
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from urllib.parse import urlsplit

import httpx

from ..config import Settings
from .base import RobotsDisallowed, StoreBlocked, StoreError
from .robots import RobotsRules

log = logging.getLogger("http_policy")

_BLOCK_MARKERS = (
    "captcha", "account-verification", "are you a robot", "verifique que voce e humano",
    "access denied", "cf-chl", "challenge-platform", "/gz/account-verification",
)


_CHALLENGED = "challenged"


def _is_challenge(resp: httpx.Response) -> bool:
    """Página de desafio anti-robô (Cloudflare "Just a moment...", captcha etc.)."""
    if resp.headers.get("cf-mitigated") == "challenge":
        return True
    if resp.status_code in (403, 429, 503):
        head = resp.text[:2000].lower()
        return "just a moment" in head or "captcha" in head or "challenge" in head
    return False


class HttpPolicy:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.6",
            },
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=False,
            transport=transport,
        )
        self._robots: dict[str, tuple[float, RobotsRules | None]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._last_hit: dict[str, float] = {}
        self.min_delay = settings.request_delay_min
        self.max_delay = settings.request_delay_max

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client

    async def aclose(self) -> None:
        await self._client.aclose()

    # -- robots ------------------------------------------------------------

    async def _robots_for(self, url: str) -> RobotsRules | None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        cached = self._robots.get(origin)
        if cached and time.monotonic() - cached[0] < 6 * 3600:
            return cached[1]
        rules: RobotsRules | None | str
        try:
            resp = await self._client.get(f"{origin}/robots.txt", follow_redirects=True)
            if _is_challenge(resp):
                # Não dá para ler as regras: não seguimos. Tentamos de novo em 10 min.
                log.warning("robots.txt de %s respondeu com desafio anti-robô", origin)
                self._robots[origin] = (time.monotonic() - 6 * 3600 + 600, _CHALLENGED)
                return _CHALLENGED
            rules = RobotsRules(resp.text) if resp.status_code == 200 else None
        except httpx.HTTPError as exc:
            log.warning("robots.txt de %s indisponível (%s); seguindo com cautela", origin, exc)
            rules = None
        self._robots[origin] = (time.monotonic(), rules)
        return rules

    async def check_robots(self, url: str) -> None:
        rules = await self._robots_for(url)
        if rules is _CHALLENGED:
            raise StoreBlocked(
                "A loja está pedindo verificação anti-robô no momento",
                detail=f"robots.txt de {urlsplit(url).netloc} veio com desafio (ex.: Cloudflare)",
            )
        if rules and not rules.can_fetch(self.settings.user_agent, url):
            raise RobotsDisallowed("Página bloqueada pelo robots.txt da loja", detail=f"robots.txt proíbe {url}")

    # -- rate limit ----------------------------------------------------------

    async def _wait_turn(self, host: str) -> None:
        lock = self._locks.setdefault(host, asyncio.Lock())
        async with lock:
            last = self._last_hit.get(host)
            if last is not None:
                wait = random.uniform(self.min_delay, self.max_delay) - (time.monotonic() - last)
                if wait > 0:
                    await asyncio.sleep(wait)
            self._last_hit[host] = time.monotonic()

    # -- requisição ----------------------------------------------------------

    async def get(self, url: str, *, check_robots: bool = True, _redirects: int = 0, **kwargs) -> httpx.Response:
        if check_robots:
            await self.check_robots(url)
        await self._wait_turn(urlsplit(url).netloc)
        try:
            resp = await self._client.get(url, **kwargs)
        except httpx.TimeoutException as exc:
            raise StoreError("A loja demorou demais para responder", detail=f"timeout em {url}") from exc
        except httpx.HTTPError as exc:
            raise StoreError("Não foi possível conectar à loja", detail=f"{type(exc).__name__}: {exc}") from exc

        location = resp.headers.get("location", "")
        if resp.is_redirect and any(m in location.lower() for m in _BLOCK_MARKERS):
            raise StoreBlocked("A loja pediu verificação (captcha/login)", detail=f"redirecionado para {location}")
        if _is_challenge(resp):
            raise StoreBlocked(
                "A loja está pedindo verificação anti-robô no momento",
                detail=f"desafio anti-robô (HTTP {resp.status_code}) em {url}",
            )
        if resp.status_code in (403, 429):
            raise StoreBlocked(
                "A loja bloqueou o acesso no momento", detail=f"HTTP {resp.status_code} em {url}"
            )
        if resp.status_code >= 500:
            raise StoreError("A loja está com instabilidade", detail=f"HTTP {resp.status_code} em {url}")
        if resp.is_redirect:
            # Redirecionamento comum (ex.: busca -> categoria): segue com as mesmas regras, no máximo 3 vezes.
            if _redirects >= 3:
                raise StoreError("A loja redirecionou demais", detail=f"muitos redirecionamentos a partir de {url}")
            target = str(resp.next_request.url) if resp.next_request else location
            return await self.get(target, _redirects=_redirects + 1, **kwargs)
        if resp.status_code >= 400:
            raise StoreError("A loja respondeu com erro", detail=f"HTTP {resp.status_code} em {url}")
        head = resp.text[:4000].lower()
        if "captcha" in head and "__next_data__" not in head:
            raise StoreBlocked("A loja pediu verificação (captcha)", detail=f"captcha detectado em {url}")
        return resp
