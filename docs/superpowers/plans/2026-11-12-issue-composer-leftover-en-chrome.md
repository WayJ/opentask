# 创建与编辑剩句英文铬 Implementation Plan

第 8 刀 plan 草稿，送 Yuri 代审；没有审批结论。要等 Yuri「design ok，开写」之后才可实施。本文不是已批准范围。未来 repo 路径：`docs/superpowers/plans/2026-11-12-issue-composer-leftover-en-chrome.md`。本文与 design 是一组。精确 base：`8cfc5fbe49f0541faec3e1975b9e8b9029593c58`（PR19 tip）。不要用 `09413d29` 或更早 SHA 当实施 base。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把创建页剩下的「自定义字段（可选）」和编辑页剩下的「加载中...」接到已有 `page.issueComposer`，不改 19 个旧键，不带上 toast、编辑器种子或列表布尔格。

**Architecture:** 只在已有 `page.issueComposer` 追加 `customFieldsOptional` 与 `loading` 两叶（19 → 21），同步 `App.I18n.Schema`。两页继续用 `@/locales` 的 `$t`。决定 A/B 按 design 推荐案实施。

**Tech Stack:** Vue 3、vue-i18n、Naive UI、Vitest、已有 `$t` 与 `App.I18n.Schema`，无新依赖。

## Global Constraints

- 本轮只交本地草稿。获批口令为「design ok，开写」。决定 A/B 未确认前不得实施。本计划按 design 推荐案写；否决任一条，先改 design 与本 plan，再执行。不要把本刀写成已经批准的范围。不要把第二片（列表布尔格）写成这刀范围，也不要当成已批准。
- 精确 base：`8cfc5fbe49f0541faec3e1975b9e8b9029593c58`（PR19 tip）。`starting_ref` / 检出必须是该全 SHA。不要用 `09413d29` 当实施 base。不改写 PR6–19 已存提交或头。不要 amend、rebase、force。
- 后续仅普通隔离 clone（`.git` 为目录），禁止 worktree。路径为 `/tmp/cursor/opentask-issue-composer-leftover-en-chrome-clone`。不写/reset MAIN `244c93e296a047cf138a880fa24d683b4be8203d` 或 PIN `250fc34af9c64e828aab706567b0430d3d74e452`。不碰已有 pid 服务。本机 `/workspace/opentask` 是无关旧树，不要用。
- 不买额度，不 merge，不部署。未经再授权不 push、不开 PR。本轮不建产品分支、不改产品、不红测、不 commit。获批后才按本 plan 实施。
- 英文页内铬 sentence case。中文逐字保留，包括全角括号和三个 ASCII 点。不要把「加载中...」写成 U+2026，也不要复用通知页「加载中…」。不要把「自定义字段（可选）」拆句再拼。新键只追加进已有 `page.issueComposer`，不要另开 namespace，不要塞进 `page.issueForm`。不要改 19 个旧叶的键值或调用次数。不要把已有 `$t` 改成局部 `t()`。不要无故把 `@/locales` 的 `$t` / `locale` 改成 `useI18n()`。模板属性直接 `:title="$t('page.issueComposer.customFieldsOptional')"` / `:description="$t('page.issueComposer.loading')"`。不要为这两句新造 computed；若不得不写成 computed，第一句必须是 `void locale.value;`（在任何短路之前）。`no-void` 只用 next-line 或紧贴块，禁止文件级 disable。
- 不改 `route.issue_create` / `route.issue_edit`，不改已有 `page.issueComposer` / `page.issueTemplate` / `page.markdownEditor` / `page.issueForm` 的旧键值。schema 与 zh/en 三份一致。
- 四门从 `frontend/` 跑：`pnpm exec vitest run`、`pnpm exec vite build --mode prod`（仓库外 config）、`pnpm exec vue-tsc --noEmit --skipLibCheck`、`pnpm exec eslint .`。对照当次干净 `8cfc5fbe49f0541faec3e1975b9e8b9029593c58` baseline。tsc/eslint 基线非 0 则保持 added 0 / removed 0，忽略行号，用 eslint 汇总行。不得写成全绿，不得借用先前刀子的失败行号当终值。不能写 dual Grok Approve。Vite 只读 config 的 server port 用 **9575**，`strictPort: true`，`open: false`（不要复用 9571 / 9572 / 9573 / 9574）。
- 两笔提交：第一笔仅两份 docs，信息恰好 `docs: specify issue composer leftover English chrome`；第二笔是红测与最小产品一起提交，信息恰好 `fix: localize leftover issue composer chrome for English`。不预安排第三笔。不 amend、不 rebase、不 squash、不用 `--no-verify`。已批 docs 必须从箱上原文 `cmp` 进仓库。建议分支名（获批实施后才建，现在不要建）：`cursor/issue-composer-leftover-en-chrome-4333`。
- hook：只在新 clone 上处理。官方 hook 正文是 `bun sa git-commit-verify`，已核原件 sha256 `46d7a87f731e693d7d81f98f9d9c0286e070f28c8d6aa9a0f88326e8699b5a59`（234 字节），路径 `/workspace/designs/app-shell-en-chrome-approved/official-commit-msg`（也有 `/workspace/designs/issue-list-board-en-chrome-approved/official-commit-msg` 与 `/workspace/designs/issue-composer-en-chrome-verify/official-commit-msg`）。`pnpm install` 后若 simple-git-hooks 把 hook 写到 `frontend/.git/hooks/`，按第 4 刀已接受做法：把官方原件原样拷到 `$REPO/.git/hooks/commit-msg` 且可执行；只删 `frontend/.git/hooks/pre-commit` 与根目录若出现的非 sample pre-commit；不删整个 `frontend/.git`，不动那里的 commit-msg；不重跑 `simple-git-hooks`，不改 `core.hooksPath`（须为空），不用 `SKIP` / `--no-verify`，不另装 verifier，不改写 hook 正文。再在仓库根建 gitignore 相对软链 `ln -s frontend/node_modules node_modules`；不把软链入库，不改 `.gitignore`。只允许在仓库根 `git commit`。EXIT 0 不是 hook 路径证明，须有 strace 显示只读打开克隆根 `.git/COMMIT_EDITMSG`。若 hook 读到 `frontend/.git/COMMIT_EDITMSG` 或同类 ENOENT：原件落盘后立即 STOP，不重试，不改 hook。hook 失败（含缺少 bun / `Script not found "sa"`）也 STOP，不准跳过、不准重试、不准改 hook。
- 不运行 `eslint --fix`。不改 `.env.prod` 正文；实施若要 prod build，只使用 sha256 仍为 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`（1896 字节）的已核 `.env.prod` 副本。缺文件或哈希不符则该门记 EXIT STOP，不用 `.env.example` 顶替，也不把 `.env.example` 拷成 `.env.prod`（即使它碰巧同哈希），也不因此中断红测与其它门禁。不把正文或键值写进证据。缺失已核 `.env.prod` 不得挡住 clone / 红测 / 其它门禁。Yuri 已在本机确认当前没有任何名为 `.env.prod` 的文件哈希等于该锁；这是已记录限制，不是本刀必修项。
- prod build 若弄脏 `frontend/src/typings/components.d.ts` 或 elegant-router 生成文件（`frontend/src/router/elegant/transform.ts`、`frontend/src/typings/elegant-router.d.ts`），必须从**仓库根** `git checkout --` 还原被弄脏的已跟踪路径，再跑 tsc/eslint；打包还原前后 porcelain；不提交这些文件。不要只在 `frontend/` 下 checkout。永远不要还原白名单产品路径（包括 `app.d.ts`）。

### 白名单（恰好 8 路径）

- `docs/superpowers/specs/2026-11-12-issue-composer-leftover-en-chrome-design.md`
- `docs/superpowers/plans/2026-11-12-issue-composer-leftover-en-chrome.md`
- `frontend/src/views/issue/create/index.vue`（只改 `:488` 这一处 `title`）
- `frontend/src/views/issue/edit/index.vue`（只改 `:279` 这一处 `description`）
- `frontend/src/locales/__tests__/issue-composer-chrome.test.ts`（必须改 `:274-275`；可在同文件扩展 `composer` 表与调用次数。保留 `:271-273` 与 `:276-284`）
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/typings/app.d.ts`

实施前若发现上列产品路径在 `8cfc5fbe49f0541faec3e1975b9e8b9029593c58` 上不存在或主入口已改名，STOP 并改 plan，不要扩白名单到范围外文件。`display-prefs.ts`、`groupIssuesBy.ts`、`list/index.vue`、`detail/index.vue`、`IssueCustomFieldsEditor`、`IssueTemplateForm.vue`、`MarkdownEditor.vue`、`issue-list-board-chrome.test.ts`、`app-shell-chrome.test.ts`、设置页不在白名单。

---

### Task 0: 获批后隔离、当次基线、docs-only commit

**Files:** 仅上述两份 docs。

**Interfaces:**

- Consumes: 精确 `8cfc5fbe49f0541faec3e1975b9e8b9029593c58` 与已批的两份本地文件。
- Produces: 普通 clone 上的文档提交，以及仓库外 baseline 原件。

- [ ] **Step 1: 在实施环境建全新普通 clone**

下面的命令等获批后再执行。先确认目标不存在。不写/reset main `244c93e2` 或 pin `250fc34a`。不要用 `/workspace/opentask`。不要 worktree。

```bash
export TZ=Asia/Shanghai
export REPO=/tmp/cursor/opentask-issue-composer-leftover-en-chrome-clone
export EVIDENCE=/tmp/cursor/opentask-readonly/issue-composer-leftover-en-chrome-logs
export OFFICIAL_HOOK=/workspace/designs/app-shell-en-chrome-approved/official-commit-msg
export APPROVED_DESIGN=/workspace/designs/issue-composer-leftover-en-chrome-spec/2026-11-12-issue-composer-leftover-en-chrome-design.md
export APPROVED_PLAN=/workspace/designs/issue-composer-leftover-en-chrome-spec/2026-11-12-issue-composer-leftover-en-chrome.md
test ! -e "$REPO" || exit 1
test -f "$OFFICIAL_HOOK" || exit 1
test "$(sha256sum "$OFFICIAL_HOOK" | awk '{print $1}')" = 46d7a87f731e693d7d81f98f9d9c0286e070f28c8d6aa9a0f88326e8699b5a59 || exit 1
test "$(wc -c < "$OFFICIAL_HOOK" | tr -d ' ')" = 234 || exit 1
mkdir -p "$EVIDENCE"
git clone https://github.com/WayJ/opentask.git "$REPO"
cd "$REPO"
git switch --detach 8cfc5fbe49f0541faec3e1975b9e8b9029593c58
test -d .git || exit 1
test "$(git rev-parse HEAD)" = 8cfc5fbe49f0541faec3e1975b9e8b9029593c58 || exit 1
test -z "$(git status --porcelain)" || exit 1
test -z "$(git config --get core.hooksPath)" || exit 1
git switch -c cursor/issue-composer-leftover-en-chrome-4333
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
# .env.prod 不是开写前置。有已核副本才拷；缺失或哈希不符则不拷、不用 .env.example，prod build 记 EXIT STOP，其它任务继续
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

任一项失败即 STOP，不改 hook 正文，不另装 verifier。`.env.prod` 只从已核来源拷贝，拷贝后立刻核 sha256 仍是 `b686d37a…`（1896）。缺原件或哈希不符时不拷贝、不用 `.env.example` 顶替（即使它碰巧同一哈希），prod build 记 EXIT STOP，作为已记录限制，不是本刀必修复项，也不阻塞后续红测与其它门禁。不记录正文或键值。依赖准备好之后再确认除 gitignored `.env.prod` 外 tracked diff 为空。已有服务端口不动。Vite 只读 config 的 server port 用 `9575`，`strictPort: true`，`open: false`。

若审批后另有已批副本，改用那份路径再 `cmp`。拿不到已批原件就 STOP，不从未批草稿复刻。

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
    server: { ...(resolved.server || {}), open: false, host: '127.0.0.1', port: 9575, strictPort: true }
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
# 若 build 弄脏 components.d.ts 或 elegant-router 生成文件，从仓库根还原后再跑 tsc/eslint
cd "$REPO"
git status --porcelain > "$EVIDENCE/$phase/porcelain-after-build.txt"
# 只还原 typings / elegant-router 生成文件；不要还原白名单产品路径，不要 add
while IFS= read -r path; do
  case "$path" in
    frontend/src/locales/*|frontend/src/views/issue/create/*|frontend/src/views/issue/edit/*|frontend/src/typings/app.d.ts)
      ;;
    frontend/src/typings/*|frontend/src/router/elegant/*)
      git checkout -- "$path"
      ;;
  esac
done < <(git diff --name-only -- frontend)
cd "$REPO/frontend"
run tsc pnpm exec vue-tsc --noEmit --skipLibCheck
run eslint pnpm exec eslint .
SH
chmod +x "$EVIDENCE/run-gates.sh"
bash "$EVIDENCE/run-gates.sh" baseline
```

baseline HEAD 必须仍是精确 base，tracked diff 空（还原生成文件之后；gitignored `.env.prod` 除外）。vitest 必须 EXIT 0 才继续。build 仅在已核 `.env.prod` 已就位时必须 EXIT 0；否则记录 EXIT STOP 为限制并继续，不得用 `.env.example` 换通。tsc / eslint 非 0 则把诊断原样留下，不修范围外问题。记录 eslint 摘要行（以当次 baseline 为准）。build 前后比较 tracked diff 和生成文件 hash。意外改动就 STOP。

- [ ] **Step 3: 文档先行，恰好两文件提交**

把已批文件逐字节放入 docs，`cmp` 前后 sha256。拿不到已批原件就 STOP，不从未批草稿复刻。只在仓库根提交。

```bash
cd "$REPO"
mkdir -p docs/superpowers/specs docs/superpowers/plans
cp "$APPROVED_DESIGN" docs/superpowers/specs/2026-11-12-issue-composer-leftover-en-chrome-design.md
cp "$APPROVED_PLAN" docs/superpowers/plans/2026-11-12-issue-composer-leftover-en-chrome.md
cmp "$APPROVED_DESIGN" docs/superpowers/specs/2026-11-12-issue-composer-leftover-en-chrome-design.md
cmp "$APPROVED_PLAN" docs/superpowers/plans/2026-11-12-issue-composer-leftover-en-chrome.md
git add docs/superpowers/specs/2026-11-12-issue-composer-leftover-en-chrome-design.md docs/superpowers/plans/2026-11-12-issue-composer-leftover-en-chrome.md
test "$(git diff --cached --name-only | wc -l)" = 2 || exit 1
git diff --cached --name-only | sort > "$EVIDENCE/docs-cached-paths.txt"
# 只从仓库根 commit；留下 strace
strace -f -e trace=openat,execve -o "$EVIDENCE/docs-commit.strace" git commit -m "docs: specify issue composer leftover English chrome"
test "$(git rev-parse HEAD^)" = 8cfc5fbe49f0541faec3e1975b9e8b9029593c58 || exit 1
test -z "$(git status --porcelain)" || exit 1
```

`git diff --cached --name-only` 必须恰好是这两个路径。hook 哈希提交后仍须是 `46d7a87f…`。strace 必须出现克隆根 `.git/COMMIT_EDITMSG` 以及 hook / `bun sa git-commit-verify`。EXIT 0 本身不够。遇到 hook 失败或 `COMMIT_EDITMSG` ENOENT 立即 STOP，不重试。

### Task 1: 先红测（只改测试，不改产品，不另强制 RED commit）

**Files:**

- Modify: `frontend/src/locales/__tests__/issue-composer-chrome.test.ts`

**Interfaces:**

- Consumes: design 第 3 节两叶，以及该测试里已有的 `composer` / `createCalls` / `editCalls` / `leafKeys` / `schemaLeaves` / `countCalls`。
- Produces: 红测；产品尚未改时必须失败。不另强制 RED commit。

- [ ] **Step 1: 只改同一测试文件，覆盖 21 叶与两处冻结**

不要新开测试文件。不要改 `:271-273` 与 `:276-284`。不要削弱其它已有冻结（旧 19 叶键值与次数、`page.issueTemplate` / `page.markdownEditor`、范围外 toast 与 `insertText` 种子）。

在已有 `composer` 数组末尾、`exitKeep` 之后追加两行，不要重排或改写旧 19 行：

```ts
  ['customFieldsOptional', '自定义字段（可选）', 'Custom fields (optional)'],
  ['loading', '加载中...', 'Loading...']
```

注意「加载中...」是三个 ASCII 点，不要写成 `加载中…`。

在已有 `createCalls` 增加 `customFieldsOptional: 1`（不要改其它次数）。在已有 `editCalls` 增加 `loading: 1`（不要改其它次数）。若该测试对其它「只在一页出现」的键有显式 0 次断言，照同样模式补上：

```ts
expect(countCalls(edit, 'page.issueComposer', 'customFieldsOptional')).toBe(0);
expect(countCalls(create, 'page.issueComposer', 'loading')).toBe(0);
```

必须改 `:274-275`。盘点在 tip 上这两行是：

```ts
    expect(create).toContain('自定义字段（可选）');
    expect(edit).toContain('加载中...');
```

改成带周围 markup 的精确断言，例如：

```ts
    expect(create).toContain("$t('page.issueComposer.customFieldsOptional')");
    expect(create).not.toContain('title="自定义字段（可选）"');
    expect(edit).toContain("$t('page.issueComposer.loading')");
    expect(edit).not.toContain('description="加载中..."');
```

禁止宽泛的 `not.toContain('自定义字段')` 或 `not.toContain('加载中')`。不要改测试名以外的范围外冻结块结构；`:271-273` 仍须 `toContain('请输入问题标题')` / `'问题创建成功'` / `'问题创建失败'`，`:276-284` 仍须含 `insertText('**', '**', '粗体文本')` 到 `insertText('\\n- [ ] ', '', '待办事项')`。

不要改产品文件。不要提交。

- [ ] **Step 2: 跑该测试，确认 RED**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/issue-composer-chrome.test.ts
```

期望：非 0。失败应来自新叶尚未进入语言包 / schema，以及两处模板仍是写死中文。若测试意外全绿，STOP 并改 plan，不要先改产品凑绿。若失败来自被改动的 `:271-273` / `:276-284` 或其它范围外冻结，STOP，先把那些断言恢复。把这次输出落入 `$EVIDENCE/task1-red/`。

### Task 2: 语言包与 schema

**Files:**

- Modify: `frontend/src/locales/langs/zh-cn.ts`
- Modify: `frontend/src/locales/langs/en-us.ts`
- Modify: `frontend/src/typings/app.d.ts`

**Interfaces:**

- Consumes: design 第 3 节两叶。
- Produces: `page.issueComposer` 从 19 叶变为 21 叶；旧叶原值不动。

- [ ] **Step 1: 只追加两叶，三份一致**

在已有 `page.issueComposer` 对象末尾追加，不要重写 19 个旧键，不要另开 namespace，不要写入 `page.issueForm`。

`zh-cn.ts`：

```ts
customFieldsOptional: '自定义字段（可选）',
loading: '加载中...'
```

`en-us.ts`：

```ts
customFieldsOptional: 'Custom fields (optional)',
loading: 'Loading...'
```

`app.d.ts` 的 `issueComposer` 块追加：

```ts
customFieldsOptional: string;
loading: string;
```

中文必须含全角括号和三个 ASCII 点。英文必须是 sentence case，括号为 ASCII，省略号为三个 ASCII 点。`en-us.ts` 不得出现汉字。walker / `schemaLeaves('issueComposer')` 扩到 21 叶时不得改旧叶。

- [ ] **Step 2: 再跑 Task 1 的测试（此时仍应有红，因模板未改）**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/issue-composer-chrome.test.ts
```

语言包与 schema 断言可以通过；对 `title="自定义字段（可选）"` / `description="加载中..."` 以及新键调用次数的断言仍应失败。不要在这一步改模板。不要提交。

### Task 3: 两处模板属性

**Files:**

- Modify: `frontend/src/views/issue/create/index.vue`（只改 `:488` 这一处 `title`）
- Modify: `frontend/src/views/issue/edit/index.vue`（只改 `:279` 这一处 `description`）

**Interfaces:**

- Consumes: Task 2 的两叶，以及两页已有的 `@/locales` `$t` 导入。
- Produces: 两处写死属性改为 `$t`。

- [ ] **Step 1: 只改这两处属性**

创建页 `:488` 把 `title="自定义字段（可选）"` 改成：

```vue
:title="$t('page.issueComposer.customFieldsOptional')"
```

编辑页 `:279` 把 `description="加载中..."` 改成：

```vue
:description="$t('page.issueComposer.loading')"
```

继续用已有 `$t`，不要改成 `useI18n()`，不要把既有 `$t` 改成局部 `t()`。不要为这两句新造 computed。不要改同一文件里的 toast、模板字段兜底「标题」「描述」，或其它属性。

- [ ] **Step 2: 跑测试确认转为绿，并核既有冻结**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/issue-composer-chrome.test.ts src/locales/__tests__/issue-list-board-chrome.test.ts src/locales/__tests__/app-shell-chrome.test.ts
```

期望：`issue-composer-chrome.test.ts` EXIT 0；`:271-273` 与 `:276-284` 仍在且通过；`issue-list-board-chrome.test.ts` 与 `app-shell-chrome.test.ts` EXIT 0，其常量「待办」「低」「是/否」以及壳层冻结未被改弱。不要改后两份测试。若测试因其它范围外原因失败，STOP 并改 plan，不要顺手扩范围。

- [ ] **Step 3: 产品提交（测试与产品一起，恰好白名单内的 6 个非 docs 路径）**

```bash
cd "$REPO"
git add frontend/src/locales/langs/zh-cn.ts frontend/src/locales/langs/en-us.ts frontend/src/typings/app.d.ts \
  frontend/src/views/issue/create/index.vue frontend/src/views/issue/edit/index.vue \
  frontend/src/locales/__tests__/issue-composer-chrome.test.ts
git diff --cached --name-only | sort
# 不得出现白名单外路径，不得含 .env.prod、components.d.ts、elegant-router 生成文件、list/index.vue、display-prefs.ts
allowed='frontend/src/locales/__tests__/issue-composer-chrome.test.ts
frontend/src/locales/langs/en-us.ts
frontend/src/locales/langs/zh-cn.ts
frontend/src/typings/app.d.ts
frontend/src/views/issue/create/index.vue
frontend/src/views/issue/edit/index.vue'
while IFS= read -r path; do
  printf '%s\n' "$allowed" | grep -Fxq "$path" || exit 1
done < <(git diff --cached --name-only)
test "$(git diff --cached --name-only | wc -l)" = 6 || exit 1
strace -f -e trace=openat,execve -o "$EVIDENCE/product-commit.strace" \
  git commit -m "fix: localize leftover issue composer chrome for English"
```

父提交必须是文档笔。porcelain 必须为空（`.env.prod` 须已被 gitignore，不得出现在 porcelain 或 index）。strace 再核克隆根 `COMMIT_EDITMSG`。hook 失败则 STOP。

### Task 4: 终轮四门与证据包

- [ ] **Step 1: 再跑四门**

```bash
bash "$EVIDENCE/run-gates.sh" final
```

vitest 必须 EXIT 0。build 仅在已核 `.env.prod` 已就位时必须 EXIT 0；否则对照 baseline 同记 EXIT STOP，不得写成全绿或换用 `.env.example`。tsc/eslint 对照 baseline：路径 + rule/code + severity + message（忽略行号），added 0、removed 0。若 build 再次弄脏 `components.d.ts` 或 elegant-router 生成文件，从仓库根还原后再记 tsc/eslint。不要把未还原的脏跑当成终轮。不得写成全绿。

- [ ] **Step 2: 打包证据并停手**

证据包写入 `/workspace/designs/issue-composer-leftover-en-chrome-verify/`（实施时再建目录）。必须含：每一笔提交的 `git rev-parse` / 第一父提交 / 说明；相对精确 base 的 `git diff --name-only --no-ext-diff`、`--stat` 与完整 `final.diff`；**每一笔提交相对其第一父提交**的 name-only、diffstat 与完整 diff（不得只用 `final.diff` 代替分笔）；白名单路径列表；四门 baseline 与 final 的 meta/stdout/stderr；每一笔 commit 的 strace 与 hook sha256；两份 docs 与已批原文的 `cmp` / sha256；`git status --porcelain`（空）；不含 `.env.prod` 正文、token、`dist/`、`node_modules`。若后来不得不多出修订笔，每一笔同样要有相对其第一父提交的这三份，不要 amend 前序提交来补证据。算出包的 sha256 与字节数后再交审。

```bash
BASE=8cfc5fbe49f0541faec3e1975b9e8b9029593c58
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
test "$(git log -1 --format=%s "$first")" = "docs: specify issue composer leftover English chrome" || exit 1
test "$(git rev-parse "${first}^")" = "$BASE" || exit 1
printf '%s\n' \
  docs/superpowers/plans/2026-11-12-issue-composer-leftover-en-chrome.md \
  docs/superpowers/specs/2026-11-12-issue-composer-leftover-en-chrome-design.md \
  | sort > "$EVIDENCE/commit1.expected-paths.txt"
sort "$EVIDENCE/commit1.name-only.txt" | cmp - "$EVIDENCE/commit1.expected-paths.txt"
second=$(git rev-list --reverse "$BASE"..HEAD | tail -n1)
test "$(git log -1 --format=%s "$second")" = "fix: localize leftover issue composer chrome for English" || exit 1
test "$(git rev-parse "${second}^")" = "$first" || exit 1
test "$(git diff --name-only --no-ext-diff "${second}^" "$second" | wc -l)" = 6 || exit 1
cmp "$APPROVED_DESIGN" "$REPO/docs/superpowers/specs/2026-11-12-issue-composer-leftover-en-chrome-design.md"
cmp "$APPROVED_PLAN" "$REPO/docs/superpowers/plans/2026-11-12-issue-composer-leftover-en-chrome.md"
```

上面 `cmp` 失败即 STOP，不要改第一笔去凑。第一笔的分笔 diff 须恰好是那两份 docs，不得混入产品或测试路径。第二笔须恰好是白名单里的 6 个非 docs 路径。`final.diff` 仍要保留，但不能代替分笔。

到此停止。不 push，不开 PR，不 merge，不部署，不写下一刀。也不要中途通报 Way 或 Yuri。

## 自我核对

- 盘点第 3 节与第 6 节第一片的白名单与范围外项，都能在本 plan 的 Files / 范围约束里找到对应处理或明确排除。第二片列表布尔格未列入实施任务，也未写成已批准。第 4–7 刀未重开。
- 决定 A/B 已写入 Global Constraints 和 Task 2 / Task 3，并按推荐案锁定。文案表与 design 第 3 节一致，含全角括号与三个 ASCII 点，明确排除 U+2026 与拆句。
- 必须改 `issue-composer-chrome.test.ts:274-275`，保留 `:271-273` 与 `:276-284`。为覆盖 21 叶与调用次数，只在同一文件扩展已有表，不新开测试文件。无 TBD / “类似 Task N”。
- hook sha256 `46d7a87f…` / 234、只删 pre-commit、gitignore 相对软链、只从仓库根 commit、strace 读克隆根 `COMMIT_EDITMSG`、`components.d.ts` / elegant-router 生成文件从仓库根还原、Vite 端口 `9575`，均已写死。常规隔离克隆，禁止 worktree。`.env.prod` 缺失则 prod build 记 EXIT STOP，不用 `.env.example`。
- 证据包必须含每一笔的 name-only / diffstat / 完整 diff，加上相对 base 的 `final.diff`；第一笔分笔须恰好是两份 docs，第二笔恰好 6 个产品路径。不得只用 `final.diff`。不得写成全绿或 dual Grok Approve。未经后续授权不 push / 开 PR / merge / 部署。
