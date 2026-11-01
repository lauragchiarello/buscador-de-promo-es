import { useState } from 'react';
import styles from './OfferCard.module.css';
import Card from '../../ui/Card/Card.jsx';
import Badge from '../../ui/Badge/Badge.jsx';
import Button from '../../ui/Button/Button.jsx';
import Icon from '../../ui/Icon/Icon.jsx';
import PriceTag from '../../ui/PriceTag/PriceTag.jsx';
import StoreTag from '../../ui/StoreTag/StoreTag.jsx';
import Tooltip from '../../ui/Tooltip/Tooltip.jsx';
import { formatDiscount, formatRelative } from '../../../utils/format.js';
import { specChips } from '../../../utils/specs.js';
import { cx } from '../../../utils/classNames.js';

/** Lojas cujo preço à vista é especificamente no Pix. */
const PIX_STORES = new Set(['kabum', 'terabyte']);

const LEVEL = {
  exato: { label: 'Bate com a busca', tone: 'success' },
  provavel: { label: 'Provavelmente bate', tone: 'accent' },
  duvidoso: { label: 'Confira os detalhes', tone: 'warning' },
};

/**
 * Card de uma oferta.
 *
 * @param {object} props
 * @param {object} props.offer   Oferta como vem da API (ver backend/app/schemas.py: Offer).
 * @param {boolean} [props.best=false]  É a melhor oferta da busca?
 */
export default function OfferCard({ offer, best = false }) {
  const [imgFailed, setImgFailed] = useState(false);
  const level = LEVEL[offer.match_level] || LEVEL.duvidoso;
  const verdict = offer.history?.verdict;
  const chips = specChips({ ...offer.specs, category: null, keywords: [] }).slice(0, 5);
  const soldByStore = offer.seller && (offer.seller === offer.store_name || offer.seller === 'KaBuM!');
  const realDeal = verdict === 'real' || (offer.discount_pct >= 5 && verdict !== 'suspeito');

  return (
    <Card as="article" padding="none" interactive highlighted={best} className={styles.card}>
      <div className={styles.top}>
        <StoreTag store={offer.store} name={offer.store_name} size="sm" />
        <div className={styles.topBadges}>
          {best && (
            <Badge tone="accent" variant="solid" icon="sparkle">
              Melhor oferta
            </Badge>
          )}
          {offer.discount_pct >= 1 && (
            <Badge tone="deal" variant={realDeal ? 'solid' : 'soft'}>
              {formatDiscount(offer.discount_pct)}
            </Badge>
          )}
        </div>
      </div>

      <a href={offer.url} target="_blank" rel="noopener noreferrer" className={styles.imageLink} tabIndex={-1}>
        {offer.image_url && !imgFailed ? (
          <img src={offer.image_url} alt="" loading="lazy" className={styles.image} onError={() => setImgFailed(true)} />
        ) : (
          <span className={styles.imagePlaceholder}>
            <Icon name="tag" size="lg" />
          </span>
        )}
      </a>

      <div className={styles.body}>
        <h3 className={styles.title} title={offer.title}>
          <a href={offer.url} target="_blank" rel="noopener noreferrer">
            {offer.title}
          </a>
        </h3>

        {chips.length > 0 && (
          <ul className={styles.chips} aria-label="Especificações encontradas">
            {chips.map((c) => (
              <li key={c} className={styles.chip}>
                {c}
              </li>
            ))}
          </ul>
        )}

        <div className={styles.badges}>
          {offer.is_official && (
            <Badge tone="success" icon="shield" size="sm">
              {soldByStore ? 'Vendido pela loja' : 'Loja oficial'}
            </Badge>
          )}
          {offer.shipping === 0 && (
            <Badge tone="neutral" icon="truck" size="sm">
              Frete grátis
            </Badge>
          )}
          {offer.condition !== 'novo' && (
            <Badge tone="warning" size="sm">
              {offer.condition === 'usado' ? 'Usado' : 'Recondicionado'}
            </Badge>
          )}
          {verdict === 'real' && (
            <Badge tone="deal" icon="trending-down" size="sm" title="Abaixo da mediana dos últimos 30 dias">
              Promoção de verdade
            </Badge>
          )}
          {verdict === 'suspeito' && (
            <Badge tone="warning" icon="alert" size="sm" title="O preço está igual ou acima do normal dos últimos 30 dias">
              Desconto suspeito
            </Badge>
          )}
        </div>

        <PriceTag
          cash={offer.price_cash}
          listPrice={offer.price_list}
          installmentTotal={offer.price_installment}
          installments={offer.installments}
          installmentValue={offer.installment_value}
          cashLabel={PIX_STORES.has(offer.store) ? 'à vista no Pix' : 'à vista'}
          highlight={best}
        />

        <div className={styles.meta}>
          <Tooltip
            content={
              offer.match_reasons.length ? (
                <ul className={styles.reasons}>
                  {offer.match_reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              ) : (
                'Todas as especificações pedidas aparecem no título.'
              )
            }
          >
            <span className={cx(styles.match, styles[level.tone])} tabIndex={0}>
              <Icon name={offer.match_reasons.length ? 'info' : 'check'} size="sm" />
              {offer.match_score}% · {level.label}
            </span>
          </Tooltip>
          {offer.match_reasons.length > 0 && <p className={styles.reasonInline}>{offer.match_reasons[0]}</p>}
          {offer.seller && (
            <p className={styles.seller}>
              Vendido por <strong>{offer.seller}</strong>
              {offer.seller_reputation && ` · ${offer.seller_reputation}`}
            </p>
          )}
        </div>
      </div>

      <footer className={styles.footer}>
        <span className={styles.collected} title={new Date(offer.collected_at).toLocaleString('pt-BR')}>
          <Icon name="clock" size="sm" /> {formatRelative(offer.collected_at)}
        </span>
        <Button href={offer.url} size="sm" variant={best ? 'primary' : 'secondary'} iconRight="external-link">
          Ver na loja
        </Button>
      </footer>
    </Card>
  );
}
