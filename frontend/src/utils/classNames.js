/** Junta classes CSS ignorando valores falsos: cx('a', cond && 'b') -> "a b" */
export function cx(...args) {
  return args.filter(Boolean).join(' ');
}
