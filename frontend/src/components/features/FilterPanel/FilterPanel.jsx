import styles from './FilterPanel.module.css';
import Card from '../../ui/Card/Card.jsx';
import Input from '../../ui/Input/Input.jsx';
import Checkbox from '../../ui/Checkbox/Checkbox.jsx';
import Button from '../../ui/Button/Button.jsx';
import StoreTag from '../../ui/StoreTag/StoreTag.jsx';

/**
 * Filtros opcionais (aplicados na hora, sem nova busca).
 *
 * @param {object} props
 * @param {object} props.filters   {minPrice, maxPrice, stores: string[], officialOnly, includeUsed}
 * @param {(filters: object) => void} props.onChange
 * @param {{slug: string, name: string, configured: boolean}[]} props.stores  Lojas disponíveis.
 * @param {() => void} props.onClear
 */
export default function FilterPanel({ filters, onChange, stores, onClear }) {
  const set = (patch) => onChange({ ...filters, ...patch });
  const toggleStore = (slug, checked) => {
    const current = filters.stores.length ? filters.stores : stores.map((s) => s.slug);
    const next = checked ? [...new Set([...current, slug])] : current.filter((s) => s !== slug);
    set({ stores: next.length === stores.length ? [] : next });
  };
  const isStoreOn = (slug) => !filters.stores.length || filters.stores.includes(slug);
  const dirty = filters.minPrice || filters.maxPrice || filters.stores.length || filters.officialOnly || filters.includeUsed;

  return (
    <Card as="aside" padding="md" className={styles.panel} aria-label="Filtros">
      <div className={styles.header}>
        <h2 className={styles.heading}>Filtros</h2>
        {dirty ? (
          <Button variant="ghost" size="sm" onClick={onClear}>
            Limpar
          </Button>
        ) : null}
      </div>

      <fieldset className={styles.group}>
        <legend className={styles.legend}>Faixa de preço</legend>
        <div className={styles.priceRow}>
          <Input
            size="sm"
            prefix="R$"
            inputMode="numeric"
            placeholder="mín."
            aria-label="Preço mínimo"
            value={filters.minPrice}
            onChange={(e) => set({ minPrice: e.target.value.replace(/[^\d]/g, '') })}
          />
          <span className={styles.dash}>–</span>
          <Input
            size="sm"
            prefix="R$"
            inputMode="numeric"
            placeholder="máx."
            aria-label="Preço máximo"
            value={filters.maxPrice}
            onChange={(e) => set({ maxPrice: e.target.value.replace(/[^\d]/g, '') })}
          />
        </div>
      </fieldset>

      {stores.length > 0 && (
        <fieldset className={styles.group}>
          <legend className={styles.legend}>Lojas</legend>
          {stores.map((s) => (
            <Checkbox
              key={s.slug}
              checked={isStoreOn(s.slug)}
              onChange={(checked) => toggleStore(s.slug, checked)}
              label={<StoreTag store={s.slug} name={s.name} size="sm" />}
              description={s.configured ? undefined : 'precisa de chave de API'}
            />
          ))}
        </fieldset>
      )}

      <fieldset className={styles.group}>
        <legend className={styles.legend}>Vendedor e condição</legend>
        <Checkbox
          checked={filters.officialOnly}
          onChange={(v) => set({ officialOnly: v })}
          label="Só lojas oficiais"
          description="Esconde vendedores de marketplace"
        />
        <Checkbox
          checked={filters.includeUsed}
          onChange={(v) => set({ includeUsed: v })}
          label="Incluir usados e recondicionados"
        />
      </fieldset>
    </Card>
  );
}
