# 技术债清偿笔记 — 2026-11-03（TD3 / TD7 / TD8 修复；TD6 待裁定）

## background

上一轮（`2026-11-03-epic-closure.md`）把 E1/E2 两个 epic 关闭后，`docs/tech-debt-tracker.md`
里仍挂着 4 条未关闭债。本轮按「**能修的直接修、需裁定的留下并说清**」处理。

## 本轮修了什么

### TD7 · 全量 OpenAPI spec 与实现漂移 —— 已销账

- **根因**：OAuth2 Provider（2026-11-02 交付）之后没人重新导出全量 spec，`backend/openapi.json`
  / `openapi_current.json` 停在 171 路径、**0 条** `/oauth2`。
- **处置**：新增可重复执行的导出脚本 `backend/scripts/export_openapi.py`
  （`app.openapi()` → 两个产物文件），重跑后 **183 路径（+12 条 oauth2）**。
  与 HEAD 逐路径对比：**added 12 / removed 0 / changed 0**——除新增外无任何其它路径变化。
  重跑产物字节一致（md5 校验）→ 幂等。
- **顺带订正了 TD7 原判据里的路径名错误**：后端**没有** `/oauth2/authorize` 端点。
  授权入口是**前端 SPA 路由** `/oauth2/authorize`；后端对应的是
  `/api/oauth2/authorize/context`（校验请求 + 返回同意页上下文）与
  `/api/oauth2/authorize/approve`（同意/拒绝）。spec 覆盖的是这两个。

### TD8 · Jira 线格式契约无稳定落点 —— 已销账

- **先澄清**：TD8 原描述说「唯一权威是 sprint 探测文档」并不准确——`backend/README.md`
  早有一节 Jira 线格式速查。真正的缺口是：① 那只是 README 摘要，不是完整契约；
  ② **没有任何机制防止文档与实现漂移**。
- **处置**：新增 `backend/docs/jira-wire.md`——仓内权威契约：
  18 个端点全表、鉴权（Basic/Bearer → 契约凭证内核）、Jira 形状错误体与错误码表、
  issue/search 形状要点、JQL 支持子集与越界语义、状态映射表、已知边界
  （cloud v3 / agile board / webhook 皆有意不做）。
- **护栏**：新增 `backend/tests/tasks/test_jira_wire_doc.py`（4 例）——**双向对账**：
  已实现路由 ⊆ 文档表格，且文档表格 ⊆ 已实现路由（防文档腐化），另断言关键契约锚点。
  **新增端点忘写文档 → 测试红。** 这是 TD8 的还款条件（把契约固化为稳定文档）+
  额外的漂移防护。

### TD3 · Docker 栈与实际技术栈不符 —— 已销账

- **原状**（三处错）：根 `Dockerfile` 是 Node+Prisma 模板（改名前残留，与 Python 栈完全不符）；
  compose 的 `backend` 服务 build 它、`frontend` 服务指向**并不存在**的 `frontend/Dockerfile`；
  环境变量写的是后端**根本不读**的 `DATABASE_URL` / `REDIS_URL`——代码里**没有任何 redis 依赖**。
- **处置**：
  - 根 `Dockerfile` 重写为 **Python 3.11 + uv** 后端镜像（启动前 `alembic upgrade head`，
    再 uvicorn 7377；端口固定按 `backend/AGENTS.md`）；
  - 新增 `frontend/Dockerfile`（pnpm 9 构建 → nginx 托管静态资源）；
  - 新增 `frontend/nginx.conf`——静态托管 + `location /opentask/ { proxy_pass http://backend:7377/; }`。
    **这就是 E1-Q1（生产 nginx 与 `/opentask/` 前缀同步）的参考形态**，运维侧可据此对齐；
  - 新增根 `.dockerignore` 与 `frontend/.dockerignore`（顺带把 `backend/config/local.yaml`、
    `.env.*.local` 挡在镜像层外）；
  - `docker-compose.yml` 重写：postgres 15 + backend + frontend；env 换成后端真正读的
    `POSTGRES_*` + `AUTH_SECRET_KEY`（`${AUTH_SECRET_KEY:?…}` fail-closed，缺 key 直接拒起）；
    **删掉无用的 redis 服务**。
- **踩坑**：镜像里 uv 版本 pin 得太老（0.5.11）与 `uv.lock` 的 `revision = 3` 存在格式风险 →
  对齐到本机工具链 **uv 0.12.21** 后重建通过。
- **踩坑（只有真跑才暴露）**：第一次起全栈，后端容器**直接起不来**——
  `ImportError: Bad git executable`：`opentask.services.git_knowledge_service` 在 **import 期**
  就要求 `git` 可执行文件（GitPython 初始化），而镜像里没装 git。
  → 已在镜像中补 `git`（apt）后重建通过。**镜像不实际起一次，就不知道缺什么。**
- **踩坑（前端 nginx，两个）**：
  1. `proxy_pass http://backend:7377;` 里的**静态主机名只在启动时解析一次并写死 IP**——
     后端容器一重建换 IP，前端就永久 502（`Host is unreachable`）。
     → 改用 Docker 内嵌 DNS（`resolver 127.0.0.11`）+ 变量形式 `proxy_pass http://$backend_host:7377`
     做**每请求解析**；前缀剥离改用 `rewrite ^/opentask/(.*)$ /$1 break`（proxy_pass 带变量时
     URI 替换语义会变，rewrite 语义明确）。
  2. 健康检查用 `wget http://localhost/` → busybox 把 localhost 解析到 IPv6 `::1`，
     nginx 只听 IPv4 → Connection refused → 容器一直 unhealthy。
     → 改用 `http://127.0.0.1/`。
- **顺带验证到 fail-closed 生效**：`docker compose build` 时没带 `AUTH_SECRET_KEY`，
  compose 直接报错 `required variable AUTH_SECRET_KEY is missing`（compose 的 `${VAR:?}` 插值），
  不会带着空密钥起容器。

### TD6 · OAuth2 身份自动建号 —— 已销账（用户拍板「维持标准 OAuth2 语义」）

- **复核订正了原描述里的一个误解**：设计文档 §280 说「前端用户名正则不允许 `@`，与 email 作
  username 种子冲突」——**不成立**。`REG_USER_NAME`（`frontend/src/constants/reg.ts:1`）只约束
  前端表单；后端 `user.username` 是 `String(50)` 唯一索引且**无任何格式校验**，
  服务端自动建号不受该正则约束。唯一真实边界是列长 50（超长 email 需截断/派生）。
- **真正的待裁定项是身份来源与信任模型**：email 从哪来？客户端可否代断言 email
  （否则存在冒名建号面）？
- **裁定（2026-11-03，用户拍板）**：走「维持标准 OAuth2 语义」——**成员须先有 OpenTask 账号**
  才能完成授权同意，授权流**不接入自动建号**。资源所有者身份由授权服务器的登录会话决定
  （谁在同意页点同意就代表谁）。
- **落地**：设计文档 §280 已标注裁定结论并订正上述误解；`resolve_or_create` 保留在仓内
  （含单测）但不接线，作为将来改口径时的现成实现；本期不改核心 `user` 表、不放宽前端正则。
- **需求侧动作（非本仓，需你/dsh-saas 侧跟进）**：「连接 OpenTask」入口的引导文案需说明
  「需先有 OpenTask 账号」并给出注册入口。

## 门禁（2026-11-03 实测）

| 门禁 | 结果 |
|---|---|
| backend pytest | **575 passed / 27 skipped / 0 failed**（571 → +4 = 新增文档漂移测试） |
| frontend lint | 0 errors（272 warnings 为仓内存量） |
| frontend build | Build successful |
| docker 后端镜像 | 构建通过 |
| docker 前端镜像 | 构建通过 |
| compose 全栈 | postgres 迁移到 head（含 oauth2 revision）→ backend healthy(7377) → frontend healthy(8080)；`/` 200、`/login` SPA 回退 200、`/opentask/openapi.json` 经反代 200、`/opentask/capabilities` 经反代返回契约 JSON |

## 踩坑

- 后端门禁第一次跑是 **205 passed / 368 errors**（清一色 `OSError`）：根因不是代码——
  本机 PG 容器停着、DB 连不上。起容器后即全绿。**跑门禁前先确认 DB 在跑。**
- 文档类债容易「看着已修其实没修」：TD8 原判据本身就不准确（README 里已有速查），
  销账前先复核债条本身写得对不对。

## handover

- **用户**：TD6 的产品口径裁定（接 `resolve_or_create` 还是「须先有账号」）
- **运维**：E1-Q1——生产 nginx 必须同步 `/opentask/` 前缀（仓内参考 `frontend/nginx.conf`）
- **WayJ**：TD3/TD7/TD8 已销账；compose 栈的 secret 注入方式（`AUTH_SECRET_KEY`）需在
  CI/部署侧确认
