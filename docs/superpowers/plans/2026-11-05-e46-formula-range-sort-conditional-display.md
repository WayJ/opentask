# E46 Plan：Formula query surfaces v2 — range · sort · conditional display

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`b5b132e` · 分支 `sprint/E46-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e46-formula-range-sort-conditional-display-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E47**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** CF/formula **range**（`gt/gte/lt/lte`）+ **`sort_by=cf:<key>`**（cap 2000、nulls last）+ Display **`conditionalFormats[]`**（≤10、枚举 tint、客户端求值）；SmartSearch 薄 `>=` 等；FE 过滤比较符+排序+Display；CLI **1.30.0**；守 E40 D2/D7 **永不 emit**；无新表。

**Architecture:** 扩展 `parse_cf_query_items` → `(key,op,raw)`；`apply_list_filters` / formula match 支持 op；stored number/date 走 JSONB 比较；`IssueService.list_issues` 对 `cf:` sort 内存排序；`normalize_display_json` + FE tint；CLI/SmartSearch 薄对齐。

**Tech Stack:** FastAPI + SQLAlchemy（PG JSONB）；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E47；中文 docs；CLI **1.30.0**（`pyproject.toml` + `__init__.py` + `setup.py` + `opentask_cli.py` VERSION 全钉）
- Q1a `[op]`；Q2a SmartSearch 薄；Q3 text/boolean/date/number sort，禁 multi_select；Q4 数组序先匹配；Q5 不进 CSV；Q6 stored number/date 也开 range
- ADR D1–D9；E40 D2/D7 no-emit；无 Redis/cron；无营业日历；无新 migration（默认）
- 非目标见 design §3

## File map
| 区域 | 文件 |
|------|------|
| Parse/filter/sort helpers | `backend/opentask/services/custom_field/service.py` |
| List + cf sort | `backend/opentask/services/issue_service.py`；`api/issue/router.py`（透传） |
| Display normalize | `backend/opentask/services/display_prefs/service.py`；FE `frontend/src/utils/display-prefs.ts` + tint helper |
| SmartSearch | `frontend/src/utils/issueSearchParser.ts` |
| FE UI | `views/issue/list/index.vue`；`DisplayOptionsPanel.vue`；List/Board 行 tint |
| CLI | `agent-harness/opentask-cli/...` version + `--cf` help + tests |
| Tests | `backend/tests/api/test_e46_*.py`；FE vitest；CLI `test_e46_*.py` |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E46-acceptance.md`（骨架；收口补 tip/测数）

- [x] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：parse op + unit（TDD）

**Files:**
- Modify: `backend/opentask/services/custom_field/service.py`
  - `CF_RANGE_OPS = frozenset({"gt","gte","lt","lte"})`
  - `CF_EQ_OPS = frozenset({"eq"})`
  - `parse_cf_query_items` → `list[tuple[str,str,str]]` = `(key, op, raw)`
  - 解析：`cf.<key>` / `cf.<key>[op]`；短形 `cf=key=value` / `cf=key[op]=value`
  - key 内 `[op]` 用正则 `^([a-z][a-z0-9_-]{0,63})(?:\[(eq|gt|gte|lt|lte)\])?$`
  - 非法 `[op]` → 跳过该项（或视为无匹配）；缺省 op=`eq`
- Update: `backend/tests/api/test_e32_custom_field_filters.py` 断言三元组
- Test: `backend/tests/api/test_e46_formula_range_sort.py`（新建）

**Interfaces:**
- Produces: `parse_cf_query_items(...) -> list[tuple[str,str,str]]`

- [x] **Step 1: 红测**
```python
def test_parse_cf_ops():
    from opentask.services.custom_field.service import parse_cf_query_items
    items = parse_cf_query_items([
        ("cf.score[gte]", "8"),
        ("cf.score[lt]", "20"),
        ("cf.weight", "5"),
        ("cf", "risk[gt]=3"),
        ("cf", "env=prod"),
    ])
    assert items == [
        ("score", "gte", "8"),
        ("score", "lt", "20"),
        ("weight", "eq", "5"),
        ("risk", "gt", "3"),
        ("env", "eq", "prod"),
    ]
```
- [x] **Step 2: 跑红 → 实现绿 → commit**（同步修 E32 unit 断言）

---

### Task 3 — A：stored number/date range + unsupported 400（TDD）

**Files:**
- Modify: `custom_field/service.py`
  - `apply_list_filters(filters: list[tuple[str,str,str]])`
  - `_range_type_ok(field) -> bool`：stored `number|date` 或 formula 且 `formulaResultType in {number,date}`
  - op∈range 且类型不支持 → `HTTPException(400, detail={"code":"cf_range_unsupported",...})`
  - stored eq：沿用 `cf_value_match_clause`
  - stored range：`cf_value_range_clause(field, op, expected)` — PG JSONB：number 用 `astext::float`；date 用 `astext` 字典序；null 行不匹配
  - 同 key 多 op AND
- Modify: `issue_service.py` 类型注解与透传（若仍 `(k,v)` 则适配）
- Extend tests in `test_e46_formula_range_sort.py`

**Interfaces:**
- Consumes: `(key,op,raw)`；Produces: SQL AND filters；400 `cf_range_unsupported`

- [x] **Step 1: 红测** stored number `cf.weight[gte]=5` + `[lt]=10`；date range；text `[gt]` → 400；eq 回归绿
- [x] **Step 2: 绿 → commit**

---

### Task 4 — A：formula range match + cap + no-emit（TDD）

**Files:**
- Modify: `_apply_formula_list_filter` / `_match_formula_candidates` 接受 `op`；比较 `_formula_values_compare(actual, op, expected, result_type)`
  - number：float 比较；date：字符串比较；null/error → False
  - 仍受 `FORMULA_FILTER_CANDIDATE_CAP=2000`
  - cache 路径 **不**调用 emit / fire_automations / fire_webhooks / timeline
- Spy 测：range 过滤后 webhook/automation 未触发

- [x] **Step 1: 红测** formula score `gte=8`/`lt=20`；与 eq AND；cap 超限仍 400 `formula_filter_too_broad`；spy no-emit
- [x] **Step 2: 绿 → commit**

---

### Task 5 — B：`sort_by=cf:<key>` + cap + saved view（TDD）

**Files:**
- Modify: `issue_service.py` `list_issues`
  - 若 `sort_by` 匹配 `^cf:([a-z][a-z0-9_-]{0,63})$`：
    1. 校验字段存在未归档；类型 ∈ `{number,text,date,boolean}` 或 formula 同 resultType；`multi_select` → 400 `cf_sort_unsupported`
    2. 先应用全部过滤（含 cf range）
    3. count > `FORMULA_SORT_CANDIDATE_CAP`（=2000，可 alias `FORMULA_FILTER_CANDIDATE_CAP`）→ 400 `formula_sort_too_broad`
    4. 取全部候选 id + CF/formula 值；内存排序；null/error **nulls last**（asc/desc 皆然）；二级 `created_at`,`id`
    5. 再 slice 分页
  - 系统 sort 白名单回归不变
- Saved View：`sort_json` 已透传；测 `{sort_by:"cf:score",sort_order:"desc"}` 可存可读；应用 View 时 list 带同参（既有 FE 路径即可）
- Constant: `FORMULA_SORT_CANDIDATE_CAP = FORMULA_FILTER_CANDIDATE_CAP` 导出

- [x] **Step 1: 红测** sort cf:score desc；error/null 末；multi_select 400；超 cap 400；系统 created_at 回归；saved view 存 `cf:`
- [x] **Step 2: 绿 → commit**

---

### Task 6 — C：display_json `conditionalFormats[]`（TDD）

**Files:**
- Modify: `display_prefs/service.py`
  - `DEFAULT_DISPLAY["conditional_formats"] = []`
  - `normalize_display_json`：解析数组；每条需 `id/when/style/target`；非法丢弃；**写路径** `validate_and_normalize_display(..., on_write=True)` 若规范化前原始长度 >10 → 400；规范化后 ≤10
  - when.field：白名单 `priority|status|due_date|estimate_points` 或 `cf:<key>`
  - when.op：`eq|neq|gt|gte|lt|lte`（按类型约束在 FE；BE 宽松丢弃非法）
  - style.rowTint ∈ `{danger,warning,success,info,neutral}`；target ∈ `{row,cell}`
- FE: `display-prefs.ts` 同步类型 + normalize + `displayStateToJson`
- FE: `conditionalFormat.ts`（或同文件）`matchConditionalFormat` / `resolveRowTint` — 数组序先匹配；vitest
- FE: DisplayOptionsPanel 增删改规则；List/Board 行 class / cell tint
- **不做** CSV 导出 formats

- [x] **Step 1: 红测** BE normalize；写 >10 → 400；FE vitest tint first-match
- [x] **Step 2: 绿 → commit**

---

### Task 7 — D/E：SmartSearch 薄 op + CLI 1.30.0 + FE 芯片（TDD）

**Files:**
- FE `issueSearchParser.ts`：
  - `CustomFieldFilter` += optional `op?: 'eq'|'gt'|...`（默认 eq）
  - 解析 `cf:score>=8` / `cf:score>5` / `cf:score<=1` / `cf:key:value`（既有）
  - token 正则扩展：允许 `cf:key>=val`（在 `field:value` 之外另扫，或预处理）
  - `customFieldsToCfParams` → `cf.<key>` 或 `cf.<key>[op]`
- FE list：number/date CF 过滤芯片比较符；sort 菜单含 CF/formula
- CLI：
  - bump **1.30.0**：`pyproject.toml`、`opentask/__init__.py`、`setup.py`、`opentask_cli.py` VERSION
  - 全仓 `1.29.0` → `1.30.0` 断言同步（含 historical epic 测试文件）
  - `--cf` help 示例 `score[gte]=8`；`--sort-by cf:score`（既有 `--sort-by` 透传即可）
  - 新测 `tests/test_e46_formula_range_sort.py`：version + help 含 gte / cf:

- [x] **Step 1: 红测** parser `cf:score>=8` → op gte；CLI version 1.30.0
- [x] **Step 2: 绿 → commit**（确认三文件 version 齐全）

---

### Task 8 — 门禁 + acceptance tip

- [x] BE：`pytest` 全量 + 定向 `test_e46*` `test_e43*` `test_e32*`（记 passed；`test_user_search` flake 可记）
- [x] CLI：`pytest` agent-harness/opentask-cli
- [x] FE：`npx vitest run` + `npm run build`
- [x] 确认 pyproject/`__init__`/setup/`opentask_cli` 均为 **1.30.0**
- [x] 写 acceptance tip（HEAD 为准）+ 最终 commit
- [x] **STOP**；不 push；不开 PR；不自开 E47

---

## Self-review
- Spec A–F / Acceptance A–H → Tasks 2–8 覆盖
- no-emit spy → Task 4
- Q1–Q6 / ADR D1–D9 写入 Global Constraints
- 无 placeholder；无 E47 范围

