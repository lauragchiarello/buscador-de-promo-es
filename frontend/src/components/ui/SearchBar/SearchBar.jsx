import styles from './SearchBar.module.css';
import Icon from '../Icon/Icon.jsx';
import Button from '../Button/Button.jsx';

/**
 * Campo de busca grande com botão "Buscar".
 *
 * @param {object} props
 * @param {string} props.value
 * @param {(value: string) => void} props.onChange
 * @param {(value: string) => void} props.onSubmit   Chamado ao apertar Enter ou clicar em Buscar.
 * @param {boolean} [props.loading=false]
 * @param {string} [props.placeholder]
 * @param {boolean} [props.autoFocus=false]
 */
export default function SearchBar({ value, onChange, onSubmit, loading = false, placeholder = 'O que você procura?', autoFocus = false }) {
  function handleSubmit(e) {
    e.preventDefault();
    const v = value.trim();
    if (v.length >= 2) onSubmit(v);
  }

  return (
    <form className={styles.bar} onSubmit={handleSubmit} role="search">
      <Icon name="search" size="md" className={styles.icon} />
      <input
        className={styles.input}
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label="Buscar produto"
        autoFocus={autoFocus}
        enterKeyHint="search"
        maxLength={300}
      />
      {value && (
        <button type="button" className={styles.clear} onClick={() => onChange('')} aria-label="Limpar busca">
          <Icon name="x" size="sm" />
        </button>
      )}
      <Button type="submit" size="lg" loading={loading} disabled={value.trim().length < 2} className={styles.submit}>
        Buscar
      </Button>
    </form>
  );
}
