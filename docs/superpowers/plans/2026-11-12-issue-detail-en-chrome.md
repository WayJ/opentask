# 问题详情页英文铬 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把问题详情页宿主上仍写死的可见文案（顶栏、描述与活动、评论框、右侧下半、反应 / 外链 / PR 面板、活动流动词）接到 zh/en，不改提交、关系、标签、评论和附件的行为。

**Architecture:** 新增 `page.issueDetail`、`page.issueReaction`、`page.issueLink`、`page.issuePr`，并同步 `App.I18n.Schema`。页面与三个只被详情引用的组件继续用 `@/locales` 的 `$t`。活动流复用 `page.issueStatus` / `page.issuePriority`，其余动词走 `page.issueDetail.timeline*`。已有整句优先复用，不造近义 key。

**Tech Stack:** Vue 3、vue-i18n、Naive UI、Vitest、Vue Test Utils、已有 `$t` 与 `App.I18n.Schema`，无新依赖。

## Global Constraints

- 本轮只交本地草稿。获批口令为「design ok，开写」。决定 A/B/C/D/G 未确认前不得实施。本计划按 design 推荐案写；否决任一条，先改 design 与本 plan，再执行。
- 精确 base：`290c3ed3be0cbd760eafca15e3a682b13b7b7004`（PR16 tip）。不改写 PR6–16 已存提交或头。
- 后续仅普通隔离 clone（`.git` 为目录），不用 worktree。不写/reset MAIN `244c93e296a047cf138a880fa24d683b4be8203d` 或 PIN `250fc34af9c64e828aab706567b0430d3d74e452`。不碰已有 pid 服务。不回复会绑到 PR13–PR16 头的既有 CloudAgent。
- 不买额度，不 merge，不部署。未经再授权不 push、不开 PR。本轮不建产品分支、不改产品、不 TDD、不 commit。获批后才按本 plan 实施。
- 英文页内铬 sentence case。新键进入 `App.I18n.Schema`。页面用 `$t`。不要把已有 `$t` 改成局部 `t()`。不要改 `constants/issue.ts`。
- 脚本里调用 `$t` 的 computed，第一句必须是 `void locale.value;`，位于任何短路之前。`no-void` 只用 `eslint-disable-next-line` 盖住这一句，或紧贴该 computed 的 disable/enable 块。禁止文件级 `eslint-disable no-void`。
- 命名参数插值必须写成 `$t('…', { n: … })` 或 `$t('…', { from, to, … })`，禁止 `.replace('{n}', …)` 或同类字符串替换迁就测试。
- 测试统计 `$t('…')` 调用点。字面缺失用正则。禁止 `not.toContain('描述')`、`('预览')`、`('附件')`、`('编辑')`、`('取消')`、`('标题')`、`('状态')`。
- Vue Test Utils stub 同时覆盖 naive-ui 真实 name 与 `N*` 别名。不为测试修改产品组件的 `name` 或 `defineOptions`。有 `useI18n()` 的挂载必须带 `plugins: [i18n]`（已有 pinia 则 `[pinia, i18n]`），不要删 `useI18n`。
- 四门从 `frontend/` 跑：`pnpm exec vitest run`、`pnpm exec vite build --mode prod`（仓库外 config）、`pnpm exec vue-tsc --noEmit --skipLibCheck`、`pnpm exec eslint .`。对照当次干净 `290c3ed3` baseline。tsc/eslint 基线非 0 则保持 added 0 / removed 0，不得写成全绿，不得借用 PR15/PR16 的失败行号。不能写 dual Grok Approve。
- 两笔提交：第一笔仅两份 docs；第二笔是 RED 测试与最小 GREEN 产品一起提交。不预安排第三笔。不 amend、不 rebase、不 squash、不用 `--no-verify`。
- hook：只在新 clone 上处理。官方 hook 正文是 `bun sa git-commit-verify`，已核原件 sha256 `46d7a87f731e693d7d81f98f9d9c0286e070f28c8d6aa9a0f88326e8699b5a59`（234 字节），路径 `/workspace/designs/issue-composer-en-chrome-verify/official-commit-msg`。`pnpm install` 后若 simple-git-hooks 把 hook 写到 `frontend/.git/hooks/`，按第 4 刀已接受做法：把官方原件原样拷到 `$REPO/.git/hooks/commit-msg` 且可执行；只删 `frontend/.git/hooks/pre-commit` 与根目录若出现的非 sample pre-commit；不删整个 `frontend/.git`，不动那里的 commit-msg；不重跑 `simple-git-hooks`，不改 `core.hooksPath`，不用 `SKIP` / `--no-verify`，不另装 verifier。再在仓库根建 gitignore 相对软链 `ln -s frontend/node_modules node_modules`；不把软链入库，不改 `.gitignore`。只允许在仓库根 `git commit`。EXIT 0 不是 hook 路径证明，须有 strace 显示只读打开克隆根 `.git/COMMIT_EDITMSG`。若 hook 失败（含 `Script not found "sa"`）或 `COMMIT_EDITMSG` ENOENT：原件落盘后立即 STOP，不重试，不改 hook。
- 不运行 `eslint --fix`。不改 `.env.prod` 正文；实施若要 prod build，只使用 sha256 仍为 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`（1896 字节）的已核副本。缺文件或哈希不符则 STOP，不用 `.env.example` 顶替。不把正文或键值写进证据。
- prod build 若弄脏 `frontend/src/typings/components.d.ts`，必须从**仓库根** `git checkout -- frontend/src/typings/components.d.ts`，再跑 tsc/eslint；打包还原前后 porcelain；不提交该文件。不要只在 `frontend/` 下 checkout。
- 决定 A：不译 Agent 指令弹层标题、说明和生成正文。决定 B：活动流复用 `page.issueStatus` / `page.issuePriority`，中文「待处理」变为「待办」。决定 C：不改 `deletedReadonlyBanner` / `restoreSuccessMessage`；顶栏「恢复」走 `page.issueTrash.restore`。决定 D：不改 `slaMetricBadgePrefix`，不改 `sla.test.ts`。决定 G：本刀是详情宿主，不改先做壳层。
- 本刀不改 `MarkdownEditor.vue`、`AttachmentList.vue`、`IssueCustomFieldsEditor.vue` 内部、`constants/issue.ts`、详情页 `window.$message`（外链 / PR 面板自己文件内的 toast 除外）、创建页「自定义字段（可选）」、编辑页「加载中...」。

### 白名单（14 路径）

- `docs/superpowers/specs/2026-11-12-issue-detail-en-chrome-design.md`
- `docs/superpowers/plans/2026-11-12-issue-detail-en-chrome.md`
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/typings/app.d.ts`
- `frontend/src/views/issue/detail/index.vue`
- `frontend/src/components/IssueReactions.vue`
- `frontend/src/components/issue-links/IssueLinksPanel.vue`
- `frontend/src/components/issue-vcs/IssuePrPanel.vue`
- `frontend/src/utils/formatTimelineAction.ts`
- `frontend/src/utils/formatTimelineAction.test.ts`
- `frontend/src/locales/__tests__/issue-detail-chrome.test.ts`（新建）
- `frontend/src/locales/__tests__/issue-composer-chrome.test.ts`（只改把详情顶栏「状态」「删除」「取消」冻成范围外的那段）
- `frontend/src/views/issue/detail/focus.test.ts`（只改用字面量「编辑」定位顶栏按钮的那段，不改 CSS）

实施前若发现 `formatTimelineAction.test.ts` 路径不同，STOP 并改 plan，不要扩白名单到范围外文件。`sla.test.ts`、`sla-trash-chrome.test.ts`、`issueTrashMeta.ts`、`service/api/sla.ts` 不在白名单。

---

### Task 0: 获批后隔离、当次基线、docs-only commit

**Files:** 仅上述两份 docs。**Consumes:** 精确 `290c3ed3be0cbd760eafca15e3a682b13b7b7004` 与已批的两份本地文件。**Produces:** 普通 clone 上的文档提交，以及仓库外 baseline 原件。

- [ ] **Step 1: 在实施环境建全新普通 clone**

下面的命令等获批后再执行。先确认目标不存在。不写/reset main `244c93e2` 或 pin `250fc34a`。不回复 PR16 的 CloudAgent。

```bash
export TZ=Asia/Shanghai
export REPO=/tmp/cursor/opentask-issue-detail-en-chrome-clone
export EVIDENCE=/tmp/cursor/opentask-readonly/issue-detail-en-chrome-logs
export OFFICIAL_HOOK=/workspace/designs/issue-composer-en-chrome-verify/official-commit-msg
export APPROVED_DESIGN=/workspace/designs/issue-detail-en-chrome-spec/2026-11-12-issue-detail-en-chrome-design.md
export APPROVED_PLAN=/workspace/designs/issue-detail-en-chrome-spec/2026-11-12-issue-detail-en-chrome.md
test ! -e "$REPO" || exit 1
test -f "$OFFICIAL_HOOK" || exit 1
test "$(sha256sum "$OFFICIAL_HOOK" | awk '{print $1}')" = 46d7a87f731e693d7d81f98f9d9c0286e070f28c8d6aa9a0f88326e8699b5a59 || exit 1
mkdir -p "$EVIDENCE"
git clone https://github.com/WayJ/opentask.git "$REPO"
cd "$REPO"
git switch --detach 290c3ed3be0cbd760eafca15e3a682b13b7b7004
test -d .git || exit 1
test "$(git rev-parse HEAD)" = 290c3ed3be0cbd760eafca15e3a682b13b7b7004 || exit 1
test -z "$(git status --porcelain)" || exit 1
test -z "$(git config --get core.hooksPath)" || exit 1
git switch -c cursor/issue-detail-en-chrome-4333
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
test -z "$(git status --porcelain)" || exit 1
sha256sum .git/hooks/commit-msg > "$EVIDENCE/commit-msg.sha256"
git status --porcelain > "$EVIDENCE/checkout-porcelain.txt"
test ! -s "$EVIDENCE/checkout-porcelain.txt" || exit 1
```

任一项失败即 STOP，不改 hook 正文，不另装 verifier。`.env.prod` 只从已核来源拷贝，拷贝后立刻核 sha256 仍是 `b686d37a…`（1896）；缺原件或哈希不符 STOP。不记录正文。依赖和 env 准备好之后再确认 tracked diff 为空。已有服务端口不动。Vite 只读 config 的 server port 用 `9572`，`strictPort: true`，`open: false`。

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
    server: { ...(resolved.server || {}), open: false, host: '127.0.0.1', port: 9572, strictPort: true }
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

baseline HEAD 必须仍是精确 base，tracked diff 空（还原 `components.d.ts` 之后）。vitest 与 build 必须 EXIT 0 才继续。tsc / eslint 非 0 则把诊断原样留下，不修范围外问题。记录 eslint 摘要行（历史指纹是 872 problems，以当次 baseline 为准）。build 前后比较 tracked diff 和生成文件 hash。意外改动就 STOP。

- [ ] **Step 3: 文档先行，恰好两文件提交**

把已批文件逐字节放入 docs，`cmp` 前后 sha256。拿不到已批原件就 STOP，不从未批草稿复刻。只在仓库根提交。

```bash
cd "$REPO"
mkdir -p docs/superpowers/specs docs/superpowers/plans
cp "$APPROVED_DESIGN" docs/superpowers/specs/2026-11-12-issue-detail-en-chrome-design.md
cp "$APPROVED_PLAN" docs/superpowers/plans/2026-11-12-issue-detail-en-chrome.md
cmp "$APPROVED_DESIGN" docs/superpowers/specs/2026-11-12-issue-detail-en-chrome-design.md
cmp "$APPROVED_PLAN" docs/superpowers/plans/2026-11-12-issue-detail-en-chrome.md
git add docs/superpowers/specs/2026-11-12-issue-detail-en-chrome-design.md docs/superpowers/plans/2026-11-12-issue-detail-en-chrome.md
test "$(git diff --cached --name-only | wc -l)" = 2 || exit 1
git diff --cached --name-only | sort > "$EVIDENCE/docs-cached-paths.txt"
# 只从仓库根 commit；留下 strace
strace -f -e trace=openat,execve -o "$EVIDENCE/docs-commit.strace" git commit -m "docs: specify issue detail English chrome"
test "$(git rev-parse HEAD^)" = 290c3ed3be0cbd760eafca15e3a682b13b7b7004 || exit 1
test -z "$(git status --porcelain)" || exit 1
```

`git diff --cached --name-only` 必须恰好是这两个路径。hook 哈希提交后仍须是 `46d7a87f…`。strace 必须出现克隆根 `.git/COMMIT_EDITMSG` 以及 hook / `bun sa git-commit-verify`。EXIT 0 本身不够。遇到 hook 失败或 `COMMIT_EDITMSG` ENOENT 立即 STOP，不重试。

### Task 1: tests-only RED（不改产品，不另强制 RED commit）

**Files:**

- Create: `frontend/src/locales/__tests__/issue-detail-chrome.test.ts`
- Modify: `frontend/src/locales/__tests__/issue-composer-chrome.test.ts`（只改详情顶栏范围外那段）
- Modify: `frontend/src/views/issue/detail/focus.test.ts`（只改「编辑」定位）
- Modify: `frontend/src/utils/formatTimelineAction.test.ts`（按决定 B 更新状态词期望；必须接入真实 `@/locales` i18n，可切换 zh-CN / en-US，不要只改期望字符串）

**Consumes:** design 第 3 节键表。**Produces:** 红测；产品尚未改时必须失败。

- [ ] **Step 1: 写详情铬测试**

测试文件安装真实 `@/locales` i18n（`zh-CN` / `en-US`），不要自己造一套残缺 messages。模式对齐 `markdown-editor-chrome.test.ts` / `issue-composer-chrome.test.ts`：统计 `$t('精确键')` 调用次数；用正则断言源码不再出现本刀范围内的写死中文；禁止宽泛 `not.toContain('状态')` 等。

至少覆盖：

1. `zh-cn.ts` / `en-us.ts` / `app.d.ts` 含 design 列出的全部新键，英文无汉字，中文与 design 逐字一致（含 `commentPlaceholder` 句末「等」和顿号）。
2. `detail/index.vue` 对复用键与新键的调用次数：`page.issueTrash.restore`、`common.edit`、`common.delete`、`common.cancel`、`common.confirm`、`page.issueForm.status`、`page.issueForm.unset`、`page.issueComposer.description`、`page.issueComposer.attachments`、`page.issueList.columns.estimate`、`page.issueList.toolbar.pinToSidebar`、`page.issueList.toolbar.unpinFromSidebar`、`page.insights.exportCsv`，以及 `page.issueDetail.*` 各键。`watch`、`unwatch`、`unwatchInline` 必须分别 `countCalls`：顶栏 `:1545` 走 `watch` / `unwatch`，关注者行内 `:2026` 只走 `unwatchInline`，次数均为 1，且行内不得出现 `page.issueDetail.unwatch` 或 `common.cancel`。`activity` 与 `viewedNTimes` 必须是 `$t('page.issueDetail.activity', { n: … })` / `$t('page.issueDetail.viewedNTimes', { n: … })`，并 `not.toContain(".replace('{n}'")`。顶栏收藏按复用后的中英文断言：`pinToSidebar` 仍是「收藏到侧栏」/ Pin to sidebar，`unpinFromSidebar` 是「取消侧栏」/ Unpin from sidebar；源码不再出现字面量「取消侧栏收藏」。
3. 模板与脚本里不再出现本刀范围内的字面量：`父问题：`、`复制问题`、`更换父`、`设为子项…`、`提升为根`、`复制分支名`、`暂无描述`（只禁这句完整空态，不要禁「暂无描述内容」）、`子问题`、`+ 添加`、`暂无子问题`、`写下回复...支持 Markdown`、`发表回复`、`发表评论`、完整 `commentPlaceholder` 中文、`选择 Milestone`、`无 Milestone`、`工时`、`预估:`、`实际:`、`已暂停`、`客户需求`、`暂无关联`、`目标问题 ID 或 KEY-N`、`确认添加`、`暂无标签`、`选择标签`、`创建于`、`更新于`、`快速操作`、`获取 Agent 指令`、`刷新数据`。顶栏「状态」「编辑」「删除」「恢复」「关注」「取消关注」用带周围 markup 或精确属性的正则，避免误伤范围外 toast / Agent 正文。关注者行内「取消」的缺失正则必须带周围 markup（例如该按钮所在节点），避免误伤评论宿主的 `common.cancel` 或 toast。
4. 明确保留（正向断言仍然存在）：`MarkdownEditor` 未被本文件修改；`AttachmentList` 内部中文仍在；`IssueCustomFieldsEditor` 内部中文仍在；`deletedReadonlyBanner` / `restoreSuccessMessage` 源串仍在；`slaMetricBadgePrefix` 仍是「首响 SLA」「状态 SLA」；Agent 弹层标题 `🤖 Agent 工作指令` 与说明「复制下方指令，粘贴到 Claude 中即可指挥 agent 开始工作」仍在；详情 `window.$message` 里本刀未收的 toast 仍是中文。
5. `IssueReactions.vue`、`IssueLinksPanel.vue`、`IssuePrPanel.vue` 的 `$t` 次数与范围内字面缺失。面板 toast 走新键。URL 示例 `https://github.com/org/repo/pull/1` 仍在 `IssuePrPanel.vue`。
6. `formatTimelineAction.ts` 不再含写死的 `open: '待处理'` 表；`getStatusLabel` / `getPriorityLabel` 走 `$t('page.issueStatus.'…)` / `$t('page.issuePriority.'…)`（先读 locale 若放在 computed/函数闭包里则按 Global Constraints）。`待处理` 不得再出现在该文件。`formatTimelineAction.test.ts` 必须接入真实 `@/locales` i18n（可切换 `zh-CN` / `en-US`），不要只改期望字符串，也不要自己造一套残缺 messages。这是第 4 刀挂载缺 i18n 的教训，避免 RED/GREEN 被 `Need to install with app.use` 打断。在已安装的 i18n 下断言中文「待办」/ 英文 Open，以及 design 的活动流动词。

挂载 `IssueReactions` 等使用 `useI18n` 的组件时：`plugins: [i18n]`。

代表性骨架（完整键表以 design 为准，不要把这段示例里省略的键漏掉）：

```ts
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const detailVue = readFileSync(new URL('../../../views/issue/detail/index.vue', import.meta.url), 'utf8');
const timelineTs = readFileSync(new URL('../../../utils/formatTimelineAction.ts', import.meta.url), 'utf8');

function countCalls(src: string, key: string): number {
  const exact = src.split(`$t('${key}')`).length - 1;
  const named = src.split(`$t('${key}',`).length - 1;
  return exact + named;
}

describe('issue detail English chrome', () => {
  it('binds the top bar and activity count with named interpolation', () => {
    expect(countCalls(detailVue, 'page.issueForm.status')).toBeGreaterThanOrEqual(2); // 顶栏 + 右侧已有
    expect(countCalls(detailVue, 'page.issueTrash.restore')).toBe(1);
    expect(countCalls(detailVue, 'common.edit')).toBeGreaterThanOrEqual(1);
    expect(countCalls(detailVue, 'page.issueDetail.activity')).toBe(1);
    expect(detailVue).toContain("$t('page.issueDetail.activity', { n:");
    expect(detailVue).toContain("$t('page.issueDetail.viewedNTimes', { n:");
    expect(detailVue).not.toContain(".replace('{n}'");
    expect(detailVue).not.toMatch(/父问题：/);
  });

  it('stops hard-coding open as 待处理 in the timeline helper', () => {
    expect(timelineTs).not.toMatch(/open:\s*'待处理'/);
    expect(timelineTs).toMatch(/page\.issueStatus/);
  });
});
```

这些断言在产品尚未换绑时失败（RED），换绑后同一批断言变绿。不要先写「源码仍含中文」再翻成缺失断言。实施时按 design 补全全部键的 `countCalls`、精确字面缺失正则，以及范围外保留项的正向断言。


- [ ] **Step 2: 收窄改写两份既有测试**

`issue-composer-chrome.test.ts` 中要求详情源码仍含「状态」「删除」「取消」的那段（盘点记在约 `:285-289`），改为：详情顶栏「状态」走 `page.issueForm.status`，「删除」走 `common.delete`，评论宿主「取消」走 `common.cancel`；不要再把这三字当作详情必须留下的中文。不要改该文件里对创建页「请输入问题标题」等范围外冻结。不要改写 PR16 提交。

`focus.test.ts` 里用字面量「编辑」找顶栏按钮的断言，改为按 `common.edit` 的当前语言译文或稳定 `data-` / 角色选择器定位。不改 scoped 焦点 CSS，不改其它用例。

- [ ] **Step 3: 跑测试确认 RED**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/issue-detail-chrome.test.ts src/locales/__tests__/issue-composer-chrome.test.ts src/views/issue/detail/focus.test.ts src/utils/formatTimelineAction.test.ts
```

期望：失败原因是缺键、调用次数为 0，或活动流仍返回「待处理」。不要为了变绿先改产品。不要在这一步单独 commit。

### Task 2: 语言包与 schema

**Files:** `zh-cn.ts`、`en-us.ts`、`app.d.ts`。

- [ ] **Step 1: 按 design 第 3 节加入全部新键**

`page.issueDetail`、`page.issueReaction`、`page.issueLink`、`page.issuePr` 与 `App.I18n.Schema` 同步。中文逐字。英文 sentence case，无汉字。已有键（`common.*`、`page.issueForm.status`、`page.issueTrash.restore`、`page.issueComposer.description` / `attachments`、`page.issueList.columns.estimate`、`page.issueList.toolbar.pinToSidebar` / `unpinFromSidebar`、`page.insights.exportCsv`、`page.issueStatus.*`、`page.issuePriority.*`）不改值。精确 base 上没有 `common.save`，外链「保存」用 `page.issueLink.save`，不要新造近义键，也不要为此去加 `common.save`。

- [ ] **Step 2: 再跑 Task 1 的测试**

语言包断言应变绿；详情源码与活动流断言应仍红。

### Task 3: 详情宿主与三个面板、活动流

**Files:** `detail/index.vue`、`IssueReactions.vue`、`IssueLinksPanel.vue`、`IssuePrPanel.vue`、`formatTimelineAction.ts`。

- [ ] **Step 1: 最小改动换绑 `$t`**

按 design 键表替换范围内模板与直接 label。`relationTypeOptions` 与显示映射改读 `page.issueDetail.relation*`，不要改 `constants/issue.ts`。Milestone 选项「无 Milestone」与 placeholder 走新键。顶栏 `:1545`「取消关注 / 关注」走 `page.issueDetail.unwatch` / `watch`；关注者行内 `:2026`「取消」走 `page.issueDetail.unwatchInline`，不要绑到 `unwatch`，也不要用 `common.cancel`。顶栏收藏复用列表 toolbar 的 `pinToSidebar` / `unpinFromSidebar`，接受中文从「取消侧栏收藏」变成「取消侧栏」，不要新造 unpin 键。活动标题与浏览次数用命名参数 `$t`。评论两则 placeholder 作为传入 `MarkdownEditor` 的绑定，不要改编辑器默认占位。

不要改：Agent 弹层 `:2355` 一带标题、说明、正文与「复制指令」；`window.$message` 在本文件内的 toast；附件卡内部（只改卡标题「附件」）；自定义字段编辑器内部（只改侧栏标题）；回收站横幅绑定。

`formatTimelineAction.ts`：删除写死状态/优先级表，改 `$t('page.issueStatus.' + key)` 等；无匹配 key 时的兜底不要退回「待处理」。动词与「未分配」「空」走 `timeline*` 键。函数若在模块顶层调用 `$t`，须能随 locale 变化（不要把译好的字符串缓存成与 locale 无关的常量）。SLA 活动流用 `timelineSlaPaused` / `timelineSlaResumed` 和 metric 键；不要去改 `sla.ts` 前缀。

三个面板按 design 换绑模板与文件内 toast。PR URL 示例保留。

- [ ] **Step 2: 跑测试确认 GREEN**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/issue-detail-chrome.test.ts src/locales/__tests__/issue-composer-chrome.test.ts src/views/issue/detail/focus.test.ts src/utils/formatTimelineAction.test.ts
```

期望 EXIT 0。若只有插值或 i18n plugin 失败，按 Global Constraints 修测试与产品，不要 `.replace`，不要摘掉 `useI18n`。

- [ ] **Step 3: 产品提交（测试与产品一起，恰好白名单内的非 docs 路径）**

```bash
cd "$REPO"
git add frontend/src/locales/langs/zh-cn.ts frontend/src/locales/langs/en-us.ts frontend/src/typings/app.d.ts \
  frontend/src/views/issue/detail/index.vue frontend/src/components/IssueReactions.vue \
  frontend/src/components/issue-links/IssueLinksPanel.vue frontend/src/components/issue-vcs/IssuePrPanel.vue \
  frontend/src/utils/formatTimelineAction.ts frontend/src/utils/formatTimelineAction.test.ts \
  frontend/src/locales/__tests__/issue-detail-chrome.test.ts \
  frontend/src/locales/__tests__/issue-composer-chrome.test.ts \
  frontend/src/views/issue/detail/focus.test.ts
git diff --cached --name-only | sort
# 不得出现白名单外路径，不得含 .env.prod 或 components.d.ts
strace -f -e trace=openat,execve -o "$EVIDENCE/product-commit.strace" \
  git commit -m "fix: localize issue detail chrome for English"
```

父提交必须是文档笔。porcelain 空。strace 再核克隆根 `COMMIT_EDITMSG`。hook 失败则 STOP。

### Task 4: 终轮四门与证据包

- [ ] **Step 1: 再跑四门**

```bash
bash "$EVIDENCE/run-gates.sh" final
```

vitest、build 必须 EXIT 0。tsc/eslint 对照 baseline：路径 + rule/code + severity + message（忽略行号），added 0、removed 0。若 build 再次弄脏 `components.d.ts`，从仓库根还原后再记 tsc/eslint。不要把未还原的脏跑当成终轮。不得写成全绿。

- [ ] **Step 2: 打包证据并停手**

证据包写入 `/workspace/designs/issue-detail-en-chrome-verify/`（实施时再建目录）。必须含：两笔 `git rev-parse` / 父母 / 说明；`git diff --stat` 与完整 `final.diff`；白名单路径列表；四门 baseline 与 final 的 meta/stdout/stderr；两笔 commit 的 strace 与 hook sha256；`git status --porcelain`（空）；不含 `.env.prod` 正文、token、`dist/`、`node_modules`。算出包的 sha256 与字节数后再交审。

到此停止。不 push，不开 PR，不 merge，不部署，不写下一刀。

## 自我核对

- 盘点第一片白名单与范围外项，都能在本 plan 的 Files / 范围约束里找到对应处理或明确排除。
- 决定 A–D、G 已写入 Global Constraints 和 Task 3 禁改清单。E/F 属于第二片，本 plan 不实施。
- 无 TBD / “类似 Task N” / 无代码的“写测试”。`commentPlaceholder` 以 design 与盘点 `:1796` 逐字为准。
- `watch` / `unwatch` / `unwatchInline` 分键；行内「取消」不绑 `unwatch`。unpin 复用后顶栏中文变为「取消侧栏」，测试按复用后的中英文断言。
- `formatTimelineAction.test.ts` 必须接入真实 `@/locales` i18n，可切换 zh-CN / en-US，不要只改期望字符串。
- 插值风格与第 4 刀终审要求一致：`$t(key, { n })`，禁止 `.replace`。
- hook、软链、根目录提交、`components.d.ts` 从仓库根还原，均按第 4 刀已接受做法写死，不是改 hook 正文。
