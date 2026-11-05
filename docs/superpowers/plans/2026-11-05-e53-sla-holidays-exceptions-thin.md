# E53 Plan：SLA 节假日/例外日 thin — exceptions · CLI 1.37.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`5fbb63e` · 分支 `sprint/E53-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e53-sla-holidays-exceptions-thin-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E54**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** WS 可维护例外日（closed / forced_open）；营业分钟加法器跳过 closed、覆盖 forced_open；enabled=false 例外惰性；配置变更批量重算；FE 薄例外列表；CLI **1.37.0**；无国家日历包 / policy 覆盖 / Push / webhook 仪表 / formula emit。

**Architecture:** 扩 `workspaces.business_hours` JSON 增加 `exceptions:[{date,kind,windows?}]`（无新表，上限 366）；纯函数 normalize + 日段解析接入既有 `add_business_minutes` / `elapsed_business_minutes`；SlaService `compute_deadline`/`compute_elapsed` 透传 exceptions；Workspace.update 既有 bh 变更重算；FE 在 SLA 设置页旁薄 CRUD；CLI `sla business-hours exceptions list|add|remove`。

**Tech Stack:** FastAPI + SQLAlchemy；zoneinfo；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E54；中文 docs；CLI **1.37.0**
- ADR D1–D7；Q1a–Q6a 全关（双 kind；forced_open 默认窗=周一窗或 09–18；WS 级；无 policy 覆盖；JSON 扩列 cap 366；CLI 挂 business-hours）
- formula 永不 emit；不扩 E51 pack；不改 E52 Activity；无 Redis/cron
- 非目标见 design §2
- 重算封顶 `RECOMPUTE_CAP=500`（E50 既有）

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e53-sla-holidays-exceptions-thin.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E53-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e53-sla-holidays-exceptions-thin.md \
  docs/superpowers/acceptances/2026-11-05-E53-acceptance.md
git commit -m "docs(E53): plan + acceptance skeleton"
```

---

### Task 2 — A：纯函数 exceptions + 加法器接线（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/business_hours.py`
- Create: `backend/tests/unit/test_e53_business_exceptions.py`
- Extend (compat): `backend/tests/unit/test_e50_business_hours.py` 仅当默认 normalize 形状变

**Interfaces:**
- Produces:
  - `EXCEPTION_KINDS = ("closed", "forced_open")`
  - `MAX_EXCEPTIONS = 366`
  - `DATE_RE` → `YYYY-MM-DD`
  - `normalize_exceptions(raw, *, windows_for_default: dict|None=None) -> list[dict]`
    - 每项 `{date, kind, windows?}`；`closed` 可无 windows（忽略）；`forced_open` windows 0..2 或省略
    - 非法 date / 未知 kind / 重复 date / >366 → `ValueError`
    - 段校验复用 `_parse_hhmm` / 合并逻辑（与日段同）
  - `default_forced_open_windows(windows: dict) -> list[dict]` — **Q2a**：若 `windows["mon"]` 非空取其副本；否则 `[{"start":"09:00","end":"18:00"}]`
  - `resolve_day_segments(local_day: datetime, windows: dict, exceptions: list[dict]) -> list[dict]`
    - 按本地 `YYYY-MM-DD` 查例外；`closed` → `[]`；`forced_open` → 显式 windows 或 default；否则 weekday windows
  - `normalize_business_hours(raw)` → `{enabled, windows, exceptions}`（`exceptions` 默认 `[]`）
  - `add_business_minutes(..., windows, exceptions=None)` / `elapsed_business_minutes(..., windows, exceptions=None)`：扫描日用 `resolve_day_segments`
- Consumes: 既有 `normalize_windows` / `_day_key` / `_seg_bounds_local`

- [ ] **Step 1: 红测** `backend/tests/unit/test_e53_business_exceptions.py`

```python
"""E53: business-hours exceptions pure helpers (TDD)."""
from __future__ import annotations
from datetime import datetime
import pytest
from opentask.services.sla.business_hours import (
    MAX_EXCEPTIONS,
    add_business_minutes,
    default_forced_open_windows,
    elapsed_business_minutes,
    normalize_business_hours,
    normalize_exceptions,
    resolve_day_segments,
)

def _utc(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, 0)

def _mon_fri():
    return {d: [{"start": "09:00", "end": "18:00"}] for d in ("mon","tue","wed","thu","fri")} | {d: [] for d in ("sat","sun")}

def test_normalize_exceptions_rejects_bad_date_kind_dup_cap():
    with pytest.raises(ValueError):
        normalize_exceptions([{"date": "2026-13-01", "kind": "closed"}])
    with pytest.raises(ValueError):
        normalize_exceptions([{"date": "2026-11-05", "kind": "holiday"}])
    with pytest.raises(ValueError):
        normalize_exceptions([
            {"date": "2026-11-05", "kind": "closed"},
            {"date": "2026-11-05", "kind": "forced_open"},
        ])
    with pytest.raises(ValueError, match="366"):
        normalize_exceptions([{"date": f"2026-01-{(i%28)+1:02d}", "kind": "closed"} for i in range(MAX_EXCEPTIONS + 1)])

def test_default_forced_open_uses_monday_or_0918():
    assert default_forced_open_windows(_mon_fri()) == [{"start": "09:00", "end": "18:00"}]
    assert default_forced_open_windows({**_mon_fri(), "mon": []}) == [{"start": "09:00", "end": "18:00"}]
    custom = {**_mon_fri(), "mon": [{"start": "10:00", "end": "16:00"}]}
    assert default_forced_open_windows(custom) == [{"start": "10:00", "end": "16:00"}]

def test_resolve_closed_and_forced_open():
    # 2026-11-05 Thursday
    day = datetime(2026, 11, 5, 12, 0)
    win = _mon_fri()
    assert resolve_day_segments(day, win, [{"date": "2026-11-05", "kind": "closed"}]) == []
    segs = resolve_day_segments(day, win, [{"date": "2026-11-05", "kind": "forced_open", "windows": [{"start": "10:00", "end": "12:00"}]}])
    assert segs == [{"start": "10:00", "end": "12:00"}]
    # Saturday forced_open without windows → Mon default
    sat = datetime(2026, 11, 7, 12, 0)
    segs2 = resolve_day_segments(sat, win, [{"date": "2026-11-07", "kind": "forced_open"}])
    assert segs2 == [{"start": "09:00", "end": "18:00"}]

def test_add_skips_closed_day_across_holiday():
    # Thu 2026-11-05 17:00 Shanghai = UTC 09:00; closed Fri 11-06; +120 with Mon–Fri 09–18
    # Thu remaining 60 → skip Fri closed → Mon 09:00 + 60 = Mon 10:00 = UTC 02:00 (2026-11-09)
    start = _utc(2026, 11, 5, 9, 0)
    win = _mon_fri()
    ex = [{"date": "2026-11-06", "kind": "closed"}]
    deadline = add_business_minutes(start, 120, "Asia/Shanghai", win, exceptions=ex)
    assert deadline == _utc(2026, 11, 9, 2, 0)

def test_add_forced_open_on_empty_weekday():
    # Sat 2026-11-07 10:00 Shanghai = UTC 02:00; sat window empty; forced_open default 09–18; +60 → 11:00 = UTC 03:00
    start = _utc(2026, 11, 7, 2, 0)
    win = _mon_fri()
    ex = [{"date": "2026-11-07", "kind": "forced_open"}]
    deadline = add_business_minutes(start, 60, "Asia/Shanghai", win, exceptions=ex)
    assert deadline == _utc(2026, 11, 7, 3, 0)

def test_elapsed_skips_closed():
    win = _mon_fri()
    # Fri 2026-11-06 closed; Thu 17:00 → Mon 10:00 span
    a = _utc(2026, 11, 5, 9, 0)   # Thu 17:00 CST
    b = _utc(2026, 11, 9, 2, 0)   # Mon 10:00 CST
    # without closed Fri: Thu 60 + Fri 540? wait Fri full 9h=540 — with closed only Thu 60 + Mon 60 = 120? 
    # elapsed [Thu17, Mon10): Thu 17–18=60, Fri closed=0, Sat/Sun=0, Mon 09–10=60 → 120
    assert elapsed_business_minutes(a, b, "Asia/Shanghai", win, exceptions=[{"date":"2026-11-06","kind":"closed"}]) == 120

def test_normalize_business_hours_includes_exceptions():
    bh = normalize_business_hours({"enabled": True, "windows": _mon_fri(), "exceptions": [{"date":"2026-10-01","kind":"closed"}]})
    assert bh["exceptions"] == [{"date": "2026-10-01", "kind": "closed"}]
    assert normalize_business_hours(None)["exceptions"] == []
```

- [ ] **Step 2: 跑红** `cd backend && python -m pytest tests/unit/test_e53_business_exceptions.py -v` → FAIL（缺符号）
- [ ] **Step 3: 最小实现** — 扩 `business_hours.py`：normalize_exceptions / default_forced_open_windows / resolve_day_segments；改 normalize_business_hours；加法器日扫描改用 resolve；`exceptions` 默认 None→[]
- [ ] **Step 4: 绿** + 既有 `test_e50_business_hours` 仍绿
- [ ] **Step 5: Commit** `feat(E53): business-hours exceptions pure helpers`

---

### Task 3 — B：SlaService 透传 + API CRUD/校验（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/service.py` — `compute_deadline` / `compute_elapsed` 传 `exceptions=(ws.business_hours or {}).get("exceptions")`
- Modify: `backend/opentask/services/workspace/service.py` — 已走 `normalize_business_hours`（含 exceptions）；确认 400 透传
- Create: `backend/tests/api/test_e53_sla_exceptions.py`

**Interfaces:**
- Consumes: Task 2 normalize / add / elapsed
- Produces: PATCH `businessHours.exceptions` CRUD via workspace update；跨租户 404；owner 写；配置写无额外 webhook/automation；formula no-emit spy；closed/forced_open SLA 时钟样例；enabled=false 墙钟；配置变更重算

- [ ] **Step 1: 红测**（要点）

```python
# test_patch_exceptions_crud_and_validation
# - PATCH exceptions closed OK；重复 date → 400；非法 kind → 400；>366 → 400
# - other WS owner 不可改本 WS
# test_closed_day_skips_deadline / test_forced_open_counts_on_weekend
# test_enabled_false_exceptions_inert (墙钟)
# test_config_change_recomputes_with_exceptions
# test_config_write_no_extra_webhook_automation_formula_no_emit
```

- [ ] **Step 2: 绿（接线 compute_* + normalize 已在 Task2）→ commit** `feat(E53): wire exceptions into SLA + workspace API`

---

### Task 4 — C：FE 薄例外列表（TDD）

**Files:**
- Modify: `frontend/src/utils/businessHours.ts` — `BusinessException` 类型；`normalizeExceptions`；`normalizeBusinessHours` 含 exceptions；`MAX_EXCEPTIONS=366`
- Modify: `frontend/src/utils/businessHours.test.ts` — 归一化 / closed skip 样例 / 拒重复
- Modify: `frontend/src/views/settings/sla/index.vue` — 例外日卡片：列表 + 日期/kind/可选窗口 + 增删 + 空态；保存随 businessHours

- [ ] **Step 1: 红测** vitest normalizeExceptions
- [ ] **Step 2: 绿 + `npm run build` → commit** `feat(E53): FE thin exceptions list`

---

### Task 5 — D：CLI **1.37.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/sla.py` — `business-hours exceptions` group：`list|add|remove`；`show` 展示 exceptions
- Pin 全部 → **1.37.0**：`VERSION` / `__init__.py` / `opentask_cli.py` / `setup.py` / `pyproject.toml`；全仓历史 `1.36.0` 断言 → `1.37.0`
- Create: `agent-harness/opentask-cli/tests/test_e53_sla_exceptions.py`

```python
"""E53 CLI: sla business-hours exceptions + version 1.37.0."""
from click.testing import CliRunner
from opentask.opentask_cli import cli

def test_version_1_37_0():
    r = CliRunner().invoke(cli, ["--version"])
    assert r.exit_code == 0
    assert "1.37.0" in r.output

def test_exceptions_help():
    r = CliRunner().invoke(cli, ["sla", "business-hours", "exceptions", "--help"])
    assert r.exit_code == 0
    assert "list" in r.output and "add" in r.output and "remove" in r.output
```

- [ ] **Step 1: 红** version / help
- [ ] **Step 2: 实现 + 批量钉版 → 绿 → commit** `feat(E53): CLI 1.37.0 business-hours exceptions`

**exceptions add 行为：** GET workspace → merge exceptions → PATCH；`remove --date YYYY-MM-DD` 过滤后 PATCH；`list` 打印 show 中的 exceptions。

---

### Task 6 — 门禁 + acceptance tip

- [ ] BE 定向 `test_e53_*` + `test_e50_*` + `test_e48_*` + `test_e45_*`；全量（记 passed；`test_user_search` flake 可记）
- [ ] CLI 全量；确认 pins **1.37.0**
- [ ] FE vitest + build
- [ ] 填写 acceptance；最终 tip commit
- [ ] **STOP**；不 push；不自开 E54

---

## Self-Review
1. Spec A–E / 验收 A–H / ADR D1–D7 / Q1a–Q6a 均有 Task 覆盖  
2. 无 TBD/placeholder  
3. 无新 migration（Q5a JSON）；CLI 全钉 1.37.0；重算封顶 500；不改 E51/E52
