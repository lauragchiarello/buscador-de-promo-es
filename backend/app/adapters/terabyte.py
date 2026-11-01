"""Terabyte — catálogo pelas páginas de categoria (acesso LIMITADO).

- O robots.txt proíbe a busca (/busca), mas libera /notebooks, /hardware, /pc-gamer...
- O site é protegido pela Cloudflare: às vezes responde com desafio anti-robô
  ("Just a moment..."). Nesse caso a loja aparece como indisponível. NÃO tentamos
  contornar.
- A paginação ("ver mais produtos") é um POST que a Cloudflare sempre desafia, então
  lemos só a PRIMEIRA página de cada categoria (~20-30 produtos, ordenados por
  mais vendidos). Por isso a cobertura da Terabyte é parcial.

Cada produto da listagem é um bloco `.product-item` com:
  link /produto/<id>/<slug>, <h2> título, imagem, "De: R$ X" (riscado),
  "R$ Y à vista no Pix", "12x de R$ Z sem juros". Sem estoque = botão "Avise-me".
"""

from __future__ import annotations

import html as html_lib
import re

from ..schemas import Offer
from .base import StoreError
from .catalog_base import CatalogAdapter
from .registry import register
from .utils import detect_condition, discount, parse_brl

BASE = "https://www.terabyteshop.com.br"

_ITEM_SPLIT = re.compile(r'<div class="product-item-frame">')
_LINK = re.compile(r'href="https://www\.terabyteshop\.com\.br/produto/(\d+)/([^"]+)"')
_TITLE = re.compile(r"<h2>(.*?)</h2>", re.S)
_IMG = re.compile(r'<img[^>]+class="image-thumbnail"[^>]+src="([^"]+)"|<img[^>]+src="([^"]+)"[^>]+class="image-thumbnail"')
_OLD = re.compile(r'product-item__old-price.*?<span>\s*(R\$\s*[\d.,]+)\s*</span>', re.S)
_NEW = re.compile(r'product-item__new-price.*?<span>\s*(R\$\s*[\d.,]+)\s*</span>', re.S)
_INST = re.compile(r'product-item__juros.*?<span>\s*(\d{1,2})x\s*</span>.*?<span>\s*(R\$\s*[\d.,]+)\s*</span\s*>(.*?)</div>', re.S)


def parse_terabyte_listing(page: str) -> list[Offer]:
    """Extrai as ofertas de uma página de categoria."""
    if "product-item" not in page:
        if "just a moment" in page[:3000].lower():
            raise StoreError("A Terabyte pediu verificação anti-robô", detail="desafio Cloudflare na listagem")
        return []
    offers: list[Offer] = []
    for block in _ITEM_SPLIT.split(page)[1:]:
        if "tbt_avicon" in block or "Avise-me" in block:  # sem estoque
            continue
        link = _LINK.search(block)
        title = _TITLE.search(block)
        new = _NEW.search(block)
        if not (link and title and new):
            continue
        name = html_lib.unescape(re.sub(r"\s+", " ", title.group(1))).strip()
        price_cash = parse_brl(new.group(1))
        old = _OLD.search(block)
        price_list = parse_brl(old.group(1)) if old else None
        inst = _INST.search(block)
        n_inst = inst_value = inst_total = None
        if inst:
            n_inst, inst_value = int(inst.group(1)), parse_brl(inst.group(2))
            inst_total = round(n_inst * inst_value, 2) if inst_value else None
        img = _IMG.search(block)
        offers.append(
            Offer(
                store="terabyte",
                store_name="Terabyte",
                external_id=link.group(1),
                title=name,
                url=f"{BASE}/produto/{link.group(1)}/{link.group(2)}",
                image_url=(img.group(1) or img.group(2)) if img else None,
                price_cash=price_cash,
                price_installment=inst_total,
                installments=n_inst if n_inst and n_inst > 1 else None,
                installment_value=inst_value if n_inst and n_inst > 1 else None,
                price_list=price_list if price_list and price_cash and price_list > price_cash else None,
                discount_pct=discount(price_list, price_cash),
                seller="Terabyte",
                is_official=True,  # a Terabyte vende os próprios produtos
                condition=detect_condition(name),
            )
        )
    return offers


@register
class TerabyteAdapter(CatalogAdapter):
    slug = "terabyte"
    name = "Terabyte"
    homepage = BASE
    strategy = "Catálogo das páginas de categoria (1ª página de cada; atualizado a cada 6 h)"

    category_paths = {
        "notebook": ["/notebooks"],
        "desktop": ["/pc-gamer"],
        "placa_video": [
            "/hardware/placas-de-video/nvidia-geforce",
            "/hardware/placas-de-video/amd-radeon",
            "/hardware/placas-de-video/intel-arc",
        ],
        "processador": ["/hardware/processadores/intel", "/hardware/processadores/amd-ryzen"],
        "memoria": ["/hardware/memorias/ddr5", "/hardware/memorias/ddr4", "/hardware/memorias/memoria-p-notebook"],
        "armazenamento": ["/hardware/hard-disk/ssd"],
        "placa_mae": [
            "/hardware/placas-mae/lga-1700-intel",
            "/hardware/placas-mae/lga-1851-intel",
            "/hardware/placas-mae/am5-amd-ryzen",
            "/hardware/placas-mae/am4-amd-ryzen",
        ],
        "monitor": ["/monitores"],
        "*": ["/notebooks", "/pc-gamer"],
    }

    async def fetch_path(self, path: str) -> list[Offer]:
        if self.http is None:
            raise StoreError("Cliente HTTP não configurado")
        resp = await self.http.get(f"{BASE}{path}")
        return parse_terabyte_listing(resp.text)
