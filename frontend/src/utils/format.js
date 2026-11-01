/** Formatação de moeda, porcentagem e datas em pt-BR. */

const brl = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const brlNoCents = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 0,
});

/** 1234.5 -> "R$ 1.234,50" (ou "—" se vazio) */
export function formatBRL(value, { cents = true } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return (cents ? brl : brlNoCents).format(value);
}

/** 25.04 -> "-25%" */
export function formatDiscount(pct) {
  if (!pct) return '';
  return `-${Math.round(pct)}%`;
}

const dateTime = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
const dateShort = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit' });

export function formatDateTime(iso) {
  if (!iso) return '';
  return dateTime.format(new Date(iso));
}

export function formatDateShort(iso) {
  if (!iso) return '';
  return dateShort.format(new Date(iso));
}

/** "há 5 min", "há 2 h", "agora" */
export function formatRelative(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'agora';
  if (diff < 3600) return `há ${Math.round(diff / 60)} min`;
  if (diff < 86400) return `há ${Math.round(diff / 3600)} h`;
  return `há ${Math.round(diff / 86400)} d`;
}

/** 32 -> "32GB", 1024 -> "1TB" */
export function formatGB(gb) {
  if (!gb) return '';
  return gb >= 1024 && gb % 1024 === 0 ? `${gb / 1024}TB` : `${gb}GB`;
}
