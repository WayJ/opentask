# E58 Plan：国家/地区假日包 mid — 精选包一键合并 · CLI 1.42.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`ed17b2d` · 分支 `sprint/E58-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e58-sla-country-holiday-packs-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E59**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Owner 可浏览仓内精选假日包（CN+US，至少 2026），预览/应用合并进 WS `business_hours.exceptions` 或 policy `calendar.exceptions`（pack wins）；应用后触发既有重算；FE 假日包折叠；CLI **1.42.0**；无 ICS/外网拉取/冲突矩阵/Push/formula emit。

**Architecture:** 静态 JSON `backend/opentask/data/holiday_packs/{region}/{year}.json` + loader/校验；纯函数 `merge_exceptions_pack_wins`；`applied_holiday_packs` JSON 账本（WS/policy）；API list/show/preview/apply；FE 折叠；CLI holiday-packs 子命令。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest；alembic。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E59；中文 docs；CLI **1.42.0**
- ADR D1–D7；Q1a–Q6a 全关
- formula 永不 emit；不改 E55 Insights / E57 webhook 告警；无新 webhook 事件名；无运行时 HTTP 拉包
- 非目标见 design §2
- `RECOMPUTE_CAP=500`；exceptions cap 366；kind ⊆ `{closed, forced_open}`
- Q5a：forced_open 缺 windows → E53 `default_forced_open_windows`（resolve 时）；包可省略 windows

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e58-sla-country-holiday-packs.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E58-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e58-sla-country-holiday-packs.md \
  docs/superpowers/acceptances/2026-11-05-E58-acceptance.md
git commit -m "docs(E58): plan + acceptance skeleton"
```

---

### Task 2 — A：静态包 CN/US 2026 + loader/校验（TDD）

**Files:**
- Create: `backend/opentask/data/holiday_packs/CN/2026.json`
- Create: `backend/opentask/data/holiday_packs/US/2026.json`
- Create: `backend/opentask/data/holiday_packs/__init__.py`（空或导出路径常量）
- Create: `backend/opentask/services/sla/holiday_packs.py`
- Create: `backend/tests/unit/test_e58_holiday_packs_loader.py`

**Interfaces:**
- Produces:
  - Pack shape: `{region, year, name, sourceNote, holidays:[{date, kind, windows?, label?}]}`
  - `PACKS_ROOT` → `Path` to `opentask/data/holiday_packs`
  - `load_pack(region: str, year: int) -> dict` — 校验 region/year 匹配文件；kind∈EXCEPTION_KINDS；date 合法；未知 kind / 坏 JSON → `ValueError`；缺文件 → `FileNotFoundError`
  - `list_packs() -> list[dict]` — 扫目录，返回 `{region, year, name, sourceNote, count}` 排序
  - `pack_to_exceptions(pack) -> list[dict]` — holidays→`{date,kind,windows?}`（label 不进 exceptions 存储，仅 diff 展示可选）
  - CN 2026：closed 元旦/春节/清明/劳动/端午/中秋/国庆；forced_open 调休 2026-01-04, 02-14, 02-28, 05-09, 09-20, 10-10；sourceNote 引国办发明电〔2025〕7号
  - US 2026：联邦常见 closed（含 observed 如适用）；无州级；无 forced_open

- [ ] **Step 1: 红测** `backend/tests/unit/test_e58_holiday_packs_loader.py`

```python
"""E58: holiday pack loader/validate (TDD)."""
from __future__ import annotations
import pytest
from opentask.services.sla.holiday_packs import list_packs, load_pack, pack_to_exceptions

def test_list_contains_cn_us_2026():
    rows = list_packs()
    keys = {(r["region"], r["year"]) for r in rows}
    assert ("CN", 2026) in keys and ("US", 2026) in keys
    cn = next(r for r in rows if r["region"] == "CN" and r["year"] == 2026)
    assert cn["count"] > 10 and cn["name"] and cn["sourceNote"]

def test_load_cn_has_closed_and_forced_open():
    pack = load_pack("CN", 2026)
    assert pack["region"] == "CN" and pack["year"] == 2026
    kinds = {h["kind"] for h in pack["holidays"]}
    assert "closed" in kinds and "forced_open" in kinds
    dates = {h["date"] for h in pack["holidays"]}
    assert "2026-10-01" in dates and "2026-10-10" in dates  # National Day + makeup
    ex = pack_to_exceptions(pack)
    assert all("date" in e and e["kind"] in ("closed", "forced_open") for e in ex)

def test_load_us_closed_only_and_missing_404ish():
    pack = load_pack("US", 2026)
    assert all(h["kind"] == "closed" for h in pack["holidays"])
    assert "2026-11-26" in {h["date"] for h in pack["holidays"]}  # Thanksgiving
    with pytest.raises(FileNotFoundError):
        load_pack("ZZ", 2026)
    with pytest.raises(FileNotFoundError):
        load_pack("CN", 1999)
```

- [ ] **Step 2:** Run → FAIL（module missing）
- [ ] **Step 3:** 实现 JSON 包 + `holiday_packs.py`
- [ ] **Step 4:** Run → PASS
- [ ] **Step 5:** Commit `feat(E58): static CN/US 2026 holiday packs + loader`

---

### Task 3 — B+C：merge pack-wins + applied 账本 + alembic + preview/apply API（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/holiday_packs.py` — merge / ledger helpers
- Modify: `backend/opentask/models/workspace/model.py` — `applied_holiday_packs` JSON nullable
- Modify: `backend/opentask/models/sla/model.py` — `applied_holiday_packs` JSON nullable
- Create: `backend/alembic/versions/2026_11_05_4300-q3f4a5b6c7d1_applied_holiday_packs.py`（revises `p2e3f4a5b6c0`）
- Modify: `backend/opentask/services/sla/service.py` — `preview_holiday_pack` / `apply_holiday_pack`
- Modify: `backend/opentask/api/sla/router.py` — GET list/show；POST preview/apply
- Modify: workspace/policy serializers to include `appliedHolidayPacks` when present
- Create: `backend/tests/unit/test_e58_merge_exceptions.py`
- Create: `backend/tests/api/test_e58_holiday_packs.py`

**Interfaces:**
- Produces:
  - `merge_exceptions_pack_wins(existing: list, pack_exceptions: list) -> dict`
    - returns `{exceptions: list, added: list, replaced: list, unchanged: list, skipped: list}`
    - Q3a：同 date 以包覆盖（kind/windows）；包外既有保留；同 date 同内容 → unchanged
    - normalize via `normalize_exceptions`；总数 ≤366 else ValueError
  - `upsert_applied_ledger(ledger, region, year, *, applied_at: str) -> list` — 同 region+year 更新 appliedAt；否则 append
  - Service:
    - `preview_holiday_pack(ws, *, region, year, target="workspace", policy_id=None) -> dict` 不写库
    - `apply_holiday_pack(...) -> dict` 写 exceptions + ledger；WS→`recompute_deadlines_for_workspace`；policy→物化 exceptions-only overlay（若 calendar null）+ `recompute_deadlines_for_policy`；返回 merge stats + recompute
  - API:
    - `GET /api/sla/holiday-packs` member+
    - `GET /api/sla/holiday-packs/{region}/{year}` member+；缺 → 404
    - `POST /api/sla/holiday-packs/{region}/{year}/preview` body `{target?: "workspace"|"policy", policyId?}` member+
    - `POST …/apply` 同 body；owner；跨租户 policyId → 404
  - Alembic：两列 JSON nullable；SQLite 友好

- [ ] **Step 1: 红测** unit merge + api smoke

```python
# unit
from opentask.services.sla.holiday_packs import merge_exceptions_pack_wins
def test_pack_wins_and_keeps_non_pack():
    existing = [
        {"date": "2026-10-01", "kind": "closed"},
        {"date": "2026-06-01", "kind": "closed"},
    ]
    pack = [
        {"date": "2026-10-01", "kind": "forced_open"},
        {"date": "2026-10-02", "kind": "closed"},
    ]
    out = merge_exceptions_pack_wins(existing, pack)
    by = {e["date"]: e for e in out["exceptions"]}
    assert by["2026-10-01"]["kind"] == "forced_open"
    assert "2026-06-01" in by and "2026-10-02" in by
    assert any(x["date"] == "2026-10-01" for x in out["replaced"])
    assert any(x["date"] == "2026-10-02" for x in out["added"])
    assert any(x["date"] == "2026-06-01" for x in out["unchanged"])
```

- [ ] **Step 2–4:** 实现 merge → API → 绿
- [ ] **Step 5:** Commit `feat(E58): holiday-pack preview/apply + applied ledger`

---

### Task 4 — D：FE 假日包折叠 + merge 纯函数（TDD）

**Files:**
- Modify: `frontend/src/utils/businessHours.ts` — `mergeExceptionsPackWins`
- Modify: `frontend/src/utils/businessHours.test.ts`
- Modify: `frontend/src/service/api/sla.ts` — list/show/preview/apply helpers
- Modify: `frontend/src/views/settings/sla/index.vue` — 「假日包」折叠；目标 WS/policy；预览表；确认应用；policy 区快捷

- [ ] **Step 1: 红测** vitest merge
- [ ] **Step 2–4:** 实现 FE → vitest 绿
- [ ] **Step 5:** Commit `feat(E58): FE holiday packs collapse + preview apply`

---

### Task 5 — E：CLI **1.42.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/sla.py` — `holiday-packs` group
- Bump: pyproject.toml / `__init__.py` / setup.py / VERSION / `opentask_cli.VERSION` → **1.42.0**
- Sync: 所有历史 `1.41.0` version 断言 → `1.42.0`
- Create: `agent-harness/opentask-cli/tests/test_e58_holiday_packs.py`

```python
"""E58 CLI: sla holiday-packs + version 1.42.0."""
from click.testing import CliRunner
from opentask.opentask_cli import cli

def test_version_142():
    r = CliRunner().invoke(cli, ["--version"])
    assert r.exit_code == 0 and "1.42.0" in r.output

def test_holiday_packs_help():
    r = CliRunner().invoke(cli, ["sla", "holiday-packs", "--help"])
    assert r.exit_code == 0
    for sub in ("list", "show", "preview", "apply"):
        assert sub in r.output
```

- [ ] Commit `feat(E58): CLI 1.42.0 holiday-packs`

---

### Task 6 — 门禁 + acceptance tip

- BE full + targeted E58+E56+E53/E50；CLI；FE vitest+build
- 记 flake `test_user_search` 若现
- 确认全部 CLI pins **1.42.0**
- 更新 acceptance tip SHA + 门禁数
- Commit `docs(E58): acceptance + tip SHA`
- **STOP**；不 push；不自开 E59

---

## Self-Review
- Spec A–F → Tasks 2–5；Q1a–Q6a / D1–D7 写入 Global
- 无 TBD/placeholder；类型名与 Task 3 Interfaces 一致
- 重算复用 E50/E56；无新 webhook 事件；包不进 DB
