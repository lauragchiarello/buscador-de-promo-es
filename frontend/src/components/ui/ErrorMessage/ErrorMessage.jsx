import styles from './ErrorMessage.module.css';
import Icon from '../Icon/Icon.jsx';
import Button from '../Button/Button.jsx';
import { cx } from '../../../utils/classNames.js';

/**
 * Aviso de erro (ou atenção) com ação opcional de "tentar de novo".
 *
 * @param {object} props
 * @param {string} [props.title='Algo deu errado']
 * @param {React.ReactNode} [props.children]  Detalhe do erro em linguagem simples.
 * @param {() => void} [props.onRetry]        Mostra o botão "Tentar de novo".
 * @param {'error'|'warning'} [props.tone='error']
 * @param {boolean} [props.compact=false]     Versão em uma linha, para dentro de cards.
 */
export default function ErrorMessage({ title = 'Algo deu errado', children, onRetry, tone = 'error', compact = false }) {
  return (
    <div className={cx(styles.box, styles[tone], compact && styles.compact)} role="alert">
      <Icon name="alert" size={compact ? 'sm' : 'md'} className={styles.icon} />
      <div className={styles.body}>
        <p className={styles.title}>{title}</p>
        {children && <p className={styles.text}>{children}</p>}
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" icon="refresh" onClick={onRetry}>
          Tentar de novo
        </Button>
      )}
    </div>
  );
}
