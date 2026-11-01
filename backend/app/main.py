"""Ponto de entrada da API: `uvicorn app.main:app --reload`."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .adapters.http_policy import HttpPolicy
from .adapters.registry import build_adapters
from .api.routes import router
from .config import BASE_DIR, get_settings
from .logging_setup import setup_logging
from .services.orchestrator import SearchOrchestrator

settings = get_settings()
setup_logging(settings.log_level)
log = logging.getLogger("app")


def run_migrations() -> None:
    """Aplica as migrações do Alembic ao subir (cria o banco SQLite na primeira vez)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BASE_DIR / "alembic.ini"))
    cfg.attributes["skip_logging"] = True  # mantém nosso formato de log
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))  # configparser usa "%"
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    http = HttpPolicy(settings)
    adapters = build_adapters(settings, http=http)
    app.state.http = http
    app.state.adapters = adapters
    app.state.orchestrator = SearchOrchestrator(settings, adapters)
    log.info("Lojas ativas: %s", ", ".join(f"{a.name}{'' if a.is_configured() else ' (sem chave)'}" for a in adapters.values()))
    yield
    await http.aclose()


app = FastAPI(title="Buscador de Promoções", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_list, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)

# Em produção (Render), o mesmo serviço entrega as telas do React já compiladas
# (frontend/dist). Em desenvolvimento quem serve o frontend é o Vite.
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    log.info("Servindo o frontend de %s", FRONTEND_DIST)
