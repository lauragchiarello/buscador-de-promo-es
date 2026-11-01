"""Funções auxiliares comuns aos adaptadores."""

from __future__ import annotations

import re

from ..parsing.normalize import normalize

_BRL = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)")


def parse_brl(text: str | None) -> float | None:
    """'R$ 1.234,56' -> 1234.56"""
    if not text:
        return None
    m = _BRL.search(text.replace(" ", " "))
    if not m:
        return None
    return float(m.group(1).replace(".", "").replace(",", "."))


def parse_installments(text: str | None) -> tuple[int | None, float | None]:
    """'10x de R$ 894,90' -> (10, 894.90)"""
    if not text:
        return None, None
    m = re.search(r"(\d{1,2})\s*x\s*(?:de\s*)?R?\$?\s*([\d.,]+)", text, re.I)
    if not m:
        return None, None
    return int(m.group(1)), parse_brl(m.group(2))


def discount(price_list: float | None, price: float | None) -> float | None:
    if not price_list or not price or price_list <= price:
        return None
    return round(100 * (price_list - price) / price_list, 1)


def detect_condition(title: str) -> str:
    t = normalize(title)
    if re.search(r"\b(recondicionado|recondicionada|refurbished|remanufaturado|open ?box|vitrine)\b", t):
        return "recondicionado"
    if re.search(r"\b(usado|usada|seminovo|seminova|semi novo)\b", t):
        return "usado"
    return "novo"


def slugify_term(term: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize(term)).strip("-")
