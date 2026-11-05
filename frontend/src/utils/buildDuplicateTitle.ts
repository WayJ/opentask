/** E75: ASCII title suffix for Issue duplicate (Q3a). UI may label 副本. */
export const COPY_TITLE_SUFFIX = ' (copy)';

export function buildDuplicateTitle(title: string, override?: string | null): string {
  if (override != null && override.trim()) {
    return override.trim();
  }
  return `${title}${COPY_TITLE_SUFFIX}`;
}
