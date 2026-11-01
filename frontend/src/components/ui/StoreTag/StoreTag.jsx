import styles from './StoreTag.module.css';
import { cx } from '../../../utils/classNames.js';

/**
 * Identificação da loja: "logo" com as iniciais na cor da marca + nome.
 * (Não usamos logos oficiais para evitar problemas de marca registrada.)
 *
 * Para adicionar uma loja: inclua uma entrada em STORES e a cor em StoreTag.module.css.
 *
 * @param {object} props
 * @param {string} props.store        Slug da loja (kabum, mercadolivre, amazon...).
 * @param {string} [props.name]       Nome a exibir (se não informado, usa o padrão).
 * @param {'sm'|'md'} [props.size='md']
 * @param {boolean} [props.showName=true]
 */
const STORES = {
  kabum: { name: 'KaBuM!', initials: 'K!' },
  mercadolivre: { name: 'Mercado Livre', initials: 'ML' },
  amazon: { name: 'Amazon', initials: 'a' },
  shopee: { name: 'Shopee', initials: 'S' },
  pichau: { name: 'Pichau', initials: 'P' },
  fastshop: { name: 'Fast Shop', initials: 'FS' },
  terabyte: { name: 'Terabyte', initials: 'TB' },
};

export default function StoreTag({ store, name, size = 'md', showName = true }) {
  const info = STORES[store] || { name: name || store, initials: (name || store || '?').slice(0, 2).toUpperCase() };
  return (
    <span className={cx(styles.tag, styles[size])}>
      <span className={cx(styles.logo, styles[store] || styles.default)} aria-hidden="true">
        {info.initials}
      </span>
      {showName && <span className={styles.name}>{name || info.name}</span>}
    </span>
  );
}
