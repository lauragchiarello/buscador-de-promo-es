import { useId } from 'react';
import styles from './Input.module.css';
import Icon from '../Icon/Icon.jsx';
import { cx } from '../../../utils/classNames.js';

/**
 * Campo de texto com rótulo, dica e erro.
 *
 * @param {object} props
 * @param {string} [props.label]       Rótulo acima do campo.
 * @param {string} [props.hint]        Texto de ajuda abaixo do campo.
 * @param {string} [props.error]       Mensagem de erro (deixa a borda vermelha).
 * @param {string} [props.icon]        Ícone à esquerda (nome do Icon).
 * @param {string} [props.prefix]      Texto fixo à esquerda (ex.: "R$").
 * @param {'sm'|'md'|'lg'} [props.size='md']
 * Demais props vão para o <input> (value, onChange, placeholder, type...).
 */
export default function Input({ label, hint, error, icon, prefix, size = 'md', className, id, ...rest }) {
  const autoId = useId();
  const inputId = id || autoId;
  const hintId = hint || error ? `${inputId}-hint` : undefined;
  return (
    <div className={cx(styles.field, className)}>
      {label && (
        <label className={styles.label} htmlFor={inputId}>
          {label}
        </label>
      )}
      <div className={cx(styles.control, styles[size], error && styles.hasError)}>
        {icon && <Icon name={icon} size="sm" className={styles.icon} />}
        {prefix && <span className={styles.prefix}>{prefix}</span>}
        <input id={inputId} className={styles.input} aria-invalid={!!error || undefined} aria-describedby={hintId} {...rest} />
      </div>
      {(error || hint) && (
        <p id={hintId} className={cx(styles.hint, error && styles.errorText)}>
          {error || hint}
        </p>
      )}
    </div>
  );
}
