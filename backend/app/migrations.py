"""Aplica as migrações do Alembic (usado pelo site e pelo coletor ao iniciar)."""

from __future__ import annotations

from .config import BASE_DIR, get_settings


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.attributes["skip_logging"] = True  # mantém nosso formato de log
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
    command.upgrade(cfg, "head")
