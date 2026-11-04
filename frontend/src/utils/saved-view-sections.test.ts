import { describe, expect, it } from 'vitest';
import type { SavedView } from '@/service/api/saved-views';
import { buildSavedViewDropdownOptions, canWriteSavedView } from './saved-view-sections';

function view(partial: Partial<SavedView> & Pick<SavedView, 'id' | 'name'>): SavedView {
  return {
    workspaceId: 'ws',
    ownerUserId: 'u1',
    isFavorite: false,
    isShared: false,
    filter: {},
    createdAt: '',
    updatedAt: '',
    ...partial
  };
}

describe('buildSavedViewDropdownOptions', () => {
  it('returns empty placeholder when no views', () => {
    const opts = buildSavedViewDropdownOptions([], []);
    expect(opts).toEqual([{ label: '暂无已保存视图', key: '__empty', disabled: true }]);
  });

  it('partitions personal and shared into groups', () => {
    const personal = [view({ id: 'p1', name: 'Mine', isFavorite: true })];
    const shared = [view({ id: 's1', name: 'Team', isShared: true, ownerUserId: 'u2' })];
    const opts = buildSavedViewDropdownOptions(personal, shared);
    expect(opts).toHaveLength(2);
    expect(opts[0]).toMatchObject({ type: 'group', label: '我的', key: 'personal-group' });
    expect(opts[0].children).toEqual([{ label: '★ Mine', key: 'p1' }]);
    expect(opts[1]).toMatchObject({ type: 'group', label: '共享', key: 'shared-group' });
    expect(opts[1].children).toEqual([{ label: 'Team', key: 's1' }]);
  });
});

describe('canWriteSavedView', () => {
  it('allows personal owner only', () => {
    const v = view({ id: 'p', name: 'p', ownerUserId: 'u1', isShared: false });
    expect(canWriteSavedView(v, 'u1', 'member')).toBe(true);
    expect(canWriteSavedView(v, 'u2', 'owner')).toBe(false);
  });

  it('allows shared creator or workspace owner', () => {
    const v = view({ id: 's', name: 's', ownerUserId: 'u1', isShared: true });
    expect(canWriteSavedView(v, 'u1', 'member')).toBe(true);
    expect(canWriteSavedView(v, 'u2', 'owner')).toBe(true);
    expect(canWriteSavedView(v, 'u2', 'member')).toBe(false);
  });
});
