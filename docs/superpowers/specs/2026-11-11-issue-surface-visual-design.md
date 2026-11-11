# OpenTask 问题列表与新建表单视觉规格

日期：2026-11-11  
状态：正式规格。Yuri 已批准按 §11 实现。下面 §5 的测量是改代码之前的基线。  
基线：仓库 `https://github.com/WayJ/opentask`，工作区 HEAD 与远程 `cursor/residual-copy-design-658f` 均为 `75cc03e21e1ce44e9687e8d9fee9201a9df510a5`。远程 `main` 仍为 `22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34`。2026-11-11 本轮 `git fetch` 后两边都没有前进。  
产品方向：Yuri 已拍板方案 A。本文件把该方向落到这一 SHA 的源码与合成基线实测上。

## 1. 目标

在不改信息架构、文案、路由、权限、API 和数据的前提下，让问题列表和新建问题表单使用同一套**局部**明暗令牌：表面、文字、分隔、强调色、主按钮、危险按钮和焦点。侧栏、详情、编辑、登录、SLA 不改文件。单行行高维持实测，长标题继续换行，操作按钮维持实测命中区。

## 2. 已排除

- 不改详情、编辑的布局或样式。`route.issue_edit` 已在本 SHA 复现，留给下一轮本地化，不进本轮视觉。
- 不改术语、菜单、空态文案、工具条文案和按钮职责。
- 不折叠、不隐藏现有字段，不把「高级选项」改成默认展开或删掉。
- 不移动主按钮，不改 toast / dialog 的出现时机和文案。
- 不改 `issueListColumnLayout`、900px 钉住阈值、标题 300px、横向滚动。
- 不把单行行高硬压到 36px。
- 不改 `frontend/src/theme/settings.ts`、`frontend/src/styles/design-system.css`、`frontend/src/styles/design-tokens.css`。
- 不改侧栏组件。局部选择器不会命中侧栏。
- 不恢复问题集或 Requirement 管理，不删除客户「新建需求」。
- 不把强调色换成另一套紫色，也不改回 soybean `#646cff`。
- 不在 PR6 分支 `cursor/residual-copy-design-658f` 上追加提交。不自动合并 PR6。

## 3. 引用与远程核对

| 项 | 本轮核对 |
|---|---|
| HEAD | `75cc03e21e1ce44e9687e8d9fee9201a9df510a5`，提交说明 `fix(ui): localize the SLA business-hours card` |
| `origin/main` | `22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34`，与事先告知一致 |
| `origin/cursor/residual-copy-design-658f` | 与 HEAD 相同，没有前进 |
| merge-base | `22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34` |
| PR6 相对 main 的文件 | 25 个，见 §4。本轮 `git diff --stat origin/main...HEAD` |
| OT-UI-001 / 002 / 006 | **Yuri已验历史证据，本轮未重验。** 不根据 2026-11-06 截图重开。合成预览里 SLA 页标题是「SLA 策略」，这只说明该 SHA 的页面标题可读，不是生产复验 |

## 4. 源码映射

PR6 相对 `origin/main` 的 25 个路径（`git diff --stat origin/main...HEAD`）：

- `docs/superpowers/plans/2026-11-11-residual-copy.md`
- `docs/superpowers/specs/2026-11-11-residual-copy-design.md`
- `frontend/src/constants/issue.ts`
- `frontend/src/locales/__tests__/residual-copy.test.ts`
- `frontend/src/locales/display-label.ts`
- `frontend/src/locales/langs/en-us.ts`
- `frontend/src/locales/langs/zh-cn.ts`
- `frontend/src/locales/use-label-table.ts`
- `frontend/src/typings/app.d.ts`
- `frontend/src/utils/boardSwimlanes.ts`
- `frontend/src/utils/groupIssuesBy.ts`
- `frontend/src/views/initiatives/__tests__/create-label.test.ts`
- `frontend/src/views/initiatives/index.vue`
- `frontend/src/views/insights/__tests__/labels.test.ts`
- `frontend/src/views/insights/index.vue`
- `frontend/src/views/issue/create/index.vue`
- `frontend/src/views/issue/detail/index.vue`
- `frontend/src/views/issue/edit/index.vue`
- `frontend/src/views/issue/list/__tests__/type-labels.test.ts`
- `frontend/src/views/issue/list/index.vue`
- `frontend/src/views/issue/list/modules/IssueBoard.vue`
- `frontend/src/views/issue/list/modules/IssueListGrouped.vue`
- `frontend/src/views/settings/sla/__tests__/labels.test.ts`
- `frontend/src/views/settings/sla/index.vue`
- `frontend/src/views/settings/sla/policy-name.ts`

本轮视觉只允许再改下面「将修改」行。其余文件只作行为依据。

| 表面 | 路径 | 本轮 |
|---|---|---|
| 问题列表页 | `frontend/src/views/issue/list/index.vue` | 将修改：只加样式表 import。不改 script 里的列、删除对话框、工具条 |
| 列表列宽 | `frontend/src/views/issue/list/column-layout.ts` 第 1–19 行；测试 `column-layout.test.ts` | 不改。回归必须继续通过 |
| 新建表单 | `frontend/src/views/issue/create/index.vue` | 将修改：import 与 `<style scoped>` 里的颜色、焦点。不改模板结构和 script |
| 新局部令牌 | `frontend/src/styles/issue-surface.css`（新建） | 将创建 |
| 新对比测试 | `frontend/src/styles/__tests__/issue-surface.test.ts`（新建） | 将创建 |
| 全局令牌 | `frontend/src/styles/design-system.css`、`design-tokens.css`、`frontend/src/theme/settings.ts`、`frontend/src/main.ts` 第 2–3 行 | 不改 |
| 壳层焦点 | `frontend/src/styles/css/linear-shell.css` 第 118–121 行 | 不改。已有 `:focus-visible { outline: 2px solid var(--vk-accent) }` |
| 侧栏 | `frontend/src/layouts/modules/global-sider/index.vue` 及同目录 `*Nav.vue`；菜单来自 `frontend/src/router/elegant/routes.ts` | 不改 |
| 编辑 | `frontend/src/views/issue/edit/index.vue`；路由 `frontend/src/router/elegant/routes.ts` 第 213–218 行，`i18nKey: 'route.issue_edit'` | 不改 |
| 详情 | `frontend/src/views/issue/detail/index.vue` | 不改 |
| 客户新建需求 | `frontend/src/views/customers/detail/index.vue` 第 184、188 行，文案键 `page.shell.createRequest` | 不改。`zh-cn.ts` 第 364 行值为「新建需求」 |
| Requirement 管理 | `frontend/src/router/guard/surface.ts` 第 3–9 行把 `workflow_requirements` 重定向到 `issue_list`；`elegant/routes.ts` 第 791–798 行 `hideInMenu: true` | 不改 |
| 无 id 列表重定向 | `frontend/src/router/list-entry.ts` 第 9–12 行只覆盖 customers / requests / initiatives。**不包含** `issue_detail` | 不改 |

### 4.1 当前令牌值（读文件，不是推断）

`frontend/src/theme/settings.ts` 第 2–13 行：

- `themeScheme: 'light'`
- `themeColor: '#5e6ad2'`
- `otherColor.error: '#f5222d'`
- 侧栏 `sider.width: 220`，`collapsedWidth: 64`，`header.height: 56`

`frontend/src/styles/design-tokens.css` `:root`：`--vk-accent: #5e6ad2`，`--vk-bg: #f5f6f6`，`--vk-ink: #000000`，`--vk-muted: #62666d`。`html.dark`：`--vk-accent: #828fff`，`--vk-bg: #010102`，`--vk-paper: #0f1011`，`--vk-ink: #f7f8f8`。

`frontend/src/styles/design-system.css` `:root`：`--color-primary: #5e6ad2`，`--color-bg-primary: #ffffff`，`--color-bg-secondary: #f5f6f6`，`--color-text-primary: #000000`，`--color-text-secondary: #62666d`，`--color-text-tertiary: #8a8f98`，`--color-hairline: #e6e7e8`。`html.dark`：`--color-bg-primary: #0f1011`，`--color-canvas: #010102`，`--color-text-primary: #f7f8f8`，`--color-text-secondary: #d0d6e0`。

`DESIGN.md` 第 6、94 行把 `#5e6ad2` 写成当前产品主题色，并写明 soybean `#646cff` 已废弃。因此「不要换成紫色」的可执行含义是：**不要改这套已经在库里的值，也不要再引入另一个紫色。** 本轮不把强调色从 `#5e6ad2` 换走。若产品其实想退回 `#5e6ad2` 之前的颜色，那是另一项决定，不在本规格内。

开发模式不读 localStorage 主题（`frontend/src/store/modules/theme/shared.ts` 第 14 行 `if (!isProd) return themeSettings`）。暗色只能通过 store 的 `setThemeScheme('dark')` 或头部主题按钮进入。`darkMode` 为真时给 `html` 加上 `dark`（`frontend/src/constants/app.ts` 第 63 行）。

### 4.2 列表当前行为

`frontend/src/views/issue/list/index.vue`：

- 工具条顺序第 1595–1640 行：列表、看板、导出、导入、回收站、主按钮「新建问题」（`page.shell.createIssue`，中文「新建问题」）。
- 筛选页签第 1649–1693 行：我的待办、开放中、已关闭、全部。默认 `activeTab` 第 121 行是 `'open'`。
- 空态第 2006 行：`NEmpty`，描述 `page.shell.noIssues`，中文「暂无问题」。空态内部没有第二个新建按钮。
- 列第 1306–1448 行：编号、标题、类型、状态、优先级、估点、负责人、报告人、创建时间、操作。操作是「详情」「删除」，`NButton size="small"`，删除 `type="error"`。
- 删除第 907–910 行：`window.$dialog.warning`，标题「确认删除」，按钮「删除 / 取消」。成功 toast「问题删除成功」，失败 toast「问题删除失败」。
- 标题单元格第 1322–1327 行和第 2091–2094 行：`white-space: normal`，`overflow-wrap: anywhere`，`line-height: 20px`。单元格第 2470–2477 行：`height: auto`，`max-height: none`，`padding: 6px 12px`，`font-size: var(--vk-font-ui, 13px)`。
- 钉住逻辑调用 `issueListColumnLayout`。`ISSUE_ACTIONS_PIN_MIN = 900`，`ISSUE_TITLE_COLUMN_MAX = 300`，`ISSUE_CODE_COLUMN_WIDTH = 120`。表 `scroll-x` 第 2014 行为 1400。
- 窄屏折叠：`frontend/src/store/modules/app/index.ts` 第 33 行 `isMobile = breakpoints.smaller('sm')`，Tailwind `sm` 为 640px。375 会收起侧栏；768 和 1280 不收。

### 4.3 新建表单当前行为

`frontend/src/views/issue/create/index.vue`：

- 页头第 405–438 行从左到右：返回、标题「创建问题」、未保存标记；右侧「使用模板」、预览切换、主按钮「创建问题」。
- 可见字段：标题、描述、自定义字段（仅当接口返回定义）、附件、类型、优先级、关联项目。「高级选项」第 80 行 `advancedExpanded = false`，展开后才是关联任务 ID、关联需求 ID、负责人 ID。
- 校验第 216 行：空标题 `window.$message.error('请输入问题标题')`。成功第 251 行「问题创建成功」，失败第 258 行「问题创建失败」。
- 样式硬编码：页背景 `#f5f7fa`（第 686 行），页头和主栏 `#fff`（第 695、723 行），标题色 `#1a1a1a`（第 736 行），占位 `#aaa`（第 746 行），边 `#e8eaed`，标题字号 32px / 1024 以下 28px / 768 以下 24px。第 749–751 行 `.title-input:focus { outline: none }`。
- 响应式第 893–926 行：`max-width: 1024px` 收紧内边距；`max-width: 768px` 时属性栏改为上下排列。这些断点保持。

### 4.4 `route.issue_edit`

`zh-cn.ts` 的 `route` 对象有 `issue_list`、`issue_create`、`issue_detail`、`issue_trash`，没有 `issue_edit`。`en-us.ts` 同样没有。合成预览打开 `/issue/edit?id=issue-long` 后，文档标题和页签文字都是 `route.issue_edit`。这是本 SHA 上的复现，不是视觉缺陷。下一轮本地化按既有规则编号。本轮不补这个键。

## 5. 合成基线实测

预览没有请求生产，也没有使用真实账号。Vite 代理目标由环境变量设为 `http://127.0.0.1:7378`。代理日志里的真实 URL 全部是该地址。模拟服务只监听 `127.0.0.1:7378`。浏览器拦截了全部非回环请求，共 799 次，主机只有 `api.iconify.design`、`api.unisvg.com`、`api.simplesvg.com`。工具条图标仍来自本地编译的图标，截图里可见。页面底部的圆形按钮是 Vite 开发工具，不是产品控件。

数据集：

- 有数据：`SMOKEW-1` 标题「登录按钮无响应」；`SMOKEW-2` 为重复两遍的长标题；`SMOKEW-3` 已关闭。默认「开放中」只显示前两条。
- 空列表：同一接口返回 `rows: []`，出现「暂无问题」。
- 用户「合成用户」，工作区「合成工作区」。令牌字符串是 `synthetic-preview-token`，不是凭据。

主题通过应用自己的 `theme-store.setThemeScheme` 切换，并确认 `html` 的 `dark` class。不是手工改 CSS。

视口：375×812、768×1024、1280×800（新建表单 1280×900，整页截图）。截图与 `measurements.json` 在 `/opt/cursor/artifacts/ui-round1/screenshots/`。

### 5.1 列表几何

| 视口 | 表 `clientWidth` | `scrollWidth` | `scrollLeft` 起点 | 滚到末端 | 操作列 `position` |
|---|---:|---:|---:|---:|---|
| 375 | 349 | 1400 | 0 | 1051 | `relative` |
| 768 | 522 | 1402 | 0 | 880 | `relative` |
| 1280 | 1034 | 1402 | 0 | 368 | `sticky` |

这三组宽度与 `column-layout.test.ts` 里的 349 / 522 / 1034 一致。375 和 768 在 `scrollLeft = 0` 时先看到编号和标题，长标题换行，操作列不盖住标题。滚到末端后「详情」「删除」可见。1280 操作列钉住，会压住右侧「负责人」末字；这是 `fixed: 'right'` 在表宽 ≥ 900 时的现行为，本轮保持。

行高（明暗、三个宽度一致）：

- `SMOKEW-1` 单行：行盒 **41px**，标题高 20px，`white-space: normal`，`scrollHeight === clientHeight`。
- `SMOKEW-2`：768 与 1280 行盒 **93px**、标题高 80px；375 行盒 **113px**、标题高 100px。没有被裁切。
- 「详情」「删除」按钮盒均为 **48×28**。

因此 36–40px 只作为历史目标被记录。实测单行已经是 41px，按钮 28px 加单元格上下各 6px 再加边框就是这个高度。本轮**不改**行的 `padding`、`height`、`max-height`、`line-height`，也不加 `line-clamp`。

编号单元格计算样式已经是 `font-variant-numeric: tabular-nums`，字号 13px，行高 20px。明色字色 `rgb(51, 54, 57)` 对白底对比 **12.16**。暗色 `rgba(255, 255, 255, 0.82)` 对 `rgb(24, 24, 28)` 对比 **17.70**。不要改成更浅的次级色。

### 5.2 对比（已计算，不是凭 CSS 存在就判通过）

| 元素 | 明色 | 暗色 |
|---|---|---|
| 编号 / 标题正文 | 12.16，高于 4.5 | 17.70，高于 4.5 |
| 主按钮「新建问题」白字对 `#5e6ad2` | **4.70** | 暗色 Naive 把字改成黑色，黑字对 `#5e6ad2` 为 **4.47**，低于 4.5 |
| 「删除」 | 白字对 `rgb(245, 34, 45)`（即 `#f5222d`）**4.08**，低于 4.5 | 黑字对同一红 **5.15**，高于 4.5 |
| 页头图标按钮焦点 | Tab 到的按钮为 `outline: 2px solid rgb(94, 106, 210)` | 同一规则随 `--vk-accent` |

本轮 Tab 了列表页 12 次，停在页头工具上，**没有**走到「详情」「删除」。不能把这两个按钮写成已经键盘验收。实现后必须继续 Tab，直到这两个按钮成为 `document.activeElement`，并看到可见焦点。

### 5.3 新建表单

1280 计算样式：

| 节点 | 明色 | 暗色 |
|---|---|---|
| `.issue-create-page` | `rgb(245, 247, 250)` | `rgb(1, 1, 2)` |
| `.main-content` 与 `.page-header` | `rgb(255, 255, 255)` | **仍是** `rgb(255, 255, 255)` |
| 表单右侧 `.sidebar` | `rgb(245, 247, 250)` | **仍是** `rgb(245, 247, 250)` |
| 标题字色 | `rgb(26, 26, 26)` | **仍是** `rgb(26, 26, 26)` |
| 占位符 | `rgb(170, 170, 170)`，对白底 **2.32** | 相同 |
| 标题 `:focus` | `outline-style: none` | 相同 |
| 主按钮对比 | 4.70 | 4.47 |
| 高级字段 | 不可见 | 不可见 |
| 可见属性标签 | 类型、优先级、关联项目 | 同左 |

暗色下壳层已经变暗，表单内区仍是白底。这是本轮要修的不一致。标题若继续用 `#1a1a1a` 放到暗色表面 `#0f1011` 上，对比只有 **1.09**，所以字色必须成对，不能只改背景。

标题焦点是对本元素调用 `focus()` 后读到的计算样式，不是仅凭源码。8 次 Tab 没有走到标题输入框，所以「能否 Tab 到它」留到实现后补测；「它得到焦点时没有轮廓」已经测到。

### 5.4 范围外抽检（共享令牌未改，这些是基线，不是验收通过）

| 文件 | 文档标题 | 观察 |
|---|---|---|
| `spot-detail-light-1280.png`、`spot-detail-dark-1280.png`、`spot-detail-light-375.png` | 问题详情 - OpenTask | 长标题完整换行。本轮不改该页 |
| `spot-edit-*-1280.png`、`spot-edit-light-375.png` | `route.issue_edit - OpenTask` | 页内标题是「编辑问题」，页签是原始 key |
| `spot-sla-light-1280.png`、`spot-sla-dark-1280.png` | SLA 策略 - OpenTask | 面包屑「设置 / SLA 策略」。同一次会话里残留的编辑页签仍显示 key，那是页签缓存，不是 SLA 页自己的标题 |
| `spot-login-light-1280.png`、`spot-login-dark-1280.png` | 登录 - OpenTask | OT 标志加「OpenTask」，主按钮「确认」 |

侧栏在 1280 列表截图里展开了「问题」和「工作区」。可见快捷项为分诊、客户、洞察、活动、收藏。没有「问题集」。375 按现有断点收起侧栏。

## 6. 目标值

新建文件 `frontend/src/styles/issue-surface.css`。选择器只包在 `.issue-list-container` 和 `.issue-create-page` 上。明暗成对。数值取自现有令牌或下面算过对比的局部色。

| 令牌 | 明色 | 暗色 | 理由 |
|---|---|---|---|
| `--issue-canvas` | `var(--color-bg-secondary)` = `#f5f6f6` | `var(--color-canvas)` = `#010102` | 取代新建页 `#f5f7fa`。差 2 个色阶，仍用现有表面，不新造灰 |
| `--issue-surface` | `var(--color-bg-primary)` = `#ffffff` | `var(--color-bg-primary)` = `#0f1011` | 页头和主栏 |
| `--issue-surface-muted` | `var(--color-bg-secondary)` | `var(--color-bg-secondary)` 的暗色值 `#141516` | 属性栏、附件底 |
| `--issue-ink` | `var(--color-text-primary)` = `#000000` | `#f7f8f8` | `#1a1a1a` 不能放到暗底上 |
| `--issue-ink-secondary` | `#62666d`（对白 **5.77**） | `#d0d6e0`（对 `#0f1011` **13.04**） | `#8a8f98` 对白只有 3.25；`#62666d` 对暗底只有 3.30。必须成对 |
| `--issue-line` | `var(--color-hairline)` = `#e6e7e8` | 暗色 hairline `#23252a` | 取代 `#e8eaed` |
| `--issue-accent` | `#5e6ad2` | `#5e6ad2` | 不改品牌色。暗色主按钮底仍用它 |
| `--issue-on-accent` | `#ffffff` | `#ffffff` | 白字对 `#5e6ad2` 为 **4.70**。不用 Naive 暗色黑字（4.47） |
| `--issue-danger` | `#cf1322` | `#cf1322` | 白字对比 **5.57**。只用于列表里的 error 按钮 |
| `--issue-on-danger` | `#ffffff` | `#ffffff` | 同上 |
| `--issue-focus` | `2px solid #5e6ad2` | `2px solid #828fff` | 与现有壳层焦点同思路，但是局部变量 |

列表行、列宽、空态结构、工具条不使用新的尺寸令牌。

新建表单：

- 页、页头、主栏、属性栏、附件底、边框、标题字、占位符改用上表。页头现有的 `0 1px 3px` 阴影去掉，与列表卡片一样不再叠阴影。
- 标题字号保持 32 / 28 / 24。主按钮留在页头右侧，前面仍是「使用模板」和预览。
- 删除 `.title-input:focus { outline: none }`。焦点使用 `--issue-focus`，`outline-offset: 2px`。
- 「高级选项」默认仍关闭。
- 768px 仍改为上下排列。

列表：

- 只改**启用**状态。选择器必须带 `:not(.n-button--disabled)`。不设置 `--n-color-disabled`、`--n-text-color-disabled`，也不给禁用按钮写前景或背景。
- Naive `Button.mjs` 把 `--n-*` 写在元素的内联 `style` 上。局部样式表里的同名变量要在 `.issue-list-container` / `.issue-create-page` 内用 `!important` 才能压过内联，禁止改全局主题。
- 不写死 `background-color`。启用删除钮只改 `--n-color`、`--n-color-hover`（`#a8071a`）、`--n-color-pressed`（`#820014`）、`--n-color-focus` 和对应字色，让 Naive 自己的 hover / active 规则继续换底。白字对这三底分别是 5.57、7.75、10.72。
- 启用主按钮和删除钮的 `:focus-visible` 使用 `--issue-focus`。轮廓色对相邻表面：明色 `#5e6ad2` 对白 4.70，暗色 `#828fff` 对 `#0f1011` 6.64，都高于 3。
- 验收要量默认、hover、按下、`:focus-visible` 的计算前景和背景，不能只量默认。
- 按钮盒保持至少 48×28。不改「详情」的默认按钮色。
- 删除对话框的标题、正文、按钮文案和成功/失败 toast 一字不改。

空态保持只有「暂无问题」。不在空态里加「新建问题」。页头主按钮已经在。

## 7. 验收

实现后用同一合成数据、同一三个视口、明暗各拍一遍。用计算样式，不用源码里有没有变量下结论。

必须同时成立：

1. `SMOKEW-1` 行高仍约为 41px（允许 ±1px 的亚像素）。`SMOKEW-2` 行高仍大于标题一行，且 `scrollHeight === clientHeight`。
2. 375 与 768 的表宽仍使操作列 `position` 不是 `sticky`；1280 表宽 1034 这一档仍是 `sticky`。`scrollLeft = 0` 时标题列不被操作列盖住。1280 钉住的操作列仍盖住「负责人」末字，这是既有行为，保持不变，不要写成整表无遮挡。滚到末端后「详情」「删除」可见，盒尺寸仍 ≥ 48×28。窄屏钉列行为与基线相同。
3. 新建表单暗色验收覆盖编辑器正文、占位符、工具条、附件标签、属性标签、主按钮、次按钮，以及页面上实际出现的禁用态和错误态，不只标题。基线里工具条和附件是白底上的浅字。父级表面改完后必须重测计算样式。`.main-content`、`.page-header` 不再是 `rgb(255, 255, 255)`。标题字、占位符、编辑器正文和占位符对各自背景 ≥ 4.5。标题焦点必须是真实 Tab 到达后的 `:focus-visible`，`outline-style` 不是 `none`，宽度 ≥ 2px。对元素调用 `focus()` 不算 Tab 验收。高级字段默认仍不可见；展开后「关联任务 ID」「关联需求 ID」「负责人 ID」仍在。空标题提交仍提示「请输入问题标题」，不发出创建成功。
4. 列表与新建表单的**启用**主按钮在明暗下，默认、hover、按下、`:focus-visible` 的字色对当时背景 ≥ 4.5，默认底仍是 `#5e6ad2`。列表启用「删除」在这四态的字色对当时按钮底 ≥ 4.5，hover 底与默认底不同，按下底与 hover 底不同。焦点轮廓对相邻表面 ≥ 3。禁用按钮若出现，前景和背景保持 Naive 禁用色。按钮文案仍是「删除」。
5. 工具条文案、列名、空态「暂无问题」、删除确认文案与现在一致。
6. 登录、详情、SLA、侧栏相对本基线没有因共享令牌变化而变色。编辑页仍会显示 `route.issue_edit`，这不算本轮失败，也不算本轮修复。
7. `column-layout.test.ts` 与 `theme-contrast.test.ts` 仍通过。`vue-tsc --noEmit --skipLibCheck` 的原始完整日志与 `/opt/cursor/artifacts/ui-round1/commands/vue-tsc.txt` 逐条比对，不以 29 这个数字、也不以本节摘要代替原始日志。全库 ESLint 现状不要求清零。新测试文件和两个 Vue 文件各自对照基线诊断，不得新增；CSS 被 ESLint 忽略不算 CSS 验收，CSS 靠构建和浏览器计算样式。禁止 `pnpm lint` 和任何带 `--fix` 的 ESLint。`vite build --mode prod` 退出码 0。
8. 最终 HEAD 要有与实施者不是同一人的规格评审和代码评审。Important 和 Critical 先改再评最终 HEAD。实施者自查不能写成独立评审。评审工具不可用就停并报告，不许编造评审者。

## 8. 本轮已跑命令

工作目录 `frontend/`，HEAD `75cc03e`。输出在 `/opt/cursor/artifacts/ui-round1/commands/`。

| 命令 | 退出码 | 结果 |
|---|---:|---|
| `pnpm exec vitest run` | 0 | 81 files，504 passed。与 PR6 正文自报数字相同，但是本轮重跑的 |
| `pnpm exec vue-tsc --noEmit --skipLibCheck` | 2 | 29 条，全部列出如下 |
| `pnpm exec eslint .`（没有 `--fix`） | 1 | 870 problems（190 errors，680 warnings）。仓库仍干净 |
| `pnpm exec eslint` 只针对列表、新建、`column-layout.ts`、两份设计 CSS | 1 | 31 problems（6 errors，25 warnings）。6 个 error 全在 `issue/list/index.vue` 的 script：未使用的 `GROUP_BY_OPTIONS`、`loadCustomFieldDefs`、`applySmartSearchFromString`，`customFieldDefs` 使用前定义，以及第 1396 行 `== null`。新建页 17 个 warning、0 error。本轮不修这些 |
| `pnpm exec vite build --mode prod` | 0 | 日志末行 `Build successful` |

`vue-tsc` 的 29 条，逐条保留：

1. `src/typings/api/issue.d.ts(75,5): error TS1357`。原因是第 74 行 `PROJECT_CHANGED = 'project_changed'` 后面少逗号，下一行是 `SLA_PAUSED`。
2. `src/typings/components.d.ts(242,9)` 到 `(255,33)`：`TS1134` 与 `TS1005` 成对出现，对象键写成了 `'IconMdi:arrowLeft'` 这种带冒号的引用名。

这两处都不在本轮修改范围内。不要为了让 typecheck 变 0 去改它们。

## 9. 分支

2026-11-11 已再 fetch：`origin/main` 仍是 `22c8d8b3e3681e9d6b79d6e72fd200c2156cbd34`，PR6 仍是 `75cc03e21e1ce44e9687e8d9fee9201a9df510a5`。

1. 新分支 `cursor/issue-surface-visual-ab12` 从该精确 SHA 分出。不在 `cursor/residual-copy-design-658f` 上提交。
2. 第一笔提交只含本文件和 `docs/superpowers/plans/2026-11-11-issue-surface-visual-plan.md`。其后是计划里的三笔实现提交。
3. PR base 是 `cursor/residual-copy-design-658f`，正文写明 `Depends on PR6` 和 `https://github.com/WayJ/opentask/pull/6`。只用仓库允许的 PR 工具。工具拒绝时不改用 `gh` 或 API。不合并、不部署、不改 PR6。

## 10. 自检

已对照全文查过，没有留空项。下面这些容易打架的地方已经定死：

- 36–40px 与实测 41px：保持 41px，不压行。
- 2026-11-06 规格写「删除样式不变」，本轮实测明色删除字对比 4.08。Yuri 已批准局部 `#cf1322` / 白字，确认框和文案不动。不再保留“删掉危险色”这条退路。
- 暗色主按钮黑字 4.47：只改列表和新建页的主按钮字色为白，不改 `themeColor`。登录页「确认」因此保持原样。
- 旧规格空态含新建按钮，现页空态没有：不加按钮。
- 侧栏「必要成对令牌」：局部选择器足够，侧栏文件零改动。范围外截图是基线，不是改造。
- `route.issue_edit` 已看见：不修。
- 编号列已经是 `tabular-nums`：不再加一条重复规则。
- 独立评审不能由实施者兼任。规格评审和代码评审各要一份，且都看最终 HEAD。

## 11. 评审修订（优先于上文冲突句）

Yuri 已读本规格、实施计划和新建页暗色基线，并批准本轮实现。下面五条覆盖上文里写得更窄的句子。

1. 按钮只覆盖启用态，保留禁用外观和语义。量默认、hover、按下、`:focus-visible` 的计算前景和背景。Naive 内联 `--n-*` 只在 `.issue-list-container` 与 `.issue-create-page` 内覆盖。不用固定 `background-color` 抹掉删除钮 hover。焦点轮廓对相邻表面 ≥ 3，文字 ≥ 4.5，非文字 ≥ 3。
2. 暗色新建页验收包含编辑器正文、占位符、工具条、附件标签、属性标签、主按钮、次按钮、页面上出现的禁用态和错误态。`MarkdownEditor.vue` 的 scoped 样式把工具条写成 `#f9f9f9`、正文写成 `#24292f`、占位符写成 `#999`。`#24292f` 对 `#0f1011` 只有 1.30，`#999` 对 `#f9f9f9` 只有 2.71。这些颜色可以用 `.issue-create-page` 下更高优先级的选择器覆盖，不必改组件源文件。若实测仍不可读，且唯一修法是改白名单以外的组件内部文件，停下来，写出最小 diff，交给 Yuri。不许悄悄扩大白名单，也不许在不可读时宣称该页通过。
3. 每个新 TS 测试和两个 Vue 文件都跑 ESLint，逐条对照基线。CSS 不被 ESLint 检查，所以 CSS 靠 `vite build` 和浏览器计算样式。`vue-tsc` 对照原始完整日志，不对照 29 或本节摘要。禁止 `pnpm lint` 的自动修复。
4. 1280 操作列盖住「负责人」末字是既有行为，保持并写明。真实 Tab 到标题和「详情」「删除」，并留截图。`focus()` 不算。高级选项默认关闭；展开后的三个字段，以及空标题校验，要有回归。保持 41px 单行、长标题换行不裁切、操作钮 48×28、窄屏既有钉列行为。
5. 最终 HEAD 的规格评审和代码评审必须换人。Important / Critical 改完再评最终 HEAD。

允许改动的路径：

- `docs/superpowers/specs/2026-11-11-issue-surface-visual-design.md`
- `docs/superpowers/plans/2026-11-11-issue-surface-visual-plan.md`
- `frontend/src/styles/issue-surface.css`
- `frontend/src/styles/__tests__/issue-surface.test.ts`
- `frontend/src/views/issue/create/index.vue`
- `frontend/src/views/issue/create/surface.test.ts`
- `frontend/src/views/issue/list/index.vue`
- `frontend/src/views/issue/list/surface.test.ts`

第一笔提交只有前两份文档。
