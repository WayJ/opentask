import { type ComputedRef, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { type LabelTable, labelTable } from './display-label';

/** Current locale's string table at `path`. Recomputes when the language changes. */
export function useLabelTable(path: string): ComputedRef<LabelTable> {
  const { tm, locale } = useI18n();
  return computed(() => (locale.value ? labelTable(tm(path)) : labelTable(tm(path))));
}
