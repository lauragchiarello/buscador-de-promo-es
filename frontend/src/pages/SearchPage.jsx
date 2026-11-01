import { useState } from 'react';
import styles from './SearchPage.module.css';
import SearchBar from '../components/ui/SearchBar/SearchBar.jsx';
import Button from '../components/ui/Button/Button.jsx';
import ErrorMessage from '../components/ui/ErrorMessage/ErrorMessage.jsx';
import Modal from '../components/ui/Modal/Modal.jsx';
import FilterPanel from '../components/features/FilterPanel/FilterPanel.jsx';
import OfferList from '../components/features/OfferList/OfferList.jsx';
import SortControl from '../components/features/SortControl/SortControl.jsx';
import StoreStatusBar from '../components/features/StoreStatusBar/StoreStatusBar.jsx';
import QuerySummary from '../components/features/QuerySummary/QuerySummary.jsx';
import ProductTypeFilter from '../components/features/ProductTypeFilter/ProductTypeFilter.jsx';
import { useSearch } from '../hooks/useSearch.js';
import { useStores } from '../hooks/useStores.js';
import { useDebounce } from '../hooks/useDebounce.js';
import { DEFAULT_FILTERS, useFilteredOffers } from '../hooks/useFilteredOffers.js';

const EXAMPLES = ['notebook 32gb ram i7 13th', 'iphone 15 128gb', 'samsung tab', 'placa de video rtx 4060'];

/** Tela principal: campo de busca, filtros e resultados que chegam loja por loja. */
export default function SearchPage() {
  const [text, setText] = useState('');
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [sort, setSort] = useState('price');
  const [productType, setProductType] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const { state, search } = useSearch();
  const { stores, error: storesError } = useStores();

  const debouncedFilters = useDebounce(filters, 300);
  const { offers, bestKey, hiddenCount } = useFilteredOffers(state.offers, debouncedFilters, sort);
  const loading = state.status === 'loading';
  const started = state.status !== 'idle';

  const run = (q, opts = {}) => {
    setText(q);
    search(q, { category: productType, ...opts });
  };

  // Trocar o tipo de produto refaz a busca atual com o novo tipo.
  const changeType = (value) => {
    setProductType(value);
    if (state.query) search(state.query, { category: value });
  };

  const filterPanel = (
    <FilterPanel filters={filters} onChange={setFilters} stores={stores} onClear={() => setFilters(DEFAULT_FILTERS)} />
  );

  if (!started) {
    return (
      <section className={styles.hero}>
        <h1 className={styles.heroTitle}>Ache o preço certo, do jeito que você pediu</h1>
        <p className={styles.heroText}>
          Digite exatamente o que procura. A gente busca nas lojas, descarta o que não bate e mostra o mais barato primeiro.
        </p>
        <div className={styles.heroSearch}>
          <SearchBar value={text} onChange={setText} onSubmit={run} placeholder="ex.: notebook 32gb ram i7 13th" autoFocus />
          <ProductTypeFilter value={productType} onChange={setProductType} />
        </div>
        <div className={styles.examples}>
          <span className={styles.examplesLabel}>Experimente:</span>
          {EXAMPLES.map((ex) => (
            <Button key={ex} variant="secondary" size="sm" onClick={() => run(ex)}>
              {ex}
            </Button>
          ))}
        </div>
        {storesError && (
          <div className={styles.heroError}>
            <ErrorMessage title="O servidor não respondeu">
              Confira se o backend está rodando (veja o README). Detalhe: {storesError.message}
            </ErrorMessage>
          </div>
        )}
      </section>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.searchRow}>
        <SearchBar value={text} onChange={setText} onSubmit={run} loading={loading} />
        <ProductTypeFilter value={productType} onChange={changeType} />
      </div>

      <div className={styles.layout}>
        <div className={styles.sidebar}>{filterPanel}</div>

        <section className={styles.results} aria-live="polite">
          <QuerySummary specs={state.specs} />
          <StoreStatusBar stores={state.stores} />

          {state.error && (
            <ErrorMessage title="A busca foi interrompida" onRetry={() => run(state.query, { fresh: true })} tone="warning">
              {state.error.message}
            </ErrorMessage>
          )}

          <div className={styles.toolbar}>
            <p className={styles.count}>
              {loading && !offers.length
                ? 'Procurando nas lojas…'
                : `${offers.length} ${offers.length === 1 ? 'oferta compatível' : 'ofertas compatíveis'}${loading ? ' (ainda chegando…)' : ''}`}
            </p>
            <div className={styles.toolbarActions}>
              <span className={styles.mobileOnly}>
                <Button variant="secondary" size="sm" icon="sliders" onClick={() => setFiltersOpen(true)}>
                  Filtros
                </Button>
              </span>
              <SortControl value={sort} onChange={setSort} />
              {state.status === 'done' && (
                <Button variant="ghost" size="sm" icon="refresh" onClick={() => run(state.query, { fresh: true })} title="Buscar de novo ignorando o cache">
                  Atualizar
                </Button>
              )}
            </div>
          </div>

          <OfferList
            offers={offers}
            bestKey={bestKey}
            loading={loading}
            hiddenCount={hiddenCount}
            onClearFilters={() => setFilters(DEFAULT_FILTERS)}
          />
        </section>
      </div>

      <Modal open={filtersOpen} onClose={() => setFiltersOpen(false)} title="Filtros" footer={<Button onClick={() => setFiltersOpen(false)}>Ver ofertas</Button>}>
        {filterPanel}
      </Modal>
    </div>
  );
}
