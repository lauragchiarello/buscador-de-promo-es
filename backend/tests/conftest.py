"""Configuração dos testes: banco SQLite temporário e helpers."""

import json
import os
import tempfile
from pathlib import Path

# Precisa vir ANTES de importar a aplicação (o engine é criado no import).
_TMP = tempfile.mkdtemp(prefix="buscador-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP, 'test.db').as_posix()}"
os.environ["REQUEST_DELAY_MIN"] = "0"
os.environ["REQUEST_DELAY_MAX"] = "0"
os.environ["ML_CLIENT_ID"] = ""
os.environ["ML_CLIENT_SECRET"] = ""

import pytest  # noqa: E402

from app import models  # noqa: E402,F401
from app.config import Settings  # noqa: E402
from app.db import Base, engine  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"

Base.metadata.create_all(engine)


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def fixture_json(name: str):
    return json.loads(fixture_text(name))


@pytest.fixture
def settings() -> Settings:
    return Settings(request_delay_min=0, request_delay_max=0, ml_client_id="", ml_client_secret="")
