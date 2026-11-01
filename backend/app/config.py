"""Configurações lidas do ambiente / arquivo .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR.parent / ".env", BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'app.db').as_posix()}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    # Cache e limites
    cache_ttl_minutes: int = 30
    store_timeout_seconds: float = 25.0
    request_delay_min: float = 1.5
    request_delay_max: float = 4.0
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )

    # Lojas habilitadas (slugs separados por vírgula). Vazio = todas registradas.
    enabled_stores: str = ""

    # Mercado Livre (https://developers.mercadolivre.com.br/devcenter)
    ml_client_id: str = ""
    ml_client_secret: str = ""

    # Amazon Creators API (requer Associados)
    amazon_client_id: str = ""
    amazon_client_secret: str = ""
    amazon_partner_tag: str = ""
    amazon_marketplace: str = "www.amazon.com.br"

    # Shopee Afiliados (requer aprovação)
    shopee_app_id: str = ""
    shopee_app_secret: str = ""

    # Lomadee — rede de afiliados (https://docs.lomadee.com.br)
    lomadee_api_key: str = ""
    lomadee_base_url: str = "https://api.lomadee.com.br"
    lomadee_price_in_cents: bool = True

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def enabled_list(self) -> list[str]:
        return [s.strip() for s in self.enabled_stores.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
