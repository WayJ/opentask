# E64 Plan：假日包扩容 mid — EU/UK + 2027 年卷 · CLI 1.48.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`63d7c4f`（全文 `63d7c4f66ca3e1f83e14b7bb4392b80a5607413a`）· 分支 `sprint/E64-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e64-holiday-pack-expansion-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E65**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Workspace 成员可在既有 E58 API/FE/CLI 上发现并 preview/apply 新增静态包 EU/UK 2026 + CN/US/EU/UK 2027；list 可选 `region`/`year` 过滤；CLI **1.48.0**；无 ICS/州包/外网；不改 E57–E63 邻面主表面；formula no-emit。

**Architecture:** 仓内新增 6 份 JSON；复用 E58 `list_packs`/`load_pack`/`merge_exceptions_pack_wins`/`preview`/`apply`；`list_packs` 与 `GET /holiday-packs` 加法可选 `region`/`year`；FE 列表自然多出新区/年 + 可选筛；CLI list `--region/--year` + 全钉 1.48.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E65；中文 docs；CLI **1.48.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；不改 E63 公开门户 / E57 告警 / E60–E62 Search / E61 Insights 主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- MAX_EXCEPTIONS=366（超限 HTTP 400）；RECOMPUTE_CAP=500；pack wins
- Q4a：CN2027 官方调休未公布 → 仅 closed + sourceNote 含「调休待补」；无 forced_open
- Q5a：UK = England & Wales only
- Q1a：单一 `EU` 超集（非 DE/FR）
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/data/holiday_packs/{EU,UK}/2026.json` | 新包 |
| `backend/opentask/data/holiday_packs/{CN,US,EU,UK}/2027.json` | 新包 |
| `backend/opentask/services/sla/holiday_packs.py` | `list_packs` + optional region/year |
| `backend/opentask/api/sla/router.py` | list query params |
| `backend/tests/unit/test_e64_holiday_packs_expansion.py` | loader 发现/校验 |
| `backend/tests/api/test_e64_holiday_packs_expansion.py` | list filter + apply EU + no-emit |
| `frontend/src/service/api/sla.ts` | fetchHolidayPacks params |
| `frontend/src/views/settings/sla/index.vue` | 文案 + region/year 筛 |
| `frontend/src/utils/businessHours.test.ts` | list keys 断言（或新建 e64 test） |
| `agent-harness/opentask-cli/**` | 1.48.0 + list flags |

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e64-holiday-pack-expansion-mid.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E64-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e64-holiday-pack-expansion-mid.md \
  docs/superpowers/acceptances/2026-11-05-E64-acceptance.md
git commit -m "docs(E64): plan + acceptance skeleton"
```

---

### Task 2 — A：6 静态包 + loader 发现（TDD）

**Files:**
- Create: 6 JSON under `backend/opentask/data/holiday_packs/`
- Create: `backend/tests/unit/test_e64_holiday_packs_expansion.py`
- Modify: none required in loader for discovery（目录扫描已有）

**Interfaces:**
- Pack shape 同 E58：`{region,year,name,sourceNote,holidays:[{date,kind,label?}]}`
- Keys 必须出现：`(EU,2026),(UK,2026),(CN,2027),(US,2027),(EU,2027),(UK,2027)` + 旧 `(CN,2026),(US,2026)`
- CN2027：无 `forced_open`；sourceNote 含「调休待补」
- EU/UK：全部 `closed`
- UK sourceNote 标明 England & Wales

- [ ] **Step 1: 红测**

```python
"""E64: holiday pack expansion — EU/UK + 2027 (TDD)."""
from __future__ import annotations
import pytest
from opentask.services.sla.holiday_packs import list_packs, load_pack

REQUIRED = {
    ("CN", 2026), ("US", 2026),
    ("EU", 2026), ("UK", 2026),
    ("CN", 2027), ("US", 2027), ("EU", 2027), ("UK", 2027),
}

def test_list_contains_e64_keys_and_legacy():
    rows = list_packs()
    keys = {(r["region"], r["year"]) for r in rows}
    assert REQUIRED <= keys
    for region, year in (("EU", 2026), ("UK", 2026), ("CN", 2027), ("US", 2027), ("EU", 2027), ("UK", 2027)):
        row = next(r for r in rows if r["region"] == region and r["year"] == year)
        assert row["count"] >= 5 and row["name"] and row["sourceNote"]

def test_cn_2027_closed_only_pending_makeup():
    pack = load_pack("CN", 2027)
    assert all(h["kind"] == "closed" for h in pack["holidays"])
    assert "调休待补" in pack["sourceNote"]
    dates = {h["date"] for h in pack["holidays"]}
    assert "2027-01-01" in dates and "2027-02-06" in dates and "2027-10-01" in dates

def test_eu_uk_closed_and_uk_england_wales():
    eu = load_pack("EU", 2026)
    uk = load_pack("UK", 2026)
    assert all(h["kind"] == "closed" for h in eu["holidays"] + uk["holidays"])
    assert "England" in uk["sourceNote"] or "Wales" in uk["sourceNote"]
    assert "2026-04-03" in {h["date"] for h in uk["holidays"]}  # Good Friday
    assert "2026-05-01" in {h["date"] for h in eu["holidays"]}  # Labour Day

def test_us_2027_observed():
    pack = load_pack("US", 2027)
    dates = {h["date"] for h in pack["holidays"]}
    assert "2027-07-05" in dates  # Independence observed
    assert "2027-12-24" in dates  # Christmas observed
    assert all(h["kind"] == "closed" for h in pack["holidays"])
```

- [ ] **Step 2:** Run → FAIL（缺包）
- [ ] **Step 3:** 写 6 JSON（内容见下方数据附录约定）
- [ ] **Step 4:** Run → PASS
- [ ] **Step 5:** Commit `feat(E64): add EU/UK 2026 + CN/US/EU/UK 2027 holiday packs`

**数据约定（写入 JSON）：**
- **UK 2026**（GOV.UK England & Wales）：01-01, 04-03 GF, 04-06 EM, 05-04 Early May, 05-25 Spring, 08-31 Summer, 12-25 Xmas, 12-28 Boxing substitute
- **UK 2027**：01-01, 03-26 GF, 03-29 EM, 05-03 Early May, 05-31 Spring, 08-30 Summer, 12-27 Xmas sub, 12-28 Boxing sub
- **EU 2026**（精选自 EC Decision C(2025)4899 共用日 + Labour Day；非各国全集）：01-01, 01-02, 04-03 GF, 04-06 EM, 05-01, 05-14 Ascension, 05-25 Whit, 11-02 All Souls, 12-25, 12-26
- **EU 2027**（C(2025)4897 + Labour Day）：01-01, 03-26 GF, 03-29 EM, 05-01, 05-06 Ascension, 05-17 Whit, 11-01 All Saints, 12-25, 12-26
- **US 2027**（OPM federal observed）：01-01, 01-18 MLK, 02-15 Washington, 05-31 Memorial, 06-18 Juneteenth obs, 07-05 Independence obs, 09-06 Labor, 10-11 Columbus, 11-11 Veterans, 11-25 Thanksgiving, 12-24 Christmas obs
- **CN 2027**（法定日 closed only；调休待补）：01-01 元旦；02-05..08 除夕–初三；04-05 清明；05-01..02 劳动；06-09 端午；09-15 中秋；10-01..03 国庆

---

### Task 3 — B：list_packs + API `region`/`year` 过滤（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/holiday_packs.py` — `list_packs(*, region=None, year=None, root=None)`
- Modify: `backend/opentask/api/sla/router.py` — query params
- Create/extend: unit + api tests in `test_e64_*`

**Interfaces:**
- `list_packs(*, region: Optional[str] = None, year: Optional[int] = None, root: Optional[Path] = None) -> list[dict]`
- Filter：region 大小写不敏感；year 精确 int；无参 = 全量（回归）
- API：`GET /api/sla/holiday-packs?region=EU&year=2027`

- [ ] **Step 1: 红测**

```python
def test_list_packs_filter_region_year():
    rows = list_packs(region="eu", year=2027)
    assert rows and all(r["region"] == "EU" and r["year"] == 2027 for r in rows)
    assert list_packs(region="ZZ") == []
    assert len(list_packs()) >= 8

# API
async def test_list_filter_query(test_client):
    user = await _register(test_client)
    resp = await test_client.get(
        "/api/sla/holiday-packs",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"region": "UK", "year": 2026},
    )
    assert resp.status_code == 200
    rows = resp.json()["data"]["rows"]
    assert len(rows) == 1 and rows[0]["region"] == "UK" and rows[0]["year"] == 2026
```

- [ ] **Step 2:** FAIL（无过滤）
- [ ] **Step 3:** 实现过滤 + router Query
- [ ] **Step 4:** PASS；另加 `test_apply_eu_2026_ws` + webhook/no-emit spy（对齐 E58）
- [ ] **Step 5:** Commit `feat(E64): holiday-packs list region/year filter + apply regression`

---

### Task 4 — C：FE 列表/筛 + vitest

**Files:**
- Modify: `frontend/src/service/api/sla.ts` — `fetchHolidayPacks(params?: { region?: string; year?: number })`
- Modify: `frontend/src/views/settings/sla/index.vue` — 文案扩至 EU/UK/2027；可选 region/year NSelect；load 带参
- Modify: `frontend/src/utils/businessHours.test.ts` 或新建 `holidayPacks.e64.test.ts` — 断言包键集合（mock list 或纯函数筛）

- [ ] **Step 1:** 红测：筛函数或常量 `E64_PACK_KEYS` 含 EU/UK/2027
- [ ] **Step 2–4:** 实现 API params + UI 筛；vitest 绿；`pnpm run build` ok
- [ ] **Step 5:** Commit `feat(E64): FE holiday-pack EU/UK/2027 + region/year filter`

---

### Task 5 — D：CLI 1.48.0 + list flags

**Files:**
- Pins：`VERSION` / `opentask/__init__.py` / `opentask_cli.py` / `setup.py` / `pyproject.toml` → **1.48.0**
- 全仓 `1.47.0` → `1.48.0`（tests + integration）
- Modify: `opentask/core/sla.py` holiday-packs list `--region/--year`
- Modify: `opentask/utils/api_client.py` `list_holiday_packs(region=None, year=None)`
- Create: `tests/test_e64_holiday_packs.py`（version + list help flags）

- [ ] **Step 1: 红测** list `--help` 含 `--region` `--year`；version 1.48.0
- [ ] **Step 2–4:** 实现 + sed bump
- [ ] **Step 5:** Commit `feat(E64): CLI 1.48.0 holiday-packs list --region/--year`

---

### Task 6 — E：门禁 + acceptance

- [ ] BE full + directed `test_e64*` + `test_e58*`
- [ ] CLI full
- [ ] FE vitest + build
- [ ] 写 acceptance tip SHA + 门禁数；`superpowers: design/plan/TDD/verify/acceptance = ok`
- [ ] Commit `docs(E64): acceptance + tip`
- [ ] **STOP** — 不 push；不开 E65

