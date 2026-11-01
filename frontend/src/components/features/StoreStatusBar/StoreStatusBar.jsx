import styles from './StoreStatusBar.module.css';
import StoreTag from '../../ui/StoreTag/StoreTag.jsx';
import Spinner from '../../ui/Spinner/Spinner.jsx';
import Icon from '../../ui/Icon/Icon.jsx';
import Tooltip from '../../ui/Tooltip/Tooltip.jsx';
import { cx } from '../../../utils/classNames.js';

function describe(info) {
  const viaHome = info.via_collector ? ' · via PC de casa' : '';
  switch (info.status) {
    case 'loading':
      return { text: 'buscando…', tone: 'loading' };
    case 'ok': {
      const n = info.offerCount ?? 0;
      const secs = info.elapsed_ms ? ` · ${(info.elapsed_ms / 1000).toFixed(1)}s` : '';
      return {
        text: `${n} ${n === 1 ? 'oferta' : 'ofertas'}${info.cached ? ' · do cache' : secs}${viaHome}`,
        tone: n ? 'ok' : 'empty',
        tip: info.total_found
          ? `${info.total_found} anúncios encontrados, ${info.excluded_count} descartados por não baterem com a busca.`
          : 'A loja não retornou anúncios para esta busca.',
      };
    }
    case 'not_configured':
      return { text: 'precisa de chave', tone: 'muted', tip: info.message };
    default:
      if (info.via_collector && /desligado/i.test(info.message || '')) {
        return {
          text: 'PC de casa desligado',
          tone: 'muted',
          tip: 'Esta loja bloqueia acessos da nuvem e é buscada pelo coletor no seu computador. Ligue o coletor para ver as ofertas dela.',
        };
      }
      return { text: 'indisponível no momento', tone: 'error', tip: info.message };
  }
}

const ICON = { ok: 'check', empty: 'info', muted: 'info', error: 'alert' };

/**
 * Situação de cada loja durante a busca ("KaBuM! · 12 ofertas", "Amazon · indisponível").
 *
 * @param {object} props
 * @param {Record<string, object>} props.stores  slug -> {name, status, message, offerCount, cached, elapsed_ms...}
 */
export default function StoreStatusBar({ stores }) {
  const entries = Object.entries(stores);
  if (!entries.length) return null;
  return (
    <ul className={styles.bar} aria-label="Situação das lojas">
      {entries.map(([slug, info]) => {
        const d = describe(info);
        return (
          <li key={slug}>
            <Tooltip content={d.tip} placement="bottom">
              <span className={cx(styles.pill, styles[d.tone])} tabIndex={d.tip ? 0 : undefined}>
                <StoreTag store={slug} name={info.name} size="sm" />
                <span className={styles.status}>
                  {d.tone === 'loading' ? <Spinner size="sm" label={`Buscando em ${info.name}`} /> : <Icon name={ICON[d.tone]} size="sm" />}
                  {d.text}
                </span>
              </span>
            </Tooltip>
          </li>
        );
      })}
    </ul>
  );
}
