# E40 Plan：Formula custom fields v1

日期：2026-11-04（Asia/Shanghai）  
基线 tip：`6d82547` · 分支 `sprint/E40-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-04-e40-formula-custom-fields-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E41**。

**Goal:** WS 可定义只读 `formula` 自定义字段；Issue 详情/列表返回读时计算值；白名单 AST 沙箱；环/深度拒绝；FE 可建/只读展示；CLI **1.24.0**。

**Architecture:** 新 type=`formula` + `formula_expr`/`formula_result_type` 列；写路径校验解析+DAG；`opentask.services.custom_field.formula` 受限 AST 解释器（禁 eval/exec）；`values_for_issues` 读时记忆化求值并标 `computed:true`；不物化、不 emit。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；Vue3/Naive；Click CLI；pytest/vitest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E41；中文 docs；CLI **1.24.0**
- 禁 `eval`/`exec`/`compile` 用户串进 builtins；expr≤500；fn args≤8；AST nodes≤200；DAG 深度≤8
- upsert formula → 400；读时不写 `issue_custom_field_values`；不发 `custom_field_changed`
- 标识符仅 `cf.*` + `issue.estimate_points|priority|status` + `days_until_due`
- 函数：IF/COALESCE/ABS/MIN/MAX/ROUND/LEN/LOWER/UPPER/DATE_DIFF；用 IF 非三元
- 非目标见 design §7

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-04-e40-formula-custom-fields.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-04-E40-acceptance.md`（骨架；收口补 tip/测数）

- [x] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：Migration + FIELD_TYPES + create/update 校验（环/深度）（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_04_3300-g3b4c5d6e7f1_formula_custom_fields.py`
  - revision `g3b4c5d6e7f1`；down_revision `f2a3b4c5d6e0`
  - `custom_fields` +`formula_expr` Text nullable；+`formula_result_type` String(32) nullable
- Modify: `backend/opentask/models/custom_field/model.py`
  - `FIELD_TYPES` += `"formula"`
  - 列 `formula_expr`、`formula_result_type`
- Modify: `backend/opentask/services/custom_field/service.py`
  - `RESULT_TYPES = ("number","boolean","text","date")`
  - `serialize_field` 增 `formulaExpr`/`formulaResultType`（非 formula 为 null）
  - `create`/`update` 接受 `formula_expr`/`formula_result_type`；公式强制 options=[]；非 formula 禁带 expr
  - 依赖图：`_formula_deps_from_expr` + `_assert_formula_dag`（无环、深度≤8；依赖 cf 存在且未归档）
  - `upsert_issue_values`：`field.type == "formula"` → 400「公式字段只读」
  - `validate_value`：formula → 400（防御）
  - `coerce_cf_filter_value`：formula → None（不可过滤，空匹配）
- Modify: `backend/opentask/api/custom_fields/router.py`
  - Create/Update body 增 `formulaExpr`/`formulaResultType`
- Test: `backend/tests/api/test_e40_formula_custom_fields.py`

**Interfaces:**
- Consumes: E25 CRUD 模式
- Produces: formula 字段可创建；环/深度/非法 AST → 400；upsert 拒写

- [x] **Step 1: 红测** create formula ok；缺 expr 400；环依赖 400；深度>8 400；非 formula 带 expr 400；upsert formula 400
- [x] **Step 2: 跑测确认红 → 最小实现（可先 stub parse 放行简单字面量）→ 绿 → commit**

注：完整解析器在 Task 3；本任务可用最小 `parse_formula` 接口（字面量/依赖提取）使 create 通路先绿。

---

### Task 3 — B：Parser/interpreter + validate-formula + Issue 读时求值（TDD）

**Files:**
- Create: `backend/opentask/services/custom_field/formula.py`
  - `FormulaError(code)`；`parse_formula(expr) -> ParsedFormula`（deps:set[str], ast_root）
  - 预处理：`cf.<key>`→`__cf__("key")`；`issue.(estimate_points|priority|status)`→`__issue__("…")`；`true/false/null`→True/False/None
  - `ast.parse(mode='eval')` + 白名单节点遍历；禁 Attribute/Subscript/Lambda/…；Call 仅白名单
  - `eval_formula(parsed, env) -> (value, error_code|None)`
  - `build_issue_env(issue, cf_get, utc_today)`：days_until_due / issue.* / cf.*
  - 限：len≤500；args≤8；nodes≤200
- Modify: `backend/opentask/services/custom_field/service.py`
  - `values_for_issues`：有 formula 时加载 Issue；记忆化 `eval_field`；`serialize_issue_field(..., computed=, error=)`
  - `validate_formula_expr(workspace_id, expr, result_type=None) -> {ok, dependencies, error?}`
- Modify: router — **在 `/{field_id}` 之前**注册 `POST /validate-formula`
- Extend tests

**Interfaces:**
- `POST /api/custom-fields/validate-formula` body `{formulaExpr, formulaResultType?}` → `{ok, dependencies, error?}`
- Issue `customFields[]` formula 项：`value`/`computed:true`/`error?`
- 除零→`div_zero`；类型→`type_error`；依赖→`dep_error`；解析→`parse_error`；value=null 不 500

- [x] **Step 1: 红测** IF/COALESCE/算术；除零；链式 formula；源变更后 GET 变；validate-formula；列表批量不串租户；viewer 读 ok
- [x] **Step 2: 实现绿 → commit**

---

### Task 4 — C：FE 设置 + 详情只读 + 泳道不提供 formula（TDD）

**Files:**
- Modify: `frontend/src/service/api/custom-fields.ts`
  - type += `formula`；Row 增 `formulaExpr`/`formulaResultType`
  - IssueCustomFieldValue 增 `computed?`/`error?`
  - `fetchValidateFormula`；create/update body 支持 expr/resultType
  - `formatCustomFieldValue` 支持 formula（按 result 展示）
  - `isGroupingCfType` 已排除 formula（GROUPING_CF_TYPES 不含）— 加测确认
- Modify: `frontend/src/service/api/custom-fields.test.ts`
- Modify: `frontend/src/views/workspace/custom-fields/index.vue`
  - type 选项「公式」；expr textarea；result type select；校验按钮；短说明
- Modify: `frontend/src/components/issue/IssueCustomFieldsEditor.vue`
  - formula：只读 ƒ 标签；error → `—` + title tooltip；不可 save
- Modify: `frontend/src/utils/groupIssuesBy.test.ts` 或 custom-fields.test — formula 不进 grouping 选项

- [x] **Step 1: 红测** format/helpers；isGroupingCfType('formula')===false
- [x] **Step 2: 实现绿；vitest → commit**

---

### Task 5 — D：CLI **1.24.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/custom_field.py`
  - create Choice += formula；`--expr`/`--result-type`；body `formulaExpr`/`formulaResultType`
  - `custom-field update`（id/key + --expr/--result-type/--name/--archive）
  - `custom-field validate-formula --expr … [--result-type]`
  - help 示例含 IF/COALESCE
- Modify: `api_client.py` — `update_custom_field`、`validate_formula`
- Bump **1.24.0**：`__init__.py`、`opentask_cli.py`、`setup.py`、`pyproject.toml`；全仓 `1.23.0`→`1.24.0`
- Create: `agent-harness/opentask-cli/tests/test_e40_formula_custom_fields.py`

- [x] **Step 1: 红测** version / create help 含 formula / validate-formula help
- [x] **Step 2: 实现 + bump → 绿 → commit**

---

### Task 6 — 门禁 + acceptance

- [x] BE：`pytest backend/tests/api/test_e40_formula_custom_fields.py -q`；全量 `pytest backend/tests -q`（记 passed；`test_user_search` flake 可记）
- [x] CLI：`pytest agent-harness/opentask-cli/tests -q`
- [x] FE：`cd frontend && npx vitest run && npm run build`
- [x] 写满 acceptance（tip SHA、测数、ADR、非目标）
- [x] 最终 tip；**不 push**；**不自开 E41**；回执 `superpowers: design/plan/TDD/verify/acceptance = ok`

---

## Self-review
- Spec A–D / ADR D1–D10 均有对应任务
- 无 TBD；validate-formula 路由须在 `/{field_id}` 之前
- E36 emit 仅真实 CF 写路径；formula 计算结果不 emit
- GROUPING_CF_TYPES 已无 formula → 泳道不提供
