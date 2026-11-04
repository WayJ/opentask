# E44 Plan：Webhook event pack + delivery reliability v1

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`2984a54` · 分支 `sprint/E44-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e44-webhook-events-delivery-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E45**。

**Goal:** 出站 webhook 专用 `issue.assignee_changed` / `issue.label_added` / `issue.label_removed`；失败投递持久化 payload + 外部 `run-due-deliveries` + 人工 replay；FE 失败列表/重试；CLI **1.28.0**。

**Architecture:** 扩 `webhook_delivery_logs` 状态机（一逻辑投递一行，共享 `delivery_id`）；首次同步短重试保留（E29 `MAX_ATTEMPTS=2`），失败入 `pending_retry`；外部 tick / owner replay 用存盘 envelope 再签再投；写路径旁路挂专用事件（指派双发、标签只发专用）。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3 + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E45；中文 docs；CLI **1.28.0**
- Q1–Q6 已拍板：`issue.label_*`；标签不双发 updated；扩列；dead 续同 delivery_id；简单 prune；run-due member+
- `WEBHOOK_DELIVERY_MAX_ATTEMPTS=5`（含首次同步）；backoff 分钟 `[1,5,25,120]`；tick cap 100
- E43 formula / cache **永不** emit；HMAC 不变；无 Redis/cron
- 非目标见 design §3

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e44-webhook-events-delivery.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E44-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：WEBHOOK_EVENTS +3 + 写路径 fire（TDD）

**Files:**
- Modify: `backend/opentask/models/workspace_webhook/model.py` — `WEBHOOK_EVENTS` += 三事件
- Modify: `backend/opentask/services/issue_service.py` — `update_issue`：捕获 `assignee_changed_from`；`assignee_did_change` 时 **额外** `fire_webhooks("issue.assignee_changed", {id,issueCode,title,from,to,actorUserId})`（仍发 `issue.updated`）
- Modify: `backend/opentask/services/tag/service.py` — `attach_tag` / `detach_tag` / `replace_issue_tags` 成功后 `fire_webhooks` `issue.label_added` / `issue.label_removed`（**不**发假 `issue.updated`）；payload `{id,issueCode,title,labelId,labelName,actorUserId}`
- Test: `backend/tests/api/test_e44_webhook_events_delivery.py`

**Interfaces:**
- Produces: 三事件可订阅；assignee 双发；label 专用

- [ ] **Step 1: 红测** WEBHOOK_EVENTS 含三项；PATCH assignee → spy 含 assignee_changed(from/to) + updated；未订阅不调用专用；add/remove label → 对应事件；无标签变更不发；不发假 updated
- [ ] **Step 2: 跑测红 → 最小实现绿 → commit**

---

### Task 3 — B：Migration + delivery 账本状态机（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_3700-k7f8a9b0c1d5_webhook_delivery_reliability.py`
  - revision `k7f8a9b0c1d5`；`down_revision = j6e7f8a9b0c4`
  - ADD COLUMN：`delivery_id` String(64) nullable+index；`payload_json` JSON/JSONB nullable；`status` String(32) nullable default `success`；`next_attempt_at` DateTime nullable；`max_attempts` Integer default 5
  - index `(workspace_id, status, next_attempt_at)`
- Modify: `WebhookDeliveryLog` ORM 同步列
- Modify: `backend/tests/conftest.py` — `ADD COLUMN IF NOT EXISTS` 上述列（create_all 存量表）
- Modify: `WorkspaceWebhookService`
  - 常量：`WEBHOOK_DELIVERY_MAX_ATTEMPTS=5`；`RETRY_BACKOFF_MINUTES=[1,5,25,120]`；`RUN_DUE_CAP=100`
  - `_deliver`：按 `envelope.id` 作 `delivery_id`；**一逻辑投递一行**（upsert）；同步短重试仍 `MAX_ATTEMPTS=2`；成功 → `status=success|success_after_retry`、`success=True`、可清 `payload_json`；同步最终失败且 `attempt < max` → `pending_retry` + 存 payload + `next_attempt_at=now+backoff`；`attempt>=max` → `dead`
  - `serialize_delivery` 增：`status`/`nextAttemptAt`/`deliveryId`/`replayable`（`replayable = status in (pending_retry,dead) and payload_json is not None`）；保留 `success`
  - prune：仍按时间/上限简单删最旧（Q5）

**Interfaces:**
- Produces: 扩列模型；失败入队语义

- [ ] **Step 1: 红测** mock httpx 全失败 → log `pending_retry` + payload；成功无 payload（或清空）；attempt 计数
- [ ] **Step 2: 绿 → commit**

---

### Task 4 — C：run-due + replay API（TDD）

**Files:**
- Modify: `backend/opentask/services/workspace_webhook/service.py`
  - `run_due_deliveries(workspace_id)`：扫本 WS `status=pending_retry AND next_attempt_at<=now`，limit 100；逐条用 payload 再投（单次 HTTP 或 `_redeliver`）；失败隔离；返回 `{processed,succeeded,failed,dead,errors[]}`
  - `retry_delivery(workspace_id, webhook_id, delivery_log_id)`：owner 路径外层；无 payload → 400 `delivery_not_replayable`；跨 WS 404；dead/pending 均可；同 `delivery_id` attempt++；立即投
- Modify: `backend/opentask/api/webhooks/router.py`
  - **先**注册 `POST /run-due-deliveries`（member+ = `require_reader`）
  - `POST /{webhook_id}/deliveries/{delivery_log_id}/retry`（owner）
- Extend tests

**Interfaces:**
- Produces: tick + replay 端点

- [ ] **Step 1: 红测** 拨 `next_attempt_at` 过去 + run-due → 再 POST 成功；超限 dead；retry 拉起；无 payload 400；跨 WS 404；viewer run-due 403
- [ ] **Step 2: 绿 → commit**

---

### Task 5 — D：FE 事件 +3 + 投递表状态/重试（TDD）

**Files:**
- Modify: `frontend/src/service/api/webhooks.ts`
  - `WEBHOOK_EVENTS` +3；labels：经办人变更 / 添加标签 / 移除标签
  - `WebhookDelivery` 增 `status?`/`nextAttemptAt?`/`deliveryId?`/`replayable?`
  - `fetchRetryWebhookDelivery(webhookId, deliveryLogId)`；`isDeliveryReplayable(d)` helper
- Modify: `frontend/src/service/api/webhooks.test.ts` — 新事件；replayable 逻辑
- Modify: `frontend/src/views/settings/webhooks/index.vue` — 事件多选自动含新三项；点行打开详情：投递表（状态列、失败/死信筛选、重试按钮、dead 高亮）

- [ ] **Step 1: 红测 vitest → 绿 → commit**

---

### Task 6 — E：CLI **1.28.0**

**Files:**
- Bump：`__init__.py` / `opentask_cli.py` / `setup.py` / `pyproject.toml` → **1.28.0**
- 全仓历史 `1.27.0` version 断言 → `1.28.0`
- Modify: `agent-harness/opentask-cli/opentask/core/webhook.py` — EVENTS +3；`deliveries` / `retry` / `run-due`
- Modify: `api_client.py` — `get_webhook` / `list_webhook_deliveries`（或 get）/ `retry_webhook_delivery` / `run_due_webhook_deliveries`
- Create: `agent-harness/opentask-cli/tests/test_e44_webhook_events_delivery.py`

- [ ] **Step 1: 红测 version/help → 绿 → commit**

---

### Task 7 — F：门禁 + acceptance tip

- [ ] BE 定向 `test_e44*` + 回归 webhooks/E41/E42；全量记 passed（`test_user_search` flake 可记）
- [ ] CLI 全量；FE vitest + build
- [ ] 填 acceptance；最终 tip；**STOP**；不 push；不 E45

---

## Spec coverage
| Design | Task |
|--------|------|
| A 事件包 | T2 |
| B 账本 | T3 |
| C tick/replay | T4 |
| D FE | T5 |
| E CLI 1.28.0 | T6 |
| F 模型/写路径 | T2–T3 |
| ADR/非目标 | Global + T7 |
