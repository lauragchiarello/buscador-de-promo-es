"""Base para lojas "de catálogo".

Usada quando o robots.txt da loja proíbe a página de busca, mas libera as
páginas de categoria. Funcionamento:
1. A busca descobre quais categorias interessam (pela categoria da busca: notebook,
   placa de vídeo...).
2. Categorias lidas há mais de `refresh_hours` são lidas de novo (com rate limit).
3. As ofertas guardadas dessas categorias são devolvidas; o filtro de
   compatibilidade faz o resto, como em qualquer loja.
Se a loja bloquear a atualização, usamos o catálogo antigo (o card mostra a idade
do preço). Se nunca conseguimos ler, a loja aparece como indisponível.

Para uma nova loja: herde, preencha `category_paths` e implemente `fetch_path()`.
"""

from __future__ import annotations

import abc
import asyncio

from ..schemas import Offer, SearchQuery
from ..services import catalog
from .base import StoreAdapter, StoreError


class CatalogAdapter(StoreAdapter):
    #: categoria da busca -> caminhos de categoria na loja. "*" = quando a busca não tem categoria.
    category_paths: dict[str, list[str]] = {}
    refresh_hours: float = 6.0
    timeout_seconds = 60.0

    def paths_for(self, query: SearchQuery) -> list[str]:
        cat = query.specs.get("category")
        if cat in self.category_paths:
            return self.category_paths[cat]
        if query.specs.get("gpu") and "placa_video" in self.category_paths:
            return list(dict.fromkeys(self.category_paths.get("*", []) + self.category_paths["placa_video"]))
        return self.category_paths.get("*", [])

    @abc.abstractmethod
    async def fetch_path(self, path: str) -> list[Offer]:
        """Lê UMA página de categoria e devolve as ofertas dela."""

    async def search(self, query: SearchQuery) -> list[Offer]:
        paths = self.paths_for(query)
        if not paths:
            return []
        errors: list[StoreError] = []
        for path in paths:
            age = await asyncio.to_thread(catalog.page_age_hours, self.slug, path)
            if age is not None and age < self.refresh_hours:
                continue
            try:
                offers = await self.fetch_path(path)
            except StoreError as exc:
                errors.append(exc)
                self.log.warning("não consegui atualizar %s: %s", path, exc.detail)
                if exc.status == "blocked":
                    break  # bloqueou: não insistir nas outras categorias
                continue
            await asyncio.to_thread(catalog.save_page, self.slug, path, offers)
            self.log.info("catálogo %s atualizado: %d itens", path, len(offers))

        items = await asyncio.to_thread(catalog.load_items, self.slug, paths)
        if not items and errors:
            raise errors[0]
        if errors:
            self.log.warning("usando catálogo salvo (%d itens) porque a atualização falhou", len(items))
        return items
