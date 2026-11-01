import { useEffect, useState } from 'react';

/** Devolve `value` só depois de `delay` ms sem mudanças (ex.: campos de preço). */
export function useDebounce(value, delay = 400) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}
