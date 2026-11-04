# E48 Plan：SLA first-response metric + pause timeline · CLI 1.32.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`88ea4e8` · 分支 `sprint/E48-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e48-sla-first-response-pause-timeline-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E49**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** WS 可配置 `metric=first_response` SLA（与 `time_in_status` 并存）；非创建者首条 comment → 时钟 met；pause/resume 写 `sla_paused`/`sla_resumed` timeline（不 fire webhook/automation）；breach payload 增 `metric`；FE/CLI **1.32.0**；无 migration / 无营业日历。

**Architecture:** 扩 `SLA_METRICS`；复用 `issue_sla_clocks`；`sync_clocks` 处理全部 enabled policies（去掉仅 `time_in_status` 过滤）并在 pause/resume 同事务 append timeline；`add_comment` 后调 `mark_first_response`；`run_due` payload +`metric`；FE 文案；CLI 钉 **1.32.0**。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E49；中文 docs；CLI **1.32.0**
- Q1–Q6 已拍板：Q1a 非创建者首评；Q2b assignee 不算；Q3a pause 仅 timeline；Q4a 同 start/stop/pause 集；Q5a 双 metric OK；Q6a **无 migration**
- ADR：stop>pause>start；paused 永不 tick breach；无营业日历/策略优先级；formula 永不 emit；HMAC 不变
- PG `timeline_action` ENUM：无 alembic；`conftest` `ALTER TYPE … ADD VALUE IF NOT EXISTS` 保测试（Gaps 记生产需同语句）
- 非目标见 design §3

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e48-sla-first-response-pause-timeline.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E48-acceptance.md`（骨架；收口补 tip/测数）

- [x] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — TimelineAction + pause/resume 写审计（TDD）

**Files:**
- Modify: `backend/opentask/models/issue/enums.py` — `SLA_PAUSED = "sla_paused"` / `SLA_RESUMED = "sla_resumed"`
- Modify: `backend/opentask/models/issue/model.py` — `IssueTimeline.action_type` ENUM 字面量加两值
- Modify: `frontend/src/typings/api/issue.d.ts` — 同步枚举
- Modify: `backend/tests/conftest.py` — `ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS` ×2（无 alembic）
- Modify: `backend/opentask/services/sla/service.py` → `sync_clocks`
  - 去掉 `SlaPolicy.metric == "time_in_status"` 过滤（改扫全部 enabled）
  - running→paused：flush 后 `IssueTimeline(action_type=sla_paused, action_data={policyId,policyName,metric,elapsedBeforePauseMinutes,fromStatus,toStatus})`；**不**调 fire_webhooks/fire_automations
  - paused→running：`sla_resumed` payload `{policyId,policyName,metric,remainingMinutes,newDeadlineAt,fromStatus,toStatus}`
  - stop/met/breach/cancel 路径不写 pause 类 timeline
- Test: `backend/tests/api/test_e48_sla_first_response.py`

**Interfaces:**
- Produces: TimelineAction 两值；sync_clocks 对所有 metric 写 pause 审计

- [ ] **Step 1: 红测**
  - `TimelineAction.SLA_PAUSED.value == "sla_paused"`
  - time_in_status 策略：in_progress→feedback → timeline 含 `sla_paused`；payload 含 metric/policyId；spy `fire_webhooks`/`fire_automations` **未**因 pause 调用
  - feedback→in_progress → `sla_resumed`；resolved → met **无**额外 pause 类条
- [ ] **Step 2: 跑红 → 最小实现绿 → commit**

---

### Task 3 — A：`first_response` metric 启停/met/breach（TDD）

**Files:**
- Modify: `backend/opentask/models/sla/model.py` — `SLA_METRICS = ("time_in_status", "first_response")`
- Modify: `backend/opentask/services/sla/service.py`
  - `serialize_clock(..., metric=None)` += `"metric": metric`
  - `list_issue_clocks` outerjoin 取 `SlaPolicy.metric`
  - 新方法 `async def mark_first_response(*, issue: Issue, actor_user_id: str) -> None`：
    - creator = `issue.created_by or issue.reporter_id`；若 `actor_user_id == creator` → return
    - 查该 issue 上 enabled `metric=="first_response"` 且 clock `status in (running,paused)` → `status=met`；`stopped_at=now`
    - 同 workspace；不 fire webhook/automation
  - `run_due` webhook `data` + automation `event` 均加 `"metric": policy.metric`
- Modify: `backend/opentask/services/issue_service.py` → `add_comment`：commit 前（timeline 后）若拿到 issue，调用 `await SlaService(self.db).mark_first_response(issue=issue, actor_user_id=user_id)`（需在 commit 前加载 issue；若当前在 commit 后加载，改为 commit 前 get + mark，再 commit 一次或合并）
  - 实现要点：在 `_add_timeline` 后、`commit` 前 `get_issue` + `mark_first_response`，再统一 commit
- Modify: `backend/opentask/api/issue/router.py` serialize 传 metric
- Extend: `backend/tests/api/test_e48_sla_first_response.py`

**Interfaces:**
- Consumes: TimelineAction；Produces: first_response 启停/met；breach metric 字段

- [ ] **Step 1: 红测**
  - create `metric=first_response` OK；非法 metric 400；与 time_in_status 同 WS 并存
  - Issue → in_progress：两策略各一 running 钟
  - 创建者自评 → first_response 仍 running；他评 → met + stopped_at
  - assignee 变更 → first_response 仍 running
  - 超时 running → run-due breach；webhook/automation spy payload 含 `metric`
  - paused first_response 不被 run-due breach
  - 跨租户：他 WS 评论/策略不可见
  - Feed/activity 可读 `sla_paused`；读路径 spy 无 formula emit（patch evaluate 或既有 emit 入口）
- [ ] **Step 2: 绿 → commit**

---

### Task 4 — C：FE 设置/徽标/文案（TDD）

**Files:**
- Modify: `frontend/src/service/api/sla.ts` — `SLA_METRICS`；`metricLabel`；`fetchCreate/Update` body += `metric`；`SlaClockRow.metric?`；`slaMetricBadgePrefix(metric)` → `首响 SLA` / `状态 SLA`
- Modify: `frontend/src/service/api/sla.test.ts`
- Modify: `frontend/src/views/settings/sla/index.vue` — metric 下拉「首次响应」+ 帮助：非创建者首评算首响；指派不算
- Modify: `frontend/src/views/issue/detail/index.vue` — 徽标前缀区分 first_response
- Modify: `frontend/src/utils/formatTimelineAction.ts` — `sla_paused` / `sla_resumed` 文案
- Modify: `frontend/src/utils/formatTimelineAction.test.ts`
- Modify: `frontend/src/utils/activityFeed.ts` — ACTIVITY_ACTION_OPTIONS += 两动作
- Modify: `frontend/src/views/workspace/automations/index.vue` — sla_breached 帮助注明含 first_response
- Modify: `frontend/src/typings/api/issue.d.ts` — TimelineAction 两值

- [ ] **Step 1: 红测** vitest metric 标签 / timeline 文案 / badge 前缀
- [ ] **Step 2: 绿 → commit**

---

### Task 5 — D：CLI **1.32.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/sla.py` — `--metric` on create/update；list 表 Metric 列；issue 表 Metric 列；help 示例
- Modify: `opentask/__init__.py` / `opentask_cli.py` / `setup.py` / `pyproject.toml` → **1.32.0**；Create `VERSION` 文件 `1.32.0`
- 全仓历史 `1.31.0` version 断言 → `1.32.0`
- Create: `agent-harness/opentask-cli/tests/test_e48_sla_first_response.py`

- [ ] **Step 1: 红测** version 1.32.0；create help 含 `--metric` / `first_response`
- [ ] **Step 2: 绿 → commit**

---

### Task 6 — 门禁 + acceptance tip

- [ ] BE 定向 `test_e48_*` + `test_e45_*` + `test_e42_*`；全量（记 passed；`test_user_search` flake 可记 Gaps）
- [ ] CLI 全量；确认所有 pin **1.32.0**
- [ ] FE vitest + build
- [ ] 填写 acceptance；最终 tip commit
- [ ] **STOP**；不 push；不自开 E49

---

## Self-Review
1. Spec A–E / 验收 A–H / ADR D1–D9 均有 Task 覆盖  
2. 无 TBD/placeholder  
3. Q1–Q6 落入 Global Constraints；无 alembic migration（Q6a）；conftest ENUM ADD VALUE 保测
