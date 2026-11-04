# E36 Plan：Automation trigger `custom_field_changed`

日期：2026-11-04（Asia/Shanghai）  
基线 tip：`09c7bf0` · 分支 `sprint/E36-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-04-e36-automation-cf-changed-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E37**。

**Goal:** CF 写入后触发 `custom_field_changed`；多 CF 条件 AND≤5；防环 depth≤1；FE/CLI 1.20.0。

**Architecture:** 在 `CustomFieldService.upsert_issue_values` 成功 after-commit 按变更字段 emit；`AutomationService._match_trigger` 支持 field/from/to；`_match_condition` 支持 `customFields[]`；沿用 `_automation_depth` 禁二次触发。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive；Click CLI；pytest/vitest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E37；中文 docs；CLI **1.20.0**；非目标见 design §4。

---

### Task 1 — Docs
- [ ] plan 入库（本文件）
- [ ] acceptance 骨架；收口补 tip/测数

### Task 2 — BE：trigger + emit + 多条件（TDD）
**Files:**
- Modify: `backend/opentask/models/automation/model.py`（`TRIGGER_TYPES` += `custom_field_changed`）
- Modify: `backend/opentask/services/automation/service.py`（`_match_trigger` / `_match_condition` / create 校验 max 5）
- Modify: `backend/opentask/services/custom_field/service.py`（upsert 后 emit；可选 `actor_user_id`）
- Modify: `backend/opentask/api/issue/router.py`（传 actor）
- Test: `backend/tests/api/test_e36_automation_cf_changed.py`

- [ ] **Step 1: 红测** — 写 `test_e36_automation_cf_changed.py`：
  - 改 CF → 匹配规则执行（`set_priority` / `add_comment`）
  - `field_key` / `field_id` 过滤；`from`/`to` 过滤
  - `customFields` 多条件 AND；>5 → 400
  - `set_custom_field` 动作不二次触发 `custom_field_changed`
  - 跨租户 / viewer 403（create 规则）
- [ ] **Step 2: 跑测确认红**（缺 trigger / 无 emit → FAIL）
- [ ] **Step 3: 最小实现绿**
  - `TRIGGER_TYPES` 加 `custom_field_changed`
  - `_match_trigger`: field_key|field_id|key；from/to（缺省不限）；值用 `==` JSON 语义
  - upsert：提交前记录 old；commit 后对实际变更逐字段 `fire_automations(..., event={field_key,field_id,from:old,to:new})`
  - `_match_condition`: `customFields`/`custom_fields` 列表全部 AND；单 `customField` 兼容；create/update 列表长度 >5 → 400
- [ ] **Step 4: BE 相关测绿并 commit**

### Task 3 — FE
**Files:** `frontend/src/service/api/automations.ts`、`automations.test.ts`、`frontend/src/views/workspace/automations/index.vue`
- [ ] trigger 选项 + 类型加 `custom_field_changed`
- [ ] 触发表单：字段下拉 + 可选 from/to → 写入 `triggerConfig`
- [ ] 多 CF 条件：`withCustomFieldConditions` / `getCustomFieldConditions`（≤5）；列表 summarize
- [ ] vitest 覆盖 helpers

### Task 4 — CLI 1.20.0
**Files:** `agent-harness/opentask-cli/opentask/core/automation.py`、`__init__.py`、`opentask_cli.py`、`setup.py`、`pyproject.toml`、全仓 version 断言、`tests/test_e36_automation_cf_changed.py`
- [ ] TRIGGERS += `custom_field_changed`；help 示例
- [ ] version → **1.20.0**（含历史 e2x 测里的版本串）

### Task 5 — 门禁
- [ ] BE/CLI/FE 全量或定向证据；acceptance 写 tip+测数；`superpowers: … = ok`；STOP

## ADR（实现对齐 design）
| ID | 决定 |
|----|------|
| D1 | emit：`upsert_issue_values` commit 后，仅实际变更字段 |
| D2 | 防环：既有 depth≥1 跳过；自动化内 set_cf 不再触发 |
| D3 | `customFields` 数组 AND，max 5；单 `customField` 仍有效 |
| D4 | CLI 1.20.0 |

## Spec coverage
- §3.1 trigger ✅ Task2
- §3.2 多条件 ✅ Task2/3
- §3.3 防环 ✅ Task2
- §3.4 FE/CLI ✅ Task3/4
- §3.5 租户 ✅ Task2
- §4 非目标 — 不实现
