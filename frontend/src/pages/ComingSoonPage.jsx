import styles from './ComingSoonPage.module.css';
import Card from '../components/ui/Card/Card.jsx';
import EmptyState from '../components/ui/EmptyState/EmptyState.jsx';

/**
 * Tela provisória para funcionalidades das próximas fases.
 *
 * @param {object} props
 * @param {string} props.icon
 * @param {string} props.title
 * @param {string} props.description
 */
export default function ComingSoonPage({ icon, title, description }) {
  return (
    <div className={styles.page}>
      <Card padding="lg">
        <EmptyState icon={icon} title={title} description={description} />
      </Card>
    </div>
  );
}
