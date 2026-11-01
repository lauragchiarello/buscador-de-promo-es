"""Interface comum de todas as lojas.

Para criar uma loja nova:
1. Crie `app/adapters/minha_loja.py` com uma classe herdando de `StoreAdapter`.
2. Preencha `slug`, `name` e implemente `search()`.
3. Decore a classe com `@register` (de `registry.py`).
Pronto: ela aparece na API e na interface automaticamente.
"""

from __future__ import annotations

import abc
import logging
from typing import TYPE_CHECKING

from ..config import Settings
from ..schemas import Offer, SearchQuery

if TYPE_CHECKING:
    from .http_policy import HttpPolicy


class StoreError(Exception):
    """Erro "esperado" de uma loja. A mensagem é mostrada ao usuário de forma amigável."""

    status = "unavailable"

    def __init__(self, message: str, *, detail: str | None = None):
        super().__init__(message)
        self.detail = detail or message


class StoreNotConfigured(StoreError):
    status = "not_configured"


class StoreBlocked(StoreError):
    """Captcha, verificação de conta, 403/429... Não tentamos contornar."""

    status = "blocked"


class RobotsDisallowed(StoreError):
    status = "blocked"


class StoreAdapter(abc.ABC):
    slug: str = ""
    name: str = ""
    homepage: str = ""
    #: Explica de onde vêm os dados (aparece no /api/stores e no README)
    strategy: str = ""
    #: Timeout próprio (se None, usa o padrão das configurações)
    timeout_seconds: float | None = None

    def __init__(self, settings: Settings, http: HttpPolicy | None = None):
        self.settings = settings
        #: Cliente HTTP compartilhado (robots.txt, rate limit, detecção de bloqueio)
        self.http = http
        self.log = logging.getLogger(f"store.{self.slug}")

    def is_configured(self) -> bool:
        """Lojas que precisam de chave de API retornam False quando ela falta."""
        return True

    def not_configured_message(self) -> str:
        return f"{self.name} precisa de chaves de API no .env"

    @abc.abstractmethod
    async def search(self, query: SearchQuery) -> list[Offer]:
        """Busca ofertas na loja. Pode levantar StoreError (ou qualquer exceção)."""

    async def aclose(self) -> None:  # pragma: no cover - opcional
        return None
