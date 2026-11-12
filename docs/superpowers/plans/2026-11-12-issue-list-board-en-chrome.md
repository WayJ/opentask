# 问题列表看板英文铬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把问题列表页上仍写死的看板、显示选项、批量条和搜索建议铬接到 zh/en，不改分组相等比较、公式后缀源串、工具栏已有 `$t`，也不改创建/编辑或壳层。

**Architecture:** 在已有 `page.issueList` 下新增 `board`、`displayOptions`、`bulk`、`search`、`searchSuggestions` 分组，并同步 `App.I18n.Schema`。组件继续用 `@/locales` 的 `$t`。已有整句优先复用。卡片优先级与批量条 options 走 `useLabelTable` / `lookupLabel`。显示选项在组件内覆盖常量表与公式后缀。`generateSearchSuggestions` 只译横线后说明。决定 E/F 按 design 推荐案实施。

**Tech Stack:** Vue 3、vue-i18n、Naive UI、Vitest、Vue Test Utils、已有 `$t` 与 `App.I18n.Schema`，无新依赖。

## Global Constraints

- 本轮只交本地草稿。获批口令为「design ok，开写」。决定 E/F 未确认前不得实施。本计划按 design 推荐案写；否决任一条，先改 design 与本 plan，再执行。
- 精确 base：`6b6ad3b4784fd65ce917c42fb3ec978c10e4b557`（PR17 tip）。`starting_ref` / 检出必须是 `6b6ad3b4`。不要用 `290c3ed3` 当实施 base。不改写 PR6–17 已存提交或头。
- 后续仅普通隔离 clone（`.git` 为目录），不用 worktree。不写/reset MAIN `244c93e296a047cf138a880fa24d683b4be8203d` 或 PIN `250fc34af9c64e828aab706567b0430d3d74e452`。不碰已有 pid 服务。不回复会绑到 PR13–PR17 头的既有 CloudAgent。
- 不买额度，不 merge，不部署。未经再授权不 push、不开 PR。本轮不建产品分支、不改产品、不 TDD、不 commit。获批后才按本 plan 实施。
- 英文页内铬 sentence case。新键进入 `App.I18n.Schema`。页面与组件用 `$t`。不要把已有 `$t` 改成局部 `t()`。不要改 `constants/issue.ts`。
- 脚本里调用 `$t` 的 computed，以及会缓存文案的函数，第一句必须是 `void locale.value;`，位于任何短路之前。`no-void` 只用 `eslint-disable-next-line` 盖住这一句，或紧贴该 computed / 函数的 disable/enable 块。禁止文件级 `eslint-disable no-void`。
- 命名参数插值必须写成 `$t('…', { n: … })` 或 `$t('…', { count: … })`（与已有键签名一致），禁止 `.replace('{n}', …)`、`.replace('{count}', …)` 或同类字符串替换迁就测试。
- 测试统计 `$t('…')` 调用点。字面缺失用正则。禁止 `not.toContain('取消')`、`('状态')`、`('重置')`、`('应用')`、`('标题')`、`('编辑')`。
- Vue Test Utils stub 同时覆盖 naive-ui 真实 name 与 `N*` 别名。不为测试修改产品组件的 `name` 或 `defineOptions`。有 `useI18n()` 的挂载必须带 `plugins: [i18n]`（已有 pinia 则 `[pinia, i18n]`），不要删 `useI18n`。`IssueSmartSearch` 优先继续用从 `@/locales` 导入的 `$t` / `locale`，不要无故改成 `useI18n()`。
- 四门从 `frontend/` 跑：`pnpm exec vitest run`、`pnpm exec vite build --mode prod`（仓库外 config）、`pnpm exec vue-tsc --noEmit --skipLibCheck`、`pnpm exec eslint .`。对照当次干净 `6b6ad3b4` baseline。tsc/eslint 基线非 0 则保持 added 0 / removed 0，不得写成全绿，不得借用 PR15/PR16/PR17 的失败行号。不能写 dual Grok Approve。Vite 只读 config 的 server port 用 `9573`，`strictPort: true`，`open: false`（不要沿用旧片的 9571 / 9572）。
- 两笔提交：第一笔仅两份 docs，信息恰好 `docs: specify issue list board English chrome`；第二笔是 RED 测试与最小 GREEN 产品一起提交，信息恰好 `fix: localize issue list board chrome for English`。不预安排第三笔。不 amend、不 rebase、不 squash、不用 `--no-verify`。已批 docs 必须从箱上原文 `cmp` 进仓库。
- hook：只在新 clone 上处理。官方 hook 正文是 `bun sa git-commit-verify`，已核原件 sha256 `46d7a87f731e693d7d81f98f9d9c0286e070f28c8d6aa9a0f88326e8699b5a59`（234 字节），路径 `/workspace/designs/issue-composer-en-chrome-verify/official-commit-msg`。`pnpm install` 后若 simple-git-hooks 把 hook 写到 `frontend/.git/hooks/`，按第 4 刀已接受做法：把官方原件原样拷到 `$REPO/.git/hooks/commit-msg` 且可执行；只删 `frontend/.git/hooks/pre-commit` 与根目录若出现的非 sample pre-commit；不删整个 `frontend/.git`，不动那里的 commit-msg；不重跑 `simple-git-hooks`，不改 `core.hooksPath`，不用 `SKIP` / `--no-verify`，不另装 verifier。再在仓库根建 gitignore 相对软链 `ln -s frontend/node_modules node_modules`；不把软链入库，不改 `.gitignore`。只允许在仓库根 `git commit`。EXIT 0 不是 hook 路径证明，须有 strace 显示只读打开克隆根 `.git/COMMIT_EDITMSG`。若 hook 失败（含 `Script not found "sa"`）或 `COMMIT_EDITMSG` ENOENT：原件落盘后立即 STOP，不重试，不改 hook。
- 不运行 `eslint --fix`。不改 `.env.prod` 正文；实施若要 prod build，只使用 sha256 仍为 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`（1896 字节）的已核 `.env.prod` 副本。缺文件或哈希不符则该门记 EXIT STOP（与 PR17 相同限制，不是本刀开写或必修复项），不用 `.env.example` 顶替，也不因此中断 TDD 与其它门禁。不把正文或键值写进证据。
- prod build 若弄脏 `frontend/src/typings/components.d.ts`，必须从**仓库根** `git checkout -- frontend/src/typings/components.d.ts`，再跑 tsc/eslint；打包还原前后 porcelain；不提交该文件。不要只在 `frontend/` 下 checkout。
- 决定 E：不改「（计算值·只读）」源串；不改 `groupIssuesBy.ts` 的四个桶字与相等比较；卡片「未指派」走 `page.issueList.board.unassigned`，禁止复用 `page.issueForm.unassigned`；不要在组件里覆盖四个桶字。决定 F：只译建议说明；同句才复用 `syntax.isOpen` / `isClosed` / `isInProgress` / `priorityUrgent`；「指派给我」复用同句 `scopeTitle.assignedToMe`，不复用近义 `syntax.assigneeMe`。本刀不实施壳层或创建/编辑剩余句。
- 本刀不改 `views/issue/list/index.vue`、`groupIssuesBy.ts`、`groupIssuesBy.test.ts`、`display-prefs.ts`、`constants/issue.ts`、`detail/index.vue`、`MarkdownEditor.vue`、`AttachmentList`、自定义字段内部、设置页、大模块、`noneCycle` 合并、命令面板 keywords。

### 白名单（12 路径，另加有条件的第 13 项）

- `docs/superpowers/specs/2026-11-12-issue-list-board-en-chrome-design.md`
- `docs/superpowers/plans/2026-11-12-issue-list-board-en-chrome.md`
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/typings/app.d.ts`
- `frontend/src/views/issue/list/modules/IssueBoard.vue`
- `frontend/src/views/issue/list/modules/DisplayOptionsPanel.vue`
- `frontend/src/views/issue/list/modules/IssueListGrouped.vue`
- `frontend/src/components/IssueBulkBar.vue`
- `frontend/src/components/IssueSmartSearch.vue`
- `frontend/src/utils/issueSearchParser.ts`（只改 `generateSearchSuggestions`）
- `frontend/src/locales/__tests__/issue-list-board-chrome.test.ts`（新建）
- 有条件：`frontend/src/tests/issue/index.test.ts`（仅当既有挂载因缺少 i18n plugin 失败时，补 `plugins: [i18n]`，不得削弱 `:111-114` 的 token 断言；能不改就不改，不改则第二笔提交不得出现该路径）

实施前若发现上列产品路径在 `6b6ad3b4` 上不存在或主入口已改名，STOP 并改 plan，不要扩白名单到范围外文件。`display-prefs.ts`、`groupIssuesBy.ts`、`constants/issue.ts`、`views/issue/list/index.vue` 不在白名单。

---

### Task 0: 获批后隔离、当次基线、docs-only commit

**Files:** 仅上述两份 docs。**Consumes:** 精确 `6b6ad3b4784fd65ce917c42fb3ec978c10e4b557` 与已批的两份本地文件。**Produces:** 普通 clone 上的文档提交，以及仓库外 baseline 原件。

- [ ] **Step 1: 在实施环境建全新普通 clone**

下面的命令等获批后再执行。先确认目标不存在。不写/reset main `244c93e2` 或 pin `250fc34a`。不回复 PR17 的 CloudAgent。

```bash
export TZ=Asia/Shanghai
export REPO=/tmp/cursor/opentask-issue-list-board-en-chrome-clone
export EVIDENCE=/tmp/cursor/opentask-readonly/issue-list-board-en-chrome-logs
export OFFICIAL_HOOK=/workspace/designs/issue-composer-en-chrome-verify/official-commit-msg
export APPROVED_DESIGN=/workspace/designs/issue-list-board-en-chrome-spec/2026-11-12-issue-list-board-en-chrome-design.md
export APPROVED_PLAN=/workspace/designs/issue-list-board-en-chrome-spec/2026-11-12-issue-list-board-en-chrome.md
test ! -e "$REPO" || exit 1
test -f "$OFFICIAL_HOOK" || exit 1
test "$(sha256sum "$OFFICIAL_HOOK" | awk '{print $1}')" = 46d7a87f731e693d7d81f98f9d9c0286e070f28c8d6aa9a0f88326e8699b5a59 || exit 1
mkdir -p "$EVIDENCE"
git clone https://github.com/WayJ/opentask.git "$REPO"
cd "$REPO"
git switch --detach 6b6ad3b4784fd65ce917c42fb3ec978c10e4b557
test -d .git || exit 1
test "$(git rev-parse HEAD)" = 6b6ad3b4784fd65ce917c42fb3ec978c10e4b557 || exit 1
test -z "$(git status --porcelain)" || exit 1
test -z "$(git config --get core.hooksPath)" || exit 1
git switch -c cursor/issue-list-board-en-chrome-4333
cd "$REPO/frontend"
pnpm install --frozen-lockfile
cd "$REPO"
# 官方 hook 落到克隆根；不要重跑 simple-git-hooks
cp "$OFFICIAL_HOOK" .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
test "$(sha256sum .git/hooks/commit-msg | awk '{print $1}')" = 46d7a87f731e693d7d81f98f9d9c0286e070f28c8d6aa9a0f88326e8699b5a59 || exit 1
rm -f .git/hooks/pre-commit
rm -f frontend/.git/hooks/pre-commit
# 根目录 gitignore 相对软链，不入库、不改 .gitignore
ln -s frontend/node_modules node_modules
test "$(readlink node_modules)" = frontend/node_modules || exit 1
test -e node_modules/.bin/sa || exit 1
git check-ignore -v node_modules > "$EVIDENCE/node_modules.check-ignore.txt"
test -s "$EVIDENCE/node_modules.check-ignore.txt" || exit 1
# 必须写明 cwd 为仓库根
( cd "$REPO" && pwd && bun sa --help ) > "$EVIDENCE/bun-sa-help.txt" 2>&1
# .env.prod 不是开写前置。有已核副本才拷；缺失或哈希不符则不拷、不用 .env.example，prod build 记 EXIT STOP（与 PR17 相同限制），其它任务继续
if [ -n "${VERIFIED_ENV_PROD:-}" ] && [ -f "$VERIFIED_ENV_PROD" ] \
  && [ "$(wc -c < "$VERIFIED_ENV_PROD" | tr -d " ")" = 1896 ] \
  && [ "$(sha256sum "$VERIFIED_ENV_PROD" | awk '{print $1}')" = b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7 ]; then
  cp "$VERIFIED_ENV_PROD" "$REPO/frontend/.env.prod"
  test "$(sha256sum "$REPO/frontend/.env.prod" | awk '{print $1}')" = b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7 || exit 1
  git check-ignore -q frontend/.env.prod || exit 1
  printf 'env_prod_present=yes\nenv_prod_bytes=1896\nenv_prod_sha256=b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7\n' > "$EVIDENCE/env-prod.meta.txt"
else
  printf 'env_prod_present=no\nprod_build_expected=EXIT_STOP\nnote=missing_or_mismatch_verified_env_prod; do_not_use_env_example\n' > "$EVIDENCE/env-prod.meta.txt"
fi
sha256sum .git/hooks/commit-msg > "$EVIDENCE/commit-msg.sha256"
git status --porcelain > "$EVIDENCE/checkout-porcelain.txt"
test -z "$(git status --porcelain)" || exit 1
```

任一项失败即 STOP，不改 hook 正文，不另装 verifier。`.env.prod` 只从已核来源拷贝，拷贝后立刻核 sha256 仍是 `b686d37a…`（1896）。缺原件或哈希不符时不拷贝、不用 `.env.example` 顶替（即使它碰巧同一哈希），prod build 记 EXIT STOP，作为与 PR17 相同的已记录限制，不是本刀必修复项，也不阻塞后续 TDD 与其它门禁。不记录正文或键值。依赖准备好之后再确认除 gitignored `.env.prod` 外 tracked diff 为空。已有服务端口不动。Vite 只读 config 的 server port 用 `9573`，`strictPort: true`，`open: false`。

- [ ] **Step 2: 仓库外 config，先在干净 base 跑四门**

```bash
cd "$REPO/frontend"
node --input-type=module <<'JS'
import { writeFileSync } from 'node:fs';
const root = process.cwd();
const evidence = process.env.EVIDENCE;
writeFileSync(`${evidence}/vite.readonly.config.mjs`, `
import original from ${JSON.stringify(root + '/vite.config.ts')};
export default async env => {
  const resolved = typeof original === 'function' ? await original(env) : await original;
  return {
    ...resolved,
    root: ${JSON.stringify(root)},
    cacheDir: ${JSON.stringify(evidence + '/vite-cache')},
    build: { ...(resolved.build || {}), outDir: ${JSON.stringify(evidence + '/dist')} },
    server: { ...(resolved.server || {}), open: false, host: '127.0.0.1', port: 9573, strictPort: true }
  };
};
`);
JS
cat > "$EVIDENCE/run-gates.sh" <<'SH'
#!/usr/bin/env bash
set -u
phase="$1"
cd "$REPO/frontend" || exit 1
run() {
  name="$1"; shift
  dir="$EVIDENCE/$phase/$name"; mkdir -p "$dir"
  { printf 'CWD=%s\nTZ=%s\n' "$PWD" "$TZ"; printf 'COMMAND='; printf '%q ' "$@"; printf '\n'; git -C "$REPO" rev-parse HEAD; git -C "$REPO" status --porcelain; } > "$dir/meta.txt"
  "$@" > "$dir/stdout.txt" 2> "$dir/stderr.txt"
  rc=$?; printf 'EXIT=%s\n' "$rc" >> "$dir/meta.txt"
}
run vitest pnpm exec vitest run
run build pnpm exec vite build --mode prod --config "$EVIDENCE/vite.readonly.config.mjs"
# 若 build 弄脏 components.d.ts，从仓库根还原后再跑 tsc/eslint
cd "$REPO"
if ! git diff --quiet -- frontend/src/typings/components.d.ts; then
  git checkout -- frontend/src/typings/components.d.ts
fi
cd "$REPO/frontend"
run tsc pnpm exec vue-tsc --noEmit --skipLibCheck
run eslint pnpm exec eslint .
SH
chmod +x "$EVIDENCE/run-gates.sh"
bash "$EVIDENCE/run-gates.sh" baseline
```

baseline HEAD 必须仍是精确 base，tracked diff 空（还原 `components.d.ts` 之后；gitignored `.env.prod` 除外）。vitest 必须 EXIT 0 才继续。build 仅在已核 `.env.prod` 已就位时必须 EXIT 0；否则记录 EXIT STOP 为限制并继续，不得用 `.env.example` 换通。tsc / eslint 非 0 则把诊断原样留下，不修范围外问题。记录 eslint 摘要行（历史指纹是 872 problems，以当次 baseline 为准）。build 前后比较 tracked diff 和生成文件 hash。意外改动就 STOP。

- [ ] **Step 3: 文档先行，恰好两文件提交**

把已批文件逐字节放入 docs，`cmp` 前后 sha256。拿不到已批原件就 STOP，不从未批草稿复刻。只在仓库根提交。

```bash
cd "$REPO"
mkdir -p docs/superpowers/specs docs/superpowers/plans
cp "$APPROVED_DESIGN" docs/superpowers/specs/2026-11-12-issue-list-board-en-chrome-design.md
cp "$APPROVED_PLAN" docs/superpowers/plans/2026-11-12-issue-list-board-en-chrome.md
cmp "$APPROVED_DESIGN" docs/superpowers/specs/2026-11-12-issue-list-board-en-chrome-design.md
cmp "$APPROVED_PLAN" docs/superpowers/plans/2026-11-12-issue-list-board-en-chrome.md
git add docs/superpowers/specs/2026-11-12-issue-list-board-en-chrome-design.md docs/superpowers/plans/2026-11-12-issue-list-board-en-chrome.md
test "$(git diff --cached --name-only | wc -l)" = 2 || exit 1
git diff --cached --name-only | sort > "$EVIDENCE/docs-cached-paths.txt"
# 只从仓库根 commit；留下 strace
strace -f -e trace=openat,execve -o "$EVIDENCE/docs-commit.strace" git commit -m "docs: specify issue list board English chrome"
test "$(git rev-parse HEAD^)" = 6b6ad3b4784fd65ce917c42fb3ec978c10e4b557 || exit 1
test -z "$(git status --porcelain)" || exit 1
```

`git diff --cached --name-only` 必须恰好是这两个路径。hook 哈希提交后仍须是 `46d7a87f…`。strace 必须出现克隆根 `.git/COMMIT_EDITMSG` 以及 hook / `bun sa git-commit-verify`。EXIT 0 本身不够。遇到 hook 失败或 `COMMIT_EDITMSG` ENOENT 立即 STOP，不重试。

### Task 1: tests-only RED（不改产品，不另强制 RED commit）

**Files:**

- Create: `frontend/src/locales/__tests__/issue-list-board-chrome.test.ts`
- 不预先改 `tests/issue/index.test.ts`

**Consumes:** design 第 3 节键表。**Produces:** 红测；产品尚未改时必须失败。

- [ ] **Step 1: 写列表看板铬测试**

测试文件安装真实 `@/locales` i18n（`zh-CN` / `en-US`），不要自己造一套残缺 messages。模式对齐 `issue-detail-chrome.test.ts` / `issue-composer-chrome.test.ts`：统计 `$t('精确键')` 调用次数；用正则断言源码不再出现本刀范围内的写死中文；禁止宽泛 `not.toContain('状态')` 等。

至少覆盖：

1. `zh-cn.ts` / `en-us.ts` / `app.d.ts` 含 design 列出的全部新键，英文无汉字（对 `\u4e00-\u9fff` 搜索 `en-us.ts` 无命中），中文与 design 逐字一致（含 `defaultPlaceholder` 的 ASCII `...`、`groupedListHint` 的 `depth-1` / `Sprint`、`conditionalFormats` 的 `（≤10）`、`formulaRange` 的 `range` 与 `E46`、`fieldCycle` 中文仍是 `Cycle`）。测试必须读取 typings 源文件，断言 `page.issueList.board` / `displayOptions` / `bulk` / `search` / `searchSuggestions` 在三份文件键齐全，不能只比较两份 locale。
2. 调用次数（实施时按 tip 源码钉死精确数字，不得用宽泛大于 0 代替设计已写明的位点）：
   - `IssueBoard.vue`：`page.shell.noIssues` 1；`page.issueList.blockedBy` 1 且含 `$t('page.issueList.blockedBy', { count:`；`page.issueList.blocks` 1 且含 `{ count:`；`page.issueList.columns.estimate` 至少 1；`page.issueList.filters.project` 至少 1；`page.issueForm.cycle` 至少 1；`page.issueList.board.due` 1；`page.issueList.board.unassigned` 1；`page.issueList.board.moveFailed` 2。源码含 `lookupLabel(priorityLabels.value, issue.priority)` 或同等已有 `priorityLabels` 查找，不再调用 `getIssuePriorityLabel(`。
   - `IssueListGrouped.vue`：`page.shell.noIssues` 1；`page.issueList.board.groupedListHint` 1。
   - `DisplayOptionsPanel.vue`：`displayOptions.title` / `cardFields` / `customFieldColumns` / `boardSwimlanes` / `hideEmptyLanes` / `conditionalFormats` / `addRule` / `colorScales` / `addColorScale` / `iconSets` / `addIconSet` / `setPersonalDefault` / `noSwimlane` / `fieldCycle` 各至少 1；`displayOptions.remove` 为 3；`displayOptions.ruleCount` 为 1 且含 `$t('page.issueList.displayOptions.ruleCount', { n:`；`common.reset` 1；`page.issueList.computedFieldSuffixReadonly` 1；并映射 `columns.key` / `columns.assignee` / `columns.priority` / `groupBy.label` / `columns.type` / `columns.estimate` / `issueForm.dueDate` / `filters.project`。
   - `IssueBulkBar.vue`：`page.issueList.bulk.selected` 1 且含 `{ n:`；`page.issueForm.status`、`page.issueForm.priority`、`page.issueList.columns.assignee`、`page.issueForm.cycle`、`page.issueList.bulk.apply`、`page.issueList.bulk.selectFieldWarning`、`page.issueList.bulk.updateSuccess` 各 1；`page.issueList.bulk.updateFailed` 2；`common.cancel` 1 且源码在取消按钮处为 `$t('common.cancel')` 再接 ` (Esc)`。含 `useLabelTable('page.issueStatus')` 与 `useLabelTable('page.issuePriority')`。
   - `IssueSmartSearch.vue`：`page.issueList.search.defaultPlaceholder` 1；`page.issueList.search.appliedFilters` 1；`page.issueList.search.field` 1；芯片短标签分别走 `columns.status` / `columns.type` / `columns.priority` / `columns.assignee` / `columns.reporter` / `displayOptions.fieldCycle` / `filters.project` / `groupBy.label` / `common.search`。冒号只出现在模板或脚本拼接里，不出现在新键值里。
   - `issueSearchParser.ts` 的 `generateSearchSuggestions`：函数开头有 `void locale.value`；四条复用 `syntax.isOpen` / `isClosed` / `isInProgress` / `priorityUrgent`；`assignee:@me` 走 `scopeTitle.assignedToMe`；其余七条走 design 的 `searchSuggestions.*`；源码仍含 token 字面量 `is:open`、`label:bug`、`type:feature`、`priority:urgent`、`assignee:@me`、`cycle:__none__`、`project:<id>`、`cf:score>=8`。不得出现 `syntax.assigneeMe`、`syntax.typeFeature`、`syntax.customField`、`page.issueList.noneCycle`、`page.issueForm.unassigned`、`page.issueForm.dueDate`（卡片短标签）、`filters.cycle`、`common.confirm`、`issueForm.assignee`。
3. 范围内字面缺失（精确整句或带周围 markup 的正则，实施时按位点写）：`IssueBoard.vue` 不再出现 `description="暂无问题"`、`return '未指派'`、`被阻塞 {{`、`阻塞 {{`、`估点 {{`、`截止 {{`、`项目 {{`、`冲刺 {{`、`'看板移动失败'` / `"看板移动失败"`；`IssueListGrouped.vue` 不再出现 `description="暂无问题"` 与完整脚注原句；`DisplayOptionsPanel.vue` 不再出现模板里的「显示选项」「卡片字段」「自定义字段列」「看板泳道」「隐藏空泳道」「条件格式（≤10）」「添加规则」「色阶（≤5）」「添加色阶」「图标集（≤5）」「条规则」「添加图标集」「设为个人默认」以及独立按钮「删」；`IssueBulkBar.vue` 不再出现 `` `已选 ${selection.count.value} 项` ``、「请至少选择一项要修改的字段」「批量更新失败」「批量更新成功」、`placeholder="状态"`、`placeholder="优先级"`、`placeholder="负责人"`、`placeholder="冲刺"`、`>应用<`、`>取消 (Esc)<`；`IssueSmartSearch.vue` 不再把 `'搜索问题... (支持 is:open, field:key:value 等)'` 当作默认值，不再出现 `` `状态: ${` ``、`` `应用过滤器:` `` 这类写死短标签（`Cycle:` 改走 `fieldCycle` 后也不再写死拉丁字面，除非测试证明该字面只来自 `$t` 结果）。禁止用 `not.toContain('取消')` 或 `('状态')` 这类宽泛断言。
4. 明确保留（正向断言仍然存在）：`groupIssuesBy.ts` 仍含 `'未分配'`、`'无标签'`、`'空'`、`'计算错误'` 以及 `'（计算值·只读）'`；`groupIssuesBy.test.ts` 仍含 `toBe('未分配')`；`display-prefs.ts` 仍含 `（计算值·只读）` 与 `return value ? '是' : '否'`；`list/index.vue` 仍含 `const readonlySuffix = '（计算值·只读）'` 与 `$t('page.shell.searchIssues')`；`constants/issue.ts` 仍含 `label: '待办'` 与 `label: '低'`；`IssueBoard.vue` / `IssueListGrouped.vue` 仍渲染 `bucket.label`（或同等泳道标题）且不含把四个桶字映射到 `$t` 的覆盖表。`en-us.ts` 无汉字。
5. 用真实 i18n 抽查：`zh-CN` 下 `board.unassigned` 为「未指派」、`board.due` 为「截止」、`displayOptions.fieldCycle` 为 `Cycle`、`searchSuggestions.cycleNone` 为「无冲刺」；`en-US` 下分别为 Unassigned、Due、Cycle、No cycle。`blockedBy` 英文为 `Blocked by {count}`。

代表性骨架（完整键表以 design 为准，不要把这段示例里省略的键漏掉）：

```ts
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { $t, locale, setLocale } from '@/locales';

const boardVue = readFileSync(new URL('../../../views/issue/list/modules/IssueBoard.vue', import.meta.url), 'utf8');
const displayVue = readFileSync(new URL('../../../views/issue/list/modules/DisplayOptionsPanel.vue', import.meta.url), 'utf8');
const groupedVue = readFileSync(new URL('../../../views/issue/list/modules/IssueListGrouped.vue', import.meta.url), 'utf8');
const bulkVue = readFileSync(new URL('../../../components/IssueBulkBar.vue', import.meta.url), 'utf8');
const searchVue = readFileSync(new URL('../../../components/IssueSmartSearch.vue', import.meta.url), 'utf8');
const parserTs = readFileSync(new URL('../../../utils/issueSearchParser.ts', import.meta.url), 'utf8');
const groupTs = readFileSync(new URL('../../../utils/groupIssuesBy.ts', import.meta.url), 'utf8');
const listVue = readFileSync(new URL('../../../views/issue/list/index.vue', import.meta.url), 'utf8');

function countCalls(src: string, key: string): number {
  const exact = src.split(`$t('${key}')`).length - 1;
  const named = src.split(`$t('${key}',`).length - 1;
  return exact + named;
}

describe('issue list board English chrome', () => {
  it('binds board counts with the existing {count} signature', () => {
    expect(countCalls(boardVue, 'page.issueList.blockedBy')).toBe(1);
    expect(boardVue).toContain("$t('page.issueList.blockedBy', { count:");
    expect(countCalls(boardVue, 'page.issueList.blocks')).toBe(1);
    expect(boardVue).toContain("$t('page.issueList.blocks', { count:");
    expect(countCalls(boardVue, 'page.issueList.board.unassigned')).toBe(1);
    expect(countCalls(boardVue, 'page.issueList.board.due')).toBe(1);
    expect(countCalls(boardVue, 'page.issueList.board.moveFailed')).toBe(2);
    expect(boardVue).not.toContain(".replace('{count}'");
    expect(boardVue).not.toContain(".replace('{n}'");
    expect(boardVue).not.toContain("getIssuePriorityLabel(");
    expect(boardVue).not.toMatch(/description="暂无问题"/);
    expect(boardVue).not.toMatch(/return '未指派'/);
    expect(boardVue).not.toMatch(/看板移动失败/);
  });

  it('does not reuse near-synonym keys forbidden by design', () => {
    expect(boardVue).not.toContain("page.issueForm.unassigned");
    expect(boardVue).not.toContain("page.issueForm.dueDate");
    expect(displayVue).not.toContain("page.issueList.filters.cycle");
    expect(displayVue).not.toContain("page.issueList.groupBy.none");
    expect(bulkVue).not.toContain("page.issueForm.assignee");
    expect(bulkVue).not.toContain('common.confirm');
    expect(parserTs).toContain("page.issueList.syntax.isOpen");
    expect(parserTs).toContain("page.issueList.scopeTitle.assignedToMe");
    expect(parserTs).not.toContain("page.issueList.syntax.assigneeMe");
    expect(parserTs).not.toContain("page.issueList.syntax.typeFeature");
    expect(parserTs).not.toContain("page.issueList.syntax.customField");
    expect(parserTs).toMatch(/void\s+locale\.value/);
  });

  it('keeps decision E source strings and the list suffix bridge', () => {
    expect(groupTs).toContain("const UNASSIGNED_LABEL = '未分配'");
    expect(groupTs).toContain("const UNLABELLED_LABEL = '无标签'");
    expect(groupTs).toContain("const EMPTY_CF_LABEL = '空'");
    expect(groupTs).toContain("const ERROR_CF_LABEL = '计算错误'");
    expect(listVue).toContain("const readonlySuffix = '（计算值·只读）'");
    expect(listVue).toContain("$t('page.shell.searchIssues')");
    expect(displayVue).toContain("page.issueList.computedFieldSuffixReadonly");
  });
});
```

这些断言在产品尚未换绑时失败（RED），换绑后同一批断言变绿。不要先写「源码仍含中文」再翻成缺失断言。实施时按 design 补全全部新键与复用键的 `countCalls`、精确字面缺失正则，以及范围外保留项的正向断言。

- [ ] **Step 2: 跑测试确认 RED**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/issue-list-board-chrome.test.ts src/tests/issue/index.test.ts src/utils/groupIssuesBy.test.ts
```

期望：新测试失败原因是缺键、调用次数为 0，或范围内字面仍在。`index.test.ts` 与 `groupIssuesBy.test.ts` 在尚未改产品时应仍通过（token 与「未分配」桶仍在）。不要为了变绿先改产品。不要在这一步单独 commit。若新测试文件自己 import 失败，只修测试，不改产品。

### Task 2: 语言包与 schema

**Files:** `zh-cn.ts`、`en-us.ts`、`app.d.ts`。

**Consumes:** design 第 3 节全部新键。**Produces:** 三份文件中 `page.issueList` 下新分组齐全，已有键值不变。

- [ ] **Step 1: 按 design 第 3 节加入全部新键**

在 `page.issueList` 下、已有 `blockedBy` / `blocks` / `noneCycle` 附近增加下列分组，并同步 `App.I18n.Schema`。中文逐字。英文 sentence case，无汉字。已有键（含 `common.reset`、`common.cancel`、`common.search`、`page.shell.noIssues`、`page.shell.searchIssues`、`page.issueList.columns.*`、`page.issueList.groupBy.*`、`page.issueList.filters.project`、`page.issueList.computedFieldSuffixReadonly`、`page.issueList.syntax.*`、`page.issueList.scopeTitle.assignedToMe`、`page.issueForm.status` / `priority` / `cycle` / `dueDate`、`page.issuePriority.*`）不改值。不要新增 `common.apply` 或改 `common.confirm`。不要把 `fieldCycle` 的中文写成「冲刺」。不要把 `board.unassigned` 的中文写成「未分配」。

```ts
// App.I18n.Schema.page.issueList 增补（与 zh-cn.ts / en-us.ts 同形）
board: {
  unassigned: string;
  due: string;
  moveFailed: string;
  groupedListHint: string;
};
displayOptions: {
  title: string;
  cardFields: string;
  customFieldColumns: string;
  boardSwimlanes: string;
  hideEmptyLanes: string;
  conditionalFormats: string;
  remove: string;
  addRule: string;
  colorScales: string;
  addColorScale: string;
  iconSets: string;
  ruleCount: string;
  addIconSet: string;
  setPersonalDefault: string;
  noSwimlane: string;
  fieldCycle: string;
};
bulk: {
  selected: string;
  apply: string;
  selectFieldWarning: string;
  updateFailed: string;
  updateSuccess: string;
};
search: {
  defaultPlaceholder: string;
  appliedFilters: string;
  field: string;
};
searchSuggestions: {
  labelBug: string;
  typeFeature: string;
  cycleNone: string;
  filterByProject: string;
  customField: string;
  formulaEquals: string;
  formulaRange: string;
};
```

英文 `moveFailed` / `updateFailed` 使用弯引号 `Couldn’t`（U+2019），与已有 `page.issueList.messages` 一致。

- [ ] **Step 2: 再跑 Task 1 的测试**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/issue-list-board-chrome.test.ts
```

语言包与 schema 断言应变绿；各产品源码的调用次数与字面缺失断言应仍红。不要在这一步单独 commit。

### Task 3: 五个表面组件与搜索建议函数

**Files:** `IssueBoard.vue`、`DisplayOptionsPanel.vue`、`IssueListGrouped.vue`、`IssueBulkBar.vue`、`IssueSmartSearch.vue`、`issueSearchParser.ts`（仅 `generateSearchSuggestions`）。有条件：`tests/issue/index.test.ts`。

**Consumes:** Task 2 的键。**Produces:** 范围内写死中文换绑为 `$t`，既有 token 与决定 E 源串仍在。

- [ ] **Step 1: 最小改动换绑 `$t`**

从 `@/locales` 导入 `$t` 与 `locale`（组件若已导入则复用，不要改成局部 `t()`）。从 `@/locales/display-label` 导入已有的 `useLabelTable` / `lookupLabel`（`IssueBoard.vue` 已在用，保持同一路径）。

`IssueBoard.vue`：

- 空状态：`description="$t('page.shell.noIssues')"`。
- `assigneeLabel` 的兜底由 `'未指派'` 改为 `$t('page.issueList.board.unassigned')`。有名字 / sso_name / id 切片的分支不译。
- 被阻塞 / 阻塞改为 `$t('page.issueList.blockedBy', { count: issue.blocked_by_count })` 与 `$t('page.issueList.blocks', { count: issue.blocks_count })`。
- 估点 / 项目 / 冲刺标签复用 design 第 3 节键，短标签与数值仍在模板拼接，例如 `{{ $t('page.issueList.columns.estimate') }} {{ issue.estimate_points }}`。截止走 `$t('page.issueList.board.due')`，不要用 `issueForm.dueDate`。
- 优先级：用已有 `priorityLabels` 做 `lookupLabel(priorityLabels.value, issue.priority)`，删除卡片上的 `getIssuePriorityLabel(...)` 调用。不要改 `constants/issue.ts`。
- `:214` 与 `:224` 的 `'看板移动失败'` 改为 `$t('page.issueList.board.moveFailed')`。
- 不要增加把「未分配」「无标签」「空」「计算错误」映射到 `$t` 的表，不要改传入 `groupIssuesBy` 的 label 或桶 title 的渲染。

`DisplayOptionsPanel.vue`：

- 模板标题与按钮按 design 换绑。`{{ iset.rules.length }} 条规则` 改为 `$t('page.issueList.displayOptions.ruleCount', { n: iset.rules.length })`。「重置」走 `common.reset`。「删」三处走同一 `displayOptions.remove`。
- 字段勾选不要直接渲染 `DISPLAY_FIELD_LABELS[key]`。在组件内做映射 computed，第一句 `void locale.value;`，按 design 把九个字段指到复用键或 `displayOptions.fieldCycle`。不改 `display-prefs.ts`。
- 泳道下拉不要直接把 `buildSwimlaneOptions(...)` / `SWIMLANE_OPTIONS` 交给 `NSelect`。computed 第一句 `void locale.value;`，然后：`none` → `displayOptions.noSwimlane`；`assignee` / `priority` / `type` / `label` → 对应 `groupBy.*`；`option.label.endsWith('（计算值·只读）')` 时，按 `list/index.vue:157-160` 同样切片并接 `$t('page.issueList.computedFieldSuffixReadonly')`。不要复用 `groupBy.none` 或 `filters.cycle`。不要改 `:510` 源串。

`IssueListGrouped.vue`：

- 空状态走 `page.shell.noIssues`。底部脚注走 `page.issueList.board.groupedListHint`。继续渲染 `bucket.label`，不覆盖四个桶字。

`IssueBulkBar.vue`：

- `countLabel` computed 改为：

```ts
const countLabel = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  return $t('page.issueList.bulk.selected', { n: selection.count.value });
});
```

- 占位：状态 `page.issueForm.status`，优先级 `page.issueForm.priority`，负责人 `page.issueList.columns.assignee`，冲刺 `page.issueForm.cycle`。不要用 `issueForm.assignee`。Labels 占位保持 `'Labels'`。
- 应用走 `page.issueList.bulk.apply`，不要用 `common.confirm`。取消按钮：`{{ $t('common.cancel') }} (Esc)`。
- toast 三句走 `selectFieldWarning` / `updateFailed` / `updateSuccess`。
- 用 `useLabelTable('page.issueStatus')` 与 `useLabelTable('page.issuePriority')` 做成 computed options，替换模板里直接绑定的 `issueStatusOptions` / `issuePriorityOptions`。computed 第一句 `void locale.value;`。不改常量文件。

`IssueSmartSearch.vue`：

- 不要引入 `useI18n()`，除非 tip 源码已经在用。默认占位改为未传入时走 `$t('page.issueList.search.defaultPlaceholder')`（computed 或等价解析，第一句 `void locale.value;`）。不要改 `list/index.vue` 传入的 `page.shell.searchIssues`。
- `activeFilters` computed 第一句 `void locale.value;`。短标签走 design 复用键，再在脚本里拼 `:` 与值，例如 `` `${$t('page.issueList.columns.status')}: ${parsedQuery.value.status}` ``。`Cycle` 走 `displayOptions.fieldCycle`。自定义字段走 `` `${$t('page.issueList.search.field')} ${cf.key}: ${cf.value}` ``。芯片值不译。
- 「应用过滤器」走 `$t('page.issueList.search.appliedFilters')`，冒号留在模板或拼接里。

`issueSearchParser.ts` 只改 `generateSearchSuggestions`：

```ts
import { $t, locale } from '@/locales';

export function generateSearchSuggestions(): string[] {
  // eslint-disable-next-line no-void
  void locale.value;
  return [
    `is:open - ${$t('page.issueList.syntax.isOpen')}`,
    `is:closed - ${$t('page.issueList.syntax.isClosed')}`,
    `is:in_progress - ${$t('page.issueList.syntax.isInProgress')}`,
    `assignee:@me - ${$t('page.issueList.scopeTitle.assignedToMe')}`,
    `label:bug - ${$t('page.issueList.searchSuggestions.labelBug')}`,
    `type:feature - ${$t('page.issueList.searchSuggestions.typeFeature')}`,
    `priority:urgent - ${$t('page.issueList.syntax.priorityUrgent')}`,
    `cycle:__none__ - ${$t('page.issueList.searchSuggestions.cycleNone')}`,
    `project:<id> - ${$t('page.issueList.searchSuggestions.filterByProject')}`,
    `field:severity:s1 - ${$t('page.issueList.searchSuggestions.customField')}`,
    `field:score:10 - ${$t('page.issueList.searchSuggestions.formulaEquals')}`,
    `cf:score>=8 - ${$t('page.issueList.searchSuggestions.formulaRange')}`
  ];
}
```

若该文件已有 `@/locales` 导入，合并之，不要双份。不要改 parser 其它导出。

- [ ] **Step 2: 跑测试确认 GREEN，并核既有搜索测试**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/issue-list-board-chrome.test.ts src/tests/issue/index.test.ts src/utils/groupIssuesBy.test.ts
```

期望：新测试 EXIT 0；`groupIssuesBy.test.ts` EXIT 0 且「未分配」断言仍在。`index.test.ts` 期望 EXIT 0，且 `:111-114` 的 token 断言未被改弱。

若 `index.test.ts` 因挂载 `IssueSmartSearch` 出现 `Need to install with app.use` 或同等缺少 i18n plugin 的失败：不要删产品里的 `$t` / `useI18n`。只在该测试的 `mount(IssueSmartSearch, …)` 处补 `global: { plugins: [i18n] }`（若已有 pinia 则为 `[pinia, i18n]`），i18n 必须来自真实 `@/locales`，可切换 `zh-CN` / `en-US`。不得改 token 期望，不得放宽 `toContain('is:open')` 等。补完后再跑同一条命令，期望 EXIT 0。若测试因其它范围外原因失败，STOP 并改 plan，不要顺手扩范围。

若只有插值或 plugin 失败，按 Global Constraints 修测试与产品，不要 `.replace`，不要摘掉 `useI18n`。

- [ ] **Step 3: 产品提交（测试与产品一起，恰好白名单内的非 docs 路径）**

```bash
cd "$REPO"
git add frontend/src/locales/langs/zh-cn.ts frontend/src/locales/langs/en-us.ts frontend/src/typings/app.d.ts \
  frontend/src/views/issue/list/modules/IssueBoard.vue \
  frontend/src/views/issue/list/modules/DisplayOptionsPanel.vue \
  frontend/src/views/issue/list/modules/IssueListGrouped.vue \
  frontend/src/components/IssueBulkBar.vue \
  frontend/src/components/IssueSmartSearch.vue \
  frontend/src/utils/issueSearchParser.ts \
  frontend/src/locales/__tests__/issue-list-board-chrome.test.ts
# 仅当 Step 2 实际修改了 index.test.ts 时才 add 该文件
if git status --porcelain -- frontend/src/tests/issue/index.test.ts | grep -q .; then
  git add frontend/src/tests/issue/index.test.ts
fi
git diff --cached --name-only | sort
# 不得出现白名单外路径，不得含 .env.prod、components.d.ts、groupIssuesBy.ts、display-prefs.ts、constants/issue.ts、list/index.vue
allowed='frontend/src/locales/langs/zh-cn.ts
frontend/src/locales/langs/en-us.ts
frontend/src/typings/app.d.ts
frontend/src/views/issue/list/modules/IssueBoard.vue
frontend/src/views/issue/list/modules/DisplayOptionsPanel.vue
frontend/src/views/issue/list/modules/IssueListGrouped.vue
frontend/src/components/IssueBulkBar.vue
frontend/src/components/IssueSmartSearch.vue
frontend/src/utils/issueSearchParser.ts
frontend/src/locales/__tests__/issue-list-board-chrome.test.ts
frontend/src/tests/issue/index.test.ts'
while IFS= read -r path; do
  printf '%s\n' "$allowed" | grep -Fxq "$path" || exit 1
done < <(git diff --cached --name-only)
test "$(git diff --cached --name-only | grep -cx 'frontend/src/tests/issue/index.test.ts')" -le 1
strace -f -e trace=openat,execve -o "$EVIDENCE/product-commit.strace" \
  git commit -m "fix: localize issue list board chrome for English"
```

父提交必须是文档笔。porcelain 必须为空（`.env.prod` 须已被 gitignore，不得出现在 porcelain 或 index）。strace 再核克隆根 `COMMIT_EDITMSG`。hook 失败则 STOP。

### Task 4: 终轮四门与证据包

- [ ] **Step 1: 再跑四门**

```bash
bash "$EVIDENCE/run-gates.sh" final
```

vitest 必须 EXIT 0。build 仅在已核 `.env.prod` 已就位时必须 EXIT 0；否则对照 baseline 同记 EXIT STOP，不得写成全绿或换用 `.env.example`。tsc/eslint 对照 baseline：路径 + rule/code + severity + message（忽略行号），added 0、removed 0。若 build 再次弄脏 `components.d.ts`，从仓库根还原后再记 tsc/eslint。不要把未还原的脏跑当成终轮。不得写成全绿。

- [ ] **Step 2: 打包证据并停手**

证据包写入 `/workspace/designs/issue-list-board-en-chrome-verify/`（实施时再建目录）。必须含：每一笔提交的 `git rev-parse` / 第一父提交 / 说明；相对精确 base 的 `git diff --name-only --no-ext-diff`、`--stat` 与完整 `final.diff`；**每一笔提交相对其第一父提交**的 name-only、diffstat 与完整 diff（不得只用 `final.diff` 代替分笔；第 5 刀第一包因缺分笔被 Request Changes）；白名单路径列表；四门 baseline 与 final 的 meta/stdout/stderr；每一笔 commit 的 strace 与 hook sha256；`git status --porcelain`（空）；不含 `.env.prod` 正文、token、`dist/`、`node_modules`。若后来不得不多出修订笔，每一笔同样要有相对其第一父提交的这三份，不要 amend 前序提交来补证据。算出包的 sha256 与字节数后再交审。

```bash
BASE=6b6ad3b4784fd65ce917c42fb3ec978c10e4b557
cd "$REPO"
test "$(git merge-base --is-ancestor "$BASE" HEAD && echo yes)" = yes || exit 1
test "$(git rev-list --count "$BASE"..HEAD)" -ge 2 || exit 1
git log --reverse --format='%H %P %s' "$BASE"..HEAD > "$EVIDENCE/commits.txt"
git diff --name-only --no-ext-diff "$BASE" HEAD > "$EVIDENCE/final.name-only.txt"
git diff --stat --no-ext-diff "$BASE" HEAD > "$EVIDENCE/final.diffstat.txt"
git diff --no-ext-diff "$BASE" HEAD > "$EVIDENCE/final.diff"
i=1
git rev-list --reverse "$BASE"..HEAD | while read -r sha; do
  parent=$(git rev-parse "${sha}^")
  git diff --name-only --no-ext-diff "$parent" "$sha" > "$EVIDENCE/commit${i}.name-only.txt"
  git diff --stat --no-ext-diff "$parent" "$sha" > "$EVIDENCE/commit${i}.diffstat.txt"
  git diff --no-ext-diff "$parent" "$sha" > "$EVIDENCE/commit${i}.diff"
  printf 'sha=%s\nparent=%s\nsubject=%s\n' "$sha" "$parent" "$(git log -1 --format=%s "$sha")" > "$EVIDENCE/commit${i}.meta.txt"
  i=$((i+1))
done
first=$(git rev-list --reverse "$BASE"..HEAD | head -n1)
test "$(git log -1 --format=%s "$first")" = "docs: specify issue list board English chrome" || exit 1
test "$(git rev-parse "${first}^")" = "$BASE" || exit 1
printf '%s\n' \
  docs/superpowers/plans/2026-11-12-issue-list-board-en-chrome.md \
  docs/superpowers/specs/2026-11-12-issue-list-board-en-chrome-design.md \
  | sort > "$EVIDENCE/commit1.expected-paths.txt"
sort "$EVIDENCE/commit1.name-only.txt" | cmp - "$EVIDENCE/commit1.expected-paths.txt"
```

上面 `cmp` 失败即 STOP，不要改第一笔去凑。第一笔的分笔 diff 须恰好是那两份 docs，不得混入产品或测试路径。`final.diff` 仍要保留，但不能代替分笔。

到此停止。不 push，不开 PR，不 merge，不部署，不写下一刀。

## 自我核对

- 盘点第 3 节与第 6 节第一片的白名单与范围外项，都能在本 plan 的 Files / 范围约束里找到对应处理或明确排除。第二片壳层与第三片创建/编辑剩余句未列入实施任务。
- 决定 E/F 已写入 Global Constraints 和 Task 3 禁改清单，并按推荐案锁定。
- 无 TBD / “类似 Task N” / 无代码的“写测试”。插值：被阻塞/阻塞用 `{count}`，已选与条规则用 `{n}`，禁止 `.replace`。
- `tests/issue/index.test.ts` 的处理已写死：先不改；只有挂载缺 plugin 才补 plugin 并加入白名单；token 断言不削弱。
- hook、软链、根目录提交、`components.d.ts` 从仓库根还原、Vite 端口 `9573`，均按第 4 / 5 刀已接受做法写死并改了 base，不是改 hook 正文。
- 证据包必须含每一笔的 name-only / diffstat / 完整 diff，加上相对 base 的 `final.diff`；第一笔分笔须恰好是两份 docs。不得只用 `final.diff`。
