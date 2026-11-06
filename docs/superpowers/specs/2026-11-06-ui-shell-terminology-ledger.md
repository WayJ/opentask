# 界面缺陷台账

日期：2026-11-06  
基线：`main` @ `f2f81c51fda85bf48221d7f84a2f56d071e7704e`（PR #4 已合并）  
状态：已在当前代码核对。本文件不表示已经修好。

确认缺陷是现网或代码路径上已经发生的错误。美化项是同一批范围内的外观整理，不改变数据和操作。

| ID | 类别 | 优先级 | 现象 | 代码证据 | 处理 |
|---|---|---|---|---|---|
| UI-1 | 确认缺陷 | P0 | 快捷入口「客户」打开 `/customers/detail`。浏览器标题、内部标签是字面量 `route.customers_detail`。正文是「客户详情」。面包屑为空。 | `CustomersNav.vue` 的 `go()` 推 `name: 'customers'`。`transform.ts` 在父路由有子路由且没有 `redirect` 时重定向到第一个子路由。`routes.ts` 里 `customers` 的组件是 `layout.base`，唯一子路由是 `customers_detail`，路径 `/customers/detail`，没有 id。`zh-cn.ts` / `en-us.ts` 的 `route` 都没有 `customers` 和 `customers_detail`。父路由 `hideInMenu: true`，所以 `getGlobalMenusByAuthRoutes` 不会把它放进菜单，`getBreadcrumbsByRoute` 返回空数组。列表页 `views/customers/index.vue` 已存在，标题就是「客户」，`imports.ts` 已有 `customers`，但生成路由没有把它挂上。 | 把已有列表挂成默认子路由。详情保持 `/customers/detail?id=`，并从菜单隐藏。补上两种语言的文案。无 id 时回到列表，不展示空表单。 |
| UI-2 | 确认缺陷 | P0 | 设置菜单、浏览器标题、内部标签、面包屑都是字面量 `route.settings_sla`。正文卡片标题是「SLA 策略」。 | 生效路由在 `frontend/src/router/routes/index.ts` 的 custom `settings_sla`，`i18nKey` 为 `route.settings_sla`。两种语言的 `route` 对象都没有这个键。页面 `views/settings/sla/index.vue` 的卡片标题已经是「SLA 策略」。标题守卫用 `$t(i18nKey)`。 | 只补文案键，使菜单、标题、标签、面包屑和页面标题都用「SLA 策略」/ `SLA`。不改 `/settings/sla`，不改后端字段。 |
| UI-3 | 确认缺陷 | P0 | Initiatives 展开后只有「Initiative详情」，指向 `/initiatives/detail`，没有 id。页面提示缺少 Initiative id，或留下空的详情壳。 | `routes.ts` 中 `initiatives` 的唯一子路由是 `initiatives_detail`。菜单因此只有这一项。`detail/index.vue` 在没有 `query.id` 时 `warning('缺少 Initiative id')` 并 `replace({ name: 'initiatives' })`。父路由又重定向回详情，所以回不到列表。列表 `views/initiatives/index.vue` 已存在且已导入，生成路由未挂载。带 id 的深链在 `favorites.ts`、`global-search.ts`，必须保留。 | 菜单变成一项，打开已有列表。详情 `hideInMenu`，路径和 `?id=` 不变。无 id 的详情改去列表路由，避免弹回详情。 |
| UI-4 | 确认缺陷 | P0 | 客户列表上的「全部需求」会打开没有 id 的需求详情。两种语言都没有 `route.requests`。 | `views/customers/index.vue` 推 `name: 'requests'`。`routes.ts` 的 `requests` 同样只有 `requests_detail`。列表 `views/requests/index.vue` 已存在。详情无 id 时标题回落为「需求详情」。 | 与 UI-1 同一做法。这是客户列表已有按钮，不新做需求管理。遗留 Requirement 页面仍然隐藏。 |
| UI-C1 | 美化 | P0 | 快捷入口写死中文，副文案用 `opacity: 0.55`，和选中语言不一致，对比也不稳定。侧栏阴影和分组还比较重。 | `TriageNav.vue`、`CustomersNav.vue`、`InsightsNav.vue`、`ActivityNav.vue`。主题色已经是 `themeSettings.themeColor` `#5e6ad2`，侧栏宽已经是 220。 | 快捷入口改用文案键。副文案改用现有 `--vk-muted`，去掉透明度。壳层用现有分隔线，不换主题包，不改 OT 标。 |
| UI-C2 | 美化 | P1 | 菜单中英并列（「成员 Members」「冲刺 Cycles」）。问题列表、详情、项目、客户页和设置页有多层卡片。空状态不统一。 | `zh-cn.ts` 的 `workspace_members`、`workspace_cycles`。`views/issue/list/index.vue`、`views/issue/detail/index.vue`、`views/settings/sla/index.vue`。 | 按术语表改显示文案。视觉只收成一层表面和分隔线。不改表格字段、按钮动作、弹窗关闭方式和 toast。 |
| UI-C3 | 美化 | P2 | 窄屏和公开页还没有按同一套密度整理。 | `views/f/[token].vue`、`views/r/[token].vue`、`views/invite/[token].vue`，以及登录、引导、问题列表在 375 / 768 / 1280 的布局。 | 三档宽度都能完成原来的操作。不把公开页收成登录后页面。`f` / `r` 继续在路由变换时挂上。 |

不在本台账里修、也不要顺手改掉的行为：根路径 `/login`、OpenTask 标题和现有 OT 图、Requirement 界面隐藏但接口保留、客户详情里的「新建需求」、问题集代码保持删除而表和数据保留、`/f` `/r` `/invite`、空工作区引导和 `ensure-owner`、不重置口令、不删库、不把 `/ws/hub` 暴露出去。
