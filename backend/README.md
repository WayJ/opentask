# OpenTask Backend

基于 FastAPI 的 OpenTask 后端服务，提供需求管理、项目追踪、AI 集成等核心功能。

## 目录

- [安装](#安装)
- [环境配置](#环境配置)
- [数据库（PostgreSQL）](#数据库postgresql)
- [运行后端](#运行后端)
- [数据库迁移](#数据库迁移)
- [测试](#测试)
- [开发工具](#开发工具)
- [API 文档](#api-文档)
- [示例数据库](#示例数据库)

## 安装

确保已安装 Python 3.11+。

### 使用 UV（现代 Python 包管理器）

从 [官方网站](https://docs.astral.sh/uv/getting-started/installation/) 安装 UV，然后运行：

```bash
uv sync
```



### 2. 配置认证（可选）

在 `.env` 文件中设置基础认证：

```bash
AUTH_USERNAME=admin
AUTH_PASSWORD=admin
```

### 5. 运行数据库迁移

```bash
# 使用虚拟环境
alembic upgrade head

# 或使用 uv
uv run alembic upgrade head
```

## 小蓝工作台 Ontology MCP

`POST /mcp` 提供无会话、只读的 MCP 工具。业务本体版本为 `1.0.0`，数据沿用 PostgreSQL 与 OpenTask 的工作区、部门数据范围。每次对象读取和关系遍历都检查当前 OAuth 成员权限；不可见与不存在对象均返回 `OBJECT_NOT_FOUND`（业务状态 404），关系总数不包含不可见目标。

| 工具 | 用途 |
|---|---|
| `discover_ontology` | 获取本体版本、类型目录、scope 与分页约定 |
| `describe_object_type` | 按类型读取字段、原生枚举、可筛选属性、关系方向与基数 |
| `search_objects` | 搜索 Issue / Project / Member，支持类型适用的筛选和分页 |
| `get_object` | 用类型和对象 id 读取详情 |
| `get_related_objects` | 沿指定关系遍历一跳，起点和目标均须可见 |
| `list_issues` | 兼容旧任务表示，保留原输出结构及状态映射 |

本体对象使用 OpenTask 原生 issue 状态，如 `open`、`in_progress`、`resolved`。`list_issues` 的契约状态（如 `todo`）不用于本体筛选。对象主键为返回结果的 `id`，业务单号在 Issue 的 `properties.issue_code`。

Issue 支持项目、主负责人、报告人、父子问题与阻塞/依赖/重复/关联关系；Project 支持问题集合；Member 支持主负责和报告的问题。`assignee` / `assigned_issues` 表示主负责人，不含额外协作者。完整关系目录通过 `describe_object_type` 获取。关系目标为不可见对象时返回空集合，不透露其标识。查询和关系结果每页默认 20、最多 50 个对象，`offset` 范围为 0–100000，返回 `total`、`has_more`、`next_offset`。列表描述最多 1000 字符，详情描述最多 8000 字符，截断字段记录在 `truncated_properties`。

使用成员 OAuth 授权码令牌：Issue 需要 `read:tasks`，Project 需要 `read:projects`；`profile` 只能读取本人的 Member，`read:members` 可以读取共享工作区且符合部门范围的启用成员。类型发现只需有效 OAuth 身份。新增 scope 后必须重新取得成员同意；旧令牌不会自动扩权。所有工具都为只读，本期不提供业务写入动作。

小蓝应用使用 `OAUTH_AUTHORIZATION_CODE`，MCP 路径 `/mcp`，令牌端点 `/oauth2/token`，用户信息端点 `/oauth2/userinfo`，授权地址指向前端 `/oauth2/authorize`。申请所需 scopes 后，成员在工作台连接 OpenTask。`/tasks/token` 产生的客户端凭据令牌不适用于此接口。

工作台验证示例：先询问“OpenTask 有哪些对象类型和问题关系？”，再询问“查询测试问题，并说明它所属项目、主负责人和阻塞的问题”。程序调用可先 `search_objects({"object_type":"Issue","query":"测试"})`，再将返回 id 用于 `get_related_objects({"object_type":"Issue","object_id":"<id>","relation":"blocks"})`。

响应同时提供 JSON 文本与 `structuredContent`。本体工具的查询和权限失败使用 HTTP 200 + `isError=true`，并在 `error` 中提供 `code`、业务 `status`（400/403/404）和 `detail`，以免平台代理把对象不存在误判为会话过期。无效或缺失 OAuth 令牌仍返回 HTTP 401；旧 `list_issues` 保持原 HTTP 参数/scope 错误语义。JSON-RPC 解析、请求形态和未知工具错误使用对应 error code。

## 数据库（PostgreSQL）

OpenTask 统一使用 PostgreSQL 16（ADR D11：dev/test/prod 统一 PG）。

### 1. 启动 PG 容器

```bash
# 直连 Docker Hub 超时时，可先经镜像站拉取再改 tag：
#   docker pull docker.m.daocloud.io/library/postgres:16
#   docker tag docker.m.daocloud.io/library/postgres:16 postgres:16
docker run -d --name opentask-pg \
  -e POSTGRES_USER=opentask \
  -e POSTGRES_PASSWORD=opentask \
  -e POSTGRES_DB=opentask_test \
  -p 5432:5432 \
  -v opentask-pgdata:/var/lib/postgresql/data \
  postgres:16

# 容器初始化只创建测试库 opentask_test，开发库需补建一次：
docker exec opentask-pg psql -U opentask -d opentask_test -c "CREATE DATABASE opentask;"
```

### 2. 连接配置

`backend/config/*.yaml` 中的 `database.postgres` 段（dev/test 默认指向本地容器 `localhost:5432`，用户/密码 `opentask/opentask`，测试库名 `opentask_test`，开发库名 `opentask`）。环境变量 `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DATABASE` 优先级高于 yaml（生产环境通过 `${POSTGRES_*}` 占位符注入）。

连接串由 `opentask.config` 生成：同步 `postgresql+psycopg2://`，异步 `postgresql+asyncpg://`。

### 3. 初始化

```bash
# 容器就绪检查
docker exec opentask-pg pg_isready -U opentask -d opentask_test

# 建表/迁移（开发库）
APP_ENV=development uv run alembic upgrade head
```

## 运行后端

### 开发模式

```bash
# 激活虚拟环境
sh run_dev.sh
```

### 生产模式

```bash
sh stop_server.sh

sh run_server_nohup.sh

```

### 容器化发布与初始管理员

生产发布用仓库根的 `docker-compose.prod.yml`（端口只绑回环，外部经宿主 nginx 进入），
完整流程见 `deploy/README.md`。

**全新部署的库是空的**——`alembic upgrade head` 只建表不播种账号，而后端**没有注册接口**
（只有登录），所以发布后必须显式建出第一个管理员：

```bash
# 在后端容器内执行（发布机 /opt/opentask）
docker compose -f docker-compose.prod.yml exec backend \
    python scripts/create_admin_user.py --username admin

# 重置已有账号的口令
docker compose -f docker-compose.prod.yml exec backend \
    python scripts/create_admin_user.py --username admin --password '新口令' --reset-password
```

脚本幂等：账号已存在默认跳过（不覆盖口令）；会先跑一遍用户中心播种，再把用户显式挂到
`admin` 角色；口令只存 bcrypt 哈希，库里无明文。

### 验证服务运行

```bash
# 健康检查
curl http://localhost:7377/healthcheck

# 查看 API 文档
# 浏览器访问: http://localhost:7377/docs
```

## 数据库迁移

### 创建新迁移

```bash
# 自动生成迁移（基于模型变更）
alembic revision --autogenerate -m "描述你的变更"

# 手动创建迁移
alembic revision -m "描述你的变更"
```

### 应用迁移

```bash
# 升级到最新版本
alembic upgrade head

# 升级到特定版本
alembic upgrade <revision_id>

# 回滚一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision_id>
```

### 外键约束注意事项

当使用 SQLite 时，如果迁移涉及外键关系，请记得添加以下 PRAGMA 命令：

```python
# 在迁移文件中
def upgrade():
    # 禁用外键检查
    op.execute("PRAGMA foreign_keys=OFF;")

    # 你的迁移操作
    # ...

    # 重新启用外键检查
    op.execute("PRAGMA foreign_keys=ON;")
```

## 测试

```bash
# 运行所有测试
pytest . -vv

# 运行特定测试文件
pytest tests/test_specific.py -vv

# 运行测试并生成覆盖率报告
pytest --cov=opentask --cov-report=html

# 使用 uv
uv run pytest . -vv
```

## 开发工具

### 代码格式化

```bash
# 使用 Black 格式化代码
black .

# 使用 Ruff 进行 lint 检查
ruff check .

# 使用 Ruff 修复问题
ruff check . --fix
```

### 类型检查

```bash
# 使用 mypy 进行类型检查
mypy opentask
```

### Pre-commit 钩子

```bash
# 安装 pre-commit 钩子
pre-commit install

# 手动运行 pre-commit
pre-commit run --all-files
```

## API 文档

启动服务后，可以通过以下地址访问 API 文档：

- **Swagger UI**: http://localhost:7377/docs
- **ReDoc**: http://localhost:7377/redoc
- **OpenAPI Schema**: http://localhost:7377/openapi.json

> 全量 spec 另随代码提交为 `backend/openapi.json` / `backend/openapi_current.json`（两份内容一致）。
> 路由变更后需重新导出：`cd backend && uv run python scripts/export_openapi.py`（脚本见 `backend/scripts/export_openapi.py`）。

## 任务源契约 API（Orca 集成）

OpenTask 以「通用任务源」形态对 Orca 暴露 REST 契约（模拟 Jira 对接模式），路由挂根，与既有 `/api/issues` 并列、互不影响。代码位于 `opentask/api/tasks/`，测试位于 `tests/tasks/`（PostgreSQL）。

### 端点总览

| 端点 | 说明 |
|---|---|
| `GET /capabilities` | 能力声明（**公开**）：契约版本、端点支持、鉴权模式、当前生效状态词表 |
| `POST /tasks/token` | OAuth2 client credentials 换 token（**公开**，凭证即 API Key） |
| `GET /tasks` | 列表：`status`/`assignee` 过滤 + `limit`/`offset` 分页 + `updated_since` 增量游标（排他语义） |
| `POST /tasks` | 创建（title/description/assignee/status/labels 完整落库，经 issue service） |
| `GET /tasks/{task_id}` | 读取（软删除的不可见） |
| `PATCH /tasks/{task_id}` | 更新（PATCH 语义；状态变更写既有 timeline） |
| `DELETE /tasks/{task_id}` | 软删除（复用 `is_deleted`，不物理删除） |

除前两个公开端点外，其余端点均需 Bearer 凭证。

### 鉴权

两种模式，均以 `Authorization: Bearer <token>` 携带，复用既有 access_token 体系（用户 API Key，`vk_` 前缀）：

1. **Bearer API Key（推荐，长周期）**：先在 OpenTask 前端「个人设置 → Access Token」或 `POST /api/access-tokens` 创建 API Key（需登录态），直接作为 Bearer 凭证调用契约端点。
2. **OAuth2 client credentials（短时效 JWT）**：以 API Key 为 client secret 换短时效 JWT（默认 2 小时，`auth.access_expire_minutes` 可配），适合不便长期持有 Key 的调用方：

   ```bash
   curl -X POST http://localhost:7377/tasks/token \
     -d "grant_type=client_credentials" \
     -d "client_id=<可选：Key 归属用户 ID>" \
     -d "client_secret=<vk_ 开头的 API Key>"
   # → {"access_token": "<JWT>", "token_type": "Bearer", "expires_in": 7200}
   ```

**错误语义（S6 定稿：统一错误码族）**：契约层语义错误统一返回可辨识错误码 + 可读消息（401 附 `WWW-Authenticate: Bearer`）：

```json
{"detail": {"code": "CONTRACT_AUTH_MISSING", "message": "..."}}
```

| HTTP | code | 触发场景 |
|---|---|---|
| 400 | `CONTRACT_AUTH_UNSUPPORTED_GRANT` | `POST /tasks/token` 不支持的 `grant_type` |
| 401 | `CONTRACT_AUTH_MISSING` | 未携带 Bearer 凭证 |
| 401 | `CONTRACT_AUTH_INVALID` | 凭证错误/过期/吊销/用户禁用 |
| 403 | `CONTRACT_FORBIDDEN` | 操作被 `contract.forbidden_operations` 禁用（禁操作） |
| 404 | `CONTRACT_TASK_NOT_FOUND` | 任务不存在（含软删除后） |
| 422 | `CONTRACT_STATUS_UNKNOWN` | `status` 不在生效词表内（查询参数或请求体） |
| 503 | `CONTRACT_UNAVAILABLE` | 后端依赖（数据库）不可达 |

语义优先级：**503（依赖不可达）先于 401（凭证校验）先于 403（禁操作）**——凭证无法在依赖不可达时验证；未认证请求无从谈禁不禁。

- 结构性 schema 违规（缺字段/类型错/超长）仍为 FastAPI 标准 422 校验体（`detail=[{loc,msg,type}]`）；状态词表随配置运行时变化、无法静态穷举，故词表违规单独带错误码。
- 503 在依赖解析阶段以轻量探测查询判定，`/tasks` 全端点与 `/tasks/token` 语义一致；`GET /capabilities` 无 DB 依赖，后端不可达时仍可用于协商（消费方降级路径）。
- 禁操作表经 `GET /capabilities` 的 `features.forbidden_operations` 实时下发（逗号分隔操作名；`none` = 全放行），消费方可据此隐藏入口或提前拦截。
- client credentials 换到的 JWT 为无 `scp` 声明的无限制 token（API Key bearer 模式同权，交换不降权）；不下发 refresh token，也不落 `refresh_tokens` 行（RFC 6749 §4.4.3）。

### 状态映射配置（`contract.status_mapping`）

契约状态词表与 OpenTask IssueStatus 的双向映射可配置（`config/*.yaml`，默认表见 `opentask/api/tasks/mapping.py`；**未配置该段时使用代码默认表**，配置非法时启动后首次访问即报错、拒绝静默降级）：

```yaml
contract:
  # key 必须覆盖全部 6 种 IssueStatus；value 为通用状态（可自定义词表）
  # 反向取规范逆：同一通用状态多值时取枚举序在前者（done ← resolved/closed → resolved）
  status_mapping:
    open: todo
    in_progress: in_progress
    feedback: in_review
    resolved: done
    closed: done
    rejected: cancelled
  # 契约层无 type 概念：POST /tasks 落库的默认 issue 类型
  # 必须在 IssueType 词表内（bug/feature/question/feedback/incident/improvement），
  # 非法值启动后首次访问即报错（快速失败，不静默降级）
  default_issue_type: feature
  # 可选：禁用部分契约操作（默认空 = 全放行；被禁操作 → 403 CONTRACT_FORBIDDEN）
  # 合法值：list_tasks/create_task/get_task/update_task/delete_task；未知值快速失败
  forbidden_operations: []
```

- 配置在 `default.yaml` 集中维护，环境配置（development/production/test.yaml）可按键深合并覆盖；**修改后重启进程生效**。
- `GET /capabilities` 的 `status_vocabulary` 与 `features.status_mapping_source`（`config`/`default`）、`features.forbidden_operations` 实时反映生效配置，消费方可据此自适应。
- 往返保证：`generic → IssueStatus → generic` 对生效词表全部状态恒等（`resolved`/`closed` 同归 `done` 时逆取 `resolved`）。
- 词表语义细节：`GET /tasks?status=` 按正映射**集合**过滤（`done` 命中 `resolved` 与 `closed`，与列表正向展示口径一致）；`POST /tasks` 缺省 `status` 时自生效词表推导（含 `todo` 取 `todo`，否则规范序首个）。

### OpenAPI spec（随代码提交）

契约端点的独立 spec 由 FastAPI 既有机制自动生成并随代码提交为 `backend/openapi_contract.json`（与全量 `openapi.json` 分开，避免混淆）：

```bash
cd backend
AUTH_SECRET_KEY=<密钥> uv run python -m opentask.api.tasks.openapi_export
```

路由、schema 与错误响应模型（`ContractErrorResponse`，含 401/403/404/503 声明与 Bearer 安全方案）均从代码推导，无手写 spec；`tests/tasks/test_tasks_openapi.py` 对账测试守护一致性（spec 文件与实时构建不一致即测试失败）。

### Jira 线格式兼容层（`/rest/api/2/*`，S7）

让 Orca 的 Jira 集成把 OpenTask 当**自建 Jira（Server/DC）**调用：契约端点（`/tasks`，D12 形状）保持不动，Jira 层与其共用 mapping/auth/schemas 内核。代码位于 `opentask/api/jira/`（keys/jql/converters/auth/errors/router/wiring），经 ASGI 转发路由挂在 tasks 契约路由下（`include_in_schema=False`，不污染契约 OpenAPI）。

| 端点 | 说明 |
|---|---|
| `GET /rest/api/2/myself` | 连接验证 + 当前用户（Orca 连接向导的第一跳） |
| `POST /rest/api/2/search` | JQL 子集搜索（`assignee/reporter = currentUser()`、`status( = / != / in )`、`statusCategory`、`key = / in`、`project`、`summary/description/text ~`、`ORDER BY updated`；子集外 400） |
| `GET/POST /rest/api/2/issue[/{key}]` | 读取/创建/更新（key 形状 `OPENTASK-{n}`，由 KEY-N 投影，如 `OT-1 → OPENTASK-{KEY_N_BASE+…}`；写成功 204） |
| `GET/POST /rest/api/2/issue/{key}/transitions` | 可流转列表 / 执行流转（transition.id = 通用状态 token） |
| `GET/POST /rest/api/2/issue/{key}/comment` | 评论（`startAt`/`maxResults`/`total` 翻页） |
| `PUT /rest/api/2/issue/{key}/assignee` | 分配/取消（server 形状 `{name}`，兼容 `{accountId}`） |
| `GET /rest/api/2/project`、`/priority`、`/field`、`/issue/createmeta/{proj}/issuetypes[/​{type}]`、`/user[/​assignable]/search`、`/filter/favourite` | 元数据（单虚拟项目 OPENTASK；`/field` 空数组即安全） |

- **鉴权**：`Authorization: Basic base64(user:vk_…)`（密码位即 API Key，用户名位不校验）或 `Bearer vk_…/JWT`，统一走契约 access_token 内核（`api/tasks/auth.resolve_contract_token`）。
- **错误**：沿用 CONTRACT_* 错误码语义，响应体为 Jira 形状 `{"errorMessages": ["CONTRACT_XXX: …"], "errors": {…}}`（Orca 适配器按该形状解析）。
- **禁操作联动**：`contract.forbidden_operations` 对 Jira 线同样生效（list/create/get/update 映射到对应契约操作，403 同语义）。
- **对接 Orca**：Settings → Jira → 添加自建站点（Site URL `http://<host>:<port>`、Server 模式、PAT = `vk_` API Key）；连接即调 `/myself` 验证。端点形状依据与 E2E 证据见 `docs/superpowers/sprints/2026-11-01-S7-orca-jira-probe.md` 与 `…-orca-e2e-evidence.md`；往返测试 `tests/tasks/test_tasks_jira_wire.py`。
- **完整契约文档**：本节是速查摘要；**仓内权威契约**为 `backend/docs/jira-wire.md`（18 个端点全表、请求/响应形状、JQL 支持子集、状态映射、错误码表、已知边界）。该层以 ASGI catch-all 挂载、不进 OpenAPI spec，故文档漂移由 `tests/tasks/test_jira_wire_doc.py` 拦截（新增端点未写文档即测试红）。

## OAuth2 Provider（对外授权）

OpenTask 作为 OAuth2 **授权服务器**（Provider），供外部应用代表用户读取 OpenTask 数据。
代码位于 `opentask/api/oauth2/`（router / read_api / dependencies / schemas）与
`opentask/services/oauth2/`，测试位于 `tests/oauth2/`。

| 端点 | 说明 |
|---|---|
| `GET /api/oauth2/authorize/context` | 校验授权请求（client / redirect_uri / scope），返回同意页上下文 |
| `POST /api/oauth2/authorize/approve` | 同意 / 拒绝 → 返回跳转 URL（带 `code` 与 `state`） |
| `POST /oauth2/token` | 授权码换令牌（RFC 6749 §5 **标准**响应体，不走本仓 `{code,message,data}` 包装——包装会破坏 OAuth2 互操作性） |
| `GET /oauth2/userinfo` | 当前代表用户信息 |
| `POST /oauth2/revoke` | 吊销令牌 |
| `GET/POST/PATCH/DELETE /api/oauth2/clients` | 客户端注册管理（**管理员权限**） |
| `GET /oauth2/api/{me,tasks,projects,requirements}` | 只读数据面（按 scope 与**成员可见集**收窄） |

- **scope**：`profile` / `read:tasks` / `read:projects` / `read:requirements`；scope 不足 → 403 `insufficient_scope`，请求 scope ⊄ 客户端允许集 → `invalid_scope`。
- **令牌**：JWT，claims = `sub`（user.id）+ `tv`（token_version）+ `aud`（client_id）+ `scope` + `jti` + `exp`；**用 `scope` 不用 `scp`**（`scp` 已被内部受限令牌占用，语义互斥）。授权码一次性消费、10min TTL，重放即吊销该用户全部 OAuth 令牌。
- **前提（重要）**：资源所有者身份由**授权服务器的登录会话**决定——成员须**先有 OpenTask 账号**
  并登录，才能完成同意（2026-11-03 产品口径，详见 `docs/superpowers/specs/2026-11-02-oauth2-provider-design.md` §280）。
- **安全边界**：带 `aud` 的 OAuth 令牌**进不了**通用 `/api/*` 与契约层 `/tasks`（既有鉴权链校验
  aud 不匹配即 401），只读 scope 不会被越权扩大；不带 `aud` 的既有会话令牌不受影响。

## 项目结构

```
backend/
├── opentask/
│   ├── api/               # API 路由层
│   │   ├── auth/          # 认证 API
│   │   ├── requirement/   # 需求管理 API
│   │   ├── project/       # 项目管理 API
│   │   ├── agent/         # AI Agent API
│   │   └── ...
│   ├── models/            # SQLAlchemy 数据模型
│   ├── services/          # 业务逻辑层
│   ├── repositories/      # 数据访问层
│   ├── app.py             # FastAPI 应用配置
│   ├── main.py            # 应用入口
│   ├── config.py          # 配置管理
│   ├── auth.py            # JWT 认证
│   └── db.py              # 数据库连接
├── alembic/               # 数据库迁移文件
├── tests/                 # 测试文件
├── .env                   # 环境变量配置
├── alembic.ini            # Alembic 配置
└── pyproject.toml         # Python 项目配置
```

## 技术栈

- **Python**: 3.11+
- **Web 框架**: FastAPI 0.105.0
- **ASGI 服务器**: Uvicorn
- **数据库 ORM**: SQLAlchemy 2.0 (异步)
- **数据库迁移**: Alembic
- **认证**: JWT (python-jose)
- **AI 集成**: OpenAI API / Anthropic Claude API
- **数据验证**: Pydantic v2

## 故障排查

### 问题：数据库迁移失败

```bash
# 查看当前迁移版本
alembic current

# 查看迁移历史
alembic history

# 强制标记特定版本（谨慎使用）
alembic stamp head
```

### 问题：端口已被占用

```bash
# 查找占用端口的进程（后端端口固定 7377）
lsof -i :7377
```

后端端口**固定为 7377**（见 `backend/AGENTS.md`：禁止修改后端服务端口）。端口被占用时，
先关闭占用该端口的服务，再重新启动，不要改用其他端口。

### 问题：导入错误

```bash
# 确保已激活虚拟环境
source .venv/bin/activate

# 重新安装依赖
pip install -e .
```

## 贡献

欢迎贡献！请确保：

1. 代码通过所有测试
2. 遵循代码风格规范（Black + Ruff）
3. 为新功能添加测试
4. 更新相关文档

## 许可证

MIT License

### 本地 Ontology 联调环境

若已有隔离联调配置，可在 backend 目录加载后启动（端口保持 7377）：

```sh
set -a
. ./.env.ontology.local
set +a
uv run uvicorn opentask.main:app --host 0.0.0.0 --port 7377
```

`.env.ontology.local` 与 `.smoke/ontology/` 为 git 忽略的本机配置和验收数据，复用已保存密钥与独立数据库；不要覆盖已有数据环境的签名密钥。


### Ontology Issue 状态动作

`update_issue_status` 使用 `object_id` 和 OpenTask 原生 `status` 修改可见 Issue。调用者需同时获得 `read:tasks`、`write:tasks`、`issue:update` 权限以及目标工作区 member/owner 身份；现有令牌不会自动取得新增 scope，须重新授权。动作复用 Issue 更新服务，记录时间线并执行既有业务逻辑。`resolved` 是通用状态 `done` 的默认原生映射；`closed` 同样属于完成状态。

### Ontology 对象集

`query_object_set` 对可见的 Issue、Project、Member 按白名单字段进行 `eq` / `in` 条件组合，支持选择属性、排序、分页和分组计数；每次最多 50 条或 50 组，分组超限返回 `truncated`。Issue 可沿一条关系按可见目标筛选；关系两端分别校验 scope 和可见范围。`describe_object_type` 返回可筛选、排序和分组的字段。`describe_action` 返回状态动作的参数 schema、所需 scope、成员权限和副作用；实际写入仍由 `update_issue_status` 执行。

对象集操作使用现有 PostgreSQL 数据与业务权限，并非 Palantir OSDK 协议兼容实现。分页为 offset，数据变化时跨页不保证快照一致性。
