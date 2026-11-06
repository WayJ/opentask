# 待修批次设计：Requirement 隐藏、问题集移除、品牌、README、空工作区

日期：2026-11-06  
基线：`main` @ `c1d2424`（`c1d2424ca87bb3dae5e2a730b86a90f14abf34ad`，Merge pull request #3，E99）  
`git fetch origin main` 后 `origin/main` 与该提交一致。  
状态：**设计检查点，待 Yuri 复核。本文件入库时不改业务代码、不合并、不部署、不开启下一 Epic。**  
计划：`docs/superpowers/plans/2026-11-06-pending-fixes.md`（与本设计同批交出；实施仍等 Yuri 回复）

本批是 E99 已合并之后的修复批次，不新编号 Epic。验收文档留到实施完成之后再写。

## 0. 已批准范围与硬约束

1. **Requirement**：隐藏全部面向用户的导航、发现、创建表面；Requirement 专用代码内部标记废弃。保留已有数据、表结构和 API 行为。不删除、不迁移。不隐藏客户与客户反馈。不做新的 Requirement 标识。
2. **问题集**：按最新口径**删除页面及其专属代码**，不是只隐藏。以中文文案和路由识别实体。普通 Issue 列表、Issues、Projects、客户反馈、保存的视图保留，除非依赖审计证明它们就是该功能。不删库表、不删记录。共享依赖安全解开，并报告保留的表和历史迁移。
3. **品牌**：浏览器文档标题、favicon、应用内产品名和 logo 统一为 OpenTask 与**现有 logo**。不新画图形。只清理活跃产品表面上的模板品牌残留。
4. **README**：根目录和相关组件/部署 README 按当前代码改。纠正过时功能、启动与测试说明、只剩 KEY-N 的标识写法。不编造命令，也不编造测试结果。README 在对应行为落地后再改，避免先写未实现的事实。
5. **全新部署空工作区**：生产上初始管理员创建后 `workspaces=0`、`member=0`；`GET /api/workspaces` 返回 `[]`；前端 `ensureWorkspace` 只在列表非空时写 `localStorage.workspaceId`；拦截器因此不带 `X-Workspace-Id`；多个需工作区的接口返回 400，`detail` 为 `缺少 X-Workspace-Id 请求头`。生产已用正式 `POST /api/workspaces` 建成名为 OpenTask、owner 为该管理员的工作区。代理没有注入错误。要补上首次工作区创建/引导和正式部署引导，并用测试覆盖空工作区、登录初始化、登录后主页面请求、多工作区隔离。
6. **站点根路径**：`http://112.126.60.109/login` 当前打不开。生产去掉 `/opentask` 前缀，SPA、静态资源、API、公开 `/f` 与 `/r`、深链刷新都走站点根。不把浏览器重定向进 `/opentask`。多租户头和现有鉴权保持。本轮只改仓库里的构建与 nginx 片段；不连上那台机器、不 reload、不部署。根路径已由用户授权为部署变更。验证通过后用发布说明交接产物，由人决定何时套到服务器。

硬约束：

- 仓库和日志不写入口令；不重置已有管理员口令；不做破坏性 schema 变更。
- 保留公开路由 `/f/:token`、`/r/:token`。
- 不改线上服务器。
- 不在代理里写死 workspace id，不挑其他租户的工作区当默认，不关闭工作区校验，不泄漏数据。
- 已有账号和已有数据保持可用。
- 测试要覆盖主页面业务请求，健康检查或登录 200 不够。单元/API 与浏览器验证分开记录。
- **首个工作区由部署引导创建，还是由前端引导创建，本设计给出推荐，等 Yuri 拍板后再写这部分业务代码。**
- 根路径会占掉该 IP 上 notegit 的 `location /`。这是用户要求 `/login` 与 `/` 可用的直接后果，写在第 2.6 节。实施仍不连活服务器。

## 1. 调查结论

### 1.1 Requirement（隐藏，不删）

实体是 workflow Requirement（`/api/requirements`，`backend/opentask/api/requirement/router.py`），与客户需求不是同一个东西。

已经隐藏的部分：

- 生成路由 `workflow_requirements` 带 `hideInMenu: true`（`frontend/src/router/elegant/routes.ts`）。
- 静态自定义路由同名项也隐藏（`frontend/src/router/routes/index.ts`）。`createStaticRoutes` 同名顶层路由以 custom 为准，所以线上 workflow 树是 custom 这份。
- 侧栏菜单由 `getGlobalMenusByAuthRoutes` 丢掉 `hideInMenu`。命令面板的菜单项来自这份菜单，因此「需求（遗留）」不会出现在侧栏或菜单搜索里。
- `frontend/src/utils/command-palette.ts` 的固定动作只有 Issue、Project、Inbox 等，没有 Requirement。

仍然面向用户的表面：

- 直接打开 `/workflow/requirements`、`/workflow/requirement-detail` 仍会挂上列表和创建界面（`frontend/src/views/workflow/requirements/index.vue` 会 `addRequirement`）。
- 文案仍是 `需求（遗留）` / `需求详情`（`frontend/src/locales/langs/zh-cn.ts`）。

客户页上的「新建需求」**不是** Requirement。`frontend/src/views/customers/detail/index.vue` 的 `onCreateRequest` 调用 `fetchCreateCustomerRequest`。客户、客户需求、客户反馈保留，包括这个按钮。

`frontend/src/components/DocDrawer.vue` 引用 `requirement-detail/utils/documentType`。Requirement 页面代码保留，这个共享工具不用搬。

CLI 的 `requirement` / `task` 命令继续调用保留的 API。帮助文案标为废弃，命令行为不改。

### 1.2 问题集 = IssueCollection（删除专属代码）

中文「问题集」只出现在 Issue Collection：

| 表面 | 位置 |
|---|---|
| 页面 | `frontend/src/views/issue/collection/[id].vue`、`collection-list/index.vue`、`collection-create/index.vue` |
| 文案 | `zh-cn.ts`：`issue_collection` = 问题集 |
| 线上菜单 | custom 路由 `issue` **整棵替换**生成的 `issue`。子项 `issue_collection` 路径 `/issue/collection`，**没有** `hideInMenu`，标题走 `route.issue_collection` |
| 生成路由（被 custom `issue` 挡住） | `/issue/collection/:id`、`/issue/collection-create`、`/issue/collection-list` |
| API | `backend/opentask/api/issue/router.py` 约 940–1193 行，前缀 `/api/issues/collections` |
| 服务 | `backend/opentask/services/issue_collection_service.py` |
| 模型 | `backend/opentask/models/issue_collection/`，表 `issue_collections` |
| 测试 | `backend/tests/issue_collection/` |
| CLI | `agent-harness/opentask-cli/opentask/core/collection.py`，客户端方法打的是 **`/api/issue-collections`**，与后端 `/api/issues/collections` 不一致 |

`issue_ids` 是 JSON 列表，没有指向 `issues` 的外键。`parse` 创建的是普通 Issue，删服务不会删这些 Issue。全库除本模块、`models/__init__.py` 导出、以及 `issue_saved_view` 的一句「非 IssueCollection」注释外，没有别的模型 relationship 指向 `IssueCollection`。

必须留下的共享物：

- `generic_status_to_issue_set`（`backend/opentask/api/tasks/mapping.py`，Jira JQL 也用）是状态集合，不是问题集。
- `issue_saved_views` 与保存的视图页面。E4 明确不复用 IssueCollection。
- Issue 列表、Issue 详情里内联的 Agent 指令弹窗（`issue/detail/index.vue` 自己有一份，不引用 `AgentPromptModal.vue`）。
- `AgentPromptModal.vue` 只有问题集详情引用，随问题集删除。
- 客户、Projects、公开 `/f`、`/r`。

保留的 schema / 历史迁移（本批不改这些文件，也不新增 drop revision）：

- `backend/alembic/versions/2026_10_31_1529-003ccd38d5cd_pg_initial_baseline.py` 创建 `issue_collections`（downgrade 才 drop）。
- `backend/migrations/fix_uuid_32_to_36.py` 列出 `issue_collections.creator_id`。这是历史脚本，不执行删除。

移除 ORM 后表仍在库里，数据仍在，只是不再映射。禁止随后用 autogenerate 生成 drop。`models/__init__.py` 留一行注释，说明表被故意保留。

`backend/tests/api/test_e98_linear_issue_identifiers.py::test_create_surfaces_call_resolver` 把 `issue_collection_service.py` 列进「创建面必须调用 resolver」。删除该文件时，从列表去掉这一项；Issue、Jira、Tasks 三条断言保持。

历史 spec / acceptance 里对 IssueCollection 的叙述是当时的记录，本批不改写。

### 1.3 品牌

现有 logo 已确认，两份像素内容一致：

- `frontend/src/assets/imgs/opentask-logo.png`（`SystemLogo` 已使用）
- `frontend/public/opentask-logo.png`
- `frontend/public/favicon.png`（同一 OT 标）

活跃表面上的残留：

- `frontend/index.html` 先链接 `favicon.svg`。该 SVG 是蓝紫渐变笑脸，不是现有 OT 标。浏览器会优先用 SVG。
- `frontend/src/router/guard/title.ts` 与 `store/modules/app/index.ts` 的 `useTitle` 只写路由名，登录后标签页不再是 OpenTask。`VITE_APP_TITLE` 与 `system.title` 已经是 OpenTask。
- `frontend/src/plugins/loading.ts` 的 `getLogoSvg()` 是模板几何图形，启动屏会显示它，旁边文字已经是 `system.title`。
- 登录页和侧栏 `GlobalLogo` 已经是 `SystemLogo` + `system.title`。
- 主题预设 `frontend/src/theme/preset/default.json`、`dark.json` 的 watermark `text` 仍是 `SoybeanAdmin`。`settings.ts` 默认已是 OpenTask，但套用预设会盖回去。水印设置 placeholder 也是 `SoybeanAdmin`。
- 隐藏但仍可打开的 `/home`：`header-banner.vue` 用 `soybean.jpg`，`project-news.vue` 用 `SoybeanAvatar`，文案是 soybean-admin 编年。
- `global-footer` 链到 soybean-admin LICENSE。页脚默认 `visible: false`，组件仍在布局里。

不改：`presetSoybeanAdmin` 函数名、elegant-router 生成文件头注释、npm 包名 `soybean-admin`（改包名会动工具链，且不出现在产品界面）。不新生成 logo 或 favicon 图形。favicon 改指向现有 `favicon.png`，并去掉笑脸 SVG 的引用；可删除 `favicon.svg` 以免再被链上。

### 1.4 README 与当前代码的偏差（实施时改，本设计不先改 README）

| 文档 | 与代码不符处 |
|---|---|
| 根 `README.md` | 架构图写 TypeScript「Vibe CLI」；主叙事是 Requirement→Task。CLI 实际是 Python（`agent-harness/opentask-cli`）。示例标识 `REQ-20260213-001` 与现行 Issue `KEY-N` 不符。Node 写 18+，`frontend/package.json` engines 是 `>=20.19.0`。PostgreSQL 写 14+。 |
| `frontend/README.md` | 整篇是 SoybeanAdmin 模板说明，克隆地址指向 soybean-admin。 |
| `frontend/AGENTS.md` | 写「webpack 代理」。实际是 Vite，`vite.config.ts` 端口 **9527**。 |
| `backend/README.md` | 写 PostgreSQL 16。`docker-compose.yml` 与 `docker-compose.prod.yml` 镜像是 `postgres:15-alpine`。认证节示例 `AUTH_USERNAME` / `AUTH_PASSWORD` 不是当前登录模型。 |
| `deploy/README.md` | 写「后端没有注册接口」。`POST /api/auth/register` 存在，且 `AuthService.register` 会 `create_for_owner`。正式首次部署走的是 `create_admin_user.py`，该脚本**不**建工作区。 |
| CLI README | 仍把 `collection` 列为可用遗留命令。问题集删除后这句变为过时。`requirement` 可标废弃但仍可用。 |

本批不改 Postgres 镜像，只把文档写成 compose 实际的 15-alpine，并注明 README 曾写 16、旧 sprint 曾用 16。不把两种说法收成一个未核实的「统一版本」。

根 README 的快速开始命令（`uv run uvicorn ... --port 7377`、`pnpm dev`、`docker compose`）与 `frontend/package.json` 的 `lint` / `build` / `test` 脚本、后端 `uv run pytest tests/ -v` 一致，保留这些命令。不写未跑过的通过数字。

### 1.5 空工作区根因

正式路径：

1. `deploy/deploy.sh` 在栈起来之后执行 `python scripts/create_admin_user.py`。
2. `create_admin`（`backend/scripts/create_admin_user.py`）只写 `users`、播种角色、写 `user_role`。不调用 `WorkspaceService`。
3. 开放注册才会建默认工作区（`auth_service.py` `register` → `create_for_owner`）。生产首个管理员不走注册。
4. 登录后 `loginByToken` → `ensureWorkspace`（`frontend/src/store/modules/auth/index.ts`）。`localStorage` 已有 id 则直接返回；否则 `GET /api/workspaces`，**仅当 `data.length` 非 0** 才 `localStg.set('workspaceId', data[0].id)`。
5. `initUserInfo`（刷新已有 token）**不**调用 `ensureWorkspace`。
6. `frontend/src/service/request/index.ts` 只在有 `workspaceId` 时加 `X-Workspace-Id`。两处拦截器相同。
7. `require_workspace_context`（`backend/opentask/api/workspace/deps.py`）缺头即 400，文案就是生产上的那句。Issue 列表页会请求保存的视图（`loadSavedViews` → `/api/saved-views`，该路由强制头）。`GET /api/issues` 用的是可选上下文，缺头不返回这句 400。
8. `list_for_user` 排除遗留 id `00000000-0000-4000-8000-000000000001`，并按 `created_at` 升序。
9. 顶栏 `workspace-switcher.vue` 同样只在本地无 id 且列表非空时写入 `data[0]`。列表为空时没有引导，只有一个「+」对话框。主页面先 400，用户不会被带到创建流程。生产是靠直接 `POST /api/workspaces` 恢复的。
10. Vite 代理与 `frontend/nginx.conf` 只转发，不添加 `X-Workspace-Id`。

已有成员关系的账号不受影响：本地 id 若仍在自己的列表里，应继续用它，不能改成「第一个工作区」或库里任意工作区。

### 1.6 登录路由与 `/opentask` 前缀

前端登录**已经是**站点路径 `/login`，不是另起一个名字。生成路由（`frontend/src/router/elegant/routes.ts`）：

- 路由名 `login`
- 路径 `/login/:module(pwd-login|code-login|register|reset-pwd|bind-wechat|change-password|dingtalk-callback)?`
- 模块参数可省略，所以 `/login` 与 `/login/pwd-login`、`/login/register` 都匹配同一路由
- `meta.constant: true`，未登录可进
- 已登录且模块不是 `change-password` 时，守卫 `next({ name: 'root' })`
- `root` 是 `/`，重定向到 `VITE_ROUTE_HOME`（`.env.example` 为 `issue_list`，即 `/issue/list`）
- 未登录访问非常量路由时，守卫 `next({ name: 'login', query: { redirect: to.fullPath } })`
- 登录成功后 `redirectFromLogin` 用 query `redirect` 做 `routerPush`，否则 `toHome()`

守卫按**路由名**跳转，不拼 `/opentask`。`createWebHistory(VITE_BASE_URL)` 才把前缀加到浏览器地址上。

生产打不开 `http://112.126.60.109/login` 的原因是前缀部署，不是缺这条路由：

| 层 | 现状 |
|---|---|
| `frontend/Dockerfile` | `ARG VITE_BASE_URL=/opentask/`、`VITE_SERVICE_BASE_URL=/opentask/`；`dist` 拷到 `/usr/share/nginx/html/opentask`；健康检查打 `/opentask/` |
| `frontend/nginx.conf` | 只提供 `/opentask/assets/`、`/opentask/api/`、`/opentask/` |
| `deploy/nginx/opentask-locations.conf` | 宿主只把 `/opentask/` 转到 `127.0.0.1:8080` |
| `deploy/deploy.sh` | 要求 `.env.prod` 两行都是 `/opentask/`，并检查 `index.html` 含 `/opentask/assets/` |
| 宿主 `location /` | `deploy/README.md` 写明交给 notegit `127.0.0.1:3000`。`/login` 不会进 OpenTask |

本地 `frontend/.env.example` 已是 `VITE_BASE_URL=/`、history 模式、`VITE_ROUTE_HOME=issue_list`。开发时代理前缀另算：`src/utils/service.ts` 的 `createProxyPattern()` 固定返回 `/opentask`，Vite 把它剥掉再转到 `7377`。所以本机 `http://localhost:9527/login` 可以是根路径，生产构建却把同一路由挂到 `/opentask/login`。

硬编码 `/opentask` 的浏览器 URL 还有 `frontend/src/utils/attachmentUrls.ts`（附件地址总是加这个前缀）。改生产基址时这里必须跟服务基址走，否则附件仍请求 `/opentask/api/...`。

与根路径撞车的后端路径（宿主今天就单独代理，SPA 挪到根之后必须继续单独代理，且不能被 SPA 的 `try_files` 吃掉）：

| 浏览器路径 | 归属 |
|---|---|
| `/api/*` | 后端业务 API。后端路由本身带 `/api`，反代不要再剥一层产品前缀 |
| `/ws/*` | 后端 WebSocket。工作区实时是 `/ws/workspace`，查询串带 token 与 `workspace_id`，成员校验在后端。nginx 不添加 `X-Workspace-Id` |
| `/oauth2/token`、`/oauth2/userinfo`、`/oauth2/revoke` | OAuth2 协议端点 |
| `/oauth2/api/*` | OAuth2 只读 API |
| `/oauth2/authorize` | **前端 SPA 同意页**（路由名 `oauth2`，非常量，未登录会进 `/login?redirect=...`） |
| `/tasks/*`、`/capabilities`、`/healthcheck` | 任务源契约与探活，保持现状 |
| `/f/:token`、`/r/:token` | 前端常量路由（custom）。刷新必须回 `index.html` |
| `/rest/api/2/*`、`/mcp`、`/docs`、`/test/*` | 今天的宿主片段没有把它们公开到 80 端口。本批不新开这些口 |

`location /oauth2/` 若继续整段转后端，会把 SPA 的 `/oauth2/authorize` 一并送走。精确匹配 `location = /oauth2/authorize` 优先于前缀，应指向前端容器。

## 2. 方案

### 2.1 Requirement

**推荐：** 路由继续注册（深链不 404、代码不删），在路由守卫里把 `workflow_requirements` 与 `workflow_requirement-detail` 重定向到 `issue_list`（`VITE_ROUTE_HOME`）。页面不再挂载，创建表单不可达。模块、路由和 CLI 帮助标 `deprecated`。FastAPI `APIRouter(..., deprecated=True)` 只影响 OpenAPI 标记，不改处理函数、状态码和响应体。不新增标识字段，不改表。

备选：只维持现状的 `hideInMenu`。深链仍能创建 Requirement，达不到「隐藏全部创建表面」。

备选：从路由表删掉页面。这是删除而不是隐藏，也碰 `DocDrawer` 的工具引用，超出本条范围。

客户需求按钮不动。公开 `/f`、`/r` 的 `constant: true` 守卫分支不动。

### 2.2 问题集

**推荐：** 删除专属 UI、前端 API/类型/常量、custom 与生成路由项、后端 collection 路由与 service 与 ORM 包、CLI `collection` 命令及专属测试。然后 `pnpm gen-route`，再 `uv run python scripts/export_openapi.py` 重导出 `backend/openapi.json` 与 `openapi_current.json`。

Issue CRUD、保存的视图、`generic_status_to_issue_set` 不改语义。删除 collection 路由后，`GET /api/issues/collections` 会落到 `/{issue_id}` 并 404，这是删除 API 的结果；用测试锁住 404，并锁住 `GET /api/issues` 与 `GET /api/saved-views` 仍在。

不新增 Alembic revision。

### 2.3 品牌

**推荐：** 活跃表面改用现有 PNG 与文案 OpenTask。

- 文档标题：`{路由标题} - OpenTask`；标题本身已是 OpenTask 时不重复。
- favicon 只引用 `favicon.png`。
- 启动屏用 `/opentask-logo.png` 的 `<img>`，去掉内联模板 SVG。
- 主题预设水印文字与 placeholder 改为 OpenTask。
- `/home` 上的 soybean 头像和编年改成现有 logo 与不含模板项目史的短文案。
- 页脚去掉 soybean-admin 外链，改为不指向新站点的「OpenTask」文本。

不改 npm 包名，不改 Uno 预设函数名。

### 2.4 空工作区（待 Yuri 选）

三条都能保住隔离：选择只来自**当前用户的成员关系**；不读其他用户的工作区；不使用固定 UUID；不改 `require_workspace_context` 的 400。

| 方案 | 行为 | 代价 |
|---|---|---|
| A. 只做部署引导 | `create_admin_user.py` 在该用户零成员关系时调用 `WorkspaceService.create_for_owner`。已有成员则不动。默认名 `OpenTask`，可用 `--workspace-name` 覆盖。`--skip-workspace` 才跳过。不改口令。 | 修好官方首次部署和「账号已存在但零成员」的补跑。SSO 或后台建号且零成员的用户登录后仍 400。 |
| B. 只做前端引导 | 登录和 `initUserInfo` 都解析成员列表。空列表进入引导页，用户确认名称后 `POST /api/workspaces`，只把**响应里的 id** 写入本地。列表非空时：本地 id 在列表中则保留，否则用该用户 `created_at` 最早的一项。 | 任何零成员用户都能在 UI 恢复。不跑 UI 的全新部署在第一次打开浏览器之前，API/CLI 仍无工作区。 |
| **C. 两者都做（推荐）** | A 的脚本引导 + B 的解析和引导页。脚本已提交工作区后，列表非空，引导页不出现。 | 范围比单侧大。若脚本与引导页并发且都看到空列表，可能建出两个工作区；见风险。 |

推荐 C 的理由：生产故障就是官方脚本没建工作区，所以脚本要补上，并与已执行过的 `POST /api/workspaces`（名 OpenTask、owner=管理员）同一服务。只补脚本留不下「零成员用户打开主页面」的产品行为，刷新路径今天也不重新解析。引导页使用现成创建接口，不在前端伪造 id。

**在 Yuri 回复 A、B 或 C 之前，不实现第 5 节的工作区代码。** 计划里的工作区任务按 C 写好；若选 A 或 B，只做对应任务。

### 2.5 README

行为落地后改第 1.4 节列出的文档，并改写根路径拓扑（第 2.6 节）。Requirement 写成「API 仍在，界面不再进入」。问题集写成「专属界面、API、CLI 已移除；表 `issue_collections` 保留」。空工作区按 Yuri 选定的方案写实际命令（脚本参数或引导页），不写未选中的方案。测试节只列真实命令，结果以实施当次输出为准，写进验收而不是编进 README。

### 2.6 站点根路径（用户已授权；本轮不连服务器）

**推荐：** 生产浏览器地址去掉 `/opentask`。登录仍用现有路由名 `login` 和路径 `/login`，不新造路由，不把 `/login` 重定向到 `/opentask/login`。

构建：

- `frontend/Dockerfile` 的默认 `VITE_BASE_URL` 与 `VITE_SERVICE_BASE_URL` 改为 `/`
- `dist` 拷到 `/usr/share/nginx/html/`，不再放进 `opentask/` 子目录
- `Dockerfile.dist` 同样
- `deploy/deploy.sh` 的 `.env.prod` 检查改为这两行等于 `/`；`index.html` 必须出现 `/assets/`，且不得出现 `/opentask/assets/`
- 本地 Vite 开发代理可以继续用 `/opentask` 这个**仅开发机**的剥离前缀（`createProxyPattern`）。它不出现在生产 history base 里。附件 URL 改为使用 `getServiceBaseURL` 的结果：开发代理下仍是 `/opentask/api/...`，生产基址 `/` 时就是 `/api/...`

容器 nginx（`frontend/nginx.conf`）按根提供：

- `/assets/` 长期缓存
- `/api/` 原样转到后端 `7377`（保留 `/api` 前缀；继续用 Docker DNS 变量，避免后端重建后 502）
- `/ws/` 同样原样转到后端，并带 Upgrade。不设置 `X-Workspace-Id`
- `/` 用 `try_files` 回退 `/index.html`，这样 `/`、`/login`、`/issue/list`、`/f/:token`、`/r/:token` 刷新都进 SPA
- 健康检查改为请求 `/login` 或 `/`，期望 200 且正文是 `index.html`

宿主片段（`deploy/nginx/opentask-locations.conf`）删掉 `/opentask` 的 location 和「301 到 `/opentask/`」。保留并补上：

- `/api/`、`/ws/` → `127.0.0.1:7377`
- `location = /oauth2/authorize` → `127.0.0.1:8080`（SPA）
- `/oauth2/` 的其余路径 → `7377`（token、userinfo、revoke、`/oauth2/api/`）
- `/tasks/`、`/capabilities`、`/healthcheck` 维持现状
- 片段里**不写**第二个 `location /`

notegit：`deploy/README.md` 写明该 vhost 的 `location /` 现在转到 `127.0.0.1:3000`。只要它还在，`/login` 仍然进 notegit。要让 OpenTask 占据 `/` 与 `/login`，应用片段时必须把这份 `location /` 的 `proxy_pass` 改到 `127.0.0.1:8080`（前端容器）。这会让该 IP 根路径不再打开 notegit。回滚是把 `proxy_pass` 指回 `3000`，并恢复旧的 `/opentask/` 片段。仓库只提供片段和说明；`deploy.sh` 继续禁止由本代理执行。实施者也不要 SSH 到 `112.126.60.109`。

不增加「从 `/opentask` 301 回根」的规则，除非 Yuri 另要。用户要求的是不要再进 `/opentask`。旧书签会失效，写进发布说明。

登录与鉴权不动语义：未登录深链 → 路由名 `login`，query `redirect` 为站内 fullPath（基址为 `/` 时就是 `/issue/list` 这种路径）→ 登录后 `routerPush` 回去。已登录打开 `/login` → 路由名 `root` → `/issue/list`。`/f`、`/r`、`/invite/:token` 仍是 `constant`，不进登录墙。`/oauth2/authorize` 仍非常量，未登录先到 `/login`。nginx 不注入 workspace 头，不关后端成员校验。

备选：只加 `location = /login`，其余深链仍归 notegit。刷新 `/issue/list` 会进 notegit，不满足深链。不采用。

备选：只在新域名上把 OpenTask 放在根，IP 的 `/` 留给 notegit。不能满足当前要打开的 `http://112.126.60.109/login`。域名和 TLS 仍按现有 README 作为后续，不替代这次根路径。

发布交接（实施验证之后写，不在本检查点冒充已上线）：列出改过的 Dockerfile、nginx、deploy 检查项；本地容器对 `/`、`/login`、一条深链、`/api` 与 `/f` 回退的探测结果；明确「未对 112.126.60.109 执行 reload」。

## 3. 工作区数据流（方案 C）

```
create_admin_user.py
  seed roles
  create or load user          # 已存在且未 --reset-password：不改 password_hash
  ensure_owner_workspace(user) # 已有任意 membership → 返回现有，不新建
                               # 否则 create_for_owner(name, owner=该用户)
  commit

登录 / initUserInfo
  GET /api/workspaces          # 仅当前用户成员，排除遗留默认 id
  resolve(storedId, list)
    空列表 → 引导页（不写 localStorage）
    storedId ∈ list → 保持
    否则 → list[0].id          # 该用户自己的最早工作区
  之后的请求才带 X-Workspace-Id

引导页
  POST /api/workspaces { name }  # 默认预填 OpenTask，可改
  响应 id 写入 localStorage
  进入 issue_list
```

`ensure_owner_workspace` 不查询「库内第一个工作区」，不把用户加入别人的 workspace。`issue_key` 沿用 `create_for_owner` 的唯一化，不写死 `OT`。

引导页路由为登录后常量页，守卫放行 `/f/:token`、`/r/:token` 和未登录路由。

## 4. 测试（实施时先红后绿）

区分：

- **单元：** 纯函数 `resolveWorkspaceSelection`；脚本 CLI 默认值（`--workspace-name` 默认 OpenTask，`--skip-workspace` 默认关，`--reset-password` 默认关）。不连接生产库。
- **API：** 测试库里零成员用户调用 `ensure_owner_workspace` 得到 owner 成员；第二次调用不增加工作区；不使用 `DEFAULT_WORKSPACE_ID`；不加入其他用户的工作区。缺头时 `GET /api/saved-views` 为 400 且 detail 为 `缺少 X-Workspace-Id 请求头`。带该用户自己的头时 200。用户 A 的头不能读到用户 B 的 Issue。`GET /api/issues/collections` 为 404。`GET /api/issues` 与客户接口仍 200。Requirement `POST/GET /api/requirements` 行为与现测试一致。
- **前端单测：** 空列表不写 `workspaceId`；两个工作区且本地为空时写入第一个；本地 id 属于列表则不变；本地 id 不属于列表则换成第一个，且结果 id 必须来自列表。拦截器无 id 时请求头没有 `X-Workspace-Id`。菜单不含问题集。Requirement 路由名会被守卫改到 `issue_list`。文档标题包含 OpenTask。登录路由路径匹配 `/login`（模块可空）；生产基址 `/` 时附件 URL 不再以 `/opentask` 开头；守卫跳转目标是路由名 `login` / `root`，不包含字符串 `/opentask`。
- **部署冒烟（本地，实施阶段，与浏览器分开记）：** 用新的 `frontend/nginx.conf` 起容器或等价 nginx，`GET /`、`GET /login`、`GET /issue/list`、`GET /f/sample-token` 都回 `index.html`（200，不是 301 到 `/opentask`）。`/assets/` 命中静态文件。不请求 `112.126.60.109`。探活仍是宿主上的 `location = /healthcheck` 转到后端，不新造 `/api/healthcheck`。容器配置要写明 `/api/` 与 `/ws/` 原样转到 `backend:7377`。只有本地后端真的在听时才记录一次真实 API 状态码。
- **浏览器（实施阶段，与单测分开记）：** 零成员账号登录后看到引导而不是主列表的 400；提交名称后进入 Issue 列表，保存的视图请求带上刚创建的工作区 id 且不是 400。切换到第二个自有工作区后列表不出现前一个工作区的 Issue。侧栏没有「问题集」「需求（遗留）」。标签页标题含 OpenTask，图标是现有 OT 标。客户页仍能打开。`/f/:token` 不把未登录用户送进引导页。

主页面指 `VITE_ROUTE_HOME=issue_list` 的 Issue 列表及其保存的视图请求，不是 `/health` 或登录 200。

## 5. 风险

- 方案 C 的并发双建：脚本与引导页同时看到空列表会建两个工作区，都属该用户，不跨租户。正式部署先跑脚本并提交，用户再打开 UI，正常路径只建一个。可接受。
- 去掉 ORM 后，将来的 `alembic revision --autogenerate` 可能提议 drop `issue_collections`。本批不跑 autogenerate 作为提交内容；注释和本设计写明表保留。
- custom `issue` 整棵盖住生成路由。删问题集时只删 collection 子项，不重写 Issue 列表/详情/回收站子项，避免把现行 Issue 菜单收窄或放宽。
- `GET /api/issues` 缺头时的可选过滤是既有行为。本批不把它改成强制头，也不放宽强制头的接口。
- 生产管理员已经有 OpenTask 工作区。脚本补跑看到成员关系后不得再插入第二个，也不得重置口令。
- README 若在代码前改，会先写下尚未存在的行为。计划把 README 放在对应任务之后。
- 根路径占掉 notegit 的 `location /`。仓库改片段不会自动生效；若有人以后运行 `deploy.sh` 且只更新片段、不改那条 `location /`，`/login` 仍然进 notegit。发布说明要把这一步写清。本代理与本批实施都不 SSH、不 reload。
- `location /oauth2/` 若不去掉对 `/oauth2/authorize` 的覆盖，同意页会打到后端而不是 SPA。用精确匹配避免。
- 本地开发代理仍可能出现 `/opentask`。那只存在于 Vite dev。生产 `index.html` 与浏览器地址不得再带这个前缀。

## 6. 自检

- 无未定字段：工作区默认名 OpenTask；跳过开关名 `--skip-workspace`；Requirement 重定向目标 `issue_list`；问题集删除清单在计划里按路径列出。
- 方案 C 未写成已经开工。实施门在计划任务 0。根路径已授权，仍只入库设计，不连服务器。
- Requirement 与客户需求已分开。问题集与 `generic_status_to_issue_set`、保存的视图已分开。
- 登录路径以生成路由为准：`/login` 可省略模块。不假设需要新路径。
- 本批不包含下一 Epic 的范围。
