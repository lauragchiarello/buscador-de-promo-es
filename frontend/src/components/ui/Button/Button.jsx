import styles from './Button.module.css';
import Spinner from '../Spinner/Spinner.jsx';
import Icon from '../Icon/Icon.jsx';
import { cx } from '../../../utils/classNames.js';

/**
 * Botão padrão do app.
 *
 * @param {object} props
 * @param {'primary'|'secondary'|'ghost'} [props.variant='primary']
 * @param {'sm'|'md'|'lg'} [props.size='md']
 * @param {boolean} [props.loading=false]   Mostra spinner e bloqueia cliques.
 * @param {boolean} [props.disabled=false]
 * @param {string} [props.icon]             Nome de um ícone (ver Icon) à esquerda do texto.
 * @param {string} [props.iconRight]        Ícone à direita do texto.
 * @param {boolean} [props.fullWidth=false] Ocupa toda a largura disponível.
 * @param {string} [props.href]             Se informado, renderiza um link com cara de botão.
 * @param {'button'|'submit'} [props.type='button']
 * @param {React.ReactNode} props.children
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  icon,
  iconRight,
  fullWidth = false,
  href,
  type = 'button',
  className,
  children,
  ...rest
}) {
  const classes = cx(
    styles.button,
    styles[variant],
    styles[size],
    fullWidth && styles.fullWidth,
    loading && styles.loading,
    !children && styles.iconOnly,
    className,
  );
  const iconSize = size === 'lg' ? 'md' : 'sm';
  const content = (
    <>
      {loading ? <Spinner size="sm" inverse={variant === 'primary'} label="Aguarde" /> : icon && <Icon name={icon} size={iconSize} />}
      {children && <span>{children}</span>}
      {iconRight && !loading && <Icon name={iconRight} size={iconSize} />}
    </>
  );

  if (href) {
    return (
      <a className={classes} href={href} target="_blank" rel="noopener noreferrer" {...rest}>
        {content}
      </a>
    );
  }
  return (
    <button type={type} className={classes} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {content}
    </button>
  );
}
