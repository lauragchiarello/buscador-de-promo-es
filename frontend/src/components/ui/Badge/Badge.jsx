import styles from './Badge.module.css';
import Icon from '../Icon/Icon.jsx';
import { cx } from '../../../utils/classNames.js';

/**
 * Etiqueta curta ("Loja oficial", "-25%", "Melhor oferta").
 *
 * @param {object} props
 * @param {'neutral'|'accent'|'deal'|'success'|'warning'|'error'} [props.tone='neutral']
 * @param {'soft'|'solid'} [props.variant='soft']
 * @param {string} [props.icon]   Nome de um ícone à esquerda.
 * @param {'sm'|'md'} [props.size='md']
 * @param {string} [props.title]  Dica nativa ao passar o mouse.
 * @param {React.ReactNode} props.children
 */
export default function Badge({ tone = 'neutral', variant = 'soft', icon, size = 'md', className, children, ...rest }) {
  return (
    <span className={cx(styles.badge, styles[tone], styles[variant], styles[size], className)} {...rest}>
      {icon && <Icon name={icon} size="sm" />}
      {children}
    </span>
  );
}
