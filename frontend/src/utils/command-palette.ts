export type PaletteItemKind = 'action' | 'menu' | 'issue' | 'project' | 'saved_view';

export interface PaletteItem {
  id: string;
  kind: PaletteItemKind;
  title: string;
  subtitle?: string;
  keywords?: string[];
  icon?: string;
  run: () => void | Promise<void>;
}

export interface PaletteGroup {
  id: string;
  label: string;
  items: PaletteItem[];
}

export function itemMatchesQuery(item: PaletteItem, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const hay = [item.title, item.subtitle ?? '', ...(item.keywords ?? [])].join(' ').toLowerCase();
  return hay.includes(q);
}

export function buildNavActions(
  navigate: (path: string) => void,
  titles: { issues: string; createIssue: string; projects: string; inbox: string }
): PaletteItem[] {
  return [
    {
      id: 'nav.issues',
      kind: 'action',
      title: titles.issues,
      keywords: ['issues', 'list', 'issue'],
      run: () => navigate('/issue/list')
    },
    {
      id: 'nav.create_issue',
      kind: 'action',
      title: titles.createIssue,
      keywords: ['create', 'new', 'issue'],
      run: () => navigate('/issue/create')
    },
    {
      id: 'nav.projects',
      kind: 'action',
      title: titles.projects,
      keywords: ['projects', 'project'],
      run: () => navigate('/workflow/projects')
    },
    {
      id: 'nav.inbox',
      kind: 'action',
      title: titles.inbox,
      keywords: ['inbox', '通知'],
      run: () => navigate('/inbox')
    }
  ];
}

export function menusToPaletteItems(
  menus: Array<{ routePath: string; label: string; i18nKey?: string | null }>,
  resolveTitle: (m: { routePath: string; label: string; i18nKey?: string | null }) => string,
  navigate: (path: string) => void
): PaletteItem[] {
  return menus.map(m => ({
    id: `menu.${m.routePath}`,
    kind: 'menu' as const,
    title: resolveTitle(m),
    keywords: [m.label, m.routePath],
    run: () => navigate(m.routePath)
  }));
}

export function buildPaletteGroups(opts: {
  actions: PaletteItem[];
  menus: PaletteItem[];
  query: string;
  groupLabels: {
    actions: string;
    menus: string;
    issues?: string;
    projects?: string;
    views?: string;
  };
  issues?: PaletteItem[];
  projects?: PaletteItem[];
  savedViews?: PaletteItem[];
}): PaletteGroup[] {
  const groups: PaletteGroup[] = [];
  const q = opts.query.trim();
  const actionItems = opts.actions.filter(i => itemMatchesQuery(i, opts.query));
  if (actionItems.length) {
    groups.push({ id: 'actions', label: opts.groupLabels.actions, items: actionItems });
  }

  // Menus require a non-empty query (legacy soybean search behavior).
  const menuItems = opts.menus.filter(i => itemMatchesQuery(i, opts.query));
  if (q && menuItems.length) {
    groups.push({ id: 'menus', label: opts.groupLabels.menus, items: menuItems });
  }

  // Entity groups only when the user is actively searching.
  if (q) {
    if (opts.issues?.length) {
      groups.push({
        id: 'issues',
        label: opts.groupLabels.issues ?? 'Issues',
        items: opts.issues
      });
    }
    if (opts.projects?.length) {
      groups.push({
        id: 'projects',
        label: opts.groupLabels.projects ?? 'Projects',
        items: opts.projects
      });
    }
    if (opts.savedViews?.length) {
      groups.push({
        id: 'views',
        label: opts.groupLabels.views ?? 'Views',
        items: opts.savedViews
      });
    }
  }

  return groups;
}

export function flattenGroupItems(groups: PaletteGroup[]): PaletteItem[] {
  return groups.flatMap(g => g.items);
}

export function clampActiveIndex(index: number, length: number): number {
  if (length <= 0) return 0;
  if (index < 0) return 0;
  if (index >= length) return length - 1;
  return index;
}
