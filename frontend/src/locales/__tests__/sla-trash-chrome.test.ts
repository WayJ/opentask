import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

const source = (path: string) => readFileSync(resolve(path), 'utf8');
const slaSource = source('src/views/settings/sla/index.vue');
const trashSource = source('src/views/issue/trash/index.vue');
const metaSource = source('src/utils/issueTrashMeta.ts');
const typings = source('src/typings/app.d.ts');
const digest = (text: string) => createHash('sha256').update(text).digest('hex');
const slaCopy = [
  ['policies', 'SLA 策略', 'SLA policies'],
  ['refresh', '刷新', 'Refresh'],
  ['newPolicy', '新建策略', 'New policy'],
  ['name', '名称', 'Name'],
  ['startStopStatuses', '启停状态', 'Start and stop statuses'],
  ['enabled', '启用', 'Enabled'],
  ['actions', '操作', 'Actions'],
  ['minutes', '{n} 分钟', '{n} min'],
  ['holidayPack', '假日包', 'Holiday pack'],
  ['holidayPacks', '假日包', 'Holiday packs'],
  ['clearOverride', '清除覆盖', 'Clear override'],
  ['delete', '删除', 'Delete'],
  ['notifyAssignee', '通知负责人', 'Notify assignee'],
  ['notifyWatchers', '通知关注者', 'Notify watchers'],
  ['calendarOverride', '日历覆盖', 'Calendar override'],
  [
    'calendarOverrideHint',
    '关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承',
    'Off inherits the workspace. When on, only filled fields override; the rest still inherit.'
  ],
  ['timezoneOverride', '时区覆盖', 'Time zone override'],
  ['inheritWorkspace', '（继承工作区）', '(Inherit workspace)'],
  [
    'exceptionOverride',
    '例外覆盖（填写则整表替换 WS 例外；留空=继承）',
    'Exception override (a filled table replaces workspace exceptions; empty inherits)'
  ],
  ['create', '创建', 'Create'],
  ['allRegions', '全部地区', 'All regions'],
  ['allYears', '全部年份', 'All years'],
  ['region', '地区', 'Region'],
  ['year', '年份', 'Year'],
  ['packTitle', '国家/地区假日包（一键合并例外日）', 'Country and region holiday packs (merge exception days)'],
  ['preview', '预览', 'Preview'],
  ['applyPack', '确认应用', 'Apply'],
  [
    'packPreviewSummary',
    '变更：+{added} / 覆盖 {replaced} / 保留 {kept} （{before} → {after}）',
    'Changes: +{added} / replaced {replaced} / kept {kept} ({before} → {after})'
  ]
] as const;
const trashCopy = [
  ['title', '回收站', 'Trash'],
  ['backToList', '返回列表', 'Back to list'],
  ['refresh', '刷新', 'Refresh'],
  ['empty', '回收站为空', 'Trash is empty'],
  ['key', '编号', 'Key'],
  ['issueTitle', '标题', 'Title'],
  ['status', '状态', 'Status'],
  ['priority', '优先级', 'Priority'],
  ['updatedAt', '更新时间', 'Updated'],
  ['actions', '操作', 'Actions'],
  ['restore', '恢复', 'Restore']
] as const;
const oldSlaKeys = [
  'runDue',
  'help',
  'businessHours',
  'metricPlaceholder',
  'startPlaceholder',
  'stopPlaceholder',
  'pausePlaceholder',
  'targetPlaceholder',
  'windowPlaceholder',
  'pauseHint',
  'priorityRule',
  'firstResponseNote',
  'closingStatuses',
  'startPrefix',
  'stopPrefix',
  'pausePrefix',
  'targetWorkspace',
  'targetPolicy',
  'choosePolicy',
  'defaultPolicyName',
  'nameRequired',
  'holidayIntro',
  'hoursIntro',
  'hoursEnabled',
  'weekdayPreset',
  'hoursWindowPlaceholder',
  'exceptionDays',
  'noExceptions',
  'defaultWindow',
  'addException',
  'removeException',
  'weekday.mon',
  'weekday.tue',
  'weekday.wed',
  'weekday.thu',
  'weekday.fri',
  'weekday.sat',
  'weekday.sun',
  'saveHours',
  'hoursSaved',
  'packAdded',
  'packReplaced',
  'regionCN',
  'regionUS',
  'regionEU',
  'regionUK',
  'metric.time_in_status',
  'metric.first_response',
  'exception.closed',
  'exception.forced_open'
];
const preservedCopy = {
  'zh-cn': {
    help: '支持「状态停留」和「首次响应」两种度量。默认按墙钟分钟；启用营业时段后按营业分钟。首次响应：不是创建者的第一条评论即满足，指派负责人不算。结束状态留空时，进入已解决、已关闭或已拒绝即满足。进入暂停状态时不计时，离开后按剩余时间继续。没有内置定时任务（cron）。请用外部调度调用 POST /api/sla/run-due。',
    businessHours: '营业时段',
    holidayIntro:
      '精选静态包（中国、美国、欧盟、英国 · 2026/2027）。预览后应用到本工作区营业例外，或某个策略的日历。同日以包为准覆盖；包外例外保留。无外网同步。',
    defaultPolicyName: '进行中停留',
    runDue: '立即执行到期检查'
  },
  'en-us': {
    help: 'Two metrics: time in status and first response. Minutes use the wall clock unless business hours are on. First response is the first comment by someone other than the creator. Assignment does not count. If no stop status is set, resolved, closed, or rejected completes it. Pause statuses do not count; the clock resumes with the time left. There is no built-in scheduler (cron). Call POST /api/sla/run-due from an external scheduler.',
    businessHours: 'Business hours',
    holidayIntro:
      'Static packs for China, the United States, the European Union, and the United Kingdom, 2026 and 2027. Preview, then apply them to this workspace or to a policy calendar. The pack wins on the same date. Other exceptions stay. No network sync.',
    defaultPolicyName: 'Time in progress',
    runDue: 'Run due checks'
  }
};
const slaCalls = {
  policies: 1,
  refresh: 1,
  newPolicy: 1,
  name: 2,
  startStopStatuses: 1,
  enabled: 1,
  actions: 1,
  minutes: 1,
  holidayPack: 1,
  holidayPacks: 1,
  clearOverride: 1,
  delete: 1,
  notifyAssignee: 1,
  notifyWatchers: 1,
  calendarOverride: 1,
  calendarOverrideHint: 1,
  timezoneOverride: 1,
  inheritWorkspace: 1,
  exceptionOverride: 1,
  create: 1,
  allRegions: 1,
  allYears: 1,
  region: 1,
  year: 1,
  packTitle: 1,
  preview: 1,
  applyPack: 1,
  packPreviewSummary: 1
};
const trashCalls = {
  title: 1,
  backToList: 1,
  refresh: 1,
  key: 1,
  issueTitle: 1,
  status: 1,
  priority: 1,
  updatedAt: 1,
  actions: 1,
  restore: 1
};

function keysOf(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object') return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    keysOf(child, prefix ? `${prefix}.${key}` : key)
  );
}

function schemaKeys(namespace: 'sla' | 'issueTrash'): string[] {
  const match = new RegExp(`(?:^|[\n\r;{])\\s*${namespace}\\s*:\\s*\\{`).exec(typings);
  if (!match) return [];
  const start = typings.indexOf('{', match.index);
  const tokens =
    typings
      .slice(start)
      .replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, '')
      .match(/[A-Za-z_]\w*|[{}:;,]/g) ?? [];
  let index = 0;
  function walk(prefix: string): string[] {
    const leaves: string[] = [];
    expect(tokens[index]).toBe('{');
    index += 1;
    while (tokens[index] !== '}' && index < tokens.length) {
      if (tokens[index] === ';' || tokens[index] === ',') {
        index += 1;
      } else {
        const key = tokens[index];
        index += 1;
        expect(tokens[index]).toBe(':');
        index += 1;
        const path = prefix ? `${prefix}.${key}` : key;
        if (tokens[index] === '{') leaves.push(...walk(path));
        else {
          expect(tokens[index]).toBe('string');
          index += 1;
          leaves.push(path);
        }
      }
    }
    expect(tokens[index]).toBe('}');
    index += 1;
    return leaves;
  }
  return walk('').sort();
}

function calls(text: string, namespace: string, key: string): number {
  const token = `$t('${namespace}.${key}'`;
  return text.split(token).length - 1;
}
const messages = (text: string) =>
  (text.match(/window\.\$message[\s\S]*?;/g) ?? []).map(s => s.replace(/\s+/g, ' ').trim());

describe('SLA and trash chrome contract', () => {
  it('locks every new key, existing SLA leaves, and object Schema shapes', () => {
    for (const lang of [zh, en]) {
      const page = lang.page as unknown as Record<string, Record<string, unknown>>;
      expect(keysOf(page.sla).sort()).toEqual([...oldSlaKeys, ...slaCopy.map(([key]) => key)].sort());
      expect(keysOf(page.issueTrash).sort()).toEqual(trashCopy.map(([key]) => key).sort());
      expect(schemaKeys('sla')).toEqual(keysOf(page.sla).sort());
      expect(schemaKeys('issueTrash')).toEqual(keysOf(page.issueTrash).sort());
      const columnTitle = page.issueTrash?.issueTitle;
      expect(columnTitle).not.toBe(page.issueTrash?.title);
    }
    for (const [index, lang] of [zh, en].entries()) {
      const page = lang.page as unknown as Record<string, Record<string, unknown>>;
      for (const [key, z, e] of slaCopy) expect(page.sla[key]).toBe(index === 0 ? z : e);
      for (const [key, z, e] of trashCopy) expect(page.issueTrash?.[key]).toBe(index === 0 ? z : e);
      expect(Object.fromEntries(Object.keys(preservedCopy['zh-cn']).map(key => [key, page.sla[key]]))).toEqual(
        preservedCopy[index === 0 ? 'zh-cn' : 'en-us']
      );
    }
    expect(zh.route.settings_sla).toBe('SLA 策略');
    expect(en.route.settings_sla).toBe('SLA');
    expect(zh.route.issue_trash).toBe('回收站');
    expect(en.route.issue_trash).toBe('Trash');
    expect([zh.page.issueStatus.open, en.page.issueStatus.open]).toEqual(['待办', 'Open']);
    expect([zh.page.issuePriority.critical, en.page.issuePriority.critical]).toEqual(['紧急', 'Urgent']);
    expect([zh.page.sla.addException, en.page.sla.addException]).toEqual(['添加例外', 'Add exception']);
    expect([zh.page.sla.removeException, en.page.sla.removeException]).toEqual(['删除', 'Remove']);
    expect([zh.page.sla.packAdded, en.page.sla.packAdded]).toEqual(['新增', 'Added']);
    expect([zh.page.sla.packReplaced, en.page.sla.packReplaced]).toEqual(['覆盖', 'Replaced']);
  });

  it('counts real translator call sites and binds card titles', () => {
    // 去掉注释后数调用，不能向注释填 token 冒充接线。
    const stripComments = (text: string) => text.replace(/<!--[\s\S]*?-->|\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, '');
    for (const [key, count] of Object.entries(slaCalls))
      expect(calls(stripComments(slaSource), 'page.sla', key), key).toBe(count);
    for (const [key, count] of Object.entries(trashCalls))
      expect(calls(stripComments(trashSource), 'page.issueTrash', key), key).toBe(count);
    expect(calls(stripComments(metaSource), 'page.issueTrash', 'empty')).toBe(1);
    expect(calls(stripComments(slaSource), 'page.sla', 'addException')).toBe(2);
    expect(calls(stripComments(slaSource), 'page.sla', 'removeException')).toBe(2);
    for (const key of ['policies', 'newPolicy', 'holidayPacks']) {
      expect(slaSource).toContain(`:title="$t('page.sla.${key}')"`);
    }
    expect(trashSource).toContain(`:title="$t('page.issueTrash.title')"`);
    expect(slaSource).toContain(`:placeholder="$t('page.sla.name')"`);
    expect(trashSource).not.toContain("$t('route.issue_trash')");
    expect(trashSource).not.toContain('page.issueList.columns.');
    expect(slaSource).toContain(
      'const columns = computed<DataTableColumns<SlaPolicyRow>>(() => {\n  void locale.value;\n  return ['
    );
    expect(trashSource).toContain(
      'const columns = computed<DataTableColumns<Api.Issue.Issue>>(() => {\n  void locale.value;\n  return ['
    );
    for (const name of ['packRegionFilterOptions', 'packYearFilterOptions']) {
      expect(slaSource).toContain(`const ${name} = computed(() => {\n  void locale.value;\n  return [`);
    }
    expect(trashSource).toContain("useLabelTable('page.issueStatus')");
    expect(trashSource).toContain("useLabelTable('page.issuePriority')");
    expect(trashSource).toContain('lookupLabel(statusLabels.value, row.status)');
    expect(trashSource).toContain('lookupLabel(priorityLabels.value, row.priority)');
    expect(trashSource).toContain(
      'const emptyHint = computed(() => {\n  void locale.value;\n  return trashEmptyHint();\n});'
    );
    expect(trashSource).toContain(':description="emptyHint"');
    expect(metaSource).toContain("return $t('page.issueTrash.empty');");
    expect(slaSource).toContain("$t('page.sla.minutes', { n: row.targetMinutes })");
    expect(slaSource).toContain("$t('page.sla.packPreviewSummary', {");
    for (const binding of [
      'added: (packPreview.added || []).length',
      'replaced: (packPreview.replaced || []).length',
      'kept: (packPreview.unchanged || []).length',
      'before: packPreview.countBefore',
      'after: packPreview.countAfter'
    ])
      expect(slaSource).toContain(binding);
  });

  it('removes only the exact in-scope literal contexts', () => {
    for (const text of [
      'title="SLA 策略"',
      'title="新建策略"',
      'title="假日包"',
      'placeholder="名称"',
      'placeholder="地区"',
      'placeholder="年份"',
      "title: '名称'",
      "title: '启停状态'",
      "title: '启用'",
      "title: '操作'",
      "'全部地区'",
      "'全部年份'",
      "default: () => '假日包'",
      "default: () => '清除覆盖'",
      "default: () => '删除'",
      "label: '（继承工作区）'",
      // eslint-disable-next-line no-template-curly-in-string -- expected source snippet, not a template
      '${row.targetMinutes} 分钟',
      '>通知负责人<',
      '>通知关注者<',
      '>日历覆盖<',
      '>时区覆盖<',
      '>关闭=继承工作区；开启后仅填写字段覆盖，其余仍继承<',
      '}} 国家/地区假日包（一键合并例外日）'
    ])
      expect(slaSource).not.toContain(text);
    for (const regex of [
      /^\s+刷新\s*$/m,
      /^\s+预览\s*$/m,
      /^\s+确认应用\s*$/m,
      /^\s+删\s*$/m,
      /^\s+例外覆盖（填写则整表替换 WS 例外；留空=继承）\s*$/m,
      /^\s+变更：\+/m,
      />刷新<\/NButton>/,
      />预览<\/NButton>/,
      />创建<\/NButton>/,
      />添加例外<\/NButton>/
    ])
      expect(slaSource).not.toMatch(regex);
    for (const text of [
      'title="回收站"',
      "title: '编号'",
      "title: '标题'",
      "title: '状态'",
      "title: '优先级'",
      "title: '更新时间'",
      "title: '操作'",
      'default: () => row.status',
      'default: () => row.priority',
      "default: () => '恢复'"
    ])
      expect(trashSource).not.toContain(text);
    for (const regex of [/^\s+返回列表\s*$/m, /^\s+刷新\s*$/m, />返回列表<\/NButton>/, />刷新<\/NButton>/])
      expect(trashSource).not.toMatch(regex);
  });

  it('freezes out-of-scope messages, Business hours, and policy-name implementation', () => {
    expect(messages(slaSource)).toEqual([
      "window.$message?.error?.(t('page.sla.choosePolicy'));",
      "window.$message?.error?.(error?.message || '预览失败');",
      "window.$message?.error?.(t('page.sla.choosePolicy'));",
      "window.$message?.error?.(error?.message || '应用失败');",
      // eslint-disable-next-line no-template-curly-in-string -- expected source snippet, not a template
      'window.$message?.success?.(`已应用：+${(data.added || []).length} 覆盖${(data.replaced || []).length}`);',
      "window.$message?.error?.(e?.message || '时段非法');",
      "window.$message?.error?.(error?.message || '保存失败');",
      "window.$message?.success?.(t('page.sla.hoursSaved'));",
      "window.$message?.error?.(e?.message || '例外日非法');",
      "window.$message?.error?.(error.message || '加载失败');",
      "window.$message?.warning?.(t('page.sla.nameRequired'));",
      "window.$message?.error?.(e?.message || '日历覆盖无效');",
      "window.$message?.error?.(error.message || '创建失败');",
      "window.$message?.success?.('已创建');",
      "window.$message?.error?.(error.message || '更新失败');",
      "window.$message?.error?.(error.message || '删除失败');",
      "window.$message?.success?.('已删除');",
      "window.$message?.error?.(error.message || '清除失败');",
      "window.$message?.success?.('已清除日历覆盖');",
      "window.$message?.error?.(e?.message || '例外无效');",
      "window.$message?.error?.(error.message || '执行失败');",
      // eslint-disable-next-line no-template-curly-in-string -- expected source snippet, not a template
      'window.$message?.success?.( `扫描 ${data?.scanned ?? 0} · 违约 ${data?.breached ?? 0} · 通知 ${data?.notificationsCreated ?? 0}` );'
    ]);
    expect(messages(trashSource)).toEqual([
      "window.$message?.error('加载回收站失败');",
      "window.$message?.success(restoreSuccessMessage(row.issue_code || ''));",
      "window.$message?.error('恢复失败（需要 member 权限）');"
    ]);
    const start = slaSource.indexOf(`    <NCard :title="$t('page.sla.businessHours')"`);
    const end = slaSource.indexOf('    </NCard>', start) + '    </NCard>'.length;
    expect(start).toBeGreaterThan(-1);
    expect(digest(slaSource.slice(start, end))).toBe(
      '5dbec96843fec4652d92d7f8a4e4908a781cfe707b62342465a84a96688558ad'
    );
    expect(digest(source('src/views/settings/sla/policy-name.ts'))).toBe(
      'ec9f5d1110650696459a6817427cca72eb58a97e7a93e507b1864c0b04a87daa'
    );
    // eslint-disable-next-line no-template-curly-in-string -- expected source snippet, not a template
    expect(metaSource).toContain("return c ? `已恢复 ${c}` : '已恢复';");
    expect(metaSource).toContain("return '此问题已在回收站中，只读。恢复后可继续编辑。';");
  });
});
