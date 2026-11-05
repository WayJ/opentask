# E59 Plan：Insights 再厚 / 效能日报 mid — 多 label OR +「我的报表」+ digest · CLI 1.43.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`e52ad34` · 分支 `sprint/E59-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e59-insights-saved-reports-digest-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E60**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** viewer+ 可对 Insights summary/export 用多 label OR；CRUD 个人「我的报表」（cap 20、isDefault≤1）；可选效能 digest（外部 tick → Inbox + E30 邮件）；FE `/insights` 多选标签 + 我的报表 + digest 开关；CLI **1.43.0**；无报表构建器 / Push / formula emit。

**Architecture:** 扩展既有 `InsightsService` 为 `label_ids: list[int]|None`（OR EXISTS）；新表 `insights_saved_reports` + CRUD API；pref `insights_digest` + 账本 `insights_digest_deliveries` + `POST /api/insights/run-digest`；FE 薄加；CLI 钉 1.43.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest；alembic。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E60；中文 docs；CLI **1.43.0**
- ADR D1–D7；Q1a–Q6a 全关
- formula 永不 emit；不改 E57 告警 / E58 假日包 / Activity；无新 webhook 事件；无内置 cron
- 非目标见 design §2
- REPORT_CAP=20；digest 默认关；tick 权限对齐 E39 `require_writer`

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e59-insights-saved-reports-digest.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E59-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e59-insights-saved-reports-digest.md \
  docs/superpowers/acceptances/2026-11-05-E59-acceptance.md
git commit -m "docs(E59): plan + acceptance skeleton"
```

---

### Task 2 — A：多 label OR（TDD）

**Files:**
- Modify: `backend/opentask/services/insights/service.py` — `label_ids` OR；`_parse`/`_ensure_labels`
- Modify: `backend/opentask/api/insights/router.py` — `labelIds` 重复+逗号；与 `labelId` 同传 → 400
- Create: `backend/tests/api/test_e59_insights_saved_reports_digest.py`（先写 A 段）

**Interfaces:**
- `resolve_label_ids(label_id, label_ids_raw) -> list[int]|None`
  - 重复 query + comma；同传 labelId+labelIds → HTTP 400
  - 空 → None（不过滤）；单 labelId → `[id]`
- `InsightsService.summary(..., label_ids: list[int]|None=None, label_id: int|None=None)`  
  - 内部归一：若两者都给且冲突由 router 挡；service 优先 label_ids，否则 wrap label_id
- `_base_issue_filter(..., label_ids=None)`：`exists(IssueTag.tag_id.in_(label_ids))` OR
- `_ensure_labels`：任一非法/跨租户 → 404
- cycleSnapshot / velocity / trend 一并收窄（E55 Q2a）
- export.csv 同参

- [ ] **Step 1: 红测** A 段（见测试文件）
- [ ] **Step 2:** Run → FAIL
- [ ] **Step 3:** 实现 service + router
- [ ] **Step 4:** Run → PASS；E55 回归绿
- [ ] **Step 5:** Commit `feat(E59): insights multi-label OR filters`

---

### Task 3 — B：insights_saved_reports CRUD + alembic（TDD）

**Files:**
- Create: `backend/opentask/models/insights_saved_report/model.py` + `__init__.py`
- Modify: `backend/opentask/models/__init__.py`
- Create: `backend/alembic/versions/2026_11_05_4400-r4a5b6c7d8e2_insights_saved_reports_digest.py`（revises `q3f4a5b6c7d1`）
- Modify: `backend/opentask/services/insights/service.py` — reports CRUD + serialize
- Modify: `backend/opentask/api/insights/router.py` — GET/POST/PATCH/DELETE reports
- Extend: `backend/tests/api/test_e59_insights_saved_reports_digest.py`

**Interfaces:**
- Model `InsightsSavedReport`: id, workspace_id, owner_user_id, name, filters JSON, is_default bool, created_at, updated_at
- Cap 20 / user / WS → 400 when exceed
- Q6a：设 isDefault=true 时清除同用户同 WS 其它 default
- API：`/api/insights/reports` list/create；`/api/insights/reports/{id}` patch/delete
- 跨租户 / 非本人 → 404；viewer+ CRUD own
- Q4a：无 `…/summary` 专用端点
- filters shape: `{ projectId?, labelIds?, cycleId?, assigneeLimit? }`

- [ ] 红→绿→commit `feat(E59): insights saved reports CRUD`

---

### Task 4 — C：digest pref + 账本 + run-digest（TDD）

**Files:**
- Create: `backend/opentask/models/insights_digest_delivery/model.py` + `__init__.py`
- Modify: `backend/opentask/models/notification_preference/model.py` — `insights_digest` + TYPE map
- Modify: `backend/opentask/services/notification/service.py` — serialize/upsert
- Modify: `backend/opentask/api/inbox/router.py` — PrefsBody
- Modify: `backend/opentask/services/insights/service.py` — `run_digest`
- Modify: `backend/opentask/api/insights/router.py` — `POST /run-digest` + require_writer
- Modify: `backend/tests/conftest.py` — ALTER prefs column
- Extend tests

**Interfaces:**
- Pref `insights_digest` bool default **false**（类 due_reminder_digest）
- Inbox type `insights_digest` → TYPE_TO_PREF_KEY
- Ledger `insights_digest_deliveries`: unique `(workspace_id, user_id, bucket_date)`
- `run_digest(workspace_id, actor)`：成员 prefs on → default report filters else 全 WS；写 ≤1 Inbox/day；同日幂等；`_maybe_send_email`
- Tick：`require_writer`（对齐 E39）
- spy：无 fire_webhooks / automations

- [ ] 红→绿→commit `feat(E59): insights digest tick + ledger`

---

### Task 5 — D：FE 多选 + 我的报表 + digest

**Files:**
- Modify: `frontend/src/service/api/insights.ts` + `insights.test.ts`
- Modify: `frontend/src/views/insights/index.vue`

**Interfaces:**
- `labelIds?: number[]`；`normalizeLabelIds`；空=不过滤；build params 发重复 `labelIds`
- reports CRUD helpers；digest prefs 读写（inbox prefs API）
- UI：Label 多选 + OR 提示；「我的报表」下拉（应用/另存为/删除/设默认）；digest 开关

- [ ] vitest 绿 → commit `feat(E59): FE multi-label + my reports + digest`

---

### Task 6 — E：CLI 1.43.0

**Files:**
- Bump：`pyproject.toml` / `__init__.py` / `setup.py` / `VERSION` / `opentask_cli.VERSION`
- Sync：所有历史 `1.42.0` 断言 → `1.43.0`
- Modify：`opentask/core/insights.py` + `api_client.py`
- Create：`tests/test_e59_insights_reports_digest.py`

**Commands:**
- `insights summary|export` + `--label-ids`
- `insights reports list|create|delete`（create 支持 `--default`）
- `insights run-digest [--yes]`

- [ ] CLI 绿 → commit `feat(E59): CLI 1.43.0 insights reports + digest`

---

### Task 7 — 门禁 + acceptance tip

- BE full + targeted E59+E55+E24；CLI；FE vitest+build
- 填 tip SHA / 测数；`superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP**；不 push；不开 E60
