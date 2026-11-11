# 详情「编辑」按钮的两档焦点环

Yuri 已批准方案 A，以及原先草案的事实、源码、局部两档环和 3:1 门槛。整组按钮与全局焦点不在本轮。本文修正编译结果的标法，并把键盘与鼠标的验收改成浏览器启发式下能观察的行为。

本文件获批之后才允许从 exact `244c93e296a047cf138a880fa24d683b4be8203d` 开隔离分支。当前不建分支，不 commit，不改产品。PR #10 与既有 PR 不动。PR #10 缺失的历史 TDD 日志仍然缺证，本文不追认。

文件名沿用同目录已有文档的 `2026-11-12` 前缀。

## 1. 已测事实

树：`/agent/repos/opentask` HEAD `244c93e296a047cf138a880fa24d683b4be8203d`，分支 `cursor/issue-detail-edit-4333`。探针前后 porcelain 都是 0 字节。Pin 树 HEAD 仍是 `250fc34af9c64e828aab706567b0430d3d74e452`，porcelain 0。

Vite：pid 22995，`/proc/22995/cwd` 为 `/agent/repos/opentask/frontend`。命令行是 `pnpm exec vite --mode prod --host 127.0.0.1 --port 9527 --strictPort`。页面 `http://127.0.0.1:9527/issue/detail?id=issue-long`。

到达方式：只按键盘 Tab。没有调用 `element.focus()`，没有点击「编辑」。第一次从页面起始按 29 次，`activeElement` 是 `.issue-actions` 内文本为「编辑」的 `BUTTON`。主题按钮点过之后再按 20 次，再次停在同一枚按钮。没有做 Shift+Tab。

主题：探针只写入 `SOY_token`、`SOY_refreshToken`、`SOY_lang`。没有写主题 storage。页面加载后应用自己已有 `SOY_darkMode` 等键。切换用页眉真实按钮，tooltip 文案是「主题模式」（`frontend/src/locales/langs/zh-cn.ts` 第 724 行）。`prefers-color-scheme` 两次都是 light。

- 点击前 `htmlDark` false。第一次取样时 `documentElement.className` 是一个空格；另一次 Tab 取样停在 `nprogress-busy`。两次都没有 `dark`。
- 点一次主题按钮后 `className` 为 `dark`，`htmlDark` true。

主题由 `html` 是否带 `dark` 决定。`html.dark` 为 false 只记录暗色类不存在。

两次 Tab 停在目标上时：

| 读取 | `html.dark` false | `html.dark` true |
| --- | --- | --- |
| `:focus-visible` | true | true |
| 页内编译选择器 `[data-v-23e76b62]:focus-visible` | 匹配 | 匹配 |
| `outline` | `rgb(51, 54, 57) none 3px` | `rgba(255, 255, 255, 0.82) none 3px` |
| `outline-style` | none | none |
| `box-shadow` | none | none |
| `disabled` / `aria-disabled` | false / null | false / null |
| `.n-button__state-border` | `1px solid rgba(0, 0, 0, 0)` | `1px solid rgba(0, 0, 0, 0)` |

按钮自身背景和 `.issue-actions`、`.n-button-group` 都是 `rgba(0, 0, 0, 0)`。第一层不透明祖先是 `.issue-header`：类不存在时 `rgb(255, 255, 255)`，类存在时 `rgb(15, 16, 17)`。叠色 alpha 为 1。

`--color-accent-primary`、`--issue-accent`、`--issue-focus` 在按钮、`.issue-detail-container` 和根上的计算值都是空。这三项对比 absent。`--color-primary` 两边都是 `#5e6ad2`。

相对 `.issue-header` 的不透明叠色：

- `#5e6ad2` 对 `rgb(255, 255, 255)`：`4.699901244313427`
- `#828fff` 对 `rgb(255, 255, 255)`：`2.86801025674667`
- `#5e6ad2` 对 `rgb(15, 16, 17)`：`4.052688430465267`
- `#828fff` 对 `rgb(15, 16, 17)`：`6.641271715242952`

当前 `outline-style` 为 none，环没有画出来。暗色那条 `rgba(255, 255, 255, 0.82)` 带透明，不计算可见环对比。

`detail-244c-edit-focus/probe.mjs` 使用 `button.focus()`，不是 Tab。那份 `sample.json` 不计入本次 Tab。

## 2. 源码来源

`/agent/repos/opentask/frontend/src/views/issue/detail/index.vue`

- 第 1432 行根节点 `class="issue-detail-container"`。
- 第 1478–1485 行：`v-if="!issue.is_deleted"` 时，`.issue-actions` 第一枚 `NButton` 文本是「编辑」，`@click` 是 `router.push({ path: '/issue/edit', query: { id: issue.id } })`。没有 `disabled`，没有 `loading`。
- 第 2351 行起是唯一的 `<style scoped>`，第 2881 行结束。
- 第 2444–2448 行 `.issue-actions` 只设 flex。
- 第 2802–2804 行保留：`*:focus-visible { outline: 2px solid var(--color-accent-primary); outline-offset: 2px; }`。

运行页 `<style>` 文本里，这条旧规则编译成 `[data-v-23e76b62]:focus-visible`。这是页面样式文本，不是一次 `compileStyle` 命令的 stdout。按钮属性里有空的 `data-v-23e76b62`。该选择器的静态特异性是一个属性加一个伪类，(0, 2, 0)。Tab 取样时它匹配，同时 `--color-accent-primary` 为空，计算出的 `outline-style` 仍是 none。

`frontend/node_modules/naive-ui/es/button/src/Button.mjs` 没有 `inheritAttrs: false`。加在 `NButton` 上的 `class` 按 Vue 3 默认规则落到根节点。`frontend/node_modules/naive-ui/es/button/src/styles/index.cssr.mjs` 第 51 行在 `cB('button', ...)` 的模板里写了 `outline: none`。发出的类是 `.n-button`，静态特异性 (0, 1, 0)。这是源码事实。当时的样式表遍历没有收成一条匹配的 outline 规则，所以本文不把这条 naive 规则写成已经赢下的层叠。

编辑页同档在 `frontend/src/views/issue/edit/index.vue`：第 494 行 `--issue-focus: 2px solid #5e6ad2`，第 511 行 `--issue-focus: 2px solid #828fff`。`frontend/src/styles/issue-surface.css` 第 1–2 行和第 16–17 行的选择器只有 `.issue-list-container` 与 `.issue-create-page`，第 13 和 28 行是同样两档。详情容器不在其中，所以详情上 `--issue-focus` 为空。

`frontend/src/styles/design-system.css` 第 4 行 `--color-primary: #5e6ad2`。第 67 行 `html.dark` 没有改写它。暗色档不能靠这个变量得到 `#828fff`。

`frontend/src/constants/app.ts` 第 63 行 `DARK_CLASS = 'dark'`。

## 3. 局部规则

只在 `index.vue` 的 scoped 样式里增加下面三块，并给第 1480 行那一枚 `NButton` 加上 `class="issue-action-edit"`。同组其他按钮不加这个类。第 2802 行旧规则原文不动。

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

两档色值与编辑页第 494、511 行相同。不使用空的 `--color-accent-primary` 作为这圈的颜色。

拟议编译结果，不是已保存的命令 stdout，也不是浏览器层叠：若用当前页面见到的 scope id，并调用 `@vue/compiler-sfc` 3.5.44 的 `compileStyle({ id: 'data-v-23e76b62', scoped: true })`，属性会落在最后一个复合选择器上，形成

```css
.issue-detail-container .issue-actions .n-button.issue-action-edit[data-v-23e76b62]:focus-visible
```

实施时的 scope id 由编译器按当次 SFC 重新生成，不保证仍是 `23e76b62`。持久测试用固定 id `focus`，只锁定编译器返回的选择器字符串。真正的层叠以同一最终 SHA 上的浏览器计算样式为准。

静态特异性，只按选择器计数，不是浏览器测量：四个类、一个属性、一个 `:focus-visible`，(0, 6, 0)。它高于 `.n-button` 的 (0, 1, 0)，也高于现有 `[data-v-xxxx]:focus-visible` 的 (0, 2, 0)。不用 `!important`。

## 4. 对比门槛

焦点环对着实测不透明表面，至少 3:1。详情文字用过的 4.5 不替换这个 3:1。

- 没有 `dark` 类时用 `#5e6ad2`：对白底 `4.699901244313427`，过 3，也过 4.5。
- 有 `dark` 类时用 `#828fff`：对 `rgb(15, 16, 17)` `6.641271715242952`，过 3，也过 4.5。
- `#828fff` 对白底是 `2.86801025674667`，不过 3。这一档只放在 `html.dark .issue-detail-container`。
- 暗色若用 `#5e6ad2`，对 `rgb(15, 16, 17)` 是 `4.052688430465267`，过 3，不过 4.5。暗色档仍用编辑页的 `#828fff`。

验收时重新测量当次有效背景链。背景若不再是这两层不透明色，用当次叠色重算，仍须至少 3:1。不能拿本节旧数字代替当次测量。

## 5. 键盘、鼠标、禁用

新规则使用 `:focus-visible`，不另写一条 `:focus` outline。`:focus-visible` 是否匹配由浏览器启发式决定。本文不承诺只有 Tab 会匹配，也不承诺鼠标点击绝不会出现这圈。

验收在同一个最终干净 SHA 上做。`html.dark` 的两种取值都做。通过与否看 `activeElement` 是不是这枚按钮，不看某一固定的 Tab 次数。不调用 `element.focus()`。环的计算条件每次都是：`outline-style` 为 `solid`，`outline-width` 为 `2px`，`outline-offset` 为 `2px`；没有 `dark` 类时颜色是 `rgb(94, 106, 210)`，有 `dark` 类时是 `rgb(130, 143, 255)`；相对当次不透明背景链的对比至少 3。离开时它不再是 `activeElement`，不再匹配 `:focus-visible`，`outline-style` 为 `none`。

每个主题的顺序是：

1. 反复按 Tab，直到这枚按钮成为 `activeElement`。记录环、对比，并保存未裁切原图。
2. 再按一次 Tab。焦点离开，环消失。
3. 再按一次 Shift+Tab。`activeElement` 回到这枚按钮。再记录环、对比，并另存一张未裁切原图。
4. 再按一次 Shift+Tab。焦点再次离开，环消失。

原图在按钮边框外留出 8px，盖住 offset 2px 和宽度 2px。按钮距视口边缘不足 8px 时，探针直接抛错，该步 blocked。不滚动，也不做第二次拍摄。

鼠标点击后仍进入 `/issue/edit`，查询参数仍是当前问题 id。可见性、文案「编辑」、`v-if` 和这段路由不改。不要求鼠标截图，也不要求断言鼠标当时没有环。

`.n-button__state-border` 维持现有规则，本轮不改它，也不改按钮静止边框。

这枚按钮没有禁用绑定。问题已删除时，第 1478 行的 `v-if` 不渲染整块 `.issue-actions`。本轮不加禁用态规则。

## 6. 白名单与测试文件

将来获批后的 diff 恰好 4 条路径：

- `docs/superpowers/specs/2026-11-12-issue-detail-edit-focus-design.md`
- `docs/superpowers/plans/2026-11-12-issue-detail-edit-focus.md`
- `frontend/src/views/issue/detail/index.vue`
- `frontend/src/views/issue/detail/focus.test.ts`

持久回归只有 `focus.test.ts` 一份。不追加到 `description-surface.test.ts`。该文件的 `describe` 是详情描述暗色表面：它编译 id 为 `surface`，夹具是 `description-content` 里的 `pre.hljs` 和行内 `code`，不断言按钮、outline 或路由。把焦点断言放进去会让描述合同和按钮合同共用一次失败。两份测试同时存在也不符合「只留一份」。

`focus.test.ts` 锁定四件事：按钮文案、可见条件、原路由表达式；旧的 `*:focus-visible` 原文还在；`class="issue-action-edit"` 只出现一次，选择器字符串里可以再出现这个类名；`compileStyle` 返回的字符串含拟议选择器。编译器字符串不是层叠证明。层叠由浏览器计算样式证明。

## 7. 不在本轮

不改同组其他按钮，不改第 2802 行旧规则，不改 naive 主题，不改保存和权限。不测 375、768、分组列表，不重跑 PR #10 矩阵。除这枚「编辑」按钮以外的控件没有新的焦点测量。
