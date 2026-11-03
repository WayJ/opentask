# OpenTask 前端镜像（构建期 pnpm/vite → 运行期 nginx 静态托管 + API 反代）
#
#   docker build -f frontend/Dockerfile -t opentask-frontend frontend
#
# 构建上下文为 frontend/ 目录（compose 中 context: ./frontend）。
# 运行期 nginx 同时承担两件事（见 frontend/nginx.conf）：
#   1. 托管 vite 产出的静态资源（SPA history fallback）
#   2. 把 /opentask/api/ 前缀的请求反代到后端 7377 —— 这正是生产部署侧
#      「nginx location /opentask/」应有的形态（E1-Q1），仓内此文件可作为运维参考。
#
# 产物落位：/usr/share/nginx/html/opentask/ —— 与 URL 前缀 /opentask/ 一一对应，
# 使容器内 try_files 直接命中真实路径（无需 rewrite / alias）。

FROM node:22-alpine AS builder

WORKDIR /app

# pnpm 版本与 pnpm-lock.yaml 的 lockfileVersion 9.0 对应
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

# 先拷依赖清单以复用缓存
COPY package.json pnpm-lock.yaml .npmrc ./
COPY packages/ ./packages/
RUN pnpm install --frozen-lockfile

COPY . .

# 生产构建的两个路径前缀。
#
# 注意：.env.prod **不在版本库里**（.gitignore 的 ".env.*" 规则——仓内只入库
# .env.example 模板），它由构建机的本地文件提供。这里用 ARG 把前缀固化为
# 构建参数：Vite 里 process.env 的优先级高于 .env 文件，故这两个值一定会生效，
# 产物的前缀不因构建机的 .env.prod 内容漂移。
#
# 其余 VITE_* 配置（路由模式、成功码、存储前缀等）仍依赖构建机的 frontend/.env.prod；
# 缺失时构建会得到不可用的产物 —— deploy/deploy.sh 有前置校验会拦下。
ARG VITE_BASE_URL=/opentask/
ARG VITE_SERVICE_BASE_URL=/opentask/
ENV VITE_BASE_URL=${VITE_BASE_URL}
ENV VITE_SERVICE_BASE_URL=${VITE_SERVICE_BASE_URL}

# 登录口令传输加密用的**服务端公钥**（SPKI DER 的 base64）。
# 私钥只在服务器（<DATA_DIRECTORY>/login_private.pem），公钥打进 bundle 后前端用它
# 做 RSA-OAEP 加密——这样链路是明文 HTTP 时，抓包拿到的也只是解不开的密文。
# 由 deploy/deploy.sh 从服务器取回后以 --build-arg 传入；为空则登录走明文。
ARG VITE_LOGIN_PUBLIC_KEY=
ENV VITE_LOGIN_PUBLIC_KEY=${VITE_LOGIN_PUBLIC_KEY}

# vite build --mode prod
RUN pnpm build


FROM nginx:1.27-alpine AS runtime

# 删掉基础镜像自带的默认首页（避免与 /opentask/ 下的应用首页混淆）
RUN rm -f /usr/share/nginx/html/index.html /usr/share/nginx/html/50x.html

COPY --from=builder /app/dist /usr/share/nginx/html/opentask
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/opentask/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
