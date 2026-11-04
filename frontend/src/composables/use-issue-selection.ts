import { computed, ref } from 'vue';

const selectedIds = ref<string[]>([]);
const anchorId = ref<string | null>(null);
/** Visual order of issues on list/board for Shift+X range select (E21). */
const issueOrderIds = ref<string[]>([]);

/** Test-only reset of module singleton state. */
export function resetIssueSelectionForTests() {
  selectedIds.value = [];
  anchorId.value = null;
  issueOrderIds.value = [];
}

/** Shared multi-select for issue list/board + X / Esc hotkeys (E20/E21). */
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
  function selectRange(targetId: string, orderedIds?: string[]) {
    const order = orderedIds?.length ? orderedIds : issueOrderIds.value;
    const target = targetId.trim();
    if (!target || !order.length) return;
    const anchor = anchorId.value && order.includes(anchorId.value) ? anchorId.value : target;
    const a = order.indexOf(anchor);
    const b = order.indexOf(target);
    if (a < 0 || b < 0) {
      toggle(target);
      return;
    }
    const [lo, hi] = a <= b ? [a, b] : [b, a];
    const slice = order.slice(lo, hi + 1);
    const set = new Set(selectedIds.value);
    for (const id of slice) set.add(id);
    selectedIds.value = order.filter(id => set.has(id)).concat(
      [...set].filter(id => !order.includes(id))
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

  function setIssueOrder(ids: string[]) {
    issueOrderIds.value = ids.map(x => String(x)).filter(Boolean);
  }

  function getIssueOrder(): string[] {
    return issueOrderIds.value;
  }

  return {
    selectedIds,
    anchorId,
    issueOrderIds,
    selectedSet,
    count,
    hasSelection,
    isSelected,
    toggle,
    selectRange,
    clear,
    setMany,
    setIssueOrder,
    getIssueOrder
  };
}
