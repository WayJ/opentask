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
| 生产数据 | **全新空库** | 内网 MySQL 从公网机不可达，且 MySQL→PG 转换面大 |
| 品牌字样 | 代码中**全面改名**（`jnpf_*` → `sso_*`），**保留**上游 SSO 集成 | 用户裁定；协议字面量集中在单一模块 |

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

## 踩坑（全部是发布过程中真实撞到的）

1. **macOS 的 tar 会打 AppleDouble 残片**（`._<原名>`，163 字节、含空字节）。这次带过去
   485 个，其中 `backend/alembic/._env.py` 被 alembic 当迁移脚本加载 →
   `SyntaxError: source code string cannot contain null bytes` → 后端崩溃循环。
   处置：`COPYFILE_DISABLE=1` + tar `--exclude='._*'` + `.dockerignore` 排除 + 送达后清理。
2. **国内机器直连 Debian 官方源 33KB/s**（阿里云 ECS 实测）——首轮发布卡在
   `apt-get install` 近 2 小时。改 `Dockerfile` 加 `ARG DEBIAN_HOST`，生产编排默认走
   `mirrors.aliyun.com`（650KB/s，20 倍）。PyPI 侧不用动：`uv.lock` 本身就锁在清华镜像。
3. **本机 docker 没装 buildx**，BuildKit 也不可用（`docker build --platform linux/amd64`
   被忽略，产物仍是 arm64）。因此**放弃交叉构建**，改为：开发机出 `dist` → 传服务器 →
   服务器用 `frontend/Dockerfile.dist`（只有 COPY）原生打包成版本化镜像。
4. **`frontend/.env.prod` 从未入库**（`.gitignore` 的 `.env.*` 规则），但 Dockerfile 旧注释
   称「已在仓内」——事实不符。已缓解（Dockerfile 增 `ARG/ENV` 固化前缀 +
   `deploy.sh` 前置校验拦下缺文件/错前缀），根因登记为 **TD9** 待用户裁定是否入库。
5. **后端镜像单阶段 3.4GB**（gcc 留在运行层）→ 改多阶段后 **1.8GB**（剩下的是
   venv 里 numpy/pandas/pyarrow 等真实依赖体积，不是工具链）；新增构建期
   `import opentask.main` 冒烟，运行期缺动态库在构建阶段就炸。
   另一处耗时点：`COPY --from=ghcr.io/astral-sh/uv:0.12.21` 从 ghcr 拉 23.5MB
   在国内只有 ~30KB/s（首次拉了 10 分钟），该层之后被 BuildKit 缓存，不再重复付。
6. **脚本在容器里的两个坑**：`python scripts/x.py` 时 `sys.path[0]` 是 scripts/ 而包在上一级
   （镜像用 `--no-install-project`，项目自身没进 venv）；以及 `opentask.models` 包**没导出**
   `AccessToken` 与 `project_knowledge_bases` 关联表，mapper 配置期报
   "expression 'X' failed to locate a name"。处置：脚本加路径自举 + 加载 app 的真实导入图
   （不能自己全量扫 models 包——已退役未删除的 `models/datainsight/` 导进去反而炸）。
7. **仓库在本次会话期间被另一会话并发提交**（`afe784e` 偿清 TD3/TD7/TD8、`ae010dd` TD6 销账）。
   `frontend/nginx.conf` 在我读取后被改写，带入两条我没写过的经验——**照单全收**：
   ① nginx 静态主机名只在启动时解析，后端容器重建换 IP 会让前端永久 502，
   故用 Docker 内嵌 DNS（127.0.0.11）逐请求解析；
   ② 前缀剥选用 `rewrite ... break` + 不带 URI 的 `proxy_pass`（带变量时 URI 替换语义会变）。

## 产出

- `docker-compose.prod.yml` —— 生产编排（端口一律绑回环、fail-closed 密钥、日志轮转、
  三个服务 mem_limit 封顶）
- `deploy/deploy.sh` —— 幂等发布脚本（产物构建 → 送达 → 服务器打包/构建/起栈 → 建管理员 →
  装 nginx）
- `deploy/nginx/opentask-locations.conf` —— 宿主 nginx location 片段
- `deploy/README.md` —— 拓扑、路径语义、发布流程、运维手册、网络实测、验收清单
- `frontend/Dockerfile.dist` —— 预构建产物版前端镜像
- `backend/scripts/create_admin_user.py` —— 初始管理员（幂等）+ 5 例单测
- `backend/alembic/versions/2026_11_03_1900-b7e2c9140d3a_rename_user_sso_columns.py` —— SSO 列改名

## 登录口令的传输加密（用户要求「密码加密，不要依赖 https」）

部署形态是明文 HTTP（无域名 → 签不了 HTTPS 证书），口令明文提交不可接受。方案：

**RSA-OAEP / SHA-256 非对称**——私钥只在服务器，公钥打进前端 bundle。

| 侧 | 实现 | 关键约束 |
|---|---|---|
| 前端 | node-forge（新增依赖 1.3.1 + @types/node-forge） | **`crypto.subtle` 只在安全上下文可用**，明文 HTTP 页面是 undefined → 必须用纯 JS 库；crypto-js 4.x 已移除 RSA 模块 |
| 后端 | cryptography（已有依赖） | 私钥 `<DATA_DIRECTORY>/login_private.pem`（600，不进镜像） |

- **实测互通**：node-forge 加密 → Python cryptography 解密成功；两边 OAEP 参数
  （SHA-256 + MGF1-SHA256 + 空 label）一致
- **踩坑**：node-forge 的 `publicKey.encrypt` 是**位置参数**
  `encrypt(data, 'RSA-OAEP', {md, mgf1})`——旧版对象式 API 会静默产出**非法密文**
  （我第一次就踩了，Python 侧解密直接 ValueError）；node-forge 的 decrypt 返回的是
  **字节串**，中文要 `decodeUtf8` 才还原
- **发布流程改动**：`deploy.sh` 顺序重构为「同步 → 起后端 → 生成密钥对 → 取回公钥 →
  构建前端（注入公钥）→ 打包前端镜像 → 全栈起停」，因为公钥必须在前端构建**之前**
  就存在于服务器
- 测试：后端 8 例（往返/明文回退/无密钥/公钥格式）+ 前端 4 例（往返/随机性/中文）

**剩余风险（已写进 deploy/README.md）**：这套机制防**被动抓包**；但明文 HTTP 下前端
bundle 与公钥都可被替换 → 防不了**主动中间人**；且 **JWT 仍是明文**（在
Authorization 头里），抓包可劫持会话。完整保护仍需 TLS。

## 资源清理（用户授权「服务器上其他服务都可以关掉」）

| 动作 | 效果 |
|---|---|
| journal vacuum + 固化上限 200M | **释放 3.7GB 磁盘**（journal 原占 3.9GB） |
| 停 Orca 远程守护进程（202MB） | 全机最大内存占用者；恢复命令留档在 `/root/.orca-remote/RESTART-HINT.txt` |
| 停 ModemManager / udisks2 / rsyslog / multipathd / tuned | 桌面态服务，云主机用不上 |
| 清理旧镜像（6 个后端标签 → 1 个） | 磁盘从 30G 用量降到 25G |
| 栈内服务 mem_limit（256M/512M/64M） | 防止单服务吃干 1.6GB 的机器 |

**保留未动**：docker / containerd / nginx / ssh / chrony（TLS 证书与 JWT 有效期依赖时间同步）/
systemd-resolved / 阿里云安全与监控 agent。

## 门禁

| 门禁 | 结果 |
|---|---|
| backend pytest | **580 passed / 27 skipped / 0 failed** |
| frontend lint | 0 errors（272 warnings 为仓内存量） |
| frontend build | Build successful；产物 `index.html` 资源引用 `/opentask/assets/index-*.js` ✓ |
| CLI | `opentask --version` → v1.0.6 |
| 凭据卫生 | `Hzgl@2026`、`minioadmin123` **全历史零命中**；`local.yaml` 从未入库、远端也没有 |

## 验收（对 `http://112.126.60.109` 实跑，13/13 通过）

SPA 首页 200 且是 SPA index.html ✓；资源引用 `/opentask/assets/` 且 Content-Type 为
javascript ✓；`/opentask/home` SPA 回退 200 ✓；`/opentask/api/*` 反代通、未带 token 被拒 401 ✓；
**`POST /opentask/api/auth/login` 200 并返回 JWT** ✓；`POST /oauth2/token` 端点存活（422，
缺参数）✓；`/capabilities`、`/healthcheck` 均 200 ✓。

## handover

- **用户**：① 阿里云 DNS 加 A 记录 `opentask.recluse.fun → 112.126.60.109`（加完可切
  HTTPS；当前**明文 HTTP**，前端登录口令是明文传输的，代码注释明写「依赖 HTTPS」）；
  ② TD9 裁定（`frontend/.env.prod` 是否入库）；③ Orca 守护进程如需恢复，按
  `/root/.orca-remote/RESTART-HINT.txt` 的命令启动
- **运维**：本机现为明文 HTTP 过渡形态；`/test/*`、`/openapi.json`、`/docs` 刻意不外露；
  上游 SSO 集成保留但生产关闭（`AUTH_SSO_ENABLED=false`）
