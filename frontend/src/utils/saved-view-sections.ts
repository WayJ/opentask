import type { SavedView } from '@/service/api/saved-views';

export interface SavedViewSectionOption {
  type?: 'group';
  label: string;
  key: string;
  disabled?: boolean;
  children?: Array<{ label: string; key: string }>;
}

/** Build Naive NDropdown options with 我的 / 共享 groups. */
export function buildSavedViewDropdownOptions(personal: SavedView[], shared: SavedView[]): SavedViewSectionOption[] {
  if (!personal.length && !shared.length) {
    return [{ label: '暂无已保存视图', key: '__empty', disabled: true }];
  }

  const options: SavedViewSectionOption[] = [];

  if (personal.length) {
    options.push({
      type: 'group',
      label: '我的',
      key: 'personal-group',
      children: personal.map(v => ({
        label: v.isFavorite ? `★ ${v.name}` : v.name,
        key: v.id
      }))
    });
  }

  if (shared.length) {
    options.push({
      type: 'group',
      label: '共享',
      key: 'shared-group',
      children: shared.map(v => ({
        label: v.name,
        key: v.id
      }))
    });
  }

  return options;
}

export function canWriteSavedView(
  view: SavedView,
  currentUserId: string,
  workspaceRole: string | null | undefined
): boolean {
  if (!view.isShared) {
    return view.ownerUserId === currentUserId;
  }
  return view.ownerUserId === currentUserId || workspaceRole === 'owner';
}
