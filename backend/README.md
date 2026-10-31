# OpenTask Backend

基于 FastAPI 的 OpenTask 后端服务，提供需求管理、项目追踪、AI 集成等核心功能。

## 目录

- [安装](#安装)
- [环境配置](#环境配置)
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
