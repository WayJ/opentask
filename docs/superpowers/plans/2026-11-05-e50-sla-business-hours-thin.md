# E50 Plan：SLA business hours thin — timezone + weekday windows · CLI 1.34.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`a77e2cf` · 分支 `sprint/E50-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e50-sla-business-hours-thin-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E51**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** WS 可配置 IANA timezone + 周内营业窗口；SLA `deadline_at` / pause-resume / run_due 按营业分钟；enabled=false 回退墙钟；配置变更批量重算；FE 薄设置；CLI **1.34.0**；无节假日/policy 覆盖。

**Architecture:** 纯函数 `add_business_minutes` / `elapsed_business_minutes`（`zoneinfo`）；Workspace 列 `timezone` + `business_hours` JSON；SlaService create/resume/pause elapsed 走加法器；Workspace.update 同事务重算 running/paused；FE SLA 设置页旁营业时区编辑；CLI workspace/sla 读写。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic；zoneinfo；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E51；中文 docs；CLI **1.34.0**
- Q1a Workspace；Q2a 无 policy 覆盖；Q3a alembic；Q4a elapsed=营业分钟 when enabled；Q5a 批量重算；Q6a 每日最多 2 段
- ADR D1–D8（design §4）；formula 永不 emit；HMAC 不变；无 Redis/cron
- 非目标见 design §2
- 重算封顶 `RECOMPUTE_CAP=500`；超额记 warning 日志

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e50-sla-business-hours-thin.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E50-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

---

### Task 2 — A：纯函数 business minutes（TDD）

**Files:**
- Create: `backend/opentask/services/sla/business_hours.py`
- Create: `backend/tests/unit/test_e50_business_hours.py`

**Interfaces:**
- Produces:
  - `WEEKDAY_KEYS = ("mon","tue","wed","thu","fri","sat","sun")`
  - `normalize_windows(windows: dict|None) -> dict[str, list[dict]]` — 校验 HH:MM；每日 ≤2；`start < end` 否则 400（`HTTPException` 或 `ValueError` 由调用方转 400）；重叠合并
  - `validate_timezone(name: str|None) -> str|None` — 空/None OK；非法 IANA → ValueError
  - `normalize_business_hours(raw: dict|None) -> dict` → `{enabled: bool, windows: {...}}`
  - `add_business_minutes(start_utc: datetime, minutes: int, tz_name: str, windows: dict) -> datetime`（naive UTC out）
  - `elapsed_business_minutes(a_utc, b_utc, tz_name, windows) -> int`
  - `DEFAULT_WINDOWS`：全空；`WEEKDAY_PRESET_09_18`：mon–fri 09:00–18:00

- [ ] **Step 1: 红测**
  - 同日窗口内：Asia/Shanghai 周一 10:00 + 60min → 11:00
  - 跨午休：09–12 + 13–18，11:30 + 60 → 14:30
  - 跨周末：周五 17:00 + 120（仅工作日 09–18）→ 下周一 10:00
  - enabled 路径外：`elapsed` 半开边界；空日不计
  - normalize：倒置拒；重叠合并；>2 段拒；非法 IANA 拒
- [ ] **Step 2: 跑红 → 最小实现绿 → commit**

---

### Task 3 — B：Alembic + Workspace 模型/API（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_3900-m9b0c1d2e3f7_workspace_business_hours.py`（revises `l8a9b0c1d2e6`）
- Modify: `backend/opentask/models/workspace/model.py` — `timezone: Optional[str]`；`business_hours: dict` JSON default `{enabled:false, windows:{}}`
- Modify: `backend/opentask/schemas/workspace.py` — Update/Out += `timezone` / `businessHours`
- Modify: `backend/opentask/api/workspace/router.py` — `_ws_out` += 两字段
- Modify: `backend/opentask/services/workspace/service.py` — update 校验 + 写；变更时调 `SlaService.recompute_deadlines_for_workspace`；**不** fire webhook/automation
- Modify: `backend/tests/conftest.py` — additive ALTER timezone + business_hours
- Test: `backend/tests/api/test_e50_sla_business_hours.py`

**Interfaces:**
- Consumes: normalize_* from Task 2
- Produces: WS PATCH 读写；跨租户 404；owner 写

- [ ] **Step 1: 红测**
  - GET 默认 timezone=null / businessHours.enabled=false
  - PATCH 合法 Asia/Shanghai + windows OK
  - 非法 IANA / 倒置 / >2 段 → 400
  - 他 WS owner 不可改本 WS；viewer 403
  - spy：配置写路径 `fire_webhooks`/`fire_automations` 未调用
- [ ] **Step 2: 绿 → commit**

---

### Task 4 — C：接线 SLA create/pause/resume/recompute（TDD）

**Files:**
- Modify: `backend/opentask/services/sla/service.py`
  - 加载 WS；若 `business_hours.enabled` 且 timezone：create/resume 用 `add_business_minutes`；pause 累加用 `elapsed_business_minutes`；else 墙钟
  - `async def recompute_deadlines_for_workspace(workspace_id, *, cap=500) -> dict`：扫 running/paused；重算 deadline；超额 log warning
- Extend: `backend/tests/api/test_e50_sla_business_hours.py`

- [ ] **Step 1: 红测**
  - enabled=true：周五傍晚 start + 短 target → deadline 跳过周末（钉死样例）
  - enabled=false：与墙钟一致（E45 语义）
  - pause 期间不计营业分钟；resume 剩余营业分钟重算
  - first_response 与 time_in_status 共用加法器；breach payload 仍含 metric
  - 配置变更后 running deadline 变；跨租户隔离
  - formula no-emit spy（配置写 + SLA 读）
- [ ] **Step 2: 绿 → commit**

---

### Task 5 — E：FE 薄设置（TDD）

**Files:**
- Modify: `frontend/src/service/api/workspace.ts` — types += timezone/businessHours；update body
- Create: `frontend/src/utils/businessHours.ts` — normalize / weekday preset / validate
- Create: `frontend/src/utils/businessHours.test.ts`
- Modify: `frontend/src/views/settings/sla/index.vue` — 营业时段卡片：timezone + enabled + 周历编辑 +「工作日 09–18」预设 + 保存（owner）
- Optional: Issue SLA 徽标「营业时」提示（非必须；可薄一行）

- [ ] **Step 1: 红测** vitest normalize / preset / 非法时段
- [ ] **Step 2: 绿 + build → commit**

---

### Task 6 — F：CLI **1.34.0**

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py` — `update_workspace`
- Modify: `agent-harness/opentask-cli/opentask/core/workspace.py` — show 显示；`update` 子命令 `--timezone` / `--business-hours-enabled` / `--business-hours-json`
- Modify: `agent-harness/opentask-cli/opentask/core/sla.py` — `business-hours show|set`；run-due help 注明营业时
- Pin: `__init__.py` / `opentask_cli.py` / `setup.py` / `pyproject.toml` / `VERSION` → **1.34.0**；全仓历史 version 断言 → 1.34.0
- Create: `agent-harness/opentask-cli/tests/test_e50_sla_business_hours.py`

- [ ] **Step 1: 红测** version 1.34.0；workspace update / sla business-hours help
- [ ] **Step 2: 绿 → commit**

---

### Task 7 — 门禁 + acceptance tip

- [ ] BE 定向 `test_e50_*` + `test_e48_*` + `test_e45_*`；全量（记 passed；`test_user_search` flake 可记）
- [ ] CLI 全量；确认所有 pin **1.34.0**
- [ ] FE vitest + build
- [ ] 填写 acceptance；最终 tip commit
- [ ] **STOP**；不 push；不自开 E51

---

## Self-Review
1. Spec A–E / 验收 A–H / ADR D1–D8 / Q1–Q6 均有 Task 覆盖  
2. 无 TBD/placeholder  
3. Alembic revises `l8a9b0c1d2e6`；CLI 全钉 1.34.0；重算封顶 500
