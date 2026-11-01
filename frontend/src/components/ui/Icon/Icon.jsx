import styles from './Icon.module.css';
import { cx } from '../../../utils/classNames.js';

/**
 * Desenhos dos ícones (traço, viewBox 24x24). Para adicionar um ícone novo,
 * inclua aqui o conteúdo SVG interno (paths) com uma chave em kebab-case.
 */
const PATHS = {
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
  x: <path d="M18 6 6 18M6 6l12 12" />,
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  'chevron-down': <path d="m6 9 6 6 6-6" />,
  'chevron-right': <path d="m9 6 6 6-6 6" />,
  filter: <path d="M4 5h16l-6 8v5l-4 2v-7L4 5Z" />,
  sliders: <><path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0" /><circle cx="16" cy="6" r="2" /><circle cx="10" cy="12" r="2" /><circle cx="18" cy="18" r="2" /></>,
  store: <><path d="M4 9.5 5.5 4h13L20 9.5" /><path d="M4 9.5a2.7 2.7 0 0 0 5.3 0 2.7 2.7 0 0 0 5.4 0 2.7 2.7 0 0 0 5.3 0" /><path d="M5.5 12v8h13v-8" /><path d="M10 20v-4.5h4V20" /></>,
  truck: <><path d="M3 6h11v10H3zM14 10h4l3 3v3h-7" /><circle cx="7" cy="17.5" r="1.8" /><circle cx="17.5" cy="17.5" r="1.8" /></>,
  tag: <><path d="M3.5 12.5V4h8.5l8.5 8.5-8.5 8.5-8.5-8.5Z" /><circle cx="8" cy="8.5" r="1.3" /></>,
  star: <path d="m12 3.5 2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.8L12 3.5Z" />,
  shield: <><path d="M12 3 5 6v5.5c0 4.3 3 8 7 9.5 4-1.5 7-5.2 7-9.5V6l-7-3Z" /><path d="m9 12 2.2 2.2L15.5 10" /></>,
  sparkle: <path d="M12 3.5 13.8 9l5.7 1.8-5.7 1.8L12 18.5l-1.8-5.9-5.7-1.8L10.2 9 12 3.5ZM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z" />,
  alert: <><path d="M12 4 2.5 20h19L12 4Z" /><path d="M12 10v4.5M12 17.5v.01" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5.5M12 7.5v.01" /></>,
  'external-link': <><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  chart: <><path d="M4 4v16h16" /><path d="m7.5 14.5 3.5-4 3 2.5 5-6" /></>,
  bell: <><path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15L6 16Z" /><path d="M10 20.5a2 2 0 0 0 4 0" /></>,
  refresh: <><path d="M20 11a8 8 0 0 0-14.3-4.5L4 8.5" /><path d="M4 4v4.5h4.5" /><path d="M4 13a8 8 0 0 0 14.3 4.5L20 15.5" /><path d="M20 20v-4.5h-4.5" /></>,
  'sort-asc': <path d="M7 4v16M3.5 7.5 7 4l3.5 3.5M13 6h8M13 11h6M13 16h4" />,
  'sort-desc': <path d="M7 4v16M3.5 16.5 7 20l3.5-3.5M13 6h4M13 11h6M13 16h8" />,
  palette: <><path d="M12 3a9 9 0 1 0 0 18c1.2 0 1.8-.9 1.4-2-.4-1.2.4-2.5 1.7-2.5H17a4 4 0 0 0 4-4C21 7 17 3 12 3Z" /><circle cx="7.5" cy="11" r="1" /><circle cx="10" cy="7" r="1" /><circle cx="15" cy="7.5" r="1" /></>,
  'credit-card': <><rect x="3" y="5.5" width="18" height="13" rx="2" /><path d="M3 10h18M7 15h3" /></>,
  'trending-down': <path d="m3 7 7 7 4-4 7 7M21 11v6h-6" />,
};

/**
 * Ícone SVG inline.
 *
 * @param {object} props
 * @param {keyof PATHS} props.name   Nome do ícone (ex.: "search", "store", "shield").
 * @param {'sm'|'md'|'lg'} [props.size='md']  Tamanho (tokens --icon-size-*).
 * @param {string} [props.label]     Texto para leitores de tela. Sem label, o ícone é decorativo.
 * @param {string} [props.className]
 */
export default function Icon({ name, size = 'md', label, className }) {
  const content = PATHS[name];
  if (!content) return null;
  return (
    <svg
      viewBox="0 0 24 24"
      className={cx(styles.icon, styles[size], className)}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      {content}
    </svg>
  );
}

export const ICON_NAMES = Object.keys(PATHS);
