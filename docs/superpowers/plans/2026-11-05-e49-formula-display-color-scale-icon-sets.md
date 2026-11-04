# E49 Plan：Formula Display v2 — color scale + icon sets · CLI 1.33.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`39b2f79` · 分支 `sprint/E49-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e49-formula-display-color-scale-icon-sets-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E50**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Display 独立 `colorScales[]`（≤5；手动 min/max；固定 palette；number/date）+ `iconSets[]`（≤5×8；固定 icon 枚举）；与 E46 tint **并存且 tint > scale**；List/Board 客户端求值；BE normalize；**无 migration**；CLI **1.33.0**；守 formula **no-emit**。

**Architecture:** 扩展 `normalize_display_json` / FE `normalizeIssueDisplay` 接纳 `color_scales`/`icon_sets`（camelCase 别名）；写路径超限 400（对齐 E46）；FE 新增 `interpolateScaleColor` / `resolveRowScale` / `resolveCellIcon`；`resolveRowAppearance`：先 `resolveRowTint`，未命中再 scale；DisplayOptionsPanel 增编辑器；CLI 仅 version bump（无既有 display prefs CLI）。

**Tech Stack:** FastAPI + SQLAlchemy（JSON prefs）；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E50；中文 docs；CLI **1.33.0**（`pyproject.toml` + `__init__.py` + `setup.py` + `VERSION` + `opentask_cli.VERSION` 全钉）
- Q1a 独立数组；Q2a 手动 min/max；Q3a 固定 palette；Q4a tint>scale；Q5a icon vocab；Q6a **无 alembic**
- ADR D1–D8；E40 D2/D7 no-emit；无营业日历/专用 webhook/自由 CSS/auto domain
- 非目标见 design §3

## File map
| 区域 | 文件 |
|------|------|
| BE normalize | `backend/opentask/services/display_prefs/service.py` |
| BE tests | `backend/tests/api/test_e49_display_color_scale_icons.py` |
| FE helpers | `frontend/src/utils/display-prefs.ts` + `.test.ts` |
| FE UI | `DisplayOptionsPanel.vue`；`list/index.vue`；`IssueBoard.vue` |
| CLI | `agent-harness/opentask-cli/` version pins + `tests/test_e49_display_v2.py` |
| Docs | 本 plan；`docs/superpowers/acceptances/2026-11-05-E49-acceptance.md` |

## Schema（锁定）

### colorScales[]（存储键 `color_scales`；读入亦接受 `colorScales`）
```json
{
  "id": "cs1",
  "field": "cf:score",
  "domain": { "min": 0, "max": 100 },
  "palette": "blue_red",
  "target": "row"
}
```
- `field`：`cf:<slug>` | `due_date` | `estimate_points`
- `palette` ∈ `{blue_red, green_red, mono, yellow_blue, purple_green}`（5 套）
- `target` ∈ `{row, cell}`；`domain.min/max` 可解析为 float；`min==max` → 视为中点色
- cap ≤5；写路径原始长度 >5 → 400 `color_scales_too_many`；非法条目 normalize 丢弃

### iconSets[]（存储键 `icon_sets`；亦接受 `iconSets`）
```json
{
  "id": "is1",
  "field": "cf:risk",
  "rules": [
    { "op": "gte", "value": 8, "icon": "arrow_up" },
    { "op": "lt", "value": 3, "icon": "arrow_down" }
  ]
}
```
- `field`：同 E46 cfmt 白名单（`cf:`|`priority`|`status`|`due_date`|`estimate_points`）
- `op` ∈ `{eq,neq,gt,gte,lt,lte}`；`icon` ∈ `{arrow_up,arrow_down,arrow_flat,flag,dot_red,dot_yellow,dot_green,check,warn}`
- cap：sets ≤5；每 set rules ≤8（多余规则截断）；写路径 sets >5 → 400 `icon_sets_too_many`
- 渲染：cell 前缀；数组序先匹配先生效；不影响 sort/filter

### Palette 端点色（FE 插值）
| palette | low (t=0) | high (t=1) |
|---------|-----------|------------|
| blue_red | `#2080f0` | `#d03050` |
| green_red | `#18a058` | `#d03050` |
| mono | `#e8e8e8` | `#4a4a4a` |
| yellow_blue | `#f0a020` | `#2080f0` |
| purple_green | `#8a2be2` | `#18a058` |

线性 RGB 插值；越界 clamp 到 [0,1]；非有限数 / 非 number|date 字段值 → 不着色。

### 优先级（Q4a）
1. E46 `resolveRowTint` 命中 → 用 tint，**跳过** row-target scale  
2. 未命中 → 按 `colorScales` 数组序取第一条 `target=row` 且值可插值的 scale  
3. Icon 独立：不与 tint/scale 互斥；按 sets 数组序、rules 序先匹配

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E49-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — BE：color_scales / icon_sets normalize + cap（TDD）

**Files:**
- Modify: `backend/opentask/services/display_prefs/service.py`
- Test: `backend/tests/api/test_e49_display_color_scale_icons.py`

**Interfaces:**
- Produces: `DEFAULT_DISPLAY["color_scales"]=[]` / `["icon_sets"]=[]`；`_normalize_color_scales` / `_normalize_icon_sets`；写路径超限 400

- [ ] **Step 1: 红测**
```python
def test_normalize_color_scales_and_icon_sets_unit():
    from opentask.services.display_prefs.service import normalize_display_json
    d = normalize_display_json({
        "colorScales": [
            {"id": "cs1", "field": "cf:score", "domain": {"min": 0, "max": 10},
             "palette": "blue_red", "target": "row"},
            {"id": "bad", "field": "priority", "domain": {"min": 0, "max": 1},
             "palette": "blue_red", "target": "row"},  # priority 非 scale 字段 → drop
            {"id": "badp", "field": "cf:x", "domain": {"min": 0, "max": 1},
             "palette": "neon", "target": "row"},  # 非法 palette → drop
        ],
        "iconSets": [
            {"id": "is1", "field": "cf:risk", "rules": [
                {"op": "gte", "value": 8, "icon": "arrow_up"},
                {"op": "lt", "value": 3, "icon": "url_http"},  # 非法 icon → drop rule
            ]},
        ],
    })
    assert len(d["color_scales"]) == 1
    assert d["color_scales"][0]["palette"] == "blue_red"
    assert len(d["icon_sets"]) == 1
    assert len(d["icon_sets"][0]["rules"]) == 1
    assert d["icon_sets"][0]["rules"][0]["icon"] == "arrow_up"

@pytest.mark.asyncio
async def test_prefs_write_scales_icons_and_caps(test_client):
    # 合法 PUT 200 roundtrip；6 scales → 400 color_scales_too_many；6 icon sets → 400
```
- [ ] **Step 2: 跑红 → 实现绿 → commit**
  - `_SCALE_FIELD_RE`：`^(?:cf:([a-z][a-z0-9_-]{0,63})|due_date|estimate_points)$`
  - `_SCALE_PALETTES` / `_ICON_VOCAB` / caps 5
  - `validate_and_normalize_display` on_write 检查原始 list 长度（接受 camel+snake）

---

### Task 3 — BE：Display 读/写 no-emit spy（TDD）

**Files:**
- Extend: `test_e49_display_color_scale_icons.py`

- [ ] **Step 1: 红测** PUT/GET display-prefs 含 colorScales+iconSets；spy `fire_webhooks` / `fire_automations` 未被调用
- [ ] **Step 2: 绿 → commit**（预期现网路径本就无 emit；测锁住）

---

### Task 4 — FE：types + normalize + 插值/优先级 helpers（TDD）

**Files:**
- Modify: `frontend/src/utils/display-prefs.ts`
- Modify: `frontend/src/utils/display-prefs.test.ts`

**Interfaces:**
- Produces:
  - `ColorScaleRule` / `IconSetRule` / `DisplayIcon` / `ColorPalette`
  - `IssueDisplayState.colorScales` / `.iconSets`
  - `interpolateScaleColor(palette, t): string`  // `#rrggbb`
  - `resolveRowScale(issue, scales): string | null`  // hex bg 或 null
  - `resolveCellIcon(issue, sets, field?): DisplayIcon | null`
  - `resolveRowBackground(issue, {conditionalFormats, colorScales}): {kind:'tint'|'scale', value:string} | null`
    - tint 先；未命中再 scale（row target）

- [ ] **Step 1: 红测**
  - normalize 丢弃非法 palette/icon/field；cap 截断
  - `interpolateScaleColor('blue_red', 0)` ≈ blue；`t=1` ≈ red；`t=0.5` 中间
  - tint 命中时 `resolveRowBackground` 返回 tint，即使 scale 也会命中
  - tint 未命中时返回 scale hex
  - icon 先匹配；未知丢弃
- [ ] **Step 2: 绿 → commit**

---

### Task 5 — FE：DisplayOptionsPanel + List/Board 接线

**Files:**
- Modify: `DisplayOptionsPanel.vue` — 色阶/图标集增删（默认样例；≤5）
- Modify: `list/index.vue` — state + persist + `issueRowProps` 用 `resolveRowBackground`；CF 列前缀 icon
- Modify: `IssueBoard.vue` — props + `cardTintStyle` 改 appearance（tint 优先；否则 scale bg）

- [ ] **Step 1:** 接线；保留 E46 tint class；scale 用 inline `background`
- [ ] **Step 2:** vitest 仍绿；手动无冒烟要求；commit

---

### Task 6 — CLI **1.33.0**

**Files:**
- Bump: `pyproject.toml` / `__init__.py` / `setup.py` / `VERSION` / `opentask_cli.py` → **1.33.0**
- Sync: 全部历史 `1.32.0` version 断言 → `1.33.0`
- Create: `agent-harness/opentask-cli/tests/test_e49_display_v2.py` — version + help 提及 Display/API（无 display prefs 子命令则 assert `--help` 与 version）

- [ ] **Step 1: 红测** `test_version_is_1_33_0`
- [ ] **Step 2: bump + sync → 绿 → commit**

---

### Task 7 — 门禁 + acceptance tip

- [ ] BE full + targeted `test_e49_*` + `test_e46_conditional*`
- [ ] CLI pytest
- [ ] FE vitest + `npm run build`
- [ ] 填 acceptance tip/测数；`superpowers: design/plan/TDD/verify/acceptance = ok`
- [ ] **STOP**；不 push；不自开 E50

## Self-review
- Spec A–E / ADR D1–D8 / Q1–Q6 → Tasks 2–6 覆盖
- 无 placeholder；无 migration；tint>scale；palette/icon 枚举固定；CLI 四文件+VERSION 全钉
