import { computed, type ComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { labelTable, type LabelTable } from './display-label';

/** Current locale's string table at `path`. Recomputes when the language changes. */
export function useLabelTable(path: string): ComputedRef<LabelTable> {
  const { tm, locale } = useI18n();
  return computed(() => {
    void locale.value;
    return labelTable(tm(path));
  });
}
