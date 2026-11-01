"""Detecção de acessórios e peças que aparecem misturados nas buscas."""

from __future__ import annotations

import re

_PRODUCTS = r"(?:notebook|laptop|macbook|chromebook|tablet|ipad|pc|computador)"
# "para notebook", "p notebook", "compativel com notebook", "reposicao notebook"
_FOR_PRODUCT = re.compile(
    rf"\b(?:para|p|pra|compativel com|compativel|serve em|serve no|reposicao|substituicao|refil)\s(?:o\s|a\s|seu\s|sua\s)?(?:\w+\s)?{_PRODUCTS}\b"
)
_FIRST_PRODUCT = re.compile(rf"\b{_PRODUCTS}\b")

# Termos que, quando presentes, indicam peça/acessório mesmo com a categoria certa
_PART_HINTS = re.compile(
    r"\b(?:peca|pecas|retirada de pecas|sucata|defeito|com defeito|nao liga|placa mae do|"
    r"carcaca|dobradica|tela lcd|tela led para|flat cable|teclado para)\b"
)


def is_accessory(normalized_title: str, category: str | None) -> bool:
    """True se o anúncio é acessório/peça, e não o produto em si.

    Recebe o título JÁ normalizado e a categoria detectada (primeira palavra de categoria).
    """
    if category == "acessorio":
        return True
    if _PART_HINTS.search(normalized_title):
        return True
    # A primeira vez que "notebook" aparece é depois de "para"? Então é acessório.
    first = _FIRST_PRODUCT.search(normalized_title)
    for m in _FOR_PRODUCT.finditer(normalized_title):
        if first and m.start() <= first.start() <= m.end():
            return category not in ("notebook", "desktop", "tablet") or m.start() == 0
    return False
