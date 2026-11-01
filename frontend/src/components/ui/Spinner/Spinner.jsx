import styles from './Spinner.module.css';
import { cx } from '../../../utils/classNames.js';

/**
 * Indicador de carregamento circular.
 *
 * @param {object} props
 * @param {'sm'|'md'|'lg'} [props.size='md']
 * @param {string} [props.label='Carregando']  Texto para leitores de tela.
 * @param {boolean} [props.inverse=false]      Usa cor clara (para fundos escuros/coloridos).
 */
export default function Spinner({ size = 'md', label = 'Carregando', inverse = false }) {
  return (
    <span className={cx(styles.spinner, styles[size], inverse && styles.inverse)} role="status">
      <span className="visually-hidden">{label}</span>
    </span>
  );
}
