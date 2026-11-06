# E101 · OAuth 自动接入（Install Flow）Implementation Plan **v2**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 交付「小蓝发起安装（PKCE verifier/challenge）→ 管理员确认 → 一次性 code → 服务端兑换密钥」的 OpenTask 侧全链路，并做进管理员界面。

**Architecture:** 新增 1 张表 `oauth_install_requests` + 安装服务 + 安装端点；**无长期凭据**（OpenTask 只存 `challenge=S256(verifier)`）；密钥**永不落库明文**（批准时占位密钥、兑换时轮换）；**未认证发起** → 滥用上限（全局/单 IP pending 配额 + 速率 + 幂等复用 + 15 分钟存活）；`callback_url` 由来方提供 → **开放重定向硬校验**（M1/M2/M3）；**consumed ≠ 成功** → 恢复窗口（verifier 重试换发新密钥）+ 窗口外强制重装。

**Tech Stack:** FastAPI + SQLAlchemy(async) + Alembic；Vue 3 + TS strict + Naive UI + elegant-router；pytest；vitest；`pnpm`。

**Spec:** `docs/superpowers/specs/2026-11-06-e101-oauth2-install-flow-design.md`
**Contract:** `docs/superpowers/contracts/2026-11-06-e101-oauth2-install-contract.md`

## Global Constraints

- **无长期凭据**：不引入 installer token / 共享密钥；OpenTask 只存 challenge。
- **密钥零落库明文**：`client_secret` / 安装码 / verifier 只存哈希（verifier 根本不落库）。
- **`client_secret` 永不进浏览器**：只在小蓝后端的兑换响应体出现一次。
- **日志零泄漏**：新端点不打印 code / verifier / challenge / client_secret / state。
- **consumed ≠ 成功**：只有 2xx 且含 `client_secret` 才算成功；所有 4xx/5xx 是失败。
- **成员授权独立**：安装流不签发 token，不改同意页。
- **不改既有 OAuth2 协议端点**与 `/api/oauth2/clients` 的鉴权口径。
- **不部署线上**：只写代码、迁移、测试、文档；不迁移线上库、不推送。
- 一任务一提交；更新 `progress.txt`；不开下一 Epic。

---

### Task 1: 配置 + 模型 + 迁移

**Files:** `backend/opentask/config.py`、`backend/opentask/models/oauth2/model.py`、`backend/opentask/models/oauth2/__init__.py`、`backend/alembic/versions/2026_11_06_6000-*.py`

- [ ] Step 1: 配置 6 项（§4.8），env 别名 `AUTH_OAUTH_INSTALL_*`
- [ ] Step 2: 模型 `OAuthInstallRequest`（全部列 + 索引，见 §4.1）
- [ ] Step 3: 迁移 `upgrade head` → `downgrade` → `upgrade head` 往返成功
- [ ] Step 4: `uv run pytest tests/oauth2 -q` 仍全绿

### Task 2: 安装服务（TDD）

**Files:** Create `backend/opentask/services/oauth2/install_service.py`；Test `backend/tests/oauth2/test_install_flow.py`

- [ ] Step 1: 写失败测试（16 条，见 §5）
- [ ] Step 2: 跑测试确认红
- [ ] Step 3: 实现服务：
  - `create_request()`：校验 challenge(S256)/redirect_uris/scopes/callback_url(M1/M2)；幂等复用；client_id 冲突 409；pending 配额/速率 429
  - `get_status()`：verifier 恒定时间比对，不匹配 → 404
  - `approve()`：admin；条件更新 PENDING→APPROVED；建 client（**占位密钥**）；生成安装码（只存哈希）；返回 `redirect_to`（回跳前二次校验 M1/M2）
  - `reject()`
  - `exchange()`：verifier 绑定校验 → 首次消费 code（条件更新）+ **轮换密钥**；**恢复路径**（窗口内重试换发新密钥）；窗口外 409
  - `_validate_callback_url()`：M1/M2 严格校验
- [ ] Step 4: 跑测试确认绿

### Task 3: 安装端点

**Files:** `backend/opentask/api/oauth2/install_router.py`、`backend/opentask/api/oauth2/schemas.py`、`backend/opentask/app.py`

- [ ] Step 1: `POST /api/oauth2/install/requests`（201/200）
- [ ] Step 2: `POST /api/oauth2/install/status`（verifier 鉴权，404 不泄露）
- [ ] Step 3: `POST /api/oauth2/install/requests/{id}/approve` / `/reject`（登录 + admin；409 幂等保护；回跳响应头 no-referrer/no-store/nosniff）
- [ ] Step 4: `POST /api/oauth2/install/exchange`（verifier；错误码对齐契约 §3.F）
- [ ] Step 5: `GET /api/oauth2/install/requests`（审计列表，最近 50 条，不含敏感字段）
- [ ] Step 6: 端点日志走查：无 code/verifier/secret/state 打印

### Task 4: 权限点 + 前端路由/i18n

**Files:** `backend/opentask/services/user_center/permission_defs.py`、`backend/tests/unit/test_seed.py`、`frontend/src/store/modules/route/shared.ts`、`frontend/src/router/elegant/{routes,imports}.ts`、`frontend/src/typings/elegant-router.d.ts`、`frontend/src/locales/langs/{zh-cn,en-us}.ts`

- [ ] Step 1: 字典加 `menu:manage_oauth2`；测试断言 admin 获得、其余三个系统角色不获得
- [ ] Step 2: 前端登记 `manage_oauth2`（E100 页）与 `oauth2_install`（安装确认页）
- [ ] Step 3: i18n 文案

### Task 5: 前端 API + 类型 + 页面

**Files:** `frontend/src/service/api/oauth2.ts`、`frontend/src/typings/api/oauth2.d.ts`、`frontend/src/views/oauth2/install/[installId].vue`、`frontend/src/views/manage/oauth2/index.vue`

- [ ] Step 1: API 函数与类型（install requests / status / approve / reject / exchange / audit list）
- [ ] Step 2: 安装确认页：展示名称/接入方来源 IP/UA/回调白名单/scopes/callback 主机 + 风险提示；批准 → 整页跳 `redirect_to`；拒绝 → 提示
- [ ] Step 3: 管理页「安装申请」页签（审计列表 + 状态 + 来源 IP）
- [ ] Step 4: `pnpm lint` + `pnpm typecheck` + `pnpm test` 通过

### Task 6: 文档与进度

- [ ] Step 1: `docs/oauth2-client-onboarding.md` 更新为自动接入流程（引用契约）
- [ ] Step 2: `progress.txt` 更新

### Task 7: 门禁与浏览器验证

- [ ] Step 1: `cd backend && uv run pytest tests/ -v` —— 0 failed（记录数字）
- [ ] Step 2: `cd frontend && pnpm lint && pnpm build && pnpm test && pnpm typecheck`
- [ ] Step 3: 浏览器实测：客户端管理页、安装确认页（登录→确认→回跳）、审计列表；截图
- [ ] Step 4: 验收文档 `docs/superpowers/acceptances/2026-11-06-e101-oauth2-install-flow-acceptance.md`
- [ ] Step 5: 提交（一次提交：本 Epic 全部改动）
