# E100 · OAuth 客户端管理体验 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 在 OpenTask 管理端交付「OAuth 客户端」界面（创建/查看/编辑/停用、回调地址与 scopes 管理、一次性密钥展示与复制），并在页面上给出小蓝 CoWork 接入所需的端点与操作说明（含 appKey 先建 → 回调后定的两步流程）。

**Architecture:** 后端 OAuth2 client 管理 API 已完备，**不新增、不改写任何 OAuth2 端点**；后端唯一改动是权限点字典新增 1 条菜单权限 `menu:manage_oauth2`（admin 角色权限集 = 字典全集，随启动播种自动获得）。前端新增 `views/manage/oauth2/**` 页面族 + `service/api/oauth2.ts` 管理函数 + `typings/api/oauth2.d.ts` 类型 + `utils/oauth2-client.ts` 纯函数；路由名 `manage_oauth2`，登记进 `MENU_PERMISSION_ROUTE_KEYS` 受菜单权限门禁；`manage` 父路由改为可见使管理页在侧边栏可达。

**Tech Stack:** Vue 3 + TypeScript strict + Naive UI + elegant-router；FastAPI + SQLAlchemy；pytest；vitest；`pnpm`。

**Spec:** `docs/superpowers/specs/2026-11-06-e100-oauth2-client-admin-design.md`

## Global Constraints

- **不改后端 OAuth2 端点的鉴权口径**：继续用 `_require_admin()`（`role == "admin"`），不换成 `require_permission(...)`（存量 admin 未挂 `user_role` 时会被挡 → 回归风险）。
- **不泄漏、不二次展示密钥**：明文只在注册/轮换的那一次响应里出现；前端只在内存弹窗短暂持有，关闭即清空；列表只显示 `secret_prefix`；不写 localStorage / URL / 日志。
- **前端校验只是防呆**，不是安全边界：redirect_uri 精确匹配与 scope 上界仍由后端强校验。
- **不承诺跨仓一键对接**：小蓝侧应用创建、appKey 生成、回调地址登记仍由小蓝 CoWork 后台完成，本仓只管 OpenTask 侧 client 登记。
- 不改线上环境、不推送、不部署；不使用真实用户凭据。
- 不做 RFC 7591 自助注册；不做密钥找回。
- 一任务一提交；每个 Task 完成后更新 `progress.txt`。
- 本计划不自动开下一 Epic。

---

### Task 1: 后端菜单权限点（TDD）

**Files:**
- Modify: `backend/opentask/services/user_center/permission_defs.py`
- Test: `backend/tests/unit/test_seed.py`

**Interfaces:**
- Consumes: `permission_defs.PERMISSIONS`（字典）、`seed_user_center()`（幂等播种）
- Produces: 权限码 `menu:manage_oauth2`（type=menu，route_key=`manage_oauth2`）

- [ ] **Step 1: 写失败测试**

在 `tests/unit/test_seed.py` 追加用例：

```python
async def test_oauth2_client_menu_permission_granted_to_admin_only(session_maker):
    """OAuth 客户端菜单权限：admin 获得，maintainer/developer/viewer 均不获得"""
    async with session_maker() as session:
        await seed_user_center(session)

        perms = {
            p.code: p
            for p in (await session.execute(select(Permission))).scalars().all()
        }
        assert "menu:manage_oauth2" in perms
        perm = perms["menu:manage_oauth2"]
        assert perm.type == "menu"
        assert perm.route_key == "manage_oauth2"

        admin_codes = await _role_perm_codes(session, "admin")
        assert "menu:manage_oauth2" in admin_codes
        for role in ("maintainer", "developer", "viewer"):
            assert "menu:manage_oauth2" not in await _role_perm_codes(session, role)
```

- [ ] **Step 2: 跑测试确认红**（断言失败：字典里没有该权限码）

- [ ] **Step 3: 实现**——在 `PERMISSIONS` 的「管理端菜单」段落追加：

```python
{"code": "menu:manage_oauth2", "name": "OAuth 客户端", "type": "menu", "route_key": "manage_oauth2"},
```

- [ ] **Step 4: 跑测试确认绿** + 回归 `tests/unit/test_seed.py` 全绿

- [ ] **Step 5: 确认未触碰 OAuth2 端点鉴权**（`git diff` 应只含 permission_defs.py 与测试）

---

### Task 2: 前端纯函数与单测（TDD）

**Files:**
- Create: `frontend/src/utils/oauth2-client.ts`
- Test: `frontend/src/utils/oauth2-client.test.ts`

**Interfaces:**
- Produces（纯函数，无副作用、可单测）：
  - `parseRedirectUriList(raw: string): string[]` —— 按行/逗号切分、去空白、去重、保序
  - `validateRedirectUri(uri: string): { valid: boolean; reason?: string }` —— 必须绝对 http(s) URL
  - `normalizeScopeList(raw: string | string[]): string[]` —— 逗号/空格切分、去重、保序
  - `KNOWN_OAUTH_SCOPES: { scope: string; label: string; endpoint: string }[]` —— provider 实际支持的 4 个 scope（真源：`backend/opentask/api/oauth2/read_api.py`）
  - `scopeLabel(scope: string): string` —— 已知 scope 中文名，未知回退原值（不静默吞掉）

- [ ] **Step 1: 写失败测试** `oauth2-client.test.ts`（覆盖：多行/逗号切分、去重保序、相对路径与 `ftp://` 被拒、`http/https` 通过、scope 归一去重、未知 scope 回退原值）

- [ ] **Step 2: 跑 `pnpm vitest run src/utils/oauth2-client.test.ts` 确认红**

- [ ] **Step 3: 实现 `utils/oauth2-client.ts`**

- [ ] **Step 4: 跑测试确认绿**

---

### Task 3: 前端 API 层与类型

**Files:**
- Modify: `frontend/src/service/api/oauth2.ts`
- Modify: `frontend/src/typings/api/oauth2.d.ts`

**Interfaces:**
- Produces: `fetchGetOAuthClients` / `fetchCreateOAuthClient` / `fetchUpdateOAuthClient` / `fetchDeleteOAuthClient` / `fetchRotateOAuthClientSecret`
- Produces: `Api.OAuth2.OAuthClient` / `OAuthClientCreate` / `OAuthClientUpdate` / `OAuthClientCreated`（字段与后端 schema 一一对应）

- [ ] **Step 1: 补类型**（`OAuthClientView` 字段：client_id / name / description / redirect_uris / scopes / grant_types / status / secret_prefix / created_at）

- [ ] **Step 2: 补 API 函数**（沿用现有 `request` 封装；DELETE 返回 `null`）

- [ ] **Step 3: `pnpm typecheck` 通过**

---

### Task 4: 页面组件

**Files:**
- Create: `frontend/src/views/manage/oauth2/index.vue`
- Create: `frontend/src/views/manage/oauth2/modules/client-form-drawer.vue`
- Create: `frontend/src/views/manage/oauth2/modules/secret-modal.vue`
- Create: `frontend/src/views/manage/oauth2/modules/guide-panel.vue`

**Interfaces:**
- `client-form-drawer.vue`：props `{ visible, clientId }`，emits `update:visible` / `submitted`；负责创建与编辑共用表单
- `secret-modal.vue`：props `{ visible, secret, clientId }`，emits `update:visible`；负责一次性明文展示 + 复制 + 关闭即清空
- `guide-panel.vue`：无 props，纯展示端点表 + 两步流程 + 边界声明

- [ ] **Step 1: `secret-modal.vue`**——明文只渲染在弹窗内；复制按钮走 `navigator.clipboard.writeText`；关闭时清空父级持有的明文；顶部告警「仅此一次」

- [ ] **Step 2: `client-form-drawer.vue`**——名称、client_id（编辑禁改）、描述、回调地址动态列表（逐条校验 + 去重提示）、scopes（已知多选 + 自定义输入）、grant_types（默认两项）

- [ ] **Step 3: `guide-panel.vue`**——端点表（前端 origin 取 `window.location.origin`，后端地址取 API base）、appKey 两步流程、跨仓边界声明、常见问题

- [ ] **Step 4: `index.vue`**——列表（名称/client_id、状态、回调地址数、scopes 标签、密钥前缀、创建时间、操作列）、状态切换、轮换密钥、删除二次确认、创建/编辑抽屉编排

- [ ] **Step 5: `pnpm lint` + `pnpm typecheck` 通过**

---

### Task 5: 路由 / 菜单 / i18n 登记

**Files:**
- Modify: `frontend/src/router/elegant/routes.ts`（`manage` 父路由去掉 `hideInMenu`；新增 `manage_oauth2` 子路由）
- Modify: `frontend/src/router/elegant/imports.ts`（新增视图导入）
- Modify: `frontend/src/typings/elegant-router.d.ts`（路由类型）
- Modify: `frontend/src/store/modules/route/shared.ts`（`MENU_PERMISSION_ROUTE_KEYS` 追加 `'manage_oauth2'`）
- Modify: `frontend/src/locales/langs/zh-cn.ts` + `en-us.ts`（`route.manage_oauth2` 与页面文案）

- [ ] **Step 1: 注册路由与导入**（用 `pnpm gen-route` 生成后再校对 meta；生成器不可用则手工补齐三处）

- [ ] **Step 2: 登记菜单权限 route_key** + 补 `shared.ts` 的既有单测期望值

- [ ] **Step 3: i18n 文案**（zh-cn 必填；en-us 同步）

- [ ] **Step 4: `pnpm test` 通过**（含 `src/store/modules/route/__tests__/shared.test.ts`）

---

### Task 6: 文档与进度

**Files:**
- Create: `docs/oauth2-client-onboarding.md`（管理员/接入方手册，与页面说明面板同源）
- Modify: `progress.txt`

- [ ] **Step 1: 写 onboarding 手册**（端点表、两步流程、边界声明、常见问题）

- [ ] **Step 2: 更新 `progress.txt`**（本次改动摘要与验证状态）

---

### Task 7: 门禁与浏览器验证

- [ ] **Step 1: 后端** `cd backend && uv run pytest tests/ -q` —— 0 failed（记录 passed/skipped 数）
- [ ] **Step 2: 前端** `cd frontend && pnpm lint`（0 error）、`pnpm build`（成功）、`pnpm test`（全绿）、`pnpm typecheck`
- [ ] **Step 3: 浏览器实测**（AGENTS.md 强制：新页面必须浏览器验证）——列表加载、创建 client、一次性密钥弹窗与复制、编辑回调地址、停用、删除、接入说明面板；截图存档
- [ ] **Step 4: 验收文档** `docs/superpowers/acceptances/2026-11-06-e100-oauth2-client-admin-acceptance.md`（门禁数字 + 截图链接 + 已知限制）
- [ ] **Step 5: 提交**（一次提交：本 Epic 全部改动）
