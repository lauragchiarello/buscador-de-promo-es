import styles from './PriceTag.module.css';
import { formatBRL } from '../../../utils/format.js';
import { cx } from '../../../utils/classNames.js';

/**
 * Bloco de preço: "de" riscado, preço à vista/Pix em destaque e parcelamento.
 *
 * @param {object} props
 * @param {number|null} props.cash               Preço à vista / Pix.
 * @param {number|null} [props.listPrice]        Preço "de" (antes do desconto) — aparece riscado.
 * @param {number|null} [props.installmentTotal] Preço total parcelado.
 * @param {number|null} [props.installments]     Nº de parcelas.
 * @param {number|null} [props.installmentValue] Valor de cada parcela.
 * @param {string} [props.cashLabel='à vista no Pix']
 * @param {'md'|'lg'} [props.size='md']
 * @param {boolean} [props.highlight=false]      Preço na cor de destaque.
 */
export default function PriceTag({
  cash,
  listPrice,
  installmentTotal,
  installments,
  installmentValue,
  cashLabel = 'à vista no Pix',
  size = 'md',
  highlight = false,
}) {
  const main = cash ?? installmentTotal;
  const showInstallments = installments > 1 && installmentValue;
  const sameAsCash = installmentTotal && cash && Math.abs(installmentTotal - cash) < 0.5;

  return (
    <div className={cx(styles.price, styles[size])}>
      {listPrice > main && <span className={styles.list}>{formatBRL(listPrice)}</span>}
      <span className={cx(styles.main, highlight && styles.highlight)}>{formatBRL(main)}</span>
      {cash && <span className={styles.caption}>{cashLabel}</span>}
      {showInstallments && (
        <span className={styles.installments}>
          ou {installments}x de {formatBRL(installmentValue)}
          {sameAsCash ? ' sem juros' : installmentTotal ? ` (${formatBRL(installmentTotal)})` : ''}
        </span>
      )}
    </div>
  );
}
