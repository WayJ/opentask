import { computed, ref } from 'vue';

const selectedIds = ref<string[]>([]);
const anchorId = ref<string | null>(null);

/** Test-only reset of module singleton state. */
export function resetIssueSelectionForTests() {
  selectedIds.value = [];
  anchorId.value = null;
}

/** Shared multi-select for issue list/board + X / Esc hotkeys (E20). */
export function useIssueSelection() {
  const selectedSet = computed(() => new Set(selectedIds.value));
  const count = computed(() => selectedIds.value.length);
  const hasSelection = computed(() => selectedIds.value.length > 0);

  function isSelected(id: string): boolean {
    return selectedSet.value.has(id);
  }

  function toggle(id: string) {
    const next = id.trim();
    if (!next) return;
    const idx = selectedIds.value.indexOf(next);
    if (idx >= 0) {
      selectedIds.value = selectedIds.value.filter(x => x !== next);
    } else {
      selectedIds.value = [...selectedIds.value, next];
    }
    anchorId.value = next;
  }

  /** Shift+X: select inclusive range between anchor and target within orderedIds. */
  function selectRange(targetId: string, orderedIds: string[]) {
    const target = targetId.trim();
    if (!target || !orderedIds.length) return;
    const anchor = anchorId.value && orderedIds.includes(anchorId.value) ? anchorId.value : target;
    const a = orderedIds.indexOf(anchor);
    const b = orderedIds.indexOf(target);
    if (a < 0 || b < 0) {
      toggle(target);
      return;
    }
    const [lo, hi] = a <= b ? [a, b] : [b, a];
    const slice = orderedIds.slice(lo, hi + 1);
    const set = new Set(selectedIds.value);
    for (const id of slice) set.add(id);
    selectedIds.value = orderedIds.filter(id => set.has(id)).concat(
      [...set].filter(id => !orderedIds.includes(id))
    );
    anchorId.value = target;
  }

  function clear() {
    selectedIds.value = [];
    anchorId.value = null;
  }

  function setMany(ids: string[]) {
    selectedIds.value = [...new Set(ids.map(x => x.trim()).filter(Boolean))];
    anchorId.value = selectedIds.value[selectedIds.value.length - 1] || null;
  }

  return {
    selectedIds,
    anchorId,
    selectedSet,
    count,
    hasSelection,
    isSelected,
    toggle,
    selectRange,
    clear,
    setMany
  };
}
