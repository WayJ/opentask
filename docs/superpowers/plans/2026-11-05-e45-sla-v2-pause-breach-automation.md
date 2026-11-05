# E45 Plan：SLA v2 thin — pause + breach→automation

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`f6683d2` · 分支 `sprint/E45-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e45-sla-v2-pause-breach-automation-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E46**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** WS 可为 time-in-status 策略配置 `pauseStatuses`；Issue 入 pause 态时钟 `paused` 不计时；离开后续跑并重算 `deadline_at`；`run-due` breach 后 Inbox+webhook+`fire_automations(issue.sla_breached)`；FE pause 多选+徽标+automation 触发；CLI **1.29.0**。

**Architecture:** 扩 `sla_policies.pause_statuses` + `issue_sla_clocks`（`elapsed_before_pause_minutes` / `paused_at` / `segment_started_at`）；`CLOCK_STATUSES+=paused`；`sync_clocks` 优先级 stop>pause>start；`run_due` 仅扫 running，breach 后 fire_automations；TRIGGER_TYPES+=`issue.sla_breached`；复用 ACTION_TYPES。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E46；中文 docs；CLI **1.29.0**
- Q1–Q6 已拍板：`issue.sla_breached`；显式 `segment_started_at`；pause 保留旧 deadline；无 pause timeline；默认 `[]`；允许 set_status + 文档警告
- ADR：stop>pause>start；paused 永不 tick breach；无营业日历/新 metric；无 Redis/cron；formula 不 emit；HMAC 不变
- 非目标见 design §3

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e45-sla-v2-pause-breach-automation.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E45-acceptance.md`（骨架；收口补 tip/测数）

- [x] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：Migration + models + TRIGGER（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_3800-l8a9b0c1d2e6_sla_v2_pause.py`
  - revision `l8a9b0c1d2e6`；`down_revision = k7f8a9b0c1d5`
  - `sla_policies.pause_statuses` JSON/JSONB NOT NULL default `[]`
  - `issue_sla_clocks.elapsed_before_pause_minutes` INT NOT NULL default 0
  - `issue_sla_clocks.paused_at` DateTime NULL
  - `issue_sla_clocks.segment_started_at` DateTime NULL
  - 回填：既有 `status='running'` → `segment_started_at = started_at`
- Modify: `backend/opentask/models/sla/model.py`
  - `CLOCK_STATUSES = ("running","paused","met","breached","cancelled")`
  - `SlaPolicy.pause_statuses` JSON list
  - `IssueSlaClock` 三列
- Modify: `backend/opentask/models/automation/model.py` — `TRIGGER_TYPES` += `"issue.sla_breached"`
- Modify: `backend/tests/conftest.py` — `ADD COLUMN IF NOT EXISTS` 上述列（create_all 存量表）
- Test: `backend/tests/api/test_e45_sla_v2_pause.py`

**Interfaces:**
- Produces: ORM 字段；CLOCK/TRIGGER 常量；迁移可 upgrade

- [x] **Step 1: 红测** `CLOCK_STATUSES` 含 `paused`；`TRIGGER_TYPES` 含 `issue.sla_breached`；policy create 默认 `pauseStatuses==[]`
- [x] **Step 2: 跑测红 → 最小实现绿 → commit**

---

### Task 3 — A/B：Policy CRUD pauseStatuses + serialize clocks（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/service.py`
  - `serialize_policy` += `pauseStatuses`
  - `serialize_clock` += `elapsedBeforePauseMinutes` / `pausedAt` / `segmentStartedAt`
  - `create_policy` / `update_policy` 接受 `pause_statuses` / `pauseStatuses`；`_validate_statuses(..., allow_empty=True)`；默认 `[]`
- Modify: `backend/opentask/api/sla/router.py` — PolicyCreate/Update += `pauseStatuses`
- Extend: `backend/tests/api/test_e45_sla_v2_pause.py`

**Interfaces:**
- Policy JSON：既有字段 + `pauseStatuses: string[]`
- Clock JSON：既有 + `elapsedBeforePauseMinutes:int` / `pausedAt` / `segmentStartedAt`

- [x] **Step 1: 红测** create 带 `pauseStatuses:["feedback"]`；非法 status 400；patch 清空为 `[]`；跨 WS 404；GET issue sla 含新字段
- [x] **Step 2: 绿 → commit**

---

### Task 4 — B：`sync_clocks` pause/resume（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/service.py` → `sync_clocks`
  - 加载活跃钟：`status in ("running","paused")`（每 policy 至多一条）
  - **stop > pause > start**（D3）：
    1. 若 running|paused 且 `_should_stop` → `met` + `stopped_at=now`（保留 elapsed）
    2. 若 running 且 `new_s ∈ pause_statuses` → 累加 elapsed：`elapsed += floor((now - segment_started_at).total_seconds()/60)`（segment 缺省用 `started_at`）；`status=paused`；`paused_at=now`；**不改** `deadline_at`
    3. 若 paused 且 `new_s ∉ pause` 且非 stop → resume：`status=running`；`paused_at=null`；`segment_started_at=now`；`deadline_at = now + timedelta(minutes=max(0, target - elapsed))`
    4. 若 `new_s ∈ start` 且无活跃钟 → 新建 running；设 `segment_started_at=now`；`elapsed=0`
    5. 若已有 paused **不**因 start 另开第二条
  - 新建 running 时始终设 `segment_started_at=now`

**Interfaces:**
- Consumes: policy.pause_statuses；Produces: paused/running 状态机

- [x] **Step 1: 红测**
  - in_progress→feedback → paused；elapsed>0；run-due 不 breach paused（即使 deadline 过去）
  - feedback→in_progress → running；deadline ≈ now+(target-elapsed)
  - paused→resolved → met
  - running→resolved 仍 met（无 pause 配置回归）
  - stop 优先于 pause（stop 态同时在 pause 列表 → met）
- [x] **Step 2: 绿 → commit**

---

### Task 5 — C：`run_due` → `fire_automations`（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/service.py` → `run_due`
  - 扫描条件仍仅 `status=='running' AND deadline_at<=now`
  - 标 breached + Inbox + webhook **之后**：
    ```python
    try:
        await fire_automations(
            self.db,
            workspace_id=workspace_id,
            trigger_type="issue.sla_breached",
            issue=issue,
            actor_user_id=None,
            event={
                "policyId": policy.id,
                "policyName": policy.name,
                "deadlineAt": ...,
                "breachedAt": ...,
                "clockId": clock.id,
            },
        )
    except Exception as auto_err:
        logger.exception(...); errors.append(...)
    ```
  - 失败不回滚 breach；幂等：已 breached 不再扫
- Docs 警告：automation 帮助/FE 文案注明 `set_status` 可能绕回 start 造成震荡（Q6）

**Interfaces:**
- Consumes: `fire_automations`；Produces: breach 路径 automation 一次火

- [x] **Step 1: 红测** breach → automation spy 含 `issue.sla_breached`；set_priority 落地；再 run-due 不双火；automation 异常记 errors 但 clock 仍 breached
- [x] **Step 2: 绿 → commit**

---

### Task 6 — D：FE pause 多选 + 徽标 + automation 触发（TDD）

**Files:**
- Modify: `frontend/src/service/api/sla.ts`
  - `SlaClockStatus` += `'paused'`
  - `SlaPolicyRow.pauseStatuses`；create/update body
  - `SlaClockRow` += elapsed/pausedAt/segmentStartedAt
  - `slaBadgeType('paused') → 'warning'`（琥珀色）
  - `formatSlaPaused(elapsed, target)` → `已暂停 · 已用 X / 目标 Y`
- Modify: `frontend/src/service/api/sla.test.ts` — pauseStatuses 类型；badge paused；formatSlaPaused
- Modify: `frontend/src/views/settings/sla/index.vue` — 多选「暂停计时的状态」+ 帮助文案；列表展示 pause
- Modify: `frontend/src/views/issue/detail/index.vue` — paused 徽标「已暂停」+ formatSlaPaused
- Modify: `frontend/src/service/api/automations.ts` — `AutomationTrigger` += `'issue.sla_breached'`
- Modify: `frontend/src/service/api/automations.test.ts` — 常量含新 trigger
- Modify: `frontend/src/views/workspace/automations/index.vue` — triggerOptions += `{ label: 'SLA 违约 (issue.sla_breached)', value: 'issue.sla_breached' }`；旁注 set_status 警告

- [x] **Step 1: 红测** vitest badge/format/trigger
- [x] **Step 2: 绿 → commit**

---

### Task 7 — E：CLI **1.29.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/sla.py`
  - `policy create|update` += `--pause` multiple；body `pauseStatuses`
  - list 表增 Pause 列；issue 输出 paused 字段
- Modify: `agent-harness/opentask-cli/opentask/core/automation.py` — `TRIGGERS` += `issue.sla_breached`
- Modify: `__init__.py` / `opentask_cli.py` / `setup.py` → **1.29.0**
- 全仓历史 `1.28.0` version 断言 → `1.29.0`
- Create: `agent-harness/opentask-cli/tests/test_e45_sla_v2.py`

- [x] **Step 1: 红测** version 1.29.0；`--pause` help；TRIGGERS 含 issue.sla_breached
- [x] **Step 2: 绿 → commit**

---

### Task 8 — 门禁 + acceptance tip

- [x] BE 定向 `test_e45_*` + `test_e42_*` + 相关；全量（记 passed；`test_user_search` flake 可记 Gaps）
- [x] CLI 全量；FE vitest + build
- [x] 填写 acceptance；最终 tip commit
- [x] **STOP**；不 push；不自开 E46

---

## Self-Review
1. Spec A–F / 验收 A–H / ADR D1–D10 均有 Task 覆盖  
2. 无 TBD/placeholder  
3. Q1–Q6 落入 Global Constraints + 任务语义；migration id `l8a9b0c1d2e6` / down `k7f8a9b0c1d5` 对齐 design
