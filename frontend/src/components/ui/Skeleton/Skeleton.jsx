import styles from './Skeleton.module.css';
import { cx } from '../../../utils/classNames.js';

/**
 * Bloco cinza animado que ocupa o lugar do conteúdo enquanto carrega.
 *
 * @param {object} props
 * @param {'text'|'title'|'block'|'circle'|'image'} [props.shape='text']
 * @param {'full'|'3/4'|'1/2'|'1/3'} [props.width='full']  Largura relativa.
 * @param {number} [props.lines=1]   Para shape="text": quantas linhas.
 */
export default function Skeleton({ shape = 'text', width = 'full', lines = 1, className }) {
  const widthClass = styles[`w-${width.replace('/', '-')}`];
  if (shape === 'text' && lines > 1) {
    return (
      <span className={cx(styles.group, className)} aria-hidden="true">
        {Array.from({ length: lines }, (_, i) => (
          <span key={i} className={cx(styles.skeleton, styles.text, i === lines - 1 ? styles['w-2-3'] : widthClass)} />
        ))}
      </span>
    );
  }
  return <span className={cx(styles.skeleton, styles[shape], widthClass, className)} aria-hidden="true" />;
}
