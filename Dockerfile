# OpenTask 后端镜像（Python 3.11 + uv）
#
# 取代此前的 Node+Prisma 模板（那是改名前的残留，与本仓 Python 栈完全不符）。
# 构建上下文为**仓库根目录**（compose 中 context: .），因此前端源码不会进入本镜像。
#
#   docker build -f Dockerfile -t opentask-backend .
#
# 运行时必需环境变量（fail-closed，缺一即拒启动）：
#   AUTH_SECRET_KEY     JWT 签名密钥（config.py 显式禁止默认值）
#   POSTGRES_HOST / POSTGRES_PORT / POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DATABASE
#
# 服务端口固定 7377（见 backend/AGENTS.md：禁止修改后端端口）。

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# 构建期系统依赖：
#   build-essential + libpq-dev  → psycopg[pool]（源码分发）
#   unixodbc-dev                 → pyodbc
#   git                          → GitPython（opentask.services.git_knowledge_service 在 import 期就要 git 可执行文件，
#                                  缺它后端直接 ImportError 起不来）
#   curl                         → 健康检查
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        unixodbc-dev \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# uv 版本与本仓锁文件格式对齐（uv.lock revision=3；本机工具链 uv 0.12.21）
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /uvx /usr/local/bin/

WORKDIR /app

# 先只拷依赖清单，让依赖层可缓存（源码变动不触发重装依赖）
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen --no-dev --no-install-project

# 再拷源码
COPY backend/ ./backend/

WORKDIR /app/backend

EXPOSE 7377

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:7377/openapi.json || exit 1

# 启动前先跑迁移（alembic baseline 003ccd38d5cd + oauth2 revision c4f8a2b91d6e）
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn opentask.main:app --host 0.0.0.0 --port 7377"]
