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

- 分支：`cursor/pending-fixes-design-658f`
- 设计检查点：`7c812eb37fab02726d829173f54f1fbcf100fcd8`
- 实施提交：`4110a77080b0093987abe63f976bdc760fa06ecb`
- 实施验收补记：`f284692d60d92d487d19090076b051dd00a85331`
- 交付前复核与本文件同时入库。分支 tip 即该提交。

## 行数

`c1d2424..f284692` 是 94 个文件，`+52925 / -19893`。其中两份内容相同的 OpenAPI 各 `+25486 / -7104`，合计占插入行的约 96%。基线快照 183 条路径，该提交 326 条。删掉的是 4 条问题集路径。多出来的 147 条是代码里已经有、快照里没有的工作区、客户、保存视图、公开表单等契约。这是补齐后的契约，不是格式化噪声，不能退回旧快照。

其余大块是问题集页面、服务、CLI 和测试的删除，以及设计和计划。`frontend/pnpm-lock.yaml` 只增加 12 行，用来锁住 `package.json` 里已经声明的 `@pinia/testing`，冻结安装需要它。`frontend/src/plugins/loading.ts` 是 `+2 / -153`，去掉 soybean 的内联 SVG，改用仓库里已有的 OT 图。`AgentPromptModal.vue` 整文件删除，基线上只有问题集详情页导入它。

复核在此之上再改 15 个文件左右。OpenAPI 只为 `POST /api/workspaces/ensure-owner` 各增加 45 行，路径从 326 变为 327。没有再重写整份快照。

## 单元与 API

这些数字来自本机命令，不是浏览器。对照用的是同一台 PostgreSQL、同一条 `pytest tests/ -q --tb=line`、各自的空库。`tests/conftest.py` 在会话结束时 `drop_all`，所以跑完后库里没有业务表。

| 门禁 | 结果 |
|---|---|
| 基线 `c1d2424`，库 `opentask_baseline` | **1499 passed，24 skipped，0 failed**，566.16s |
| 当前工作区，库 `opentask_head` | **1500 passed，24 skipped，0 failed**，510.22s |
| 前端 `pnpm test` | **68 files，446 passed** |
| 前端生产构建 `pnpm build --mode prod` | 成功。产物脚本是 `/assets/index-DSH-jR5k.js`，没有 `/opentask/assets/` |
| CLI 非集成 | 实施时 **830 passed，3 skipped，84 deselected**。本复核没有改 CLI 源码，没有重跑这一组 |
| CLI `scripts/e14_cli_smoke.sh` 对 `127.0.0.1:7377` | **E14 smoke OK** |
| CLI `-m integration` | **3 passed，41 skipped**。通过的是本机 `config` / `help` / `version`。其余在登录处跳过 |
| 改过的前端文件 eslint | 0 error |

先前在共用库 `opentask_test` 上出现过 3 failed / 1491 passed / 27 skipped。那一次不能当成这次的回归分类。三条的名字是：

1. `tests/tasks/test_tasks_jira_wire.py::TestJqlSearch::test_status_in_and_display_names`
2. `tests/tasks/test_tasks_jira_wire.py::TestJqlSearch::test_pagination_offset`
3. `tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`

前两条的日志是无法识别的 `ISSUE2026-596813`。第三条是 `GET /rest/api/2/user/assignable/search?username=.&maxResults=50` 的结果里没有 `test_user`。单独重跑能过，这不能说明三条都是 E99 已经记录的 `test_user_search` 顺序污染。E99 验收只记了第三条。

同一顺序、空库、同一台数据库上，基线和当前树这三条都是 PASSED。当前树没有改 Jira 线码。不把它们改成“已知 flaky”，也不为了消掉旧库上的失败去改 Jira。

CLI 集成文件把账号写成占位符 `xxxxx`，并且只有设置了 `OPENTASK_TEST_API_URL` 才不整文件跳过。对着本机 API 设置了该变量后，登录失败被用例自己跳过。这不是整组 CLI 集成通过。`e14_cli_smoke.sh` 是对着本机 API 跑通的冒烟。

全仓 `eslint .` 在本批之前就有大量既有 error。没有对全仓执行 `--fix`。

## 浏览器与根路径冒烟

浏览器和接口计数分开。Chrome 打开的是本地 nginx 上的编译产物 `http://127.0.0.1:8080`，后端是本机 `127.0.0.1:7377`。没有截图留口令或 token。

浏览器里实际走过：

- `/login` 标题为「登录 - OpenTask」。未登录时打开 `/issue/list` 回到 `/login`。
- 已有成员的账号登录后进入 `/issue/list`，标题为「我的问题 - OpenTask」。刷新后仍停在该页。登录后的请求顺序是：`/api/workspaces` 不带 `X-Workspace-Id`，随后 `/api/auth/getUserInfo` 带上解析后的 id，问题和保存视图使用同一个 id。刷新会再清一次本地选择并重新解析，之后的问题和视图请求仍是这一个 id。
- 零成员账号登录后进入 `/workspace-onboarding`，标题为「创建工作区 - OpenTask」。页面上有「退出登录」。点下去之后停在 `/login/pwd-login?redirect=/workspace-onboarding`，正文是密码登录表单，本地不再留下 token。创建工作区走 `POST /api/workspaces/ensure-owner`。
- `/f/sample-token` 停在公开表单，标题「公开表单 - OpenTask」，请求打到同源 `/api/public/forms/sample-token`，接口 404，页面显示「表单不存在或已禁用」。已登录时也不会被送去引导页。
- `/r/sample-token` 停在请求状态页，标题「请求状态 - OpenTask」，同源状态接口 404。
- `/invite/sample-token` 停在邀请页，未知邀请显示不存在。
- 客户详情页仍在，上面有「新建需求」。侧栏正文里没有「问题集」。
- `/favicon.png` 与 `frontend/public/favicon.png` 字节相同。

本地 nginx 冒烟（编译产物，不是占位页）：

- 容器等价配置在 `127.0.0.1:8080`：`/`、`/login`、`/issue/list`、`/f`、`/r`、`/oauth2/authorize` 返回 SPA；主脚本约 1.7 MB 且为 200；登录响应不是跳进 `/opentask`。
- `/ws/workspace` 带升级头时返回 `101 Switching Protocols`。`/ws/hub` 在 8080 和 8090 上都是 SPA 的 `200 text/html`，没有升级到后端。
- 宿主片段在 `127.0.0.1:8090`：`/oauth2/authorize` 是 SPA；`POST /oauth2/token` 是后端 422，不是 SPA。`/tasks/ping` 401，`/capabilities` 与 `/healthcheck` 仍是后端 JSON。`/api/workspaces` 未登录 401。`/rest/api/2/issue` 和 `/mcp` 仍是 SPA，没有新接到后端。`/docs/` 是前端静态目录的 403，不是 FastAPI 文档页。

本地冒烟把容器配置里的 `listen` 和 Docker DNS `backend` 改成了本机端口和 `127.0.0.1`。提交的 `frontend/nginx.conf` 仍使用 `backend` 和 `127.0.0.11`。

## 发布说明

仓库里的产物：

- 前端生产基址 `/`。镜像把 `dist` 放到站点根，健康检查打 `/login`。
- 新增 `deploy/nginx/opentask-site.conf` 作为独立站点示例。`deploy/nginx/opentask-locations.conf` 把 `/api/` 和精确的 `/ws/workspace` 转到 `127.0.0.1:7377`，不转发 `/ws/hub*`。精确的 `/oauth2/authorize` 给前端，其余 `/oauth2/` 给后端，并保留原先的 `/tasks/`、`/capabilities`、`/healthcheck`。
- `deploy/deploy.sh` 检查 `VITE_BASE_URL=/` 和 `VITE_SERVICE_BASE_URL=/`，并拒绝 `dist` 里出现 `/opentask/assets/`。创建管理员时不传 `--reset-password`。本批没有执行这个脚本，没有 SSH，没有 reload 任何现网。

没有检查 `112.126.60.109`。若某台机器的 nginx 里已经有别的 `location /`，操作者要自己处理冲突。那不是本批观察到的现网事实。旧的 `/opentask` 书签在新配置下不再由 OpenTask 接住，仓库里没有加回到 `/opentask` 的 301。

## 准备与回滚

没有对任何现网执行。操作者以后发布时：

1. 生产构建使用 `VITE_BASE_URL=/` 和 `VITE_SERVICE_BASE_URL=/`。`deploy/deploy.sh` 会检查这两行，并检查 `dist/index.html` 引用 `/assets/` 而不是 `/opentask/assets/`。
2. 前端镜像把 `dist` 放到容器站点根。容器 `frontend/nginx.conf` 把 `/api/` 和精确的 `/ws/workspace` 转到 `backend:7377`，使用 Docker DNS `127.0.0.11`。`/ws/hub*` 留在 SPA。
3. 宿主使用 `deploy/nginx/opentask-site.conf` 加上 `deploy/nginx/opentask-locations.conf`。`nginx -t` 通过后再 reload。健康检查打 `/login`。数据库镜像仍是 `postgres:15-alpine`。
4. 管理员脚本不传 `--reset-password`。已有成员的账号不会被补一个工作区，口令也不会被改掉。

回滚是换回上一份镜像，并把宿主片段换回 `c1d2424` 的 `deploy/nginx/opentask-locations.conf`。那一版只把 `/opentask` 转到前端容器，另外保留 `/oauth2/`、`/tasks/`、`/capabilities`、`/healthcheck`，没有把 `/ws/` 转到后端。仓库里没有从 `/opentask` 到 `/` 的 301，旧书签不会自动改道。示例站点没有 TLS。不要在回滚说明里写入口令或密钥。已有的 `.env` 按 `deploy.sh` 的行为不会被覆盖。

## 保留与限制

- `issue_collections` 表和 `backend/alembic/versions/2026_10_31_1529-003ccd38d5cd_pg_initial_baseline.py` 仍在。ORM 不再映射这张表。不要提交会 drop 它的 autogenerate。
- Requirement 的 API 还在，界面不再进入。客户和「新建需求」保留。
- 部署镜像是 `postgres:15-alpine`。本机 pytest 用的是系统 PostgreSQL 16，不是该镜像。旧 README 把数据库写成 16 的说法只记在这里。
- elegant-router 仍会警告单字母目录 `f` 和 `r` 不合格。公开页在路由变换时再挂上视图。本复核的生产构建仍打印这两条警告，`/f/:token` 和 `/r/:token` 的单测和浏览器都还在。
- 同一用户的首次工作区由 `ensure_owner_workspace` 的事务咨询锁收成一个。普通 `POST /api/workspaces` 不加这把锁，已有成员的用户仍可再建。没有删除已有工作区，没有新增迁移。
- CLI 集成用例因占位账号不能当成通过。冒烟脚本可以通过。
- 全仓 eslint 不是干净的。改过的文件是干净的。
- 没有合并，没有部署，没有打开下一 Epic。
