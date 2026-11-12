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

const boardVue = readSrc('src/views/issue/list/modules/IssueBoard.vue');
const displayVue = readSrc('src/views/issue/list/modules/DisplayOptionsPanel.vue');
const groupedVue = readSrc('src/views/issue/list/modules/IssueListGrouped.vue');
const bulkVue = readSrc('src/components/IssueBulkBar.vue');
const searchVue = readSrc('src/components/IssueSmartSearch.vue');
const parserTs = readSrc('src/utils/issueSearchParser.ts');
const groupTs = readSrc('src/utils/groupIssuesBy.ts');
const groupTest = readSrc('src/utils/groupIssuesBy.test.ts');
const displayPrefs = readSrc('src/utils/display-prefs.ts');
const listVue = readSrc('src/views/issue/list/index.vue');
const constantsTs = readSrc('src/constants/issue.ts');
const zhSrc = readSrc('src/locales/langs/zh-cn.ts');
const enSrc = readSrc('src/locales/langs/en-us.ts');
const typings = readSrc('src/typings/app.d.ts');

const groups = {
  board: ['unassigned', 'due', 'moveFailed', 'groupedListHint'],
  displayOptions: [
    'title',
    'cardFields',
    'customFieldColumns',
    'boardSwimlanes',
    'hideEmptyLanes',
    'conditionalFormats',
    'remove',
    'addRule',
    'colorScales',
    'addColorScale',
    'iconSets',
    'ruleCount',
    'addIconSet',
    'setPersonalDefault',
    'noSwimlane',
    'fieldCycle'
  ],
  bulk: ['selected', 'apply', 'selectFieldWarning', 'updateFailed', 'updateSuccess'],
  search: ['defaultPlaceholder', 'appliedFilters', 'field'],
  searchSuggestions: [
    'labelBug',
    'typeFeature',
    'cycleNone',
    'filterByProject',
    'customField',
    'formulaEquals',
    'formulaRange'
  ]
} as const;

const zhCopy = {
  board: {
    unassigned: '未指派',
    due: '截止',
    moveFailed: '看板移动失败',
    groupedListHint: '列表分组为展示泳道；泳道内 depth-1 嵌套。跨泳道拖拽改字段不在本 Sprint 范围。'
  },
  displayOptions: {
    title: '显示选项',
    cardFields: '卡片字段',
    customFieldColumns: '自定义字段列',
    boardSwimlanes: '看板泳道',
    hideEmptyLanes: '隐藏空泳道',
    conditionalFormats: '条件格式（≤10）',
    remove: '删',
    addRule: '添加规则',
    colorScales: '色阶（≤5）',
    addColorScale: '添加色阶',
    iconSets: '图标集（≤5）',
    ruleCount: '{n} 条规则',
    addIconSet: '添加图标集',
    setPersonalDefault: '设为个人默认',
    noSwimlane: '无泳道',
    fieldCycle: 'Cycle'
  },
  bulk: {
    selected: '已选 {n} 项',
    apply: '应用',
    selectFieldWarning: '请至少选择一项要修改的字段',
    updateFailed: '批量更新失败',
    updateSuccess: '批量更新成功'
  },
  search: {
    defaultPlaceholder: '搜索问题... (支持 is:open, field:key:value 等)',
    appliedFilters: '应用过滤器',
    field: '字段'
  },
  searchSuggestions: {
    labelBug: '只显示标签为 bug 的问题',
    typeFeature: '只显示类型为功能的问题',
    cycleNone: '无冲刺',
    filterByProject: '按项目过滤',
    customField: '自定义字段过滤（cf:key:value 亦可）',
    formulaEquals: '公式字段按计算值等值过滤（只读）',
    formulaRange: '公式/数字字段 range 过滤（E46）'
  }
} as const;

const enCopy = {
  board: {
    unassigned: 'Unassigned',
    due: 'Due',
    moveFailed: 'Couldn\u2019t move the issue',
    groupedListHint:
      'Grouped list is a display swimlane; issues nest at depth-1 inside a lane. Dragging across lanes to change a field is out of scope for this Sprint.'
  },
  displayOptions: {
    title: 'Display options',
    cardFields: 'Card fields',
    customFieldColumns: 'Custom field columns',
    boardSwimlanes: 'Board swimlanes',
    hideEmptyLanes: 'Hide empty swimlanes',
    conditionalFormats: 'Conditional formats (≤10)',
    remove: 'Delete',
    addRule: 'Add a rule',
    colorScales: 'Color scales (≤5)',
    addColorScale: 'Add a color scale',
    iconSets: 'Icon sets (≤5)',
    ruleCount: '{n} rules',
    addIconSet: 'Add an icon set',
    setPersonalDefault: 'Set as your personal default',
    noSwimlane: 'No swimlane',
    fieldCycle: 'Cycle'
  },
  bulk: {
    selected: 'Selected {n} items',
    apply: 'Apply',
    selectFieldWarning: 'Select at least one field to change',
    updateFailed: 'Couldn\u2019t update in bulk',
    updateSuccess: 'Updated in bulk'
  },
  search: {
    defaultPlaceholder: 'Search issues... (supports is:open, field:key:value, and similar)',
    appliedFilters: 'Applied filters',
    field: 'Field'
  },
  searchSuggestions: {
    labelBug: 'Show only issues labeled bug',
    typeFeature: 'Show only issues whose type is feature',
    cycleNone: 'No cycle',
    filterByProject: 'Filter by project',
    customField: 'Custom field filter (cf:key:value also works)',
    formulaEquals: 'Filter a formula field by exact computed value (read-only)',
    formulaRange: 'Formula/number field range filter (E46)'
  }
} as const;

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

function suggestionBody(): string {
  const start = parserTs.indexOf('export function generateSearchSuggestions');
  const rest = start < 0 ? '' : parserTs.slice(start);
  const next = rest.indexOf('\nexport function', 10);
  return next < 0 ? rest : rest.slice(0, next);
}

describe('issue list board English chrome', () => {
  it('locks the new keys in zh, en, and the schema', () => {
    expect(enSrc).not.toMatch(/[\u4E00-\u9FFF]/);
    const issueListSources = [
      extractBlock(zhSrc, 'issueList'),
      extractBlock(enSrc, 'issueList'),
      extractBlock(typings, 'issueList')
    ];
    for (const issueList of issueListSources) {
      expect(issueList).not.toBe('');
      for (const [group, keys] of Object.entries(groups)) {
        expect(blockKeys(extractBlock(issueList, group)).sort()).toEqual([...keys].sort());
      }
    }
    for (const group of Object.keys(groups) as (keyof typeof groups)[]) {
      for (const key of groups[group]) {
        expect(zh.page.issueList[group][key]).toBe(zhCopy[group][key]);
        expect(en.page.issueList[group][key]).toBe(enCopy[group][key]);
      }
    }
    expect(zh.page.issueList.blockedBy).toBe('被阻塞 {count}');
    expect(en.page.issueList.blockedBy).toBe('Blocked by {count}');
    expect(zh.page.issueList.blocks).toBe('阻塞 {count}');
    expect(en.page.issueList.blocks).toBe('Blocks {count}');
  });

  it('binds board counts with the existing {count} signature', () => {
    expect(countCalls(boardVue, 'page.shell.noIssues')).toBe(1);
    expect(countCalls(boardVue, 'page.issueList.blockedBy')).toBe(1);
    expect(boardVue).toContain("$t('page.issueList.blockedBy', { count:");
    expect(countCalls(boardVue, 'page.issueList.blocks')).toBe(1);
    expect(boardVue).toContain("$t('page.issueList.blocks', { count:");
    expect(countCalls(boardVue, 'page.issueList.columns.estimate')).toBeGreaterThanOrEqual(1);
    expect(countCalls(boardVue, 'page.issueList.filters.project')).toBeGreaterThanOrEqual(1);
    expect(countCalls(boardVue, 'page.issueForm.cycle')).toBeGreaterThanOrEqual(1);
    expect(countCalls(boardVue, 'page.issueList.board.due')).toBe(1);
    expect(countCalls(boardVue, 'page.issueList.board.unassigned')).toBe(1);
    expect(countCalls(boardVue, 'page.issueList.board.moveFailed')).toBe(2);
    expect(boardVue).toContain('lookupLabel(priorityLabels.value, issue.priority)');
    expect(boardVue).not.toContain('getIssuePriorityLabel(');
    expect(boardVue).not.toContain(".replace('{count}'");
    expect(boardVue).not.toContain(".replace('{n}'");
    expect(boardVue).not.toMatch(/description="暂无问题"/);
    expect(boardVue).not.toMatch(/return '未指派'/);
    expect(boardVue).not.toMatch(/被阻塞 \{\{/);
    expect(boardVue).not.toMatch(/阻塞 \{\{/);
    expect(boardVue).not.toMatch(/估点 \{\{/);
    expect(boardVue).not.toMatch(/截止 \{\{/);
    expect(boardVue).not.toMatch(/项目 \{\{/);
    expect(boardVue).not.toMatch(/冲刺 \{\{/);
    expect(boardVue).not.toMatch(/看板移动失败/);
    expect(boardVue).toContain('lane.label');
    expect(boardVue).not.toContain('未分配');
    expect(boardVue).not.toContain('无标签');
    expect(boardVue).not.toContain('计算错误');
  });

  it('localizes grouped empty state and the footnote without covering bucket words', () => {
    expect(countCalls(groupedVue, 'page.shell.noIssues')).toBe(1);
    expect(countCalls(groupedVue, 'page.issueList.board.groupedListHint')).toBe(1);
    expect(groupedVue).not.toMatch(/description="暂无问题"/);
    expect(groupedVue).not.toContain('列表分组为展示泳道；泳道内 depth-1 嵌套。跨泳道拖拽改字段不在本 Sprint 范围。');
    expect(groupedVue).toContain('bucket.label');
    expect(groupedVue).not.toContain('未分配');
    expect(groupedVue).not.toContain('无标签');
    expect(groupedVue).not.toContain('计算错误');
  });

  it('binds display options, field labels, swimlanes, and rule counts', () => {
    for (const key of [
      'title',
      'cardFields',
      'customFieldColumns',
      'boardSwimlanes',
      'hideEmptyLanes',
      'conditionalFormats',
      'addRule',
      'colorScales',
      'addColorScale',
      'iconSets',
      'addIconSet',
      'setPersonalDefault',
      'noSwimlane',
      'fieldCycle'
    ]) {
      expect(countCalls(displayVue, `page.issueList.displayOptions.${key}`)).toBeGreaterThanOrEqual(1);
    }
    expect(countCalls(displayVue, 'page.issueList.displayOptions.remove')).toBe(3);
    expect(countCalls(displayVue, 'page.issueList.displayOptions.ruleCount')).toBe(1);
    expect(displayVue).toContain("$t('page.issueList.displayOptions.ruleCount', { n:");
    expect(countCalls(displayVue, 'common.reset')).toBe(1);
    expect(countCalls(displayVue, 'page.issueList.computedFieldSuffixReadonly')).toBe(1);
    for (const key of [
      'page.issueList.columns.key',
      'page.issueList.columns.assignee',
      'page.issueList.columns.priority',
      'page.issueList.groupBy.label',
      'page.issueList.columns.type',
      'page.issueList.columns.estimate',
      'page.issueForm.dueDate',
      'page.issueList.filters.project'
    ]) {
      expect(countCalls(displayVue, key)).toBeGreaterThanOrEqual(1);
    }
    expect(displayVue).toContain("endsWith('（计算值·只读）')");
    expect(displayVue).not.toContain('page.issueList.filters.cycle');
    expect(displayVue).not.toContain('page.issueList.groupBy.none');
    expect(displayVue).not.toContain(".replace('{n}'");
    expect(displayVue).not.toContain('显示选项');
    expect(displayVue).not.toContain('卡片字段');
    expect(displayVue).not.toContain('自定义字段列');
    expect(displayVue).not.toContain('看板泳道');
    expect(displayVue).not.toContain('隐藏空泳道');
    expect(displayVue).not.toContain('条件格式（≤10）');
    expect(displayVue).not.toContain('添加规则');
    expect(displayVue).not.toContain('色阶（≤5）');
    expect(displayVue).not.toContain('添加色阶');
    expect(displayVue).not.toContain('图标集（≤5）');
    expect(displayVue).not.toContain('条规则');
    expect(displayVue).not.toContain('添加图标集');
    expect(displayVue).not.toContain('设为个人默认');
    expect(displayVue).not.toMatch(/>\s*删\s*</);
  });

  it('binds the bulk bar without reusing confirm or assignee synonyms', () => {
    expect(countCalls(bulkVue, 'page.issueList.bulk.selected')).toBe(1);
    expect(bulkVue).toContain("$t('page.issueList.bulk.selected', { n:");
    expect(countCalls(bulkVue, 'page.issueForm.status')).toBe(1);
    expect(countCalls(bulkVue, 'page.issueForm.priority')).toBe(1);
    expect(countCalls(bulkVue, 'page.issueList.columns.assignee')).toBe(1);
    expect(countCalls(bulkVue, 'page.issueForm.cycle')).toBe(1);
    expect(countCalls(bulkVue, 'page.issueList.bulk.apply')).toBe(1);
    expect(countCalls(bulkVue, 'page.issueList.bulk.selectFieldWarning')).toBe(1);
    expect(countCalls(bulkVue, 'page.issueList.bulk.updateSuccess')).toBe(1);
    expect(countCalls(bulkVue, 'page.issueList.bulk.updateFailed')).toBe(2);
    expect(countCalls(bulkVue, 'common.cancel')).toBe(1);
    expect(bulkVue).toMatch(/\$t\('common\.cancel'\) \}\} \(Esc\)/);
    expect(bulkVue).toContain("useLabelTable('page.issueStatus')");
    expect(bulkVue).toContain("useLabelTable('page.issuePriority')");
    expect(bulkVue).toContain('lookupLabel(');
    expect(bulkVue).not.toContain('page.issueForm.assignee');
    expect(bulkVue).not.toContain('common.confirm');
    expect(bulkVue).not.toContain(".replace('{n}'");
    expect(bulkVue).not.toContain(`已选 ${'${'}selection.count.value} 项`);
    expect(bulkVue).not.toContain('请至少选择一项要修改的字段');
    expect(bulkVue).not.toContain('批量更新失败');
    expect(bulkVue).not.toContain('批量更新成功');
    expect(bulkVue).not.toContain('placeholder="状态"');
    expect(bulkVue).not.toContain('placeholder="优先级"');
    expect(bulkVue).not.toContain('placeholder="负责人"');
    expect(bulkVue).not.toContain('placeholder="冲刺"');
    expect(bulkVue).not.toContain('>应用<');
    expect(bulkVue).not.toContain('>取消 (Esc)<');
    expect(bulkVue).toContain('placeholder="Labels"');
  });

  it('binds search chrome and suggestion blurbs without near-synonym keys', () => {
    expect(countCalls(searchVue, 'page.issueList.search.defaultPlaceholder')).toBe(1);
    expect(countCalls(searchVue, 'page.issueList.search.appliedFilters')).toBe(1);
    expect(countCalls(searchVue, 'page.issueList.search.field')).toBe(1);
    for (const key of [
      'page.issueList.columns.status',
      'page.issueList.columns.type',
      'page.issueList.columns.priority',
      'page.issueList.columns.assignee',
      'page.issueList.columns.reporter',
      'page.issueList.displayOptions.fieldCycle',
      'page.issueList.filters.project',
      'page.issueList.groupBy.label',
      'common.search'
    ]) {
      expect(countCalls(searchVue, key)).toBeGreaterThanOrEqual(1);
    }
    expect(searchVue).not.toContain('useI18n');
    expect(searchVue).not.toContain("'搜索问题... (支持 is:open, field:key:value 等)'");
    expect(searchVue).not.toContain('`状态: ${');
    expect(searchVue).not.toContain('`类型: ${');
    expect(searchVue).not.toContain('`优先级: ${');
    expect(searchVue).not.toContain('`负责人: ${');
    expect(searchVue).not.toContain('`报告人: ${');
    expect(searchVue).not.toContain('`Cycle: ${');
    expect(searchVue).not.toContain('`项目: ${');
    expect(searchVue).not.toContain('`标签: ${');
    expect(searchVue).not.toContain('`搜索: ${');
    expect(searchVue).not.toContain('`字段 ${');
    expect(searchVue).not.toContain('应用过滤器:');
    expect(en.page.issueList.search.appliedFilters).not.toContain(':');
    expect(en.page.issueList.search.field).not.toContain(':');

    const suggestions = suggestionBody();
    const stripped = suggestions.slice(suggestions.indexOf('{') + 1).replace(/^\s*(\/\/[^\n]*\n\s*)*/, '');
    expect(stripped.startsWith('void locale.value;')).toBe(true);
    expect(suggestions).toContain('page.issueList.syntax.isOpen');
    expect(suggestions).toContain('page.issueList.syntax.isClosed');
    expect(suggestions).toContain('page.issueList.syntax.isInProgress');
    expect(suggestions).toContain('page.issueList.syntax.priorityUrgent');
    expect(suggestions).toContain('page.issueList.scopeTitle.assignedToMe');
    for (const key of groups.searchSuggestions) {
      expect(suggestions).toContain(`page.issueList.searchSuggestions.${key}`);
    }
    for (const token of [
      'is:open',
      'label:bug',
      'type:feature',
      'priority:urgent',
      'assignee:@me',
      'cycle:__none__',
      'project:<id>',
      'field:severity:s1',
      'field:score:10',
      'cf:score>=8'
    ]) {
      expect(suggestions).toContain(token);
    }
    expect(parserTs).not.toContain('page.issueList.syntax.assigneeMe');
    expect(parserTs).not.toContain('page.issueList.syntax.typeFeature');
    expect(parserTs).not.toContain('page.issueList.syntax.customField');
    expect(parserTs).not.toContain('page.issueList.noneCycle');
    expect(parserTs).not.toContain('page.issueForm.unassigned');
    expect(parserTs).not.toContain('page.issueForm.dueDate');
    expect(parserTs).not.toContain('page.issueList.filters.cycle');
    expect(parserTs).not.toContain('common.confirm');
    expect(parserTs).not.toContain('page.issueForm.assignee');
    expect(parserTs).not.toContain(".replace('{count}'");
    expect(parserTs).not.toContain(".replace('{n}'");
    expect(boardVue).not.toContain('page.issueForm.unassigned');
    expect(boardVue).not.toContain('page.issueForm.dueDate');
  });

  it('keeps decision E source strings and the list suffix bridge', () => {
    expect(groupTs).toContain("const UNASSIGNED_LABEL = '未分配'");
    expect(groupTs).toContain("const UNLABELLED_LABEL = '无标签'");
    expect(groupTs).toContain("const EMPTY_CF_LABEL = '空'");
    expect(groupTs).toContain("const ERROR_CF_LABEL = '计算错误'");
    expect(groupTs).toContain('（计算值·只读）');
    expect(groupTest).toContain("toBe('未分配')");
    expect(displayPrefs).toContain('（计算值·只读）');
    expect(displayPrefs).toContain("return value ? '是' : '否'");
    expect(listVue).toContain("const readonlySuffix = '（计算值·只读）'");
    expect(listVue).toContain("$t('page.shell.searchIssues')");
    expect(constantsTs).toContain("label: '待办'");
    expect(constantsTs).toContain("label: '低'");
  });

  it('resolves locked strings from the real i18n catalog', () => {
    const previous = getLocale();
    try {
      setLocale('zh-CN');
      expect($t('page.issueList.board.unassigned')).toBe('未指派');
      expect($t('page.issueList.board.due')).toBe('截止');
      expect($t('page.issueList.displayOptions.fieldCycle')).toBe('Cycle');
      expect($t('page.issueList.searchSuggestions.cycleNone')).toBe('无冲刺');
      setLocale('en-US');
      expect($t('page.issueList.board.unassigned')).toBe('Unassigned');
      expect($t('page.issueList.board.due')).toBe('Due');
      expect($t('page.issueList.displayOptions.fieldCycle')).toBe('Cycle');
      expect($t('page.issueList.searchSuggestions.cycleNone')).toBe('No cycle');
      expect($t('page.issueList.blockedBy', { count: 2 })).toBe('Blocked by 2');
      expect(en.page.issueList.blockedBy).toBe('Blocked by {count}');
    } finally {
      setLocale(previous);
    }
  });
});
