# E43 Plan：Formula surfaces v1

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`bf57338` · 分支 `sprint/E43-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e43-formula-surfaces-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E44**。

**Goal:** Formula CF 可做 `cf.<key>` 等值过滤 / SmartSearch / Board·List 泳道分组；`issue_formula_cache` 仅加速过滤（不 emit）；CLI **1.27.0**。

**Architecture:** 扩展 `coerce_cf_filter_value` + `apply_list_filters`（非 formula SQL 先收窄 → 候选 cap 2000 → cache 命中或批 `values_for_issues` 等值）；新表 `issue_formula_cache` 在依赖写路径 best-effort 刷新/失效；FE 解禁 grouping/filter；详情仍走 `values_for_issues`（Q1）。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3；Click CLI；pytest/vitest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E44；中文 docs；CLI **1.27.0**
- E40 D2/D7：**cache/求值结果永不** `_emit_custom_field_changed` / automations / webhooks / timeline
- `FORMULA_FILTER_CANDIDATE_CAP = 2000`；超限 400 `formula_filter_too_broad`
- 等值 only；无 range/sort；null/error 过滤不命中
- Q1 详情不读 cache；Q5 text 大小写与 text CF 一致
- 非目标见 design §3

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e43-formula-surfaces.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E43-acceptance.md`（骨架）

- [x] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：coerce + apply_list_filters 批求值 + cap（TDD）

**Files:**
- Modify: `backend/opentask/services/custom_field/service.py`
  - 常量 `FORMULA_FILTER_CANDIDATE_CAP = 2000`
  - `coerce_cf_filter_value`：`formula` 按 `formula_result_type or "number"` 走 number/text/boolean/date coerce；未知 result → number
  - `apply_list_filters`：拆分 formula / 非 formula；非 formula 仍走 `IssueCustomFieldValue` SQL；对每个 formula：
    1. archived → 空集（与「未知」同空）
    2. 对当前 query 先 `count`；`> CAP` → `HTTPException(400, detail={"code":"formula_filter_too_broad","message":"..."})`
    3. 取候选 ids → 批求值（本任务先纯 `values_for_issues`；Task 3 接 cache）→ 内存等值（`==`；JSON 数字 int/float 宽松对齐 number CF）→ `Issue.id.in_(matched)`
  - null / `error` 字段 → 不匹配
- Test: `backend/tests/api/test_e43_formula_surfaces.py`

**Interfaces:**
- Produces: formula 过滤可用；cap 400

- [x] **Step 1: 红测** `cf.score=10` 命中；error/null 不命中；与 number CF AND；仅 formula 且候选>cap → 400；跨 WS 空；未知 key 空
- [x] **Step 2: 跑测确认红 → 最小实现绿 → commit**

---

### Task 3 — B：`issue_formula_cache` + 写路径刷新/失效 + 过滤用 cache（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_3600-j6e7f8a9b0c4_issue_formula_cache.py`
  - revision `j6e7f8a9b0c4`；down_revision `i5d6e7f8a9b3`
  - 表 `issue_formula_cache`：`id` PK uuid；`workspace_id` FK CASCADE；`issue_id` FK CASCADE；`field_id` FK CASCADE；`value_json` JSON/JSONB nullable；`error` String(64) nullable；`computed_at` DateTime；unique(`issue_id`,`field_id`)；index(`workspace_id`,`field_id`)
- Create/Modify: `backend/opentask/models/custom_field/model.py` — `IssueFormulaCache`
- Modify: `backend/opentask/models/custom_field/__init__.py` + `models/__init__.py` 导出
- Modify: `backend/opentask/services/custom_field/service.py`
  - `refresh_formula_cache_for_issue(workspace_id, issue_id, field_ids=None)` — 调 `values_for_issues` 写 cache；**禁止** emit
  - `invalidate_formula_cache(workspace_id, field_id)` — 删该 field 全 WS 行
  - `formulas_depending_on_cf_key` / `formulas_depending_on_issue_fields` 辅助
  - `upsert_issue_values`：commit+emit **之后** best-effort 刷新依赖变更 key 的 formula cache（不二次 emit）
  - `create`/`update` formula 定义：expr/result_type 变更 → invalidate 该 field
  - `apply_list_filters` formula 路径：优先读 cache（error is null）；miss/error → 批求值并回填
- Modify: `backend/opentask/services/issue_service.py` — `update_issue` 在 priority/status/due_date/estimate_points 变更后 best-effort 刷新依赖 issue.* / days_until_due 的 formula cache
- Extend tests：cache hit 过滤；定义变更失效；依赖 number upsert **仍**发 E36/E41 对该 number；**不**因公式结果再发；cache 写不打 webhook（spy）

**Interfaces:**
- Produces: `IssueFormulaCache` ORM；refresh/invalidate；过滤 cache 路径

- [x] **Step 1: 红测** 上述行为
- [x] **Step 2: 绿 → commit**

---

### Task 4 — D：FE grouping/泳道 + error 桶 + 拖拽只读（TDD）

**Files:**
- Modify: `backend/opentask/services/display_prefs/service.py`
  - `_resolve_cf_dim`：`type==formula` 且 `formula_result_type in {number,text,boolean}`（缺省 number）允许；date formula / multi_select 仍拒
- Modify: `frontend/src/utils/groupIssuesBy.ts`
  - `isGroupingCfType(type, formulaResultType?)`：formula + result∈{number,text,boolean} → true
  - `ERROR_CF_KEY = '__error__'`；`resolveCfBucket`：formula+error → `__error__`；空 → `__empty__`
  - `orderKeys('cf')`：`__error__` 与 `__empty__` 置后
  - `buildGroupByOptions` 传入 `formulaResultType`
- Modify: `frontend/src/utils/display-prefs.ts` — `buildSwimlaneOptions` 同传 result type
- Modify: `frontend/src/views/issue/list/index.vue` — `sanitizeCfDim` 用新签名；选项 map 带 `formulaResultType`
- Modify: `frontend/src/service/api/custom-fields.test.ts` — 更新「formula 可分组」断言
- Modify: `frontend/src/utils/groupIssuesBy.test.ts` + `boardSwimlanes.test.ts` — formula 桶 / error 桶
- Board：跨泳道已按 lane 隔离 group；补充注释/辅助 `isFormulaCfDimReadonly`；若有跨泳道写 CF 逻辑则对 formula no-op + toast（对齐 E37 展示-only）

- [x] **Step 1: 红测** isGroupingCfType('formula','number') true；error 桶；prefs 写 formula 泳道 200
- [x] **Step 2: 绿 → commit**

---

### Task 5 — C：FE 过滤解禁 + SmartSearch 文案

**Files:**
- Modify: `frontend/src/utils/issueSearchParser.ts` — suggestions 补 `field:score:10` formula 示例
- 确认 SmartSearch `field:`/`cf:` 无需新语法；若存在按 type 禁选 formula 的芯片则按 `formulaResultType` 解禁
- FE 文案：可选处标明「计算值（只读）」

- [x] **Step 1: 测/改 → commit**

---

### Task 6 — E/F：CLI **1.27.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/__init__.py` / `opentask_cli.py` / `setup.py` / `pyproject.toml` → **1.27.0**
- 全仓历史 `1.26.0` version 断言 → `1.27.0`
- Create: `agent-harness/opentask-cli/tests/test_e43_formula_surfaces.py` — version + `issue list --cf` help/示例含 formula
- Modify: issue list help 补一行 formula 过滤说明（若有）

- [x] **Step 1: 红测 version → bump → 绿 → commit**

---

### Task 7 — 门禁 + acceptance tip

- [x] BE：`pytest backend/tests -q`（记 passed/skip；`test_user_search` flake 可记）
- [x] CLI：`pytest agent-harness/opentask-cli/tests -q`
- [x] FE：`pnpm vitest run` + `pnpm build`
- [x] 填 `docs/superpowers/acceptances/2026-11-05-E43-acceptance.md` tip/测数
- [x] 最终 tip commit；**不 push**；**不自开 E44**；STOP

## Self-review
- A–G / ADR D1–D9 均有任务
- Q1–Q5 已关闭并写入实现
- emit 负例在 Task 3
- 无 placeholder
