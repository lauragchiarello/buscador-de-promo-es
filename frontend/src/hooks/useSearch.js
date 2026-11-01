import { useCallback, useEffect, useReducer, useRef } from 'react';
import { streamSearch } from '../services/api.js';

const initialState = {
  status: 'idle', // idle | loading | done | error
  query: '',
  category: '', // tipo de produto usado na busca atual
  specs: null,
  terms: [],
  stores: {}, // slug -> {name, status, message, cached, elapsed_ms, total_found, excluded_count, excluded_samples}
  offers: [],
  error: null,
  startedAt: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'start':
      return { ...initialState, status: 'loading', query: action.query, category: action.category || '', startedAt: Date.now() };
    case 'query':
      return { ...state, specs: action.data.specs, terms: action.data.terms };
    case 'store_status':
      return { ...state, stores: { ...state.stores, [action.data.store]: { name: action.data.name, status: 'loading' } } };
    case 'store_result': {
      const { offers = [], type: _t, ...info } = action.data;
      return {
        ...state,
        stores: { ...state.stores, [info.store]: { ...info, offerCount: offers.length } },
        offers: [...state.offers, ...offers],
      };
    }
    case 'done':
      return { ...state, status: 'done' };
    case 'error':
      // Se algumas lojas já responderam, mantemos o que chegou e só avisamos.
      return { ...state, status: Object.keys(state.stores).length ? 'done' : 'error', error: action.error };
    case 'reset':
      return initialState;
    default:
      return state;
  }
}

/**
 * Executa buscas com streaming e guarda o estado (lojas, ofertas, specs entendidas).
 *
 * @returns {{state: typeof initialState, search: (query: string, opts?: object) => void, reset: () => void}}
 */
export function useSearch() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const cancelRef = useRef(null);

  const search = useCallback((query, opts = {}) => {
    cancelRef.current?.();
    dispatch({ type: 'start', query, category: opts.category });
    // Pedimos usados também; os filtros são aplicados na tela, sem buscar de novo.
    cancelRef.current = streamSearch(
      query,
      { includeUsed: true, fresh: opts.fresh, category: opts.category },
      {
        onQuery: (data) => dispatch({ type: 'query', data }),
        onStoreStatus: (data) => dispatch({ type: 'store_status', data }),
        onStoreResult: (data) => dispatch({ type: 'store_result', data }),
        onDone: () => dispatch({ type: 'done' }),
        onError: (error) => dispatch({ type: 'error', error }),
      },
    );
  }, []);

  const reset = useCallback(() => {
    cancelRef.current?.();
    dispatch({ type: 'reset' });
  }, []);

  useEffect(() => () => cancelRef.current?.(), []);

  return { state, search, reset };
}
