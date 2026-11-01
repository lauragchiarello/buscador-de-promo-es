import { useId } from 'react';
import styles from './Checkbox.module.css';
import Icon from '../Icon/Icon.jsx';
import { cx } from '../../../utils/classNames.js';

/**
 * Caixa de seleção com rótulo.
 *
 * @param {object} props
 * @param {string|React.ReactNode} props.label
 * @param {boolean} props.checked
 * @param {(checked: boolean) => void} props.onChange
 * @param {string} [props.description]  Texto menor abaixo do rótulo.
 * @param {boolean} [props.disabled=false]
 */
export default function Checkbox({ label, checked, onChange, description, disabled = false, className }) {
  const id = useId();
  return (
    <label className={cx(styles.wrapper, disabled && styles.disabled, className)} htmlFor={id}>
      <input
        id={id}
        type="checkbox"
        className={styles.native}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className={styles.box} aria-hidden="true">
        <Icon name="check" size="sm" className={styles.check} />
      </span>
      <span className={styles.text}>
        <span className={styles.label}>{label}</span>
        {description && <span className={styles.description}>{description}</span>}
      </span>
    </label>
  );
}
