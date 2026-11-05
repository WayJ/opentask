# E38 Plan：Automation delayed / scheduled actions

日期：2026-11-04（Asia/Shanghai）  
基线 tip：`9e8ce90` · 分支 `sprint/E38-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-04-e38-automation-delayed-actions-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E39**。

**Goal:** 规则可配 `delay_minutes`；匹配后入队 `automation_pending_actions`；外部 `POST /api/automations/run-due` 到期执行；FE/CLI 1.22.0。

**Architecture:** 对齐 E35 外部 tick。delay 存于 `action_config`；`run_for_event` 分流即时/`INSERT pending`；`run_due` 重评 condition 后用快照 `_execute_action`；disable→cancel pending。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3/Naive；Click CLI；pytest/vitest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E39；中文 docs；CLI **1.22.0**；UTC naive；无内置 cron；非目标见 design §7。

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-04-e38-automation-delayed-actions.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-04-E38-acceptance.md`（骨架；收口补 tip/测数）

- [x] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：Model + Migration + 入队分流 + 校验 + disable→cancel（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_04_3100-e1f2a3b4c5d9_automation_pending_actions.py`
- Modify: `backend/opentask/models/automation/model.py`（`AutomationPendingAction` + PENDING_STATUSES）
- Modify: `backend/opentask/models/automation/__init__.py`、`backend/opentask/models/__init__.py`
- Modify: `backend/opentask/services/automation/service.py`
  - `_parse_delay_minutes` / `_strip_delay` / `_validate_action_config`
  - create/update 调 delay 校验
  - `run_for_event`：delay≥1 → enqueue（去重）；0 → 即时 `_execute_action`
  - `_execute_action(..., config_override=None)`
  - `set_enabled(False)` / `update(enabled=False)` → cancel pending
  - `enqueue_pending` / `cancel_pending_for_rule` / `list_pending` / `run_due`
- Test: `backend/tests/api/test_e38_automation_delayed_actions.py`

**Interfaces:**
- Consumes: `AutomationRule`、`_match_trigger`、`_match_condition`、`_execute_action`、E35 run-due 风格
- Produces:
  - `AutomationPendingAction` 表字段见 design §A
  - `AutomationService.run_due(workspace_id, actor_user_id, now=None) -> {processed,executed,cancelled,failed,errors[]}`
  - `AutomationService.list_pending(workspace_id, status="pending", limit=100)`
  - delay helpers: `parse_delay_minutes(cfg) -> int`（0=即时）；非法 raise 400

- [x] **Step 1: 红测** — 写 `test_e38_automation_delayed_actions.py`：
  - `delay_minutes` 缺省/0 → 即时执行（回归 set_priority）
  - `delay_minutes=5` → 不立即改 issue；DB 有 pending；`run_at` ≈ now+5m
  - 非法 delay（-1 / 10081 / "x"）create → 400
  - 同 rule+issue 二次触发不双写 pending
  - disable 规则 → pending.status=cancelled
  - camel `delayMinutes` 亦接受
- [x] **Step 2: 跑测确认红**
- [x] **Step 3: 最小实现绿**
  - Model + migration（indexes `(workspace_id,status,run_at)`、`(rule_id,issue_id,status)`）
  - validate + enqueue + strip delay from snapshot
  - `_execute_action` 支持 `config_override`
- [x] **Step 4: 相关测绿并 commit**

---

### Task 3 — B：`POST /api/automations/run-due` + `GET /pending`（TDD）

**Files:**
- Modify: `backend/opentask/api/automations/router.py`（**在 `/{rule_id}` 之前**注册 `/run-due` 与 `/pending`）
- Modify: `backend/opentask/services/automation/service.py`（`run_due` / `list_pending` / serialize_pending）
- Extend: `backend/tests/api/test_e38_automation_delayed_actions.py`

**Interfaces:**
- `POST /api/automations/run-due` → member+；强制 X-Workspace-Id；仅当前 WS
- Response: `{processed, executed, cancelled, failed, errors:[{pendingId,ruleId,issueId,message}]}`
- `GET /api/automations/pending?status=pending` → `{rows,total}` limit 100
- Per pending: rule missing/disabled → cancelled；issue gone/wrong WS → cancelled；重评 condition 不匹配 → cancelled；else execute snapshot → done|failed；失败隔离

- [x] **Step 1: 红测**
  - 未到期 run-due → processed 含行但不 executed（或 skipped 计 processed 且不改 issue）——按 design：仅选 `run_at<=now`，故未到期不入选 processed=0
  - 到期 → 执行 set_status / add_comment / set_priority；pending=done
  - 条件失效 → cancelled
  - rule disable 后 tick → cancelled
  - 人为失败隔离（一条 failed 不影响另一条）
  - viewer run-due 403；跨租户不泄漏
- [x] **Step 2: 红确认 → 实现绿 → commit**

---

### Task 4 — C：FE delay 控件 + 摘要

**Files:**
- Modify: `frontend/src/service/api/automations.ts`（`getDelayMinutes` / `withDelayMinutes` / `summarizeAutomationRule` 含 delay）
- Modify: `frontend/src/service/api/automations.test.ts`
- Modify: `frontend/src/views/workspace/automations/index.vue`（延迟分钟输入；写入 actionConfig；列表摘要）

- [x] **Step 1: 红测** helpers：withDelayMinutes(0) 剥离；>0 写 delay_minutes；summarize 含 `delay 60m →`
- [x] **Step 2: 实现绿**；表单 `delayMinutes` NInputNumber 0…10080；watch 合并进 actionConfigText（保留其它键）
- [x] **Step 3: vitest 绿并 commit**

---

### Task 5 — D：CLI **1.22.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/automation.py`（`run-due`、可选 `pending`；create help 示例含 delay_minutes）
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（`run_due_automations` / `list_automation_pending`）
- Modify: version → **1.22.0**：`opentask/__init__.py`、`opentask_cli.py`、`setup.py`、`pyproject.toml`；**全仓**历史 `1.21.0` 断言同步
- Create: `agent-harness/opentask-cli/tests/test_e38_automation_delayed.py`

- [x] **Step 1: 红测** version / `automation run-due --help` / pending help
- [x] **Step 2: 实现 + bump → 绿 → commit**

---

### Task 6 — 门禁 + acceptance

- [x] BE 全量 pytest（记录 passed/skip；`test_user_search` flake 可文档化）
- [x] CLI 全量；FE vitest + build
- [x] 填 acceptance tip/测数；`superpowers: design/plan/TDD/verify/acceptance = ok`
- [x] **STOP**；不 push；不自开 E39

## ADR（对齐 design §9）
| ID | 决定 |
|----|------|
| D1 | 表 `automation_pending_actions`；delay 在 action_config |
| D2 | 无内置 cron；外部 run-due；UTC naive |
| D3 | delay ∈ 0…10080；非法 400；0/缺省=即时 |
| D4 | 同 (rule_id,issue_id) 仅一条 pending |
| D5 | tick 重评 condition + enabled |
| D6 | 执行用入队快照（去 delay） |
| D7 | 防环 depth 不变；run-due depth=0 |
| D8 | 每条 due 每 tick 最多 1 次 |
| D9 | CLI 1.22.0 |
| D10 | 非目标 §7；不 push；不自开 E39 |

## Spec coverage
- §A 入队/校验/去重/disable→cancel → Task2
- §B run-due + pending list → Task3
- §C FE → Task4
- §D CLI → Task5
- §7 非目标 — 不实现
