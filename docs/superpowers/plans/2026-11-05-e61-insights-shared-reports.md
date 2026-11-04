# E61 Plan：Insights 共享报表 mid — personal→WS 只读共享 · CLI 1.45.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`36dfb75` · 分支 `sprint/E61-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e61-insights-shared-reports-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E62**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Workspace 成员可将本人 Insights 报表分享为 workspace 可见；任意成员可列出「我的 personal ∪ WS shared」并应用 filters；非 owner 只读 + fork 为本人 personal；digest 仍仅本人 default；FE 我的/团队分区；CLI **1.45.0**；无报表构建器 / Push / formula emit。

**Architecture:** 在既有 `insights_saved_reports` 加 `visibility`（personal|workspace）；扩展 list/create/update ACL + shared cap；新 `POST …/fork`；复用 summary/export；FE 薄加；CLI 钉 1.45.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest；alembic。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E62；中文 docs；CLI **1.45.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；不改 E57 告警 / E58 假日包 / E60 Search 主表面；无新 webhook 事件；无 Inbox 广播 on share
- PERSONAL_REPORT_CAP=20 / user / WS（visibility=personal）；SHARED_REPORT_CAP=50 / WS（visibility=workspace）
- 非 owner 写 → **404**；viewer 不可 share（member+）；digest 语义保持 E59

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e61-insights-shared-reports.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E61-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e61-insights-shared-reports.md \
  docs/superpowers/acceptances/2026-11-05-E61-acceptance.md
git commit -m "docs(E61): plan + acceptance skeleton"
```

---

### Task 2 — A：alembic visibility + model（TDD 伴随 Task 3）

**Files:**
- Modify: `backend/opentask/models/insights_saved_report/model.py` — `visibility` String(16) default `personal`
- Create: `backend/alembic/versions/2026_11_05_4600-t6c7d8e9f0a4_insights_report_visibility.py`（revises `s5b6c7d8e9f3`）
- Modify: `backend/tests/conftest.py` — additive `ALTER … ADD COLUMN IF NOT EXISTS visibility`

**Interfaces:**
- Column `visibility: str` ∈ {`personal`,`workspace`}; server_default `personal`
- Backfill existing rows → `personal`
- Optional index `idx_insights_reports_ws_visibility` on `(workspace_id, visibility)`
- No team ACL / link tokens

- [ ] **Step 1:** 写迁移 + model；conftest ALTER
- [ ] **Step 2:** Commit `feat(E61): insights report visibility column`

---

### Task 3 — B：list / ACL / share / caps / fork（TDD）

**Files:**
- Modify: `backend/opentask/services/insights/service.py`
- Modify: `backend/opentask/api/insights/router.py`
- Create: `backend/tests/api/test_e61_insights_shared_reports.py`

**Interfaces:**
- Constants: `VIS_PERSONAL="personal"`, `VIS_WORKSPACE="workspace"`, `SHARED_REPORT_CAP=50`
- `serialize_saved_report(row, *, viewer_user_id: str) -> dict` adds:
  - `visibility`, `canEdit` (= owner), keep `ownerUserId`/`isDefault`
- `list_reports(*, workspace_id, owner_user_id)` → mine (any vis) ∪ `visibility=workspace` in WS；order `updated_at DESC`
- `create_report(..., visibility="personal", actor_role=...)`:
  - default personal；`workspace` 需 role ∈ {owner,member} 否则 403
  - personal cap：count owner+personal ≥20 → 400
  - shared cap：count WS+workspace ≥50 → 400
- `update_report(..., visibility=None, actor_role=...)`：仅 owner（`_get_own_report` → 404）；改 visibility 时校验 role+caps；分享不 clear `is_default`
- `delete_report`：仅 owner
- `fork_report(*, workspace_id, actor_user_id, report_id, name=None, actor_role=...)`：
  - source = own OR shared-in-WS，否则 404
  - 新建 personal，filters 深拷贝，name 默认 `副本 · {src.name}`，is_default=False
  - 走 personal cap
- Router：
  - `ReportCreateBody.visibility: Optional[str] = "personal"`
  - `ReportPatchBody.visibility: Optional[str] = None`
  - `ReportForkBody.name: Optional[str] = None`
  - `POST /api/insights/reports/{report_id}/fork`
  - pass `member.role` into service for share gates

**Red tests (file):**
```python
# helpers: _register, _auth, _add_member (from invites pattern)

async def test_share_visible_to_teammate_and_unshare(test_client):
    owner = await _register(...); mate = await _register(...); await _add_member(..., mate, "member")
    # owner create personal → mate list 不见
    # owner patch visibility=workspace → mate list 见；canEdit False for mate, True for owner
    # owner patch personal → mate 不见

async def test_non_owner_patch_delete_404(test_client): ...

async def test_viewer_cannot_share_403(test_client):
    # owner add viewer; viewer create personal ok; create/patch workspace → 403

async def test_fork_copies_filters_personal(test_client): ...

async def test_shared_cap_50_and_personal_cap_20(test_client): ...

async def test_cross_tenant_shared_isolated(test_client): ...

async def test_digest_unaffected_by_peer_shared_default(test_client):
    # peer shares default report; actor digest still uses own default / WS fallback
    # fire_webhooks spy not called; no extra inbox for peer on share

async def test_share_does_not_broadcast_inbox(test_client): ...
```

- [ ] **Step 1:** 写红测 → FAIL
- [ ] **Step 2:** 实现 service + router → PASS；E59 回归绿
- [ ] **Step 3:** Commit `feat(E61): insights shared reports ACL + fork`

---

### Task 4 — D：FE 我的/团队 + share/fork

**Files:**
- Modify: `frontend/src/service/api/insights.ts` + `insights.test.ts`
- Modify: `frontend/src/views/insights/index.vue`

**Interfaces:**
- `InsightsSavedReport` += `visibility?: 'personal'|'workspace'`, `canEdit?: boolean`
- `createInsightsReport` / `patchInsightsReport` accept `visibility?`
- `forkInsightsReport(id, { name? })`
- Helpers: `partitionReports(rows, currentUserId)` → `{ mine, shared }`；`canEditReport(r, userId)`
- UI：两个 Select / 分组「我的报表」「团队报表」；owner 分享开关；非 owner「另存为我的」(fork)；无编辑删除按钮当 `!canEdit`

- [ ] vitest 绿 → commit `feat(E61): FE shared reports partitions + fork`

---

### Task 5 — E：CLI 1.45.0

**Files:**
- Bump：`pyproject.toml` / `__init__.py` / `setup.py` / `VERSION` / `opentask_cli.VERSION`（凡钉 1.44.0 → 1.45.0）
- Modify：`opentask/core/insights.py` + `utils/api_client.py`
- Create：`tests/test_e61_insights_shared_reports.py`
- Update：`tests/test_e59_insights_reports_digest.py` version asserts

**Commands:**
- `insights reports list [--mine|--shared|--all] [--json]`（默认 all；client-side filter on visibility/owner if API returns union）
- `insights reports create … [--visibility personal|workspace]`
- `insights reports set-visibility <id> personal|workspace`
- `insights reports fork <id> [--name]`
- keep delete / summary `--label-ids` / run-digest

- [ ] CLI 绿 → commit `feat(E61): CLI 1.45.0 insights shared reports`

---

### Task 6 — 门禁 + acceptance tip

- BE full + targeted E61+E59+E55；CLI；FE vitest+build
- 填 tip SHA / 测数；`superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；不 push；不开 E62

## Spec coverage self-check
| Design | Task |
|--------|------|
| A visibility + alembic | T2 |
| B list/ACL/share/fork/caps | T3 |
| C digest 不变 / 无 Inbox 广播 | T3 tests |
| D FE 分区 | T4 |
| E CLI 1.45.0 | T5 |
| F tenant / no-emit / 不改 E57–E60 | T3 + T6 |
