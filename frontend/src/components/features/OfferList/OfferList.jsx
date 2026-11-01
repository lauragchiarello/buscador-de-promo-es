import styles from './OfferList.module.css';
import OfferCard from '../OfferCard/OfferCard.jsx';
import Card from '../../ui/Card/Card.jsx';
import Skeleton from '../../ui/Skeleton/Skeleton.jsx';
import EmptyState from '../../ui/EmptyState/EmptyState.jsx';
import Button from '../../ui/Button/Button.jsx';

/** Card "fantasma" mostrado enquanto as lojas respondem. */
function OfferCardSkeleton() {
  return (
    <Card padding="md" className={styles.skeleton}>
      <Skeleton shape="text" width="1/3" />
      <Skeleton shape="image" />
      <Skeleton shape="text" lines={2} />
      <Skeleton shape="title" width="1/2" />
      <Skeleton shape="text" width="3/4" />
    </Card>
  );
}

/**
 * Grade de ofertas com estados de carregando e vazio.
 *
 * @param {object} props
 * @param {object[]} props.offers           Ofertas já filtradas e ordenadas.
 * @param {string|null} props.bestKey       "loja:id" da melhor oferta.
 * @param {boolean} props.loading           Ainda há lojas respondendo?
 * @param {number} [props.hiddenCount=0]    Quantas ofertas os filtros esconderam.
 * @param {() => void} [props.onClearFilters]
 */
export default function OfferList({ offers, bestKey, loading, hiddenCount = 0, onClearFilters }) {
  if (!offers.length && loading) {
    return (
      <div className={styles.grid} aria-busy="true" aria-label="Carregando ofertas">
        {Array.from({ length: 6 }, (_, i) => (
          <OfferCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (!offers.length) {
    return hiddenCount > 0 ? (
      <EmptyState
        emoji="🧐"
        title="Os filtros esconderam todas as ofertas"
        description={`Achamos ${hiddenCount} ${hiddenCount === 1 ? 'oferta' : 'ofertas'}, mas nenhuma passa nos filtros atuais.`}
        action={onClearFilters && <Button variant="secondary" onClick={onClearFilters}>Limpar filtros</Button>}
      />
    ) : (
      <EmptyState
        emoji="😕"
        title="Não achamos ofertas para isso"
        description="Tente tirar alguma especificação (por exemplo a geração do processador) ou escrever de outro jeito."
      />
    );
  }

  return (
    <ul className={styles.grid}>
      {offers.map((o) => {
        const key = `${o.store}:${o.external_id}`;
        return (
          <li key={key} className={styles.item}>
            <OfferCard offer={o} best={key === bestKey} />
          </li>
        );
      })}
      {loading && (
        <li className={styles.item}>
          <OfferCardSkeleton />
        </li>
      )}
    </ul>
  );
}
