# 界面壳层、菜单语义与美化

日期：2026-11-06  
基线：`main` @ `f2f81c51fda85bf48221d7f84a2f56d071e7704e`  
台账：`docs/superpowers/specs/2026-11-06-ui-shell-terminology-ledger.md`  
状态：给 Yuri 审的设计。未改业务代码，没有修现网。

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

- `customers`、`requests`、`initiatives` 在 `customRoutes` 里覆盖同名生成路由。
- 每个父路由的第一个子路由是列表：路由名 `customers_list`、`requests_list`、`initiatives_list`，组件分别是已有的 `view.customers`、`view.requests`、`view.initiatives`，`path` 为空字符串，所以地址仍是 `/customers`、`/requests`、`/initiatives`。
- 详情子路由保持 `customers_detail`、`requests_detail`、`initiatives_detail`，路径仍是 `/customers/detail`、`/requests/detail`、`/initiatives/detail`。`hideInMenu: true`。`activeMenu` 指向对应的列表名。
- 父路由不写会跳到详情的 `redirect`。`transform` 会把第一个子路由当成默认目标，所以第一个子路由必须是列表。
- 客户和需求的父路由继续 `hideInMenu: true`。侧栏入口仍是现有快捷按钮，不在生成菜单里再挂一份。
- 举措的两个子路由都 `hideInMenu: true`，父路由保持可见。`getGlobalMenusByAuthRoutes` 在没有可见子项时会把它画成单项，点击 `/initiatives` 后进入列表。不再展开出一个「详情」。
- 详情页在没有 `query.id` 时替换到列表路由名，不替换到父路由名。已有的「缺少 Initiative id」提示只留给直接打开无 id 详情的情况，提示之后停在列表，不再弹回详情。
- 不跑 elegant-router 代码生成。生成文件里的视图键已经够用；本批的路由形状放在 custom 路由，避免下一次生成把列表丢掉。
- 若类型要求路由名预先登记，把 `customers_list`、`requests_list`、`initiatives_list` 加进 `frontend/src/typings/elegant-router.d.ts` 的 `RouteMap` 和 `RouteKey`。不改 API 路径和数据库 id。

### 3.2 文案

缺键就补键，已有键按下面的术语表改显示文字。页面标题、菜单、标签、面包屑用同一个 `i18nKey`。不改路由名、接口路径、包名和字段名。

快捷入口的「分诊 / 入站」「客户 / 需求」「Insights / 效能」「活动 / Feed」改为文案键，中英文都能切换。Insights 和 Feed 保持这两个词，不译成另一套产品名。

SLA、Webhook、Issue、Cycles 按术语表保留。冲刺和周期建单必须分开：`workspace_cycles` 是迭代冲刺，`settings_recurrences` 是周期建单。

### 3.3 面包屑

菜单里找得到的路由继续用 `getBreadcrumbsByRoute`。找不到时，用当前路由的 `i18nKey` 生成一项；如果有 `activeMenu`，再把那个路由的文案放在前面。客户详情因此是「客户 / 客户详情」，而不是空白，也不是键名。

### 3.4 视觉

克制、任务优先，沿用现有 OT 标和 OpenTask 字样。侧栏退后：背景用 `--vk-bg`，与内容之间只用现有的 1px 分隔，不再叠一层卡片阴影。主色只用已经配置的 `#5e6ad2`；暗色继续用令牌里的 `#828fff`。不把主色改成另一种紫，也不新增第二强调色。

字号使用现有阶梯，并补一个界面用的 13px：`--vk-font-ui: 13px`。正文 13–14。间距继续 4px 网格。控件高 32px，问题行高 32–40。侧栏保持 220。圆角控件继续 6，需要稍大的触控面用已有的 8。不引入新的主题包，继续用 Naive UI。

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
| Issue 模板 | Issue 模板 | Issue templates | 保留 Issue |
| 项目模板 | 项目模板 | Project templates |  |
| 自定义字段 | 自定义字段 | Custom fields |  |
| 自动化 | 自动化 | Automations |  |
| 分诊 | 分诊 | Triage | 副文案：入站 / Incoming |
| Insights | Insights | Insights | 副文案：效能 / Performance |
| 活动 | 活动 | Activity | 副文案：Feed / Feed |
| 收件箱 | 收件箱 | Inbox |  |
| 问题 | 问题 | Issues |  |
| 我的问题 | 我的问题 | My issues |  |
| 回收站 | 回收站 | Trash |  |
| 工作区 | 工作区 | Workspace |  |
| 项目 | 项目 | Projects |  |
| 导出 / 导入 | 导出 / 导入 | Export / Import | 只改可见文字，不改处理函数 |
| 新建 Issue | 新建 Issue | New issue | 保留 Issue 这个对象名 |

## 5. 阶段

三阶段都在本批范围内。后面的阶段不能因为前面做完就从计划里删掉。

- P0：路由入口、缺键、面包屑回落、壳层令牌、焦点和减少动效、问题列表密度、登录和空工作区引导。
- P1：共享空状态、对话框和抽屉的表面，问题详情、项目、客户、需求、举措和设置页的卡片层级，术语表里其余菜单文案。
- P2：375 / 768 / 1280 的收边，公开表单、请求状态和邀请页。不改变公开路由的注册方式。

## 6. 测试

实施时先写会失败的测试。

- 路由：`customers`、`requests`、`initiatives` 的第一个子路由是列表；详情路径不变且 `hideInMenu`；举措父路由可见且没有可见子菜单。
- 文案：上述 `i18nKey` 在 `zh-cn.ts` 和 `en-us.ts` 都有值，并且不等于键名。
- 面包屑：菜单中不存在的客户详情回落为两项；SLA 在补键后不再是 `route.settings_sla`。
- 标题：`formatDocumentTitle` 的现有测试继续通过，产品名仍是 OpenTask。
- 已有守卫：Requirement 仍离开 `workflow_requirements`；`/f`、`/r` 仍由 `viewsWithPublicPages()` 挂上。
- 视觉单测只检查令牌存在，以及减少动效规则写在样式里。像素和三档宽度放到浏览器验收，不和单测数字混写。

浏览器验收要另记：编译后的前端，375 / 768 / 1280，亮色和暗色，至少覆盖菜单、问题列表、登录。另有一组不改业务数据的检查：公开页、无 id 详情回到列表、深链带 id 仍打开原来的记录。本检查点还没有这些截图。

## 7. 不做

- 不合并、不部署、不连接现网。
- 不生成新的标志或插画。
- 不把 Requirement 管理页面加回菜单，不恢复问题集页面，不删表。
- 不改口令，不写删除数据的迁移。
- 不放宽工作区隔离，不发布 `/ws/hub`。
- 不因为外观调整改默认工作流、字段自动折叠、弹窗关闭或 toast。
