# 问题列表操作列钉住条件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 只在未分组列表表的表体横滚容器放得下编号到负责人再加上操作列时，才把操作列钉在右侧。

**Architecture:** 列宽、门槛 T、选择器和 `createListScrollBinder` 都在 `column-layout.ts`。绑定单元自己管理代次、`nextTick`、`ResizeObserver` 和表根上的 `MutationObserver`。`index.vue` 只把未分组 `NDataTable` 的 `$el` 交进去，并在卸载时先关掉活动标志再 `disconnect`。

**Tech Stack:** Vue 3.5.27、`<script setup>`、Vitest 4 + happy-dom、Vite 7 `--mode prod`、naive-ui 2.43.2。不加依赖。

## Global Constraints

- 起点提交是 `088a34308cb0fe75a95f129432ee67b8f54067c3`。不改 PR #6、#7、#8、#9，不 merge，不 deploy。
- 只读 worktree `/tmp/cursor/opentask-pr7` 保持不动。实施用另一个 worktree。
- 产品与测试只有 `column-layout.ts`、`column-layout.test.ts`、`index.vue`。文档只有下面两条，第一笔提交就入库。
- `pnpm exec vite` 用 `--mode prod`。不跑 `--mode test`。不 `eslint --fix`。不新增依赖。
- 意外的 tracked 脏文件出现就停，不自行恢复。
- 视口宽度不是 T。几何以横滚节点的 `clientWidth` 和 `issueListActionsPinThreshold()` 比较。
- 本计划批准前，375、768、暗色、宽桌面、Tab、侧栏、看板来回都还没有新采样。

---

### Task 0: 批准后的隔离分支，只提交文档

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-issue-list-pin-design.md`
- Create: `docs/superpowers/plans/2026-11-12-issue-list-pin.md`

**Interfaces:**
- Consumes: 已批准的外部 spec 与本计划
- Produces: 分支 `cursor/issue-list-pin-4333`，HEAD 在文档提交上

- [ ] **Step 1: 从精确 088a 建新 worktree**

不要使用 `/tmp/cursor/opentask-pr7`。

```bash
git -C /agent/repos/opentask worktree add -b cursor/issue-list-pin-4333 /tmp/cursor/opentask-list-pin 088a34308cb0fe75a95f129432ee67b8f54067c3
git -C /tmp/cursor/opentask-list-pin rev-parse HEAD
git -C /tmp/cursor/opentask-list-pin status --porcelain
```

Expected: HEAD 是 `088a34308cb0fe75a95f129432ee67b8f54067c3`。第二条命令的标准输出为空。

- [ ] **Step 2: 记下 088a 的 vue-tsc 和 eslint**

cwd：`/tmp/cursor/opentask-list-pin/frontend`。目录新建，不覆盖旧 SHA。

```bash
mkdir -p /tmp/cursor/opentask-readonly/list-pin-logs/088a34308cb0fe75a95f129432ee67b8f54067c3
cd /tmp/cursor/opentask-list-pin/frontend
{ echo "DATE $(date -u '+%Y-%m-%dT%H:%M:%SZ')"; echo "SHA $(git rev-parse HEAD)"; echo "CWD $(pwd)"; pnpm exec vue-tsc --noEmit --skipLibCheck; echo "EXIT $?"; } > /tmp/cursor/opentask-readonly/list-pin-logs/088a34308cb0fe75a95f129432ee67b8f54067c3/vue-tsc.txt 2>&1
{ echo "DATE $(date -u '+%Y-%m-%dT%H:%M:%SZ')"; echo "SHA $(git rev-parse HEAD)"; echo "CWD $(pwd)"; pnpm exec eslint .; echo "EXIT $?"; } > /tmp/cursor/opentask-readonly/list-pin-logs/088a34308cb0fe75a95f129432ee67b8f54067c3/eslint.txt 2>&1
```

Expected: vue-tsc `EXIT 2`，29 条 `error TS`。eslint `EXIT 1`，`872 problems (190 errors, 682 warnings)`。这两项仍是失败。

- [ ] **Step 3: 只提交 spec 和 plan**

```bash
cd /tmp/cursor/opentask-list-pin
git add docs/superpowers/specs/2026-11-12-issue-list-pin-design.md docs/superpowers/plans/2026-11-12-issue-list-pin.md
git diff --cached --name-only
git commit -m "docs: specify when the issue list pins actions"
```

Expected: `name-only` 只有这两个文件。`git status --porcelain` 的标准输出为空。不改 `docs/superpowers/specs/2026-11-11-issue-surface-visual-design.md`。那份文件第 112 行仍写着 `ISSUE_ACTIONS_PIN_MIN`，检索原文在外部包的 `pin-min-rg.txt`。

### Task 1: 失败的门槛、诱饵和绑定测试

**Files:**
- Modify: `frontend/src/views/issue/list/column-layout.test.ts`
- Test: `frontend/src/views/issue/list/column-layout.test.ts`

**Interfaces:**
- Consumes: 现有 `issueListColumnLayout`
- Produces: 测试所期待的 `issueListPinColumnWidths`、`issueListActionsPinThreshold`、`listTableBodyScrollElement`、`createListScrollBinder`

- [ ] **Step 1: 用下面的文件替换 `column-layout.test.ts`**

349 和 522 两条保持原样。1034 改为不钉、标题仍是 300。诱饵与真实节点用同一个选择器，诱饵先插入 `document.body`。

```ts
import { describe, expect, it } from 'vitest';
import {
  ISSUE_CODE_COLUMN_WIDTH,
  createListScrollBinder,
  issueListActionsPinThreshold,
  issueListColumnLayout,
  issueListPinColumnWidths,
  listTableBodyScrollElement,
  type ListScrollMutationObserver,
  type ListScrollResizeObserver
} from './column-layout';

describe('issueListColumnLayout', () => {
  it('fits the whole title beside the code column on a phone table', () => {
    const layout = issueListColumnLayout(349);
    expect(layout.pinActions).toBe(false);
    expect(layout.titleWidth).toBeGreaterThanOrEqual(160);
    expect(ISSUE_CODE_COLUMN_WIDTH + layout.titleWidth).toBeLessThanOrEqual(349);
  });

  it('fits a 300px title on a tablet table without pinning actions', () => {
    const layout = issueListColumnLayout(522);
    expect(layout.pinActions).toBe(false);
    expect(layout.titleWidth).toBe(300);
    expect(ISSUE_CODE_COLUMN_WIDTH + layout.titleWidth).toBeLessThanOrEqual(522);
  });

  it('does not pin at the old 1034px table width and still uses a 300px title', () => {
    const layout = issueListColumnLayout(1034);
    expect(layout.pinActions).toBe(false);
    expect(layout.titleWidth).toBe(300);
  });

  it('derives T from the pinned column widths and pins only at T and above', () => {
    const widths = issueListPinColumnWidths;
    expect(widths).toEqual({
      issue_code: 120,
      title: 300,
      type: 100,
      status: 120,
      priority: 100,
      estimate_points: 72,
      assignee_id: 120,
      actions: 200
    });
    const threshold = issueListActionsPinThreshold();
    expect(threshold).toBe(
      widths.issue_code +
        widths.title +
        widths.type +
        widths.status +
        widths.priority +
        widths.estimate_points +
        widths.assignee_id +
        widths.actions
    );
    expect(issueListColumnLayout(0)).toEqual({ pinActions: false, titleWidth: 300 });
    expect(issueListColumnLayout(threshold - 1).pinActions).toBe(false);
    expect(issueListColumnLayout(threshold).pinActions).toBe(true);
    expect(issueListColumnLayout(threshold + 1).pinActions).toBe(true);
    expect(issueListColumnLayout(threshold).titleWidth).toBe(300);
  });

  it('returns the scroller inside the given root when an earlier full decoy exists', () => {
    const decoy = document.createElement('div');
    decoy.innerHTML =
      '<div class="n-data-table-base-table-body"><div class="n-scrollbar-container" id="decoy"></div></div>';
    const root = document.createElement('div');
    root.innerHTML =
      '<div class="n-data-table-base-table-body"><div class="n-scrollbar-container" id="real"></div></div>';
    document.body.append(decoy, root);
    expect(document.querySelector('.n-data-table-base-table-body .n-scrollbar-container')?.id).toBe('decoy');
    expect(listTableBodyScrollElement(root)?.id).toBe('real');
    expect(listTableBodyScrollElement(null)).toBeNull();
    decoy.remove();
    root.remove();
  });
});

function makeFakes() {
  const events: string[] = [];
  const resizeCallbacks: Array<() => void> = [];
  const mutationCallbacks: Array<() => void> = [];
  class Resize implements ListScrollResizeObserver {
    constructor(callback: () => void) {
      resizeCallbacks.push(callback);
    }
    observe(target: Element) {
      events.push(`resize-observe:${(target as HTMLElement).id}`);
    }
    disconnect() {
      events.push('resize-disconnect');
    }
  }
  class Mutation implements ListScrollMutationObserver {
    constructor(callback: () => void) {
      mutationCallbacks.push(callback);
    }
    observe(target: Node) {
      events.push(`mutation-observe:${(target as HTMLElement).id}`);
    }
    disconnect() {
      events.push('mutation-disconnect');
    }
  }
  const queued: Array<() => void> = [];
  return {
    events,
    resizeCallbacks,
    mutationCallbacks,
    Resize,
    Mutation,
    nextTick(callback: () => void) {
      queued.push(callback);
    },
    flush() {
      const callback = queued.shift();
      if (!callback) throw new Error('no queued nextTick');
      callback();
    }
  };
}

function addScroller(root: HTMLElement, id: string) {
  const body = document.createElement('div');
  body.className = 'n-data-table-base-table-body';
  const node = document.createElement('div');
  node.className = 'n-scrollbar-container';
  node.id = id;
  let width = 0;
  Object.defineProperty(node, 'clientWidth', { configurable: true, get: () => width });
  body.append(node);
  root.append(body);
  return { node, setWidth(value: number) { width = value; } };
}

describe('createListScrollBinder', () => {
  it('observes a zero-width node and stays unpinned', () => {
    const root = document.createElement('div');
    root.id = 'table';
    const scroller = addScroller(root, 'real');
    scroller.setWidth(0);
    const widths: number[] = [];
    const fakes = makeFakes();
    const binder = createListScrollBinder({
      getRoot: () => root,
      onWidth: width => widths.push(width),
      nextTick: fakes.nextTick,
      isActive: () => true,
      ResizeObserver: fakes.Resize,
      MutationObserver: fakes.Mutation
    });
    binder.schedule();
    fakes.flush();
    expect(widths).toEqual([0]);
    expect(issueListColumnLayout(0).pinActions).toBe(false);
    expect(fakes.events).toContain('resize-observe:real');
    root.remove();
  });

  it('publishes a positive width when the observed node grows', () => {
    const root = document.createElement('div');
    root.id = 'table';
    const scroller = addScroller(root, 'real');
    scroller.setWidth(0);
    const widths: number[] = [];
    const fakes = makeFakes();
    const binder = createListScrollBinder({
      getRoot: () => root,
      onWidth: width => widths.push(width),
      nextTick: fakes.nextTick,
      isActive: () => true,
      ResizeObserver: fakes.Resize,
      MutationObserver: fakes.Mutation
    });
    binder.schedule();
    fakes.flush();
    const threshold = issueListActionsPinThreshold();
    scroller.setWidth(threshold);
    fakes.resizeCallbacks[0]();
    expect(widths.at(-1)).toBe(threshold);
    expect(issueListColumnLayout(threshold).pinActions).toBe(true);
    expect(fakes.events.filter(event => event === 'resize-observe:real')).toHaveLength(1);
    root.remove();
  });

  it('binds a scroller that appears after the queued tick', () => {
    const root = document.createElement('div');
    root.id = 'table';
    const widths: number[] = [];
    const fakes = makeFakes();
    const binder = createListScrollBinder({
      getRoot: () => root,
      onWidth: width => widths.push(width),
      nextTick: fakes.nextTick,
      isActive: () => true,
      ResizeObserver: fakes.Resize,
      MutationObserver: fakes.Mutation
    });
    binder.schedule();
    fakes.flush();
    expect(widths).toEqual([0]);
    expect(fakes.events).toContain('mutation-observe:table');
    expect(fakes.events.some(event => event.startsWith('resize-observe'))).toBe(false);
    const scroller = addScroller(root, 'late');
    fakes.mutationCallbacks[0]();
    expect(fakes.events).toContain('resize-observe:late');
    expect(widths.at(-1)).toBe(0);
    scroller.setWidth(issueListActionsPinThreshold());
    fakes.resizeCallbacks[0]();
    expect(widths.at(-1)).toBe(issueListActionsPinThreshold());
    root.remove();
  });

  it('rebinds when the resize callback finds a replacement node', () => {
    const root = document.createElement('div');
    root.id = 'table';
    const old = addScroller(root, 'old');
    old.setWidth(10);
    const widths: number[] = [];
    const fakes = makeFakes();
    const binder = createListScrollBinder({
      getRoot: () => root,
      onWidth: width => widths.push(width),
      nextTick: fakes.nextTick,
      isActive: () => true,
      ResizeObserver: fakes.Resize,
      MutationObserver: fakes.Mutation
    });
    binder.schedule();
    fakes.flush();
    const first = fakes.resizeCallbacks[0];
    root.replaceChildren();
    const next = addScroller(root, 'next');
    next.setWidth(issueListActionsPinThreshold());
    first();
    expect(fakes.events).toContain('resize-disconnect');
    expect(fakes.events).toContain('resize-observe:next');
    expect(widths.at(-1)).toBe(issueListActionsPinThreshold());
    const after = { widths: widths.length, events: fakes.events.length };
    first();
    expect(widths.length).toBe(after.widths);
    expect(fakes.events.length).toBe(after.events);
    root.remove();
  });

  it('rebinds when the table root is removed and a new root is mounted', () => {
    const firstRoot = document.createElement('div');
    firstRoot.id = 'first';
    addScroller(firstRoot, 'first-scroll');
    const secondRoot = document.createElement('div');
    secondRoot.id = 'second';
    addScroller(secondRoot, 'second-scroll');
    let current: HTMLElement | null = firstRoot;
    let active = true;
    const widths: number[] = [];
    const fakes = makeFakes();
    const binder = createListScrollBinder({
      getRoot: () => current,
      onWidth: width => widths.push(width),
      nextTick: fakes.nextTick,
      isActive: () => active,
      ResizeObserver: fakes.Resize,
      MutationObserver: fakes.Mutation
    });
    binder.schedule();
    fakes.flush();
    const oldResize = fakes.resizeCallbacks[0];
    const oldMutation = fakes.mutationCallbacks[0];
    expect(fakes.events).toContain('resize-observe:first-scroll');
    current = null;
    binder.disconnect();
    current = secondRoot;
    binder.schedule();
    fakes.flush();
    expect(fakes.events).toContain('resize-observe:second-scroll');
    const afterSwitch = {
      widths: widths.length,
      observes: fakes.events.filter(event => event.startsWith('resize-observe') || event.startsWith('mutation-observe'))
    };
    oldResize();
    oldMutation();
    expect(widths.length).toBe(afterSwitch.widths);
    expect(fakes.events.filter(event => event.startsWith('resize-observe') || event.startsWith('mutation-observe'))).toEqual(
      afterSwitch.observes
    );
    active = false;
    binder.disconnect();
    const afterUnmount = widths.length;
    const observesAfterUnmount = fakes.events.filter(
      event => event.startsWith('resize-observe') || event.startsWith('mutation-observe')
    );
    oldResize();
    oldMutation();
    for (const callback of [...fakes.resizeCallbacks, ...fakes.mutationCallbacks]) callback();
    expect(widths.length).toBe(afterUnmount);
    expect(
      fakes.events.filter(event => event.startsWith('resize-observe') || event.startsWith('mutation-observe'))
    ).toEqual(observesAfterUnmount);
    firstRoot.remove();
    secondRoot.remove();
  });

  it('does not observe from a queued tick or an old callback after disconnect', () => {
    const root = document.createElement('div');
    root.id = 'table';
    addScroller(root, 'real');
    let active = true;
    const widths: number[] = [];
    const fakes = makeFakes();
    const binder = createListScrollBinder({
      getRoot: () => root,
      onWidth: width => widths.push(width),
      nextTick: fakes.nextTick,
      isActive: () => active,
      ResizeObserver: fakes.Resize,
      MutationObserver: fakes.Mutation
    });
    binder.schedule();
    fakes.flush();
    const saved = [...fakes.resizeCallbacks, ...fakes.mutationCallbacks];
    binder.schedule();
    active = false;
    binder.disconnect();
    fakes.flush();
    for (const callback of saved) callback();
    const observes = fakes.events.filter(event => event.startsWith('resize-observe') || event.startsWith('mutation-observe'));
    expect(observes).toEqual(['mutation-observe:table', 'resize-observe:real']);
    expect(widths).toEqual([0]);
    root.remove();
  });
});
```

- [ ] **Step 2: 跑红**

cwd：`/tmp/cursor/opentask-list-pin/frontend`

```bash
pnpm exec vitest run src/views/issue/list/column-layout.test.ts
```

Expected: FAIL，`EXIT` 非 0。失败原因是 `createListScrollBinder` 或 `issueListPinColumnWidths` 还没导出。

### Task 2: 实现门槛和绑定单元

**Files:**
- Modify: `frontend/src/views/issue/list/column-layout.ts`
- Test: `frontend/src/views/issue/list/column-layout.test.ts`

**Interfaces:**
- Consumes: `ISSUE_CODE_COLUMN_WIDTH`、`ISSUE_TITLE_COLUMN_MAX`
- Produces:
  - `issueListPinColumnWidths`
  - `issueListActionsPinThreshold(): number`
  - `listTableBodyScrollElement(root: ParentNode | null): HTMLElement | null`
  - `issueListColumnLayout(tableWidth: number): { pinActions: boolean; titleWidth: number }`
  - `createListScrollBinder(options: ListScrollBinderOptions): ListScrollBinder`

- [ ] **Step 1: 用下面的文件替换 `column-layout.ts`**

删掉 `ISSUE_ACTIONS_PIN_MIN`。`disconnect` 只增加代次并卸掉两个观察器，不在排队回调里重新 `observe`。0 宽节点仍交给 `ResizeObserver`。

```ts
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
    tableWidth <= 0 || pinActions
      ? ISSUE_TITLE_COLUMN_MAX
      : Math.min(ISSUE_TITLE_COLUMN_MAX, Math.max(160, available));
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
      const id = ++activeMutationId;
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
    const id = ++activeResizeId;
    resizeObserver = new options.ResizeObserver(() => {
      if (id !== activeResizeId) return;
      sync();
    });
    resizeObserver.observe(node);
  }

  return {
    schedule() {
      const token = ++generation;
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
```

- [ ] **Step 2: 跑绿**

```bash
cd /tmp/cursor/opentask-list-pin/frontend
pnpm exec vitest run src/views/issue/list/column-layout.test.ts
```

Expected: 全部 PASS，`EXIT 0`。

- [ ] **Step 3: 提交这一层**

```bash
cd /tmp/cursor/opentask-list-pin
git add frontend/src/views/issue/list/column-layout.ts frontend/src/views/issue/list/column-layout.test.ts
git commit -m "fix: pin issue list actions only when the row fits"
```

### Task 3: 页面只接绑定单元

**Files:**
- Modify: `frontend/src/views/issue/list/index.vue`
- Test: `frontend/src/views/issue/list/column-layout.test.ts` 里的接线断言

**Interfaces:**
- Consumes: `createListScrollBinder`、`issueListColumnLayout`、`issueListPinColumnWidths`
- Produces: 未分组 `NDataTable` 的 `ref="listTableRef"`。生命周期行为已由 Task 1 的假观察器证明。这一步的源码断言只证明页面调用了那个单元。

- [ ] **Step 1: 追加接线断言并确认失败**

```ts
import { readFileSync } from 'node:fs';

it('wires the list page to the scroll binder', () => {
  const index = readFileSync(new URL('./index.vue', import.meta.url), 'utf8');
  const unmounted = index.slice(index.indexOf('onUnmounted'));
  expect(index).toContain('ref="listTableRef"');
  expect(index).toContain('createListScrollBinder');
  expect(index).toContain('listScroll.schedule()');
  expect(index).toContain('listScroll.disconnect()');
  expect(unmounted.indexOf('listScrollActive.value = false')).toBeGreaterThanOrEqual(0);
  expect(unmounted.indexOf('listScroll.disconnect()')).toBeGreaterThan(unmounted.indexOf('listScrollActive.value = false'));
  expect(index).not.toContain('document.querySelector');
  expect(index).not.toContain("querySelector('.n-data-table')");
  expect(index).not.toContain('ISSUE_ACTIONS_PIN_MIN');
  expect(index).toContain("whiteSpace: 'normal'");
  expect(index).toContain('issueListPinColumnWidths.issue_code');
  expect(index).toContain('issueListPinColumnWidths.assignee_id');
  expect(index).toContain('issueListPinColumnWidths.actions');
  expect(index).toContain("key: 'reporter_id'");
  expect(index).toContain('width: 150');
});
```

```bash
cd /tmp/cursor/opentask-list-pin/frontend
pnpm exec vitest run src/views/issue/list/column-layout.test.ts
```

Expected: FAIL，`index.vue` 还没有 `ref="listTableRef"`。`EXIT` 非 0。

- [ ] **Step 2: 改 `index.vue`**

`vue` 的导入加上 `nextTick`。列布局导入改为：

```ts
import {
  createListScrollBinder,
  issueListColumnLayout,
  issueListPinColumnWidths
} from './column-layout';
```

`baseColumns` 里这八个 `width` 改成 `issueListPinColumnWidths` 的对应字段。渲染函数不动。`reporter_id` 仍是 `width: 120`。`created_at` 仍是 `width: 150`。自定义列仍是 `width: 120`。操作列对象里先留着 `fixed: 'right'`。`columns` 在 `pinActions` 为 false 时照旧删掉 `fixed`。

删掉 `issueListEl`、`readTableWidth`、`tableObserver`。换成：

```ts
const listTableRef = ref<{ $el?: unknown } | null>(null);
const tableWidth = ref(0);
const listScrollActive = ref(true);
const ResizeObserverCtor =
  typeof ResizeObserver === 'undefined'
    ? undefined
    : class {
        private observer: ResizeObserver;
        constructor(callback: () => void) {
          this.observer = new ResizeObserver(() => callback());
        }
        observe(target: Element) {
          this.observer.observe(target);
        }
        disconnect() {
          this.observer.disconnect();
        }
      };
const MutationObserverCtor =
  typeof MutationObserver === 'undefined'
    ? undefined
    : class {
        private observer: MutationObserver;
        constructor(callback: () => void) {
          this.observer = new MutationObserver(() => callback());
        }
        observe(target: Node, init: { childList: true; subtree: true }) {
          this.observer.observe(target, init);
        }
        disconnect() {
          this.observer.disconnect();
        }
      };
const listScroll = createListScrollBinder({
  getRoot: () => {
    const el = listTableRef.value?.$el;
    return el instanceof Element ? el : null;
  },
  onWidth: width => {
    tableWidth.value = width;
  },
  nextTick: callback => {
    void nextTick(callback);
  },
  isActive: () => listScrollActive.value,
  ResizeObserver: ResizeObserverCtor,
  MutationObserver: MutationObserverCtor
});

watch(
  listTableRef,
  inst => {
    if (!listScrollActive.value) return;
    if (!inst) {
      listScroll.disconnect();
      tableWidth.value = 0;
      return;
    }
    listScroll.schedule();
  },
  { flush: 'post' }
);
```

`onMounted` 里不再创建观察器，其余加载逻辑保留。`onUnmounted` 改成：

```ts
onUnmounted(() => {
  listScrollActive.value = false;
  listScroll.disconnect();
  tableWidth.value = 0;
  unsubRealtime?.();
  unsubRealtime = null;
});
```

未分组的 `<NDataTable` 加上 `ref="listTableRef"`。看板和 `IssueListGrouped` 不加。模板上的 `ref="issueListEl"` 删掉，类名 `issue-list-container` 保留。

- [ ] **Step 3: 跑绿**

```bash
cd /tmp/cursor/opentask-list-pin/frontend
pnpm exec vitest run src/views/issue/list/column-layout.test.ts
```

Expected: 全部 PASS，`EXIT 0`。

- [ ] **Step 4: 核对无变化行为**

```bash
cd /tmp/cursor/opentask-list-pin
git diff 088a34308cb0fe75a95f129432ee67b8f54067c3 -- \
  frontend/src/views/issue/list/index.vue \
  frontend/src/views/issue/list/column-layout.ts \
  frontend/src/views/issue/list/column-layout.test.ts \
  docs/superpowers/specs/2026-11-12-issue-list-pin-design.md \
  docs/superpowers/plans/2026-11-12-issue-list-pin.md
```

Expected: 只有这五个路径。`onListSortByUpdate`、`onListSortOrderUpdate`、`handleFilterChange`、`clearFilters`、`handleSmartSearch`、`loadWorkspaceRole` 的函数体不在 diff 里。`reporter_id` 的 `width: 120` 和 `created_at` 的 `width: 150` 不在 diff 里。标题仍有 `whiteSpace: 'normal'`。

- [ ] **Step 5: 提交接线**

```bash
git add frontend/src/views/issue/list/index.vue frontend/src/views/issue/list/column-layout.test.ts
git commit -m "fix: measure the issue list body scroller before pinning"
```

### Task 4: 用实测 clientWidth 校准几何

**Files:**
- 不改产品。脚本写到 `/tmp/cursor/opentask-readonly/list-pin-logs/<实施后的完整 SHA>/calibrate.mjs`，内容就是下面这一份。证据 JSON 和 git 原文放在同一目录。

**Interfaces:**
- Consumes: Task 3 的页面，以及 `issueListActionsPinThreshold()`
- Produces: 每次尝试的视口宽度、横滚节点 `clientWidth`、源码算出的 T、表头 left/right、操作列是否有 `n-data-table-td--fixed-right`、`elementFromPoint`。视口宽度不拿来和 T 比较。

- [ ] **Step 1: 用 prod 起服务**

cwd：`/tmp/cursor/opentask-list-pin/frontend`。沿用已忽略的 `.env.prod`。端口不要占用 9527 和 9530。

```bash
pnpm exec vite --mode prod --host 127.0.0.1 --port 9531 --strictPort
```

启动后跑 `git -C /tmp/cursor/opentask-list-pin status --porcelain`。有输出就停。

- [ ] **Step 2: 取出 T**

cwd：`/tmp/cursor/opentask-list-pin/frontend`。Node 22.23.4 对 `.ts` 文件支持 `--experimental-strip-types`。这个文件没有别的导入。

```bash
node --experimental-strip-types --input-type=module -e "import { issueListActionsPinThreshold } from './src/views/issue/list/column-layout.ts'; process.stdout.write(String(issueListActionsPinThreshold()))"
```

Expected: 一行整数，没有写死 1132。把它记为 `THRESHOLD`。

- [ ] **Step 3: 把下面的脚本写到该 SHA 目录并运行**

脚本在页面加载前替换 `ResizeObserver`，用 `__listScrollLive` 记录仍被 `observe`、还没 `disconnect` 的目标。明暗各先确认 `html` 的 `dark` 类；确认失败则该档 `blocked`，不再把测量写成通过。通过的档里做 375、768、1280、宽桌面，以及 `T - 1`、`T`、`T + 1` 和回到 `T - 1`。对不上目标宽度就停在当次尝试上，状态 `blocked`。侧栏按钮用 `折叠菜单` / `展开菜单`（`zh-cn.ts` 第 728–729 行）。看板和列表按钮文案是 `看板`、`列表`。分组选项是 `状态` 和 `不分组`。Tab 从横滚节点开始按键盘，不按 Enter，不点击「删除」。

```bash
SHA=$(git -C /tmp/cursor/opentask-list-pin rev-parse HEAD)
LOG=/tmp/cursor/opentask-readonly/list-pin-logs/$SHA
mkdir -p "$LOG"
{
  echo "DATE $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "CWD /tmp/cursor/opentask-list-pin"
  echo "HEAD $(git -C /tmp/cursor/opentask-list-pin rev-parse HEAD)"
  echo "PORCELAIN_BEGIN"
  git -C /tmp/cursor/opentask-list-pin status --porcelain
  echo "PORCELAIN_END"
  echo "PORCELAIN_BYTES $(git -C /tmp/cursor/opentask-list-pin status --porcelain | wc -c)"
} > "$LOG/git-before.txt"
cd /tmp/cursor/opentask-readonly
BASE_URL=http://127.0.0.1:9531 THRESHOLD="$THRESHOLD" OUT="$LOG/calibrate.json" node "$LOG/calibrate.mjs"
echo "CALIBRATE_EXIT $?"
{
  echo "DATE $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "CWD /tmp/cursor/opentask-list-pin"
  echo "HEAD $(git -C /tmp/cursor/opentask-list-pin rev-parse HEAD)"
  echo "PORCELAIN_BEGIN"
  git -C /tmp/cursor/opentask-list-pin status --porcelain
  echo "PORCELAIN_END"
  echo "PORCELAIN_BYTES $(git -C /tmp/cursor/opentask-list-pin status --porcelain | wc -c)"
} > "$LOG/git-after.txt"
```

`node` 的 cwd 是 `/tmp/cursor/opentask-readonly`，因为这里能解析 `playwright-core`。

Expected: `CALIBRATE_EXIT 0`，且 `failures` 为空。`matrix.light` 和 `matrix.dark` 的 `theme.status` 都是 `pass`。每一档的 375、768、1280 都有 `measured.clientWidth`，并且 `measured.fixed === (clientWidth > 0 && clientWidth >= THRESHOLD)`。`wide.measured.clientWidth >= THRESHOLD + wide.reporterWidth`，`wide.geometry` 里有报告人和创建时间的 left/right；这两列是否被操作列盖住只记录，不单独当失败。`clients` 里 `T - 1`、`T`、`T + 1` 和 `returnBelow` 的 `matched` 为 true，`clientWidth` 等于目标，`fixed` 符合同一条规则。`returnBelow` 证明从门槛上方折返后不再钉。校准 `status` 为 `blocked` 时 `attempts` 保持脚本写出的原样，整次退出码 2。`sider` 在重新设成 1280 之后，折叠和展开的 `clientWidth` 都与点击前不同，并且各自的 `fixed` 符合规则。`scroll.1280` 和 `scroll.wide` 都是在 `setViewportSize` 到这两个宽度之后测的；`scrollLeft` 与 `scrollWidth - clientWidth` 的差不超过 1。两处 `tab` 都先出现 `详情` 再出现 `删除`。这两处的 `requests` 没有 GET/HEAD/OPTIONS 以外的请求。`leaksOnBoard` 为空。分组泄漏为空。名字没注入时 `nameInjection.injected` 为 false，探针仍用「负责人」整格，不把缺名字写成通过。

```javascript
import { chromium } from 'playwright-core';
import { writeFileSync } from 'node:fs';

const base = process.env.BASE_URL;
const threshold = Number(process.env.THRESHOLD);
const out = process.env.OUT;
if (!base || !Number.isInteger(threshold) || threshold <= 0 || !out) {
  console.error('NEED BASE_URL, integer THRESHOLD, OUT');
  process.exit(2);
}

const report = { threshold, base, failures: [], matrix: {} };
const failures = report.failures;

function rule(clientWidth) {
  return clientWidth > 0 && clientWidth >= threshold;
}

function columnGeometry(measured) {
  const columns = measured?.columns || [];
  const find = text => columns.find(column => column.text === text) || null;
  const reporter = find('报告人');
  const created = find('创建时间');
  const actions = find('操作');
  const overlaps = (column, action) =>
    Boolean(column && action && column.right > action.left && column.left < action.right);
  return {
    reporter,
    created,
    actions,
    reporterOverlapsActions: overlaps(reporter, actions),
    createdOverlapsActions: overlaps(created, actions)
  };
}

const browser = await chromium.launch({
  executablePath: '/usr/bin/google-chrome',
  headless: true
});
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });

await page.addInitScript(() => {
  const Native = window.ResizeObserver;
  const live = new Set();
  window.__listScrollLive = live;
  window.ResizeObserver = class extends Native {
    constructor(callback) {
      super(callback);
      this._targets = new Set();
    }
    observe(target) {
      this._targets.add(target);
      live.add(target);
      return super.observe(target);
    }
    disconnect() {
      for (const target of this._targets) live.delete(target);
      this._targets.clear();
      return super.disconnect();
    }
  };
  localStorage.setItem('SOY_token', JSON.stringify('synthetic-token'));
  localStorage.setItem('SOY_refreshToken', JSON.stringify('synthetic-token'));
  localStorage.setItem('SOY_lang', JSON.stringify('zh-CN'));
});

await page.route('**/api/issues**', async route => {
  const response = await route.fetch();
  const text = await response.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    report.nameInjection = { injected: false, reason: 'not json' };
    await route.fulfill({ response, body: text });
    return;
  }
  const list = Array.isArray(body)
    ? body
    : Array.isArray(body?.data?.items)
      ? body.data.items
      : Array.isArray(body?.data)
        ? body.data
        : Array.isArray(body?.items)
          ? body.items
          : Array.isArray(body?.issues)
            ? body.issues
            : null;
  if (!list || !list[0] || !('assignee_id' in list[0] || 'assignee' in list[0])) {
    report.nameInjection = {
      injected: false,
      keys: body && typeof body === 'object' ? Object.keys(body) : typeof body
    };
    await route.fulfill({ response, body: text });
    return;
  }
  list[0].assignee_id = list[0].assignee_id || 'synthetic-assignee';
  list[0].assignee = { id: list[0].assignee_id, name: '合成负责人甲乙丙' };
  report.nameInjection = { injected: true };
  await route.fulfill({ response, body: JSON.stringify(body) });
});

function leaks() {
  return page.evaluate(() => {
    const live = window.__listScrollLive || new Set();
    return [...live]
      .filter(el => el.classList?.contains('n-scrollbar-container'))
      .filter(el => !el.isConnected || el.closest('.issue-list-container'))
      .map(el => ({ connected: el.isConnected, className: String(el.className) }));
  });
}

async function readTable() {
  return page.evaluate(() => {
    const tables = [...document.querySelectorAll('.issue-list-container .n-data-table')];
    if (tables.length !== 1) {
      return { tableCount: tables.length, clientWidth: null, columns: [], cells: [], fixed: null, probe: null };
    }
    const table = tables[0];
    const scroller = table.querySelector('.n-data-table-base-table-body .n-scrollbar-container');
    const columns = [...table.querySelectorAll('thead th')].map(th => {
      const rect = th.getBoundingClientRect();
      return {
        text: th.innerText.replace(/\s+/g, ' ').trim(),
        left: rect.left,
        right: rect.right,
        width: rect.width,
        className: String(th.className)
      };
    });
    const row = table.querySelector('tbody tr');
    const cells = row
      ? [...row.children].map(td => {
          const rect = td.getBoundingClientRect();
          return {
            text: td.innerText.replace(/\s+/g, ' ').trim().slice(0, 80),
            left: rect.left,
            right: rect.right,
            className: String(td.className)
          };
        })
      : [];
    const assigneeIndex = columns.findIndex(column => column.text === '负责人');
    let probe = null;
    if (row && assigneeIndex >= 0 && row.children[assigneeIndex]) {
      const rect = row.children[assigneeIndex].getBoundingClientRect();
      const x = rect.right - 6;
      const y = rect.top + rect.height / 2;
      const hit = document.elementFromPoint(x, y);
      probe = {
        x,
        y,
        tag: hit ? hit.tagName : null,
        className: hit ? String(hit.className) : null,
        text: hit ? (hit.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 40) : null
      };
    }
    const action = cells.find(cell => cell.text.includes('删除'));
    return {
      tableCount: 1,
      clientWidth: scroller instanceof HTMLElement ? scroller.clientWidth : null,
      scrollWidth: scroller instanceof HTMLElement ? scroller.scrollWidth : null,
      scrollLeft: scroller instanceof HTMLElement ? scroller.scrollLeft : null,
      columns,
      cells,
      fixed: action ? action.className.includes('n-data-table-td--fixed-right') : false,
      probe
    };
  });
}

async function settle() {
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function atViewport(width) {
  await page.setViewportSize({ width, height: 800 });
  await settle();
}

async function calibrate(target) {
  const attempts = [];
  let viewport = 1280;
  for (let i = 0; i < 8; i += 1) {
    const width = Math.max(320, Math.round(viewport));
    await atViewport(width);
    const measured = await readTable();
    attempts.push({
      viewport: width,
      clientWidth: measured.clientWidth,
      fixed: measured.fixed,
      columns: measured.columns,
      probe: measured.probe
    });
    if (measured.clientWidth === target) return { status: 'pass', matched: true, attempts, measured };
    if (typeof measured.clientWidth !== 'number') return { status: 'blocked', matched: false, attempts };
    viewport += target - measured.clientWidth;
  }
  return { status: 'blocked', matched: false, attempts };
}

function judgeExact(step, target, label) {
  if (!step.matched) {
    failures.push(`${label} blocked`);
    return step;
  }
  const expected = rule(step.measured.clientWidth);
  if (step.measured.clientWidth !== target || step.measured.fixed !== expected) {
    step.status = 'blocked';
    failures.push(`${label} pin`);
  }
  return step;
}

async function reachAtLeast(target) {
  const attempts = [];
  let viewport = 1400;
  for (let i = 0; i < 8; i += 1) {
    const width = Math.max(320, Math.round(viewport));
    await atViewport(width);
    const measured = await readTable();
    attempts.push({ viewport: width, clientWidth: measured.clientWidth, fixed: measured.fixed });
    if (typeof measured.clientWidth === 'number' && measured.clientWidth >= target) {
      return { status: 'pass', matched: true, attempts, measured, viewport: width };
    }
    if (typeof measured.clientWidth !== 'number') return { status: 'blocked', matched: false, attempts };
    viewport += target - measured.clientWidth;
  }
  return { status: 'blocked', matched: false, attempts };
}

async function tabTrail() {
  await page.evaluate(() => {
    const el = document.querySelector(
      '.issue-list-container .n-data-table .n-data-table-base-table-body .n-scrollbar-container'
    );
    if (el instanceof HTMLElement) el.focus();
  });
  const trail = [];
  for (let i = 0; i < 30; i += 1) {
    await page.keyboard.press('Tab');
    const text = await page.evaluate(() => (document.activeElement?.textContent || '').replace(/\s+/g, ' ').trim());
    trail.push(text);
    if (trail.includes('详情') && trail.includes('删除')) break;
  }
  return trail;
}

async function scrollAndTab(viewport) {
  await atViewport(viewport);
  const requests = [];
  const onRequest = request => {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) {
      requests.push({ method: request.method(), url: request.url() });
    }
  };
  page.on('request', onRequest);
  await page.evaluate(() => {
    const el = document.querySelector(
      '.issue-list-container .n-data-table .n-data-table-base-table-body .n-scrollbar-container'
    );
    if (el instanceof HTMLElement) el.scrollLeft = el.scrollWidth - el.clientWidth;
  });
  await settle();
  const measured = await readTable();
  const trail = await tabTrail();
  page.off('request', onRequest);
  const distance =
    typeof measured.scrollWidth === 'number' && typeof measured.clientWidth === 'number'
      ? measured.scrollWidth - measured.clientWidth
      : null;
  const scrollClose = distance !== null && typeof measured.scrollLeft === 'number' && Math.abs(measured.scrollLeft - distance) <= 1;
  const tabOk = trail.indexOf('详情') >= 0 && trail.indexOf('删除') > trail.indexOf('详情');
  if (!scrollClose) failures.push(`scroll ${viewport}`);
  if (!tabOk) failures.push(`tab ${viewport}`);
  if (requests.length !== 0) failures.push(`requests ${viewport}`);
  return { viewport, measured, trail, requests, scrollClose, tabOk };
}

async function scheme(name) {
  const raw = await page.evaluate(() => localStorage.getItem('SOY_themeSettings'));
  if (!raw) return { status: 'blocked', applied: false, reason: 'SOY_themeSettings missing' };
  let settings;
  try {
    settings = JSON.parse(raw);
  } catch {
    return { status: 'blocked', applied: false, reason: 'SOY_themeSettings not json' };
  }
  if (!settings || typeof settings !== 'object' || !('themeScheme' in settings)) {
    return { status: 'blocked', applied: false, reason: 'themeScheme absent' };
  }
  settings.themeScheme = name;
  await page.evaluate(value => localStorage.setItem('SOY_themeSettings', value), JSON.stringify(settings));
  await page.reload({ waitUntil: 'networkidle' });
  const htmlClass = await page.evaluate(() => document.documentElement.className);
  const dark = htmlClass.split(/\s+/).includes('dark');
  const applied = name === 'dark' ? dark : !dark;
  if (!applied) return { status: 'blocked', applied: false, reason: 'class mismatch', htmlClass, dark };
  return { status: 'pass', applied: true, htmlClass, dark };
}

async function fixedView(schemeName, width) {
  await atViewport(width);
  const measured = await readTable();
  if (typeof measured.clientWidth !== 'number') {
    failures.push(`${schemeName} ${width} blocked`);
    return { status: 'blocked', viewport: width, measured };
  }
  const expectedPin = rule(measured.clientWidth);
  const ok = measured.fixed === expectedPin;
  if (!ok) failures.push(`${schemeName} ${width} pin`);
  return { status: ok ? 'pass' : 'blocked', viewport: width, expectedPin, measured };
}

async function siderAt1280(schemeName) {
  await atViewport(1280);
  const collapse = page.getByRole('button', { name: '折叠菜单' });
  const collapseCount = await collapse.count();
  if (collapseCount !== 1) {
    failures.push(`${schemeName} sider blocked`);
    return { status: 'blocked', buttonCount: collapseCount };
  }
  const before = await readTable();
  await collapse.click();
  await settle();
  const collapsed = await readTable();
  const expand = page.getByRole('button', { name: '展开菜单' });
  const expandCount = await expand.count();
  let expanded = null;
  if (expandCount === 1) {
    await expand.click();
    await settle();
    expanded = await readTable();
  }
  const collapsedChanged = collapsed.clientWidth !== before.clientWidth;
  const expandedChanged = expanded ? expanded.clientWidth !== collapsed.clientWidth : false;
  const pinsOk = [before, collapsed, expanded].filter(Boolean).every(sample => {
    return typeof sample.clientWidth === 'number' && sample.fixed === rule(sample.clientWidth);
  });
  if (!collapsedChanged || !expandedChanged || !pinsOk) failures.push(`${schemeName} sider`);
  return {
    status: collapsedChanged && expandedChanged && pinsOk ? 'pass' : 'blocked',
    before,
    collapsed,
    expanded,
    collapsedChanged,
    expandedChanged
  };
}

await page.goto(`${base}/issue/list`, { waitUntil: 'networkidle' });

for (const schemeName of ['light', 'dark']) {
  const theme = await scheme(schemeName);
  const bucket = { theme, viewports: {}, clients: {}, wide: null, sider: null, scroll: {} };
  report.matrix[schemeName] = bucket;
  if (theme.status !== 'pass') {
    failures.push(`theme ${schemeName} blocked`);
    continue;
  }
  for (const width of [375, 768, 1280]) bucket.viewports[width] = await fixedView(schemeName, width);
  await atViewport(1600);
  const header = await readTable();
  const reporter = header.columns.find(column => column.text === '报告人');
  if (!reporter || !(reporter.width > 0)) {
    bucket.wide = { status: 'blocked', reason: 'reporter header missing', attempts: [] };
    failures.push(`${schemeName} wide blocked`);
  } else {
    const need = threshold + reporter.width;
    const wide = await reachAtLeast(need);
    wide.reporterWidth = reporter.width;
    wide.need = need;
    wide.geometry = wide.measured ? columnGeometry(wide.measured) : null;
    if (!wide.matched || !(wide.measured.clientWidth >= need) || wide.measured.fixed !== true) {
      wide.status = 'blocked';
      failures.push(`${schemeName} wide`);
    }
    bucket.wide = wide;
  }
  for (const target of [threshold - 1, threshold, threshold + 1]) {
    bucket.clients[String(target)] = judgeExact(await calibrate(target), target, `${schemeName} ${target}`);
  }
  bucket.clients.returnBelow = judgeExact(await calibrate(threshold - 1), threshold - 1, `${schemeName} returnBelow`);
  bucket.sider = await siderAt1280(schemeName);
  bucket.scroll['1280'] = await scrollAndTab(1280);
  if (bucket.wide?.status === 'pass') bucket.scroll.wide = await scrollAndTab(bucket.wide.viewport);
  else {
    bucket.scroll.wide = { status: 'blocked', reason: 'wide viewport unavailable' };
    failures.push(`${schemeName} scroll wide blocked`);
  }
}

await atViewport(1280);
const boardButton = page.getByRole('button', { name: '看板', exact: true });
if ((await boardButton.count()) !== 1) {
  report.board = { status: 'blocked' };
  failures.push('board blocked');
} else {
  await boardButton.click();
  await settle();
  report.leaksOnBoard = await leaks();
  if (report.leaksOnBoard.length !== 0) failures.push('board leaks');
  const listButton = page.getByRole('button', { name: '列表', exact: true });
  if ((await listButton.count()) !== 1) failures.push('list return blocked');
  else {
    await listButton.click();
    await settle();
    report.afterList = await readTable();
    if (typeof report.afterList.clientWidth !== 'number') failures.push('list return');
  }
}

const group = page.locator('.group-by-select').filter({ hasText: '分组' }).locator('.n-base-selection');
if ((await group.count()) !== 1) {
  report.group = { status: 'blocked', count: await group.count() };
  failures.push('group blocked');
} else {
  await group.click();
  const status = page.getByRole('option', { name: '状态', exact: true });
  if ((await status.count()) !== 1) {
    report.group = { status: 'blocked', optionCount: await status.count() };
    failures.push('group blocked');
  } else {
    await status.click();
    await settle();
    report.grouped = { table: await readTable(), leaks: await leaks() };
    if (report.grouped.leaks.length !== 0) failures.push('group leaks');
    await group.click();
    const none = page.getByRole('option', { name: '不分组', exact: true });
    if ((await none.count()) !== 1) failures.push('ungroup blocked');
    else {
      await none.click();
      await settle();
      report.ungrouped = { table: await readTable(), leaks: await leaks() };
      if (typeof report.ungrouped.table.clientWidth !== 'number') failures.push('ungroup');
    }
  }
}

writeFileSync(out, JSON.stringify(report, null, 2));
await browser.close();
process.exit(failures.length === 0 ? 0 : 2);
```

- [ ] **Step 4: 不在这一步提交产品**

证据留在 SHA 目录。几何和钉住状态不一致就停，把 JSON 交给 Yuri，不改白名单以外的文件。

### Task 5: 最终 SHA 的门禁和审阅

**Files:**
- 不改产品，除非 Task 4 已停下来并得到新的批准。

- [ ] **Step 1: 四个命令，stdout 和 stderr 都进新 SHA 目录**

cwd：`/tmp/cursor/opentask-list-pin/frontend`。不要覆盖 088a 目录。

```bash
pnpm exec vitest run
pnpm exec vite build --mode prod
pnpm exec vue-tsc --noEmit --skipLibCheck
pnpm exec eslint .
```

每个文件含 `DATE`、`SHA`、`CWD`、完整输出、`EXIT`。

Expected: vitest `EXIT 0`。build `EXIT 0`。vue-tsc `EXIT 2`，诊断行与 088a 基线逐条相同。eslint `EXIT 1`，诊断行与 088a 基线逐条相同。后两项仍是失败。

- [ ] **Step 2: 一对只读审阅**

模型参数用 `grok-4.7-high`。一个看 spec，一个看这五个路径的 diff。`run_in_background` 设为 false。审阅不得改产品。若调用在数毫秒内返回空会话，记下原始返回并停止，不要用同一调用再循环。

- [ ] **Step 3: 停在 Yuri 验收前**

不创建 PR，不 merge，不 deploy。
