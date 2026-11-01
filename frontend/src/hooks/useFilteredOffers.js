import { useMemo } from 'react';

export const DEFAULT_FILTERS = {
  minPrice: '',
  maxPrice: '',
  stores: [], // vazio = todas
  officialOnly: false,
  includeUsed: false,
};

const priceOf = (o) => o.price_cash ?? o.price_installment ?? Infinity;

const SORTERS = {
  price: (a, b) => priceOf(a) - priceOf(b),
  discount: (a, b) => (b.discount_pct || 0) - (a.discount_pct || 0) || priceOf(a) - priceOf(b),
  match: (a, b) => b.match_score - a.match_score || priceOf(a) - priceOf(b),
};

/**
 * Aplica filtros e ordenação nas ofertas recebidas (sem nova busca no servidor)
 * e marca a melhor oferta (menor preço entre as bem compatíveis).
 */
export function useFilteredOffers(offers, filters, sort) {
  return useMemo(() => {
    const min = parseFloat(filters.minPrice) || null;
    const max = parseFloat(filters.maxPrice) || null;
    const list = offers.filter((o) => {
      const p = priceOf(o);
      if (min && p < min) return false;
      if (max && p > max) return false;
      if (filters.stores.length && !filters.stores.includes(o.store)) return false;
      if (filters.officialOnly && o.is_official === false) return false;
      if (!filters.includeUsed && o.condition !== 'novo') return false;
      return true;
    });
    list.sort(SORTERS[sort] || SORTERS.price);

    const best = [...list].filter((o) => o.match_score >= 70 && o.condition === 'novo').sort(SORTERS.price)[0];
    const hiddenCount = offers.length - list.length;
    return { offers: list, bestKey: best ? `${best.store}:${best.external_id}` : null, hiddenCount };
  }, [offers, filters, sort]);
}
