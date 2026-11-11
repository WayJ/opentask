# 残留界面文案 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让举措、问题类型、SLA 和洞察上残留的英文和错字变成当前语言的可读文字，存储值和接口保持原样。

**Architecture:** 句子放进 `zh-cn.ts` 与 `en-us.ts`。枚举显示只经过 `lookupLabel`。组件用 `useLabelTable` 取出当前语言的表，语言切换后计算属性重算。选项的 `value`、分组 `key` 和请求体不变。

**Tech Stack:** Vue 3、vue-i18n、Vitest、`@vue/test-utils`。不改 Naive 主题，不改后端。

Yuri 已批准 `docs/superpowers/specs/2026-11-11-residual-copy-design.md` 的范围、术语和 vue-i18n 方向。用词以该文件第 3 节为准。本计划把实现收成下面这一个查表接口，不再用 `$t('page.issueType.' + value)` 拼接。

## Global Constraints

- 基线是 `main` @ `22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34`。分支是 `cursor/residual-copy-design-658f`。不要往已合并的 PR #5 上追加。
- 不合并、不部署、不连接现网，不写入口令。
- 不改 OAuth、鉴权、路由、查询语法、CSV 列、请求字段和已有数据。
- 不改颜色、布局、响应式、`#5e6ad2`、亮色和暗色。
- 不改生成的 `frontend/src/typings/api/issue.d.ts` 和 `frontend/src/typings/components.d.ts`。
- 手写的 `frontend/src/typings/app.d.ts` 只补本批文案键。
- 客户侧「新建需求」保持这四个字。
- `slaMetricLabel` 和 `slaMetricBadgePrefix` 不改。
- 完整句子用静态键 `$t('page.sla.help')`。枚举和未知代码只用 `lookupLabel`。

## 接口

`frontend/src/locales/display-label.ts`：

```ts
export type LabelTable = Record<string, string>;

export function labelTable(source: unknown): LabelTable;

export function lookupLabel(table: LabelTable | null | undefined, value: unknown): string;

export interface LabeledOption<V extends string = string> {
  label: string;
  value: V;
}

export function labeledOptions<V extends string>(
  values: readonly V[],
  table: LabelTable | null | undefined
): LabeledOption<V>[];
```

- `labelTable` 把源对象自身的字符串值抄到 `Object.create(null)`。继承属性和非字符串丢掉。
- `lookupLabel` 在值为 `null` 或 `undefined` 时返回空字符串。其余先 `String(value)`。表上没有该自身属性，或属性不是非空字符串，就返回这个原始字符串。`toString`、`__proto__`、`constructor` 只有被写成自身属性时才当作文案。
- `labeledOptions` 的每一项是 `{ value, label: lookupLabel(table, value) }`。`value` 与入参同一引用含义，不改写。

`frontend/src/locales/use-label-table.ts`：

```ts
export function useLabelTable(path: string): ComputedRef<LabelTable>;
```

实现读取 `useI18n()` 的 `locale` 和 `tm(path)`，再交给 `labelTable`。语言一变，计算属性就变。

`frontend/src/utils/groupIssuesBy.ts` 增加可选第三参，缺省时保持现在的中文兜底：

```ts
export interface GroupLabels {
  status?: LabelTable;
  priority?: LabelTable;
  type?: LabelTable;
}

export function groupIssuesBy(
  issues: Api.Issue.Issue[],
  groupBy: GroupByKey,
  labels?: GroupLabels
): IssueGroupBucket[];
```

传入的表经过 `lookupLabel`。没传入的维度仍用 `issueStatusOptions` 等现有兜底。桶的 `key` 仍是枚举值。`buildBoardSwimlanes` 增加同样的可选末参并传给 `groupIssuesBy`。`IssueListGrouped` 和 `IssueBoard` 在组件内调用 `useLabelTable`，把表传进去。

`frontend/src/views/settings/sla/policy-name.ts`：

```ts
export interface PolicyNameDraft {
  dirty: boolean;
  loaded: boolean;
  current: string;
}

export function policyNameAfterLocaleChange(draft: PolicyNameDraft, suggested: string): string;
```

`loaded` 或 `dirty` 为真时返回 `current`。否则返回 `suggested`。新建且用户还没改过名称时，才随语言换成「进行中停留」或 `Time in progress`。加载已有策略或用户已经输入之后，切换语言不改名称框。

## Task 1: 查表和文案目录

**Files:**
- Create: `frontend/src/locales/display-label.ts`
- Create: `frontend/src/locales/use-label-table.ts`
- Create: `frontend/src/locales/__tests__/residual-copy.test.ts`
- Modify: `frontend/src/typings/app.d.ts`
- Modify: `frontend/src/locales/langs/zh-cn.ts`
- Modify: `frontend/src/locales/langs/en-us.ts`
- Modify: `frontend/src/constants/issue.ts`（只把 `bug` 的兜底 label 改为「缺陷」）

- [ ] **Step 1: Write the failing test**

把下面整段写入 `frontend/src/locales/__tests__/residual-copy.test.ts`。

```ts
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { IssueTypeEnum } from '@/constants/issue';
import { SLA_METRICS } from '@/service/api/sla';
import { labelTable, labeledOptions, lookupLabel } from '../display-label';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

describe('residual copy catalog', () => {
  it('fixes the initiative verb and keeps the customer request verb', () => {
    expect(zh.page.shell.createInitiative).toBe('新建举措');
    expect(en.page.shell.createInitiative).toBe('New initiative');
    expect(zh.page.shell.createRequest).toBe('新建需求');
    const zhSource = readFileSync(new URL('../langs/zh-cn.ts', import.meta.url), 'utf8');
    expect(zhSource).not.toContain('新建议措');
  });

  it('translates labels without changing enum values', () => {
    expect(IssueTypeEnum.Bug).toBe('bug');
    expect(zh.page.issueType.bug).toBe('缺陷');
    expect(en.page.issueType.bug).toBe('Bug');
    expect(zh.page.issueType.feature).toBe('功能');
    expect(en.page.issueType.question).toBe('Question');
    expect(SLA_METRICS).toEqual(['time_in_status', 'first_response']);
    expect(zh.page.sla.metric.time_in_status).toBe('状态停留');
    expect(en.page.sla.metric.time_in_status).toBe('Time in status');
    expect(zh.page.issueStatus.in_progress).toBe('进行中');
    expect(en.page.issueStatus.in_progress).toBe('In progress');
    expect(zh.page.sla.exception.forced_open).toBe('强制营业');
    expect(zh.page.sla.defaultPolicyName).toBe('进行中停留');
    expect(en.page.sla.defaultPolicyName).toBe('Time in progress');
  });

  it('keeps protocol words and removes raw enums from the Chinese explanation', () => {
    expect(zh.page.sla.help).toContain('POST /api/sla/run-due');
    expect(zh.page.sla.help).toContain('cron');
    expect(zh.page.sla.help).not.toContain('time_in_status');
    expect(zh.page.sla.help).not.toContain('in_progress');
    expect(zh.page.sla.help).not.toContain('resolved/closed');
    expect(en.page.sla.help).toContain('POST /api/sla/run-due');
    expect(en.page.sla.help).not.toMatch(/状态停留/);
    expect(zh.page.insights.subtitle).not.toMatch(/\bOR\b/);
    expect(zh.page.insights.subtitle).not.toMatch(/digest/i);
    expect(zh.page.insights.exportCsv).toContain('CSV');
    expect(en.page.insights.exportCsv).toBe('Export CSV');
  });
});

describe('lookupLabel', () => {
  const table = labelTable({ bug: '缺陷', toString: '自有' });

  it('returns the own label and otherwise the original value', () => {
    expect(lookupLabel(table, 'bug')).toBe('缺陷');
    expect(lookupLabel(table, 'custom')).toBe('custom');
    expect(lookupLabel(table, null)).toBe('');
    expect(lookupLabel(undefined, 'bug')).toBe('bug');
    expect(labeledOptions(['bug', 'custom'] as const, table)).toEqual([
      { value: 'bug', label: '缺陷' },
      { value: 'custom', label: 'custom' }
    ]);
  });

  it('does not read inherited names unless they are own properties', () => {
    const inherited = Object.create({ toString: '继承', constructor: '继承' }) as LabelTable;
    expect(lookupLabel(inherited, 'toString')).toBe('toString');
    expect(lookupLabel(inherited, '__proto__')).toBe('__proto__');
    expect(lookupLabel(inherited, 'constructor')).toBe('constructor');
    expect(lookupLabel(table, 'toString')).toBe('自有');
    expect(lookupLabel(table, '__proto__')).toBe('__proto__');
  });
});
```

测试文件顶部补上 `import type { LabelTable } from '../display-label';`。

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/locales/__tests__/residual-copy.test.ts`

Expected: FAIL。`display-label` 或 `page.issueType` 尚不存在。

- [ ] **Step 3: Write minimal implementation**

按设计第 3 节和上面的接口补键、补函数。`issue.ts` 里 `bug` 的兜底 label 改为「缺陷」，枚举值不动。

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/locales/__tests__/residual-copy.test.ts src/locales/__tests__/route-labels.test.ts`

Expected: PASS。`route-labels` 里「新建需求」仍通过。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/locales/display-label.ts frontend/src/locales/use-label-table.ts frontend/src/locales/__tests__/residual-copy.test.ts frontend/src/locales/langs/zh-cn.ts frontend/src/locales/langs/en-us.ts frontend/src/typings/app.d.ts frontend/src/constants/issue.ts
git commit -m "fix(ui): add locale label lookup for residual copy"
```

## Task 2: 举措空状态

**Files:**
- Modify: `frontend/src/views/initiatives/index.vue`
- Create: `frontend/src/views/initiatives/__tests__/create-label.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { i18n, setLocale } from '@/locales';
import InitiativesPage from '../index.vue';

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() })
}));

vi.mock('@/service/api', () => ({
  fetchInitiatives: vi.fn(async () => ({ data: { rows: [], total: 0 }, error: null })),
  fetchCreateInitiative: vi.fn(),
  fetchDeleteInitiative: vi.fn()
}));

describe('initiative create label', () => {
  afterEach(() => setLocale('zh-CN'));

  it('uses the same verb on the header and the empty state, and switches language', async () => {
    setLocale('zh-CN');
    const wrapper = mount(InitiativesPage, { global: { plugins: [i18n] } });
    await vi.dynamicImportSettled?.();
    expect(wrapper.text()).toContain('新建举措');
    expect(wrapper.text()).not.toContain('新建议措');
    setLocale('en-US');
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('New initiative');
    expect(wrapper.text()).not.toContain('新建举措');
  });
});
```

若该页的 API mock 路径和实际导出不一致，只补 mock，不改创建请求的参数。

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/views/initiatives/__tests__/create-label.test.ts`

Expected: FAIL。空状态仍是写死的「新建」，或英文切换后主按钮仍是中文。

- [ ] **Step 3: Write minimal implementation**

空状态按钮改为 `{{ $t('page.shell.createInitiative') }}`。不改弹窗字段和 `fetchCreateInitiative` 的参数。

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/views/initiatives/__tests__/create-label.test.ts`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/initiatives/index.vue frontend/src/views/initiatives/__tests__/create-label.test.ts
git commit -m "fix(ui): use the initiative create label in the empty state"
```

## Task 3: 问题类型、状态和分组

**Files:**
- Modify: `frontend/src/views/issue/list/index.vue`
- Modify: `frontend/src/views/issue/list/modules/IssueListGrouped.vue`
- Modify: `frontend/src/views/issue/list/modules/IssueBoard.vue`
- Modify: `frontend/src/views/issue/create/index.vue`
- Modify: `frontend/src/views/issue/edit/index.vue`
- Modify: `frontend/src/views/issue/detail/index.vue`（只改类型下拉和徽章所用的 options）
- Modify: `frontend/src/utils/groupIssuesBy.ts`
- Modify: `frontend/src/utils/boardSwimlanes.ts`
- Create: `frontend/src/views/issue/list/__tests__/type-labels.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { computed, defineComponent } from 'vue';
import { mount } from '@vue/test-utils';
import { afterEach, describe, expect, it } from 'vitest';
import { createPinia } from 'pinia';
import { i18n, setLocale } from '@/locales';
import { labeledOptions } from '@/locales/display-label';
import { useLabelTable } from '@/locales/use-label-table';
import { groupIssuesBy } from '@/utils/groupIssuesBy';
import IssueListGrouped from '../modules/IssueListGrouped.vue';

const ISSUE_TYPE_VALUES = ['bug', 'feature', 'question', 'feedback', 'incident', 'improvement'] as const;
const sampleIssues = [
  { id: '1', title: 't', type: 'bug', status: 'open', priority: 'medium', issue_code: 'T-1' }
];

const TypeHost = defineComponent({
  components: { IssueListGrouped },
  setup() {
    const typeLabels = useLabelTable('page.issueType');
    const options = computed(() => labeledOptions(ISSUE_TYPE_VALUES, typeLabels.value));
    return { options, typeLabels, issues: sampleIssues };
  },
  template: `
    <div>
      <p class="opt" v-for="opt in options" :key="opt.value">{{ opt.value }}:{{ opt.label }}</p>
      <IssueListGrouped :issues="issues" group-by="type" />
    </div>
  `
});

describe('issue type labels follow the locale', () => {
  afterEach(() => setLocale('zh-CN'));

  it('updates option labels and group headings without changing values or keys', async () => {
    setLocale('zh-CN');
    const wrapper = mount(TypeHost, { global: { plugins: [i18n, createPinia()] } });
    expect(wrapper.text()).toContain('bug:缺陷');
    const zhGroups = wrapper.getComponent(IssueListGrouped);
    expect(zhGroups.text()).toContain('缺陷');
    setLocale('en-US');
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('bug:Bug');
    expect(wrapper.text()).not.toContain('bug:缺陷');
    const buckets = groupIssuesBy(wrapper.vm.issues as never, 'type', {
      type: wrapper.vm.typeLabels
    });
    expect(buckets.find(bucket => bucket.key === 'bug')?.key).toBe('bug');
    expect(buckets.find(bucket => bucket.key === 'bug')?.label).toBe('Bug');
  });
});
```

分组组件在实现后自己读 `useLabelTable`。测试要断言切换语言后分组标题从「缺陷」变成 `Bug`，而 `groupIssuesBy` 返回的 `key` 仍是 `bug`。上面的宿主在实现完成前会失败，因为分组组件还没用这张表。补上 `computed` 的导入。样本问题若类型不够，按 `groupIssuesBy.test.ts` 的 `makeIssue` 补字段，不改分组规则。

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/views/issue/list/__tests__/type-labels.test.ts`

Expected: FAIL。分组标题仍来自写死的中文表，英文切换后不会变成 `Bug`，或宿主还编不过。

- [ ] **Step 3: Write minimal implementation**

列表、新建、编辑、详情的类型选项改为 `labeledOptions` 加 `useLabelTable('page.issueType')`。列表筛选和类型列都用这份选项。分组和看板泳道把 `useLabelTable` 的三张表传给 `groupIssuesBy` / `buildBoardSwimlanes`。不改搜索语法，不改 Agent 指令里的 `typeTextMap`。

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/views/issue/list/__tests__/type-labels.test.ts src/utils/groupIssuesBy.test.ts`

Expected: PASS。原分组测试里「进行中」「功能」仍在。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/issue frontend/src/utils/groupIssuesBy.ts frontend/src/utils/boardSwimlanes.ts
git commit -m "fix(ui): localize issue type labels and group headings"
```

## Task 4: SLA 页面

**Files:**
- Create: `frontend/src/views/settings/sla/policy-name.ts`
- Create: `frontend/src/views/settings/sla/__tests__/labels.test.ts`
- Modify: `frontend/src/views/settings/sla/index.vue`
- Do not modify: `frontend/src/service/api/sla.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { i18n, setLocale } from '@/locales';
import { policyNameAfterLocaleChange } from '../policy-name';
import SettingsSlaPage from '../index.vue';

vi.mock('@/service/api/sla', async () => {
  const actual = await vi.importActual<typeof import('@/service/api/sla')>('@/service/api/sla');
  return {
    ...actual,
    fetchSlaPolicies: vi.fn(async () => ({ data: { rows: [] }, error: null })),
    fetchHolidayPacks: vi.fn(async () => ({ data: [], error: null })),
    fetchHolidayPackPreview: vi.fn(),
    fetchHolidayPackApply: vi.fn(),
    fetchSlaRunDue: vi.fn(),
    fetchCreateSlaPolicy: vi.fn(),
    fetchUpdateSlaPolicy: vi.fn(),
    fetchDeleteSlaPolicy: vi.fn()
  };
});

vi.mock('@/service/api/workspace', () => ({
  fetchWorkspace: vi.fn(async () => ({ data: null, error: null })),
  fetchWorkspaceList: vi.fn(async () => ({ data: [], error: null })),
  fetchUpdateWorkspace: vi.fn()
}));

describe('SLA labels', () => {
  afterEach(() => setLocale('zh-CN'));

  it('switches visible metric, status and exception labels and keeps the request path', async () => {
    setLocale('zh-CN');
    const wrapper = mount(SettingsSlaPage, { global: { plugins: [i18n] } });
    await vi.waitFor(() => expect(wrapper.text()).toContain('状态停留'));
    expect(wrapper.text()).toContain('立即执行到期检查');
    expect(wrapper.text()).toContain('POST /api/sla/run-due');
    expect(wrapper.text()).not.toContain('time_in_status');
    setLocale('en-US');
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Time in status');
    expect(wrapper.text()).toContain('Run due checks');
    expect(wrapper.text()).toContain('POST /api/sla/run-due');
  });

  it('replaces a new untouched name and keeps a typed or loaded name', () => {
    expect(policyNameAfterLocaleChange({ dirty: false, loaded: false, current: '进行中停留' }, 'Time in progress')).toBe(
      'Time in progress'
    );
    expect(policyNameAfterLocaleChange({ dirty: true, loaded: false, current: '我的策略' }, 'Time in progress')).toBe(
      '我的策略'
    );
    expect(policyNameAfterLocaleChange({ dirty: false, loaded: true, current: 'Existing' }, '进行中停留')).toBe(
      'Existing'
    );
  });
});
```

页面测试在实现后还要断言：名称框初始为当前语言的默认名；调用输入更新并标为 dirty 后，再 `setLocale`，输入框文字不变。选择中的度量值仍是 `time_in_status`。假日包和策略接口的 mock 只提供空数据。若 `fetchHolidayPacks` 的返回形状和页面不一致，按页面现有读取方式改 mock。

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/views/settings/sla/__tests__/labels.test.ts`

Expected: FAIL。按钮仍是「立即 run-due」，说明里仍有 `time_in_status`，或 `policy-name` 不存在。

- [ ] **Step 3: Write minimal implementation**

页面上的枚举 label 全部来自 `lookupLabel` / `labeledOptions`。说明、按钮和占位用第 3 节的静态键。`form.metric` 等 value 保持枚举。新建表单在 `dirty === false` 且 `loaded === false` 时，用 `watch(locale)` 调用 `policyNameAfterLocaleChange`。用户通过输入事件把 `dirty` 设为真。本页今天没有把已有策略载入名称框；预留 `loaded`，载入时置真且不覆盖。不改 `runDue`、日历计算和 `sla.ts`。

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/views/settings/sla/__tests__/labels.test.ts src/service/api/sla.test.ts`

Expected: PASS。`slaMetricLabel('time_in_status')` 仍是「状态停留」。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/settings/sla
git commit -m "fix(ui): localize SLA labels without changing policy values"
```

## Task 5: 洞察页面

**Files:**
- Modify: `frontend/src/views/insights/index.vue`
- Create: `frontend/src/views/insights/__tests__/labels.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { mount } from '@vue/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createPinia } from 'pinia';
import { i18n, setLocale } from '@/locales';
import InsightsPage from '../index.vue';

vi.mock('@/service/api', () => ({
  fetchInsightsSummary: vi.fn(async () => ({
    data: {
      statusCounts: { open: 2, in_progress: 1, mystery: 1 },
      priorityCounts: { high: 2 },
      assigneeCounts: [],
      createdVsCompleted: [],
      estimateVelocity: { buckets: [] },
      cycleSnapshot: null
    },
    error: null
  })),
  fetchCycles: vi.fn(async () => ({ data: { rows: [{ id: 'c1', name: 'Sprint', status: 'active' }] }, error: null })),
  fetchInsightsReports: vi.fn(async () => ({ data: { rows: [] }, error: null })),
  fetchProjectList: vi.fn(async () => ({ data: [] })),
  fetchNotifPrefs: vi.fn(async () => ({ data: { insights_digest: false }, error: null })),
  updateNotifPrefs: vi.fn(),
  downloadInsightsExport: vi.fn(),
  createInsightsReport: vi.fn(),
  deleteInsightsReport: vi.fn(),
  patchInsightsReport: vi.fn(),
  forkInsightsReport: vi.fn(),
  tagApi: { list: vi.fn(async () => ({ data: { rows: [] }, error: null })) },
  canEditReport: () => false,
  countOpenFromStatus: () => 0,
  sumVelocityPoints: () => 0,
  filtersToSummaryParams: () => ({}),
  normalizeLabelIds: (ids: unknown) => ids,
  partitionReports: () => ({ mine: [], shared: [] })
}));

vi.mock('@/store/modules/auth', () => ({
  useAuthStore: () => ({ userInfo: { userId: 'u1' } })
}));

describe('insights labels', () => {
  afterEach(() => setLocale('zh-CN'));

  it('switches distribution labels and keeps the unknown key and the CSV wording', async () => {
    setLocale('zh-CN');
    const wrapper = mount(InsightsPage, { global: { plugins: [i18n, createPinia()] } });
    await vi.waitFor(() => expect(wrapper.text()).toContain('待办'));
    expect(wrapper.text()).toContain('进行中');
    expect(wrapper.text()).toContain('高');
    expect(wrapper.text()).toContain('mystery');
    expect(wrapper.text()).toContain('导出 CSV');
    expect(wrapper.text()).not.toMatch(/\bOR\b/);
    expect(wrapper.text()).not.toMatch(/digest/i);
    setLocale('en-US');
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Open');
    expect(wrapper.text()).toContain('In progress');
    expect(wrapper.text()).toContain('High');
    expect(wrapper.text()).toContain('mystery');
    expect(wrapper.text()).toContain('Export CSV');
  });
});
```

mock 的导出要和 `@/service/api` 的实际导入对齐。未知键 `mystery` 必须原样留下。下载文件名仍是 `insights-export.csv`，用源码断言或调用导出函数时检查，不改那个字符串。

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/views/insights/__tests__/labels.test.ts`

Expected: FAIL。分布仍显示 `open` / `in_progress`，副标题仍含 OR 或 digest。

- [ ] **Step 3: Write minimal implementation**

分布标签用 `lookupLabel`。副标题、导出、摘要开关、冲刺后缀和估点标题用设计第 3 节的键。`updateNotifPrefs({ insights_digest })` 的字段名不变。不改统计和筛选参数。

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/views/insights/__tests__/labels.test.ts`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/insights
git commit -m "fix(ui): localize insights labels and keep CSV"
```

## Task 6: 门禁

- [ ] **Step 1: Run the frontend suite, lint and build**

```bash
cd frontend && npx vitest run
cd frontend && npx eslint src/locales/display-label.ts src/locales/use-label-table.ts src/locales/__tests__/residual-copy.test.ts src/locales/langs/zh-cn.ts src/locales/langs/en-us.ts src/typings/app.d.ts src/constants/issue.ts src/views/initiatives/index.vue src/views/initiatives/__tests__/create-label.test.ts src/views/issue/list/index.vue src/views/issue/list/modules/IssueListGrouped.vue src/views/issue/list/modules/IssueBoard.vue src/views/issue/list/__tests__/type-labels.test.ts src/views/issue/create/index.vue src/views/issue/edit/index.vue src/views/issue/detail/index.vue src/views/settings/sla/index.vue src/views/settings/sla/policy-name.ts src/views/settings/sla/__tests__/labels.test.ts src/views/insights/index.vue src/views/insights/__tests__/labels.test.ts src/utils/groupIssuesBy.ts src/utils/boardSwimlanes.ts
cd frontend && npm run build
```

Expected: Vitest 全过，数字按这次记录。eslint 与 `22c8d8b` 上同一批已有文件对比，不新增错误。构建通过。

- [ ] **Step 2: Remeasure vue-tsc**

在本分支和干净的 `22c8d8b` 上分别运行 `npx vue-tsc --noEmit --skipLibCheck`。生成文件的既有语法错误不修。对照后照实写通过或未通过。

- [ ] **Step 3: Leave backend and CLI unrun**

`git diff 22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34 -- backend agent-harness` 应为空。不要把没跑的 pytest 写成通过。

- [ ] **Step 4: Browser check**

用本地编译结果或本地 dev（端口保持 9527）打开 `/initiatives`、`/issue/list`、`/settings/sla`、`/insights` 的中文和英文。能打开新建、编辑、详情的类型选项就一并看。截图只记录实际拿到的文件。打不开的页面写明原因，不连接现网。

- [ ] **Step 5: Review**

独立审查只看本分支相对 `22c8d8b` 的 diff。有实质问题就先改再提交。然后更新 PR #6 的说明。不合并、不部署。
