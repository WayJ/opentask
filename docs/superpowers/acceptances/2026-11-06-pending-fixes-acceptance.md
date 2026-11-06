# 待修批次验收

日期：2026-11-06  
分支：`cursor/pending-fixes-design-658f`  
基线：`main` @ `c1d2424ca87bb3dae5e2a730b86a90f14abf34ad`（PR #3，E99）  
设计：`docs/superpowers/specs/2026-11-06-pending-fixes-design.md`  
计划：`docs/superpowers/plans/2026-11-06-pending-fixes.md`  
PR：https://github.com/WayJ/opentask/pull/4  

Yuri 已复核设计与计划，在请求范围内批准，并指定方案 C。本批按修正实施后停在同一分支，不合并、不部署。

## 批准与修正

- 方案 C：管理员脚本只在该用户没有可用成员关系时创建工作区；前端在空成员关系时引导。两者都做。
- 仓库里的 notegit 共用 vhost 只是条件说明。没有登录 `112.126.60.109`，不声称那台机器上正在跑 notegit，也不声称这次会把它挤掉。根路径的主示例是独立 OpenTask 站点。
- 登录和刷新都在受保护页面取数之前完成工作区解析。先清掉过期或别人的本地选择，再发租户请求。当前用户仍有效的选择保留。引导不拦截 `/f`、`/r`、`/invite`，也不挡住退出和登录。重复执行管理员脚本不重置口令、不重复成员。遗留默认工作区与 `list_for_user` 一样排除。
- 问题集删除专属代码和导入。表 `issue_collections`、已有数据和基线迁移保留。路由表和 OpenAPI 里都没有这些路径。没有跑破坏性 autogenerate。
- README 只写当前部署镜像 `postgres:15-alpine`。旧文档曾写成 16 的对照只留在本文，不写进快速开始。
- 根路径冒烟用的是 `pnpm build --mode prod` 编出来的前端，不是占位 `index.html`。
- 文档标题在导航和语言切换后仍带 OpenTask。图标、启动屏和 logo 用仓库里已有的 OT 图，没有新画。

## Tip

实施提交完成后，tip 记在本节末行。

- 分支：`cursor/pending-fixes-design-658f`
- 设计检查点：`7c812eb37fab02726d829173f54f1fbcf100fcd8`
- tip：提交后补记

## 单元与 API

这些数字来自本机命令，不是浏览器。

| 门禁 | 结果 |
|---|---|
| 后端全量 `cd backend && uv run pytest tests/ -q --tb=line` | **3 failed，1491 passed，27 skipped**，565.53s |
| 上述 3 条单独重跑 | **3 passed**，2.66s |
| 前端 `pnpm test` | **68 files，446 passed** |
| 前端生产构建 `pnpm build --mode prod` | 成功。产物 `index.html` 的脚本是 `/assets/...`，没有 `/opentask/assets/` |
| CLI `uv run pytest -q -m "not integration" -o addopts=` | **830 passed，3 skipped，84 deselected**。集成用例和 `scripts/e14_cli_smoke.sh` 未跑 |
| 改过的前端文件 eslint | 0 error |

全量失败的三条都在 `tests/tasks/test_tasks_jira_wire.py`：`TestJqlSearch::test_status_in_and_display_names`、`TestJqlSearch::test_pagination_offset`、`TestMetadata::test_user_search`。日志是无法识别的 `ISSUE2026-…` 单号。本批没有改 Jira 线码。E99 验收已把 `test_user_search` 记为顺序污染，单独运行可以通过。这次另外两条也是单独运行通过，按同一类处理，不当成这次改动引入的回归。

CLI 第一次有 5 条失败，原因是虚拟环境里没有未声明的 `prompt_toolkit` 和 `PyYAML`。只在本地虚拟环境装上后再跑，计数如上。没有把这两个包写进依赖。

全仓 `eslint .` 在本批之前就有大量既有 error。没有对全仓执行 `--fix`。

## 浏览器与根路径冒烟

浏览器和接口计数分开。Chrome 打开的是本地 nginx 上的编译产物 `http://127.0.0.1:8080`，后端是本机 `127.0.0.1:7377`。没有截图留口令或 token。

浏览器里实际走过：

- `/login` 标题为「登录 - OpenTask」。未登录时打开 `/issue/list` 回到 `/login`。
- 已有成员的账号登录后进入 `/issue/list`，标题为「我的问题 - OpenTask」。刷新后仍停在该页。保存的视图和问题列表请求带的是该账号自己的工作区，第一条工作区请求不带 `X-Workspace-Id`。
- 零成员账号登录后进入 `/workspace-onboarding`，标题为「创建工作区 - OpenTask」。创建后进入问题列表，工作区 id 与前一个账号不同。
- `/f/sample-token` 停在公开表单，标题「公开表单 - OpenTask」，请求打到同源 `/api/public/forms/sample-token`，接口 404，页面显示「表单不存在或已禁用」。已登录时也不会被送去引导页。
- `/r/sample-token` 停在请求状态页，标题「请求状态 - OpenTask」，同源状态接口 404。
- `/invite/sample-token` 停在邀请页，未知邀请显示不存在。
- 客户详情页仍在，上面有「新建需求」。侧栏正文里没有「问题集」。
- `/favicon.png` 与 `frontend/public/favicon.png` 字节相同。

本地 nginx 冒烟（编译产物，不是占位页）：

- 容器等价配置在 `127.0.0.1:8080`：`/`、`/login`、`/issue/list`、`/f`、`/r`、`/oauth2/authorize` 返回 SPA；主脚本约 1.7 MB 且为 200；登录响应不是跳进 `/opentask`。
- `/ws/workspace` 带升级头时返回 `101 Switching Protocols`。
- 宿主片段在 `127.0.0.1:8090`：`/oauth2/authorize` 是 SPA；`POST /oauth2/token` 是后端 422，不是 SPA。`/tasks/ping` 401，`/capabilities` 与 `/healthcheck` 仍是后端 JSON。`/api/workspaces` 未登录 401。`/rest/api/2/issue` 和 `/mcp` 仍是 SPA，没有新接到后端。`/docs/` 是前端静态目录的 403，不是 FastAPI 文档页。

本地冒烟把容器配置里的 `listen` 和 Docker DNS `backend` 改成了本机端口和 `127.0.0.1`。提交的 `frontend/nginx.conf` 仍使用 `backend` 和 `127.0.0.11`。

## 发布说明

仓库里的产物：

- 前端生产基址 `/`。镜像把 `dist` 放到站点根，健康检查打 `/login`。
- 新增 `deploy/nginx/opentask-site.conf` 作为独立站点示例。`deploy/nginx/opentask-locations.conf` 把 `/api/`、`/ws/` 原样转到 `127.0.0.1:7377`，精确的 `/oauth2/authorize` 给前端，其余 `/oauth2/` 给后端，并保留原先的 `/tasks/`、`/capabilities`、`/healthcheck`。
- `deploy/deploy.sh` 检查生产基址是 `/`，创建管理员时不传重置口令。本批没有执行这个脚本，没有 reload 任何现网。

没有检查 `112.126.60.109`。若某台机器的 nginx 里已经有别的 `location /`，操作者要自己处理冲突。那不是本批观察到的现网事实。旧的 `/opentask` 书签在新配置下不再由 OpenTask 接住，仓库里没有加回到 `/opentask` 的 301。

## 保留与限制

- `issue_collections` 表和 `backend/alembic/versions/2026_10_31_1529-003ccd38d5cd_pg_initial_baseline.py` 仍在。ORM 不再映射这张表。不要提交会 drop 它的 autogenerate。
- Requirement 的 API 还在，界面不再进入。客户和「新建需求」保留。
- 部署镜像是 `postgres:15-alpine`。本机 pytest 用的是系统 PostgreSQL 16，不是该镜像。旧 README 把数据库写成 16 的说法只记在这里。
- elegant-router 仍会警告单字母目录 `f` 和 `r` 不合格。公开页在路由变换时再挂上视图，避免生成器把它们丢掉，也避免模块初始化时读到尚未就绪的视图表。
- 脚本和引导页若同时看到空列表，可能给同一用户建两个工作区。不跨租户。
- 示例站点没有 TLS。
- CLI 集成测试和 `scripts/e14_cli_smoke.sh` 未跑。
- 全仓 eslint 不是干净的。改过的文件是干净的。
- 后端全量 3 条失败见上，单独重跑通过。
- 没有合并，没有部署，没有打开下一 Epic。
