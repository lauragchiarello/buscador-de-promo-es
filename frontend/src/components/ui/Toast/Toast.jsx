import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import styles from './Toast.module.css';
import Icon from '../Icon/Icon.jsx';
import { cx } from '../../../utils/classNames.js';

const ToastContext = createContext(null);

const TONE_ICON = { info: 'info', success: 'check', error: 'alert', warning: 'alert' };

/**
 * Uma notificação flutuante (normalmente criada via useToast, não diretamente).
 *
 * @param {object} props
 * @param {'info'|'success'|'error'|'warning'} [props.tone='info']
 * @param {string} props.message
 * @param {() => void} [props.onClose]
 */
export function Toast({ tone = 'info', message, onClose }) {
  return (
    <div className={cx(styles.toast, styles[tone])} role={tone === 'error' ? 'alert' : 'status'}>
      <Icon name={TONE_ICON[tone]} size="sm" className={styles.icon} />
      <span className={styles.message}>{message}</span>
      {onClose && (
        <button type="button" className={styles.close} onClick={onClose} aria-label="Fechar aviso">
          <Icon name="x" size="sm" />
        </button>
      )}
    </div>
  );
}

/** Envolve o app e permite mostrar toasts de qualquer lugar com useToast(). */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => setToasts((list) => list.filter((t) => t.id !== id)), []);

  const show = useCallback(
    (message, { tone = 'info', duration = 4000 } = {}) => {
      const id = nextId.current++;
      setToasts((list) => [...list.slice(-3), { id, message, tone }]);
      if (duration) setTimeout(() => dismiss(id), duration);
      return id;
    },
    [dismiss],
  );

  const value = useMemo(() => ({ show, dismiss }), [show, dismiss]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className={styles.region} aria-live="polite">
        {toasts.map((t) => (
          <Toast key={t.id} tone={t.tone} message={t.message} onClose={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** Hook: const toast = useToast(); toast.show('Salvo!', { tone: 'success' }) */
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast precisa estar dentro de <ToastProvider>');
  return ctx;
}

export default Toast;
