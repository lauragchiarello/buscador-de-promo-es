/**
 * Todas as chamadas ao backend ficam aqui (fetch nativo + EventSource nativo).
 *
 * Em desenvolvimento, o Vite encaminha /api para o backend (ver vite.config.js).
 * Para apontar para outro servidor, defina VITE_API_URL (ex.: http://localhost:8010).
 */

const BASE = import.meta.env.VITE_API_URL || '';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let resp;
  try {
    resp = await fetch(`${BASE}${path}`, {
      headers: { Accept: 'application/json', ...(options.headers || {}) },
      ...options,
    });
  } catch {
    throw new ApiError('Não consegui falar com o servidor. Ele está rodando?', 0);
  }
  if (!resp.ok) {
    let detail = '';
    try {
      detail = (await resp.json()).detail;
    } catch {
      /* resposta sem JSON */
    }
    throw new ApiError(typeof detail === 'string' && detail ? detail : `Erro ${resp.status} no servidor`, resp.status);
  }
  return resp.json();
}

function toParams(query, filters = {}) {
  const params = new URLSearchParams({ q: query });
  if (filters.stores?.length) params.set('stores', filters.stores.join(','));
  if (filters.minPrice) params.set('min_price', filters.minPrice);
  if (filters.maxPrice) params.set('max_price', filters.maxPrice);
  if (filters.officialOnly) params.set('official_only', 'true');
  if (filters.includeUsed) params.set('include_used', 'true');
  if (filters.fresh) params.set('fresh', 'true');
  if (filters.category) params.set('category', filters.category);
  return params.toString();
}

/** Lojas disponíveis: [{slug, name, configured, message, strategy}] */
export function getStores() {
  return request('/api/stores');
}

/** Como o backend entendeu o texto: {specs, terms} */
export function parseQuery(query) {
  return request(`/api/parse?q=${encodeURIComponent(query)}`);
}

/** Histórico de preços de um anúncio. */
export function getHistory(listingId, days = 180) {
  return request(`/api/history/${listingId}?days=${days}`);
}

export function clearCache() {
  return request('/api/cache', { method: 'DELETE' });
}

/**
 * Busca com resultados chegando aos poucos (Server-Sent Events).
 *
 * @param {string} query
 * @param {object} filters   {stores, minPrice, maxPrice, officialOnly, includeUsed, fresh, category}
 * @param {object} handlers  {onQuery, onStoreStatus, onStoreResult, onDone, onError}
 * @returns {() => void}     Função para cancelar a busca.
 */
export function streamSearch(query, filters, handlers) {
  const source = new EventSource(`${BASE}/api/search/stream?${toParams(query, filters)}`);
  let finished = false;

  const listen = (type, fn) =>
    source.addEventListener(type, (ev) => {
      try {
        fn?.(JSON.parse(ev.data));
      } catch (err) {
        console.error('Evento inválido do servidor', type, err);
      }
    });

  listen('query', handlers.onQuery);
  listen('store_status', handlers.onStoreStatus);
  listen('store_result', handlers.onStoreResult);
  listen('done', (data) => {
    finished = true;
    source.close();
    handlers.onDone?.(data);
  });

  source.onerror = () => {
    if (finished) return;
    finished = true;
    source.close();
    handlers.onError?.(new ApiError('A conexão com o servidor caiu no meio da busca.', 0));
  };

  return () => {
    finished = true;
    source.close();
  };
}
