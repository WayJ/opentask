export const ISSUE_CODE_COLUMN_WIDTH = 120;
export const ISSUE_TITLE_COLUMN_MAX = 300;
const TITLE_GUTTER = 24;

export const issueListPinColumnWidths = {
  issue_code: ISSUE_CODE_COLUMN_WIDTH,
  title: ISSUE_TITLE_COLUMN_MAX,
  type: 100,
  status: 120,
  priority: 100,
  estimate_points: 72,
  assignee_id: 120,
  actions: 200
} as const;

export function issueListActionsPinThreshold(
  widths: typeof issueListPinColumnWidths = issueListPinColumnWidths
): number {
  return (
    widths.issue_code +
    widths.title +
    widths.type +
    widths.status +
    widths.priority +
    widths.estimate_points +
    widths.assignee_id +
    widths.actions
  );
}

export function listTableBodyScrollElement(root: ParentNode | null): HTMLElement | null {
  if (!root) return null;
  const node = root.querySelector('.n-data-table-base-table-body .n-scrollbar-container');
  return node instanceof HTMLElement ? node : null;
}

export function issueListColumnLayout(tableWidth: number) {
  const pinActions = tableWidth > 0 && tableWidth >= issueListActionsPinThreshold();
  const available = tableWidth - ISSUE_CODE_COLUMN_WIDTH - TITLE_GUTTER;
  const titleWidth =
    tableWidth <= 0 || pinActions ? ISSUE_TITLE_COLUMN_MAX : Math.min(ISSUE_TITLE_COLUMN_MAX, Math.max(160, available));
  return { pinActions, titleWidth };
}

export interface ListScrollResizeObserver {
  observe(target: Element): void;
  disconnect(): void;
}

export interface ListScrollMutationObserver {
  observe(target: Node, init: { childList: true; subtree: true }): void;
  disconnect(): void;
}

export interface ListScrollBinderOptions {
  getRoot: () => Element | null;
  onWidth: (width: number) => void;
  nextTick: (callback: () => void) => void;
  isActive: () => boolean;
  ResizeObserver?: new (callback: () => void) => ListScrollResizeObserver;
  MutationObserver?: new (callback: () => void) => ListScrollMutationObserver;
}

export interface ListScrollBinder {
  schedule(): void;
  disconnect(): void;
}

export function createListScrollBinder(options: ListScrollBinderOptions): ListScrollBinder {
  let generation = 0;
  let activeResizeId = 0;
  let activeMutationId = 0;
  let observed: Element | null = null;
  let resizeObserver: ListScrollResizeObserver | undefined;
  let mutationObserver: ListScrollMutationObserver | undefined;
  let mutationRoot: Element | null = null;

  function detachResize() {
    activeResizeId += 1;
    resizeObserver?.disconnect();
    resizeObserver = undefined;
    observed = null;
  }

  function detachAll() {
    detachResize();
    activeMutationId += 1;
    mutationObserver?.disconnect();
    mutationObserver = undefined;
    mutationRoot = null;
  }

  function sync() {
    if (!options.isActive()) {
      detachAll();
      options.onWidth(0);
      return;
    }
    const root = options.getRoot();
    if (!(root instanceof Element)) {
      detachAll();
      options.onWidth(0);
      return;
    }
    if (!(mutationObserver && mutationRoot === root) && options.MutationObserver) {
      mutationObserver?.disconnect();
      mutationRoot = root;
      activeMutationId += 1;
      const id = activeMutationId;
      mutationObserver = new options.MutationObserver(() => {
        if (id !== activeMutationId) return;
        sync();
      });
      mutationObserver.observe(root, { childList: true, subtree: true });
    }
    const node = listTableBodyScrollElement(root);
    options.onWidth(node && node.clientWidth > 0 ? node.clientWidth : 0);
    if (node && node === observed && resizeObserver) return;
    detachResize();
    if (!node || !options.ResizeObserver) return;
    observed = node;
    activeResizeId += 1;
    const id = activeResizeId;
    resizeObserver = new options.ResizeObserver(() => {
      if (id !== activeResizeId) return;
      sync();
    });
    resizeObserver.observe(node);
  }

  return {
    schedule() {
      generation += 1;
      const token = generation;
      options.nextTick(() => {
        if (token !== generation) return;
        if (!options.isActive()) {
          detachAll();
          return;
        }
        sync();
      });
    },
    disconnect() {
      generation += 1;
      detachAll();
    }
  };
}
