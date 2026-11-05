# E63 Plan：Customer Request 公开状态门户 mid · CLI 1.47.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`ea2119c` · 分支 `sprint/E63-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e63-customer-request-public-status-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E64**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Workspace writer+ 可对 CustomerRequest 启用/轮换/撤销公开 `status_token`；匿名访客经 `/api/public/customer-requests/{token}` 读脱敏状态卡，可选公开回复；FE `/r/:token` + 详情链接管理；CLI **1.47.0**；无客户账号 / Push / Search·Insights·E57–E58 主表面改动 / formula emit。

**Architecture:** 扩展 E22 `customer_requests` 三列 + `customer_request_public_replies` 表；对齐 E31 token（`secrets.token_urlsafe(24)`）与进程内存 rate-limit；公开路由无 auth；回复优先落首个 linked Issue 的 `IssueComment`（作者=`request.created_by`，走既有 `comment.created` webhook，**不**写 Inbox）；无 Issue 时写 public_replies 表且不 fire webhook。

**Tech Stack:** FastAPI + SQLAlchemy async；alembic；Vue3 + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E64；中文 docs；CLI **1.47.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；不改 E57 告警 / E58 假日包 / E60–E62 Search / E61 Insights 主表面（仅 CLI version pins）
- 公开未知/撤销一律 **404**；`OPENTASK_PUBLIC_REQUEST_RATE_LIMIT=0` 关限流
- 已知 flake `test_user_search` 记入 acceptance，不挡
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/models/customer/model.py` | +status_token / enabled / public_replies_enabled；+CustomerRequestPublicReply |
| `backend/alembic/versions/2026_11_05_4800-v8e9f0a1b2c6_customer_request_public_status.py` | alembic（revises `u7d8e9f0a1b5`） |
| `backend/opentask/services/customer/service.py` | status-link + public get/reply + serialize statusLink |
| `backend/opentask/api/customer_requests/router.py` | enable/rotate/revoke + publicReplies patch field |
| `backend/opentask/api/public_customer_requests/` | GET/POST public |
| `backend/opentask/app.py` | include public router |
| `backend/tests/api/test_e63_public_status.py` | 定向门禁 |
| `frontend/src/views/r/[token].vue` + router/imports/types | 公开页 |
| `frontend/src/views/requests/detail/index.vue` + api | 详情开关 |
| `agent-harness/opentask-cli/**` | 1.47.0 + status-link / public-status |

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e63-customer-request-public-status-mid.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E63-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e63-customer-request-public-status-mid.md \
  docs/superpowers/acceptances/2026-11-05-E63-acceptance.md
git commit -m "docs(E63): plan + acceptance skeleton"
```

---

### Task 2 — A：模型 + alembic + enable/rotate/revoke（TDD）

**Files:**
- Modify: `backend/opentask/models/customer/model.py`
- Modify: `backend/opentask/models/customer/__init__.py`
- Create: `backend/alembic/versions/2026_11_05_4800-v8e9f0a1b2c6_customer_request_public_status.py`
- Modify: `backend/opentask/services/customer/service.py`
- Modify: `backend/opentask/api/customer_requests/router.py`
- Create: `backend/tests/api/test_e63_public_status.py`

**Interfaces:**
```python
# CustomerRequest columns
status_token: str | None          # unique, nullable
status_token_enabled: bool        # default False
public_replies_enabled: bool      # default False

# CustomerRequestPublicReply
# id, request_id FK CASCADE, body Text, created_at

# Service
async def enable_status_link(workspace_id, request_id, *, public_replies_enabled: bool | None = None) -> CustomerRequest
async def rotate_status_link(workspace_id, request_id) -> CustomerRequest
async def revoke_status_link(workspace_id, request_id) -> CustomerRequest
# token = secrets.token_urlsafe(24)

# statusLink in to_response (always on detail; list ok without token):
# { "enabled": bool, "url": "/r/{token}"|None, "publicRepliesEnabled": bool }
# token plaintext only when include_token=True (enable/rotate responses or ?include_token=1)
```

**Endpoints (writer+):**
- `POST /api/customer-requests/{id}/status-link/enable`
- `POST /api/customer-requests/{id}/status-link/rotate`
- `POST /api/customer-requests/{id}/status-link/revoke`
- RequestUpdate + optional body on enable: `publicRepliesEnabled?: bool`

- [ ] **Step 1: 红测** `test_e63_enable_rotate_revoke_token_lifecycle`
  - enable → 有 token、enabled=true、url=/r/...
  - rotate → 新 token；旧 token 稍后公开 GET 404
  - revoke → enabled=false、token 空
  - viewer 写 → 403；跨 WS → 404
- [ ] **Step 2:** Run → FAIL
- [ ] **Step 3:** 模型+migration+service+router
- [ ] **Step 4:** Run → PASS
- [ ] **Step 5:** Commit `feat(E63): status-link enable/rotate/revoke + alembic`

---

### Task 3 — B：公开 GET 脱敏 + rate-limit（TDD）

**Files:**
- Create: `backend/opentask/api/public_customer_requests/__init__.py`
- Create: `backend/opentask/api/public_customer_requests/router.py`
- Modify: `backend/opentask/services/customer/service.py` — get_by_status_token / serialize_public_card / rate-limit
- Modify: `backend/opentask/app.py`

**Interfaces:**
```python
# Public card (Q1a/D3)
{
  "title": str,
  "status": str,
  "priority": str | None,
  "updatedAt": str | None,
  "customerName": str | None,
  "linkedIssueCount": int,
  "linkedIssueCodes": list[str],  # codes only
  "publicRepliesEnabled": bool,
  "recentPublicReplies": list[{"body": str, "createdAt": str}],  # from public_replies table only, ≤10
}
# MUST NOT include: workspaceId, member emails, issue description, internal comments, request id, token

# Rate limit (D5): 30/60s/token；env OPENTASK_PUBLIC_REQUEST_RATE_LIMIT=0 disables
# Unknown / disabled / revoked → 404 (identical)
```

- [ ] **Step 1: 红测** `test_e63_public_get_redacted_card` + `test_e63_public_get_404_revoked` + `test_e63_public_rate_limit`
- [ ] **Step 2:** Run → FAIL
- [ ] **Step 3:** 实现公开 GET + rate-limit
- [ ] **Step 4:** Run → PASS
- [ ] **Step 5:** Commit `feat(E63): public GET status card + rate-limit`

---

### Task 4 — C：公开 replies 落点 Q3a + 内部可见 + no Inbox（TDD）

**Files:**
- Modify: service + public router POST `/{token}/replies`
- Modify: `to_response` — detail 可带 `publicReplies` 列表（仅表内行）

**Behavior (Q3a/Q4a/Q5a):**
```python
# POST body: { "body": str }  (1..4000 chars strip)
# if not public_replies_enabled or not status_token_enabled → 404
# if linked issues:
#   first issue by CustomerRequestIssue.created_at ASC
#   insert IssueComment(comment_type=COMMENT, user_id=request.created_by or None)
#   fire_webhooks event_type="comment.created" (no new event name)
#   DO NOT call NotificationService.notify_comment (Q5a)
# else:
#   insert CustomerRequestPublicReply
#   DO NOT fire_webhooks
```

- [ ] **Step 1: 红测** 有 Issue 落评论；无 Issue 落表；关闭 → 404；spy fire_webhooks 仅评论路径；spy 无 inbox 类型写入（或 mock notify_comment 未调用）
- [ ] **Step 2–4:** TDD 绿
- [ ] **Step 5:** Commit `feat(E63): public replies Q3a/Q4a/Q5a`

---

### Task 5 — F 边界：tenant / no-emit / 不改邻面（TDD）

**Files:**
- Extend: `backend/tests/api/test_e63_public_status.py`

- [ ] **Step 1:** 跨租户 enable 404；公开 token 不泄露他租户；formula/fire 路径 spy（公开 GET 不 fire_webhooks）；不触 E57/E58/E61/E62 主表面文件（diff 自检）
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** Commit `test(E63): tenant + no-emit spies`

---

### Task 6 — D：FE `/r/:token` + 详情管理（vitest）

**Files:**
- Create: `frontend/src/views/r/[token].vue`
- Modify: `frontend/src/router/routes/index.ts` — custom route `public-request-status` `/r/:token` blank
- Modify: `frontend/src/router/elegant/imports.ts` + `frontend/src/typings/elegant-router.d.ts` — register `r`
- Modify: `frontend/src/service/api/customer-requests.ts` — statusLink types + enable/rotate/revoke + public fetch helpers
- Modify: `frontend/src/views/requests/detail/index.vue` — 开关/复制/轮换/撤销/公开回复
- Create: `frontend/src/service/api/customer-requests.test.ts` — 脱敏字段断言 helpers / URL builder

- [ ] **Step 1:** vitest 红 → 实现 → 绿；`pnpm run build` ok
- [ ] **Step 2:** Commit `feat(E63): FE public status page + detail controls`

---

### Task 7 — E：CLI 1.47.0

**Files:**
- Pin all `1.46.0` → `1.47.0`（VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` / 历史断言）
- Modify: `agent-harness/opentask-cli/opentask/core/request.py` — status-link group + public-status
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py` — API helpers
- Create: `agent-harness/opentask-cli/tests/test_e63_public_status.py`

```text
opentask request status-link enable|rotate|revoke|show <id>
opentask request public-status <token> [--json]
```

- [ ] **Step 1:** 测试红 → 实现 → 绿
- [ ] **Step 2:** Commit `feat(E63): CLI 1.47.0 status-link + public-status`

---

### Task 8 — Verify + acceptance

- [ ] BE full suite + directed E63/E22/E31
- [ ] CLI full suite
- [ ] FE vitest + build
- [ ] Fill acceptance tip SHA + gates
- [ ] Final tip commit
- [ ] STOP；不 push；不开 E64

## Self-review
- Spec A–F → Tasks 2–7 覆盖
- Q1a–Q6a / D1–D7 写入 Interfaces
- 无 TBD；revision `v8e9f0a1b2c6` ← `u7d8e9f0a1b5`
