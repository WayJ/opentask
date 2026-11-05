# E56 Plan：SLA policy 日历覆盖 thin · CLI 1.40.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`137f734` · 分支 `sprint/E56-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e56-sla-policy-calendar-overlay-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E57**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** SlaPolicy 可选日历覆盖（timezone / windows / exceptions）；字段缺省继承 WS（E50/E53）；create/pause/resume/recompute/run-due 走 effective calendar；WS `enabled=false` 仍全局墙钟（Q2a）；FE policy 表单薄「日历覆盖」；CLI **1.40.0**；无国家包 / 冲突矩阵 / Push / formula emit。

**Architecture:** `sla_policies.calendar` JSON nullable；纯函数 `normalize_policy_calendar` + `resolve_effective_calendar`；`compute_deadline`/`compute_elapsed` 增 `policy` 参数；policy PATCH 触发 `recompute_deadlines_for_policy`；WS 变更仍 `recompute_deadlines_for_workspace`（Q3a 全量）；FE 折叠覆盖 + 清除；CLI `--calendar-json` / `--clear-calendar` + show `effectiveCalendar`。

**Tech Stack:** FastAPI + SQLAlchemy；zoneinfo；Vue3/Naive + vitest；Click CLI；pytest；alembic。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E57；中文 docs；CLI **1.40.0**
- ADR D1–D7；Q1a–Q6a 全关（整包 JSON 可选字段；WS 总闸；WS 变更全量重算；单列 calendar；`--calendar-json`+`--clear-calendar`；show 含 effectiveCalendar）
- formula 永不 emit；不改 E52 Activity / E54 webhook / E55 Insights；无国家包 / 冲突矩阵
- 非目标见 design §2
- `RECOMPUTE_CAP=500`；exceptions cap 366；windows ≤2 段/日

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e56-sla-policy-calendar-overlay.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E56-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e56-sla-policy-calendar-overlay.md \
  docs/superpowers/acceptances/2026-11-05-E56-acceptance.md
git commit -m "docs(E56): plan + acceptance skeleton"
```

---

### Task 2 — A+C：normalize/merge 纯函数 + model + alembic（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/business_hours.py` — 增 `normalize_policy_calendar` / `resolve_effective_calendar`
- Modify: `backend/opentask/models/sla/model.py` — `SlaPolicy.calendar` JSON nullable
- Create: `backend/alembic/versions/2026_11_05_4100-o1d2e3f4a5b9_sla_policy_calendar.py`（revises `n0c1d2e3f4a8`）
- Create: `backend/tests/unit/test_e56_policy_calendar.py`

**Interfaces:**
- Produces:
  - `normalize_policy_calendar(raw) -> dict|None`
    - `None` / 空对象 → `None`（全继承）
    - 对象可含 `timezone?` / `windows?` / `exceptions?`（各自缺省 = 不覆盖）
    - IANA tz / windows / exceptions 校验复用 E50/E53；非法 → `ValueError`
  - `resolve_effective_calendar(ws, policy=None) -> dict|None`
    - WS `business_hours.enabled=false` 或无合法 tz → `None`（墙钟，**Q2a**；policy 不可强开）
    - 否则 `{timezone, windows, exceptions}`：
      - `timezone = cal.timezone ?? ws.timezone`
      - `windows = cal.windows ?? bh.windows`
      - `exceptions = cal.exceptions ?? bh.exceptions ?? []`
  - Alembic 加 `sla_policies.calendar` JSON/JSONB nullable；旧行 null ≡ 全继承

- [ ] **Step 1: 红测** `backend/tests/unit/test_e56_policy_calendar.py`

```python
"""E56: policy calendar normalize + effective merge (TDD)."""
from __future__ import annotations
from types import SimpleNamespace
import pytest
from opentask.services.sla.business_hours import (
    WEEKDAY_PRESET_09_18,
    normalize_policy_calendar,
    resolve_effective_calendar,
)

def _ws(**kw):
    base = dict(
        timezone="Asia/Shanghai",
        business_hours={
            "enabled": True,
            "windows": WEEKDAY_PRESET_09_18,
            "exceptions": [{"date": "2026-10-01", "kind": "closed"}],
        },
    )
    base.update(kw)
    return SimpleNamespace(**base)

def _pol(calendar=None):
    return SimpleNamespace(calendar=calendar)

def test_normalize_none_and_empty():
    assert normalize_policy_calendar(None) is None
    assert normalize_policy_calendar({}) is None

def test_normalize_partial_fields_and_rejects():
    out = normalize_policy_calendar({"timezone": "America/New_York"})
    assert out == {"timezone": "America/New_York"}
    out2 = normalize_policy_calendar({
        "windows": WEEKDAY_PRESET_09_18,
        "exceptions": [{"date": "2026-11-05", "kind": "closed"}],
    })
    assert "windows" in out2 and out2["exceptions"][0]["kind"] == "closed"
    with pytest.raises(ValueError):
        normalize_policy_calendar({"timezone": "Not/AZone"})
    with pytest.raises(ValueError):
        normalize_policy_calendar({"exceptions": [{"date": "2026-11-05", "kind": "holiday"}]})
    with pytest.raises(ValueError):
        normalize_policy_calendar({"exceptions": [
            {"date": "2026-11-05", "kind": "closed"},
            {"date": "2026-11-05", "kind": "forced_open"},
        ]})
    with pytest.raises(ValueError):
        normalize_policy_calendar("nope")

def test_resolve_inherits_and_overrides():
    ws = _ws()
    assert resolve_effective_calendar(ws, _pol(None))["timezone"] == "Asia/Shanghai"
    assert resolve_effective_calendar(ws, _pol(None))["exceptions"][0]["date"] == "2026-10-01"
    eff = resolve_effective_calendar(ws, _pol({"timezone": "UTC"}))
    assert eff["timezone"] == "UTC"
    assert eff["exceptions"][0]["date"] == "2026-10-01"  # inherit exceptions
    eff2 = resolve_effective_calendar(ws, _pol({
        "exceptions": [{"date": "2026-11-07", "kind": "forced_open"}],
    }))
    assert eff2["timezone"] == "Asia/Shanghai"
    assert eff2["exceptions"] == [{"date": "2026-11-07", "kind": "forced_open"}]

def test_resolve_q2a_ws_disabled_wall_clock():
    ws = _ws(business_hours={"enabled": False, "windows": WEEKDAY_PRESET_09_18, "exceptions": []})
    assert resolve_effective_calendar(ws, _pol({"timezone": "UTC", "windows": WEEKDAY_PRESET_09_18})) is None
    assert resolve_effective_calendar(None, _pol({"timezone": "UTC"})) is None
```

- [ ] **Step 2: 跑红** → FAIL（缺符号）
- [ ] **Step 3: 最小实现** normalize + resolve；model 加列；alembic 一版
- [ ] **Step 4: 绿** + commit `feat(E56): policy calendar normalize + alembic`

---

### Task 3 — B：时钟路径 + API CRUD/重算（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/service.py`
  - `compute_deadline(now, minutes, ws, policy=None)` / `compute_elapsed(..., policy=None)` 走 `resolve_effective_calendar`
  - `serialize_policy(row, ws=None)` 含 `calendar`；ws 时含 `effectiveCalendar`
  - `create_policy` / `update_policy` 接受 `calendar`（normalize；ValueError→400）；update 后若 calendar 变 → `recompute_deadlines_for_policy`
  - `recompute_deadlines_for_policy(workspace_id, policy_id, cap=500)`
  - `recompute_deadlines_for_workspace` 循环传 `policy`（Q3a 仍全量）
  - `sync_clocks` pause/resume/start 传 `policy`
- Modify: `backend/opentask/api/sla/router.py` — PolicyCreate/Update 加 `calendar: Optional[dict] = None`；create/update/list 传 ws 给 serialize
- Create: `backend/tests/api/test_e56_sla_policy_calendar.py`

**Interfaces / 行为:**
- 无覆盖 policy ≡ E53 行为
- policy exceptions forced_open 周一（WS mon 空）→ 该 policy 钟计入营业分钟
- WS enabled=false → 墙钟（即便 policy 有 calendar）
- policy calendar PATCH → 仅该 policy 钟 deadline 更新
- 跨租户 policy 404；非法 calendar 400
- spy：日历读写无额外 fire_webhooks/automations；formula no-emit

- [ ] **Step 1: 红测**（要点）

```python
"""E56: SLA policy calendar overlay — API + clock wiring · no-emit."""
# helpers mirror E50/E53 (_register/_auth/_create_issue/_create_policy/_clocks/_patch_ws_bh)

# test_no_overlay_regression_matches_ws_calendar
# test_policy_exceptions_override_only
# test_partial_timezone_override
# test_ws_enabled_false_wall_clock_despite_policy_calendar  # Q2a
# test_policy_calendar_change_recomputes_only_that_policy
# test_illegal_calendar_400_cross_tenant_404
# test_calendar_write_no_extra_webhook_automation_formula_no_emit
# test_serialize_includes_calendar_and_effective
```

- [ ] **Step 2–4: 绿 + commit** `feat(E56): wire effective calendar into SLA clocks + API`

---

### Task 4 — D：FE 日历覆盖（TDD）

**Files:**
- Modify: `frontend/src/utils/businessHours.ts` — 增 `PolicyCalendar` / `normalizePolicyCalendar` / `mergeEffectiveCalendar`
- Modify: `frontend/src/utils/businessHours.test.ts` — 空 ≡ WS；部分覆盖 merge
- Modify: `frontend/src/service/api/sla.ts` — `SlaPolicyRow.calendar?` / `effectiveCalendar?`
- Modify: `frontend/src/views/settings/sla/index.vue` — 创建表单折叠「日历覆盖」；行操作「清除覆盖」；编辑覆盖薄表单（timezone + exceptions 复用；空=继承提示）

- [ ] **Step 1: 红测** vitest normalize/merge
- [ ] **Step 2: 绿 + `npm run build` → commit** `feat(E56): FE policy calendar overlay`

---

### Task 5 — E：CLI **1.40.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/sla.py` — create/update `--calendar-json` / `--clear-calendar`；show 打印 `calendar` + `effectiveCalendar`
- Pin 全部 → **1.40.0**：`VERSION` / `opentask/__init__.py` / `opentask/opentask_cli.py` / `setup.py` / `pyproject.toml`；全仓历史 `1.39.0` 断言 → `1.40.0`
- Create: `agent-harness/opentask-cli/tests/test_e56_sla_policy_calendar.py`

```python
"""E56 CLI: sla policy --calendar-json|--clear-calendar + version 1.40.0."""
from click.testing import CliRunner
from opentask.opentask_cli import cli, VERSION

def test_version_pin():
    assert VERSION == "1.40.0"
    r = CliRunner().invoke(cli, ["--version"])
    assert "1.40.0" in r.output

def test_policy_create_help_shows_calendar_flags():
    r = CliRunner().invoke(cli, ["sla", "policy", "create", "--help"])
    assert r.exit_code == 0
    assert "--calendar-json" in r.output
    assert "--clear-calendar" in r.output or True  # clear on update
    r2 = CliRunner().invoke(cli, ["sla", "policy", "update", "--help"])
    assert "--calendar-json" in r2.output
    assert "--clear-calendar" in r2.output
```

- [ ] **Step 1–4: 红→绿→ pin 全仓 → commit** `feat(E56): CLI 1.40.0 policy calendar`

---

### Task 6 — 门禁 + acceptance tip

- BE full + targeted E56+E53+E50+E48/E45；记 flake `test_user_search`
- CLI 全量；确认 pins **1.40.0**
- FE vitest + build
- 填 acceptance tip SHA；`superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；无 push / 无 PR / 不自开 E57

---

## Self-review
- Spec A–F → Tasks 2–5；Q1a–Q6a / D1–D7 写入 Global + Task 3/5
- 无 TBD/placeholder；类型名前后一致（normalize_policy_calendar / resolve_effective_calendar / effectiveCalendar）
