# E51 Plan：专用 webhook pack + 订阅事件过滤 FE · CLI 1.35.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`38bd9c6` · 分支 `sprint/E51-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e51-webhook-pack-subscription-filter-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E52**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** 出站 webhook 可订阅专用 `issue.cycle_changed` / `issue.estimate_changed` / `issue.project_changed` / `issue.sla_paused` / `issue.sla_resumed`；与 `issue.updated` 并存；FE 勾选+「集成常用」预设+投递日志按事件过滤；CLI **1.35.0**（含 `webhook events`）。

**Architecture:** 扩 `WEBHOOK_EVENTS` 白名单；`issue_service.update_issue` 在 cycle/estimate/project 实际变更旁路 **额外** `fire_webhooks`（仍发 `issue.updated`）；`SlaService.sync_clocks` pause/resume 在写 timeline 后 **额外** fire 专用 webhook（仍不 fire automation）；FE 扩枚举/标签/预设/投递过滤 helpers；CLI 钉 1.35.0 + `webhook events`。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E52；中文 docs；CLI **1.35.0**
- Q1a 含 `sla_resumed`；Q2a 不替代 `issue.updated`；Q3a 要「集成常用」；Q4a 必须 `project_changed`；Q5a 不做回放；Q6a 要 `webhook events`
- ADR D1–D7；E40 formula **永不** emit；HMAC/重试不变；无 Redis/cron；无 Activity 加厚；无节假日
- 非目标见 design §2
- E48「pause timeline only — no webhook」被本 Epic **有意覆盖**：本轮加 webhook，仍不加 automation

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e51-webhook-pack-subscription-filter.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E51-acceptance.md`（骨架；收口补 tip/测数）

- [x] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A+B：WEBHOOK_EVENTS +5 + 写路径 fire（TDD）

**Files:**
- Modify: `backend/opentask/models/workspace_webhook/model.py` — `WEBHOOK_EVENTS` +=  
  `issue.cycle_changed` / `issue.estimate_changed` / `issue.project_changed` / `issue.sla_paused` / `issue.sla_resumed`
- Modify: `backend/opentask/services/issue_service.py` — `update_issue`：捕获  
  `cycle_changed=(from,to)|None`、`estimate_changed=(from,to)|None`、`project_changed=(from,to)|None`（与 timeline 同条件）；commit 后在 `issue.updated` 旁 **额外** `fire_webhooks` 专用事件；payload `{id,issueCode,title,from,to,actorUserId}`
- Modify: `backend/opentask/services/sla/service.py` — pause / resume 写 timeline 后 `await fire_webhooks(...)`：  
  - `issue.sla_paused`：`{id,issueCode,title,policyId,policyName,metric,fromStatus,toStatus,elapsedBeforePauseMinutes,actorUserId:null}`  
  - `issue.sla_resumed`：`{id,issueCode,title,policyId,policyName,metric,fromStatus,toStatus,remainingMinutes,newDeadlineAt,actorUserId:null}`  
  - **不** `fire_automations`；更新 E48 旁注为「E51: webhook；仍无 automation」
- Test: `backend/tests/api/test_e51_webhook_pack_subscription_filter.py`

**Interfaces:**
- Produces: 五事件可订阅；cycle/estimate/project 双发；pause/resume 专用；未订阅不投

- [x] **Step 1: 红测**（见下方测试骨架）
- [x] **Step 2: 跑红 → 最小实现绿 → commit**

测试骨架要点：
```python
def test_webhook_events_include_e51_pack():
    for ev in (
        "issue.cycle_changed",
        "issue.estimate_changed",
        "issue.project_changed",
        "issue.sla_paused",
        "issue.sla_resumed",
    ):
        assert ev in WEBHOOK_EVENTS

# create webhook with 5 events → 200
# PATCH cycle_id → spy types 含 issue.cycle_changed + issue.updated；data.from/to
# 同理 estimate_points / project_id
# 未订阅专用事件：hook 仅 issue.updated → dispatch 无专用 event_type
# SLA：policy pauseStatuses=["feedback"]；in_progress→feedback → issue.sla_paused；再→in_progress → issue.sla_resumed
# 断言无 fire_automations(sla_paused/resumed)
# formula no-emit：patch CustomFieldService.refresh_formula_cache 旁路外，spy 写路径不意外 emit formula 物化（沿用既有「配置/字段写」spy 风格：断言未调用不存在的 formula emit）
# 非法事件名 create → 400
# 跨租户：他 WS hook 收不到本 WS 事件（dispatch 按 workspace_id）
```

---

### Task 3 — D：FE labels / 预设 / 投递过滤（TDD）

**Files:**
- Modify: `frontend/src/service/api/webhooks.ts`
  - `WEBHOOK_EVENTS` +5
  - labels：`Cycle 变更` / `估点变更` / `项目变更` / `SLA 暂停` / `SLA 恢复`
  - `INTEGRATION_PRESET_EVENTS` = cycle/estimate/project/sla_paused/sla_resumed
  - `applyIntegrationPreset(current: string[]): string[]` — 并集去重
  - `clearIntegrationPreset(current: string[]): string[]` — 去掉预设集
  - `filterDeliveriesByEvent(list, eventType: string | 'all')` — `'all'` 不过滤
- Modify: `frontend/src/service/api/webhooks.test.ts` — 新事件/标签/预设/过滤
- Modify: `frontend/src/views/settings/webhooks/index.vue`
  - 「集成常用」按钮调用 `applyIntegrationPreset`；可「清除预设」
  - 投递详情：`eventFilter` 下拉（全部 + WEBHOOK_EVENTS）；`filteredDeliveries` 叠 statusFilter + eventFilter

- [x] **Step 1: 红测 vitest → 绿 → commit**

---

### Task 4 — E：CLI **1.35.0** + `webhook events`

**Files:**
- Bump：**全部** `1.34.0` → `1.35.0`：  
  `pyproject.toml` / `opentask/__init__.py` / `setup.py` / `VERSION` / `opentask/opentask_cli.py` `VERSION` + 全仓历史 version 断言
- Modify: `agent-harness/opentask-cli/opentask/core/webhook.py` — `EVENTS` +5；新增：
  ```python
  @webhook_cli.command(name="events")
  @click.option("--json", "as_json", is_flag=True)
  @click.pass_obj
  def webhook_events(obj, as_json):
      """列出允许订阅的 webhook 事件名。"""
      ...
  ```
  create help 文案可指向 `webhook events`
- Create: `agent-harness/opentask-cli/tests/test_e51_webhook_pack.py`

- [x] **Step 1: 红测 version / events 子命令 / EVENTS 含五名 → 绿 → commit**

---

### Task 5 — F：门禁 + acceptance tip

- [x] BE 定向 `test_e51*` + 回归 `test_e44*` / `test_e48*` / `test_e41*`；全量记 passed（`test_user_search` flake 可记）
- [x] CLI 全量；确认 pins 全 **1.35.0**
- [x] FE vitest + `npm run build`
- [x] 填 acceptance；最终 tip；**STOP**；不 push；不 E52

---

## Spec coverage
| Design | Task |
|--------|------|
| A 事件包 + fire | T2 |
| B 订阅过滤 FE | T3 |
| C CLI 1.35.0 | T4 |
| D 安全/no-emit | T2 + T5 |
| ADR/非目标 | Global + T5 |
| Q1a–Q6a | T2–T4 |
