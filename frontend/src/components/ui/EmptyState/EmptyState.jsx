import styles from './EmptyState.module.css';
import Icon from '../Icon/Icon.jsx';

/**
 * Mensagem amigável quando não há o que mostrar.
 *
 * @param {object} props
 * @param {string} [props.emoji]     Emoji grande (tem prioridade sobre o ícone).
 * @param {string} [props.icon]      Nome de um ícone.
 * @param {string} props.title
 * @param {React.ReactNode} [props.description]
 * @param {React.ReactNode} [props.action]  Normalmente um <Button>.
 */
export default function EmptyState({ emoji, icon, title, description, action }) {
  return (
    <div className={styles.empty}>
      {emoji ? (
        <span className={styles.emoji} aria-hidden="true">
          {emoji}
        </span>
      ) : (
        icon && (
          <span className={styles.iconWrap}>
            <Icon name={icon} size="lg" />
          </span>
        )
      )}
      <h3 className={styles.title}>{title}</h3>
      {description && <p className={styles.description}>{description}</p>}
      {action && <div className={styles.action}>{action}</div>}
    </div>
  );
}
