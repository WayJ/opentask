# 问题列表操作列钉住条件

修订稿。第 2、4、5 节按已通过的文字保留。第 3、7 节按这次批准改过。仍不进仓库。Yuri 批准计划之后，第一笔提交才把本 spec 和计划写入 `docs/`。

依赖是 PR7 的 `088a34308cb0fe75a95f129432ee67b8f54067c3`，分支 `cursor/issue-surface-visual-ab12`。不从 PR #6、#7、#8、#9 上改。

## 1. 目标

操作列只在这张列表表的横滚容器放得下「编号」到「负责人」的完整列，再加上操作列自己的宽度时，才 `fixed: 'right'`。放不下，或还没量到宽度，就不钉。负责人及其左侧列不被这列盖住。

不保证报告人、创建时间和操作列在同一屏里同时完整。报告人和创建时间靠横滚能看到。

## 2. 阈值 T

T 从同一组布局值相加得到。这组值同时给列定义和门槛用，不在 `index.vue` 里再抄一遍数字。

已有名字保持不变：编号用 `ISSUE_CODE_COLUMN_WIDTH`（120），钉住时的标题宽用 `ISSUE_TITLE_COLUMN_MAX`（300）。类型、状态、优先级、估点、负责人、操作的宽度现在写在 `baseColumns` 里，分别是 100、120、100、72、120、200。实施时把这六个数收进 `column-layout.ts` 的同一组导出，列定义改为引用它们。

按 `088a343` 这份源码，相加是 1132。1132 不是写进代码或测试的字面量。测试从导出的值计算 T。

标题不钉住时仍按现有公式变窄，`TITLE_GUTTER` 仍是 24。T 用钉住时的标题宽 300，因为要比的是钉住之后放不放得下。

`ISSUE_ACTIONS_PIN_MIN`（900）不再作为钉住门槛。

负责人右边的自定义列仍由现有 `splice` 插入，不进 T，也不保证不被挡住。不新增自定义列功能。

报告人 120 和创建时间 150 不进 T。

## 3. 读哪一个节点

只在未分组那张 `<NDataTable>` 的 `$el` 里面找 `.n-data-table-base-table-body .n-scrollbar-container`。`DataTable.mjs` 第 421 行的 render 返回单个 `div.n-data-table`。Vue 3.5.27 的 `$el` 就是 `vnode.el`（`vue.runtime.esm-browser.js` 第 5497 行），所以这个根可以做 `querySelector` 的起点。禁止 `document` 上的全局查询，也禁止拿列表根里第一张 `.n-data-table`。

`index.vue` 不自己写观察器。`column-layout.ts` 导出 `createListScrollBinder`。页面只提供表根、宽度回调、`nextTick`、是否仍挂载。这样做是因为生命周期要用假的观察器直接断言 `observe` 和 `disconnect`，而 `index.vue` 整页挂载不在这三条产品路径的测试边界里。源码字符串只检查页面有没有接上这个函数，不能代替这些断言。

宽度为 0 的节点仍然 `observe`。回调把宽度记成 0，不钉。同一个节点从 0 变成正数时，这次观察的回调更新宽度。没有节点、表根还不是 `Element`、看板或分组把这张表卸掉、或页面已卸载：不观察横滚节点，宽度记 0。

表根已经在、横滚节点稍后才出现时，对表根使用 `MutationObserver`（`childList: true`，`subtree: true`）。子节点换掉时也走同一条同步：查到的节点若不是正在观察的那个，先 `disconnect` 旧的 `ResizeObserver`，再观察新节点。观察器编号只增加，卸掉时不得清回 0。新节点绑上之后，旧的 resize 回调和旧的 mutation 回调都不得再 `observe`，也不得再调用 `onWidth`。卸载之后同样不得。只排队一次 `nextTick` 不等到节点出现。Vue 的 `nextTick`（同文件第 2518–2520 行）是 `promise.then`，卸载不会取消它。`schedule` 的代次和 `isActive()` 任一失效，排队回调不得再 `observe`。

`onUnmounted` 先把 `isActive` 设为 false，再 `disconnect`。`tableWidth` 初值是 0，不再用 `window.innerWidth`。列表根上的现有观察器去掉。

`index.vue` 只加这些绑定和生命周期。排序、筛选、权限、保存、删除、分页不改。

## 4. T-1、T、T+1

`clientWidth <= 0`：不钉，标题仍用 `ISSUE_TITLE_COLUMN_MAX`。0 不是一张窄表，不用缩小公式。
`clientWidth <= T - 1`：不钉。
`clientWidth === T`：钉。
`clientWidth >= T + 1`：钉。

比较是 `clientWidth > 0 && clientWidth >= T`。T 来自第 2 节的导出值。

## 5. 保证和几何限制

钉住之后，横滚在最左时，编号到负责人这些列的右缘不越过操作列左缘。只保证这些列。

容器刚好等于 T 时，报告人从操作列左缘开始，固定的操作列仍盖住报告人。报告人要躲开操作列，容器至少还要再加报告人列宽。创建时间在报告人右边。这是列宽关系，宽桌面是否如此要在实施时量，不能靠本草案的旧样本代替。

横滚到末端时，报告人、创建时间和操作按钮都在可视范围内。不承诺未滚动时全列同时完整。

## 6. 不变量

标题继续 `whiteSpace: 'normal'`。编号列宽保持 120。负责人列宽保持 120。操作列宽保持 200。`onListSortByUpdate`、`onListSortOrderUpdate`、`handleFilterChange`、`clearFilters`、`handleSmartSearch`、`loadWorkspaceRole` 的函数体不改。

不改全局菜单，不改 PR8 的侧栏，不改 PR #9 的详情和编辑。

## 7. 路径

产品与测试三条：

- `frontend/src/views/issue/list/column-layout.ts`
- `frontend/src/views/issue/list/column-layout.test.ts`
- `frontend/src/views/issue/list/index.vue`

文档两条，批准计划后的第一笔提交入库，不长期留在仓库外：

- `docs/superpowers/specs/2026-11-12-issue-list-pin-design.md`
- `docs/superpowers/plans/2026-11-12-issue-list-pin.md`

`IssueListGrouped.vue` 不在这五条里。分组显示时未分组表不在文档里，按没量到宽度处理，不钉。不把分组表加进本轮。

## 8. 证据

单元测试从导出的 T 断言 0、`T - 1`、`T`、`T + 1`。选择器测试把完整的 `.n-data-table-base-table-body .n-scrollbar-container` 放在表根之外、并且位于文档更前面；`document.querySelector` 会命中这只诱饵，函数必须返回表根里面的节点。

绑定单元的测试直接调用假观察器的 `observe`、`disconnect` 和保存下来的回调。覆盖：0 宽节点仍被观察且不钉；0 变为正数；节点晚出现；节点被换掉后观察新节点；旧回调在新绑定之后不再 `observe`、不再 `onWidth`；表根卸掉再挂上后旧的 mutation 回调同样如此；`disconnect` 和卸载之后也是。

浏览器在明暗都生效的前提下，交叉 375、768、1280、宽桌面，以及 `T - 1`、`T`、`T + 1`。`SOY_themeSettings` 不存在，或切换后 `html` 没有对应的 `dark` 类，这一档记 `blocked`，不把该档的图当成通过。宽桌面要有一条真实的 `clientWidth >= T + 报告人列宽`。报告人和创建时间的矩形只作记录，不因此扩大第 5 节的保证。校准对不上目标宽度时记 `blocked`，尝试列表保持原样。侧栏点击之后 `clientWidth` 必须变化，并且 `fixed === (clientWidth > 0 && clientWidth >= T)`。窄宽要有跨过门槛再折返的断言。横滚末端和 Tab 在重新设成 1280 和宽桌面视口之后各做一次。探针和 Tab 不点击删除，也不发出变更请求。

本修订没有新的浏览器采样。已有绑定只覆盖 1280 亮色。375、768、暗色、宽桌面、Tab、侧栏、看板来回仍是 absent。
