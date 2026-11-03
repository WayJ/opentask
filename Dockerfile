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
#
# ── 多阶段：构建工具链不进最终镜像 ──────────────────────────────
# 单阶段构建的镜像有 3.4GB——gcc/g++/make 这些**只在构建期需要**的东西被留在了
# 运行层。改为 builder + runtime 两阶段后，镜像约 600MB。40GB 的盘上省下的
# 每一份都要留给数据卷与日志。
#
# 运行阶段只装**动态库**（编译产物在运行期真正需要的那些）+ git + curl：
#   libpq5      → psycopg2 / psycopg
#   libodbc2    → pyodbc
#   libgomp1、libstdc++6 → numpy / pandas / matplotlib 等 C 扩展
#   git         → GitPython（opentask.services.git_knowledge_service 在 import 期
#                 就要 git 可执行文件，缺它后端直接 ImportError 起不来）
#   curl        → 健康检查
#
# DEBIAN_HOST：可换 Debian 镜像源（只换主机名，协议沿用原 URI）。
# 国内机器直连 deb.debian.org 实测仅 ~33KB/s（装完这批依赖要近 2 小时），
# 换 mirrors.aliyun.com 约 650KB/s。发布编排里按目标机所在地覆盖。

# ─────────────────────────────── 构建阶段 ───────────────────────────────
FROM python:3.11-slim AS builder

ARG DEBIAN_HOST=deb.debian.org

RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i \
            -e "s|deb\.debian\.org/debian-security|${DEBIAN_HOST}/debian-security|g" \
            -e "s|deb\.debian\.org/debian|${DEBIAN_HOST}/debian|g" \
            /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i \
            -e "s|deb\.debian\.org/debian-security|${DEBIAN_HOST}/debian-security|g" \
            -e "s|deb\.debian\.org/debian|${DEBIAN_HOST}/debian|g" \
            /etc/apt/sources.list; \
    fi; \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        unixodbc-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

# uv 版本与本仓锁文件格式对齐（uv.lock revision=3；本机工具链 uv 0.12.21）
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /uvx /usr/local/bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# 先只拷依赖清单，让依赖层可缓存（源码变动不触发重装依赖）
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen --no-dev --no-install-project

# 再拷源码
COPY backend/ ./backend/

# ─────────────────────────────── 运行阶段 ───────────────────────────────
FROM python:3.11-slim AS runtime

ARG DEBIAN_HOST=deb.debian.org

RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i \
            -e "s|deb\.debian\.org/debian-security|${DEBIAN_HOST}/debian-security|g" \
            -e "s|deb\.debian\.org/debian|${DEBIAN_HOST}/debian|g" \
            /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i \
            -e "s|deb\.debian\.org/debian-security|${DEBIAN_HOST}/debian-security|g" \
            -e "s|deb\.debian\.org/debian|${DEBIAN_HOST}/debian|g" \
            /etc/apt/sources.list; \
    fi; \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        libodbc2 \
        libgomp1 \
        libstdc++6 \
        git \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# 虚拟环境与源码从构建阶段搬过来（项目自身没装进 venv，靠 CWD 导入）
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/backend /app/backend

WORKDIR /app/backend

EXPOSE 7377

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:7377/openapi.json || exit 1

# 冒烟：把整个 app 导进来——运行期缺的动态库会在这里炸，而不是上线后。
# （AUTH_SECRET_KEY 是 fail-closed 的，此处用一次性占位值，不进镜像层之外的任何地方）
RUN AUTH_SECRET_KEY=build-time-smoke-check \
    POSTGRES_HOST=localhost POSTGRES_USER=opentask POSTGRES_PASSWORD=x POSTGRES_DATABASE=opentask \
    python -c "import opentask.main; print('runtime deps ok')"

# 启动前先跑迁移（alembic baseline 003ccd38d5cd + oauth2 revision c4f8a2b91d6e
# + SSO 列改名 b7e2c9140d3a）
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn opentask.main:app --host 0.0.0.0 --port 7377"]
