# E37 Plan：Board / List 按 Custom Field 分组（CF 泳道）

日期：2026-11-04（Asia/Shanghai）  
基线 tip：`ac42210` · 分支 `sprint/E37-S1`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-04-e37-board-cf-swimlanes-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E38**。

**Goal:** Board 行维 / List groupBy 支持 `cf:<field_key>`；prefs/views 可持久化且租户校验；FE 可操作；CLI **1.21.0**。

**Architecture:** 方案 B。`SwimlaneBy`/`GroupByKey` 扩展字符串形态 `cf:<key>`；BE 写路径严格校验 WS+类型（禁 multi_select），读路径非法回退 `none`；FE `groupIssuesBy`/`boardSwimlanes` 按 issue.customFields 分桶；选中后并入 `custom_field_keys` 并 `include=custom_fields`；拖拽不改 CF。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive；Click CLI；pytest/vitest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E38；中文 docs；CLI **1.21.0**
- ADR：允许 single_select/boolean/text/number/date；禁 multi_select；拖拽不改 CF；写严读回退 none
- 非目标见 design §7（公式字段、multi_select 泳道、聚合 API、E38…）

---

### Task 1 — Docs
- [ ] plan 入库（本文件）
- [ ] acceptance 骨架 `docs/superpowers/acceptances/2026-11-04-E37-acceptance.md`；收口补 tip/测数

### Task 2 — BE：display prefs / saved views `cf:<key>` 校验（TDD）

**Files:**
- Modify: `backend/opentask/services/display_prefs/service.py`
- Modify: `backend/opentask/api/display_prefs/router.py`（upsert 传 workspace 校验）
- Modify: `backend/opentask/services/saved_view/service.py`（create/update 校验 display）
- Modify: `backend/opentask/api/saved_views/router.py`（若需传 session/ws）
- Test: `backend/tests/api/test_e37_board_cf_swimlanes.py`

**Interfaces:**
- Produces:
  - `CF_GROUPING_TYPES = frozenset({"single_select","boolean","text","number","date"})`
  - `parse_cf_dim(value) -> str | None`（匹配 `^cf:([a-z][a-z0-9_-]{0,63})$`）
  - `normalize_display_json(raw) -> dict`：系统枚举或合法形态 `cf:<key>`；保留/合并 `custom_field_keys`；畸形 `cf:` → 视为 none
  - `async validate_and_normalize_display(db, workspace_id, raw, *, on_write: bool) -> dict`
    - `on_write=True`：字段不存在/归档/跨租户/multi_select/非法类型 → `HTTPException 400`
    - `on_write=False`：非法 → 该维回退 `"none"`
    - 若 swimlane_by 或 group_by 为 `cf:key`，把 `key` 去重并入 `custom_field_keys`

- [ ] **Step 1: 红测** — `test_e37_board_cf_swimlanes.py`：
  - PUT display prefs `swimlane_by=cf:severity`（先建 single_select）→ 200；回读同值；`custom_field_keys` 含 severity
  - `group_by=cf:severity` 同理
  - unknown key / 他租户同名 key / archived / `multi_select` key → **400**
  - saved view create/update 同校验
  - GET 含历史非法 `cf:gone` 的 prefs → 读回 `none`（可直接写 DB 或绕过校验写入再 get）
- [ ] **Step 2: 跑测确认红**
- [ ] **Step 3: 最小实现绿**
  - 扩展 `normalize_display_json` 接受 `cf:` 形态 + `custom_field_keys`
  - `DisplayPrefsService.upsert/get` 走 `validate_and_normalize_display`
  - SavedView create/update：display 非空时同样校验后写入规范化 JSON
- [ ] **Step 4: commit** `feat(E37): BE validate cf: swimlane/group_by on prefs/views`

### Task 3 — FE：groupBy / swimlanes / Display（TDD）

**Files:**
- Modify: `frontend/src/utils/groupIssuesBy.ts` + `.test.ts`
- Modify: `frontend/src/utils/boardSwimlanes.ts` + `.test.ts`
- Modify: `frontend/src/utils/display-prefs.ts` + `.test.ts`
- Modify: `frontend/src/views/issue/list/modules/DisplayOptionsPanel.vue`
- Modify: `frontend/src/views/issue/list/index.vue`（groupBy 选项、include、选 CF 并入 keys、multi_select 回退 toast）

**Interfaces:**
- `GroupByKey` / `SwimlaneBy` = 系统枚举 | `` `cf:${string}` ``
- `isCfDim(v): v is \`cf:${string}\`` / `cfKeyFromDim(v): string | null`
- `GROUPING_CF_TYPES` = 允许类型集合；`isGroupingCfType(t)`
- `groupIssuesBy(issues, groupBy, opts?)`：`cf:key` 时从 `issue.customFields|custom_fields` 取 `{key,value,type,options,name}`
  - single_select：桶 key=option value，label=option label||value；空/未知 → `__empty__`「空」
  - boolean：`true`/`false`/`__empty__`（标签 是/否/空）
  - text|number|date：规范化字符串；空 → `__empty__`
  - multi_select：不进入分组路径（调用方应先回退）
- `buildBoardSwimlanes`：`swimlaneToGroupBy` 支持 `cf:`（同字符串）
- Display：`swimlaneOptions` / `groupByOptions` = 系统项 + 活跃允许类型 CF（`cf:${key}`，label 用字段名）
- 选中 `cf:key`：自动把 key 并入 `customFieldKeys`；`needCf` 亦在 `groupBy`/`swimlaneBy` 为 `cf:` 时为 true
- prefs 读到 multi_select 的 `cf:`（或 FE 侧类型不允许）→ 回退 `none` + toast

- [ ] **Step 1: 红测** groupIssuesBy(`cf:severity`) 分桶；空值；boolean；board 矩阵行数；isGroupByKey/isSwimlaneBy 接受 `cf:x`
- [ ] **Step 2: 实现绿 + Display 面板选项 + index include/merge**
- [ ] **Step 3: vitest 绿；commit** `feat(E37): FE Board/List CF swimlanes + Display`

### Task 4 — CLI 1.21.0

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/__init__.py`、`opentask_cli.py`、`setup.py`、`pyproject.toml` → **1.21.0**
- Modify: `agent-harness/opentask-cli/opentask/core/issue.py`：`--group-by` 接受系统值或 `cf:<key>`；help 示例
- Modify: 全仓 CLI 历史 version 断言 `1.20.0` → `1.21.0`
- Test: `agent-harness/opentask-cli/tests/test_e37_cf_group_by.py`

- [ ] **Step 1: 红测** version 含 1.21.0；`issue list --help` 含 `cf:` / `--group-by`
- [ ] **Step 2: 实现** — `--group-by` 本地接受（若 API 无对应 query，至少 CLI 校验形态并在 JSON/提示中带上；契约测证明 option 被 Click 接受不报 bad choice）
- [ ] **Step 3: 同步 version 断言；commit** `feat(E37): CLI 1.21.0 — issue list --group-by cf:<key>`

### Task 5 — 门禁 + acceptance
- [ ] BE 定向 `test_e37_board_cf_swimlanes.py` + 全量 pytest（记录 passed/skip；`test_user_search` flake 注明）
- [ ] CLI pytest 全量
- [ ] FE vitest + build
- [ ] acceptance 写 tip + 测数；`superpowers: design/plan/TDD/verify/acceptance = ok`
- [ ] **STOP**；不 push；不自开 E38

## ADR（对齐 design）
| ID | 决定 |
|----|------|
| D1 | 编码 `cf:<field_key>` 单字符串 |
| D2 | 允许 single_select/boolean/text/number/date；禁 multi_select |
| D3 | 写严格 400；读非法 → none |
| D4 | 矩阵客户端计算；无新聚合 API |
| D5 | 拖拽只改 status，不改 CF |
| D6 | CLI 1.21.0 |
| D7 | 非目标见 §7；不 push；不自开 E38 |

## Spec coverage
- §1 A 契约 ✅ Task2
- §1 B FE ✅ Task3
- §1 C 薄 BE ✅ Task2（复用 list；负例测）
- §1 D CLI ✅ Task4
- §7 非目标 — 不实现
