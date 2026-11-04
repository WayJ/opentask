export type PaletteItemKind = 'action' | 'menu' | 'issue' | 'project' | 'saved_view' | 'cycle';

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
  titles: {
    issues: string;
    createIssue: string;
    createFromTemplate?: string;
    projects: string;
    inbox: string;
    triage?: string;
    initiatives?: string;
    cycles?: string;
    labels?: string;
    issueTemplates?: string;
  }
): PaletteItem[] {
  const items: PaletteItem[] = [
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
  if (titles.triage) {
    items.push({
      id: 'nav.triage',
      kind: 'action',
      title: titles.triage,
      keywords: ['triage', '分诊', '入站'],
      run: () => navigate('/triage')
    });
  }
  if (titles.initiatives) {
    items.push({
      id: 'nav.initiatives',
      kind: 'action',
      title: titles.initiatives,
      keywords: ['initiatives', 'initiative', '战略', '目标'],
      run: () => navigate('/initiatives')
    });
  }
  if (titles.cycles) {
    items.push({
      id: 'nav.cycles',
      kind: 'action',
      title: titles.cycles,
      keywords: ['cycles', 'cycle', '冲刺'],
      run: () => navigate('/workspace/cycles')
    });
  }
  if (titles.labels) {
    items.push({
      id: 'nav.labels',
      kind: 'action',
      title: titles.labels,
      keywords: ['labels', 'label', 'tags', '标签'],
      run: () => navigate('/workspace/labels')
    });
  }
  if (titles.createFromTemplate) {
    items.push({
      id: 'nav.create_from_template',
      kind: 'action',
      title: titles.createFromTemplate,
      keywords: ['template', 'templates', '从模板', '模板', 'create'],
      run: () => navigate('/issue/create?pickTemplate=1')
    });
  }
  if (titles.issueTemplates) {
    items.push({
      id: 'nav.issue_templates',
      kind: 'action',
      title: titles.issueTemplates,
      keywords: ['issue templates', 'templates', '模板设置'],
      run: () => navigate('/workspace/issue-templates')
    });
  }
  return items;
}

/** Focus-dependent issue actions (⌘K minimal label action). */
export function buildFocusIssueActions(opts: {
  hasFocusedIssue: boolean;
  openLabels: () => void;
  openEstimate?: () => void;
  title?: string;
  estimateTitle?: string;
}): PaletteItem[] {
  if (!opts.hasFocusedIssue) return [];
  const items: PaletteItem[] = [
    {
      id: 'action.labels',
      kind: 'action',
      title: opts.title ?? 'Add label…',
      keywords: ['label', 'labels', 'tag', 'tags', '标签', 'L'],
      run: () => opts.openLabels()
    }
  ];
  if (opts.openEstimate) {
    items.push({
      id: 'action.estimate',
      kind: 'action',
      title: opts.estimateTitle ?? 'Set estimate…',
      keywords: ['estimate', 'points', '估点', 'story points', 'E'],
      run: () => opts.openEstimate?.()
    });
  }
  return items;
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
    cycles?: string;
  };
  issues?: PaletteItem[];
  projects?: PaletteItem[];
  savedViews?: PaletteItem[];
  cycles?: PaletteItem[];
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
    if (opts.cycles?.length) {
      groups.push({
        id: 'cycles',
        label: opts.groupLabels.cycles ?? 'Cycles',
        items: opts.cycles
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
