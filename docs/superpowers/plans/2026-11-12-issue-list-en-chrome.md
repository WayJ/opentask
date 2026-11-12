# 问题列表英文铬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. 步骤使用 checkbox。获批前不执行。执行时从精确 PR12 tip `18a63574c4b40baf48e7990160be5516e075b89e` 开新的隔离普通检出（`.git` 为目录，不是 worktree），新建分支，不改 PR12 实施克隆，不改 PR6–11，不 amend / 不 rebase 已验 SHA。

**Goal:** 把问题列表页仍写死的中文铬（页签、工具条、列标题、「详情 / 删除」，以及同文件里的提示文案）改成 `$t('page.issueList.*')`，英文下显示已锁定的英文，中文用词保持不变。

**Architecture:** 新键集中在 `page.issueList`，两份 locale 与 `App.I18n.Schema` 同步。单元格继续走现有 `useLabelTable`。分组下拉的内建项只在本页映射，不改 `groupIssuesBy.ts`。已有 `surface.test.ts` 对中文「详情 / 删除 / 确认删除」的冻结必须改成冻结 `$t` 键，另增键完整性测试。

**Tech Stack:** Vue 3.5、vue-i18n、Vitest 4、已有 `$t` / `App.I18n.Schema`。

## Global Constraints

- 获批前不建分支、不 commit、不改产品。获批后的起点只允许 `18a63574c4b40baf48e7990160be5516e075b89e`。
- 白名单恰好这些路径：`docs/superpowers/specs/2026-11-12-issue-list-en-chrome-design.md`、`docs/superpowers/plans/2026-11-12-issue-list-en-chrome.md`、`frontend/src/locales/langs/zh-cn.ts`、`frontend/src/locales/langs/en-us.ts`、`frontend/src/typings/app.d.ts`、`frontend/src/views/issue/list/index.vue`、`frontend/src/views/issue/list/surface.test.ts`、`frontend/src/locales/__tests__/issue-list-chrome.test.ts`。出现白名单以外的已跟踪改动就停止。
- 首个 commit 只有两份文档。产品文件在 RED 原件落盘之后才改。
- 不准改 `frontend/src/utils/groupIssuesBy.ts`、`frontend/src/constants/issue.ts`、`IssueBoard.vue`、`DisplayOptionsPanel.vue`、`IssueListGrouped.vue`、`IssueBulkBar`、详情页焦点 CSS、PR6–11 头。
- 中英文案必须与已批 design 第 3 节锁定表逐字一致，不得另撰。英文里的弯引号（如 `Couldn’t`、`“{title}”`）也必须逐字相同。`tabs.open` 英文是 Active，不是 Open。删除行按钮和删除框取消/确认按钮分别复用 `common.delete` 与 `common.cancel`。不复用 `common.confirmDelete`、`common.deleteSuccess`、`common.index`。
- 枚举值不动。已翻译的 `page.shell.*` 页头、搜索框、空态和单元格 label table 不重做。
- 390 宽首屏只看到编号/标题列不单独立项，不把未量的 `scrollWidth` 当失败。不测焦点环，不量对比度。
- 每个 RED 与 GREEN 在改下一步之前把原件写入仓库外目录：HEAD、porcelain、test blob、diff、COMMAND、CWD、TZ、stdout、stderr、EXIT。
- 四门使用下列命令：`pnpm exec vitest run`、`pnpm exec vite build --mode prod`（仓库外 `--config` 与 `cacheDir`，CWD 为新检出 `frontend/`）、`pnpm exec vue-tsc --noEmit --skipLibCheck`、`pnpm exec eslint .`。不用 `pnpm run lint`，不用 `eslint --fix`，不用 `vite --mode test`。禁止 unshare 空挂 `.vite`。`.env.prod` 只允许从 PR11 克隆或主仓拷贝（sha256 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`，1896 字节），禁止手写/入库/在报告里写 env 正文或键值。`loadEnv('prod')` 只记前缀是否非空及长度。若生成文件被清空，STOP，不要自行轮循还原。
- baseline 是获批后在干净 `18a63574` 上当次跑出的四门禁原文。不得用 PR12 记录过的 87/519、tsc 29、lint 872 代替。vue-tsc 与 eslint 对照这一次 baseline 的诊断原文，行号可以漂。baseline 非 0 就保持非 0，不报成全绿。新增诊断则停止。
- 钩子按既有限制：不改 hooksPath、不改校验源码、不用 `SKIP` / `--no-verify`、不再做 hook 路径实验。若新检出按仓库既有方式装上 hooks，只允许删除本检出的 `.git/hooks/pre-commit`，必须保留已装 `commit-msg`。在仓库根目录做正常 `git commit`，不要在 `frontend/` 里提交。没有当次 hook 打开路径原件，不得把 EXIT 0 写成已校验本检出这份说明。若再遇 `frontend/.git/COMMIT_EDITMSG` 或同类 ENOENT，立即停交原文，不二次重试，不改校验。
- 新检出不得写入或 reset 主仓 `/agent/repos/opentask`、pin `/tmp/cursor/opentask-list-pin`、旧树 `/tmp/cursor/opentask-detail-focus`、PR11 `/tmp/cursor/opentask-detail-clone`、实施克隆 `/tmp/cursor/opentask-generic-focus-clone`、只读盘点 `/tmp/cursor/opentask-post-pr12-inventory`。9541 pid 59419 与 9544 上若仍在的 pid 63047 都不要动。不 fetch / 不 push 任何 remote（origin 可能是本地路径）。
- 计划结束于浏览器核对原件和两份独立 Grok 原文落盘。不 push，不开 PR，不 merge，不 deploy。停下来等 Yuri 验收。第 2、第 3 刀不得在本计划内开写。

---

### Task 0: 隔离检出、基线、文档提交

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-issue-list-en-chrome-design.md`
- Create: `docs/superpowers/plans/2026-11-12-issue-list-en-chrome.md`

**Interfaces:**
- Consumes: 已验提交 `18a63574c4b40baf48e7990160be5516e075b89e`，已批 design 的 sha256（以获批时 `/workspace/designs/issue-list-en-chrome-spec/2026-11-12-issue-list-en-chrome-design.md` 为准，拷入仓库时不得改写正文）
- Produces: 新隔离分支上的文档提交，以及 `/tmp/cursor/opentask-readonly/issue-list-en-chrome-logs/baseline/` 里的四门禁原件

- [ ] **Step 1: 只在获批后开普通隔离检出**

先核实施克隆与盘点检出仍是 `18a63574c4b40baf48e7990160be5516e075b89e`、porcelain 为空，然后：

```bash
git clone /tmp/cursor/opentask-generic-focus-clone /tmp/cursor/opentask-issue-list-en-chrome-clone
git -C /tmp/cursor/opentask-issue-list-en-chrome-clone switch --detach 18a63574c4b40baf48e7990160be5516e075b89e
git -C /tmp/cursor/opentask-issue-list-en-chrome-clone switch -c cursor/issue-list-en-chrome-4333
```

`git rev-parse HEAD` 必须打印 `18a63574c4b40baf48e7990160be5516e075b89e`。`git status --porcelain` 必须为空。`.git` 必须是目录。随后再核：实施克隆、盘点检出、PR11 克隆、MAIN、PIN、OLD 的 HEAD 与主仓 config / `node_modules/.vite` mtime 未变。

给新检出的 `frontend/node_modules` 做指向 `/agent/repos/opentask/frontend/node_modules` 的符号链接。不安装新依赖。后面启动 Vite 必须使用仓库外 `--config`，把 `cacheDir` 写到 `/tmp/cursor/opentask-readonly/issue-list-en-chrome-logs/vite-cache`，端口不得占用 9541 或 9544。本计划内一律不 fetch、不 push。钩子按 Global Constraints 处理。

- [ ] **Step 2: 在干净 18a63574 上保存当次四门禁**

CWD 是 `/tmp/cursor/opentask-issue-list-en-chrome-clone/frontend`。先按 Global Constraints 准备 `.env.prod` 并确认 `VITE_ICON_LOCAL_PREFIX` 非空后再跑 build。四条命令分开跑，各写 `stdout.txt`、`stderr.txt` 和 `meta.txt`。

```bash
pnpm exec vitest run
pnpm exec vite build --mode prod --config /tmp/cursor/opentask-readonly/issue-list-en-chrome-logs/vite.readonly.config.mjs
pnpm exec vue-tsc --noEmit --skipLibCheck
pnpm exec eslint .
```

这四份输出就是本切片 baseline。把 vue-tsc 与 eslint 的每一行诊断原文留下。

- [ ] **Step 3: 只提交两份文档**

把已批 design 与本 plan 拷入上面两个路径。不要改写已批 design 正文。`git add` 之后 `git diff --cached --name-only` 恰好是这两行。在仓库根目录执行：

```bash
git commit -m "docs: specify issue list English chrome"
```

提交后 `git status --porcelain` 为空，`git rev-parse HEAD^` 是 `18a63574c4b40baf48e7990160be5516e075b89e`。钩子若失败，按 Global Constraints 停交原文。

---

### Task 1: RED

**Files:**
- Modify: `frontend/src/views/issue/list/surface.test.ts`
- Create: `frontend/src/locales/__tests__/issue-list-chrome.test.ts`

**Interfaces:**
- Consumes: `18a63574` 上 `index.vue` 仍写死「详情」「删除」「确认删除」等中文，且尚无 `page.issueList`
- Produces: 失败断言指向这些中文冻结和新键缺失。`column-layout.test.ts` 与 `residual-copy.test.ts` 不得改，RED 时它们仍通过

- [ ] **Step 1: 先只改测试，不改 locale、`app.d.ts` 或 `index.vue`**

把 `surface.test.ts` 写成：

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { describe, expect, it } from 'vitest';

describe('issue list surface', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/views/issue/list/index.vue'), 'utf8');

  it('loads the local sheet without changing the list contract', () => {
    expect(source).toContain("import '@/styles/issue-surface.css';");
    expect(source).toContain("$t('page.issueList.actions.view')");
    expect(source).toContain("$t('common.delete')");
    expect(source).toContain("$t('page.issueList.messages.deleteTitle')");
    expect(source).toContain("$t('page.issueList.messages.deleteConfirmContent'");
    expect(source).toContain("$t('common.cancel')");
    expect(source).toContain("$t('page.issueList.messages.deleteSuccess')");
    expect(source).toContain('white-space: normal');
    expect(source).toContain('max-height: none');
    expect(source).toContain('scroll-x="1400"');
    expect(source).toContain('page.shell.noIssues');
    expect(source).toContain('page.shell.createIssue');
    expect(source).not.toContain('line-clamp');
    expect(source).not.toContain("default: () => '详情'");
    expect(source).not.toContain("default: () => '删除'");
    expect(source).not.toContain("title: '确认删除'");
  });
});
```

新建 `frontend/src/locales/__tests__/issue-list-chrome.test.ts`，断言 `zh.page.issueList`、`en.page.issueList` 与 `frontend/src/typings/app.d.ts` 里 `page.issueList` 的 Schema 三者键集合相同，并抽查锁定值（含 `tabs.open` 英文为 Active，不是 Open）：

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import en from '../langs/en-us';
import zh from '../langs/zh-cn';

function keysOf(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object') return [prefix];
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) =>
    keysOf(child, prefix ? `${prefix}.${key}` : key)
  );
}

function schemaKeysOfIssueList(source: string): string[] {
  const match = /(?:^|[\n\r;{])\s*issueList\s*:/.exec(source);
  if (!match) return [];
  const start = source.indexOf('{', match.index + match[0].length);
  if (start < 0) return [];

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

  return parseObject(start, '').keys;
}

describe('issue list chrome copy', () => {
  it('keeps locked Chinese and English list chrome', () => {
    expect(zh.page.issueList.tabs.myTodos).toBe('我的待办');
    expect(en.page.issueList.tabs.myTodos).toBe('My to-dos');
    expect(zh.page.issueList.tabs.open).toBe('开放中');
    expect(en.page.issueList.tabs.open).toBe('Active');
    expect(en.page.issueList.tabs.open).not.toBe('Open');
    expect(zh.page.issueList.actions.view).toBe('详情');
    expect(en.page.issueList.actions.view).toBe('View');
    expect(zh.page.issueList.columns.key).toBe('编号');
    expect(en.page.issueList.columns.key).toBe('Key');
    expect(zh.page.issueList.groupBy.none).toBe('不分组');
    expect(en.page.issueList.groupBy.none).toBe('No grouping');
    expect(zh.page.issueList.messages.deleteConfirmContent).toBe('确定要删除问题 "{title}" 吗？');
    expect(en.page.issueList.messages.deleteConfirmContent).toBe('Delete issue “{title}”?');
    expect(keysOf(zh.page.issueList).sort()).toEqual(keysOf(en.page.issueList).sort());
    const typings = readFileSync(resolve(process.cwd(), 'src/typings/app.d.ts'), 'utf8');
    expect(schemaKeysOfIssueList(typings).sort()).toEqual(keysOf(zh.page.issueList).sort());
    expect(en.page.issueList.tabs.myTodos).not.toBe(zh.page.issueList.tabs.myTodos);
    expect(en.page.issueList.actions.view).not.toBe(zh.page.issueList.actions.view);
  });

  it('wires the list page to the new keys and leaves groupIssuesBy alone', () => {
    const list = readFileSync(resolve(process.cwd(), 'src/views/issue/list/index.vue'), 'utf8');
    const groupBy = readFileSync(resolve(process.cwd(), 'src/utils/groupIssuesBy.ts'), 'utf8');
    expect(list).toContain("$t('page.issueList.tabs.myTodos')");
    expect(list).toContain("$t('page.issueList.toolbar.saveView')");
    expect(list).toContain("$t('page.issueList.columns.title')");
    expect(list).toContain("$t('page.issueList.filters.reset')");
    expect(list).toContain('page.issueList.groupBy.');
    expect(list).not.toContain('<span class="tab-label">我的待办</span>');
    expect(list).not.toContain("title: '编号'");
    expect(list).toContain("$t('page.issueList.columns.key')");
    expect(list).not.toContain("label: '创建时间'");
    expect(groupBy).toContain("label: '不分组'");
    expect(groupBy).toContain("label: '状态'");
  });
});
```

- [ ] **Step 2: 跑测试，确认 RED**

CWD `frontend/`：

```bash
pnpm exec vitest run src/views/issue/list/surface.test.ts src/locales/__tests__/issue-list-chrome.test.ts src/views/issue/list/column-layout.test.ts src/locales/__tests__/residual-copy.test.ts
```

预期：`surface.test.ts` 与 `issue-list-chrome.test.ts` 失败（找不到 `$t('page.issueList...')` / `page.issueList`），`column-layout.test.ts` 与 `residual-copy.test.ts` 通过。把 stdout / stderr / EXIT 写入 `.../logs/red/`。不要在这一步改产品文件。

---

### Task 2: GREEN

**Files:**
- Modify: `frontend/src/locales/langs/zh-cn.ts`
- Modify: `frontend/src/locales/langs/en-us.ts`
- Modify: `frontend/src/typings/app.d.ts`
- Modify: `frontend/src/views/issue/list/index.vue`

**Interfaces:**
- Consumes: Task 1 的失败测试和已批 design 锁定文案
- Produces: 上述测试通过；`groupIssuesBy.ts` 正文不变

- [ ] **Step 1: 写入 locale 与 Schema**

在 `zh-cn.ts` 与 `en-us.ts` 的 `page` 对象中，紧挨 `shell` 之后（或 `issueType` 之前）插入 `issueList`。中文必须是：

```ts
      issueList: {
        tabs: {
          myTodos: '我的待办',
          open: '开放中',
          closed: '已关闭',
          all: '全部'
        },
        toolbar: {
          views: '视图',
          saveView: '保存视图',
          saveViewHint: '将当前筛选保存为个人或共享视图',
          star: '星标',
          starHint: '星标视图（列表顶栏 chips，≠ 侧栏收藏）',
          pinToSidebar: '收藏到侧栏',
          unpinFromSidebar: '取消侧栏',
          pinToSidebarHint: '固定到左侧边栏 Favorites（独立于星标）',
          saveAs: '另存为',
          saveAsHint: '复制为个人视图（共享只读成员可用）',
          filters: '筛选',
          collapseFilters: '收起筛选面板',
          expandFilters: '展开筛选面板',
          syntaxHelp: '语法帮助',
          syntaxHelpHint: '查看搜索语法帮助',
          display: '显示',
          sort: '排序',
          group: '分组'
        },
        sortBy: {
          createdAt: '创建时间',
          updatedAt: '更新时间',
          priority: '优先级',
          status: '状态',
          title: '标题',
          dueDate: '截止日期'
        },
        sortOrder: {
          desc: '降序',
          asc: '升序'
        },
        groupBy: {
          none: '不分组',
          status: '状态',
          assignee: '负责人',
          priority: '优先级',
          type: '类型',
          label: '标签'
        },
        computedFieldSuffix: '（计算值）',
        computedFieldSuffixReadonly: '（计算值·只读）',
        columns: {
          key: '编号',
          title: '标题',
          type: '类型',
          status: '状态',
          priority: '优先级',
          estimate: '估点',
          assignee: '负责人',
          reporter: '报告人',
          createdAt: '创建时间',
          actions: '操作'
        },
        actions: {
          view: '详情',
          systemReporter: '系统'
        },
        filters: {
          project: '项目',
          cycle: '冲刺',
          type: '类型',
          priority: '优先级',
          reset: '重置筛选'
        },
        syntax: {
          title: '搜索语法帮助',
          tipPrefix: '提示：可以组合使用多个过滤器，如',
          assigneeMe: '显示分配给我的问题',
          isOpen: '只显示待办中的问题',
          isClosed: '只显示已完成的问题',
          isInProgress: '只显示进行中的问题',
          typeFeature: '只显示功能类型的问题',
          typeBug: '只显示缺陷类型的问题',
          priorityUrgent: '只显示紧急优先级的问题',
          priorityHigh: '只显示高优先级的问题',
          customField: '按自定义字段过滤（亦可用 cf:key:value）'
        },
        views: {
          currentPrefix: '当前视图：',
          favoriteViews: '收藏视图',
          savePersonalTitle: '保存为个人视图',
          saveSharedTitle: '保存为共享视图',
          save: '保存',
          namePlaceholder: '视图名称，例如：我的高优缺陷',
          shareWithWorkspace: '共享给工作区'
        },
        scopeTitle: {
          watching: '我关注的',
          dueSoon: '即将到期',
          assignedToMe: '指派给我',
          createdByMe: '我创建的'
        },
        import: {
          downloadTemplate: '下载模板 CSV',
          helpBefore: '列需含 title；可选 issue_code（本工作区已存在则更新）。自定义字段用',
          helpAfter: '列（模板已含当前工作区字段；multi 逗号分隔，boolean 用 true/false）。未知 key 不阻断主字段写入。'
        },
        messages: {
          enterViewName: '请输入视图名称',
          viewSaved: '视图已保存',
          sharedViewSaved: '共享视图已保存',
          saveViewFailed: '保存视图失败',
          viewApplied: '已应用视图「{name}」',
          viewNotFound: '未找到该视图',
          applyViewFirst: '请先应用一个已保存视图',
          sharedViewCantStar: '共享视图不支持收藏，可另存为个人视图后再收藏',
          starred: '已收藏',
          unstarred: '已取消收藏',
          updateStarFailed: '更新收藏失败',
          pinnedToSidebar: '已收藏到侧栏',
          unpinnedFromSidebar: '已从侧栏移除',
          updateSidebarPinFailed: '更新侧栏收藏失败',
          savedAsPersonal: '已另存为个人视图',
          saveAsFailed: '另存为失败',
          copySuffix: '（副本）',
          deleteTitle: '确认删除',
          deleteConfirmContent: '确定要删除问题 "{title}" 吗？',
          deleteSuccess: '问题删除成功',
          deleteFailed: '问题删除失败',
          personalDefaultSaved: '已设为个人默认显示',
          personalDefaultFailed: '保存个人默认失败',
          groupCfUnsupported: '该自定义字段类型不支持分组，已回退为不分组',
          savedGroupCfUnsupported: '已保存的分组自定义字段类型不受支持，已回退为不分组',
          swimlaneCfUnsupported: '该自定义字段类型不支持泳道，已回退为无泳道',
          savedSwimlaneCfUnsupported: '已保存的泳道自定义字段类型不受支持，已回退为无泳道',
          groupSyncFailed: '分组已切换，但同步到已保存视图失败',
          exportedCsv: '已导出 CSV',
          exportFailed: '导出失败',
          templateDownloadFailed: '模板下载失败',
          importFailed: '导入失败',
          noneCycle: '无 Cycle'
        },
        blockedBy: '被阻塞 {count}',
        blocks: '阻塞 {count}'
      },
```

英文必须是：

```ts
      issueList: {
        tabs: {
          myTodos: 'My to-dos',
          open: 'Active',
          closed: 'Closed',
          all: 'All'
        },
        toolbar: {
          views: 'Views',
          saveView: 'Save view',
          saveViewHint: 'Save the current filters as a personal or shared view',
          star: 'Star',
          starHint: 'Star a view (chips on the list toolbar, not the sidebar)',
          pinToSidebar: 'Pin to sidebar',
          unpinFromSidebar: 'Unpin from sidebar',
          pinToSidebarHint: 'Pin to the sidebar favorites (separate from starring)',
          saveAs: 'Save as',
          saveAsHint: 'Duplicate as a personal view (for read-only members of a shared view)',
          filters: 'Filters',
          collapseFilters: 'Collapse filters',
          expandFilters: 'Expand filters',
          syntaxHelp: 'Syntax help',
          syntaxHelpHint: 'View search syntax help',
          display: 'Display',
          sort: 'Sort',
          group: 'Group'
        },
        sortBy: {
          createdAt: 'Created',
          updatedAt: 'Updated',
          priority: 'Priority',
          status: 'Status',
          title: 'Title',
          dueDate: 'Due date'
        },
        sortOrder: {
          desc: 'Descending',
          asc: 'Ascending'
        },
        groupBy: {
          none: 'No grouping',
          status: 'Status',
          assignee: 'Assignee',
          priority: 'Priority',
          type: 'Type',
          label: 'Label'
        },
        computedFieldSuffix: '(computed)',
        computedFieldSuffixReadonly: '(computed, read-only)',
        columns: {
          key: 'Key',
          title: 'Title',
          type: 'Type',
          status: 'Status',
          priority: 'Priority',
          estimate: 'Estimate',
          assignee: 'Assignee',
          reporter: 'Reporter',
          createdAt: 'Created',
          actions: 'Actions'
        },
        actions: {
          view: 'View',
          systemReporter: 'System'
        },
        filters: {
          project: 'Project',
          cycle: 'Cycle',
          type: 'Type',
          priority: 'Priority',
          reset: 'Reset filters'
        },
        syntax: {
          title: 'Search syntax help',
          tipPrefix: 'Tip: you can combine filters, for example',
          assigneeMe: 'Show issues assigned to me',
          isOpen: 'Show only open issues',
          isClosed: 'Show only completed issues',
          isInProgress: 'Show only in-progress issues',
          typeFeature: 'Show only feature issues',
          typeBug: 'Show only bug issues',
          priorityUrgent: 'Show only urgent-priority issues',
          priorityHigh: 'Show only high-priority issues',
          customField: 'Filter by a custom field (cf:key:value also works)'
        },
        views: {
          currentPrefix: 'Current view:',
          favoriteViews: 'Starred views',
          savePersonalTitle: 'Save as personal view',
          saveSharedTitle: 'Save as shared view',
          save: 'Save',
          namePlaceholder: 'View name, e.g. My high-priority bugs',
          shareWithWorkspace: 'Share with the workspace'
        },
        scopeTitle: {
          watching: 'Watching',
          dueSoon: 'Due soon',
          assignedToMe: 'Assigned to me',
          createdByMe: 'Created by me'
        },
        import: {
          downloadTemplate: 'Download template CSV',
          helpBefore: 'Columns must include title; optional issue_code (updates when it already exists in this workspace). Custom fields use',
          helpAfter: 'columns (the template already includes this workspace’s fields; separate multi values with commas, and use true/false for booleans). Unknown keys do not block writing the main fields.'
        },
        messages: {
          enterViewName: 'Enter a view name',
          viewSaved: 'View saved',
          sharedViewSaved: 'Shared view saved',
          saveViewFailed: 'Couldn’t save the view',
          viewApplied: 'Applied view “{name}”',
          viewNotFound: 'View not found',
          applyViewFirst: 'Apply a saved view first',
          sharedViewCantStar: 'Shared views can’t be starred. Save as a personal view first',
          starred: 'Starred',
          unstarred: 'Star removed',
          updateStarFailed: 'Couldn’t update the star',
          pinnedToSidebar: 'Pinned to the sidebar',
          unpinnedFromSidebar: 'Unpinned from the sidebar',
          updateSidebarPinFailed: 'Couldn’t update the sidebar pin',
          savedAsPersonal: 'Saved as a personal view',
          saveAsFailed: 'Couldn’t save a copy',
          copySuffix: '(copy)',
          deleteTitle: 'Delete issue',
          deleteConfirmContent: 'Delete issue “{title}”?',
          deleteSuccess: 'Issue deleted',
          deleteFailed: 'Couldn’t delete the issue',
          personalDefaultSaved: 'Saved as your personal default',
          personalDefaultFailed: 'Couldn’t save the personal default',
          groupCfUnsupported: 'This custom field type can’t be used for grouping, so grouping was cleared',
          savedGroupCfUnsupported: 'The saved grouping field type isn’t supported, so grouping was cleared',
          swimlaneCfUnsupported: 'This custom field type can’t be used for swimlanes, so swimlanes were cleared',
          savedSwimlaneCfUnsupported: 'The saved swimlane field type isn’t supported, so swimlanes were cleared',
          groupSyncFailed: 'Grouping changed, but saving it to the view failed',
          exportedCsv: 'Exported CSV',
          exportFailed: 'Couldn’t export',
          templateDownloadFailed: 'Couldn’t download the template',
          importFailed: 'Couldn’t import',
          noneCycle: 'No cycle'
        },
        blockedBy: 'Blocked by {count}',
        blocks: 'Blocks {count}'
      },
```

导入说明必须保留模板里的 `<code>cf.&lt;key&gt;</code>`，分别绑定 `import.helpBefore` 与 `import.helpAfter`，不要合成一句而丢掉这段代码。在 `app.d.ts` 的 `page` 中、`shell` 与 `issueType` 之间插入：

```ts
        issueList: {
          tabs: { myTodos: string; open: string; closed: string; all: string };
          toolbar: {
            views: string; saveView: string; saveViewHint: string; star: string; starHint: string;
            pinToSidebar: string; unpinFromSidebar: string; pinToSidebarHint: string;
            saveAs: string; saveAsHint: string; filters: string; collapseFilters: string; expandFilters: string;
            syntaxHelp: string; syntaxHelpHint: string; display: string; sort: string; group: string;
          };
          sortBy: { createdAt: string; updatedAt: string; priority: string; status: string; title: string; dueDate: string };
          sortOrder: { desc: string; asc: string };
          groupBy: { none: string; status: string; assignee: string; priority: string; type: string; label: string };
          computedFieldSuffix: string;
          computedFieldSuffixReadonly: string;
          columns: {
            key: string; title: string; type: string; status: string; priority: string;
            estimate: string; assignee: string; reporter: string; createdAt: string; actions: string;
          };
          actions: { view: string; systemReporter: string };
          filters: { project: string; cycle: string; type: string; priority: string; reset: string };
          syntax: {
            title: string; tipPrefix: string; assigneeMe: string; isOpen: string; isClosed: string;
            isInProgress: string; typeFeature: string; typeBug: string; priorityUrgent: string;
            priorityHigh: string; customField: string;
          };
          views: {
            currentPrefix: string; favoriteViews: string; savePersonalTitle: string; saveSharedTitle: string;
            save: string; namePlaceholder: string; shareWithWorkspace: string;
          };
          scopeTitle: { watching: string; dueSoon: string; assignedToMe: string; createdByMe: string };
          import: { downloadTemplate: string; helpBefore: string; helpAfter: string };
          messages: {
            enterViewName: string; viewSaved: string; sharedViewSaved: string; saveViewFailed: string;
            viewApplied: string; viewNotFound: string; applyViewFirst: string; sharedViewCantStar: string;
            starred: string; unstarred: string; updateStarFailed: string;
            pinnedToSidebar: string; unpinnedFromSidebar: string; updateSidebarPinFailed: string;
            savedAsPersonal: string; saveAsFailed: string; copySuffix: string;
            deleteTitle: string; deleteConfirmContent: string; deleteSuccess: string; deleteFailed: string;
            personalDefaultSaved: string; personalDefaultFailed: string;
            groupCfUnsupported: string; savedGroupCfUnsupported: string;
            swimlaneCfUnsupported: string; savedSwimlaneCfUnsupported: string; groupSyncFailed: string;
            exportedCsv: string; exportFailed: string; templateDownloadFailed: string; importFailed: string;
            noneCycle: string;
          };
          blockedBy: string;
          blocks: string;
        };
```

三处键形状必须一致。

- [ ] **Step 2: 改 `index.vue`，只换用户可见写死文案**

用已有的 `$t`。不要改筛选/单元格的 `useLabelTable` 逻辑，不要改 `scroll-x`、标题换行样式或列宽计算。

要点（按已批 design，不要另写英文）：

- 页签四个 `tab-label` 改为 `$t('page.issueList.tabs.*')`。
- 工具条按钮和 `NTooltip` 说明改为对应 `toolbar.*`；筛选展开/收起用 `expandFilters` / `collapseFilters`。
- `sortByOptions` 的六个内建 `label` 改为 `$t('page.issueList.sortBy.*')`；公式后缀用 `computedFieldSuffix`。`listSortOrder` 选项改为 `sortOrder.desc` / `asc`。
- `groupByOptions`：对 `buildGroupByOptions(...)` 的结果做映射，仅当 `value` 是 `none|status|assignee|priority|type|label` 时换成 `$t('page.issueList.groupBy.' + value)`，其它 label 保持字段名。若 label 以「（计算值·只读）」结尾，只把这段后缀换成 `$t('page.issueList.computedFieldSuffixReadonly')`，不要改成「（计算值）」。**不要改 `groupIssuesBy.ts`。** 排序 extras 里的「（计算值）」用 `computedFieldSuffix`。
- 这些 computed 必须读取 `getLocale()` 或 `i18n.global.locale.value`，以便切语言时更新。
- 列 `title` 和「详情」改为 `columns.*` / `actions.view`；删除按钮用 `common.delete`。报告人「系统」用 `actions.systemReporter`。
- 筛选占位和「重置筛选」、语法帮助面板与 `syntaxExamples`、`收藏视图`、`当前视图：`、范围标题、保存视图弹窗、删除确认与全部同文件 toast / 警告，按 design 第 3.4–3.5 节换成 `$t`。删除确认内容传 `{ title: issue.title }`。另存为名称后缀用 `messages.copySuffix`。
- 「无 Cycle」改 `messages.noneCycle`。「被阻塞 / 阻塞」改 `blockedBy` / `blocks`，传入 `count`。
- 不要翻译或删除源码注释里的中文。

- [ ] **Step 3: 跑测试，确认 GREEN**

同一条 vitest 命令。预期上述四个文件全部通过。把原件写入 `.../logs/green/`。`git diff -- src/utils/groupIssuesBy.ts` 必须为空。

- [ ] **Step 4: 产品提交**

`git add` 白名单内的 locale、`app.d.ts`、`index.vue`、两份测试。`git diff --cached --name-only` 不得出现其它已跟踪路径。在仓库根目录：

```bash
git commit -m "fix: localize issue list chrome for English"
```

提交后 porcelain 为空。钩子失败则停交原文。

---

### Task 3: 浏览器核对

**Files:** 无产品文件。原件写入 `/tmp/cursor/opentask-readonly/issue-list-en-chrome-logs/browser/`。

- [ ] **Step 1: 在新检出起只读 Vite**

端口不得使用 9541 / 9544。仓库外 config 与 cacheDir，CWD 为新检出 `frontend/`。准备 `.env.prod` 的规则同 Global Constraints。只停自己起的进程。

- [ ] **Step 2: 按 design 第 4 节取样**

`/issue/list`：`en-US` 浅色 1280×800、`en-US` 深色 1280×800（点击主题后不重新加载，记下 `htmlClass` / `html.dark` / `prefers`）、`en-US` 390×844、`zh-CN` 浅色 1280×800。保存截图、文档标题、可见页签/工具条/列标题/行按钮文案，以及单元格仍是 Bug / Open / Medium（英文）或对应中文。不得出现原始 key。英文页签「开放中」必须是 Active，不能是 Open；状态徽章仍可以是 Open。390 首屏只需确认已露出的「Key / Title」或「编号 / 标题」，不要为了其余列去滚动或改视口。

若英文页签或「View / Delete」仍是中文，STOP 交证，不要把范围扩到其它文件。

---

### Task 4: 同 SHA 四门对照

在产品提交的干净 SHA、porcelain 为空时重跑 Task 0 的四条命令，写入 `.../logs/final/`，与当次 baseline 对照。vue-tsc / eslint 去掉行号后不得新增诊断。vitest 与 build 的退出码不得比 baseline 更差。对照原件留下。

---

### Task 5: 双 Grok 与停手

对同一干净 SHA 发两份互不重复的 grok-4.7-high 审查（spec 对照已批 design；code 对照 diff / 测试 / 未改 `groupIssuesBy.ts`）。把完整原文落入 `.../logs/reviews/`，记录 agent id 与起止时间。不要把「非空」写成 Approve，除非原文有单独的 Approve 行。审查不得改代码。然后停手：不 push，不开 PR，不 merge，不部署，不开始第 2 / 第 3 刀。把包打成 `/opt/cursor/artifacts/issue-list-en-chrome-verify.tar.gz` 并记录 sha256，交 Yuri 验收。
