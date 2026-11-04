# E55 Plan：Insights 效能加厚 mid-thick — 切片 + 估点速度 + CSV · CLI 1.39.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`6e2c8d3` · 分支 `sprint/E55-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e55-insights-thicken-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E56**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Workspace 成员（viewer+）可对 Insights summary 按 project / label(tag) / cycle 切片；查看估点完成速度（14d 日桶）；导出 CSV；FE `/insights` 过滤条 + 速度卡 + 导出；CLI **1.39.0**；无报表构建器 / Push / formula emit。

**Architecture:** 扩展既有 `InsightsService.summary`（挂 query `projectId`/`labelId`；内部映射 Tag 表）；同服务加 `estimateVelocity` 与 `export_csv`；路由增 `GET /api/insights/export.csv`；FE 加厚既有页；CLI 钉 1.39.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E56；中文 docs；CLI **1.39.0**
- ADR D1–D7；Q1a–Q6a 全关（`labelId` 对外；Q2a 收窄 cycleSnapshot；Q3a 14d；Q4a 独立 export.csv；Q5a 单 label；Q6a stdout 默认 + `-o`）
- formula 永不 emit；不改 E52 Activity / E53 SLA / E54 webhook；无 Redis/cron/报表构建器
- 非目标见 design §2
- `TREND_DAYS = VELOCITY_DAYS = 14`；`labelId` → int（Tag.id）

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e55-insights-thicken.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E55-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e55-insights-thicken.md \
  docs/superpowers/acceptances/2026-11-05-E55-acceptance.md
git commit -m "docs(E55): plan + acceptance skeleton"
```

---

### Task 2 — A+B：Service 过滤 + estimateVelocity（TDD）

**Files:**
- Modify: `backend/opentask/services/insights/service.py`
- Create: `backend/tests/api/test_e55_insights_thicken.py`

**Interfaces:**
- Extends `InsightsService.summary(..., project_id: str | None = None, label_id: int | None = None)`
- `_ensure_project(workspace_id, project_id)` → 404 if missing/cross-tenant
- `_ensure_label(workspace_id, label_id)` → 404（Tag 表；对外叫 label）
- `_base_issue_filter(workspace_id, *, project_id=None, label_id=None)` — label 时 EXISTS IssueTag
- 所有计数/趋势/velocity/cycleSnapshot（Q2a）共用过滤
- Produces `estimateVelocity: { windowDays: 14, buckets: [{ date, completedPoints }] }`
  - completedPoints = Σ coalesce(estimate_points, 0) by day of `coalesce(closed_at, resolved_at)`
  - 软删不计；空窗仍 14 行（0.0）

- [ ] **Step 1: 红测**（节选关键断言；完整见测试文件）

```python
"""E55: Insights thicken — filters + velocity + CSV · no-emit."""
# helpers: _register/_auth/_create_issue/_create_cycle/_activate/_create_project/_create_tag/_attach_tag

@pytest.mark.asyncio
async def test_summary_no_filter_regression_has_velocity(test_client):
    # E24 字段仍在；新增 estimateVelocity.windowDays == 14；len(buckets)==14

@pytest.mark.asyncio
async def test_summary_project_filter_narrows_counts_and_cycle(test_client):
    # 两 project；过滤 projectA → status/priority/assignee/trend/cycleSnapshot 仅 A

@pytest.mark.asyncio
async def test_summary_label_filter_single_and_cross_tenant_404(test_client):
    # labelId 收窄；跨租户 labelId → 404；未知 projectId → 404

@pytest.mark.asyncio
async def test_estimate_velocity_sums_points_by_completion_day(test_client):
    # resolve 两 issue（3+5 pts）→ 当日 completedPoints >= 8；无估点 → 0

@pytest.mark.asyncio
async def test_export_csv_matches_summary_filters(test_client):
    # GET /api/insights/export.csv?projectId=&labelId=&cycleId=
    # Content-Type text/csv；含 status/priority/assignee/estimate_velocity 行

@pytest.mark.asyncio
async def test_insights_read_no_emit(test_client):
    # patch fire_webhooks → summary + export 不触发
```

- [ ] **Step 2:** Run → FAIL（无 projectId / estimateVelocity / export）
- [ ] **Step 3:** 实现 service + router
- [ ] **Step 4:** Run → PASS；commit

```bash
git add backend/opentask/services/insights/service.py \
  backend/opentask/api/insights/router.py \
  backend/tests/api/test_e55_insights_thicken.py
git commit -m "feat(E55): insights filters + estimateVelocity + export.csv (TDD)"
```

**Router 变更（`backend/opentask/api/insights/router.py`）：**
- `GET /summary` 增 query：`projectId: Optional[str]`、`labelId: Optional[int]`
- `GET /export.csv` 同过滤；`StreamingResponse` media_type=`text/csv; charset=utf-8`；filename=`insights-export.csv`

**CSV 扁平格式：**
```
kind,key,value
status,<status>,<count>
priority,<priority>,<count>
assignee,<assigneeId|unassigned>,<count>
estimate_velocity,<YYYY-MM-DD>,<completedPoints>
```

---

### Task 3 — D：FE 过滤条 + 速度卡 + 导出（TDD）

**Files:**
- Modify: `frontend/src/service/api/insights.ts`
- Modify: `frontend/src/service/api/insights.test.ts`
- Modify: `frontend/src/views/insights/index.vue`

**Interfaces:**
- `InsightsEstimateVelocity = { windowDays: number; buckets: { date: string; completedPoints: number }[] }`
- `InsightsSummary` 增 `estimateVelocity`
- `fetchInsightsSummary({ cycleId?, projectId?, labelId?, assigneeLimit? })`
- `buildInsightsSummaryParams(input) -> Record` — 空串/ null / undefined 省略键
- `sumVelocityPoints(buckets, days?) -> number`
- `insightsExportUrl(params) -> '/api/insights/export.csv?…'`
- 页面：Project / Label / Cycle 下拉；速度柱（简易 CSS 条，无重 BI）；导出按钮（`window.open` 或 `<a download>` 带 workspace header 走 request blob 亦可——优先用 `request` blob + object URL）

- [ ] **Step 1: 红测** vitest normalize / empty velocity
- [ ] **Step 2:** FAIL
- [ ] **Step 3:** 实现 helpers + 页面
- [ ] **Step 4:** vitest PASS；commit

```bash
git add frontend/src/service/api/insights.ts frontend/src/service/api/insights.test.ts \
  frontend/src/views/insights/index.vue
git commit -m "feat(E55): FE insights filters + velocity + export"
```

---

### Task 4 — E：CLI 1.39.0

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/insights.py`
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py` — `insights_summary` 增参；`insights_export(...)`
- Modify pins: `pyproject.toml` / `__init__.py` / `setup.py` / `VERSION` / `opentask_cli.VERSION` → **1.39.0**
- Sync 全部历史 `1.38.0` 断言 → `1.39.0`
- Create: `agent-harness/opentask-cli/tests/test_e55_insights_thicken.py`
- Update: `tests/test_e24_insights.py` version + help 断言

**Interfaces:**
- `insights summary [--project-id] [--label-id] [--cycle] [--json]`
- `insights export [--project-id] [--label-id] [--cycle] [-o path]` — Q6a stdout 默认
- client: `insights_summary(cycle_id=, project_id=, label_id=, assignee_limit=)`
- client: `insights_export(...)` → GET raw text/csv（或 `get_raw`）

- [ ] **Step 1: 红测** version / help flags / export help
- [ ] **Step 2–4:** bump + 实现 + PASS；commit

```bash
# sed 批量钉版本后
git add agent-harness/opentask-cli
git commit -m "feat(E55): CLI 1.39.0 insights summary filters + export"
```

---

### Task 5 — F 门禁 + acceptance tip

- [ ] BE full + targeted E55+E24 insights
- [ ] CLI full；确认 pins 全 **1.39.0**
- [ ] FE vitest + build
- [ ] 记 flake `test_user_search` 若出现
- [ ] 更新 acceptance tip SHA；commit；**STOP**；不 push；不自开 E56

```bash
git add docs/superpowers/acceptances/2026-11-05-E55-acceptance.md
git commit -m "docs(E55): acceptance tip = sprint tip"
```

## Self-review
- A–F / D1–D7 / Q1a–Q6a 均有任务覆盖
- 无 placeholder；labelId=int；Q2a cycleSnapshot 收窄；CSV 独立路径；CLI stdout+`-o`
