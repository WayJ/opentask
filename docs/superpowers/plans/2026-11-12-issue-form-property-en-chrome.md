# 新建编辑与详情属性英文铬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. 步骤使用 checkbox。获批前不执行。执行时从精确已接受头 `7aed13703c8b6e117db4d7f0c00b7f2069afa8d2` 开新的隔离普通检出（`.git` 为目录，不是 worktree），新建分支，不改 PR13 已存提交，不改 PR6–12，不 amend / 不 rebase 已验 SHA。

**Goal:** 把新建/编辑页内标题与主操作、属性卡标签（含高级选项展开项与同控件占位），以及详情侧栏已划定字段标签，从写死中文改成 `$t('page.issueForm.*')`；状态/优先级选项值改走已有 `page.issueStatus` / `page.issuePriority`。英文下显示已锁定的英文，中文用词保持不变。

**Architecture:** 新键集中在 `page.issueForm`，两份 locale 与 `App.I18n.Schema` 同步。选项值复用已有 label table，不改 `constants/issue.ts`。冲刺下拉空项复用 `page.issueList.noneCycle`。已有 `create/surface.test.ts` 对范围内中文的冻结必须改成冻结 `$t` 键，并继续冻结范围外中文；另增键完整性与接线测试。

**Tech Stack:** Vue 3.5、vue-i18n、Vitest 4、已有 `$t` / `useLabelTable` / `labeledOptions` / `App.I18n.Schema`。

## Global Constraints

- 获批前不建分支、不 commit、不改产品。获批后的起点只允许 `7aed13703c8b6e117db4d7f0c00b7f2069afa8d2`。
- 白名单恰好这些路径：`docs/superpowers/specs/2026-11-12-issue-form-property-en-chrome-design.md`、`docs/superpowers/plans/2026-11-12-issue-form-property-en-chrome.md`、`frontend/src/locales/langs/zh-cn.ts`、`frontend/src/locales/langs/en-us.ts`、`frontend/src/typings/app.d.ts`、`frontend/src/views/issue/create/index.vue`、`frontend/src/views/issue/edit/index.vue`、`frontend/src/views/issue/detail/index.vue`、`frontend/src/views/issue/create/surface.test.ts`、`frontend/src/locales/__tests__/issue-form-property-chrome.test.ts`。出现白名单以外的已跟踪改动就停止。不要改 `edit/surface.test.ts`、详情 `focus.test.ts` / `description-surface.test.ts`、列表铬测试、`constants/issue.ts`。
- 首个 commit 只有两份文档。产品文件在 RED 原件落盘之后才改。
- 不准改 `frontend/src/constants/issue.ts`、枚举值、Milestone 标签与「无 Milestone」「选择 Milestone」、描述编辑区、使用模板、附件卡、「自定义字段（可选）」、详情顶栏（含 `startEdit('status'` 按钮上的「状态」）/评论/附件/子问题、看板/批量/快捷、`groupIssuesBy.ts`、列表页、焦点 CSS、PR6–13 头。Milestone 的共享空态「未分配」（约 197、1913 行）按 design 第 3 节允许接 `page.issueForm.unassigned`，只限这一句。
- 中英文案必须与已批 design 第 3 节锁定表逐字一致，不得另撰。`createTitle` 英文是 Create issue，不是 New issue，也不是 Create Issue。`cycle` 英文是 Cycle，不是 Sprint。`assignee` 中文是指派人，不是负责人。状态/优先级/类型选项值必须分别走已有 `page.issueStatus` / `page.issuePriority` / `page.issueType`，不得另造表；`page.issueStatus.open` 英文保持 Open，`page.issuePriority.critical` 英文保持 Urgent。冲刺下拉空项复用 `page.issueList.noneCycle`，不另造键。不要复用 `page.shell.createIssue`、`route.issue_create`、`route.issue_edit`、`page.issueList.columns.*`。
- Agent 指令生成器里负责人回退的「未分配」（约 419 行）以及「待处理」等映射不在范围。禁止全局替换「未分配」「未设置」。报告人的「未设置」只改报告人字段；侧栏「项目」「估点」上的 `placeholder="未设置"` 保持写死。
- 不测焦点环，不量对比度。深色截图不是本刀失败条件。
- 每个 RED 与 GREEN 在改下一步之前把原件写入仓库外目录：HEAD、porcelain、test blob、diff、COMMAND、CWD、TZ、stdout、stderr、EXIT。
- 四门使用下列命令：`pnpm exec vitest run`、`pnpm exec vite build --mode prod`（仓库外 `--config` 与 `cacheDir`，CWD 为新检出 `frontend/`）、`pnpm exec vue-tsc --noEmit --skipLibCheck`、`pnpm exec eslint .`。不用 `pnpm run lint`，不用 `eslint --fix`，不用 `vite --mode test`。禁止 unshare 空挂 `.vite`。`.env.prod` 只允许从已核过的干净来源拷贝（sha256 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`，1896 字节），禁止手写/入库/在报告里写 env 正文或键值。若找不到该原件，STOP 并交原文，不要改写或用 `.env.example` 充数后继续声称已核。`loadEnv('prod')` 只记前缀是否非空及长度。若生成文件被清空，STOP，不要自行轮循还原。
- baseline 是获批后在干净 `7aed1370` 上当次跑出的四门禁原文。不得用第 1 刀记录过的 88/521、tsc 29、lint 872 代替。vue-tsc 与 eslint 对照这一次 baseline 的诊断原文，行号可以漂。baseline 非 0 就保持非 0，不报成全绿。新增诊断则停止。
- 钩子按既有限制：不改 hooksPath、不改校验源码、不用 `SKIP` / `--no-verify`、不再做 hook 路径实验。若新检出按仓库既有方式装上 hooks，只允许删除本检出的 `.git/hooks/pre-commit`，必须保留已装 `commit-msg`。在仓库根目录做正常 `git commit`，不要在 `frontend/` 里提交。没有当次 hook 打开路径原件，不得把 EXIT 0 写成已校验本检出这份说明。若再遇 `frontend/.git/COMMIT_EDITMSG` 或同类 ENOENT，立即停交原文，不二次重试，不改校验。
- 新检出不得写入或 reset 主仓 `/agent/repos/opentask`、既有 pin / old / PR11 / 列表铬实施克隆，以及其他已验检出。9541 pid 59419 不要动。本计划内一律不 fetch、不 push 任何 remote（origin 可能是本地路径）。
- 计划结束于浏览器核对原件和两份独立 Grok 原文落盘。不 push，不开 PR，不 merge，不 deploy。停下来等 Yuri 验收。第 3 刀不得在本计划内开写。

---

### Task 0: 隔离检出、基线、文档提交

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-issue-form-property-en-chrome-design.md`
- Create: `docs/superpowers/plans/2026-11-12-issue-form-property-en-chrome.md`

**Interfaces:**
- Consumes: 已验提交 `7aed13703c8b6e117db4d7f0c00b7f2069afa8d2`，已批 design 的 sha256（以获批时 `/workspace/designs/issue-form-property-en-chrome-spec/2026-11-12-issue-form-property-en-chrome-design.md` 为准，拷入仓库时不得改写正文）
- Produces: 新隔离分支上的文档提交，以及仓库外 `…/issue-form-property-en-chrome-logs/baseline/` 里的四门禁原件

- [ ] **Step 1: 只在获批后开普通隔离检出**

从一份已经含有 `7aed13703c8b6e117db4d7f0c00b7f2069afa8d2` 的干净来源做普通 `git clone`（优先本地已有、且不需要写入的仓库；否则从 GitHub `WayJ/opentask` 克隆后 detach）。不要用 worktree。不要把先前实施检出直接改造成工作区。

```bash
git clone <verified-source> /tmp/cursor/opentask-issue-form-property-en-chrome-clone
git -C /tmp/cursor/opentask-issue-form-property-en-chrome-clone switch --detach 7aed13703c8b6e117db4d7f0c00b7f2069afa8d2
git -C /tmp/cursor/opentask-issue-form-property-en-chrome-clone switch -c cursor/issue-form-property-en-chrome-4333
```

`git rev-parse HEAD` 必须打印 `7aed13703c8b6e117db4d7f0c00b7f2069afa8d2`。`git status --porcelain` 必须为空。`.git` 必须是目录。随后再核：既有已验检出与主仓 config / `node_modules/.vite` mtime 未变（找得到才核，找不到就记录缺失，不要去重建它们）。

给新检出的 `frontend/node_modules` 做指向一份已存在、可解析依赖的 `node_modules` 的符号链接，或在本检出内用冻结锁文件安装。不添加新依赖。后面启动 Vite 必须使用仓库外 `--config`，把 `cacheDir` 写到仓库外日志目录，端口不得占用 9541 或 9544。本计划内一律不 fetch、不 push。钩子按 Global Constraints 处理。

- [ ] **Step 2: 在干净 7aed1370 上保存当次四门禁**

CWD 是新检出的 `frontend`。先按 Global Constraints 准备 `.env.prod` 并确认 `VITE_ICON_LOCAL_PREFIX` 非空后再跑 build。四条命令分开跑，各写 `stdout.txt`、`stderr.txt` 和 `meta.txt`。

```bash
pnpm exec vitest run
pnpm exec vite build --mode prod --config /tmp/cursor/opentask-readonly/issue-form-property-en-chrome-logs/vite.readonly.config.mjs
pnpm exec vue-tsc --noEmit --skipLibCheck
pnpm exec eslint .
```

这四份输出就是本切片 baseline。把 vue-tsc 与 eslint 的每一行诊断原文留下。

- [ ] **Step 3: 只提交两份文档**

把已批 design 与本 plan 拷入上面两个路径。不要改写已批 design 正文。`git add` 之后 `git diff --cached --name-only` 恰好是这两行。在仓库根目录执行：

```bash
git commit -m "docs: specify issue form and property English chrome"
```

提交后 `git status --porcelain` 为空，`git rev-parse HEAD^` 是 `7aed13703c8b6e117db4d7f0c00b7f2069afa8d2`。钩子若失败，按 Global Constraints 停交原文。

---

### Task 1: RED

**Files:**
- Modify: `frontend/src/views/issue/create/surface.test.ts`
- Create: `frontend/src/locales/__tests__/issue-form-property-chrome.test.ts`

**Interfaces:**
- Consumes: `7aed1370` 上新建/编辑/详情仍写死「创建问题」「编辑问题」「保存更改」「属性设置」「指派人」等，优先级/状态选项仍绑常量中文 `label`，且尚无 `page.issueForm` 对象
- Produces: 失败断言指向这些中文冻结和新键缺失。编辑/详情既有测试与列表铬测试不得改，RED 时它们仍通过

- [ ] **Step 1: 先只改测试，不改 locale、`app.d.ts` 或三份 Vue**

把 `create/surface.test.ts` 里范围内的中文冻结改成 `$t` 键，并保留范围外中文。`createTitle` 必须出现两次；标题字面量和主按钮那一行独立的「创建问题」都要断言已消失，但不要写 `not.toContain('创建问题')`：

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';

describe('issue create surface', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/views/issue/create/index.vue'), 'utf8');

  it('imports the local surface sheet and drops the light-only hex colors', () => {
    expect(source).toContain("import '@/styles/issue-surface.css';");
    expect(source).not.toMatch(/#(?:fff|ffffff|f5f7fa|e8eaed|1a1a1a|aaa|f9fafb)\b/i);
    expect(source).not.toContain('outline: none');
    expect(source).toContain('background: var(--issue-surface)');
    expect(source).toContain('color: var(--issue-ink)');
    expect((source.match(/\$t\('page\.issueForm\.createTitle'\)/g) ?? []).length).toBe(2);
    expect(source).not.toContain('<NText strong style="font-size: 16px; margin-left: 12px">创建问题</NText>');
    expect(source).not.toMatch(/^\s+创建问题\s*$/m);
    expect(source).toContain('使用模板');
    expect(source).toContain('从模板创建问题');
    expect(source).toContain("$t('page.issueForm.advanced')");
    expect(source).toContain('const advancedExpanded = ref(false)');
    expect(source).toContain('请输入问题标题');
    expect(source).toContain('问题创建成功');
    expect(source).toContain('问题创建失败');
    expect(source).toContain("$t('page.issueForm.linkedTaskId')");
    expect(source).toContain("$t('page.issueForm.linkedRequirementId')");
    expect(source).toContain("$t('page.issueForm.assigneeId')");
    expect(source).not.toContain('>高级选项<');
  });
});
```

新建 `frontend/src/locales/__tests__/issue-form-property-chrome.test.ts`。`keysOf` 可与列表铬测试相同。typings 提取函数必须用 `issueForm\s*:\s*\{` 定位**对象**形状的 `page.issueForm`，禁止用第一条 `issueForm:`（那是 `page.shell.issueForm: string`）。断言键集合三处一致，并抽查锁定值与接线：

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

function keysOf(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object') return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    keysOf(child, prefix ? `${prefix}.${key}` : key)
  );
}

function schemaKeysOfIssueForm(source: string): string[] {
  const match = /(?:^|[\n\r;{])\s*issueForm\s*:\s*\{/.exec(source);
  if (!match) return [];
  const start = source.indexOf('{', match.index);
  if (start < 0) return [];

  // Walker control flow stays aligned with the list-chrome typings reader.
  /* eslint-disable complexity, no-continue */
  function parseObject(from: number, prefix: string): { keys: string[]; end: number } {
    const keys: string[] = [];
    let i = from + 1;
    while (i < source.length) {
      while (i < source.length && /[\s,;]/.test(source[i])) i += 1;
      if (source[i] === '}') return { keys, end: i + 1 };
      if (source.startsWith('//', i)) {
        const nl = source.indexOf('\n', i);
        i = nl < 0 ? source.length : nl + 1;
        continue;
      }
      if (source.startsWith('/*', i)) {
        const endC = source.indexOf('*/', i + 2);
        i = endC < 0 ? source.length : endC + 2;
        continue;
      }
      const keyMatch = /^[A-Za-z_][A-Za-z0-9_]*/.exec(source.slice(i));
      if (!keyMatch) {
        i += 1;
        continue;
      }
      const key = keyMatch[0];
      i += key.length;
      while (i < source.length && /\s/.test(source[i])) i += 1;
      if (source[i] !== ':') continue;
      i += 1;
      while (i < source.length && /\s/.test(source[i])) i += 1;
      const path = prefix ? `${prefix}.${key}` : key;
      if (source[i] === '{') {
        const nested = parseObject(i, path);
        keys.push(...nested.keys);
        i = nested.end;
      } else {
        keys.push(path);
        while (i < source.length && source[i] !== ';' && source[i] !== ',' && source[i] !== '}') i += 1;
        if (source[i] === ';' || source[i] === ',') i += 1;
      }
    }
    return { keys, end: i };
  }
  /* eslint-enable complexity, no-continue */

  return parseObject(start, '').keys;
}

describe('issue form and property chrome copy', () => {
  it('keeps locked Chinese and English form chrome', () => {
    expect(zh.page.issueForm.createTitle).toBe('创建问题');
    expect(en.page.issueForm.createTitle).toBe('Create issue');
    expect(en.page.issueForm.createTitle).not.toBe('Create Issue');
    expect(en.page.issueForm.createTitle).not.toBe('New issue');
    expect(zh.page.issueForm.editTitle).toBe('编辑问题');
    expect(en.page.issueForm.editTitle).toBe('Edit issue');
    expect(zh.page.issueForm.saveChanges).toBe('保存更改');
    expect(en.page.issueForm.saveChanges).toBe('Save changes');
    expect(zh.page.issueForm.propertySettings).toBe('属性设置');
    expect(en.page.issueForm.propertySettings).toBe('Property settings');
    expect(zh.page.issueForm.assignee).toBe('指派人');
    expect(en.page.issueForm.assignee).toBe('Assignee');
    expect(zh.page.issueForm.cycle).toBe('冲刺');
    expect(en.page.issueForm.cycle).toBe('Cycle');
    expect(en.page.issueForm.cycle).not.toBe('Sprint');
    expect(zh.page.issueForm.selectProjectOptional).toBe('选择项目（可选）');
    expect(en.page.issueForm.selectProjectOptional).toBe('Select project (optional)');
    expect(zh.page.issueForm.unassigned).toBe('未分配');
    expect(en.page.issueForm.unassigned).toBe('Unassigned');
    expect(zh.page.issueList.noneCycle).toBe('无 Cycle');
    expect(en.page.issueList.noneCycle).toBe('No cycle');
    expect(en.page.issueStatus.open).toBe('Open');
    expect(zh.page.issueStatus.open).toBe('待办');
    expect(en.page.issuePriority.critical).toBe('Urgent');
    expect(zh.page.issuePriority.critical).toBe('紧急');
    expect(keysOf(zh.page.issueForm).sort()).toEqual(keysOf(en.page.issueForm).sort());
    const typings = readFileSync(resolve(process.cwd(), 'src/typings/app.d.ts'), 'utf8');
    expect(schemaKeysOfIssueForm(typings).sort()).toEqual(keysOf(zh.page.issueForm).sort());
    expect(en.page.issueForm.createTitle).not.toBe(zh.page.issueForm.createTitle);
    expect(en.page.issueForm.assignee).not.toBe(zh.page.issueForm.assignee);
  });

  it('wires create, edit, and detail to the new keys and leaves constants Chinese labels alone', () => {
    const create = readFileSync(resolve(process.cwd(), 'src/views/issue/create/index.vue'), 'utf8');
    const edit = readFileSync(resolve(process.cwd(), 'src/views/issue/edit/index.vue'), 'utf8');
    const detail = readFileSync(resolve(process.cwd(), 'src/views/issue/detail/index.vue'), 'utf8');
    const constants = readFileSync(resolve(process.cwd(), 'src/constants/issue.ts'), 'utf8');
    expect((create.match(/\$t\('page\.issueForm\.createTitle'\)/g) ?? []).length).toBe(2);
    expect(create).toContain("$t('page.issueForm.propertySettings')");
    expect(create).toContain("useLabelTable('page.issuePriority')");
    expect(create).toContain('使用模板');
    expect(create).toContain('从模板创建问题');
    expect(create).not.toContain('<NText strong style="font-size: 16px; margin-left: 12px">创建问题</NText>');
    expect(create).not.toMatch(/^\s+创建问题\s*$/m);
    expect(edit).toContain("$t('page.issueForm.editTitle')");
    expect(edit).toContain("$t('page.issueForm.saveChanges')");
    expect(edit).not.toContain('保存更改');
    expect(edit).toContain("useLabelTable('page.issuePriority')");
    expect(edit).not.toContain('<NText strong style="font-size: 16px; margin-left: 12px">编辑问题</NText>');
    expect(detail).toContain("$t('page.issueForm.status')");
    expect(detail).toContain("$t('page.issueForm.assignee')");
    expect(detail).toContain("$t('page.issueForm.cycle')");
    expect(detail).toContain("useLabelTable('page.issueStatus')");
    expect(detail).toContain("useLabelTable('page.issuePriority')");
    expect(detail).toContain("page.issueList.noneCycle");
    expect(detail).not.toContain('label="状态"');
    expect(detail).not.toContain('label="指派人"');
    const statusBtnStart = detail.indexOf("startEdit('status'");
    expect(statusBtnStart).toBeGreaterThan(-1);
    const statusBtnEnd = detail.indexOf('</NButton>', statusBtnStart);
    expect(detail.slice(statusBtnStart, statusBtnEnd)).toContain('状态');
    expect(detail).toMatch(
      /assigneeInfo = issueData\.assignee\s*\?\s*issueData\.assignee\.sso_name \|\| issueData\.assignee\.sso_account \|\| issueData\.assignee\.id\s*:\s*'未分配'/
    );
    expect(detail).toContain('label="Milestone"');
    expect(detail).toContain("'无 Milestone'");
    expect(detail).toContain('选择 Milestone');
    expect(detail).toMatch(/label="项目"[\s\S]*?placeholder="未设置"/);
    expect(detail).toMatch(/label="估点"[\s\S]*?placeholder="未设置"/);
    expect(constants).toContain("label: '待办'");
    expect(constants).toContain("label: '紧急'");
  });
});
```

其余锁定键（`start`、`dueDate`、`watchers`、高级选项占位等）以已批 design 第 3 节为准，全部写入 locale；本测试至少抽查上表这些，键集合全量比对即可覆盖其余键名。不要在 RED 步骤改产品文件。

- [ ] **Step 2: 跑 RED 并保存原件**

CWD 仍是新检出 `frontend`：

```bash
pnpm exec vitest run src/views/issue/create/surface.test.ts src/locales/__tests__/issue-form-property-chrome.test.ts
```

必须失败：新建页还没有这些 `$t` 键，`page.issueForm` 还不存在。把 stdout / stderr / EXIT 和失败断言原文写入仓库外 `red/`。不要在 RED 变绿之前改产品。

---

### Task 2: 键表、Schema 与三页接线（GREEN）

**Files:**
- Modify: `frontend/src/locales/langs/zh-cn.ts`
- Modify: `frontend/src/locales/langs/en-us.ts`
- Modify: `frontend/src/typings/app.d.ts`
- Modify: `frontend/src/views/issue/create/index.vue`
- Modify: `frontend/src/views/issue/edit/index.vue`
- Modify: `frontend/src/views/issue/detail/index.vue`

**Interfaces:**
- Consumes: 已批 design 第 3 节锁定表；已有 `useLabelTable` / `labeledOptions`；`issueStatusOptions` / `issuePriorityOptions` / `issueTypeOptions` 只提供 `value` 顺序
- Produces: 三页范围内铬走 `$t` 或已有 label table；常量文件字节级不改（除允许的空白/换行以外，本刀直接不准改它）

- [ ] **Step 1: 写入 locale 与 Schema**

在 `page` 下、与 `issueList` 并列增加 `issueForm` 对象，键与第 3 节逐字相同。不要改 `page.shell.issueForm` 字符串。不要改 `page.issueStatus` / `page.issuePriority` / `page.issueType` / `page.issueList.noneCycle` 的现有值。`App.I18n.Schema.page.issueForm` 必须是对象形状，字段与 locale 一致。

- [ ] **Step 2: 新建页与编辑页**

`createTitle` 用于标题和主按钮，两处各写一次 `$t('page.issueForm.createTitle')`。编辑页补 `import { $t } from '@/locales'`。属性卡标签和占位改 `$t`。优先级改为：

```ts
const priorityLabels = useLabelTable('page.issuePriority');
const priorityOptions = computed(() =>
  labeledOptions(
    issuePriorityOptions.map(option => option.value),
    priorityLabels.value
  )
);
```

模板里 `:options="priorityOptions"`，不要再直接绑 `issuePriorityOptions`。类型接线保持现有 `page.issueType`。高级选项展开项与占位一并改 `$t`。不要动「使用模板」、描述区、附件卡、返回提示、未保存、退出确认和 toast。

- [ ] **Step 3: 详情侧栏**

字段标签改 `$t('page.issueForm.*')`。用 `useLabelTable('page.issueStatus')` 和 `useLabelTable('page.issuePriority')` 做成 computed options，替换 `const statusOptions = issueStatusOptions` / `const priorityOptions = issuePriorityOptions`。`display-value` 必须取自翻译后的 options 或 `lookupLabel`，不能再读常量里的中文 `label`。

冲刺空项用 `$t('page.issueList.noneCycle')`。`cycleDisplayValue`、`assigneesDisplayValue`，以及指派人/冲刺和已确认允许的 Milestone 空态（`milestoneDisplayValue` 与 placeholder，约 197、1913 行），在没有值时用 `$t('page.issueForm.unassigned')`；这些 computed 必须依赖当前 locale。报告人空态只用 `page.issueForm.unset`。不要改 Agent 指令里负责人三元的「未分配」（约 419 行），不要改「项目」「估点」上写死的 `placeholder="未设置"`，不要改 Milestone 标签、「无 Milestone」「选择 Milestone」，也不要改详情顶栏 `startEdit('status'` 按钮上的「状态」。禁止全局替换「未分配」「未设置」。

- [ ] **Step 4: 跑 GREEN 并提交产品改动**

```bash
pnpm exec vitest run src/views/issue/create/surface.test.ts src/views/issue/edit/surface.test.ts src/views/issue/detail/focus.test.ts src/views/issue/detail/description-surface.test.ts src/locales/__tests__/issue-form-property-chrome.test.ts src/locales/__tests__/issue-list-chrome.test.ts
```

必须通过。再跑完整 `pnpm exec vitest run`，对照 Task 0 baseline：本刀只允许新增上述通过的测试，不得新增失败。把 GREEN 原件写入仓库外 `green/`。`git add` 后已跟踪路径必须仍在白名单内。在仓库根目录提交：

```bash
git commit -m "fix: localize issue form and property chrome for English"
```

提交后 porcelain 为空。父提交是文档提交。不准 amend 已验 SHA。

---

### Task 3: 四门对照

- [ ] **Step 1: 再跑四门，对照 Task 0 baseline**

命令与 Task 0 相同。vitest 应在 baseline 上增加本刀测试且 EXIT 0。vue-tsc / eslint 不得新增诊断（行号可漂）。build EXIT 须与 baseline 相同。原件写入 `gates/`。若新增诊断或 vitest 失败，STOP。

---

### Task 4: 浏览器核对

- [ ] **Step 1: 用仓库外 Vite 配置启动预览，合成 token，采原图**

至少：英文浅色 1280×800 的新建、编辑、详情各一张；中文浅色 1280×800 对照各一张。核对第 4 节验收句，尤其是：Create issue / Edit issue / Save changes / Property settings / Active 不是本页问题（本页状态是 Open）；`critical` 显示 Urgent；冲刺标签是 Cycle；指派人是 Assignee；高级选项无省略号；使用模板等范围外中文可以仍在。文档标题仍是 Create Issue / Edit Issue / Issue Detail。原图与核对笔记写入仓库外 `browser/`。不要把合成 token 或 cookie 写入仓库。

---

### Task 5: 双 Grok 与停手

- [ ] **Step 1: 两份独立 grok-4.7-high 审查**

一份对 design+实现是否同 SHA 对齐，一份对代码。保存完整原文。不要把模型口头「可以合并」写成已获 Approve；没有单独的 Approve 行就如实记录。不要购买额度。不要 push，不要开 PR。

- [ ] **Step 2: 打包证据并停手**

打包 baseline / red / green / gates / browser / 审查原文、HEAD、porcelain、两份 commit 与最终 diff。不 merge、不部署。把包交 Yuri 验收。第 3 刀文档不写。
