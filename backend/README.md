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

- **Swagger UI**: http://localhost:3000/docs
- **ReDoc**: http://localhost:3000/redoc
- **OpenAPI Schema**: http://localhost:3000/openapi.json

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

**401 语义独立**：缺凭证/凭证无效（错误、过期、吊销、用户禁用）一律返回 `401`，错误体带可辨识错误码字段（区别于 403/503）：

```json
{"detail": {"code": "CONTRACT_AUTH_MISSING|CONTRACT_AUTH_INVALID", "message": "..."}}
```

`POST /tasks/token` 的凭证错误同为 401；不支持的 `grant_type` 返回 400（`CONTRACT_AUTH_UNSUPPORTED_GRANT`）。

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
  default_issue_type: feature
```

- 配置在 `default.yaml` 集中维护，环境配置（development/production/test.yaml）可按键深合并覆盖；**修改后重启进程生效**。
- `GET /capabilities` 的 `status_vocabulary` 与 `features.status_mapping_source`（`config`/`default`）实时反映生效配置，消费方可据此自适应。
- 往返保证：`generic → IssueStatus → generic` 对生效词表全部状态恒等（`resolved`/`closed` 同归 `done` 时逆取 `resolved`）。

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
# 查找占用端口的进程
lsof -i :3000

# 或使用其他端口
python -m uvicorn opentask.main:app --reload --port 3001
```

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
