# E40 Acceptance：Formula custom fields v1

日期：2026-11-04（Asia/Shanghai）  
分支：`sprint/E40-S1`  
基线 design：`6d82547`  
tip：`27b2e4c`  
状态：**PASS（本地齐套；未 push）**

## 交付 A–D

| 面 | 内容 |
|----|------|
| A | `FIELD_TYPES` += `formula`；列 `formula_expr`/`formula_result_type`；Alembic `g3b4c5d6e7f1`；create/update 校验 expr≤500 + result_type + 依赖存在/未归档 + DAG 无环 + 深度≤8；非 formula 禁带 expr；upsert formula → 400「公式字段只读」；serialize 含 `formulaExpr`/`formulaResultType` |
| B | `opentask.services.custom_field.formula` 受限 AST（禁 eval/exec）；标识符 `cf.*` + `issue.estimate_points\|priority\|status` + `days_until_due`；函数 IF/COALESCE/ABS/MIN/MAX/ROUND/LEN/LOWER/UPPER/DATE_DIFF；读时记忆化求值；`computed:true` + 可选 `error`（div_zero/type_error/dep_error/parse_error）；不物化、不 emit；`POST /api/custom-fields/validate-formula` |
| C | FE 设置：类型「公式」+ expr textarea + result type + 校验按钮；详情 ƒ 只读 + error tooltip；`GROUPING_CF_TYPES` 不含 formula（泳道不提供） |
| D | CLI **1.24.0**：`custom-field create --type formula --expr --result-type`；`update`；`validate-formula`；help 含 IF/COALESCE；全仓 version 断言同步 |

## ADR（落地）
- D1 type=`formula`；expr 在 `formula_expr` 列
- D2 读时求值、不物化
- D3 受限 AST；禁 eval/exec；长度/节点/参数上限
- D4 标识符仅白名单
- D5 函数白名单 IF/COALESCE/ABS/MIN/MAX/ROUND/LEN/LOWER/UPPER/DATE_DIFF
- D6 DAG 无环，深度 ≤8
- D7 计算结果不触发 automations/webhooks
- D8 upsert formula → 400
- D9 CLI 1.24.0
- D10 非目标见 design §7；不 push；不自开 E41

## 门禁

| 面 | 结果 |
|----|------|
| BE 定向 `test_e40_formula_custom_fields.py` | **12 passed** |
| BE 全量 | **969 passed** / 24 skipped / **1 failed**（已知 flake `test_tasks_jira_wire::TestMetadata::test_user_search`；与 E40 无关；单跑复测 PASSED） |
| CLI 全量 | **479 passed** / 89 skipped |
| FE vitest | **280 passed**（42 files） |
| FE build | **ok**（vite prod） |

### flake 复测
- `pytest tests/tasks/test_tasks_jira_wire.py::TestMetadata::test_user_search`：单跑 **PASSED**（不阻塞 E40）。

## 非目标（未做）
跨 Issue rollup；JS/Python 脚本；物化/emit；按 formula 过滤/SmartSearch；Board 泳道主路径（读回退）；webhook CF outbound；SLA；Activity export；push/PR；E41。

## Superpowers
`superpowers: design/plan/TDD/verify/acceptance = ok`
