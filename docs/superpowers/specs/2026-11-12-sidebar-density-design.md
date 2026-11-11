# 侧栏密度与快捷入口图标

日期：2026-11-12。基线 SHA：`088a34308cb0fe75a95f129432ee67b8f54067c3`。  
状态：密度、折叠空收藏的 Tab 停点、图标选项 1 都已批准。本文件是这一条侧栏切片的规格。它不授权在本次文档修正里开分支、提交或改产品代码。详情/编辑是下一条切片，等本切片验收之后再开始。

## 1. 范围

一条切片同时做两件事：快捷入口的 34px / 6px 密度，以及四颗彩色 emoji 换成各路由已经写下的 Iconify id。不另开图标 PR。

不改 Logo、`frontend/src/components/custom/svg-icon.vue`、`frontend/src/router/elegant/routes.ts`、`vertical-menu.vue`、`linear-shell.css`、菜单项、收藏项里的 emoji、详情和编辑。

## 2. 已批准的密度

菜单盒高 34px、`margin-top: 6px` 保持。它们来自 `linear-shell.css` 的 `--n-item-height: 34px` 和 Naive 菜单自身的间距。

`.global-sider__quick`：`gap: 6px`。展开 `padding: 6px 8px 0`。折叠 `padding: 6px 0 0`，`align-items: center`。四个子组件根的 padding 和 margin 都是 0。

展开内容盒高 34px，`padding: 0 8px`，`border-radius: 6px`。折叠可见轨上的命中区是 36×36。375 抽屉关闭时 `aside` 宽仍是 0。

收藏保持 `max-height: 40%` 和 `overflow: auto`。有数据时仍是两行，不压成 34px。亮色「收藏」标题离开 `NText depth=3`，改为 `p.favorites-nav__title`：`font-size: 12px; line-height: 18px; color: var(--vk-muted); margin: 0 0 6px; padding: 0 8px`。展开空说明是静态 `p.favorites-nav__empty-note`，文案仍是「暂无侧栏收藏」，同一字号和行高，`margin: 0; padding: 0 8px; color: var(--vk-muted)`。折叠且空时不渲染收藏根，因此没有「无数据」Tab 停点。

## 3. 已批准的图标

基线模板里的文本是：分诊 `📥`，客户 `👥`，洞察 `📈`，活动 `🔔`。没有图标 import。

下栏通过 `getGlobalMenuByBaseRoute` → `useSvgIcon()` → `SvgIcon` → `@iconify/vue` 的 `Icon` 渲染。菜单 vnode 默认 `fontSize: 20`。`SvgIcon` 把 `style` 传给 `Icon`，并且 `inheritAttrs: false`，不转发 `aria-hidden`。`Icon` 自己的 SVG 默认带 `aria-hidden: true`。装饰层仍要在四个 SFC 里用包裹元素写 `aria-hidden="true"`，这样不改共享组件也能从名称里拿掉图标。

| 入口 | 路由 `meta.icon` | 折叠 `aria-label` 与 tooltip |
|---|---|---|
| 分诊 | `mdi:inbox-arrow-down` | `$t('page.sider.triage')`：分诊 / Triage |
| 客户 | `mdi:account-group-outline` | `$t('page.sider.customers')`：客户 / Customers |
| 洞察 | `mdi:chart-box-outline` | `$t('page.sider.insights')`：洞察 / Insights |
| 活动 | `mdi:timeline-text-outline` | `$t('page.sider.activity')`，有未读时加上现有的 `（${badge}）` |

展开按钮不设 `aria-label`。名称仍是可见的主标签加 hint：入站 / Incoming，需求 / Requests，效能 / Performance，动态 / Recent。活动有未读时，展开按钮里的徽章文本留在按钮内。

图标 `font-size: 20px`，`color: currentColor`。hover 和 `.active` 仍只改变背景为 `--vk-accent-soft`。四个按钮增加本组件内的 `:focus-visible` 环：`outline: 2px solid var(--vk-accent)`，`outline-offset: 2px`。不改全局焦点样式。

`go()`、路由名、权限和 `.active` 的判断保持原样。

## 4. 文件计数

文档，恰好 2 个，只在实施被另行授权之后的第一次提交里入库：

- `docs/superpowers/specs/2026-11-12-sidebar-density-design.md`
- `docs/superpowers/plans/2026-11-12-sidebar-density.md`

产品与测试，恰好 8 个，与上面 2 个分开计数：

- `frontend/src/layouts/modules/global-sider/index.vue`
- `frontend/src/layouts/modules/global-sider/TriageNav.vue`
- `frontend/src/layouts/modules/global-sider/CustomersNav.vue`
- `frontend/src/layouts/modules/global-sider/InsightsNav.vue`
- `frontend/src/layouts/modules/global-sider/ActivityNav.vue`
- `frontend/src/layouts/modules/global-sider/FavoritesNav.vue`
- `frontend/src/layouts/modules/global-sider/density-invariants.test.ts`
- `frontend/src/layouts/modules/global-sider/density-contract.test.ts`

## 5. 滚动与未测基线

1280×480 加上 8 条收藏并不被当成「收藏和菜单一定同时溢出」。收藏 `max-height: 40%` 是否产生滚动，菜单剩余高度是否产生滚动，都要在实施后的页面上读 `scrollHeight` 和 `clientHeight`。溢出的容器要能把 `scrollTop` 真正改到末尾，并且该容器里的最后一项可以到达。没有溢出就记录 `nooverflow`。不为了满足旧假设去改高度或行数。合成数据可以加长到收藏内容超过 40% 上限；产品 CSS 不跟着加高。

基线没有低高度、1 条、8 条、折叠且有收藏、768 有收藏的截图。那些验收是实施之后的新测量。

## 6. 终审门禁

最后一次代码提交之后，在同一个 FINAL SHA 上保存四份当次日志：全量 `pnpm exec vitest run`、`pnpm exec vue-tsc --noEmit --skipLibCheck`、`pnpm exec eslint .`、`pnpm exec vite build --mode prod`。vue-tsc 与同一组 29 条逐条对照，退出码 2 仍记为失败。ESLint 与实施前在 `088a343` 上当次跑出的逐条诊断对照，非零仍记为失败。构建期望退出码 0。非零的 typecheck 或 lint 不能挡住后面的命令。源码字符串包含某个 class，不能代替浏览器里的 SVG、无 emoji 和中英文可访问名称。
