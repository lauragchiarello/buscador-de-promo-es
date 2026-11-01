import styles from './QuerySummary.module.css';
import Badge from '../../ui/Badge/Badge.jsx';
import Skeleton from '../../ui/Skeleton/Skeleton.jsx';
import { specChips } from '../../../utils/specs.js';

/**
 * Mostra como a busca foi entendida: "Entendi: Notebook · i7 13ª geração · 32GB RAM".
 *
 * @param {object} props
 * @param {object|null} props.specs  Specs devolvidas pela API (null enquanto carrega).
 */
export default function QuerySummary({ specs }) {
  if (!specs) {
    return (
      <div className={styles.summary}>
        <Skeleton shape="text" width="1/3" />
      </div>
    );
  }
  const chips = specChips(specs);
  return (
    <div className={styles.summary}>
      <span className={styles.label}>Entendi:</span>
      {chips.length ? (
        chips.map((c) => (
          <Badge key={c} tone="accent">
            {c}
          </Badge>
        ))
      ) : (
        <span className={styles.none}>nenhuma especificação — vou mostrar tudo que não for acessório</span>
      )}
    </div>
  );
}
