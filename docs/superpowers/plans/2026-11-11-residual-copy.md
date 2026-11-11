# 残留界面文案 Implementation Plan

> **For agentic workers:** 本计划在 Yuri 书面批准设计之前不得执行。批准后按任务顺序做。步骤用 `- [ ]`。用词以 `docs/superpowers/specs/2026-11-11-residual-copy-design.md` 第 3 节为准，不要另换近义词。

**Goal:** 让举措、问题类型、SLA 和洞察上残留的英文和错字变成当前语言的可读文字，存储值和接口保持原样。

**Architecture:** 句子和枚举显示名放进现有的 `zh-cn.ts` 与 `en-us.ts`。页面用 `$t` 取当前语言。选项的 `value` 仍是原来的枚举。未知值原样显示。

**Tech Stack:** Vue 3、vue-i18n、Vitest。不改 Naive 主题，不改后端。

## Global Constraints

- 基线是 `main` @ `22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34`。工作分支是 `cursor/residual-copy-design-658f`。不要往已合并的 PR #5 分支上追加。
- Yuri 批准本设计和本计划之前，停止。不写实现，不写测试文件。
- 不合并、不部署、不连接现网，不写入口令。
- 不改 OAuth、鉴权、路由、查询语法、CSV 列、请求字段和已有数据。
- 不改颜色、布局、响应式、`#5e6ad2`、亮色和暗色。
- 不改生成的 `frontend/src/typings/api/issue.d.ts` 和 `frontend/src/typings/components.d.ts`。
- 手写的 `frontend/src/typings/app.d.ts` 只补本批文案键。
- 客户侧「新建需求」保持这四个字。
- `slaMetricLabel` 和 `slaMetricBadgePrefix` 不改，避免动问题详情上的 SLA 徽章。

## Task 1: 文案目录测试

**Files:**
- Create: `frontend/src/locales/__tests__/residual-copy.test.ts`
- Test later: `frontend/src/locales/langs/zh-cn.ts`, `frontend/src/locales/langs/en-us.ts`, `frontend/src/constants/issue.ts`, `frontend/src/service/api/sla.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { IssueTypeEnum } from '@/constants/issue';
import { SLA_METRICS } from '@/service/api/sla';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

describe('residual copy', () => {
  it('fixes the initiative verb and keeps the customer request verb', () => {
    expect(zh.page.shell.createInitiative).toBe('新建举措');
    expect(en.page.shell.createInitiative).toBe('New initiative');
    expect(zh.page.shell.createRequest).toBe('新建需求');
    const zhSource = readFileSync(new URL('../langs/zh-cn.ts', import.meta.url), 'utf8');
    expect(zhSource).not.toContain('新建议措');
  });

  it('translates issue type labels without changing enum values', () => {
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
```

显示函数另测一条：未知键原样返回。实现时把函数放在 `frontend/src/locales/display-label.ts`，测试传入文案表，不启动页面。

```ts
import { lookupLabel } from '../display-label';

it('returns an unknown code unchanged', () => {
  expect(lookupLabel({ bug: '缺陷' }, 'bug')).toBe('缺陷');
  expect(lookupLabel({ bug: '缺陷' }, 'custom')).toBe('custom');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/locales/__tests__/residual-copy.test.ts`  
Expected: FAIL，键还不存在。

- [ ] **Step 3: Write minimal implementation**

按设计第 3 节把键补进 `app.d.ts`、`zh-cn.ts`、`en-us.ts`。`lookupLabel` 只做查表。不要改 `IssueTypeEnum` 和 `SLA_METRICS`。

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/locales/__tests__/residual-copy.test.ts src/locales/__tests__/route-labels.test.ts`  
Expected: PASS。`route-labels` 里「新建需求」和「新建问题」仍通过。

## Task 2: 举措空状态

**Files:**
- Modify: `frontend/src/views/initiatives/index.vue`
- Test: `frontend/src/locales/__tests__/residual-copy.test.ts`

- [ ] **Step 1: Write the failing test**

在 Task 1 的文件里加一条：空状态按钮的模板使用 `page.shell.createInitiative`，该处不再有单独的 `>新建</NButton>`。

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL，第 192 行仍是写死的「新建」。

- [ ] **Step 3: Write minimal implementation**

空状态按钮改为 `{{ $t('page.shell.createInitiative') }}`。主按钮已经用这个键。不改弹窗字段和创建请求。

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS。

## Task 3: 问题类型显示

**Files:**
- Modify: `frontend/src/views/issue/list/index.vue`
- Modify: `frontend/src/views/issue/create/index.vue`
- Modify: `frontend/src/views/issue/edit/index.vue`
- Modify: `frontend/src/views/issue/detail/index.vue`（仅下拉和类型徽章所用的 options）
- Modify: `frontend/src/utils/groupIssuesBy.ts`
- Modify: `frontend/src/constants/issue.ts`（只把 `bug` 的兜底 label 改成「缺陷」）

- [ ] **Step 1: Write the failing test**

断言 `lookupLabel(zh.page.issueType, IssueTypeEnum.Bug)` 是「缺陷」，并且 `IssueTypeEnum.Bug` 仍是 `bug`。再断言列表列渲染使用显示函数的结果，而不是字符串 `Bug`。分组桶的 `key` 仍是枚举值。

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL。

- [ ] **Step 3: Write minimal implementation**

下拉 options 的 `value` 继续用枚举，`label` 用 `$t('page.issueType.' + value)`。列表类型列、分组标题走同一查表。不改搜索语法帮助。不改详情里生成 Agent 指令的 `typeTextMap`。不改 `groupIssuesBy` 的分桶键和顺序。现有 `groupIssuesBy.test.ts` 对「进行中」的断言必须仍然通过。

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/locales/__tests__/residual-copy.test.ts src/utils/groupIssuesBy.test.ts`  
Expected: PASS。

## Task 4: SLA 页面

**Files:**
- Modify: `frontend/src/views/settings/sla/index.vue`
- Do not modify: `frontend/src/service/api/sla.ts`

- [ ] **Step 1: Write the failing test**

Task 1 已经锁住说明文字。再断言页面把状态下拉的 label 交给 `page.issueStatus`，value 仍来自 `ISSUE_STATUSES`。度量、例外种类同样只改 label。

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL，说明里仍有 `resolved/closed` 和 `time_in_status`。

- [ ] **Step 3: Write minimal implementation**

按设计第 3 节替换按钮、说明、占位、卡片标题、例外显示和假日包目标的文字。名称框初值按当前语言使用「进行中停留」或 `Time in progress`。不改 `runDue` 的请求、日历计算、假日包接口和时区选项的 value。不改 `sla.ts`。

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/locales/__tests__/residual-copy.test.ts src/service/api/sla.test.ts`  
Expected: PASS。`slaMetricLabel('time_in_status')` 仍是「状态停留」。

## Task 5: 洞察页面

**Files:**
- Modify: `frontend/src/views/insights/index.vue`

- [ ] **Step 1: Write the failing test**

断言中文副标题不含 OR 和 digest，导出按钮含 CSV。状态分布的展示名来自 `page.issueStatus`，未知键原样返回。下载文件名仍是 `insights-export.csv`。

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL。

- [ ] **Step 3: Write minimal implementation**

按设计第 3 节改副标题、导出、摘要开关、冲刺后缀、估点标题和两张分布图的标签。`updateNotifPrefs({ insights_digest })` 的字段名不变。不改统计计算和筛选参数。

- [ ] **Step 4: Run test to verify it passes**

Expected: PASS。

## Task 6: 门禁

- [ ] **Step 1: Run the frontend suite and build**

Run from `frontend`:

```bash
npx vitest run
npx eslint src/locales/langs/zh-cn.ts src/locales/langs/en-us.ts src/locales/display-label.ts src/locales/__tests__/residual-copy.test.ts src/views/initiatives/index.vue src/views/issue/list/index.vue src/views/issue/create/index.vue src/views/issue/edit/index.vue src/views/issue/detail/index.vue src/views/settings/sla/index.vue src/views/insights/index.vue src/utils/groupIssuesBy.ts src/constants/issue.ts src/typings/app.d.ts
npm run build
```

Expected: Vitest 全过。数字按这次结果记录，不写 474。eslint 不新增错误。构建通过。

- [ ] **Step 2: Remeasure vue-tsc**

Run: `npx vue-tsc --noEmit --skipLibCheck`  
在干净的 `22c8d8b` 上跑同一条命令作对照。生成文件的既有语法错误不修。对照后照实写通过或未通过。

- [ ] **Step 3: Leave backend and CLI unrun**

`git diff 22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34 -- backend agent-harness` 应为空。不要把没跑的 pytest 写成通过。

- [ ] **Step 4: Browser check after the build**

中文打开 `/initiatives`、`/issue/list`、`/settings/sla`、`/insights`。核对新建举措、类型「缺陷」、SLA 说明里的人话和路径、洞察副标题。切到英文后这四处是英文。不要求改布局。没有本地账号时如实写未测，不要连现网。

- [ ] **Step 5: Commit**

实现提交用 `fix(ui):`。验收记录在实现通过之后另写，不放进本设计提交。
