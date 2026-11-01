import { useId, useState } from 'react';
import styles from './Tooltip.module.css';
import { cx } from '../../../utils/classNames.js';

/**
 * Dica que aparece ao passar o mouse ou focar no elemento.
 *
 * @param {object} props
 * @param {React.ReactNode} props.content   Texto da dica.
 * @param {'top'|'bottom'} [props.placement='top']
 * @param {React.ReactNode} props.children  Elemento que dispara a dica.
 */
export default function Tooltip({ content, placement = 'top', children }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  if (!content) return children;
  return (
    <span
      className={styles.wrapper}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      aria-describedby={open ? id : undefined}
    >
      {children}
      <span id={id} role="tooltip" className={cx(styles.tip, styles[placement], open && styles.open)}>
        {content}
      </span>
    </span>
  );
}
