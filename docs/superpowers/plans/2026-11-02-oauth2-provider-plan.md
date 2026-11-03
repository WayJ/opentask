# OpenTask OAuth2 Provider 实施计划

- 日期：2026-11-02
- 规格：`docs/superpowers/specs/2026-11-02-oauth2-provider-design.md`（契约权威）
- 分支：`WayJ/oauth2-provider`（从 `WayJ/check-oauth2-support` 改名而来，后者从 `e954aa4` 出发）
- 门禁：`cd backend && uv run pytest tests/ -v`；`cd frontend && npm run lint && npm run build`；MCP Playwright 浏览器证据

---

## 阶段划分

### T0 · 准备
- [x] T0.1 分支改名 `WayJ/check-oauth2-support` → `WayJ/oauth2-provider` —— **不适用（落地方式不同）**：未保留独立分支，OAuth2 的 7 个 commit 直接落在 `main`（ea02db7…df83917），2026-11-03 复核 `git branch -a` 仅 `main`
- [x] T0.2 AGENTS.md 已授权改动（移除 MANDATORY workflow-guide 段）随本次提交落地 —— 证据：commit ea02db7 改 `AGENTS.md`；2026-11-03 复核全文已无「Workflow Guide / Constitution」段

### T1 · 数据模型与迁移
- [x] T1.1 `backend/opentask/models/oauth2/model.py` — `OAuthClient` / `OAuthAuthorizationCode` / `OAuthAccessToken` / `OAuthRefreshToken`
- [x] T1.2 `backend/opentask/models/oauth2/__init__.py` + `models/__init__.py` 注册（alembic autogenerate 需完整 metadata）—— 证据：`backend/opentask/models/__init__.py:46`
- [x] T1.3 新 alembic revision（挂在 `003ccd38d5cd` 之后），4 张表 + 索引 + 外键 —— 证据：`backend/alembic/versions/2026_11_02_1015-c4f8a2b91d6e_oauth2_provider_tables.py`；4 表 = oauth_clients / oauth_authorization_codes / oauth_access_tokens / oauth_refresh_tokens
- [x] T1.4 单测：模型可建表、唯一索引生效 —— 证据：`backend/tests/oauth2/`（6 个测试文件，含 client_crud / authorization_flow）

### T2 · 服务层
- [x] T2.1 `services/oauth2/client_service.py` — 注册/列表/更新/禁用、secret 生成（明文仅一次）与哈希校验、redirect_uri 白名单精确匹配、scope 允许集
- [x] T2.2 `services/oauth2/authorization_service.py` — 授权码签发（哈希存储、10min TTL）、消费（一次性）、重放检测
- [x] T2.3 `services/oauth2/token_service.py` — access token 签发（`scope` claim + `aud` + `jti`）、refresh 签发/轮换/吊销、重放 → 吊销该用户全部 OAuth token
- [x] T2.4 `services/oauth2/identity_service.py` — email → username 精确查 → `unique_username` 建号 —— **注意**：服务已实现但授权流程未接线（仅被测试调用），已登记 TD6；设计文档 §280 记录了同一约束
- [x] T2.5 单测：secret 校验、TTL、一次性、重放吊销、建号 —— 证据：`backend/tests/oauth2/test_client_crud.py`、`test_authorization_flow.py`、`test_token_endpoint.py`、`test_userinfo.py`

### T3 · API 层
- [x] T3.1 `api/oauth2/schemas.py` — 请求/响应模型（RFC 6749 形状）
- [x] T3.2 `api/oauth2/dependencies.py` — `require_oauth_client` / `require_oauth_scope`（`options={"verify_aud": False}` + 显式 aud 比对 + scope 校验 + tv + status + jti 未吊销）
- [x] T3.3 `api/oauth2/router.py` — `/oauth2/authorize`（GET，未登录 302 登录页）、`/oauth2/authorize/approve`（POST）、`/oauth2/token`、`/oauth2/userinfo`、`/oauth2/revoke`、`/oauth2/clients`（CRUD）
- [x] T3.4 `api/oauth2/read_api.py` — `/oauth2/api/tasks|projects|requirements|me` 薄封装既有 service 层
- [x] T3.5 `app.py` 挂载 router（`/oauth2` 前缀；`/oauth2/authorize` 与 `/oauth2/token` 不挂 `common_dependencies`）
- [x] T3.6 单测：端点错误形状（RFC 6749 §5.2）、scope 不足 403 `insufficient_scope` —— 证据：`backend/tests/oauth2/test_token_endpoint.py`、`test_scope_enforcement.py`

### T4 · 安全回归钉死（**必做，防止 python-jose 升级静默失守**）
- [x] T4.1 带 `aud` 的 token 被全局链 `/api/*` 拒绝（401）—— 证据：验收记录 §3.3 scope 隔离表（`/api/issues` + OAuth token → 401）
- [x] T4.2 带 `aud` 的 token 被契约层 `/tasks` 拒绝 —— 证据：验收记录 §3.3（`/tasks` + OAuth token → 401）
- [x] T4.3 不带 `aud` 的既有会话 token 仍正常（防回归误伤）—— 证据：验收记录 §3.3（`/api/issues` + 会话 token → 200）

### T5 · 前端同意页
- [x] T5.1 `frontend/src/service/api/oauth2.ts`
- [x] T5.2 `frontend/src/views/oauth2/consent.vue`（展示应用名/描述/scope 清单/redirect 主机；同意与拒绝）—— **实际路径为 `frontend/src/views/oauth2/index.vue`**（与计划命名不同，路由 `/oauth2/authorize` → `layout.base$view.oauth2`），功能与计划一致
- [x] T5.3 `pnpm gen-route` 生成路由；i18n key 登记 —— 证据：`frontend/src/router/elegant/{imports,transform,routes}.ts` 登记 `oauth2`；`frontend/src/locales/langs/{zh-cn,en-us}.ts` 登记 `route.oauth2` 与同意页文案
- [x] T5.4 `npm run lint` + `npm run build` —— 证据 2026-11-03 复跑：eslint 0 errors（272 warnings 为仓内存量）/ vite build successful

### T6 · 浏览器证据（MCP Playwright）
- [x] T6.1 未登录访问 `/oauth2/authorize` → 登录页 → 登录后回跳同意页 —— 证据：验收记录 §2.1 / §2.2
- [x] T6.2 同意页展示正确（应用名 + scope 清单）—— 证据：验收记录 §2.3 要素逐项核对表
- [x] T6.3 同意 → 302 回 dsh-saas callback（用本地回环地址验证 code 下发）—— 证据：验收记录 §2.4 + §3.1（真实 code 换令牌）
- [x] T6.4 只读数据面截图 —— 证据：验收记录 §3.2（5 个只读端点 200）

### T7 · 提交
- [x] T7.1 commit 1：规格与计划文档（+ AGENTS.md 授权改动）—— 实际 commit ea02db7
- [x] T7.2 commit 2：后端实现（T1–T4）—— 实际 commit 63211cf（+ 后续修复 45a6c3d / df83917）
- [x] T7.3 commit 3：前端实现（T5–T6）—— 实际 commit 9c2abd0（+ 后续修复 b7ec2e3）+ 用例 bbeef16 + 验收记录 fed2546；实际拆为 7 个 commit（含 3 次修复提交）

---

## 风险与对策

| 风险 | 对策 |
|---|---|
| python-jose 版本升级改变 `aud` 行为 → OAuth token 混入通用 API 面 | T4 回归测试钉死；测试失败即阻断合并 |
| `scope` claim 与既有 `scp=pwd_change` 语义混用 | claim 名分离：`scope` vs `scp`；测试断言二者互不影响 |
| 只读数据面与通用端点口径漂移 | 只读面**薄封装**既有 service 层，不复制业务逻辑 |
| 授权码重放 | 一次性消费 + 重放即吊销该用户全部 OAuth token |
| 迁移撞号 | dsh-saas 侧写迁移前重查最大 V 号（协调者裁决 C2） |

---

## 交付物

- `docs/superpowers/specs/2026-11-02-oauth2-provider-design.md`
- `docs/superpowers/plans/2026-11-02-oauth2-provider-plan.md`
- `backend/opentask/models/oauth2/`、`backend/opentask/services/oauth2/`、`backend/opentask/api/oauth2/`
- `backend/alembic/versions/<new>_oauth2_tables.py`
- `backend/tests/oauth2/`
- `frontend/src/views/oauth2/consent.vue`、`frontend/src/service/api/oauth2.ts`
