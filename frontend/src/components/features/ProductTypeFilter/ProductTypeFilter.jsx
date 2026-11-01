import styles from './ProductTypeFilter.module.css';
import { cx } from '../../../utils/classNames.js';

/** Tipos de produto (o valor é a categoria entendida pelo backend). */
export const PRODUCT_TYPES = [
  { value: '', label: 'Todos' },
  { value: 'celular', label: 'Celulares' },
  { value: 'tablet', label: 'Tablets' },
  { value: 'notebook', label: 'Notebooks' },
  { value: 'desktop', label: 'PCs' },
  { value: 'monitor', label: 'Monitores' },
  { value: 'placa_video', label: 'Placas de vídeo' },
  { value: 'processador', label: 'Processadores' },
  { value: 'memoria', label: 'Memória RAM' },
  { value: 'armazenamento', label: 'SSD / HD' },
];

/**
 * Escolha do tipo de produto. Muda a própria busca nas lojas
 * (ex.: "samsung" + Celulares busca "celular samsung" e descarta tablets e capas).
 *
 * @param {object} props
 * @param {string} props.value               Tipo selecionado ('' = todos).
 * @param {(value: string) => void} props.onChange
 */
export default function ProductTypeFilter({ value, onChange }) {
  return (
    <div className={styles.bar} role="radiogroup" aria-label="Tipo de produto">
      {PRODUCT_TYPES.map((t) => {
        const active = value === t.value;
        return (
          <button
            key={t.value || 'todos'}
            type="button"
            role="radio"
            aria-checked={active}
            className={cx(styles.chip, active && styles.active)}
            onClick={() => onChange(t.value)}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
