import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';
import { $t, getLocale, setLocale } from '@/locales';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

function readSrc(path: string): string {
  return readFileSync(resolve(process.cwd(), path), 'utf8');
}

const favoritesVue = readSrc('src/layouts/modules/global-sider/FavoritesNav.vue');
const headerVue = readSrc('src/layouts/modules/global-header/index.vue');
const switcherVue = readSrc('src/layouts/modules/global-header/components/workspace-switcher.vue');
const hotkeyVue = readSrc('src/layouts/modules/global-search/issue-hotkey-picker-host.vue');
const paletteVue = readSrc('src/layouts/modules/global-search/command-palette-host.vue');
const favoritesUtil = readSrc('src/utils/favorites.ts');
const commandPaletteUtil = readSrc('src/utils/command-palette.ts');
const constantsTs = readSrc('src/constants/issue.ts');
const boardTest = readSrc('src/locales/__tests__/issue-list-board-chrome.test.ts');
const composerTest = readSrc('src/locales/__tests__/issue-composer-chrome.test.ts');
const displayPrefs = readSrc('src/utils/display-prefs.ts');
const zhSrc = readSrc('src/locales/langs/zh-cn.ts');
const enSrc = readSrc('src/locales/langs/en-us.ts');
const typings = readSrc('src/typings/app.d.ts');

const groups = {
  favorites: ['title', 'empty'],
  realtime: ['connected', 'disconnected'],
  workspaceSwitcher: [
    'placeholder',
    'createTitle',
    'namePlaceholder',
    'issueKeyPlaceholder',
    'issueKeyHint',
    'createFailed'
  ],
  hotkeyPicker: [
    'changeStatus',
    'assignOwner',
    'changePriority',
    'setLabels',
    'setEstimate',
    'noFocusedIssue',
    'selectOwner',
    'confirmAssign',
    'noLabels',
    'points',
    'clearEstimate',
    'updateStatusFailed',
    'statusUpdated',
    'updateEstimateFailed',
    'estimateUpdated',
    'updatePriorityFailed',
    'priorityUpdated',
    'assignFailed',
    'ownerUpdated',
    'updateLabelsFailed',
    'labelsUpdated'
  ]
} as const;

const zhCopy = {
  favorites: {
    title: '收藏',
    empty: '暂无侧栏收藏'
  },
  realtime: {
    connected: '实时已连接',
    disconnected: '实时未连接（重连中）'
  },
  workspaceSwitcher: {
    placeholder: '工作区',
    createTitle: '创建工作区',
    namePlaceholder: '工作区名称',
    issueKeyPlaceholder: '问题单号（可选，2–6 位大写）',
    issueKeyHint: '留空则从名称自动生成；创建后可在冲刺设置中修改。',
    createFailed: '创建失败'
  },
  hotkeyPicker: {
    changeStatus: '更改状态',
    assignOwner: '指派负责人',
    changePriority: '更改优先级',
    setLabels: '设置标签',
    setEstimate: '设置估点',
    noFocusedIssue: '无焦点问题',
    selectOwner: '选择负责人',
    confirmAssign: '确认指派',
    noLabels: '暂无标签，请先到 Labels 设置页创建',
    points: '{n} 点',
    clearEstimate: '清除估点',
    updateStatusFailed: '更新状态失败',
    statusUpdated: '状态已更新',
    updateEstimateFailed: '更新估点失败',
    estimateUpdated: '估点已更新',
    updatePriorityFailed: '更新优先级失败',
    priorityUpdated: '优先级已更新',
    assignFailed: '指派失败',
    ownerUpdated: '负责人已更新',
    updateLabelsFailed: '更新标签失败',
    labelsUpdated: '标签已更新'
  }
} as const;

const enCopy = {
  favorites: {
    title: 'Favorites',
    empty: 'No sidebar favorites'
  },
  realtime: {
    connected: 'Live connection on',
    disconnected: 'Live connection off (reconnecting)'
  },
  workspaceSwitcher: {
    placeholder: 'Workspace',
    createTitle: 'Create workspace',
    namePlaceholder: 'Workspace name',
    issueKeyPlaceholder: 'Issue key (optional, 2–6 uppercase letters)',
    issueKeyHint: 'Leave blank to generate from the name. You can change this later in cycle settings.',
    createFailed: 'Couldn\u2019t create the workspace'
  },
  hotkeyPicker: {
    changeStatus: 'Change status',
    assignOwner: 'Assign owner',
    changePriority: 'Change priority',
    setLabels: 'Set labels',
    setEstimate: 'Set estimate',
    noFocusedIssue: 'No focused issue',
    selectOwner: 'Select owner',
    confirmAssign: 'Confirm assignment',
    noLabels: 'No labels yet. Create them on the Labels settings page.',
    points: '{n} pts',
    clearEstimate: 'Clear estimate',
    updateStatusFailed: 'Couldn\u2019t update the status',
    statusUpdated: 'Status updated',
    updateEstimateFailed: 'Couldn\u2019t update the estimate',
    estimateUpdated: 'Estimate updated',
    updatePriorityFailed: 'Couldn\u2019t update the priority',
    priorityUpdated: 'Priority updated',
    assignFailed: 'Couldn\u2019t assign the owner',
    ownerUpdated: 'Owner updated',
    updateLabelsFailed: 'Couldn\u2019t update the labels',
    labelsUpdated: 'Labels updated'
  }
} as const;

const zhEstimateTitle = '设置估点\u2026';
const enEstimateTitle = 'Set estimate\u2026';

function countCalls(src: string, key: string): number {
  const exact = src.split(`$t('${key}')`).length - 1;
  const named = src.split(`$t('${key}',`).length - 1;
  return exact + named;
}

function extractBlock(source: string, key: string): string {
  const re = new RegExp(`(?:^|[\\n\\r{}\\s;])${key}\\s*:\\s*\\{`, 'm');
  const match = re.exec(source);
  if (!match) return '';
  const start = match.index + match[0].lastIndexOf('{');
  let depth = 0;
  for (let i = start; i < source.length; i += 1) {
    if (source[i] === '{') depth += 1;
    else if (source[i] === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(start, i + 1);
    }
  }
  return '';
}

function blockKeys(body: string): string[] {
  return [...body.matchAll(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:/gm)].map(item => item[1]);
}

function effectHasLeadingVoidLocale(src: string, haystack: string): boolean {
  const start = src.indexOf(haystack);
  if (start < 0) return false;
  const slice = src.slice(start, start + 400);
  return /void\s+locale\.value;/.test(slice);
}

describe('app shell English chrome', () => {
  it('locks the new keys in zh, en, and the schema', () => {
    expect(enSrc).not.toMatch(/[\u4E00-\u9FFF]/);
    const shellSources = [extractBlock(zhSrc, 'shell'), extractBlock(enSrc, 'shell'), extractBlock(typings, 'shell')];
    for (const shell of shellSources) {
      expect(shell).not.toBe('');
      for (const [group, keys] of Object.entries(groups)) {
        expect(blockKeys(extractBlock(shell, group)).sort()).toEqual([...keys].sort());
      }
    }
    const paletteSources = [
      extractBlock(zhSrc, 'commandPalette'),
      extractBlock(enSrc, 'commandPalette'),
      extractBlock(typings, 'commandPalette')
    ];
    for (const palette of paletteSources) {
      expect(palette).not.toBe('');
      expect(blockKeys(palette)).toContain('estimateTitle');
    }
    for (const group of Object.keys(groups) as (keyof typeof groups)[]) {
      for (const key of groups[group]) {
        expect(zh.page.shell[group][key]).toBe(zhCopy[group][key]);
        expect(en.page.shell[group][key]).toBe(enCopy[group][key]);
      }
    }
    expect(zh.common.commandPalette.estimateTitle).toBe(zhEstimateTitle);
    expect(en.common.commandPalette.estimateTitle).toBe(enEstimateTitle);
    expect(zh.common.commandPalette.estimateTitle).toContain('\u2026');
    expect(en.common.commandPalette.estimateTitle).toContain('\u2026');
    expect(zh.common.commandPalette.estimateTitle).not.toContain('...');
    expect(en.common.commandPalette.estimateTitle).not.toContain('...');
    expect(zh.page.shell.workspaceSwitcher.issueKeyPlaceholder).toContain('\u2013');
    expect(en.page.shell.workspaceSwitcher.issueKeyPlaceholder).toContain('\u2013');
    expect(en.page.shell.workspaceSwitcher.createFailed).toContain('\u2019');
    expect(en.page.shell.hotkeyPicker.updateStatusFailed).toContain('\u2019');
    expect(zh.page.shell.hotkeyPicker.noLabels).toContain('Labels');
    expect(zh.common.confirm).toBe('确认');
    expect(en.common.confirm).toBe('Confirm');
    expect(zh.page.issueDetail.create).toBe('创建');
    expect(en.page.issueDetail.create).toBe('Create');
    expect(zh.route.workspace).toBe('工作区');
    expect(en.route.workspace).toBe('Workspace');
    expect(zh.route['workspace-onboarding']).toBe('创建工作区');
    expect(en.route['workspace-onboarding']).toBe('Create workspace');
    expect(zh.page.shell.issueKeyPrefix).toBe('问题单号');
    expect(en.page.shell.issueKeyPrefix).toBe('Issue key');
  });

  it('binds FavoritesNav chrome without reusing near-synonym keys', () => {
    expect(countCalls(favoritesVue, 'page.shell.favorites.title')).toBe(1);
    expect(countCalls(favoritesVue, 'page.shell.favorites.empty')).toBe(1);
    expect(favoritesVue).toContain('page.shell.favoriteProject');
    expect(favoritesVue).toContain('page.shell.favoriteView');
    expect(favoritesVue).toContain('page.shell.favoriteIssue');
    expect(favoritesVue).toContain('page.shell.favoriteInitiative');
    expect(favoritesVue).toContain('FAVORITE_TYPE_LABEL');
    expect(favoritesVue).not.toContain('page.issueList.views.favoriteViews');
    expect(favoritesVue).not.toContain('page.issueList.toolbar.pinToSidebar');
    expect(favoritesVue).not.toMatch(/>收藏<\/NText>/);
    expect(favoritesVue).not.toContain("'暂无侧栏收藏'");
  });

  it('binds the realtime title and keeps the visible dot', () => {
    expect(countCalls(headerVue, 'page.shell.realtime.connected')).toBe(1);
    expect(countCalls(headerVue, 'page.shell.realtime.disconnected')).toBe(1);
    expect(headerVue).toContain('●');
    expect(headerVue).not.toContain("'实时已连接'");
    expect(headerVue).not.toContain("'实时未连接（重连中）'");
    expect(headerVue).not.toContain('useI18n');
  });

  it('binds the workspace switcher with decisions A and B', () => {
    expect(countCalls(switcherVue, 'page.shell.workspaceSwitcher.placeholder')).toBe(1);
    expect(countCalls(switcherVue, 'page.shell.workspaceSwitcher.createTitle')).toBe(1);
    expect(countCalls(switcherVue, 'page.issueDetail.create')).toBe(1);
    expect(countCalls(switcherVue, 'page.shell.workspaceSwitcher.namePlaceholder')).toBe(1);
    expect(countCalls(switcherVue, 'page.shell.workspaceSwitcher.issueKeyPlaceholder')).toBe(1);
    expect(countCalls(switcherVue, 'page.shell.workspaceSwitcher.issueKeyHint')).toBe(1);
    expect(countCalls(switcherVue, 'page.shell.workspaceSwitcher.createFailed')).toBe(1);
    expect(switcherVue).not.toContain('route.workspace-onboarding');
    expect(switcherVue).not.toContain("$t('route.workspace')");
    expect(switcherVue).not.toContain('page.shell.issueKeyPrefix');
    expect(switcherVue).not.toContain('placeholder="工作区"');
    expect(switcherVue).not.toContain('title="创建工作区"');
    expect(switcherVue).not.toContain('positive-text="创建"');
    expect(switcherVue).not.toContain('placeholder="工作区名称"');
    expect(switcherVue).not.toContain('placeholder="问题单号（可选，2–6 位大写）"');
    expect(switcherVue).not.toContain('留空则从名称自动生成；创建后可在冲刺设置中修改。');
    expect(switcherVue).not.toContain("'创建失败'");
  });

  it('binds the hotkey picker, points interpolation, and label tables', () => {
    for (const key of [
      'changeStatus',
      'assignOwner',
      'changePriority',
      'setLabels',
      'setEstimate',
      'noFocusedIssue',
      'selectOwner',
      'confirmAssign',
      'noLabels',
      'clearEstimate',
      'updateStatusFailed',
      'statusUpdated',
      'updateEstimateFailed',
      'estimateUpdated',
      'updatePriorityFailed',
      'priorityUpdated',
      'assignFailed',
      'ownerUpdated',
      'updateLabelsFailed',
      'labelsUpdated'
    ]) {
      expect(countCalls(hotkeyVue, `page.shell.hotkeyPicker.${key}`)).toBe(1);
    }
    expect(countCalls(hotkeyVue, 'page.shell.hotkeyPicker.points')).toBe(1);
    expect(hotkeyVue).toContain("$t('page.shell.hotkeyPicker.points', { n: pts })");
    expect(hotkeyVue).not.toContain(".replace('{n}'");
    expect(countCalls(hotkeyVue, 'common.confirm')).toBe(1);
    expect(hotkeyVue).toContain("useLabelTable('page.issueStatus')");
    expect(hotkeyVue).toContain("useLabelTable('page.issuePriority')");
    expect(hotkeyVue).toContain('lookupLabel(');
    expect(hotkeyVue).toContain('issueStatusOptions');
    expect(hotkeyVue).toContain('issuePriorityOptions');
    expect(effectHasLeadingVoidLocale(hotkeyVue, 'const title = computed(')).toBe(true);
    expect(effectHasLeadingVoidLocale(hotkeyVue, 'const statusSelectOptions = computed(')).toBe(true);
    expect(effectHasLeadingVoidLocale(hotkeyVue, 'const prioritySelectOptions = computed(')).toBe(true);
    expect(hotkeyVue).not.toContain('route.workspace-onboarding');
    expect(hotkeyVue).not.toMatch(/return '更改状态'/);
    expect(hotkeyVue).not.toMatch(/return '指派负责人'/);
    expect(hotkeyVue).not.toMatch(/return '更改优先级'/);
    expect(hotkeyVue).not.toMatch(/return '设置标签'/);
    expect(hotkeyVue).not.toMatch(/return '设置估点'/);
    expect(hotkeyVue).not.toContain('>无焦点问题<');
    expect(hotkeyVue).not.toContain('placeholder="选择负责人"');
    expect(hotkeyVue).not.toContain('>确认指派<');
    expect(hotkeyVue).not.toContain('暂无标签，请先到 Labels 设置页创建');
    expect(hotkeyVue).not.toContain('>确认<');
    expect(hotkeyVue).not.toContain('{{ pts }} 点');
    expect(hotkeyVue).not.toContain('>清除估点<');
    expect(hotkeyVue).not.toContain("'更新状态失败'");
    expect(hotkeyVue).not.toContain("'状态已更新'");
    expect(hotkeyVue).not.toContain("'更新估点失败'");
    expect(hotkeyVue).not.toContain("'估点已更新'");
    expect(hotkeyVue).not.toContain("'更新优先级失败'");
    expect(hotkeyVue).not.toContain("'优先级已更新'");
    expect(hotkeyVue).not.toContain("'指派失败'");
    expect(hotkeyVue).not.toContain("'负责人已更新'");
    expect(hotkeyVue).not.toContain("'更新标签失败'");
    expect(hotkeyVue).not.toContain("'标签已更新'");
    expect(hotkeyVue).not.toContain('useI18n');
  });

  it('binds command palette estimateTitle without rewriting other palette actions', () => {
    expect(countCalls(paletteVue, 'common.commandPalette.estimateTitle')).toBe(1);
    expect(countCalls(paletteVue, 'common.commandPalette.actionAddLabel')).toBe(1);
    expect(countCalls(paletteVue, 'common.commandPalette.navSearch')).toBe(1);
    expect(paletteVue).not.toContain("estimateTitle: '设置估点\u2026'");
    expect(paletteVue).not.toContain("estimateTitle: '设置估点...'");
    expect(effectHasLeadingVoidLocale(paletteVue, 'watchEffect(() => {')).toBe(true);
    expect(paletteVue).not.toContain('useI18n');
  });

  it('keeps out-of-scope source strings and prior-slice freezes', () => {
    expect(favoritesUtil).toContain("project: '项目'");
    expect(favoritesUtil).toContain("saved_view: '视图'");
    expect(favoritesUtil).toContain("issue: '问题'");
    expect(favoritesUtil).toContain("initiative: '举措'");
    expect(constantsTs).toContain("label: '待办'");
    expect(constantsTs).toContain("label: '低'");
    expect(boardTest).toContain("label: '待办'");
    expect(boardTest).toContain("label: '低'");
    expect(boardTest).toContain("return value ? '是' : '否'");
    expect(displayPrefs).toContain("return value ? '是' : '否'");
    expect(composerTest).toContain('自定义字段（可选）');
    expect(composerTest).toContain('加载中...');
    expect(commandPaletteUtil).toContain('keywords');
  });

  it('resolves locked strings from the real i18n catalog', () => {
    const previous = getLocale();
    try {
      setLocale('zh-CN');
      expect($t('page.shell.favorites.title')).toBe('收藏');
      expect($t('page.shell.favorites.empty')).toBe('暂无侧栏收藏');
      expect($t('page.shell.realtime.connected')).toBe('实时已连接');
      expect($t('page.shell.workspaceSwitcher.createTitle')).toBe('创建工作区');
      expect($t('page.shell.workspaceSwitcher.placeholder')).toBe('工作区');
      expect($t('page.issueDetail.create')).toBe('创建');
      expect($t('common.confirm')).toBe('确认');
      expect($t('page.shell.hotkeyPicker.points', { n: 5 })).toBe('5 点');
      expect($t('page.shell.hotkeyPicker.noLabels')).toBe('暂无标签，请先到 Labels 设置页创建');
      expect($t('common.commandPalette.estimateTitle')).toBe('设置估点\u2026');
      expect($t('page.issueStatus.open')).toBe('待办');
      expect($t('page.issuePriority.low')).toBe('低');
      setLocale('en-US');
      expect($t('page.shell.favorites.title')).toBe('Favorites');
      expect($t('page.shell.realtime.connected')).toBe('Live connection on');
      expect($t('page.shell.realtime.disconnected')).toBe('Live connection off (reconnecting)');
      expect($t('page.shell.workspaceSwitcher.createTitle')).toBe('Create workspace');
      expect($t('page.shell.workspaceSwitcher.createFailed')).toBe('Couldn\u2019t create the workspace');
      expect($t('page.issueDetail.create')).toBe('Create');
      expect($t('common.confirm')).toBe('Confirm');
      expect($t('page.shell.hotkeyPicker.confirmAssign')).toBe('Confirm assignment');
      expect($t('page.shell.hotkeyPicker.points', { n: 5 })).toBe('5 pts');
      expect($t('page.shell.hotkeyPicker.noLabels')).toBe('No labels yet. Create them on the Labels settings page.');
      expect($t('common.commandPalette.estimateTitle')).toBe('Set estimate\u2026');
      expect($t('page.issueStatus.open')).not.toBe('待办');
      expect($t('page.issuePriority.low')).not.toBe('低');
    } finally {
      setLocale(previous);
    }
  });
});
