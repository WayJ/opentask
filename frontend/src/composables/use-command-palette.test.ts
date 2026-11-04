import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PaletteItem } from '@/utils/command-palette';
import { __resetCommandPaletteForTests, useCommandPalette } from './use-command-palette';

describe('useCommandPalette', () => {
  beforeEach(() => {
    __resetCommandPaletteForTests();
  });

  it('open/close/toggle and clears query on close', () => {
    const p = useCommandPalette();
    expect(p.isOpen.value).toBe(false);
    p.open();
    expect(p.isOpen.value).toBe(true);
    p.setQuery('abc');
    expect(p.query.value).toBe('abc');
    p.close();
    expect(p.isOpen.value).toBe(false);
    expect(p.query.value).toBe('');
    p.toggle();
    expect(p.isOpen.value).toBe(true);
    p.toggle();
    expect(p.isOpen.value).toBe(false);
  });

  it('groups actions and navigates on runActive', async () => {
    const runIssues = vi.fn();
    const runInbox = vi.fn();
    const actions: PaletteItem[] = [
      { id: 'nav.issues', kind: 'action', title: 'Issues', run: runIssues },
      { id: 'nav.inbox', kind: 'action', title: 'Inbox', keywords: ['inbox'], run: runInbox }
    ];
    const p = useCommandPalette();
    p.setSources({ actions, menus: [] });
    p.open();
    expect(p.groups.value[0].items).toHaveLength(2);
    p.setQuery('inbox');
    expect(p.flatItems.value.map(i => i.id)).toEqual(['nav.inbox']);
    expect(p.activeIndex.value).toBe(0);
    await p.runActive();
    expect(runInbox).toHaveBeenCalled();
    expect(p.isOpen.value).toBe(false);
  });

  it('moveDown/moveUp wraps', () => {
    const p = useCommandPalette();
    p.setSources({
      actions: [
        { id: 'a', kind: 'action', title: 'A', run: () => undefined },
        { id: 'b', kind: 'action', title: 'B', run: () => undefined }
      ],
      menus: []
    });
    p.open();
    p.moveDown();
    expect(p.activeIndex.value).toBe(1);
    p.moveDown();
    expect(p.activeIndex.value).toBe(0);
    p.moveUp();
    expect(p.activeIndex.value).toBe(1);
  });
});
