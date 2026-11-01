import styles from './Card.module.css';
import { cx } from '../../../utils/classNames.js';

/**
 * Superfície branca com borda suave e cantos arredondados.
 *
 * @param {object} props
 * @param {'none'|'sm'|'md'|'lg'} [props.padding='md']
 * @param {boolean} [props.interactive=false]  Eleva a sombra no hover (para cards clicáveis).
 * @param {boolean} [props.highlighted=false]  Borda na cor de destaque (ex.: melhor oferta).
 * @param {'div'|'article'|'section'|'li'} [props.as='div']
 * @param {React.ReactNode} props.children
 */
export default function Card({ padding = 'md', interactive = false, highlighted = false, as: Tag = 'div', className, children, ...rest }) {
  return (
    <Tag
      className={cx(styles.card, styles[`pad-${padding}`], interactive && styles.interactive, highlighted && styles.highlighted, className)}
      {...rest}
    >
      {children}
    </Tag>
  );
}
