# 应用壳层英文铬 Implementation Plan

第 7 刀 plan 草稿，送 Yuri 代审；没有审批结论。要等 Yuri「design ok，开写」之后才可实施。本文不是已批准范围。未来 repo 路径：`docs/superpowers/plans/2026-11-12-app-shell-en-chrome.md`。本文与 design 是一组。精确 base：`09413d292c71973d4af5fc7350be88d9d55cdc2a`（PR18 tip）。不要用 `6b6ad3b4` 当实施 base。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把每页壳层上仍写死的收藏区、实时连接 title、工作区切换弹层、焦点问题快捷键浮层（含 toast）和命令面板「设置估点…」接到 zh/en，不改侧栏菜单、第 6 刀列表看板铬、创建/编辑剩句或常量源串。

**Architecture:** 在已有 `page.shell` 下新增 `favorites`、`realtime`、`workspaceSwitcher`、`hotkeyPicker` 分组，并把 `estimateTitle` 补进已有 `common.commandPalette`，同步 `App.I18n.Schema`。各文件继续用 `@/locales` 的 `$t` / `locale`。已有整句优先复用。快捷键状态/优先级 options 走 `useLabelTable` / `lookupLabel`。决定 A/B/C 按 design 推荐案实施。

**Tech Stack:** Vue 3、vue-i18n、Naive UI、Vitest、Vue Test Utils、已有 `$t` 与 `App.I18n.Schema`，无新依赖。

## Global Constraints

- 本轮只交本地草稿。获批口令为「design ok，开写」。决定 A/B/C 未确认前不得实施。本计划按 design 推荐案写；否决任一条，先改 design 与本 plan，再执行。不要把壳层写成已经批准的范围。
- 精确 base：`09413d292c71973d4af5fc7350be88d9d55cdc2a`（PR18 tip）。`starting_ref` / 检出必须是 `09413d29`。不要用 `6b6ad3b4` 当实施 base。不改写 PR6–18 已存提交或头。
- 后续仅普通隔离 clone（`.git` 为目录），不用 worktree。路径为 `/tmp/cursor/opentask-app-shell-en-chrome-clone`。不写/reset MAIN `244c93e296a047cf138a880fa24d683b4be8203d` 或 PIN `250fc34af9c64e828aab706567b0430d3d74e452`。不碰已有 pid 服务。不回复 PR18 的 `bc-411e6f0f` 或其它已绑 PR 的代理。
- 不买额度，不 merge，不部署。未经再授权不 push、不开 PR。本轮不建产品分支、不改产品、不 TDD、不 commit。获批后才按本 plan 实施。
- 英文页内铬 sentence case。新键进入 `App.I18n.Schema`。页面与组件用 `$t`。不要把已有 `$t` 改成局部 `t()`。不要改 `constants/issue.ts`。不要无故把 `@/locales` 的 `$t` / `locale` 改成 `useI18n()`。
- 脚本里调用 `$t` 的 computed，以及会缓存文案的函数（含快捷键 `title`、状态/优先级 options computed，以及命令面板写入 `palette.setSources` 的 `watchEffect`），第一句必须是 `void locale.value;`，位于任何短路之前。`no-void` 只用 `eslint-disable-next-line` 盖住这一句，或紧贴该 computed / 函数的 disable/enable 块。禁止文件级 `eslint-disable no-void`。
- 命名参数插值必须写成 `$t('page.shell.hotkeyPicker.points', { n: pts })`，禁止 `.replace('{n}', …)` 或同类字符串替换迁就测试。
- 测试统计 `$t('…')` 调用点。字面缺失用精确整句或带周围 markup 的正则。禁止 `not.toContain('取消')`、`('状态')`、`('重置')`、`('应用')`、`('确认')`、`('创建')`、`('收藏')`。
- Vue Test Utils stub 同时覆盖 naive-ui 真实 name 与 `N*` 别名。不为测试修改产品组件的 `name` 或 `defineOptions`。有 `useI18n()` 的挂载必须带 `plugins: [i18n]`（已有 pinia 则 `[pinia, i18n]`），不要删 `useI18n`。本刀五个布局文件优先继续用从 `@/locales` 导入的 `$t` / `locale`，不要无故改成 `useI18n()`。
- 四门从 `frontend/` 跑：`pnpm exec vitest run`、`pnpm exec vite build --mode prod`（仓库外 config）、`pnpm exec vue-tsc --noEmit --skipLibCheck`、`pnpm exec eslint .`。对照当次干净 `09413d29` baseline。tsc/eslint 基线非 0 则保持 added 0 / removed 0，不得写成全绿，不得借用 PR15–PR18 或第 6 刀的 95/551、✖ 868 等失败行号当终值。不能写 dual Grok Approve。Vite 只读 config 的 server port 用 `9574`，`strictPort: true`，`open: false`（不要沿用旧片的 9571 / 9572 / 9573）。
- 两笔提交：第一笔仅两份 docs，信息恰好 `docs: specify app shell English chrome`；第二笔是 RED 测试与最小 GREEN 产品一起提交，信息恰好 `fix: localize app shell chrome for English`。不预安排第三笔。不 amend、不 rebase、不 squash、不用 `--no-verify`。已批 docs 必须从箱上原文 `cmp` 进仓库。
- hook：只在新 clone 上处理。官方 hook 正文是 `bun sa git-commit-verify`，已核原件 sha256 `46d7a87f731e693d7d81f98f9d9c0286e070f28c8d6aa9a0f88326e8699b5a59`（234 字节），路径 `/workspace/designs/issue-list-board-en-chrome-approved/official-commit-msg`（也有 `/workspace/designs/issue-composer-en-chrome-verify/official-commit-msg`）。`pnpm install` 后若 simple-git-hooks 把 hook 写到 `frontend/.git/hooks/`，按第 4 刀已接受做法：把官方原件原样拷到 `$REPO/.git/hooks/commit-msg` 且可执行；只删 `frontend/.git/hooks/pre-commit` 与根目录若出现的非 sample pre-commit；不删整个 `frontend/.git`，不动那里的 commit-msg；不重跑 `simple-git-hooks`，不改 `core.hooksPath`，不用 `SKIP` / `--no-verify`，不另装 verifier，不改写 hook 正文。再在仓库根建 gitignore 相对软链 `ln -s frontend/node_modules node_modules`；不把软链入库，不改 `.gitignore`。只允许在仓库根 `git commit`。EXIT 0 不是 hook 路径证明，须有 strace 显示只读打开克隆根 `.git/COMMIT_EDITMSG`。若 hook 读到 `frontend/.git/COMMIT_EDITMSG` 或同类 ENOENT：原件落盘后立即 STOP，不重试，不改 hook。hook 失败（含缺少 bun / `Script not found "sa"`）也 STOP，不准跳过、不准重试、不准改 hook。
- 不运行 `eslint --fix`。不改 `.env.prod` 正文；实施若要 prod build，只使用 sha256 仍为 `b686d37a6c470d295b5cf4165eea1c3a6ca3a43fcc08d0155b5a27634d2d2ce7`（1896 字节）的已核 `.env.prod` 副本。缺文件或哈希不符则该门记 EXIT STOP（与 PR17/PR18 相同限制，不是本刀开写或必修复项），不用 `.env.example` 顶替，也不把 `.env.example` 拷成 `.env.prod`（即使它碰巧同哈希），也不因此中断 TDD 与其它门禁。不把正文或键值写进证据。缺失已核 `.env.prod` 不得挡住 clone / TDD / 其它门禁。
- prod build 若弄脏 `frontend/src/typings/components.d.ts` 或 elegant-router 生成文件，必须从**仓库根** `git checkout --` 还原被弄脏的已跟踪路径，再跑 tsc/eslint；打包还原前后 porcelain；不提交这些文件。不要只在 `frontend/` 下 checkout。
- 决定 A：弹层标题「创建工作区」走新键 `page.shell.workspaceSwitcher.createTitle`，禁止复用 `route.workspace-onboarding`；占位「工作区」走新键 `page.shell.workspaceSwitcher.placeholder`，禁止复用 `route.workspace`。决定 B：按钮「创建」复用 `page.issueDetail.create`，禁止把该键用在标题「创建工作区」上。决定 C：快捷键状态/优先级 options 走 `useLabelTable` / `lookupLabel`，不改 `constants/issue.ts`。本刀不实施创建/编辑剩余句或列表「是/否」，不重开第 6 刀。
- 本刀不改 `utils/favorites.ts`、`constants/issue.ts`、`utils/command-palette.ts`、`detail/index.vue`、`views/issue/list/index.vue`、`groupIssuesBy.ts`、`display-prefs.ts`、`MarkdownEditor.vue`、`AttachmentList`、自定义字段内部、设置页、大模块、`noneCycle` 合并、`issue-list-board-chrome.test.ts`、`issue-composer-chrome.test.ts`。

### 白名单（11 路径）

- `docs/superpowers/specs/2026-11-12-app-shell-en-chrome-design.md`
- `docs/superpowers/plans/2026-11-12-app-shell-en-chrome.md`
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/typings/app.d.ts`
- `frontend/src/layouts/modules/global-sider/FavoritesNav.vue`
- `frontend/src/layouts/modules/global-header/index.vue`（只改实时连接 `title`）
- `frontend/src/layouts/modules/global-header/components/workspace-switcher.vue`
- `frontend/src/layouts/modules/global-search/issue-hotkey-picker-host.vue`
- `frontend/src/layouts/modules/global-search/command-palette-host.vue`（只改 `estimateTitle`，并给会缓存文案的 `watchEffect` 补 `void locale.value`）
- `frontend/src/locales/__tests__/app-shell-chrome.test.ts`（新建）

实施前若发现上列产品路径在 `09413d29` 上不存在或主入口已改名，STOP 并改 plan，不要扩白名单到范围外文件。`utils/favorites.ts`、`constants/issue.ts`、`utils/command-palette.ts`、`detail/index.vue`、`views/issue/list/index.vue`、`display-prefs.ts`、`groupIssuesBy.ts`、`issue-list-board-chrome.test.ts`、`issue-composer-chrome.test.ts` 不在白名单。

---

### Task 0: 获批后隔离、当次基线、docs-only commit

**Files:** 仅上述两份 docs。

**Interfaces:**

- Consumes: 精确 `09413d292c71973d4af5fc7350be88d9d55cdc2a` 与已批的两份本地文件。
- Produces: 普通 clone 上的文档提交，以及仓库外 baseline 原件。

- [ ] **Step 1: 在实施环境建全新普通 clone**

下面的命令等获批后再执行。先确认目标不存在。不写/reset main `244c93e2` 或 pin `250fc34a`。不回复 PR18 的 `bc-411e6f0f`。

```bash
export TZ=Asia/Shanghai
export REPO=/tmp/cursor/opentask-app-shell-en-chrome-clone
export EVIDENCE=/tmp/cursor/opentask-readonly/app-shell-en-chrome-logs
export OFFICIAL_HOOK=/workspace/designs/issue-list-board-en-chrome-approved/official-commit-msg
export APPROVED_DESIGN=/workspace/designs/app-shell-en-chrome-spec/2026-11-12-app-shell-en-chrome-design.md
export APPROVED_PLAN=/workspace/designs/app-shell-en-chrome-spec/2026-11-12-app-shell-en-chrome.md
test ! -e "$REPO" || exit 1
test -f "$OFFICIAL_HOOK" || exit 1
test "$(sha256sum "$OFFICIAL_HOOK" | awk '{print $1}')" = 46d7a87f731e693d7d81f98f9d9c0286e070f28c8d6aa9a0f88326e8699b5a59 || exit 1
mkdir -p "$EVIDENCE"
git clone https://github.com/WayJ/opentask.git "$REPO"
cd "$REPO"
git switch --detach 09413d292c71973d4af5fc7350be88d9d55cdc2a
test -d .git || exit 1
test "$(git rev-parse HEAD)" = 09413d292c71973d4af5fc7350be88d9d55cdc2a || exit 1
test -z "$(git status --porcelain)" || exit 1
test -z "$(git config --get core.hooksPath)" || exit 1
git switch -c cursor/app-shell-en-chrome-4333
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

任一项失败即 STOP，不改 hook 正文，不另装 verifier。`.env.prod` 只从已核来源拷贝，拷贝后立刻核 sha256 仍是 `b686d37a…`（1896）。缺原件或哈希不符时不拷贝、不用 `.env.example` 顶替（即使它碰巧同一哈希），prod build 记 EXIT STOP，作为与 PR17/PR18 相同的已记录限制，不是本刀必修复项，也不阻塞后续 TDD 与其它门禁。不记录正文或键值。依赖准备好之后再确认除 gitignored `.env.prod` 外 tracked diff 为空。已有服务端口不动。Vite 只读 config 的 server port 用 `9574`，`strictPort: true`，`open: false`。

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
    server: { ...(resolved.server || {}), open: false, host: '127.0.0.1', port: 9574, strictPort: true }
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
    frontend/src/locales/*|frontend/src/layouts/*|frontend/src/typings/app.d.ts)
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

baseline HEAD 必须仍是精确 base，tracked diff 空（还原生成文件之后；gitignored `.env.prod` 除外）。vitest 必须 EXIT 0 才继续。build 仅在已核 `.env.prod` 已就位时必须 EXIT 0；否则记录 EXIT STOP 为限制并继续，不得用 `.env.example` 换通。tsc / eslint 非 0 则把诊断原样留下，不修范围外问题。记录 eslint 摘要行（以当次 baseline 为准，不要把第 6 刀的 95/551 或 ✖ 868 写成终值）。build 前后比较 tracked diff 和生成文件 hash。意外改动就 STOP。

- [ ] **Step 3: 文档先行，恰好两文件提交**

把已批文件逐字节放入 docs，`cmp` 前后 sha256。拿不到已批原件就 STOP，不从未批草稿复刻。只在仓库根提交。

```bash
cd "$REPO"
mkdir -p docs/superpowers/specs docs/superpowers/plans
cp "$APPROVED_DESIGN" docs/superpowers/specs/2026-11-12-app-shell-en-chrome-design.md
cp "$APPROVED_PLAN" docs/superpowers/plans/2026-11-12-app-shell-en-chrome.md
cmp "$APPROVED_DESIGN" docs/superpowers/specs/2026-11-12-app-shell-en-chrome-design.md
cmp "$APPROVED_PLAN" docs/superpowers/plans/2026-11-12-app-shell-en-chrome.md
git add docs/superpowers/specs/2026-11-12-app-shell-en-chrome-design.md docs/superpowers/plans/2026-11-12-app-shell-en-chrome.md
test "$(git diff --cached --name-only | wc -l)" = 2 || exit 1
git diff --cached --name-only | sort > "$EVIDENCE/docs-cached-paths.txt"
# 只从仓库根 commit；留下 strace
strace -f -e trace=openat,execve -o "$EVIDENCE/docs-commit.strace" git commit -m "docs: specify app shell English chrome"
test "$(git rev-parse HEAD^)" = 09413d292c71973d4af5fc7350be88d9d55cdc2a || exit 1
test -z "$(git status --porcelain)" || exit 1
```

`git diff --cached --name-only` 必须恰好是这两个路径。hook 哈希提交后仍须是 `46d7a87f…`。strace 必须出现克隆根 `.git/COMMIT_EDITMSG` 以及 hook / `bun sa git-commit-verify`。EXIT 0 本身不够。遇到 hook 失败或 `COMMIT_EDITMSG` ENOENT 立即 STOP，不重试。

### Task 1: tests-only RED（不改产品，不另强制 RED commit）

**Files:**

- Create: `frontend/src/locales/__tests__/app-shell-chrome.test.ts`

**Interfaces:**

- Consumes: design 第 3 节键表。
- Produces: 红测；产品尚未改时必须失败。

- [ ] **Step 1: 写壳层铬测试**

测试文件安装真实 `@/locales` i18n（`zh-CN` / `en-US`），不要自己造一套残缺 messages。模式对齐 `issue-list-board-chrome.test.ts`：统计 `$t('精确键')` 调用次数；用正则或带周围 markup 的整句断言源码不再出现本刀范围内的写死中文；禁止宽泛 `not.toContain('确认')` 等。

把下面文件原样写入 `frontend/src/locales/__tests__/app-shell-chrome.test.ts`。不要删断言，不要改成“同 design 第 3 节”。

```ts
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
    expect(switcherVue).not.toContain('$t(\'route.workspace\')');
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
      expect($t('page.shell.hotkeyPicker.noLabels')).toBe(
        'No labels yet. Create them on the Labels settings page.'
      );
      expect($t('common.commandPalette.estimateTitle')).toBe('Set estimate\u2026');
      expect($t('page.issueStatus.open')).not.toBe('待办');
      expect($t('page.issuePriority.low')).not.toBe('低');
    } finally {
      setLocale(previous);
    }
  });
});
```

注意：上面 `issueKeyPlaceholder` 的中英文都必须含 en dash `2–6`（U+2013），与 tip 源串和 design 一致。英文失败句的弯引号用 `\u2019`。`estimateTitle` 的省略号用 `\u2026`。标签确认按钮只靠 `countCalls(hotkeyVue, 'common.confirm')` 为 1 钉死，并与 `confirmAssign` 各用各的键。

- [ ] **Step 2: 跑测试确认 RED**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/app-shell-chrome.test.ts src/locales/__tests__/issue-list-board-chrome.test.ts src/locales/__tests__/issue-composer-chrome.test.ts
```

期望：新测试失败原因是缺键、调用次数为 0，或范围内字面仍在。`issue-list-board-chrome.test.ts` 与 `issue-composer-chrome.test.ts` 在尚未改产品时应仍通过（「待办」「低」「是/否」「自定义字段（可选）」「加载中...」仍被冻住）。不要为了变绿先改产品。不要在这一步单独 commit。若新测试文件自己 import 失败，只修测试，不改产品。

### Task 2: 语言包与 schema

**Files:** `frontend/src/locales/langs/zh-cn.ts`、`frontend/src/locales/langs/en-us.ts`、`frontend/src/typings/app.d.ts`。

**Interfaces:**

- Consumes: design 第 3 节全部新键。
- Produces: 三份文件中 `page.shell` 下新分组齐全，`common.commandPalette.estimateTitle` 已补，已有键值不变。

- [ ] **Step 1: 按 design 第 3 节加入全部新键**

在 `page.shell` 下、已有 `defaultCycle` 之后增加下列分组，并同步 `App.I18n.Schema`。在已有 `common.commandPalette` 块末尾、`navInbox` / `actionAddLabel` 之后补 `estimateTitle`。中文逐字。英文 sentence case，无汉字。已有键（含 `common.confirm`、`page.issueDetail.create`、`route.workspace`、`route.workspace-onboarding`、`page.shell.issueKeyPrefix`、`page.shell.favoriteProject` / `favoriteView` / `favoriteIssue` / `favoriteInitiative`、`page.issueStatus.*`、`page.issuePriority.*`、已有 `common.commandPalette.*`）不改值。不要把 `createTitle` 的中文改短，不要把 `issueKeyPlaceholder` 的 en dash 改成 ASCII 连字符，不要把 `estimateTitle` 的省略号改成三个 ASCII 点，不要把 `noLabels` 里的 `Labels` 改成「标签」。

`frontend/src/typings/app.d.ts` 在 `page.shell` 的 `defaultCycle: string;` 之后加入（缩进与邻近键一致，10 空格分组名、12 空格叶子键）：

```ts
          favorites: {
            title: string;
            empty: string;
          };
          realtime: {
            connected: string;
            disconnected: string;
          };
          workspaceSwitcher: {
            placeholder: string;
            createTitle: string;
            namePlaceholder: string;
            issueKeyPlaceholder: string;
            issueKeyHint: string;
            createFailed: string;
          };
          hotkeyPicker: {
            changeStatus: string;
            assignOwner: string;
            changePriority: string;
            setLabels: string;
            setEstimate: string;
            noFocusedIssue: string;
            selectOwner: string;
            confirmAssign: string;
            noLabels: string;
            points: string;
            clearEstimate: string;
            updateStatusFailed: string;
            statusUpdated: string;
            updateEstimateFailed: string;
            estimateUpdated: string;
            updatePriorityFailed: string;
            priorityUpdated: string;
            assignFailed: string;
            ownerUpdated: string;
            updateLabelsFailed: string;
            labelsUpdated: string;
          };
```

同一文件在 `common.commandPalette` 的 `actionAddLabel: string;` 之后补：

```ts
          estimateTitle: string;
```

`zh-cn.ts` 在 `page.shell` 的 `defaultCycle: '默认当前冲刺'` 后补（先给 `defaultCycle` 行补逗号）：

```ts
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
```

同一文件在 `common.commandPalette` 的 `navInbox: '收件箱'` 后补逗号并加入：

```ts
      estimateTitle: '设置估点…'
```

`en-us.ts` 在 `page.shell` 的 `defaultCycle: 'Default cycle'` 后补（先给 `defaultCycle` 行补逗号）。失败句英文必须用弯引号 `Couldn’t`（U+2019）。`2–6` 必须是 en dash（U+2013）。`estimateTitle` 必须用 `…`（U+2026）：

```ts
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
        createFailed: 'Couldn’t create the workspace'
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
        updateStatusFailed: 'Couldn’t update the status',
        statusUpdated: 'Status updated',
        updateEstimateFailed: 'Couldn’t update the estimate',
        estimateUpdated: 'Estimate updated',
        updatePriorityFailed: 'Couldn’t update the priority',
        priorityUpdated: 'Priority updated',
        assignFailed: 'Couldn’t assign the owner',
        ownerUpdated: 'Owner updated',
        updateLabelsFailed: 'Couldn’t update the labels',
        labelsUpdated: 'Labels updated'
      }
```

同一文件在 `common.commandPalette` 的 `navInbox: 'Inbox'` 后补逗号并加入：

```ts
      estimateTitle: 'Set estimate…'
```

- [ ] **Step 2: 再跑 Task 1 的测试**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/app-shell-chrome.test.ts
```

语言包与 schema 断言应变绿；各产品源码的调用次数与字面缺失断言应仍红。不要在这一步单独 commit。

### Task 3: 五个壳层表面

**Files:** `FavoritesNav.vue`、`global-header/index.vue`、`workspace-switcher.vue`、`issue-hotkey-picker-host.vue`、`command-palette-host.vue`（只改 `estimateTitle` 与该 `watchEffect` 的 `void locale.value`）。

**Interfaces:**

- Consumes: Task 2 的键，以及已有的 `useLabelTable` / `lookupLabel`、`page.issueDetail.create`、`common.confirm`、`issueStatusOptions` / `issuePriorityOptions` 的 `value`。
- Produces: 范围内写死中文换绑为 `$t`，决定 E 源串、常量、「是/否」、命令面板 `keywords` 与上一刀冻结测试仍在。

- [ ] **Step 1: 最小改动换绑 `$t`**

从 `@/locales` 导入 `$t` 与（若该文件有会缓存文案的 computed / 函数）`locale`。组件若已导入 `$t` 则扩展同一条导入，不要改成局部 `t()`，不要改成 `useI18n()`。从 `@/locales/display-label` 导入已有的 `lookupLabel`，从 `@/locales/use-label-table` 导入已有的 `useLabelTable`（只在快捷键浮层需要）。

`FavoritesNav.vue` 已有 `import { $t } from '@/locales'`，不要改导入，不要改 `typeHint`。只改模板两处：

```vue
      <NText depth="3" style="font-size: 12px">{{ $t('page.shell.favorites.title') }}</NText>
```

```vue
        :description="collapsed ? '' : $t('page.shell.favorites.empty')"
```

`frontend/src/layouts/modules/global-header/index.vue` 增加 `import { $t } from '@/locales';`，只改实时连接 `title`，不要动 `:51` 的 `●`，不要动颜色或样式：

```vue
        :title="realtimeConnected ? $t('page.shell.realtime.connected') : $t('page.shell.realtime.disconnected')"
```

`workspace-switcher.vue` 增加 `import { $t } from '@/locales';`。`createWorkspace` 里的失败 toast 在调用时读 `$t`，不必包 computed：

```ts
    window.$message?.error(error?.message || $t('page.shell.workspaceSwitcher.createFailed'));
```

模板改为：

```vue
      :placeholder="$t('page.shell.workspaceSwitcher.placeholder')"
```

```vue
      :title="$t('page.shell.workspaceSwitcher.createTitle')"
      :positive-text="$t('page.issueDetail.create')"
```

```vue
        <NInput v-model:value="newName" :placeholder="$t('page.shell.workspaceSwitcher.namePlaceholder')" />
        <NInput
          v-model:value="newIssueKey"
          :placeholder="$t('page.shell.workspaceSwitcher.issueKeyPlaceholder')"
          maxlength="6"
          style="text-transform: uppercase"
          @update:value="v => (newIssueKey = (v || '').toUpperCase())"
        />
        <p class="m-0 text-12px text-gray-400">{{ $t('page.shell.workspaceSwitcher.issueKeyHint') }}</p>
```

不要写 `route.workspace-onboarding` 或 `route.workspace`。不要把 `page.issueDetail.create` 用在 `title` 上。不要用 `page.shell.issueKeyPrefix`。

`issue-hotkey-picker-host.vue` 扩展导入，并增加 label table 与缓存文案的 computed。保留对 `issueStatusOptions` / `issuePriorityOptions` 的导入，只覆盖可见 `label`，不改 `constants/issue.ts`。下面这段只替换到三个 computed 为止；其后已有的 `submitting`、`assigneeId`、`availableTags`、`selectedTagIds`、`tagsLoading`、`watch`、`toggleTag`、五个 `apply*` 以及 `estimateOptions` 都必须保留，只把各函数里的 toast 字面量按下一节替换：

```ts
import { computed, ref, watch } from 'vue';
import { NButton, NCheckbox, NModal, NSpace, NSpin, NTag } from 'naive-ui';
import { issuePriorityOptions, issueStatusOptions } from '@/constants/issue';
import { issueApi } from '@/service/api/issue';
import { type TagItem, tagApi } from '@/service/api/tag';
import { useIssueFocus } from '@/composables/use-issue-focus';
import { useIssueFieldPickers } from '@/composables/use-issue-field-pickers';
import UserSelect from '@/components/UserSelect.vue';
import type { Api } from '@/typings/api';
import { $t, locale } from '@/locales';
import { lookupLabel } from '@/locales/display-label';
import { useLabelTable } from '@/locales/use-label-table';

defineOptions({ name: 'IssueHotkeyPickerHost' });

const focus = useIssueFocus();
const pickers = useIssueFieldPickers();
const { activePicker, closePicker } = pickers;
const focusedIssueId = focus.focusedIssueId;

const show = computed({
  get: () => activePicker.value !== null,
  set: (v: boolean) => {
    if (!v) closePicker();
  }
});

const statusLabels = useLabelTable('page.issueStatus');
const priorityLabels = useLabelTable('page.issuePriority');

const title = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  switch (activePicker.value) {
    case 'status':
      return $t('page.shell.hotkeyPicker.changeStatus');
    case 'assignee':
      return $t('page.shell.hotkeyPicker.assignOwner');
    case 'priority':
      return $t('page.shell.hotkeyPicker.changePriority');
    case 'labels':
      return $t('page.shell.hotkeyPicker.setLabels');
    case 'estimate':
      return $t('page.shell.hotkeyPicker.setEstimate');
    default:
      return '';
  }
});

const statusSelectOptions = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  return issueStatusOptions.map(option => ({
    ...option,
    label: lookupLabel(statusLabels.value, option.value)
  }));
});

const prioritySelectOptions = computed(() => {
  // eslint-disable-next-line no-void
  void locale.value;
  return issuePriorityOptions.map(option => ({
    ...option,
    label: lookupLabel(priorityLabels.value, option.value)
  }));
});
```

`applyStatus` / `applyEstimate` / `applyPriority` / `applyAssignee` / `applyLabels` 只把写死 toast 换成 `$t`，在调用时读取，不必给这些函数加 `void locale.value`。把原字面量替换为：

```ts
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.updateStatusFailed'));
    window.$message?.success?.($t('page.shell.hotkeyPicker.statusUpdated'));
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.updateEstimateFailed'));
    window.$message?.success?.($t('page.shell.hotkeyPicker.estimateUpdated'));
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.updatePriorityFailed'));
    window.$message?.success?.($t('page.shell.hotkeyPicker.priorityUpdated'));
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.assignFailed'));
    window.$message?.success?.($t('page.shell.hotkeyPicker.ownerUpdated'));
      window.$message?.error?.(error.message || $t('page.shell.hotkeyPicker.updateLabelsFailed'));
    window.$message?.success?.($t('page.shell.hotkeyPicker.labelsUpdated'));
```

这些替换必须落在各自原来的函数里，不要合并函数，不要改 API 调用。模板对应改为：

```vue
      <div v-if="!focusedIssueId" class="picker-empty">{{ $t('page.shell.hotkeyPicker.noFocusedIssue') }}</div>
      <template v-else-if="activePicker === 'status'">
        <NSpace vertical>
          <NButton
            v-for="opt in statusSelectOptions"
            :key="opt.value"
            block
            secondary
            @click="applyStatus(opt.value as Api.Issue.IssueStatus)"
          >
            {{ opt.label }}
          </NButton>
        </NSpace>
      </template>
      <template v-else-if="activePicker === 'priority'">
        <NSpace vertical>
          <NButton
            v-for="opt in prioritySelectOptions"
            :key="opt.value"
            block
            secondary
            @click="applyPriority(opt.value as Api.Issue.IssuePriority)"
          >
            {{ opt.label }}
          </NButton>
        </NSpace>
      </template>
      <template v-else-if="activePicker === 'assignee'">
        <NSpace vertical>
          <UserSelect v-model="assigneeId" :placeholder="$t('page.shell.hotkeyPicker.selectOwner')" clearable />
          <NButton type="primary" block :loading="submitting" @click="applyAssignee">
            {{ $t('page.shell.hotkeyPicker.confirmAssign') }}
          </NButton>
        </NSpace>
      </template>
      <template v-else-if="activePicker === 'labels'">
        <NSpace vertical>
          <div v-if="!availableTags.length" class="picker-empty">
            {{ $t('page.shell.hotkeyPicker.noLabels') }}
          </div>
          <div v-for="tag in availableTags" :key="tag.id" class="label-row">
            <NCheckbox
              :checked="selectedTagIds.includes(tag.id)"
              @update:checked="(v: boolean) => toggleTag(tag.id, v)"
            >
              <NTag size="small" :bordered="false" :style="{ background: tag.color, color: '#fff' }">
                {{ tag.name }}
              </NTag>
            </NCheckbox>
          </div>
          <NButton type="primary" block :loading="submitting" @click="applyLabels">
            {{ $t('common.confirm') }}
          </NButton>
        </NSpace>
      </template>
      <template v-else-if="activePicker === 'estimate'">
        <NSpace vertical>
          <NButton v-for="pts in estimateOptions" :key="pts" block secondary @click="applyEstimate(pts)">
            {{ $t('page.shell.hotkeyPicker.points', { n: pts }) }}
          </NButton>
          <NButton block quaternary @click="applyEstimate(null)">
            {{ $t('page.shell.hotkeyPicker.clearEstimate') }}
          </NButton>
        </NSpace>
      </template>
```

不要把 `common.confirm` 用在「确认指派」按钮上。不要 `.replace`。不要改标签名 `tag.name`。

`command-palette-host.vue` 已有 `import { $t } from '@/locales'`，改成 `import { $t, locale } from '@/locales';`。只改 `estimateTitle` 这一处，并给已有、会把文案写入 `palette.setSources` 的 `watchEffect` 补上第一句 `void locale.value;`。不要改其它 `common.commandPalette.*` 调用，不要改 `utils/command-palette.ts`。`watchEffect` 开头必须是：

```ts
watchEffect(() => {
  // eslint-disable-next-line no-void
  void locale.value;

  palette.setGroupLabels({
    actions: $t('common.commandPalette.groupActions'),
    menus: $t('common.commandPalette.groupMenus'),
    issues: $t('common.commandPalette.groupIssues'),
    projects: $t('common.commandPalette.groupProjects'),
    views: $t('common.commandPalette.groupViews'),
    cycles: $t('common.commandPalette.groupCycles')
  });
```

把 `estimateTitle: '设置估点…'` 换成：

```ts
    estimateTitle: $t('common.commandPalette.estimateTitle')
```

其余 `buildNavActions` / `buildFocusIssueActions` 参数保持原样，包括 `title: $t('common.commandPalette.actionAddLabel')`。

- [ ] **Step 2: 跑测试确认 GREEN，并核既有冻结测试**

```bash
cd "$REPO/frontend"
pnpm exec vitest run src/locales/__tests__/app-shell-chrome.test.ts src/locales/__tests__/issue-list-board-chrome.test.ts src/locales/__tests__/issue-composer-chrome.test.ts
```

期望：新测试 EXIT 0；`issue-list-board-chrome.test.ts` 与 `issue-composer-chrome.test.ts` EXIT 0，且「待办」「低」「是/否」「自定义字段（可选）」「加载中...」的冻结未被改弱。不要改这两份既有测试。若只有插值失败，按 Global Constraints 修产品，不要 `.replace`，不要摘掉 `useI18n`。若测试因其它范围外原因失败，STOP 并改 plan，不要顺手扩范围。

- [ ] **Step 3: 产品提交（测试与产品一起，恰好白名单内的非 docs 路径）**

```bash
cd "$REPO"
git add frontend/src/locales/langs/zh-cn.ts frontend/src/locales/langs/en-us.ts frontend/src/typings/app.d.ts \
  frontend/src/layouts/modules/global-sider/FavoritesNav.vue \
  frontend/src/layouts/modules/global-header/index.vue \
  frontend/src/layouts/modules/global-header/components/workspace-switcher.vue \
  frontend/src/layouts/modules/global-search/issue-hotkey-picker-host.vue \
  frontend/src/layouts/modules/global-search/command-palette-host.vue \
  frontend/src/locales/__tests__/app-shell-chrome.test.ts
git diff --cached --name-only | sort
# 不得出现白名单外路径，不得含 .env.prod、components.d.ts、favorites.ts、constants/issue.ts、command-palette.ts、detail/index.vue、list/index.vue
allowed='frontend/src/locales/langs/zh-cn.ts
frontend/src/locales/langs/en-us.ts
frontend/src/typings/app.d.ts
frontend/src/layouts/modules/global-sider/FavoritesNav.vue
frontend/src/layouts/modules/global-header/index.vue
frontend/src/layouts/modules/global-header/components/workspace-switcher.vue
frontend/src/layouts/modules/global-search/issue-hotkey-picker-host.vue
frontend/src/layouts/modules/global-search/command-palette-host.vue
frontend/src/locales/__tests__/app-shell-chrome.test.ts'
while IFS= read -r path; do
  printf '%s\n' "$allowed" | grep -Fxq "$path" || exit 1
done < <(git diff --cached --name-only)
test "$(git diff --cached --name-only | wc -l)" = 9 || exit 1
strace -f -e trace=openat,execve -o "$EVIDENCE/product-commit.strace" \
  git commit -m "fix: localize app shell chrome for English"
```

父提交必须是文档笔。porcelain 必须为空（`.env.prod` 须已被 gitignore，不得出现在 porcelain 或 index）。strace 再核克隆根 `COMMIT_EDITMSG`。hook 失败则 STOP。

### Task 4: 终轮四门与证据包

- [ ] **Step 1: 再跑四门**

```bash
bash "$EVIDENCE/run-gates.sh" final
```

vitest 必须 EXIT 0。build 仅在已核 `.env.prod` 已就位时必须 EXIT 0；否则对照 baseline 同记 EXIT STOP，不得写成全绿或换用 `.env.example`。tsc/eslint 对照 baseline：路径 + rule/code + severity + message（忽略行号），added 0、removed 0。若 build 再次弄脏 `components.d.ts` 或 elegant-router 生成文件，从仓库根还原后再记 tsc/eslint。不要把未还原的脏跑当成终轮。不得写成全绿。不要把第 6 刀的 95/551 或 ✖ 868 写成终值。

- [ ] **Step 2: 打包证据并停手**

证据包写入 `/workspace/designs/app-shell-en-chrome-verify/`（实施时再建目录）。必须含：每一笔提交的 `git rev-parse` / 第一父提交 / 说明；相对精确 base 的 `git diff --name-only --no-ext-diff`、`--stat` 与完整 `final.diff`；**每一笔提交相对其第一父提交**的 name-only、diffstat 与完整 diff（不得只用 `final.diff` 代替分笔）；白名单路径列表；四门 baseline 与 final 的 meta/stdout/stderr；每一笔 commit 的 strace 与 hook sha256；`git status --porcelain`（空）；不含 `.env.prod` 正文、token、`dist/`、`node_modules`。若后来不得不多出修订笔，每一笔同样要有相对其第一父提交的这三份，不要 amend 前序提交来补证据。算出包的 sha256 与字节数后再交审。

```bash
BASE=09413d292c71973d4af5fc7350be88d9d55cdc2a
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
test "$(git log -1 --format=%s "$first")" = "docs: specify app shell English chrome" || exit 1
test "$(git rev-parse "${first}^")" = "$BASE" || exit 1
printf '%s\n' \
  docs/superpowers/plans/2026-11-12-app-shell-en-chrome.md \
  docs/superpowers/specs/2026-11-12-app-shell-en-chrome-design.md \
  | sort > "$EVIDENCE/commit1.expected-paths.txt"
sort "$EVIDENCE/commit1.name-only.txt" | cmp - "$EVIDENCE/commit1.expected-paths.txt"
second=$(git rev-list --reverse "$BASE"..HEAD | tail -n1)
test "$(git log -1 --format=%s "$second")" = "fix: localize app shell chrome for English" || exit 1
test "$(git rev-parse "${second}^")" = "$first" || exit 1
test "$(git diff --name-only --no-ext-diff "${second}^" "$second" | wc -l)" = 9 || exit 1
```

上面 `cmp` 失败即 STOP，不要改第一笔去凑。第一笔的分笔 diff 须恰好是那两份 docs，不得混入产品或测试路径。第二笔须恰好是白名单里的 9 个非 docs 路径。`final.diff` 仍要保留，但不能代替分笔。

到此停止。不 push，不开 PR，不 merge，不部署，不写下一刀。也不要中途通报 Way。

## 自我核对

- 盘点第 3 节与第 6 节第一片的白名单与范围外项，都能在本 plan 的 Files / 范围约束里找到对应处理或明确排除。第二片创建/编辑剩余句与第三片列表「是/否」未列入实施任务。第 6 刀列表看板铬未重开。
- 决定 A/B/C 已写入 Global Constraints 和 Task 3 禁改清单，并按推荐案锁定。文案表与 design 第 3 节一致，含 U+2019、U+2013、U+2026 与 `Labels`。
- 无 TBD / “类似 Task N” / 无代码的“写测试”。估点插值用 `{n}`，禁止 `.replace`。
- hook、软链、根目录提交、`components.d.ts` / elegant-router 生成文件从仓库根还原、Vite 端口 `9574`，均按第 4 / 5 / 6 刀已接受做法写死并改了 base / 端口 / 白名单，不是改 hook 正文。
- 证据包必须含每一笔的 name-only / diffstat / 完整 diff，加上相对 base 的 `final.diff`；第一笔分笔须恰好是两份 docs。不得只用 `final.diff`。
