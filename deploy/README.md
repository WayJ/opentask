# OpenTask 发布环境

目标机：`112.126.60.109`（Ubuntu 24.04 / 2 vCPU / 1.6GB 内存 / 40G 盘 / Docker 29.8.1 + Compose v5.5.1）

> ⚠️ **当前形态是明文 HTTP 的过渡态，别当生产终态。**
> 前端登录**明文传输口令**（`frontend/src/service/api/auth.ts`：「密码明文传输，依赖
> HTTPS」），后端在 SSO 关闭时按明文比对 bcrypt。因此在接入 TLS 之前，
> **登录口令与 JWT 都在链路上裸奔**。下一步必做：阿里云 DNS 加 A 记录
> `opentask.recluse.fun → 112.126.60.109`，然后 `certbot --nginx -d opentask.recluse.fun`。

---

## 1. 拓扑

主示例是独立的 OpenTask 站点（`deploy/nginx/opentask-site.conf`）。仓库没有登录过目标机器，下面不是对某台现网机器的检查结果。

```
浏览器 ──http──▶ 宿主 nginx :80（独立 OpenTask server）
                   ├─ /                     ─▶ 127.0.0.1:8080  前端容器
                   │     容器内：/assets/* 静态，/api/ 与 /ws/workspace 原样转 7377，其余 index.html
                   ├─ /api/  /ws/workspace  ─▶ 127.0.0.1:7377
                   ├─ /oauth2/authorize     ─▶ 127.0.0.1:8080  SPA 同意页
                   ├─ /oauth2/              ─▶ 127.0.0.1:7377  token / userinfo / revoke / register
                   ├─ /mcp、/.well-known/oauth-* ─▶ 127.0.0.1:7377  MCP 与授权发现
                   ├─ /tasks/ /capabilities /healthcheck ─▶ 127.0.0.1:7377

docker compose（目录 /opt/opentask）
  ├─ postgres    postgres:15-alpine
  ├─ backend     127.0.0.1:7377
  └─ frontend    127.0.0.1:8080
```

若操作者的 nginx 里已经有别的 `location /`，要先处理那一条，否则 `/login` 到不了 OpenTask。这只是条件说明，不表示某台机器上正在跑其它服务。

**为什么容器端口只绑回环**：公网机上数据库与后端绝不能裸奔在全网卡。仓库根的
`docker-compose.yml`（本地开发编排）用的是 `7377:7377`（即 0.0.0.0 绑定），生产编排
`docker-compose.prod.yml` 一律改成 `127.0.0.1:` 前缀，外部只经宿主 nginx 进入。

### 路径语义

| 路径 | 归属 | 说明 |
|---|---|---|
| `/`、`/login`、`/issue/list`、`/f/:token`、`/r/:token` | 前端 SPA | history 基址 `/`，刷新回 index.html |
| `/api/*`、`/ws/workspace` | 后端 | 不剥前缀，不设置 `X-Workspace-Id`。`/ws/hub*` 不转发 |
| `=/oauth2/authorize` | 前端 SPA | 授权同意页 |
| `/oauth2/*` | 后端 | token、userinfo、revoke、动态注册 |
| `/mcp`、`/.well-known/oauth-*` | 后端 | MCP 工具与标准授权元数据 |
| `/tasks/*`、`/capabilities`、`/healthcheck` | 后端 | 原先已暴露的协议与探活 |

**刻意不外露**的后端顶层路径：`/test/*`（后端自测端点，公开机无需暴露）、
`/openapi.json`、`/docs`（OpenAPI 文档）。它们只能从服务器本机
`http://127.0.0.1:7377/...` 访问。

**撞车检查**（决定了上面的路径切分）：后端顶层段有
`capabilities / healthcheck / oauth2 / tasks / test`，前端 SPA 顶层路由有
`/oauth2`（授权同意页）等 17 个——**只有 `oauth2` 重名**，所以授权服务器的端点
必须与 SPA 的路径前缀分离。其余顶层段无冲突。

授权同意页是 SPA 路由 `/oauth2/authorize`，token 端点是 `/oauth2/token`。宿主用精确匹配把同意页送到前端容器，其余 `/oauth2/` 送到后端。MCP 资源 `/mcp` 与标准发现 `/.well-known/oauth-*` 均转发后端。HTTP 接入为明文兼容模式。 动态注册支持公共客户端与保密客户端；成员仍需本人登录并同意授权，公共客户端须使用 PKCE S256。

---

## 2. 首次部署

前置：开发机能免密 SSH 到目标机（`ssh root@112.126.60.109`）。

```bash
./deploy/deploy.sh --host root@112.126.60.109
```

脚本会依次完成：

1. **构建前端产物**——走仓内 `frontend/Dockerfile` 的 builder 阶段（node:22 + pnpm 9.15.9，
   与 `pnpm-lock.yaml` 严格一致），产物自检 `index.html` 含 `/assets/` 且不含 `/opentask/assets/`；
2. **送达**——后端源码（排除 `.venv`）+ `docker-compose.prod.yml` + `Dockerfile` + `.dockerignore`
   + 前端产物 tarball；
3. **服务器侧**——开 2G swap（构建期内存缓冲）→ 用 `frontend/Dockerfile.dist` 把 dist 打包成
   版本化镜像 `opentask-frontend:<tag>`（原生 amd64，只做 COPY）→ 生成 `.env` 密钥 →
   原生构建后端镜像 → 起栈 → 等后端健康；
4. **建初始管理员**——`backend/scripts/create_admin_user.py`（幂等；口令随机生成并打印一次）；
5. **宿主 nginx**——装 `/etc/nginx/snippets/opentask-locations.conf`，把 `include` 插进既有
   `server_name 112.126.60.109` 站点块，`nginx -t` 通过后 reload。

### 登录口令的传输加密

部署形态是**明文 HTTP**（没有域名就签不了 HTTPS 证书），所以口令**不能**明文提交。
当前做法：**RSA-OAEP 非对称加密**。

```
前端（SPA）                          服务端
  ├─ 公钥 VITE_LOGIN_PUBLIC_KEY  ──→  /opt/opentask/data/login_public.pem（可公开）
  └─ 用公钥加密口令 → base64 密文  ──→  /opt/opentask/data/login_private.pem（600，私钥）
                                     后端用私钥解密 → 比对 bcrypt
```

| 项 | 说明 |
|---|---|
| 算法 | RSA-OAEP / SHA-256（MGF1-SHA256），2048 位 |
| 公钥 | 打进前端 bundle（`VITE_LOGIN_PUBLIC_KEY`，base64 的 SPKI DER），由 `deploy.sh` 从服务器取回后以构建参数注入 |
| 私钥 | 只在服务器：`/opt/opentask/data/login_private.pem`（chmod 600，随 data 卷持久化），**不进镜像** |
| 参数一致性 | 前端用 node-forge（纯 JS——`crypto.subtle` 只在安全上下文可用，明文 HTTP 页面拿不到），后端用 cryptography；两边 OAEP 参数已实测互通 |
| 兼容性 | 没配置公钥时前端发明文，后端解不开时回退按明文处理 → CLI 等未接入加密的客户端照常工作 |

**轮换**（怀疑私钥泄露时）：

```bash
cd /opt/opentask
docker compose -f docker-compose.prod.yml exec backend     python scripts/generate_login_keys.py --force
# ⚠ 换公钥后必须**重新构建前端**（VITE_LOGIN_PUBLIC_KEY 变了），否则新前端登录解不开
./deploy/deploy.sh --host root@112.126.60.109
```

**这套机制防什么、不防什么**：

| | |
|---|---|
| ✅ 防 | 被动抓包（代理日志、共享网络嗅探）——密文没有私钥解不开 |
| ⚠️ 不防 | **主动中间人**：HTTP 下前端 bundle 与公钥都可被替换，攻击者能换掉公钥再收明文 |
| ⚠️ 不防 | **JWT 仍是明文**：access token 在 Authorization 头里传输，抓包可劫持会话 |

→ 完整的保护仍需 TLS（加 A 记录后 `certbot --nginx` 即可）。

### 密钥

服务器 `/opt/opentask/.env`（`chmod 600`，不入版本库）：

| 变量 | 用途 | 缺失后果 |
|---|---|---|
| `AUTH_SECRET_KEY` | JWT 签名密钥 | 后端 **fail-closed 拒启动** |
| `POSTGRES_PASSWORD` | 数据库口令 | compose 变量插值失败，拒启动 |
| `CIPHER_KEY` | 口令加密密钥 | compose 变量插值失败，拒启动 |
| `PUBLIC_ORIGIN` | CORS 允许来源 | 默认 `http://112.126.60.109` |
| `RELEASE_TAG` | 镜像标签 | 默认 `prod` |

> 轮换 `AUTH_SECRET_KEY` 会让所有已签发 JWT 立即失效（全员掉线）。`deploy.sh` 检测到 `.env`
> 已存在就**不覆盖**，避免误轮换。

### 初始管理员

全新库没有账号。发布脚本会创建第一个管理员；该用户还没有可用工作区时再创建一个，默认名 OpenTask。重复执行不重置口令，也不重复成员。产品注册接口 `POST /api/auth/register` 会给新用户创建工作区。部署脚本示例：

```bash
cd /opt/opentask
docker compose -f docker-compose.prod.yml exec backend \
    python scripts/create_admin_user.py --username admin
```

- 幂等：账号已存在默认跳过；`--reset-password` 才重置口令；
- 会先跑一遍用户中心播种（幂等），确保 `role` 表里有 `admin` 系统角色，再把用户显式挂到
  `user_role`——不依赖 `user.role` 字符串桥接那条过渡路径；
- 口令只存 bcrypt 哈希，库里无明文。

---

## 3. 日常发布

```bash
# 改完代码后
git pull                                   # 或本地改完再推
./deploy/deploy.sh --host root@112.126.60.109
```

脚本幂等：`.env` 不动、数据卷不动、数据库不重建。

回滚：把 `RELEASE_TAG` 换回上一个 tag 重新 `docker compose up -d` 即可（镜像都留在本地）。

---

## 4. 运维手册

```bash
cd /opt/opentask
C="docker compose -f docker-compose.prod.yml"

$C ps                      # 容器状态
$C logs -f backend         # 后端日志
$C logs -f frontend        # 前端 nginx 日志
$C restart backend         # 重启后端
$C down                    # 停栈（数据卷保留）
$C up -d                   # 起栈
```

**备份**（生产库）：

```bash
docker exec opentask-postgres pg_dump -U opentask opentask | gzip > /opt/opentask/backup-$(date +%F).sql.gz
```

**升级数据库**：后端容器启动时自动 `alembic upgrade head`（见根 `Dockerfile` 的 CMD），
无需手工迁移。

**磁盘**：40G 盘，镜像 + 数据 + 日志。当前 `docker system df` 可查；日志已限制
（backend 20M×5，其余 10M×3）。

---

## 5. 已知约束

| 约束 | 影响 | 处置 |
|---|---|---|
| **无 TLS** | 全程明文 HTTP，JWT 与口令在链路上裸奔 | 当前是路径前缀形态的过渡部署。切域名时：加 A 记录 `opentask.recluse.fun → 112.126.60.109`，然后 `certbot --nginx -d opentask.recluse.fun` |
| **DNS 未生效** | `opentag.recluse.fun` 在公网已是 NXDOMAIN，`recluse.fun` 托管在阿里云 DNS，但机器上无 DNS 凭据，无法代加记录 | 需人工在阿里云 DNS 加 A 记录 |
| **内存 1.6GB** | 服务器跑不动 vite 构建 | 前端产物在开发机构建；服务器只做 COPY 打包 |
| **已有别的 location /** | 根路径会被那条规则接走 | 主示例是独立站点。只有操作者的配置里确实已有 `location /` 时才需要先改。本文没有检查过现网机器 |
| **AI 能力未接** | `OPENAI_API_KEY` 未配置，AI 相关功能不可用 | 有 key 后写进 `.env` 再 `docker compose up -d backend` |
| **SSO 单点登录关闭** | `AUTH_SSO_ENABLED=false`：上游用户中心在内网，公网机不可达 | 生产走本地账号登录。将来若要启用：把上游地址写进 `.env` 的 `SSO_BASE_URL`（仓内配置只留 `${SSO_BASE_URL:}` 占位，具体地址不进版本库），并置 `AUTH_SSO_ENABLED=true` |

### 网络实测（2026-11-03，目标机）

发布前先量过各源站速度，避免"卡住但不知道为什么"：

| 源站 | 实测速度 | 说明 |
|---|---|---|
| `deb.debian.org` | **33 KB/s** | 直连极慢，装完构建依赖接近 2 小时 |
| `mirrors.aliyun.com` | **650 KB/s** | 后端镜像的 `DEBIAN_HOST` 默认走它 |
| `pypi.org` | 76 KB/s | 用不上——`uv.lock` 锁的本来就是清华镜像 |
| `pypi.tuna.tsinghua.edu.cn` | 索引页 38KB / 0.04s | `uv.lock` 里 300 个包全部指向它 |

> PyPI 侧**不需要**额外配镜像：uv 不读 `pip.conf`（机器上的 `/etc/pip.conf` 指向
> `mirrors.cloud.aliyuncs.com` 对 uv 无效），但 `uv.lock` 本身就锁在清华镜像上，
> `uv sync --frozen` 会按锁文件的 URL 取包。


---

## 6. 验收清单

```bash
# 对已部署的独立站点。不要把口令写进仓库或命令历史。
curl -sI http://<host>/login
curl -s  http://<host>/ | grep -o '/assets/[^\"]*' | head -3
curl -sI http://<host>/issue/list
curl -sI http://<host>/oauth2/token
```
