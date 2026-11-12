# 详情页通用焦点环（本页 scoped `*:focus-visible`）

Yuri 已选定方案 2：修本页已有 scoped `*:focus-visible`，改用与编辑页 / 已验「编辑」按钮相同的两档真实色；不改「编辑」专用更高优先规则；不升共享主题 token。不扩到其他页面。本文只根据精确 PR11@`ebb2a93f88bc8c5762f6823c75067de7b69bd80e` 上的只读 Tab 复现写局部方案，交审后才允许实施。当前不建分支，不 commit，不改产品，不改 PR6/7/8/9/10/11。

证据包（只读，未改产品）：sha256 `a1384fbe1d2b7dcdaed7e41c411a264f529cc70242be2396e581c71efe03e9d7`，解压于 `/workspace/designs/detail-generic-focus-repro/detail-generic-focus-repro/`。核验说明见同目录上一级 `RECEIPT.txt`。数字与计算样式以包内 `report.json`、`LIMITS.txt`、`git-after.txt` 为准。

## 1. 已测事实

树：`/tmp/cursor/opentask-detail-clone` 在探针前后都是 HEAD `ebb2a93f88bc8c5762f6823c75067de7b69bd80e`（父 `89d9bdf139ea3ba91a8288a7013cd3e81233eb25`），分支 `cursor/issue-detail-edit-focus-4333`，porcelain 空。`git-after.txt` 同时记录 MAIN `/agent/repos/opentask` HEAD `244c93e296a047cf138a880fa24d683b4be8203d`（porcelain 空，config mtime 仍为 `2026-11-11 22:28:24.300363060 +0000`）、PIN `/tmp/cursor/opentask-list-pin` HEAD `250fc34af9c64e828aab706567b0430d3d74e452`、OLD `/tmp/cursor/opentask-detail-focus` HEAD `244c93e296a047cf138a880fa24d683b4be8203d`。

Vite：pid 59419，cwd `/tmp/cursor/opentask-detail-clone/frontend`，`127.0.0.1:9541`。克隆的 `frontend/node_modules` 是指向主检出的符号链接，启动使用仓库外 `--config`，把 `cacheDir` 写到仓库外，避免写入主仓 `node_modules/.vite`。页面 `http://127.0.0.1:9541/issue/detail?id=issue-long`，视口 1280×800。打包这次探针 EXIT 0，stderr 空。

到达方式：只按键盘 Tab。没有调用 `element.focus()`，没有点击被测控件，没有为裁切滚动。主题用页眉真实按钮「主题模式」。`prefers-color-scheme` 两次都是 light。第一次探针在点击主题后重新加载了页面，`html.dark` 被清掉，该次 EXIT 2；原始记录在包内 `reload-attempt-report.json` 与 `reload-attempt-stderr.txt`。打包的 `report.json` 是后来那次：点击后在同一文档继续 Tab，没有重新加载。

「编辑」每种主题只做一次 Tab 进入，没有四步复测，不能当作 PR11 环的再次验收。

`issue-long` 上实际渲染出的操作组是这 8 个，只有「编辑」带 `issue-action-edit`：编辑、复制问题、设为子项…、状态、删除、关注、收藏到侧栏、复制分支名。源码里的「提升为根」有 `v-if canPromoteToRoot`；这个 fixture 的 `parent_issue_id` 是 null，页面上没有它，本次没有 Tab 到它。另外两个对照控件是标题行返回按钮（只有图标，没有文字、role 或 aria-label；`class` 为 `n-button n-button--default-type n-button--medium-type`）和子问题卡片里的「+ 添加」（`n-button n-button--default-type n-button--tiny-type`）。三者都在 `.issue-detail-container` 内。返回与「+ 添加」不在 `.issue-actions` 内。

浅色，操作组、返回、「+ 添加」的父级不透明叠色都是 `rgb(255, 255, 255)`。浅色返回按钮被 Tab 到时，`html.className` 还是 `nprogress-busy`；从「编辑」开始是一个空格。`html.dark` 都是 false。

| 控件 | Tab 次数 | outline | `:focus-visible` | visibleOutline | 对比 |
|---|---|---|---|---|---|
| 返回 | 28 | `rgb(51, 54, 57) none 3px`，offset 2px | true | false | 12.156226893790134 |
| 编辑 | 29 | `rgb(94, 106, 210) solid 2px`，offset 2px | true | true | 4.699901244313427 |
| 复制问题 | 30 | `rgb(51, 54, 57) none 3px` | true | false | 12.156226893790134 |
| 设为子项… | 31 | 同上 | true | false | 同上 |
| 状态 | 32 | 同上 | true | false | 同上 |
| 删除 | 33 | 同上 | true | false | 同上 |
| 关注 | 34 | 同上 | true | false | 同上 |
| 收藏到侧栏 | 35 | 同上 | true | false | 同上 |
| 复制分支名 | 36 | 同上 | true | false | 同上 |
| + 添加 | 46 | 同上 | true | false | 同上 |

浅色非编辑行的对比是探针对着未画出的不透明色 `rgb(51, 54, 57)` 算出来的。`outline-style` 为 `none`，`visibleOutline` 为 false。这不是可见环过 3:1。

深色，`html.className` 是 `dark`。操作组和返回的父级叠色是 `rgb(15, 16, 17)`；「+ 添加」是 `rgb(24, 24, 28)`（第一层不透明祖先是 `n-card n-card--bordered mt-12px`）。

| 控件 | Tab 次数 | outline | visibleOutline | 对比 |
|---|---|---|---|---|
| 返回 | 19 | `rgba(255, 255, 255, 0.82) none 3px`，offset 2px | false | null |
| 编辑 | 20 | `rgb(130, 143, 255) solid 2px`，offset 2px | true | 6.641271715242952 |
| 复制问题到复制分支名 | 21–27 | `rgba(255, 255, 255, 0.82) none 3px` | false | null |
| + 添加 | 37 | 同上 | false | null |

深色非编辑对比是 null，因为描边色 alpha 是 0.82，探针在颜色不透明之前不计算比值。这不是一个低于 3:1 的比值。全部测量点的 `box-shadow` 都是 `none`。

`--issue-focus` 在元素和 `.issue-detail-container` 上已经是两档字符串：浅色 `2px solid #5e6ad2`，深色 `2px solid #828fff`。它在 `html` 上为空。`--color-accent-primary` 在元素、容器、`html` 上两种主题都是空字符串。`--color-primary` 在容器和 `html` 上两种主题都是 `#5e6ad2`，暗色不会变成 `#828fff`，不能单独拿来做深色档。

只有「编辑」的 `outline-style` 是 `solid`，所以只有它有 8px 裁图。其余控件没有描边环，包内保留未裁剪视口原图。

## 2. 源码来源

文件仍是 `frontend/src/views/issue/detail/index.vue` 的唯一 `<style scoped>`。`source-inventory.txt` 记录当前已验三块与其后的通用规则仍在：

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
*:focus-visible {
  outline: 2px solid var(--color-accent-primary);
  outline-offset: 2px;
}
```

通用规则的颜色来自空的 `--color-accent-primary`，所以同页其他可焦点控件虽然匹配 `:focus-visible`，计算出的 `outline-style` 仍是 `none`。PR11 已按方案 A 给「编辑」单独加了更高优先规则，并明确不改这条通用规则。本轮只改这一条通用规则的颜色来源。

现有 `frontend/src/views/issue/detail/focus.test.ts` 把通用规则原文（含 `var(--color-accent-primary)`）冻在断言里。若改通用规则，必须同步改这处冻结，不能假装原文还在。专用「编辑」规则、`issue-action-edit` 只出现一次、以及按钮文案 / 可见条件 / 原路由的断言保持不变。

本页 scoped `*:focus-visible` 只作用于本 SFC 带有该 scope 属性的节点（例如本模板里的 `NButton` 根）。应用顶栏、侧栏等其他组件不在本规则范围内。本轮也不用 `:deep()` 把规则打进子组件内部。

## 3. 局部规则（方案 2）

只改上面那一条通用规则，写成复用容器上已经存在、已经两档生效的 `--issue-focus`：

```css
*:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}
```

`--issue-focus` 的两处定义，以及

```css
.issue-detail-container .issue-actions .n-button.issue-action-edit:focus-visible {
  outline: var(--issue-focus);
  outline-offset: 2px;
}
```

必须保持原文，不改选择器、不改属性、不加 `!important`、不移动到通用规则之后并削弱它。不给同组其他按钮加 `issue-action-edit`（那是方案 1）。不在本页或全局把 `--color-accent-primary` 填成实色：未审计本页其他引用，填写空 token 可能超出焦点环。不把 `--issue-focus` 或这两档色提升到 `issue-surface.css` 或其它共享样式。不改 naive 主题，不改 `.n-button__state-border`。不改其他页面。

为什么这样不会盖过已验「编辑」环：

1. 专用规则的静态特异性仍高于 scoped `*:focus-visible`（先前设计按选择器计数：专用约 (0, 6, 0)，通用 `[data-v-xxxx]:focus-visible` 为 (0, 2, 0)）。通用规则即使写在后面，在不提高自身特异性、不加 `!important` 的前提下，赢不了专用规则。
2. 专用规则继续使用同一个 `--issue-focus`，色值仍是已验收的 `#5e6ad2` / `#828fff`（计算值为 `rgb(94, 106, 210)` / `rgb(130, 143, 255)`），宽度 2px、style solid、offset 2px。
3. 验收必须用真实 Tab 再测「编辑」：两种 `html.dark` 下，环的计算条件仍须与 PR11 相同；不能只看同组其他按钮已经出现环。

改完之后，通用规则与专用规则在「编辑」上会画出同一套两档色；保护来自特异性与专用规则原文不动，而不是靠两套不同的颜色。

## 4. 对比门槛

焦点环对着当次实测不透明表面，至少 3:1。详情文字用过的 4.5 不替换这个 3:1。

下面两组是本次包里「编辑」已经测过的环色对叠色，改通用规则后，叠色相同的控件可以预期同一比值，但仍须在实施后的干净 SHA 上重新 Tab 测量，不能拿本节旧数字代替当次测量。

- 没有 `dark` 类、叠色 `rgb(255, 255, 255)`、环色 `#5e6ad2`：`4.699901244313427`，过 3。本次浅色返回、操作组、「+ 添加」的叠色都是这层白。
- 有 `dark` 类、叠色 `rgb(15, 16, 17)`、环色 `#828fff`：`6.641271715242952`，过 3。本次深色返回与操作组的叠色是这层。

深色「+ 添加」的叠色是 `rgb(24, 24, 28)`，包里没有这层上的实色环样品。用同一通道阈值 0.04045、对已记录的 `#828fff` = `rgb(130, 143, 255)` 与该叠色做计算，得到 `6.172467713917881`，过 3。这是计算，不是改规则之后的 Tab 测量。验收时必须在该控件上重测。

`#828fff` 对白底仍是先前设计里的 `2.86801025674667`，不过 3。这一档只出现在 `html.dark` 下的 `--issue-focus`，通用规则不得在没有 `dark` 类时使用它。也不得只用 `--color-primary`（两种主题都是 `#5e6ad2`）。

背景若不再是上述叠色，用当次叠色重算，仍须至少 3:1。

## 5. 键盘、鼠标、范围

新的通用规则继续只用 `:focus-visible`，不另写一条 `:focus` outline。是否匹配由浏览器启发式决定。本文不承诺只有 Tab 会匹配，也不承诺鼠标点击绝不会出现这圈。

验收在同一个最终干净 SHA 上做。`html.dark` 的两种取值都做。不调用 `element.focus()`。通过与否看 `activeElement` 是不是目标控件，不看某一固定的 Tab 次数。可见环的计算条件每次都是：`outline-style` 为 `solid`，`outline-width` 为 `2px`，`outline-offset` 为 `2px`；没有 `dark` 类时颜色是 `rgb(94, 106, 210)`，有 `dark` 类时是 `rgb(130, 143, 255)`；相对当次不透明背景链的对比至少 3。离开时它不再是 `activeElement`，不再匹配 `:focus-visible`，`outline-style` 为 `none`。

每种主题至少覆盖：

1. 「编辑」按 PR11 的四步（Tab 进入、再 Tab 离开、Shift+Tab 回到、再 Shift+Tab 离开），确认专用规则未被盖过。
2. 同组已渲染的非编辑按钮：复制问题、设为子项…、状态、删除、关注、收藏到侧栏、复制分支名。每个至少一次真实 Tab 进入，记录计算样式、对比和未裁切原图（有可见环时按先前 8px 裁图规则；距视口边缘不足 8px 则抛错，不滚动、不二次拍摄）。
3. 页内另外两个已测对照：标题行返回、「+ 添加」，同样至少一次 Tab 进入。

「提升为根」在 `issue-long` 上不渲染。本轮若要用真实 Tab 覆盖它，必须另用一个 `parent_issue_id` 非空、能画出该按钮的 fixture；否则把它明确列为未测限制，不得写成已验收。本轮不为它改 fixture 范围，除非计划审查另批。

鼠标：被测控件现有点击行为不改。不要求鼠标截图，也不要求断言鼠标当时没有环。

本轮不加禁用态规则。问题已删除时整块 `.issue-actions` 仍按现有 `v-if` 不渲染。

## 6. 拟议路径（待计划审查锁定）

获批并完成计划后，预期产品改动只在：

- `frontend/src/views/issue/detail/index.vue`（只改通用 `*:focus-visible` 的 outline 颜色来源）
- `frontend/src/views/issue/detail/focus.test.ts`（把冻结的通用规则原文改成第 3 节文本；专用规则与「编辑」合同保持）
- 本设计与后续计划两份 docs

精确路径名单与 commit 切割留给计划。基线仍是 exact `ebb2a93f` 的隔离分支，不 amend、不 rebase 已验 SHA，不改已有 PR 的 head。

## 7. 不在本轮 / 已保留限制

- 不实施、不推送、不 PR、不 merge、不 deploy，直到设计与计划都获批。
- 不改 PR6/7/8/9/10/11 的 SHA、分支或正文。
- 不扩到其他页面，不升共享主题 token，不填写 `--color-accent-primary`，不改 naive 主题。
- 钩子路径仍按 PR11 保留限制：没有当次 hook 打开路径原件，不得把 commit-msg 写成已校验本检出说明。
- 本次复现：第一次主题点击后重载（EXIT 2）原件保留；浅色返回取样时 `html` 仍带 `nprogress-busy`；深色非编辑对比为 null 不是低于 3:1；「编辑」未经四步复测；鼠标未测；「提升为根」未渲染；`prefers-color-scheme` 两次都是 light，主题只靠 `html.dark`。
- 本页其它未取样的可焦点节点（若带本 SFC scope 属性）会随通用规则一起变，但不纳入本轮必测名单，也不把未测写成已验收。
