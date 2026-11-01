"""Fast Shop — loja na plataforma VTEX (FastStore).

Usa a busca pública da VTEX (ver vtex.py). O robots.txt da Fast Shop só bloqueia
/busca/, checkout, conta e páginas de seguro; a API de busca é liberada.
"""

from __future__ import annotations

from .registry import register
from .vtex import VtexAdapter


@register
class FastShopAdapter(VtexAdapter):
    slug = "fastshop"
    name = "Fast Shop"
    homepage = "https://site.fastshop.com.br"
    strategy = "API pública de busca da VTEX (a mesma que o site usa), respeitando robots.txt"
    house_seller = "Fast Shop"
