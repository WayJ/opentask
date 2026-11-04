# E41 Plan：Issue audit & outbound signals

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`bf86c23` · 分支 `sprint/E41-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e41-issue-audit-outbound-signals-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E42**。

**Goal:** Issue 写路径把 CF / cycle / estimate / project 变更写入 `issue_timeline`；单 Issue + WS 级 timeline CSV export；出站 Webhook 可订阅 `issue.custom_field_changed`；FE 活动文案/导出/事件多选；CLI **1.25.0**。

**Architecture:** 扩展 `TimelineAction`/PG enum +4；CF upsert 同事务按 `changes[]` 写 timeline，emit 旁路 `fire_webhooks`（每字段一条）；`IssueService.update_issue` 对称写 cycle/estimate/project；两个 CSV 路由复用 list ACL + 硬顶 10000 + `X-OpenTask-Truncated`；CLI/FE 跟进。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3/Naive；Click CLI；pytest/vitest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E42；中文 docs；CLI **1.25.0**
- formula 永不写 timeline / 永不发 webhook（E40 D7）
- timeline 写入与现有 status/priority **同事务**（非 fire-and-forget）
- CF timeline + webhook 均基于 E36 `changes[]`；**每字段一条**；事件名 `issue.custom_field_changed`
- export 硬顶 **10000**；截断响应头 `X-OpenTask-Truncated: true`（仍 200）
- action_data 过长值截断至 ~2KB/字段
- 非目标见 design §7

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e41-issue-audit-outbound-signals.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E41-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：Migration + TimelineAction + update_issue / CF upsert 写 timeline（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_3400-h4c5d6e7f8a2_issue_timeline_audit_actions.py`
  - revision `h4c5d6e7f8a2`；down_revision `g3b4c5d6e7f1`
  - PG：对四值逐条 `ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS '…'`（`commit_as_you_go` / 独立 autocommit 按仓内 PG 惯例；SQLite no-op）
- Modify: `backend/opentask/models/issue/enums.py` — `TimelineAction` +=  
  `CUSTOM_FIELD_CHANGED` / `CYCLE_CHANGED` / `ESTIMATE_CHANGED` / `PROJECT_CHANGED`
- Modify: `backend/opentask/models/issue/model.py` — `IssueTimeline.action_type` ENUM 字面量列表同步 +4（SQLite `create_all` 用）
- Modify: `backend/opentask/services/issue_service.py`
  - `update_issue`：在现有 status/priority/due/assignee 块旁，对 `cycle_id` / `estimate_points` / `project_id`：
    - 读旧值；与新值比较；有变则 `_add_timeline`（同事务，commit 前）
    - `action_data={from, to}`（id/number/null；estimate 用标量）
  - 无变化不写；bulk_update **不**扩展（未走同一 update；YAGNI）
- Modify: `backend/opentask/services/custom_field/service.py`
  - `upsert_issue_values`：在 `await self.db.commit()` **之前**，对每个 `changes[]` 项 `db.add(IssueTimeline(...))`：
    - `action_type=custom_field_changed`
    - `action_data={fieldId, fieldKey, from, to}`（值经 `_truncate_timeline_value` ≤2048 字节 UTF-8）
    - `user_id=actor_user_id`
  - formula 本就不会进 changes（upsert 已 400）
- Helper（可放 custom_field/service 或 issue_service）：`_truncate_timeline_value(v) -> JSON-able`
- Test: `backend/tests/api/test_e41_issue_audit_outbound.py`

**Interfaces:**
- Consumes: `_add_timeline`、E36 `changes[]` 形状
- Produces: GET `/{id}/timeline` 可见四类新 `action_type`；无变更不写

- [ ] **Step 1: 红测**
  - PATCH issue `cycleId` / `estimatePoints` / `projectId` → timeline 对应一条；同值再 PATCH 不增行
  - upsert 两 CF 变更 → 两条 `custom_field_changed`（含 fieldKey/from/to）
  - upsert formula → 仍 400；无新 timeline
  - 跨 WS issue → 404
- [ ] **Step 2: 跑测确认红 → 最小实现绿 → commit**

---

### Task 3 — B：Timeline CSV export 两路由（TDD）

**Files:**
- Create 或 Modify: `backend/opentask/services/issue_timeline_export.py`（或 `issue_service` 方法）
  - `EXPORT_HARD_CAP = 10000`；`EXPORT_DEFAULT_LIMIT = 5000`
  - `build_timeline_csv(*, workspace_id, issue_id=None, since=None, action_types=None, limit=...) -> (bytes, truncated: bool)`
  - 列：`created_at,action_type,user_id,user_name,field_key,from_value,to_value,action_data_json`
  - `field_key`：CF 取 `action_data.fieldKey`；其它空
  - `from_value`/`to_value`：取 `action_data.from`/`to`（非标量 `json.dumps`）
  - 仅 `Issue.workspace_id == workspace_id`；`issue_id` 必须属 WS 否则空/上层 404
  - 排序 `created_at DESC`；取 `limit+1` 判 truncated，输出前 `limit` 行
- Modify: `backend/opentask/api/issue/router.py`
  - **静态路径须在 `/{issue_id}` 之前**：`GET /timeline/export.csv`
    - Query：`since`（ISO）、`issueId`、`actionType`（可重复或逗号）、`limit`
    - `require_workspace_context`；viewer+
  - 近既有 timeline：`GET /{issue_id}/timeline/export.csv`
    - `_require_issue_access`；Query `limit`/`actionType`
    - `Content-Disposition: attachment; filename="issue-{code}-timeline.csv"`
  - 两路由均：`media_type=text/csv; charset=utf-8`；truncated → 头 `X-OpenTask-Truncated: true`
- Extend tests

**Interfaces:**
- Consumes: IssueTimeline + User name 批量查
- Produces: CSV bytes + truncated flag；跨租户 404

- [ ] **Step 1: 红测** 单 Issue CSV 列头与行；`actionType` 过滤；limit=1 截断头；WS 级 `since`/`issueId`；外租户 issue 404
- [ ] **Step 2: 实现绿 → commit**

---

### Task 4 — D 前半：Webhook 事件 + `_emit` 旁路 `fire_webhooks`（TDD）

**Files:**
- Modify: `backend/opentask/models/workspace_webhook/model.py` — `WEBHOOK_EVENTS` += `"issue.custom_field_changed"`
- Modify: `backend/opentask/services/custom_field/service.py` — `_emit_custom_field_changed` 在每条 change 的 `fire_automations` 旁：
  ```python
  await fire_webhooks(
      self.db,
      workspace_id=workspace_id,
      event_type="issue.custom_field_changed",
      data={
          "id": issue_id,
          "issueCode": getattr(issue, "issue_code", None) or getattr(issue, "code", None),
          "title": issue.title,
          "fieldId": ch["field_id"],
          "fieldKey": ch["field_key"],
          "from": ch["from"],
          "to": ch["to"],
          "actorUserId": actor_user_id,
      },
  )
  ```
  （issue code 字段名以模型实际为准：`Issue.issue_code` 或现有 serialize 键）
- Extend: `backend/tests/api/test_e41_issue_audit_outbound.py` + 可选轻量 `test_webhooks.py` 断言 events 接受新值

**Interfaces:**
- Consumes: E29 `fire_webhooks` / HMAC / delivery log
- Produces: 订阅方每字段一条；未订阅不投递；formula 不触发

- [ ] **Step 1: 红测** webhook create 含新事件 ok；upsert CF → mock `httpx`/`dispatch` 见到 `issue.custom_field_changed`×N；未订阅无调用；长值 timeline 截断
- [ ] **Step 2: 实现绿 → commit**

---

### Task 5 — C：FE 活动文案 + 导出 + webhook 多选（TDD）

**Files:**
- Modify: `frontend/src/typings/api/issue.d.ts` — `TimelineAction` += 四值
- Create: `frontend/src/utils/formatTimelineAction.ts`（从 detail 抽出纯函数便于测）
  - CF：`将自定义字段 {key} 从 {from} 改为 {to}`
  - cycle：`将周期从 {from} 改为 {to}`
  - estimate：`将估分从 {from} 改为 {to}`
  - project：`将项目从 {from} 改为 {to}`
  - 旧 case 保持与现 `detail/index.vue` 一致
- Modify: `frontend/src/views/issue/detail/index.vue` — 改用导出的 formatter；活动区加「导出 CSV」按钮 → `GET /api/issues/{id}/timeline/export.csv` 下载
- Modify: `frontend/src/service/api/issue.ts` — `fetchIssueTimelineExport(issueId, params?)` blob/download helper
- Modify: `frontend/src/service/api/webhooks.ts` — `WEBHOOK_EVENTS` += `'issue.custom_field_changed'`；可选 `WEBHOOK_EVENT_LABELS`
- Modify: `frontend/src/views/settings/webhooks/index.vue` — 多选 label 用「自定义字段变更」（或 `WEBHOOK_EVENT_LABELS`）
- Test: `frontend/src/utils/formatTimelineAction.test.ts`；扩展 `webhooks.test.ts`

- [ ] **Step 1: 红测** 四类 formatter；`WEBHOOK_EVENTS` 含新事件
- [ ] **Step 2: 实现绿；vitest → commit**

---

### Task 6 — D：CLI **1.25.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/opentask_cli.py` / `pyproject.toml` / `setup.py` / `__init__.py` → **1.25.0**
- 全仓将历史 `1.24.0` 断言同步为 `1.25.0`（`rg -l '1\.24\.0'`）
- Modify: `agent-harness/opentask-cli/opentask/core/webhook.py` — `EVENTS` += `issue.custom_field_changed`
- Modify: `agent-harness/opentask-cli/opentask/core/issue.py` + client：
  - `issue timeline <id|code> [--limit N] [--json]`
  - `issue timeline-export <id|code> [--out FILE] [--action-type …] [--limit N]`
  - `issue timeline-export-workspace [--out FILE] [--since ISO] [--action-type …] [--issue-id] [--limit N]`
- Create: `agent-harness/opentask-cli/tests/test_e41_issue_audit.py` — version；三命令 help；webhook events 含新事件

- [ ] **Step 1: 红测** version / help / events
- [ ] **Step 2: 实现绿 → commit**

---

### Task 7 — 门禁 + acceptance tip

- [ ] BE 定向 `test_e41_issue_audit_outbound.py` + 全量（记 flake `test_user_search`）
- [ ] CLI 全量；FE vitest + build
- [ ] 回填 `docs/superpowers/acceptances/2026-11-05-E41-acceptance.md` tip/测数
- [ ] 最终 tip commit；**不 push**；**不自开 E42**；STOP

---

## Self-review
1. Spec A–D / ADR D1–D10 / §10 测试要点均有任务覆盖  
2. 无 TBD；bulk 明确 YAGNI  
3. 事件名与 payload 键与 design §3 一致；硬顶/截断头一致  
