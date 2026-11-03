# OpenTask 前端镜像（构建期 pnpm/vite → 运行期 nginx 静态托管 + API 反代）
#
#   docker build -f frontend/Dockerfile -t opentask-frontend frontend
#
# 构建上下文为 frontend/ 目录（compose 中 context: ./frontend）。
# 运行期 nginx 同时承担两件事（见 frontend/nginx.conf）：
#   1. 托管 vite 产出的静态资源（SPA history fallback）
#   2. 把 /opentask/ 前缀的请求反代到后端 7377 —— 这正是生产部署侧
#      「nginx location /opentask/」应有的形态（E1-Q1），仓内此文件可作为运维参考。

FROM node:22-alpine AS builder

WORKDIR /app

# pnpm 版本与 pnpm-lock.yaml 的 lockfileVersion 9.0 对应
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

# 先拷依赖清单以复用缓存
COPY package.json pnpm-lock.yaml .npmrc ./
COPY packages/ ./packages/
RUN pnpm install --frozen-lockfile

COPY . .

# vite build --mode prod（前端 .env.prod 已在仓内，VITE_SERVICE_BASE_URL=/opentask/）
RUN pnpm build


FROM nginx:1.27-alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
