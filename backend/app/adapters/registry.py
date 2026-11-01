"""Registro das lojas disponíveis."""

from __future__ import annotations

import importlib
import pkgutil

from ..config import Settings
from .base import StoreAdapter

_REGISTRY: dict[str, type[StoreAdapter]] = {}


def register(cls: type[StoreAdapter]) -> type[StoreAdapter]:
    """Decorador: `@register` em cima da classe do adaptador."""
    if not cls.slug:
        raise ValueError(f"{cls.__name__} precisa de um slug")
    _REGISTRY[cls.slug] = cls
    return cls


def _autoload() -> None:
    """Importa todos os módulos de app/adapters para os @register rodarem."""
    from . import __path__ as pkg_path

    skip = {"base", "registry", "http_policy", "robots", "utils"}
    for mod in pkgutil.iter_modules(pkg_path):
        if mod.name not in skip and not mod.name.startswith("_"):
            importlib.import_module(f"{__package__}.{mod.name}")


def available_adapters() -> dict[str, type[StoreAdapter]]:
    if not _REGISTRY:
        _autoload()
    return dict(_REGISTRY)


def build_adapters(settings: Settings, **deps) -> dict[str, StoreAdapter]:
    """Instancia os adaptadores habilitados (ENABLED_STORES no .env; vazio = todos)."""
    enabled = settings.enabled_list
    out: dict[str, StoreAdapter] = {}
    for slug, cls in available_adapters().items():
        if enabled and slug not in enabled:
            continue
        out[slug] = cls(settings, **deps)
    return out
