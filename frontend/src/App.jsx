import { useEffect, useState } from 'react';
import styles from './App.module.css';
import Icon from './components/ui/Icon/Icon.jsx';
import { ToastProvider } from './components/ui/Toast/Toast.jsx';
import SearchPage from './pages/SearchPage.jsx';
import ComingSoonPage from './pages/ComingSoonPage.jsx';
import UiShowcasePage from './pages/UiShowcasePage.jsx';
import { cx } from './utils/classNames.js';

const NAV = [
  { id: 'busca', label: 'Busca', icon: 'search' },
  { id: 'monitorados', label: 'Monitorados', icon: 'bell' },
  { id: 'historico', label: 'Histórico', icon: 'chart' },
];

const IS_DEV = import.meta.env.DEV;

/** A página do design system abre com #ui na URL (só em desenvolvimento). */
function pageFromHash() {
  const h = window.location.hash.replace('#', '');
  if (h === 'ui' && IS_DEV) return 'ui';
  return NAV.some((n) => n.id === h) ? h : 'busca';
}

export default function App() {
  const [page, setPage] = useState(pageFromHash);

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const go = (id) => {
    window.location.hash = id === 'busca' ? '' : id;
    setPage(id);
  };

  return (
    <ToastProvider>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <button type="button" className={styles.brand} onClick={() => go('busca')}>
            <span className={styles.logo} aria-hidden="true">
              <Icon name="search" size="sm" />
            </span>
            <span className={styles.brandName}>Buscador de Promoções</span>
          </button>
          <nav className={styles.nav} aria-label="Principal">
            {NAV.map((n) => (
              <button
                key={n.id}
                type="button"
                className={cx(styles.navItem, page === n.id && styles.active)}
                onClick={() => go(n.id)}
                aria-current={page === n.id ? 'page' : undefined}
              >
                <Icon name={n.icon} size="sm" />
                <span className={styles.navLabel}>{n.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className={styles.main}>
        {/* A busca fica montada ao trocar de aba, para não perder os resultados. */}
        <div hidden={page !== 'busca'}>
          <SearchPage />
        </div>
        {page === 'monitorados' && (
          <ComingSoonPage
            icon="bell"
            title="Produtos monitorados chegam na fase 3"
            description="Você vai poder escolher um produto e um preço-alvo, e a gente avisa quando ele cair abaixo disso."
          />
        )}
        {page === 'historico' && (
          <ComingSoonPage
            icon="chart"
            title="Histórico de preços chega na fase 3"
            description="Cada busca já está sendo salva. Na fase 3 você vai ver o gráfico de preço de cada produto ao longo do tempo."
          />
        )}
        {page === 'ui' && <UiShowcasePage />}
      </main>

      <footer className={styles.footer}>
        <span>Preços coletados das lojas; confira sempre no site antes de comprar.</span>
        {IS_DEV && (
          <a href="#ui" className={styles.devLink}>
            <Icon name="palette" size="sm" /> padrão visual
          </a>
        )}
      </footer>
    </ToastProvider>
  );
}
