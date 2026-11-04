# E39 Plan：Due reminders + digest tick

日期：2026-11-04（Asia/Shanghai）  
基线 tip：`019e552` · 分支 `sprint/E39-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-04-e39-due-reminders-digest-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E40**。

**Goal:** 外部 `POST /api/inbox/run-due-reminders` 对 soon/overdue Issue 向 assignee∪watchers 投递 Inbox；可选日 digest；FE 两开关；CLI **1.23.0**。

**Architecture:** 对齐 E35/E38 外部 tick。偏好列 `due_reminder`/`due_reminder_digest` + 账本表 `due_reminder_deliveries` 幂等；`NotificationService.run_due_reminders` 扫本 WS 开放 due Issue，按偏好 create（走 E30 邮件钩）；无内置 cron。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3/Naive；Click CLI；pytest/vitest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E40；中文 docs；CLI **1.23.0**；UTC naive / UTC date；LEAD_DAYS=3；无内置 cron；非目标见 design §7。
- `due_reminder` 进 `PREF_KEYS`（默认 true）；`due_reminder_digest` 为模式列（默认 false，类 email_enabled）。
- `TYPE_TO_PREF_KEY`：`due_reminder`→`due_reminder`；`due_reminder_digest`→`due_reminder`。
- create 时 `actor_user_id=None`（避免 tick 调用者自跳过）。

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-04-e39-due-reminders-digest.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-04-E39-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：prefs 列 + deliveries 表 + PREF/TYPE 映射（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_04_3200-f2a3b4c5d6e0_due_reminder_prefs_deliveries.py`
  - revision `f2a3b4c5d6e0`；down_revision `e1f2a3b4c5d9`
  - `notification_preferences` +`due_reminder` bool default true；+`due_reminder_digest` bool default false
  - 建表 `due_reminder_deliveries`（字段见 design §A）
  - 唯一：应用层先查 + 部分唯一索引（dialect where kind=…）；索引 `(workspace_id,bucket_date)`、`(user_id,bucket_date)`
- Create: `backend/opentask/models/due_reminder_delivery/model.py` + `__init__.py`
- Modify: `backend/opentask/models/__init__.py` 导出 `DueReminderDelivery`
- Modify: `backend/opentask/models/notification_preference/model.py`
  - `PREF_KEYS` += `"due_reminder"`
  - `TYPE_TO_PREF_KEY` += `due_reminder`/`due_reminder_digest` → `due_reminder`
  - 列 `due_reminder`（default True）、`due_reminder_digest`（default False）
- Modify: `backend/opentask/services/notification/service.py`
  - `serialize_prefs` / `default`：含 `due_reminder_digest=False`（`due_reminder` 经 PREF_KEYS）
  - `upsert_prefs`：处理 `due_reminder_digest`（同 email_enabled）
- Modify: `backend/opentask/api/inbox/router.py` — `PrefsBody` + put 更新 `due_reminder_digest`
- Test: `backend/tests/api/test_e39_due_reminders.py`

**Interfaces:**
- Consumes: `NotificationPreference`、`NotificationService.get_prefs_payload`/`upsert_prefs`
- Produces:
  - `DueReminderDelivery` 字段：id, workspace_id, issue_id(nullable), user_id, kind∈{soon,overdue,digest}, bucket_date, due_date_bucket(nullable), notification_id(nullable), created_at
  - prefs JSON 含 `due_reminder`（默认 true）、`due_reminder_digest`（默认 false）

- [ ] **Step 1: 红测** prefs GET 默认含两键；PUT 可改；TYPE 映射存在（`is_type_enabled` 对 due_reminder 尊开关）
- [ ] **Step 2: 跑测确认红** → 最小实现绿 → commit

---

### Task 3 — B：`POST /api/inbox/run-due-reminders` + deliveries list（TDD）

**Files:**
- Modify: `backend/opentask/services/notification/service.py`
  - `LEAD_DAYS = 3`
  - `CLOSED_STATUSES = {closed, resolved, rejected}`
  - `run_due_reminders(workspace_id, actor_user_id=None, today=None) -> dict`
  - `list_due_reminder_deliveries(workspace_id, bucket_date=None, limit=100)`
  - helpers: `_issue_due_date`, `_recipients`, `_already_delivered_*`, `_insert_delivery`, `_format_digest_body`
- Modify: `backend/opentask/api/inbox/router.py`
  - **在 `/{notification_id}` 路由之前**注册：
    - `POST /run-due-reminders` member+（`require_writer`）；强制 WS
    - `GET /due-reminder-deliveries?bucket_date=&limit=100` member+
  - 从 `opentask.services.automation.service` 复用 `require_writer`（或本地同款）
- Extend: `backend/tests/api/test_e39_due_reminders.py`

**Interfaces:**
- Response: `{processedIssues, remindersCreated, digestsCreated, skipped, errors:[{issueId,userId,kind,message}]}`
- Tick 语义见 design §B 伪代码；actor_user_id 创建通知时传 **None**
- Digest：同日已有 digest 账本 → 本 tick 不改写
- 失败隔离；viewer 403；跨 WS 不扫

- [ ] **Step 1: 红测**
  - soon 窗内 assignee+watcher 各 1 条 due_reminder
  - closed/resolved/rejected 不投；无收件人 skip
  - 二次 tick 不双投；改 due（due_date_bucket 变）可再 soon
  - overdue 同日不双投；次日可再投（换 bucket_date）
  - digest=true → 多 Issue 仅 1 条 due_reminder_digest；due_reminder=false 全跳过
  - viewer 403；跨租户不泄漏；单条失败隔离
  - email_enabled + mock transport 时 create 触发邮件
- [ ] **Step 2: 红确认 → 实现绿 → commit**

---

### Task 4 — C：FE 通知设置两开关 + Inbox 标签

**Files:**
- Modify: `frontend/src/service/api/notif-prefs.ts`
  - `NOTIF_PREF_KEYS` += `due_reminder`
  - 模式键：`due_reminder_digest`（与 email_enabled 并列）
  - labels：`到期提醒`；helper `isDigestToggleDisabled(prefs)` = !due_reminder
  - `mergeNotifPrefs` 默认 due_reminder=true、digest=false
- Modify: `frontend/src/service/api/notif-prefs.test.ts`
- Modify: `frontend/src/views/settings/notifications/index.vue`
  - 独立卡片「到期提醒」：开关 due_reminder；digest 开关（reminder 关时 disabled）
  - 短说明：UTC；soon=今日起 3 日；逾期每日至多一条；邮件受 email_enabled
  - 主列表循环可排除 `due_reminder`（避免重复），或保留在类型列表 — **采纳：单独卡片，循环排除 due_reminder**
- Modify: `frontend/src/views/inbox/index.vue` — typeLabel 补 `due_reminder`/`due_reminder_digest`

- [ ] **Step 1: 红测** merge/defaults/isDigestToggleDisabled
- [ ] **Step 2: 实现绿**；vitest 绿 → commit

---

### Task 5 — D：CLI **1.23.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/notif.py`
  - PREF_KEYS += `due_reminder`、`due_reminder_digest`
  - `notif run-due-reminders`；可选 `notif due-deliveries`
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py` — `run_due_reminders` / `list_due_reminder_deliveries`
- Bump **1.23.0**：`opentask/__init__.py`、`opentask_cli.py`、`setup.py`、`pyproject.toml`；**全仓**历史 `1.22.0` 断言 → `1.23.0`
- Create: `agent-harness/opentask-cli/tests/test_e39_due_reminders.py`

- [ ] **Step 1: 红测** version / `notif run-due-reminders --help` / prefs keys
- [ ] **Step 2: 实现 + bump → 绿 → commit**

---

### Task 6 — 门禁 + acceptance

- [ ] BE：`pytest backend/tests/api/test_e39_due_reminders.py -q` 绿；全量 `pytest backend/tests -q`（记录 passed；`test_user_search` flake 可记 gaps）
- [ ] CLI：`pytest agent-harness/opentask-cli/tests -q` 绿
- [ ] FE：`cd frontend && npx vitest run && npm run build` 绿
- [ ] 写满 `docs/superpowers/acceptances/2026-11-04-E39-acceptance.md`（tip SHA、测数、ADR、非目标）
- [ ] 最终 tip commit；**不 push**；**不自开 E40**；回执含 `superpowers: design/plan/TDD/verify/acceptance = ok`

---

## Self-review
- Spec A–D / ADR D1–D10 均有对应任务
- 无 TBD；actor=None 防自跳过已写明
- 路由注册顺序：静态 path 先于 `/{notification_id}`
