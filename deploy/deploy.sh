#!/usr/bin/env bash
#
# OpenTask 发布脚本（在**开发机**执行；服务器侧不需要 git）
#
#   ./deploy/deploy.sh --host root@112.126.60.109
#
# 分工（受目标机 1.6GB 内存 / 2 vCPU 限制）：
#   - 前端产物在开发机上构建：docker 走仓内 frontend/Dockerfile 的 builder 阶段
#     （node:22 + pnpm 9.15.9，与锁文件严格一致），取出 dist 后传到服务器。
#   - 前端镜像在**服务器上原生打包**（frontend/Dockerfile.dist 只有 COPY，
#     几秒完成）。**刻意不在开发机做交叉构建**——本机 docker 没装 buildx，
#     而跨架构构建既需要 buildx 又需要 QEMU 模拟，没有收益。
#   - 后端镜像同样在服务器上原生构建（amd64，无跨架构模拟）。
#
# 幂等：可重复执行。已存在的 .env 不会被覆盖（避免轮换掉线上密钥）。
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST=""
REMOTE_DIR="/opt/opentask"
RELEASE_TAG=""
SKIP_BUILD=0
SKIP_NGINX=0
ADMIN_USER="admin"
ADMIN_PASSWORD=""

usage() {
    cat <<'EOF'
用法: deploy/deploy.sh --host <user@host> [选项]

选项:
  --host <user@host>     目标服务器（必填），需免密 SSH
  --dir <path>           服务器部署目录（默认 /opt/opentask）
  --tag <tag>            版本标签（默认取 git short sha）
  --skip-build           跳过前端构建（复用服务器上已有的 dist）
  --skip-nginx           不动宿主 nginx
  --admin-password <pw>  初始管理员口令（不给则随机生成并打印）
  -h, --help             显示本帮助
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --host) HOST="$2"; shift 2 ;;
        --dir) REMOTE_DIR="$2"; shift 2 ;;
        --tag) RELEASE_TAG="$2"; shift 2 ;;
        --skip-build) SKIP_BUILD=1; shift ;;
        --skip-nginx) SKIP_NGINX=1; shift ;;
        --admin-password) ADMIN_PASSWORD="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "未知参数: $1" >&2; usage; exit 1 ;;
    esac
done

[ -n "$HOST" ] || { echo "缺少 --host" >&2; usage; exit 1; }

if [ -z "$RELEASE_TAG" ]; then
    RELEASE_TAG="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo prod)"
fi

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31m!!! %s\033[0m\n' "$*" >&2; exit 1; }

say "目标: $HOST  目录: $REMOTE_DIR  版本: $RELEASE_TAG"

# ---------------------------------------------------------------- 前端产物
BUILD_CTX="$(mktemp -d)"
trap 'rm -rf "$BUILD_CTX"' EXIT

if [ "$SKIP_BUILD" -eq 0 ]; then
    say "1/5 构建前端产物（仓内 builder 阶段：node:22 + pnpm 9.15.9）"

    # 前置校验：frontend/.env.prod 不在版本库（.gitignore 的 ".env.*" 规则，
    # 仓内只入库 .env.example 模板），必须由构建机的本地文件提供。缺了就早失败，
    # 别等构建出一个前缀错误、线上 404 的产物。
    ENV_FILE="$ROOT/frontend/.env.prod"
    [ -f "$ENV_FILE" ] || die "缺 $ENV_FILE —— 该文件不入库，需先由 frontend/.env.example 复制并填写"
    for kv in "VITE_BASE_URL=/opentask/" "VITE_SERVICE_BASE_URL=/opentask/"; do
        grep -qx "$kv" "$ENV_FILE" \
            || die "$ENV_FILE 里没有 '$kv' —— 路径前缀拓扑要求这两个值（见 deploy/README.md）"
    done

    docker build --target builder -t opentask-fe-builder:"$RELEASE_TAG" "$ROOT/frontend"
    CID="$(docker create opentask-fe-builder:"$RELEASE_TAG")"
    docker cp "$CID:/app/dist" "$BUILD_CTX/dist"
    docker rm "$CID" >/dev/null

    # 产物自检：资源引用必须带 /opentask 前缀（与 .env.prod 的 VITE_BASE_URL 对齐）
    if ! grep -q '/opentask/assets/' "$BUILD_CTX/dist/index.html"; then
        die "dist/index.html 里没有 /opentask/assets/ 引用——VITE_BASE_URL 改动没生效？"
    fi
    say "     产物自检通过（/opentask/assets/ 前缀）"
else
    say "1/5 跳过前端构建（--skip-build）"
fi

cp "$ROOT/frontend/nginx.conf" "$BUILD_CTX/nginx.conf"
cp "$ROOT/frontend/Dockerfile.dist" "$BUILD_CTX/Dockerfile"
tar -C "$BUILD_CTX" -czf "$BUILD_CTX/frontend-dist.tar.gz" dist nginx.conf Dockerfile

# ---------------------------------------------------------------- 送达
say "2/5 同步源码、编排文件与前端产物"
ssh "$HOST" "mkdir -p '$REMOTE_DIR'"
tar -C "$ROOT" \
    --exclude='backend/.venv' \
    --exclude='backend/**/__pycache__' \
    --exclude='backend/.pytest_cache' \
    --exclude='backend/**/.pytest_cache' \
    -czf - backend Dockerfile .dockerignore docker-compose.prod.yml \
    | ssh "$HOST" "tar -C '$REMOTE_DIR' -xzf -"
ssh "$HOST" "mkdir -p '$REMOTE_DIR/data'"
scp -q "$BUILD_CTX/frontend-dist.tar.gz" "$HOST:$REMOTE_DIR/frontend-dist.tar.gz"

# ---------------------------------------------------------------- 服务器起栈
say "3/5 服务器侧：解包前端产物 → 打包前端镜像 → 构建后端镜像 → 起栈"
ssh "$HOST" "bash -s" "$REMOTE_DIR" "$RELEASE_TAG" <<'REMOTE_SCRIPT'
set -euo pipefail
REMOTE_DIR="$1"
RELEASE_TAG="$2"
cd "$REMOTE_DIR"

# --- swap：构建期内存缓冲（机器只有 1.6GB 内存且默认无 swap）---
if [ "$(swapon --show | wc -l)" -eq 0 ]; then
    echo "创建 2G swapfile（构建期缓冲）…"
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "swap 已启用"
else
    echo "swap 已存在，跳过"
fi

# --- 前端产物 → 版本化镜像（原生 amd64，只做 COPY，几秒）---
rm -rf frontend-build && mkdir frontend-build
tar -xzf frontend-dist.tar.gz -C frontend-build
echo "打包前端镜像 opentask-frontend:$RELEASE_TAG …"
docker build -t "opentask-frontend:$RELEASE_TAG" frontend-build
rm -rf frontend-build frontend-dist.tar.gz

# --- 密钥：已存在则不覆盖（避免轮换掉线上 JWT 密钥导致全员掉线）---
if [ ! -f .env ]; then
    gen() { python3 -c 'import secrets;print(secrets.token_hex(32))'; }
    cat > .env <<EOF
# OpenTask 生产密钥（生成于 $(date -u +%Y-%m-%dT%H:%M:%SZ)）
# chmod 600；**不要提交到版本库**；轮换 AUTH_SECRET_KEY 会让所有已签发 JWT 失效
AUTH_SECRET_KEY=$(gen)
POSTGRES_PASSWORD=$(gen)
CIPHER_KEY=$(gen)
PUBLIC_ORIGIN=http://112.126.60.109
RELEASE_TAG=$RELEASE_TAG
EOF
    chmod 600 .env
    echo "已生成 .env（密钥随机生成）"
else
    echo ".env 已存在，保持不变"
fi

export RELEASE_TAG

echo "构建后端镜像（原生 amd64）…"
docker compose -f docker-compose.prod.yml build backend

echo "启动栈…"
docker compose -f docker-compose.prod.yml up -d

echo "等待后端健康…"
for i in $(seq 1 60); do
    if docker compose -f docker-compose.prod.yml exec -T backend \
        curl -fsS http://127.0.0.1:7377/openapi.json >/dev/null 2>&1; then
        echo "后端就绪"
        break
    fi
    sleep 2
done
docker compose -f docker-compose.prod.yml ps
REMOTE_SCRIPT

# 管理员（口令经环境变量传，不进命令行历史）
say "4/5 创建初始管理员"
if [ -n "$ADMIN_PASSWORD" ]; then
    ssh "$HOST" "cd '$REMOTE_DIR' && docker compose -f docker-compose.prod.yml exec -T \
        backend python scripts/create_admin_user.py --username '$ADMIN_USER' --password '$ADMIN_PASSWORD' --reset-password"
else
    ssh "$HOST" "cd '$REMOTE_DIR' && docker compose -f docker-compose.prod.yml exec -T \
        backend python scripts/create_admin_user.py --username '$ADMIN_USER'"
fi

# ---------------------------------------------------------------- 宿主 nginx
if [ "$SKIP_NGINX" -eq 0 ]; then
    say "5/5 宿主 nginx：安装片段 → include → 校验 → reload"
    ssh "$HOST" "bash -s" "$ROOT" <<'REMOTE_SCRIPT'
set -euo pipefail
ROOT="$1"
mkdir -p /etc/nginx/snippets
cp "$ROOT/deploy/nginx/opentask-locations.conf" /etc/nginx/snippets/opentask-locations.conf

SITE=/etc/nginx/sites-available/notegit
if ! grep -q "snippets/opentask-locations.conf" "$SITE"; then
    # 插到 server_name 行之后（该行在本文件内唯一）
    sed -i '/server_name 112\.126\.60\.109;/a\
\
    # OpenTask（路径前缀 /opentask/）——见 deploy/nginx/opentask-locations.conf\
    include /etc/nginx/snippets/opentask-locations.conf;' "$SITE"
    echo "已把 include 插入 $SITE"
else
    echo "include 已存在，跳过"
fi

nginx -t
systemctl reload nginx
echo "nginx 已 reload"
REMOTE_SCRIPT
fi

say "部署完成"
cat <<EOF

访问入口：
  SPA        http://112.126.60.109/opentask/
  后端 API   http://112.126.60.109/opentask/api/
  OAuth2     http://112.126.60.109/oauth2/token
  CLI        opentask --api-url http://112.126.60.109/opentask

EOF
