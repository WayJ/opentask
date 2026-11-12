# 详情页通用焦点环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. 步骤使用 checkbox。获批前不执行。执行时从精确 PR11@`ebb2a93f88bc8c5762f6823c75067de7b69bd80e` 开新的隔离普通检出（`.git` 为目录，不是 worktree），新建分支，不改 PR11 检出，不改 PR6/7/8/9/10/11，不 amend / 不 rebase 已验 SHA。

**Goal:** 把详情页已有 scoped `*:focus-visible` 的 outline 颜色来源改成已有的 `--issue-focus`，让本页通用焦点环使用与已验「编辑」按钮相同的两档真实色，并用真实 Tab 验收计算样式。

**Architecture:** 不改专用「编辑」规则，也不改两处 `--issue-focus` 定义。只把通用规则从 `outline: 2px solid var(--color-accent-primary)` 改成 `outline: var(--issue-focus)`。持久合同仍是现有 `focus.test.ts`：源文冻结和 `compileStyle` 返回值里对旧 accent 短句的断言一并改掉，不能留旧句。浏览器计算样式单独取证，编译器输出不代替层叠。若改完后非编辑必测控件仍是 `outline-style: none`，停止交证，不准自行提高通用规则特异性、加 class、填写 `--color-accent-primary` 或升共享 token。

**Tech Stack:** Vue 3.5、`@vue/compiler-sfc`、Vitest 4、真实键盘 Tab / Shift+Tab、仓库外日志与 Vite `cacheDir`。happy-dom 不负责 `:focus-visible`。

## Global Constraints

- 获批前不建分支、不 commit、不改产品。获批后的起点只允许 `ebb2a93f88bc8c5762f6823c75067de7b69bd80e`。
- 白名单恰好 4 条路径：`docs/superpowers/specs/2026-11-12-issue-detail-generic-focus-design.md`、`docs/superpowers/plans/2026-11-12-issue-detail-generic-focus.md`、`frontend/src/views/issue/detail/index.vue`、`frontend/src/views/issue/detail/focus.test.ts`。不改 `description-surface.test.ts`，不改其他页面。
- 首个 commit 只有两份文档。产品文件在 RED 原件落盘之后才改。
- `index.vue` 只改通用 `*:focus-visible` 的 outline 来源为 `var(--issue-focus)`。下面三块必须保持原文：

```css
.issue-detail-container {
  --issue-focus: 2px solid #5e6ad2;
}
html.dark .issue-detail-container {
  --issue-focus: 2px solid #828fff;
}
.issue-detail-container .issue-actions .n-button.issue-action-edit:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}
```

- 不给同组其他按钮加 `issue-action-edit`。不另写 `:focus` outline。不填 `--color-accent-primary`。不把 `--issue-focus` 或两档色提升到共享样式。不改 naive 主题，不改 `.n-button__state-border`。不改「编辑」的可见条件、文案和路由表达式。
- 色值仍是已验两档：无 `dark` 类时 `#5e6ad2` = `rgb(94, 106, 210)`，有 `dark` 类时 `#828fff` = `rgb(130, 143, 255)`。不得只用 `--color-primary`（两种主题都是 `#5e6ad2`）。
- `:focus-visible` 由浏览器启发式决定。验收不承诺只有 Tab 匹配，也不承诺鼠标绝无环。
- 对比门槛是当次不透明背景链上至少 3:1。文字 4.5 不替换它。深色「+ 添加」对 `rgb(24, 24, 28)` 的 `6.172467713917881` 只是预计算，必须重测，不能当作验收数字。
- 验收在最终干净 SHA 上，真实 Tab，两种 `html.dark`。不调用 `element.focus()`。认 `activeElement`，不认固定按键次数。「编辑」按 PR11 四步确认未被盖过。同组已渲染非编辑按钮以及返回、「+ 添加」至少各一次 Tab 进入。环须 `solid` 2px、`outline-offset` 2px、两档实色、对当次叠色 ≥3:1。环距视口不足 8px 时探针抛错，记 blocked，不滚动重试。
- 取样必须等 `nprogress-busy` 从 `html` 上消失后再记。只读复现里浅色返回带着 busy，那次不算验收。
- 「提升为根」本轮按未测限制保留，不改 fixture，不因 `issue-long` 上缺它而失败，也不把它写成已验收。
- 当前复现里这些非编辑控件已有 `outline-offset` 2px，支持「通用规则已命中、只是 shorthand 因空 token 无效」的判断，但以改后实测为准。若改完后必测非编辑控件仍是 `outline-style: none`（被其它规则盖掉），停下来交证，不准自行提高通用规则特异性、加 class、填 `--color-accent-primary` 或升共享 token。
- 每个 RED 与 GREEN 在改下一步之前把原件写入仓库外目录：HEAD、porcelain、test blob、diff、COMMAND、CWD、TZ、stdout、stderr、EXIT。脚本异常退出记 blocked，不把日志改成通过。
- `compileStyle` 的命令 stdout 只证明编译器字符串。层叠只认浏览器计算样式。
- 四门禁用 `pnpm exec`，不用 `pnpm run lint`（那条带 `--fix`），不用 `vite --mode test`，不用 `eslint --fix`。
- baseline 是获批后在干净 `ebb2a93f` 上当次跑出的四门禁原文。PR11 记录过的 87 files / 519 tests、build EXIT 0、tsc 29、lint 872 不能代替这次输出。vue-tsc 与 eslint 对照这一次 baseline 的诊断原文，行号可以漂。baseline 非 0 就保持非 0，不报成全绿。新增诊断则停止。
- 钩子按 PR11 保留限制处理：不改 hooksPath、不改校验源码、不用 `SKIP` / `--no-verify`、不请人跳钩、不再做 hook 路径实验。若新检出按仓库既有方式装上 hooks，只允许删除本检出的 `.git/hooks/pre-commit`，必须保留已装 `commit-msg` 且哈希不变。在仓库根目录做正常 `git commit`，不要在 `frontend/` 里提交。没有当次 hook 打开路径原件，不得把 EXIT 0 写成已校验本检出这份说明；两种解释都保留。若再遇 `frontend/.git/COMMIT_EDITMSG` 或同类 ENOENT，立即停交原文，不二次重试，不改校验。
- 新检出不得写入或 reset 主仓 `/agent/repos/opentask`、pin `/tmp/cursor/opentask-list-pin`、旧树 `/tmp/cursor/opentask-detail-focus`，也不得在 PR11 检出 `/tmp/cursor/opentask-detail-clone` 上提交或移动其分支。不 fetch / 不 push 任何 remote。出现白名单以外的已跟踪改动就停止，不悄悄还原。
- 计划结束于两份独立 Grok 原文落盘。不 push，不开 PR，不 merge，不 deploy。停下来等 Yuri 验收。

---

### Task 0: 隔离检出、基线、文档提交

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-issue-detail-generic-focus-design.md`
- Create: `docs/superpowers/plans/2026-11-12-issue-detail-generic-focus.md`

**Interfaces:**
- Consumes: 已验提交 `ebb2a93f88bc8c5762f6823c75067de7b69bd80e`，已批 design sha256 `0ee456ee2fdfa1f59d40d66d30e183da7200afcde94b2c754ad6cf59e0dd2202`
- Produces: 新隔离分支上的文档提交，以及 `/tmp/cursor/opentask-readonly/detail-generic-focus-logs/baseline/` 里的四门禁原件

- [ ] **Step 1: 只在获批后开普通隔离检出**

先核 `/tmp/cursor/opentask-detail-clone` 仍是 `ebb2a93f88bc8c5762f6823c75067de7b69bd80e`、分支 `cursor/issue-detail-edit-focus-4333`、porcelain 为空。然后：

```bash
git clone /tmp/cursor/opentask-detail-clone /tmp/cursor/opentask-generic-focus-clone
git -C /tmp/cursor/opentask-generic-focus-clone switch --detach ebb2a93f88bc8c5762f6823c75067de7b69bd80e
git -C /tmp/cursor/opentask-generic-focus-clone switch -c cursor/issue-detail-generic-focus-4333
```

`git rev-parse HEAD` 必须打印 `ebb2a93f88bc8c5762f6823c75067de7b69bd80e`。`git status --porcelain` 必须为空。`.git` 必须是目录，不是指向其他检出的 worktree 文件。随后再核：PR11 克隆 HEAD / 分支 / porcelain 未变；MAIN `/agent/repos/opentask`、PIN `/tmp/cursor/opentask-list-pin`、OLD `/tmp/cursor/opentask-detail-focus` 的 HEAD 与 config mtime 未变。

给新检出的 `frontend/node_modules` 做指向 `/agent/repos/opentask/frontend/node_modules` 的符号链接，与 PR11 克隆相同。不安装新依赖。不在主仓 `node_modules/.vite` 里写缓存。后面启动 Vite 必须使用仓库外 `--config`，把 `cacheDir` 写到 `/tmp/cursor/opentask-readonly/detail-generic-focus-logs/vite-cache`。新检出若继承了 remote（origin 可能指向 PR11 克隆或主仓路径），本计划内一律不 fetch、不 push。

钩子按 Global Constraints 处理。不要为了「证明钩子」改校验或做路径实验。

- [ ] **Step 2: 在干净 ebb2a93f 上保存当次四门禁**

CWD 是 `/tmp/cursor/opentask-generic-focus-clone/frontend`。四条命令分开跑，各写 `stdout.txt`、`stderr.txt` 和 `meta.txt`。meta 含 `DATE`、`TZ=UTC`、`HEAD`、`CWD`、`COMMAND`、`EXIT`。porcelain 写入同目录。

```bash
pnpm exec vitest run
pnpm exec vite build --mode prod
pnpm exec vue-tsc --noEmit --skipLibCheck
pnpm exec eslint .
```

这四份输出就是本切片 baseline。不能拿 PR11 的 87/519、tsc 29、lint 872 代替这次输出，也不能改用 pin SHA `250fc` 的数字。把 vue-tsc 与 eslint 的每一行诊断原文留下，供 Task 5 去掉行号后对照。

- [ ] **Step 3: 只提交两份文档**

把已批 design（sha256 仍须是 `0ee456ee2fdfa1f59d40d66d30e183da7200afcde94b2c754ad6cf59e0dd2202`）与本 plan 拷入上面两个路径。不要改写已批 design 正文。`git add` 之后 `git diff --cached --name-only` 恰好是这两行。在仓库根目录执行：

```bash
git commit -m "docs: specify the detail page generic focus ring"
```

提交后 `git status --porcelain` 为空，`git rev-parse HEAD^` 是 `ebb2a93f88bc8c5762f6823c75067de7b69bd80e`。钩子若失败，按 Global Constraints 停交原文。

---

### Task 1: RED

**Files:**
- Modify: `frontend/src/views/issue/detail/focus.test.ts`
- Test: `frontend/src/views/issue/detail/focus.test.ts`

**Interfaces:**
- Consumes: `index.vue` 在 `ebb2a93f` 上仍使用 `outline: 2px solid var(--color-accent-primary)` 的通用规则，以及已有的专用「编辑」规则
- Produces: 失败断言指向通用规则源文和 compiled 里的旧 accent 短句。编辑合同、两处 `--issue-focus` 定义、专用选择器在 RED 时已经通过

- [ ] **Step 1: 只改这份测试，先不改 `index.vue`**

把 `focus.test.ts` 写成下面这份。`@click` 断言保持一行，避免再引入已验过的 prettier 问题。源文冻结和 compiled 里对 `outline: 2px solid var(--color-accent-primary)` 的断言都要改掉，不能留旧句。

```ts
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import process from 'node:process';
import { compileStyle } from '@vue/compiler-sfc';
import { describe, expect, it } from 'vitest';

const detail = readFileSync(resolve(process.cwd(), 'src/views/issue/detail/index.vue'), 'utf8');

function editButtonBlock(source: string): string {
  const start = source.indexOf('<div v-if="!issue.is_deleted" class="issue-actions">');
  const end = source.indexOf('复制问题', start);
  if (start < 0 || end < 0) return '';
  return source.slice(start, end);
}

describe('detail edit button focus ring', () => {
  it('keeps the edit label, visibility, and route', () => {
    const block = editButtonBlock(detail);
    expect(block).toContain('v-if="!issue.is_deleted"');
    expect(block).toContain('编辑');
    expect(block).toContain(`@click="router.push({ path: '/issue/edit', query: { id: issue.id } })"`);
  });

  it('uses the two-tier issue-focus token on the generic focus rule', () => {
    expect(detail).toContain(`*:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}`);
    expect(detail).not.toContain('outline: 2px solid var(--color-accent-primary)');
  });

  it('adds one class and the two edit-page focus tiers', () => {
    const block = editButtonBlock(detail);
    expect(block).toContain('class="issue-action-edit"');
    expect(detail.match(/class="issue-action-edit"/g)).toHaveLength(1);
    expect(detail).toContain(`.issue-detail-container {
  --issue-focus: 2px solid #5e6ad2;
}`);
    expect(detail).toContain(`html.dark .issue-detail-container {
  --issue-focus: 2px solid #828fff;
}`);
    expect(detail).toContain(`.issue-detail-container .issue-actions .n-button.issue-action-edit:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}`);
    expect(detail).not.toContain('.issue-action-edit:focus {');
    const scoped = detail.match(/<style scoped>([\s\S]*?)<\/style>/);
    expect(scoped).not.toBeNull();
    const compiled = compileStyle({
      source: scoped?.[1] ?? '',
      filename: 'src/views/issue/detail/index.vue',
      id: 'focus',
      scoped: true
    });
    expect(compiled.errors).toEqual([]);
    expect(compiled.code).toContain(
      '.issue-detail-container .issue-actions .n-button.issue-action-edit[data-v-focus]:focus-visible'
    );
    expect(compiled.code).toContain('outline: var(--issue-focus);');
    expect(compiled.code).toContain(`[data-v-focus]:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}`);
    expect(compiled.code).not.toContain('outline: 2px solid var(--color-accent-primary)');
  });
});
```

第一个 `it` 和第三个 `it` 里专用规则 / 类名 / 两档定义 / 编辑编译选择器，在 `ebb2a93f` 上已经成立。它们若失败，说明树不是这份源码，停止，不把它们改成预期红。第二个 `it`，以及第三个 `it` 末尾对 generic compiled 块和「不得再含旧 accent 短句」的断言，才是本轮新行为的红。

- [ ] **Step 2: 跑红并先落盘**

CWD：`/tmp/cursor/opentask-generic-focus-clone/frontend`。日志目录：`/tmp/cursor/opentask-readonly/detail-generic-focus-logs/red/`。在跑之前写入 HEAD、`git status --porcelain`、`git hash-object` 的测试 blob、`git diff -- frontend/src/views/issue/detail/focus.test.ts`。然后：

```bash
pnpm exec vitest run src/views/issue/detail/focus.test.ts
```

stdout 与 stderr 分文件。meta 记录 `COMMAND`、`CWD`、`TZ=UTC`、`DATE`、`EXIT`。预期 EXIT 非 0。预期失败点包含仍在源码或 compiled 里的 `outline: 2px solid var(--color-accent-primary)`，或通用规则尚未写成 `outline: var(--issue-focus)`。预期第一个 `it` 通过。若进程在收集阶段崩溃，或失败文本不是这些断言失败，记 blocked，不改 `index.vue`。跑完再记一次 porcelain。`index.vue` 不得出现在 diff 里。

---

### Task 2: GREEN

**Files:**
- Modify: `frontend/src/views/issue/detail/index.vue`（只改通用 `*:focus-visible` 的 outline 声明）
- Test: `frontend/src/views/issue/detail/focus.test.ts`

**Interfaces:**
- Consumes: Task 1 已落盘的 RED
- Produces: 通用规则改用 `var(--issue-focus)`。GREEN 日志目录 `.../green/`

- [ ] **Step 1: 只改这一处 CSS 声明**

把通用规则从：

```css
*:focus-visible {
  outline: 2px solid var(--color-accent-primary);
  outline-offset: 2px;
}
```

改成：

```css
*:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}
```

不改选择器，不改 `outline-offset`，不加 `!important`，不移动这块规则去盖过专用规则。两处 `--issue-focus` 定义和专用「编辑」规则必须与改前字节级相同。不改模板，不加 class，不填 `--color-accent-primary`。

- [ ] **Step 2: 跑绿并先落盘**

同一条 vitest 命令。日志目录 `.../green/`。字段与 RED 相同，另加 `index.vue` 的 `git diff`。预期 3 passed、EXIT 0。EXIT 非 0 则停止，不提交。跑完 porcelain 只含 `index.vue` 与 `focus.test.ts`。`git diff` 里不得再出现 `outline: 2px solid var(--color-accent-primary)`，也不得出现专用规则或 `--issue-focus` 定义的改动。

- [ ] **Step 3: 提交产品与测试**

在仓库根目录：

```bash
git add frontend/src/views/issue/detail/index.vue frontend/src/views/issue/detail/focus.test.ts
git diff --cached --name-only
git commit -m "fix: use the detail focus token on the generic focus-visible rule"
```

暂存名单必须恰好是这两行。提交后 porcelain 为空。`git diff ebb2a93f88bc8c5762f6823c75067de7b69bd80e --name-only` 恰好是白名单 4 行。钩子失败则停交原文。不要 amend 文档提交或本提交。若随后四门禁对照只因这两文件的格式诊断新增，只允许在已批 4 路径内做单独的格式修正提交，仍不准 amend，也不准改 CSS 语义。

---

### Task 3: 编译器 stdout

**Files:**
- 无产品文件。命令在新检出的 `frontend/` 执行，输出写到日志目录。

**Interfaces:**
- Consumes: Task 2 的干净 SHA
- Produces: `.../compiler/stdout.txt`。该文件不是层叠证据

- [ ] **Step 1: 用仓库里的编译器打出返回 CSS**

CWD：`/tmp/cursor/opentask-generic-focus-clone/frontend`。

```bash
pnpm exec node --input-type=module -e '
import { readFileSync } from "node:fs";
import { compileStyle } from "@vue/compiler-sfc";
const detail = readFileSync("src/views/issue/detail/index.vue", "utf8");
const scoped = detail.match(/<style scoped>([\s\S]*?)<\/style>/);
const compiled = compileStyle({
  source: scoped[1],
  filename: "src/views/issue/detail/index.vue",
  id: "focus",
  scoped: true
});
console.log(compiled.code);
if (compiled.errors.length) console.error(compiled.errors);
'
```

stdout、stderr、meta 分开保存。预期 EXIT 0，stderr 为空，stdout 同时含：

```css
.issue-detail-container .issue-actions .n-button.issue-action-edit[data-v-focus]:focus-visible
```

以及：

```css
[data-v-focus]:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}
```

且不得再含 `outline: 2px solid var(--color-accent-primary)`。meta 写明：这是编译器返回文本，不证明浏览器层叠，也不测量特异性。命令失败则 blocked。

---

### Task 4: 同一干净 SHA 的真实键盘

**Files:**
- 无产品文件。探针放在 `/tmp/cursor/opentask-readonly/detail-generic-focus-logs/browser/probe.mjs`。

**Interfaces:**
- Consumes: Task 2 之后的最终干净 HEAD（若有格式补提交，则以最终 SHA 为准）
- Produces: 两种 `html.dark` 下，「编辑」四步以及必测非编辑控件各至少一次 Tab 进入的计算样式、对比和原图；若非编辑仍为 `outline-style: none`，本任务以 blocked 结束并交证

- [ ] **Step 1: 绑定 SHA 与 Vite**

探针前后各写 HEAD、porcelain、`readlink /proc/<pid>/cwd` 和命令行。porcelain 必须为空。cwd 必须是本检出的 `frontend/`。若 9541 或其他端口仍服务别的检出，另起新端口，不杀掉已有进程，不写主仓 Vite 缓存。页面 `http://127.0.0.1:<port>/issue/detail?id=issue-long`，视口 1280×800。只预写 `SOY_token`、`SOY_refreshToken`、`SOY_lang`。不写主题键。主题只用页眉 tooltip「主题模式」的那枚按钮。点击后必须留在同一文档，不得重新加载；若点击后 `html.dark` 被清掉，该次取样作废，保留原件，在同一文档上重来，不得把作废跑写成通过。每次取样读取 `documentElement.classList.contains("dark")` 和完整 `className`。`prefers-color-scheme` 只记录，不用它代替 `html.dark`。全程不调用 `element.focus()`，不点击被测控件来取焦点，不为裁切滚动。

- [ ] **Step 2: 先等 `nprogress-busy` 消失，再取样**

每个主题开始 Tab 之前，以及每一次准备记为验收的取样之前，`document.documentElement.className` 不得包含 `nprogress-busy`。若还在，等待其消失后再记；超时则 blocked。只读复现里浅色返回带着 busy 的那次记录，不能当作本轮验收通过。

- [ ] **Step 3: 每个主题覆盖必测控件**

`issue-long` 上预期仍渲染这 8 个操作按钮，只有「编辑」带 `issue-action-edit`：编辑、复制问题、设为子项…、状态、删除、关注、收藏到侧栏、复制分支名。「提升为根」若不出现，记入未测限制，不改 fixture，不因此失败。对照控件仍是标题行返回（无文字、role、aria-label）和子问题「+ 添加」。

每个 `html.dark` 取值都做下面这些事。通过与否看 `activeElement` 是不是目标控件，不看某一固定 Tab 次数。到不了就 blocked。安全上限 200 次 Tab。

1. 在 busy 已消失后，从页面起始 Tab 到返回按钮，记录环、对比和未裁切原图。
2. 继续 Tab 到「编辑」，按 PR11 四步：Tab 进入见环并出原图；再按一次 Tab，离开且 `outline-style` 为 `none`；再按一次 Shift+Tab，必须回到这枚按钮，再记环、对比并另存未裁切原图；再按一次 Shift+Tab，再次离开且环消失。一次 Shift+Tab 没有回到「编辑」就 blocked。这一步用于确认专用规则未被盖过：「编辑」的计算条件仍须是 `outline-style` 为 `solid`，`outline-width` 为 `2px`，`outline-offset` 为 `2px`；没有 `dark` 类时颜色是 `rgb(94, 106, 210)`，有 `dark` 类时是 `rgb(130, 143, 255)`；相对当次不透明背景链的对比至少 3。
3. 再 Tab 经过同组已渲染的非编辑按钮：复制问题、设为子项…、状态、删除、关注、收藏到侧栏、复制分支名。每个至少一次真实 Tab 进入，记录同一套计算样式、对比和未裁切原图。
4. 继续 Tab 到「+ 添加」，同样至少一次 Tab 进入。深色下该控件的叠色先前是 `rgb(24, 24, 28)`，对 `#828fff` 的 `6.172467713917881` 只是预计算，这里必须重测当次叠色和对比。

必测非编辑控件的通过条件与「编辑」相同：可见环为 `solid` 2px、offset 2px、对应主题的两档实色、对当次叠色 ≥3:1。有可见环时按 8px 裁图；距视口边缘不足 8px 则抛错，不滚动、不二次拍摄。离开时不要求对每一个非编辑控件都走完四步，但取样当下必须匹配 `:focus-visible`。

若任一必测非编辑控件在 `:focus-visible` 为 true 时仍是 `outline-style: none`，立即停止本任务和后续产品改动，把当次 HEAD、porcelain、计算样式、原图和命令原件交证。不准为了让环出现而提高通用规则特异性、加 class、填写 `--color-accent-primary` 或升共享 token。当前复现里这些控件已有 offset 2px，只能作为改前旁证，不能代替这一步的实测。

- [ ] **Step 4: 鼠标只核「编辑」路由**

键盘取样之后，用鼠标点击「编辑」。预期地址进入 `/issue/edit` 且查询参数 id 为 `issue-long`。不截鼠标图，不读鼠标当下的 outline，不点击其他被测控件。路由不对则 blocked。探针结束再记 HEAD 与 porcelain，必须与开始时的 SHA 相同且干净。

---

### Task 5: 四门禁对照当次 baseline

**Files:**
- 无产品文件

**Interfaces:**
- Consumes: Task 0 的 baseline 原文，Task 4 之后的同一个干净最终 SHA
- Produces: `.../gates/` 下四组 stdout、stderr、meta

- [ ] **Step 1: 原命令重跑**

CWD 仍是新检出 `frontend/`。命令与 Task 0 相同：`vitest run`、`vite build --mode prod`、`vue-tsc --noEmit --skipLibCheck`、`eslint .`。每条都有 stdout、stderr、meta。把当次文件数和测试数原文留下。不回写成 PR11 的 87/519，也不改用 250fc 的数字。

- [ ] **Step 2: 逐条对照 vue-tsc 与 eslint**

去掉行号和列号后，最终诊断集合必须与 Task 0 当次 baseline 相同。允许 `index.vue` 或 `focus.test.ts` 因改通用规则或测试字符串造成行号漂移，漂移的原文要随对照记下来。多出或少掉任何一条诊断，停止。baseline 里非 0 的命令，最终仍须非 0。build 若 baseline 是 EXIT 0，最终仍须 EXIT 0。不把这四条写成 CI 全绿。

---

### Task 6: 两份独立 Grok 原文

**Files:**
- 无产品文件。原文写入 `.../reviews/spec.txt` 与 `.../reviews/code.txt`，旁边写 metadata：agent id、model、开始与结束时间、返回是否为空

**Interfaces:**
- Consumes: 干净最终 SHA、spec、4 路径 diff、RED/GREEN、compiler stdout、浏览器 JSON 与原图
- Produces: 两份互不引用的审阅原文。空返回或数毫秒返回不是 Pass

- [ ] **Step 1: 同时独立发起，不共用对话**

两份都用 `grok-4.7-high`，`run_in_background: false`。一份只看 spec 与计划是否被 diff 实现。一份只看 `index.vue`、`focus.test.ts`、编译 stdout 和浏览器记录。不把第一份的结论写进第二份的提示。模型调用失败则 blocked，不换模型冒充通过。不购买新积分。

- [ ] **Step 2: 落盘后停止**

两份原文和 metadata 写入日志目录。不根据审阅改代码。不 push，不开 PR。把最终 HEAD、porcelain 和相对 `ebb2a93f` 的 4 路径 `git diff --name-only` 再记一次，并再核 MAIN / PIN / OLD / PR11 克隆未被写入。停下来等 Yuri 验收。

---

## 证据目录

```text
/tmp/cursor/opentask-readonly/detail-generic-focus-logs/
  baseline/{vitest,build,vue-tsc,eslint}/{stdout.txt,stderr.txt,meta.txt}
  red/{stdout.txt,stderr.txt,meta.txt,porcelain.txt,test.diff,testblob.sha}
  green/{stdout.txt,stderr.txt,meta.txt,porcelain.txt,test.diff,vue.diff,testblob.sha}
  compiler/{stdout.txt,stderr.txt,meta.txt}
  browser/{probe.mjs,report.json,*.png}
  gates/{vitest,build,vue-tsc,eslint}/{stdout.txt,stderr.txt,meta.txt}
  reviews/{spec.txt,code.txt,spec.meta,code.meta}
```

meta 每一份都含 DATE、TZ、HEAD、CWD、COMMAND、EXIT。缺任何一份，不能把该步写成完成。

获批前不执行本计划。获批后按 TDD 在上述隔离检出执行，并在 Task 6 结束后等待验收，不自行 push 或开 PR。
