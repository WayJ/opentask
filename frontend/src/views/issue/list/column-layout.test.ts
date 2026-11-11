import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';
import {
  ISSUE_CODE_COLUMN_WIDTH,
  type ListScrollMutationObserver,
  type ListScrollResizeObserver,
  createListScrollBinder,
  issueListActionsPinThreshold,
  issueListColumnLayout,
  issueListPinColumnWidths,
  listTableBodyScrollElement
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
    private readonly label = 'resize';
    constructor(callback: () => void) {
      resizeCallbacks.push(callback);
    }
    observe(target: Element) {
      events.push(`${this.label}-observe:${(target as HTMLElement).id}`);
    }
    disconnect() {
      events.push(`${this.label}-disconnect`);
    }
  }
  class Mutation implements ListScrollMutationObserver {
    private readonly label = 'mutation';
    constructor(callback: () => void) {
      mutationCallbacks.push(callback);
    }
    observe(target: Node) {
      events.push(`${this.label}-observe:${(target as HTMLElement).id}`);
    }
    disconnect() {
      events.push(`${this.label}-disconnect`);
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
  return {
    node,
    setWidth(value: number) {
      width = value;
    }
  };
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
    expect(
      fakes.events.filter(event => event.startsWith('resize-observe') || event.startsWith('mutation-observe'))
    ).toEqual(afterSwitch.observes);
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
    const observes = fakes.events.filter(
      event => event.startsWith('resize-observe') || event.startsWith('mutation-observe')
    );
    expect(observes).toEqual(['mutation-observe:table', 'resize-observe:real']);
    expect(widths).toEqual([0]);
    root.remove();
  });
});

it('wires the list page to the scroll binder', () => {
  const index = readFileSync(join(process.cwd(), 'src/views/issue/list/index.vue'), 'utf8');
  const unmounted = index.slice(index.indexOf('onUnmounted(() =>'));
  expect(index).toContain('ref="listTableRef"');
  expect(index).toContain('createListScrollBinder');
  expect(index).toContain('listScroll.schedule()');
  expect(index).toContain('listScroll.disconnect()');
  expect(unmounted.indexOf('listScrollActive.value = false')).toBeGreaterThanOrEqual(0);
  expect(unmounted.indexOf('listScroll.disconnect()')).toBeGreaterThan(
    unmounted.indexOf('listScrollActive.value = false')
  );
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
