# 界面壳层、菜单语义与美化

日期：2026-11-06  
基线：`main` @ `f2f81c51fda85bf48221d7f84a2f56d071e7704e`  
台账：`docs/superpowers/specs/2026-11-06-ui-shell-terminology-ledger.md`  
状态：Yuri 已在检查点 `5028d2c` 批准方向。本文件的修正已经写进实现。不合并、不部署、不连接现网。

## 0. Yuri 的修正

1. 中文显示名要收成一套。Issue 显示为「问题」，Issue 模板为「问题模板」，新建 Issue 为「新建问题」。Insights 中文为「洞察」，英文仍是 Insights。活动的中文提示用「动态」，不再用中英并列的 Feed。举措显示为「举措」。SLA 策略和 Webhook 保留公认缩写。冲刺和周期建单继续分开。菜单、浏览器标题、内部标签、面包屑、页面标题和按钮跟当前语言走。不改 API、路由名和字段名。客户详情里的「新建需求」在中文里保持这四个字。
2. 默认列表子路由用真实的 `transformElegantRoutesToVueRoutes` 加 `createRouter` 验证，不靠静态 `children` 断言。已在 Vue Router 4 上执行：父路由 `/customers`、第一个子路由 `path: ''`、显式重定向到列表名时，`push({ name: 'customers' })` 一次落到列表，地址仍是 `/customers`，不会和父路由来回跳。带 id 的 `/customers/detail` 仍停在详情。因此采用空路径，不另造 `/customers/list`。生成器在目录同时有 `index.vue` 和子页面时会丢掉列表视图，只留下 `layout.base`；生产构建会重跑代码生成并覆盖 `elegant-router.d.ts`。列表子路由在 `createStaticRoutes` 里注入，类型用已有的 `ElegantConstRoute`（`name: string`），不把 `*_list` 手写进生成的 `RouteKey`。`activeMenu` 指向父路由名，这样隐藏子路由的高亮键才是菜单上的那一个叶子。
3. 面包屑回落要进现有的 `App.Global.Breadcrumb`，带可点击的路由名，并且跟随当前语言。未登记的文案不显示键名。管理、工作管理和遗留需求这些隐藏路由不放进导航。
4. 样式是否存在不能代替行为。密度用浏览器量到的行高：单行目标 32–40，不给单元格设 `max-height: 40`，换行标题和放大后的文字可以更高。375、768、1280 的亮色和暗色都要看编译后的页面，主要按钮不能被裁掉。焦点包含传送到 `body` 的下拉和对话框。对比用现有令牌的实际色值。
5. 对话框、抽屉和空状态要有看得见的统一表面，沿用 Naive 和现有 `--vk-*`。不给所有页面套一个没用的 `ot-page`，不因此加第二层内边距，也不把所有卡片压平。Vue 模板继续写 `:bordered="false"`。登录和空工作区引导只改外观。
6. UI-4 属于同一导航缺陷，在范围内。不扩展客户或需求的业务能力。实施中发现的别的业务错误只记台账。
7. 前端跑类型检查、改动文件的 lint、全套 Vitest 和生产构建。后端和 CLI 本批不改，不把没跑的门禁写成已通过。验收分开写单测和浏览器证据，并写明最终 SHA、已解决项和限制。独立审查看最终代码；有实质修正再审一次。

## 1. 目标

让已经存在的页面从菜单进得去，并且菜单、浏览器标题、内部标签、面包屑、页面标题在当前语言下是同一句话，不再露出 `route.*`。在此之上，用仓库里已有的 Linear 式令牌把壳层和主要页面收成同一套密度。不新做客户、举措或 SLA 功能，不换标，不换主题包。

## 2. 已经核对的代码

快捷入口在 `frontend/src/layouts/modules/global-sider/index.vue`：分诊、客户、Insights、活动，然后是收藏和生成菜单。客户按钮推路由名 `customers`。

`frontend/src/router/elegant/transform.ts` 第 138–143 行：父路由只要有子路由且自己没有 `redirect`，就重定向到第一个子路由。

因此：

- `/customers` 落到 `/customers/detail`，没有 `id`。详情模板在没有客户时显示「客户详情」。
- `/initiatives` 落到 `/initiatives/detail`。没有 `id` 时提示「缺少 Initiative id」，再 `replace` 回 `initiatives`，又被重定向回详情。
- `/requests` 同样只有详情子路由。客户列表上的「全部需求」会走进去。

这三个目录的 `index.vue` 都是现成列表，`frontend/src/router/elegant/imports.ts` 已经导入，生成路由的父组件却是 `layout.base`，没有把列表挂上。

`frontend/src/router/routes/index.ts` 的 custom 路由优先于生成路由。设置页的生效定义在这里，`settings_sla` 的 `i18nKey` 是 `route.settings_sla`。`zh-cn.ts` 和 `en-us.ts` 的 `route` 都没有 `customers`、`customers_detail`、`requests`、`requests_detail`、`settings_sla`。`fallbackLocale` 是 `en`，两边都缺键时 `$t` 返回键名。标题守卫、标签和菜单都走这条路径。

面包屑只在菜单树里查找（`getBreadcrumbsByRoute`）。客户父路由 `hideInMenu: true`，整支都不进菜单，所以面包屑是空的。SLA 在菜单里，所以面包屑显示的是未翻译的键。

带 id 的详情是现成深链：客户和需求用 `query.id`，举措收藏和全局搜索用 `/initiatives/detail?id=`。这些路径和查询保持不变。

视觉真源已经在仓库里：`DESIGN.md` v2.0、`frontend/src/theme/settings.ts` 的 `themeColor: #5e6ad2`、`sider.width: 220`、`themeRadius: 6`，以及 `frontend/src/styles/design-tokens.css` 的 `--vk-*`。暗色在 `html.dark` 里整组替换。不另起一套色板。

## 3. 方案

### 3.1 客户、需求、举措的入口

比较过三种做法：

1. 在 custom 路由里把已有列表挂成默认子路由，详情 `hideInMenu`，父路由重定向到列表。推荐。
2. 只改快捷入口的 `router.push` 路径。命令面板、返回按钮和父路由重定向仍会进到没有 id 的详情。
3. 菜单打开第一条记录的详情。空列表没有可打开的记录，也会把「进列表」改成「进某一条」。

采用 1。

- 不在 `customRoutes` 里再写一份同名父路由。生成器每次都会把这三个父路由写成 `layout.base` 加详情子路由。`createStaticRoutes` 在合并之后注入列表子路由，这样生产构建重写 `routes.ts` 和 `elegant-router.d.ts` 之后，列表仍然在。
- 每个父路由的第一个子路由是列表：路由名 `customers_list`、`requests_list`、`initiatives_list`，组件分别是已有的 `view.customers`、`view.requests`、`view.initiatives`，`path` 为空字符串。真实路由器已经确认：地址仍是 `/customers`、`/requests`、`/initiatives`，命名导航一次结束。空路径被拒绝时才改用 `/customers/list` 这种不同路径；本次没有被拒绝。
- 详情子路由保持 `customers_detail`、`requests_detail`、`initiatives_detail`，路径仍是 `/customers/detail`、`/requests/detail`、`/initiatives/detail`。`hideInMenu: true`。`activeMenu` 指向父路由名 `customers`、`requests`、`initiatives`。菜单高亮读的是隐藏路由的 `activeMenu`，父路由名才等于举措那一个可见叶子。
- 父路由不写会跳到详情的 `redirect`。`transform` 会把第一个子路由当成默认目标，所以第一个子路由必须是列表。
- 客户和需求的父路由继续 `hideInMenu: true`。侧栏入口仍是现有快捷按钮，不在生成菜单里再挂一份。
- 举措的两个子路由都 `hideInMenu: true`，父路由保持可见。`getGlobalMenusByAuthRoutes` 在没有可见子项时会把它画成单项，点击 `/initiatives` 后进入列表。不再展开出一个「详情」。
- 没有 `query.id` 的详情在路由守卫里、路由确认之前替换到列表路由名，只替换一次，不替换到父路由名。这样标签页不会先记下「客户详情」。详情页里的替换留着，组件已经挂上时仍能回到列表。举措的缺 id 提示只在组件已经挂上时出现；从菜单或无 id 地址进来不会先挂上详情。
- 不把 `*_list` 写进生成的 `RouteKey`。列表的 `i18nKey` 继续用已经存在的 `route.customers`、`route.requests`、`route.initiatives`。不改 API 路径和数据库 id。

### 3.2 文案

缺键就补键，已有键按下面的术语表改显示文字。页面标题、菜单、标签、面包屑用同一个 `i18nKey`。不改路由名、接口路径、包名和字段名。

快捷入口的「分诊 / 入站」「客户 / 需求」「洞察 / 效能」「活动 / 动态」改为文案键，中英文都能切换。英文里 Insights 仍是 Insights，Activity 仍是 Activity，不再出现 Feed 这个并列标签。

SLA、Webhook、Issue、Cycles 按术语表保留。冲刺和周期建单必须分开：`workspace_cycles` 是迭代冲刺，`settings_recurrences` 是周期建单。

### 3.3 面包屑

菜单里找得到的路由继续用 `getBreadcrumbsByRoute`，结果要是现有的面包屑对象。相邻两项文案相同就合成一项，避免「举措 / 举措」。找不到时，按 `route.matched` 生成同样形状的面包屑：文案来自当前语言的 `$t`，语言切换会重算。未登记或仍等于键名的项丢掉。管理、工作管理和遗留需求路由不进入这项回落。除最后一项外，点击用路由名导航。客户详情因此是可点的「客户」加上当前的「客户详情」。

### 3.4 视觉

克制、任务优先，沿用现有 OT 标和 OpenTask 字样。侧栏退后：背景用 `--vk-bg`，与内容之间只用现有的 1px 分隔，不再叠一层卡片阴影。主色只用已经配置的 `#5e6ad2`；暗色继续用令牌里的 `#828fff`。不把主色改成另一种紫，也不新增第二强调色。

字号使用现有阶梯，并补一个界面用的 13px：`--vk-font-ui: 13px`。正文 13–14。间距继续 4px 网格。控件高 32px。问题列表的单行目标是 32–40，用单元格内边距达到，不设置会裁切换行标题的 `max-height`。侧栏保持 220。圆角控件继续 6，需要稍大的触控面用已有的 8。不引入新的主题包，继续用 Naive UI。对话框、抽屉和空状态使用 `--vk-paper`、`--vk-line` 和 `--vk-muted`，这是看得见的表面，不是给每个页面加一个类名。不给所有 `NCard` 再压一层，也不把 `bordered={false}` 写进 Vue 模板。登录和空工作区引导改用同一套背景、纸面和字色，创建工作区、重试和退出的行为不变。

暗色必须还能整页切换。新增的颜色只写进已有的 `:root` 和 `html.dark`。小字不用亮色主色直接压在暗底上；暗色小字用 `--vk-accent` 的暗色值。副文案用 `--vk-muted` 或 `--color-text-secondary`，不用 `opacity: 0.55`。

P0 就加上键盘焦点和减少动效：`:focus-visible` 使用 2px 主色轮廓，亮色和暗色都至少 3:1。`prefers-reduced-motion: reduce` 时关掉页面过渡。正文对比目标 4.5:1，界面部件 3:1。现有 `--vk-muted` `#62666d` 在 `#f5f6f6` 上约为 5.3:1，暗色 `#8a8f98` 在 `#010102` 上约为 6.4:1。

不改弹窗点击外部是否关闭，不改 toast 的出现和消失，不自动折叠表单字段，不因为变窄就藏起新建、导出、导入或保存。375、768、1280 都要能完成原来的操作。公开页只调整密度，仍是未登录可打开的页面。

## 4. 术语表

这是本批采用的显示名。Yuri 可以整表否掉；实施时不另选一套。

| 概念 | 中文 | English | 约束 |
|---|---|---|---|
| 客户入口 | 客户 | Customers | 列表，不是详情 |
| 客户深链 | 客户详情 | Customer | 仅有 id |
| 客户需求入口 | 需求 | Requests | 客户需求列表。不是遗留 Requirement 管理 |
| 客户需求深链 | 需求详情 | Request | 仅有 id。详情里的「新建需求」保留 |
| 举措入口 | 举措 | Initiatives | 菜单单项，打开列表 |
| 举措深链 | 举措详情 | Initiative | 仅有 id |
| SLA | SLA 策略 | SLA | 保留缩写 |
| Webhook | Webhooks | Webhooks | 保留 |
| 迭代周期 | 冲刺 | Cycles | `workspace_cycles`。不要叫周期建单 |
| 重复创建问题 | 周期建单 | Recurring issues | `settings_recurrences`。不要叫 Cycles |
| 成员 | 成员 | Members | 中文不再写成「成员 Members」 |
| 标签 | 标签 | Labels |  |
| 问题模板 | 问题模板 | Issue templates | 中文不再写 Issue 模板 |
| 项目模板 | 项目模板 | Project templates | 中文不再写 Project 模板 |
| 自定义字段 | 自定义字段 | Custom fields |  |
| 自动化 | 自动化 | Automations |  |
| 分诊 | 分诊 | Triage | 副文案：入站 / Incoming |
| 洞察 | 洞察 | Insights | 副文案：效能 / Performance。英文不改成别的产品名 |
| 活动 | 活动 | Activity | 副文案：动态 / Recent。不用 Feed |
| 收件箱 | 收件箱 | Inbox |  |
| 问题 | 问题 | Issues | 列表标题、空状态和按钮都用这个对象名 |
| 我的问题 | 我的问题 | My issues |  |
| 回收站 | 回收站 | Trash |  |
| 工作区 | 工作区 | Workspace |  |
| 项目 | 项目 | Projects |  |
| 导出 / 导入 | 导出 / 导入 | Export / Import | 只改可见文字，不改处理函数 |
| 新建问题 | 新建问题 | New issue | 中文不用「新建 Issue」 |
| 新建需求 | 新建需求 | New request | 中文保持这四个字，这是客户详情上的原按钮 |

## 5. 阶段

三阶段都在本批范围内。后面的阶段不能因为前面做完就从计划里删掉。

- P0：路由入口、缺键、面包屑回落、壳层令牌、焦点和减少动效、问题列表密度、登录和空工作区引导。
- P1：共享空状态、对话框和抽屉的表面，问题详情、项目、客户、需求、举措和设置页的卡片层级，术语表里其余菜单文案。
- P2：375 / 768 / 1280 的收边，公开表单、请求状态和邀请页。不改变公开路由的注册方式。

## 6. 测试

实施时先写会失败的测试。

- 路由：用 `createStaticRoutes`、`getAuthVueRoutes` 和 `createRouter`。父路由命名进入后停在列表，只发生一次导航；带 id 的详情路径和查询不变；无 id 的详情路由可以再被替换到列表一次；再次进入父路由不会循环。举措菜单只有一个叶子，列表和详情的高亮键都是 `initiatives`。
- 文案：上述 `i18nKey` 在 `zh-cn.ts` 和 `en-us.ts` 都有值，并且不等于键名。中文术语按第 4 节。
- 面包屑：客户详情在菜单为空时得到两项，第一项的键可以导航；管理路由不出现；未登记文案不出现。语言切换后同一条路由的文案改变。组件测试点击非当前项会 `router.push` 到该项的路由名。
- 标题：`formatDocumentTitle` 的现有测试继续通过，产品名仍是 OpenTask。
- 已有守卫：Requirement 仍离开 `workflow_requirements`；`/f`、`/r` 仍由 `viewsWithPublicPages()` 挂上。生产构建之后再跑这两项。
- 对比：从 `design-tokens.css` 读出亮色和暗色的实际色值并计算对比度。不把「文件里有某个选择器」当成密度或窄屏证明。

浏览器验收另记：编译后的前端，375 / 768 / 1280，亮色和暗色，覆盖菜单、问题列表、登录，并量单行和换行标题的行高。另有一组不改业务数据的检查：公开页、无 id 详情回到列表、深链带 id 仍打开原来的记录。几张截图不能写成所有页面都已修好。

## 7. 不做

- 不合并、不部署、不连接现网。
- 不生成新的标志或插画。
- 不把 Requirement 管理页面加回菜单，不恢复问题集页面，不删表。
- 不改口令，不写删除数据的迁移。
- 不放宽工作区隔离，不发布 `/ws/hub`。
- 不因为外观调整改默认工作流、字段自动折叠、弹窗关闭或 toast。
