import Select from '../../ui/Select/Select.jsx';

export const SORT_OPTIONS = [
  { value: 'price', label: 'Menor preço' },
  { value: 'discount', label: 'Maior desconto' },
  { value: 'match', label: 'Mais compatível' },
];

/**
 * Escolha da ordenação dos resultados.
 *
 * @param {object} props
 * @param {'price'|'discount'|'match'} props.value
 * @param {(value: string) => void} props.onChange
 */
export default function SortControl({ value, onChange }) {
  return <Select label="Ordenar por" inlineLabel size="sm" options={SORT_OPTIONS} value={value} onChange={onChange} />;
}
