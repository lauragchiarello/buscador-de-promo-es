import { useId } from 'react';
import styles from './Select.module.css';
import Icon from '../Icon/Icon.jsx';
import { cx } from '../../../utils/classNames.js';

/**
 * Lista de opções (select nativo estilizado).
 *
 * @param {object} props
 * @param {string} [props.label]
 * @param {{value: string, label: string}[]} props.options
 * @param {string} props.value
 * @param {(value: string) => void} props.onChange
 * @param {'sm'|'md'} [props.size='md']
 * @param {boolean} [props.inlineLabel=false]  Rótulo ao lado (ex.: "Ordenar por").
 */
export default function Select({ label, options, value, onChange, size = 'md', inlineLabel = false, className, id, ...rest }) {
  const autoId = useId();
  const selectId = id || autoId;
  return (
    <div className={cx(styles.field, inlineLabel && styles.inline, className)}>
      {label && (
        <label className={styles.label} htmlFor={selectId}>
          {label}
        </label>
      )}
      <div className={cx(styles.control, styles[size])}>
        <select id={selectId} className={styles.select} value={value} onChange={(e) => onChange(e.target.value)} {...rest}>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <Icon name="chevron-down" size="sm" className={styles.chevron} />
      </div>
    </div>
  );
}
