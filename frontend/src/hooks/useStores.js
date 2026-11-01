import { useEffect, useState } from 'react';
import { getStores } from '../services/api.js';

/** Lista de lojas do backend (carregada uma vez). */
export function useStores() {
  const [stores, setStores] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getStores()
      .then((data) => alive && setStores(data))
      .catch((err) => alive && setError(err))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  return { stores, error, loading };
}
