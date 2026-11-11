# 详情编辑按钮焦点环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. 步骤使用 checkbox。获批前不执行。执行时从 exact `244c93e296a047cf138a880fa24d683b4be8203d` 开隔离 worktree，不改当前 PR #9 检出，不改 PR #10。

**Goal:** 只给详情页这枚「编辑」按钮加上与编辑页同档的两档 `:focus-visible` 环，并用真实 Tab / Shift+Tab 验收计算样式。

**Architecture:** 一个静态类 `issue-action-edit` 落在现有 `NButton` 上。两档 `--issue-focus` 写在 `.issue-detail-container` 与 `html.dark .issue-detail-container`。outline 只写在带这个类的 `:focus-visible` 规则上。第 2802 行旧规则原文保留。持久合同是新的 `focus.test.ts`，它锁定源码和 `compileStyle` 返回字符串。浏览器计算样式单独取证，编译器输出不代替层叠。

**Tech Stack:** Vue 3.5、`@vue/compiler-sfc` 3.5.44、Vitest 4、happy-dom 不负责 `:focus-visible`、Playwright 真实键盘、仓库外合成 API `127.0.0.1:7377`、已有 Vite `127.0.0.1:9527`。

## Global Constraints

- 获批前不建分支、不 commit、不改产品。获批后的起点只允许 `244c93e296a047cf138a880fa24d683b4be8203d`。
- 白名单恰好 4 条路径：两份本文档、`frontend/src/views/issue/detail/index.vue`、`frontend/src/views/issue/detail/focus.test.ts`。不改 `description-surface.test.ts`。
- 首个 commit 只有两份文档。产品文件在 RED 原件落盘之后才改。
- 色值只用编辑页已有两档：无 `dark` 类时 `#5e6ad2`，有 `dark` 类时 `#828fff`。
- 旧规则保持这段原文，包括缩进：

```css
*:focus-visible {
  outline: 2px solid var(--color-accent-primary);
  outline-offset: 2px;
}
```

- 按钮可见条件、文案「编辑」、`@click="router.push({ path: '/issue/edit', query: { id: issue.id } })"` 不改。
- `:focus-visible` 由浏览器启发式决定。验收不承诺只有 Tab 匹配，也不承诺鼠标绝无环。
- 对比门槛是当次不透明背景链上至少 3:1。文字 4.5 不替换它。
- 每个 RED 与 GREEN 在改下一步之前把原件写入仓库外目录：HEAD、porcelain、test blob、diff、COMMAND、CWD、TZ、stdout、stderr、EXIT。脚本异常退出记 blocked，不把日志改成通过。
- `compileStyle` 的命令 stdout 只证明编译器字符串。层叠只认浏览器计算样式。特异性 (0, 6, 0) 只是静态计数。
- 四门禁用 `pnpm exec`，不用 `pnpm run lint`（那条带 `--fix`），不用 `vite --mode test`。
- 键盘验收在同一个最终干净 SHA 上，`html.dark` 两种取值各走四步：Tab 进入见环，再按一次 Tab 离开且环消失，再按一次 Shift+Tab 回到这枚按钮并见环、出未裁切原图，再按一次 Shift+Tab 离开且环消失。认 `activeElement`，不认固定按键次数，不用 `element.focus()`。环距视口不足 8px 时探针抛错，记 blocked，不滚动重试。
- baseline 是获批后在干净 `244c93e296a047cf138a880fa24d683b4be8203d` 上当次跑出的四门禁原文。86 files / 516 tests 只是先前 PR #9 的记录，本包没有跑过。不能改用 `250fc34af9c64e828aab706567b0430d3d74e452` 的 84 files。vue-tsc 与 eslint 对照这一次 baseline 的诊断原文，行号可以漂。baseline 非 0 就保持非 0，不报成全绿。新增诊断则停止。
- PR #10 的历史 TDD 日志仍然缺证。本计划不追认，也不重跑那次列表矩阵。
- 不用 `eslint --fix`。不改 git hooks。worktree 里若 hook 找不到主检出的 `COMMIT_EDITMSG`，commit 时加 `SKIP_SIMPLE_GIT_HOOKS=1`，并在 meta 里写明原因。
- 出现白名单以外的已跟踪改动就停止，不悄悄还原。
- 计划结束于两份独立 Grok 原文落盘。不 push，不开 PR。

---

### Task 0: 隔离树、基线、文档提交

**Files:**
- Create: `docs/superpowers/specs/2026-11-12-issue-detail-edit-focus-design.md`
- Create: `docs/superpowers/plans/2026-11-12-issue-detail-edit-focus.md`

**Interfaces:**
- Consumes: 已验提交 `244c93e296a047cf138a880fa24d683b4be8203d`
- Produces: 干净分支上的文档提交，以及 `/tmp/cursor/opentask-readonly/detail-edit-focus-logs/baseline/` 里的四门禁原件

- [ ] **Step 1: 只在获批后开 worktree**

```bash
git -C /agent/repos/opentask worktree add --detach /tmp/cursor/opentask-detail-focus 244c93e296a047cf138a880fa24d683b4be8203d
git -C /tmp/cursor/opentask-detail-focus switch -c cursor/issue-detail-edit-focus-4333
```

`git rev-parse HEAD` 必须打印 `244c93e296a047cf138a880fa24d683b4be8203d`。`git status --porcelain` 必须为空。主检出 `/agent/repos/opentask` 与 pin 树 `/tmp/cursor/opentask-list-pin` 不执行 add 或 commit。给 worktree 的 `frontend/node_modules` 做指向主前端 `node_modules` 的符号链接，与现有列表 worktree 相同。不安装新依赖。

- [ ] **Step 2: 在干净 244c 上保存当次四门禁**

CWD 是 `/tmp/cursor/opentask-detail-focus/frontend`。四条命令分开跑，各写 `stdout.txt`、`stderr.txt` 和 `meta.txt`。meta 含 `DATE`、`TZ=UTC`、`HEAD`、`CWD`、`COMMAND`、`EXIT`。porcelain 写入同目录。

```bash
pnpm exec vitest run
pnpm exec vite build --mode prod
pnpm exec vue-tsc --noEmit --skipLibCheck
pnpm exec eslint .
```

这四份输出就是 baseline。本包还没有跑过它们。先前 PR #9 笔记里的 86 files / 516 tests，以及更早的 vue-tsc 29 条、eslint 872 条，都不是本包的实测，不能拿来代替这次输出，也不能改用 pin SHA `250fc` 的 84 files。把 vue-tsc 与 eslint 的每一行诊断原文留下，供 Task 5 去掉行号后对照。

- [ ] **Step 3: 只提交两份文档**

把获批的 spec 与本 plan 拷入上面两个路径。`git add` 之后 `git diff --cached --name-only` 恰好是这两行。然后：

```bash
git commit -m "docs: specify the detail edit button focus ring"
```

提交后 `git status --porcelain` 为空，`git rev-parse HEAD^` 是 `244c93e296a047cf138a880fa24d683b4be8203d`。

---

### Task 1: RED

**Files:**
- Create: `frontend/src/views/issue/detail/focus.test.ts`
- Test: `frontend/src/views/issue/detail/focus.test.ts`

**Interfaces:**
- Consumes: `index.vue` 在 244c 上的按钮与第 2802 行原文
- Produces: 失败断言 `issue-action-edit` 与两档 `--issue-focus` 尚不存在。旧规则与路由断言在 RED 时已经通过

- [ ] **Step 1: 写入这份测试，先不改 `index.vue`**

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
    expect(block).toContain(
      `@click="router.push({ path: '/issue/edit', query: { id: issue.id } })"`
    );
  });

  it('keeps the existing generic focus rule', () => {
    expect(detail).toContain(`*:focus-visible {
  outline: 2px solid var(--color-accent-primary);
  outline-offset: 2px;
}`);
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
    expect(compiled.code).toContain('outline: 2px solid var(--color-accent-primary);');
  });
});
```

前两个 `it` 在 244c 上已经成立。它们若失败，说明树不是这份源码，停止，不把它们改成预期红。第三个 `it` 才是新行为的红。

- [ ] **Step 2: 跑红并先落盘**

CWD：`/tmp/cursor/opentask-detail-focus/frontend`。日志目录：`/tmp/cursor/opentask-readonly/detail-edit-focus-logs/red/`。在跑之前写入 HEAD、`git status --porcelain`、`git hash-object` 的测试 blob、`git diff -- frontend/src/views/issue/detail/focus.test.ts`。然后：

```bash
pnpm exec vitest run src/views/issue/detail/focus.test.ts
```

stdout 与 stderr 分文件。meta 记录 `COMMAND`、`CWD`、`TZ=UTC`、`DATE`、`EXIT`。预期 EXIT 非 0。预期失败点包含 `issue-action-edit`。预期前两个测试通过，第三个失败。若进程在收集阶段崩溃，或失败文本不是断言失败，记 blocked，不改 `index.vue`。跑完再记一次 porcelain。`index.vue` 不得出现在 diff 里。

---

### Task 2: GREEN

**Files:**
- Modify: `frontend/src/views/issue/detail/index.vue:1480`
- Modify: `frontend/src/views/issue/detail/index.vue:2801`
- Test: `frontend/src/views/issue/detail/focus.test.ts`

**Interfaces:**
- Consumes: Task 1 已落盘的 RED
- Produces: 按钮类名与三块 CSS。GREEN 日志目录 `.../green/`

- [ ] **Step 1: 只改按钮这一行**

把第 1480 行换成：

```vue
<NButton size="small" class="issue-action-edit" @click="router.push({ path: '/issue/edit', query: { id: issue.id } })">
```

`@click`、文案「编辑」和上面的 `v-if` 保持原样。其他 `NButton` 不加 `issue-action-edit`。

- [ ] **Step 2: 在旧焦点注释之前插入三块，旧规则一字不改**

在第 2801 行 `/* Focus Styles */` 之前插入：

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

第 2802–2804 行的 `*:focus-visible` 块仍使用 `--color-accent-primary`。不改 `.description-content` 的暗色规则。不改 `#828fff` 那条已有链接色（约第 2514 行）。

- [ ] **Step 3: 跑绿并先落盘**

同一条 vitest 命令。日志目录 `.../green/`。字段与 RED 相同，另加 `index.vue` 的 `git diff`。预期 3 passed、EXIT 0。EXIT 非 0 则停止，不提交。跑完 porcelain 只含 `index.vue` 与 `focus.test.ts`。

- [ ] **Step 4: 提交产品与测试**

```bash
git add frontend/src/views/issue/detail/index.vue frontend/src/views/issue/detail/focus.test.ts
git diff --cached --name-only
git commit -m "fix: show a focus ring on the detail edit button"
```

暂存名单必须恰好是这两行。提交后 porcelain 为空。`git diff 244c93e296a047cf138a880fa24d683b4be8203d --name-only` 恰好是白名单 4 行。

---

### Task 3: 编译器 stdout

**Files:**
- 无产品文件。命令在 worktree 的 `frontend/` 执行，输出写到日志目录。

**Interfaces:**
- Consumes: Task 2 的干净 SHA
- Produces: `.../compiler/stdout.txt`。该文件不是层叠证据

- [ ] **Step 1: 用仓库里的编译器打出返回 CSS**

CWD：`/tmp/cursor/opentask-detail-focus/frontend`。

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

以及仍在的 `[data-v-focus]:focus-visible` 和 `var(--color-accent-primary)`。meta 写明：这是编译器返回文本，不证明浏览器层叠，也不测量特异性。命令失败则 blocked。

---

### Task 4: 同一干净 SHA 的真实键盘

**Files:**
- 无产品文件。探针放在 `/tmp/cursor/opentask-readonly/detail-edit-focus-logs/browser/probe.mjs`。

**Interfaces:**
- Consumes: Task 2 的 HEAD。Vite cwd 必须是这个 worktree 的 `frontend/`。若 9527 仍服务主检出，另起 `--port 9532`，不杀掉已有进程
- Produces: 明暗两态各一份 Tab 进入与一份 Shift+Tab 返回的计算样式、对比和未裁切原图，以及两次离开消失的计算样式、一次鼠标路由记录

探针原件是本导出目录里的 `probe.mjs`。获批执行时把它原样复制到日志目录，设置 `PROBE_PORT` 与 `PROBE_OUT` 后运行。退出码非 0 就是 blocked。不改脚本让它通过，也不在本计划获批前运行它。

- [ ] **Step 1: 绑定 SHA 与 Vite**

探针前后各写 HEAD、porcelain、`readlink /proc/<pid>/cwd` 和命令行。porcelain 必须为 0。cwd 必须是本 worktree 的 frontend。页面 `http://127.0.0.1:<port>/issue/detail?id=issue-long`。只预写 `SOY_token`、`SOY_refreshToken`、`SOY_lang`。不写主题键。主题只用页眉 tooltip「主题模式」的那枚按钮。每次取样读取 `documentElement.classList.contains("dark")`。

- [ ] **Step 2: 每个主题按元素走完四步**

先反复 `keyboard.press("Tab")`，直到 `activeElement` 是 `.issue-actions` 里带 `issue-action-edit`、文本为「编辑」的按钮。安全上限 200 次。次数本身不是期望值。到不了就 blocked。到达后记录 `htmlClass`、`htmlDark`、`matches(":focus-visible")`、`outline`、`outlineStyle`、`outlineWidth`、`outlineOffset`、`outlineColor`、`boxShadow`，以及背景链和对比。通过条件与 spec §5 相同。然后保存整页图和四周各扩 8px 的裁图。

接着只按一次 Tab。这枚按钮不再是 `activeElement`，`:focus-visible` 为 false，`outline-style` 为 `none`。

接着只按一次 Shift+Tab。`activeElement` 必须回到这枚按钮。再记同一套环、对比，并另存未裁切原图。这一步不是继续按到为止。一次没有回到按钮就 blocked。

接着再只按一次 Shift+Tab。按钮再次离开，`outline-style` 为 `none`。两个 `html.dark` 取值都做。主题按钮找不到，或点击后 `html.dark` 没有变成另一值，记 blocked。`prefers-color-scheme` 只记录，不用它代替 `html.dark`。全程不调用 `element.focus()`。

- [ ] **Step 3: 贴边即 blocked**

裁图需要按钮四周 8px。`probe.mjs` 在边距不足时抛出 `ring would be cropped`，退出码非 0。这一步就是 blocked。计划里没有滚动重试，探针里也没有。不把抛错改成通过。

- [ ] **Step 4: 鼠标只核路由**

键盘取样之后，用鼠标点击这枚「编辑」。预期地址进入 `/issue/edit` 且查询参数 id 为 `issue-long`。不截鼠标图，不读鼠标当下的 outline，不点击保存。路由不对则 blocked。探针结束再记 HEAD 与 porcelain，必须与开始时的 SHA 相同且干净。

---

### Task 5: 四门禁对照当次 baseline

**Files:**
- 无产品文件

**Interfaces:**
- Consumes: Task 0 的 baseline 原文，Task 4 之后的同一个干净 SHA
- Produces: `.../gates/` 下四组 stdout、stderr、meta

- [ ] **Step 1: 原命令重跑**

CWD 仍是 worktree `frontend/`。命令与 Task 0 相同：`vitest run`、`vite build --mode prod`、`vue-tsc --noEmit --skipLibCheck`、`eslint .`。每条都有 stdout、stderr、meta。vitest 会比 Task 0 当次 baseline 摘要多出 `focus.test.ts` 的 3 个测试。把当次文件数和测试数原文留下。不回写成 86/516，也不改用 250fc 的 84 files。

- [ ] **Step 2: 逐条对照 vue-tsc 与 eslint**

去掉行号和列号后，最终诊断集合必须与 Task 0 当次 baseline 相同。允许 `index.vue` 因插入 CSS 造成行号漂移，漂移的原文要随对照记下来。多出或少掉任何一条诊断，停止。vue-tsc 仍是 EXIT 2，eslint 仍是 EXIT 1。build 仍是 EXIT 0。不把这四条写成 CI 全绿。

---

### Task 6: 两份独立 Grok 原文

**Files:**
- 无产品文件。原文写入 `.../reviews/spec.txt` 与 `.../reviews/code.txt`，旁边写 metadata：agent id、model、开始与结束时间、返回是否为空

**Interfaces:**
- Consumes: 干净最终 SHA、spec、4 路径 diff、RED/GREEN、compiler stdout、浏览器 JSON 与原图
- Produces: 两份互不引用的审阅原文。空返回或数毫秒返回不是 Pass

- [ ] **Step 1: 同时独立发起，不共用对话**

两份都用 `grok-4.7-high`，`run_in_background: false`。一份只看 spec 与计划是否被 diff 实现。一份只看 `index.vue`、`focus.test.ts`、编译 stdout 和浏览器记录。不把第一份的结论写进第二份的提示。模型调用失败则 blocked，不换模型冒充通过。

- [ ] **Step 2: 落盘后停止**

两份原文和 metadata 写入日志目录。不根据审阅改代码。不 push，不开 PR。把最终 HEAD、porcelain 和 4 路径 `git diff --name-only` 再记一次。停下来等 Yuri 验收。

---

## 证据目录

```text
/tmp/cursor/opentask-readonly/detail-edit-focus-logs/
  baseline/{vitest,build,vue-tsc,eslint}/{stdout.txt,stderr.txt,meta.txt}
  red/{stdout.txt,stderr.txt,meta.txt,porcelain.txt,test.diff,testblob.sha}
  green/{stdout.txt,stderr.txt,meta.txt,porcelain.txt,test.diff,vue.diff,testblob.sha}
  compiler/{stdout.txt,stderr.txt,meta.txt}
  browser/{probe.mjs,report.json,tab-in-html-dark-false.png,tab-in-html-dark-true.png,shift-tab-return-html-dark-false.png,shift-tab-return-html-dark-true.png,*-clip.png}
  gates/{vitest,build,vue-tsc,eslint}/{stdout.txt,stderr.txt,meta.txt}
  reviews/{spec.txt,code.txt,spec.meta,code.meta}
```

meta 每一份都含 DATE、TZ、HEAD、CWD、COMMAND、EXIT。缺任何一份，不能把该步写成完成。
