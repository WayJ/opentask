# 发布环境落地笔记 — 2026-11-03

目标机：`112.126.60.109`（Ubuntu 24.04 / 2 vCPU / 1.6GB 内存 / 40G 盘 / Docker 29.8.1 + Compose v5.5.1）

## 背景

E1/E2 两个 epic 关闭后，仓内遗留的 TD3（Docker 栈重写）虽已销账，但**从未真正部署过**——
仓里的 `Dockerfile` / `docker-compose.yml` / `frontend/nginx.conf` 是「能构建」的产物，
不是「在真机上跑通」的产物。本次把发布环境建起来，并把 E1-Q1（生产 nginx 必须同步
`/opentask/` 前缀）这条悬了很久的运维欠账一并结清。

## 关键决策（用户 2026-11-03 拍板）

| 项 | 决定 | 理由 |
|---|---|---|
| 访问入口 | 挂在既有 IP:80 站点的**路径前缀 `/opentask/`** 下 | 该机无 DNS 凭据，无法代加 A 记录；`recluse.fun` 托管在阿里云 DNS 但 `opentag.recluse.fun` 已是 NXDOMAIN |
| 构建分工 | 前端在**开发机**构建、后端在**服务器**构建 | 服务器 1.6GB 内存无 swap，vite 是内存大户；后端在服务器原生构建免跨架构 |
| 生产数据 | **全新空库** | 内网 MySQL（10.1.1.221）从公网机不可达，且 MySQL→PG 转换面大 |

## 拓扑与路径切分

```
浏览器 → 宿主 nginx :80 (server_name 112.126.60.109)
  ├─ /opentask/*      → 127.0.0.1:8080 前端容器（容器内再分流）
  │                     /opentask/assets/* → 静态
  │                     /opentask/api/*    → 后端 7377
  │                     /opentask/<路由>   → index.html
  ├─ /oauth2/*        → 127.0.0.1:7377  OAuth2 Provider
  ├─ /tasks/*、/capabilities、/healthcheck → 127.0.0.1:7377
  └─ /                → 127.0.0.1:3000  notegit（既有站点，未动）
```

**OAuth2 端点为何必须与 SPA 前缀分离**（撞车检查的结论）：后端顶层段有
`capabilities/healthcheck/oauth2/tasks/test`，前端 SPA 顶层路由有 17 个，**只有 `oauth2`
重名**——前端同意页是 SPA 路由 `/opentask/oauth2/authorize`，授权服务器端点是
`/oauth2/token`。同前缀无法区分二者，故授权服务器的 issuer 放在站点根。

**静态产物落 `html/opentask/` 子目录**：与 URL 前缀一一对应 → `try_files` 直接命中，
免 `rewrite`、免 `alias`（`alias` + `try_files` 的路径拼接是经典坑）。

## 踩坑

1. **国内机器直连 Debian 官方源 33KB/s**（阿里云 ECS 实测）——首轮发布卡在
   `apt-get install` 近 2 小时。改 `Dockerfile` 加 `ARG DEBIAN_HOST`，
   生产编排默认走 `mirrors.aliyun.com`（650KB/s，20 倍）。
   PyPI 侧不用动：`uv.lock` 本身就锁在清华镜像（300 个包全部指向 tuna）。
2. **本机 docker 没装 buildx**，BuildKit 也不可用（`docker build --platform linux/amd64`
   被忽略，产物仍是 arm64）。因此**放弃交叉构建**，改为：开发机出 `dist` → 传服务器 →
   服务器用 `frontend/Dockerfile.dist`（只有 COPY）原生打包成版本化镜像。
3. **`frontend/.env.prod` 从未入库**（`.gitignore` 的 `.env.*` 规则），但 Dockerfile 旧注释
   称「已在仓内」——事实不符。已缓解（Dockerfile 增 `ARG/ENV` 固化前缀 +
   `deploy.sh` 前置校验拦下缺文件/错前缀），根因登记为 **TD9** 待用户裁定是否入库。
4. **仓库在本次会话期间被另一会话并发提交**（`afe784e` 偿清 TD3/TD7/TD8、`ae010dd` TD6 销账）。
   `frontend/nginx.conf` 在我读取后被改写，带入两条我没写过的经验——**照单全收**：
   ① nginx 静态主机名只在启动时解析，后端容器重建换 IP 会让前端永久 502，
   故用 Docker 内嵌 DNS（127.0.0.11）逐请求解析；
   ② 前缀剥选用 `rewrite ... break` + 不带 URI 的 `proxy_pass`（带变量时 URI 替换语义会变）。

## 产出

- `docker-compose.prod.yml` —— 生产编排（端口一律绑回环，fail-closed 密钥，日志轮转）
- `deploy/deploy.sh` —— 幂等发布脚本（产物构建 → 送达 → 服务器打包/构建/起栈 → 建管理员 → 装 nginx）
- `deploy/nginx/opentask-locations.conf` —— 宿主 nginx location 片段
- `deploy/README.md` —— 拓扑、路径语义、发布流程、运维手册、网络实测、验收清单
- `frontend/Dockerfile.dist` —— 预构建产物版前端镜像
- `backend/scripts/create_admin_user.py` —— 初始管理员（幂等）
- `backend/tests/scripts/test_create_admin_user.py` —— 5 例单测

## 门禁

| 门禁 | 结果 |
|---|---|
| backend pytest | **580 passed / 27 skipped / 0 failed**（575 + 新增 5） |
| frontend lint | 0 errors（272 warnings 为仓内存量） |
| frontend build | Build successful；产物 `index.html` 资源引用 `/opentask/assets/index-*.js` ✓ |

## handover

- **用户**：① 阿里云 DNS 加 A 记录 `opentask.recluse.fun → 112.126.60.109`（加完可切
  HTTPS + 独立域名，届时路径前缀可退回根路径）；② TD6 产品口径已由另一会话拍板结清；
  ③ TD9 裁定（`frontend/.env.prod` 是否入库）
- **运维**：本机现为**明文 HTTP**过渡形态；`/test/*`、`/openapi.json`、`/docs` 刻意不外露
