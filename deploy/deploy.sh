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

# macOS 的 tar 默认把扩展属性打包成 AppleDouble 文件（`._<原名>`），它们是 163 字节的
# 二进制残片、含空字节。alembic 会把 `._env.py` 当迁移脚本加载 → SyntaxError，
# 后端容器起不来。COPYFILE_DISABLE=1 关掉这个行为，--exclude 再兜一层。
export COPYFILE_DISABLE=1

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

# ---------------------------------------------------------------- 送达源码
# 顺序说明：**先**把后端源码送到服务器并起好后端（登录加密的密钥对由后端容器生成，
# 公钥要注入前端构建），**再**构建前端产物。
BUILD_CTX="$(mktemp -d)"
trap 'rm -rf "$BUILD_CTX"' EXIT

say "1/6 同步源码与编排文件到服务器"
ssh "$HOST" "mkdir -p '$REMOTE_DIR'"
tar -C "$ROOT" \
    --exclude='._*' \
    --exclude='backend/.venv' \
    --exclude='backend/**/__pycache__' \
    --exclude='backend/.pytest_cache' \
    --exclude='backend/**/.pytest_cache' \
    --exclude='backend/config/local.yaml' \
    -czf - backend Dockerfile .dockerignore docker-compose.prod.yml \
    | ssh "$HOST" "tar -C '$REMOTE_DIR' -xzf -"
# 清掉历史遗留的 AppleDouble 残片（首轮发布带过去过 485 个）
ssh "$HOST" "find '$REMOTE_DIR' -name '._*' -delete; rm -f '$REMOTE_DIR/backend/config/local.yaml'"
ssh "$HOST" "mkdir -p '$REMOTE_DIR/data'"

# ---------------------------------------------------------------- 登录加密密钥对
say "2/6 服务器侧：构建后端镜像 → 起后端 → 生成登录加密密钥对 → 取回公钥"
LOGIN_PUBKEY=""
if [ "$SKIP_BUILD" -eq 0 ]; then
    LOGIN_PUBKEY="$(ssh "$HOST" "bash -s" "$REMOTE_DIR" "$RELEASE_TAG" <<'REMOTE_SCRIPT'
set -euo pipefail
REMOTE_DIR="$1"
RELEASE_TAG="$2"
cd "$REMOTE_DIR"
export RELEASE_TAG

# --- swap：构建期内存缓冲（机器只有 1.6GB 内存且默认无 swap）---
if [ "$(swapon --show | wc -l)" -eq 0 ]; then
    echo "创建 2G swapfile（构建期缓冲）…" >&2
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

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
    echo "已生成 .env（密钥随机生成）" >&2
fi

echo "构建后端镜像（原生 amd64）…" >&2
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d postgres backend

echo "等待后端健康…" >&2
READY=0
for i in $(seq 1 60); do
    if docker compose -f docker-compose.prod.yml exec -T backend \
        curl -fsS http://127.0.0.1:7377/openapi.json >/dev/null 2>&1; then
        READY=1
        break
    fi
    STATE="$(docker inspect -f '{{.State.Status}}' opentask-backend 2>/dev/null || echo unknown)"
    if [ "$STATE" = "restarting" ] || [ "$STATE" = "exited" ] || [ "$STATE" = "dead" ]; then
        echo "后端容器状态异常：$STATE —— 日志如下" >&2
        docker compose -f docker-compose.prod.yml logs --tail 60 backend >&2
        exit 1
    fi
    sleep 2
done
[ "$READY" = "1" ] || { echo "等待后端健康超时" >&2; docker compose -f docker-compose.prod.yml logs --tail 60 backend >&2; exit 1; }

# --- 登录口令加密的密钥对（私钥留在 data 卷，公钥给前端构建用）---
docker compose -f docker-compose.prod.yml exec -T backend \
    python scripts/generate_login_keys.py >/dev/null
docker compose -f docker-compose.prod.yml exec -T backend \
    python scripts/generate_login_keys.py --print-public
REMOTE_SCRIPT
)"
    # 只留 base64 行——防止任何日志/提示混进公钥里
    LOGIN_PUBKEY="$(printf '%s' "$LOGIN_PUBKEY" | tr -d '\r' | grep -E '^[A-Za-z0-9+/=]+$' | tail -1)"
    [ -n "$LOGIN_PUBKEY" ] || die "没拿到登录加密公钥（服务器侧输出异常）"
    say "     登录加密公钥已就绪（${#LOGIN_PUBKEY} 字节 base64）"
fi

# ---------------------------------------------------------------- 前端产物
if [ "$SKIP_BUILD" -eq 0 ]; then
    say "3/6 构建前端产物（仓内 builder 阶段：node:22 + pnpm 9.15.9）"

    # 前置校验：frontend/.env.prod 不在版本库（.gitignore 的 ".env.*" 规则，
    # 仓内只入库 .env.example 模板），必须由构建机的本地文件提供。缺了就早失败，
    # 别等构建出一个前缀错误、线上 404 的产物。
    ENV_FILE="$ROOT/frontend/.env.prod"
    [ -f "$ENV_FILE" ] || die "缺 $ENV_FILE —— 该文件不入库，需先由 frontend/.env.example 复制并填写"
    for kv in "VITE_BASE_URL=/" "VITE_SERVICE_BASE_URL=/"; do
        grep -qx "$kv" "$ENV_FILE" \
            || die "$ENV_FILE 里没有 '$kv' —— 根路径部署要求这两个值（见 deploy/README.md）"
    done

    docker build --target builder \
        --build-arg "VITE_LOGIN_PUBLIC_KEY=$LOGIN_PUBKEY" \
        -t opentask-fe-builder:"$RELEASE_TAG" "$ROOT/frontend"
    CID="$(docker create opentask-fe-builder:"$RELEASE_TAG")"
    docker cp "$CID:/app/dist" "$BUILD_CTX/dist"
    docker rm "$CID" >/dev/null

    # 产物自检：资源在站点根，不能再带 /opentask/assets/
    if ! grep -q '/assets/' "$BUILD_CTX/dist/index.html"; then
        die "dist/index.html 里没有 /assets/ 引用——前端构建没有产出可运行的页面"
    fi
    if grep -q '/opentask/assets/' "$BUILD_CTX/dist/index.html"; then
        die "dist/index.html 仍引用 /opentask/assets/ —— VITE_BASE_URL 应是 /"
    fi
    say "     产物自检通过（/assets/，无 /opentask 前缀）"

    cp "$ROOT/frontend/nginx.conf" "$BUILD_CTX/nginx.conf"
    cp "$ROOT/frontend/Dockerfile.dist" "$BUILD_CTX/Dockerfile"
    tar -C "$BUILD_CTX" --exclude='._*' -czf "$BUILD_CTX/frontend-dist.tar.gz" dist nginx.conf Dockerfile
else
    say "3/6 跳过前端构建（--skip-build）：复用服务器上已有的前端镜像"
fi

if [ "$SKIP_BUILD" -eq 0 ]; then
    scp -q "$BUILD_CTX/frontend-dist.tar.gz" "$HOST:$REMOTE_DIR/frontend-dist.tar.gz"
fi

# ---------------------------------------------------------------- 服务器起栈
say "4/6 服务器侧：打包前端镜像 → 全栈起停 → 状态确认"
ssh "$HOST" "bash -s" "$REMOTE_DIR" "$RELEASE_TAG" "$SKIP_BUILD" <<'REMOTE_SCRIPT'
set -euo pipefail
REMOTE_DIR="$1"
RELEASE_TAG="$2"
SKIP_BUILD="$3"
cd "$REMOTE_DIR"
export RELEASE_TAG

# --- 前端产物 → 版本化镜像（原生 amd64，只做 COPY，几秒）---
if [ "$SKIP_BUILD" -eq 0 ]; then
    rm -rf frontend-build && mkdir frontend-build
    tar -xzf frontend-dist.tar.gz -C frontend-build
    echo "打包前端镜像 opentask-frontend:$RELEASE_TAG …"
    docker build -t "opentask-frontend:$RELEASE_TAG" frontend-build
    rm -rf frontend-build frontend-dist.tar.gz
else
    echo "跳过前端镜像打包（--skip-build），沿用服务器上已有的镜像"
    EXISTING="$(docker images --format '{{.Repository}}:{{.Tag}}' | grep '^opentask-frontend:' | head -1)"
    [ -n "$EXISTING" ] || { echo "服务器上没有任何 opentask-frontend 镜像，无法跳过构建" >&2; exit 1; }
    echo "沿用 $EXISTING（重打标签为 opentask-frontend:$RELEASE_TAG）"
    docker tag "$EXISTING" "opentask-frontend:$RELEASE_TAG"
fi

echo "启动全栈…"
docker compose -f docker-compose.prod.yml up -d

echo "等待后端健康…"
READY=0
for i in $(seq 1 60); do
    if docker compose -f docker-compose.prod.yml exec -T backend \
        curl -fsS http://127.0.0.1:7377/openapi.json >/dev/null 2>&1; then
        READY=1
        break
    fi
    STATE="$(docker inspect -f '{{.State.Status}}' opentask-backend 2>/dev/null || echo unknown)"
    if [ "$STATE" = "restarting" ] || [ "$STATE" = "exited" ] || [ "$STATE" = "dead" ]; then
        echo "后端容器状态异常：$STATE —— 日志如下" >&2
        docker compose -f docker-compose.prod.yml logs --tail 60 backend >&2
        exit 1
    fi
    sleep 2
done
[ "$READY" = "1" ] || { echo "等待后端健康超时" >&2; docker compose -f docker-compose.prod.yml logs --tail 60 backend >&2; exit 1; }

docker compose -f docker-compose.prod.yml ps
REMOTE_SCRIPT

# 管理员（口令经环境变量传，不进命令行历史）
say "5/6 创建初始管理员"
if [ -n "$ADMIN_PASSWORD" ]; then
    ssh "$HOST" "cd '$REMOTE_DIR' && docker compose -f docker-compose.prod.yml exec -T \
        backend python scripts/create_admin_user.py --username '$ADMIN_USER' --password '$ADMIN_PASSWORD'"
else
    ssh "$HOST" "cd '$REMOTE_DIR' && docker compose -f docker-compose.prod.yml exec -T \
        backend python scripts/create_admin_user.py --username '$ADMIN_USER'"
fi

# ---------------------------------------------------------------- 宿主 nginx
if [ "$SKIP_NGINX" -eq 0 ]; then
    say "6/6 宿主 nginx：安装独立 OpenTask 站点 → 校验 → reload"
    # 不改写其它 vhost。若目标机上已有 server 占用 location /，nginx -t 或实际访问会失败，需要操作者先处理。
    scp -q "$ROOT/deploy/nginx/opentask-locations.conf" "$HOST:/tmp/opentask-locations.conf"
    scp -q "$ROOT/deploy/nginx/opentask-site.conf" "$HOST:/tmp/opentask-site.conf"
    ssh "$HOST" "bash -s" <<'REMOTE_SCRIPT'
set -euo pipefail
mkdir -p /etc/nginx/snippets /etc/nginx/sites-available /etc/nginx/sites-enabled
cp /tmp/opentask-locations.conf /etc/nginx/snippets/opentask-locations.conf
cp /tmp/opentask-site.conf /etc/nginx/sites-available/opentask
rm -f /tmp/opentask-locations.conf /tmp/opentask-site.conf
ln -sfn /etc/nginx/sites-available/opentask /etc/nginx/sites-enabled/opentask
nginx -t
systemctl reload nginx
echo "nginx 已 reload（独立站点 sites-available/opentask）"
REMOTE_SCRIPT
fi

say "部署完成"
cat <<EOF

访问入口：
  SPA        http://<host>/
  登录       http://<host>/login
  后端 API   http://<host>/api/
  OAuth2     http://<host>/oauth2/token
  CLI        opentask --api-url http://<host>

EOF
