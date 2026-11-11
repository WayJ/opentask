export type LabelTable = Record<string, string>;

export interface LabeledOption<V extends string = string> {
  label: string;
  value: V;
}

/** Copy own string values onto a null-prototype table. */
export function labelTable(source: unknown): LabelTable {
  const out: LabelTable = Object.create(null);
  if (!source || typeof source !== 'object') return out;
  for (const key of Object.keys(source as object)) {
    const value = (source as Record<string, unknown>)[key];
    if (typeof value === 'string') out[key] = value;
  }
  return out;
}

/**
 * Own string label for `value`. Missing keys, empty strings, and inherited
 * names such as `toString` or `__proto__` return the original value.
 */
export function lookupLabel(table: LabelTable | null | undefined, value: unknown): string {
  if (value == null) return '';
  const raw = String(value);
  if (!table || !Object.prototype.hasOwnProperty.call(table, raw)) return raw;
  const label = table[raw];
  return typeof label === 'string' && label !== '' ? label : raw;
}

export function labeledOptions<V extends string>(
  values: readonly V[],
  table: LabelTable | null | undefined
): LabeledOption<V>[] {
  return values.map(value => ({ value, label: lookupLabel(table, value) }));
}
