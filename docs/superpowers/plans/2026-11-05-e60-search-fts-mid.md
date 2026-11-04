# E60 Plan：Search FTS mid — 方言全文检索（Issue/Project/Doc）· CLI 1.44.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`0fb0df5` · 分支 `sprint/E60-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e60-search-fts-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E61**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Workspace viewer+ 对 `GET /api/search` 在 Postgres 走 tsvector+GIN、在 SQLite 走 FTS5（同一契约）；Issue 入索 description；可选 rank/snippet；FE 薄接；CLI **1.44.0** 顶层 `search`；无外部引擎 / Push / Insights·E57–E59 主表面改动 / formula emit。

**Architecture:** `SearchBackend` 抽象按 `session.bind.dialect.name` 选择 PostgresFTS / SQLiteFTS / ILike 降级；`SearchService` 保留 exact issue_code 置顶与 Member ILIKE；alembic 加 PG generated `search_tsv`+GIN 与 SQLite FTS5+triggers；API 可选 rank/snippet；CLI 钉 1.44.0。

**Tech Stack:** FastAPI + SQLAlchemy async；Postgres tsvector / SQLite FTS5；Vue3 + vitest；Click CLI；pytest；alembic。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E61；中文 docs；CLI **1.44.0**
- ADR D1–D7；Q1a–Q6a 全关（simple+plainto_tsquery；Member ILIKE；FTS5 triggers；截断 16KiB / snippet≤120；rank DESC+updated_at；顶层 search）
- formula 永不 emit；不改 E57 告警 / E58 假日包 / E59 Insights 主表面；无 Meili/Elastic；无 Push
- 已知 flake `test_user_search` 记入 acceptance，不挡
- 非目标见 design §2

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e60-search-fts-mid.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E60-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e60-search-fts-mid.md \
  docs/superpowers/acceptances/2026-11-05-E60-acceptance.md
git commit -m "docs(E60): plan + acceptance skeleton"
```

---

### Task 2 — A：SearchBackend 抽象 + ILIKE 降级 + description（TDD）

**Files:**
- Create: `backend/opentask/services/search/backend.py`
- Modify: `backend/opentask/services/search/service.py` — 委托 backend；exact code 置顶；members ILIKE
- Modify: `backend/opentask/services/search/__init__.py`
- Create: `backend/tests/api/test_e60_search_fts.py`（先写 A/B/G 段）
- Create: `backend/tests/services/test_e60_search_backend.py`（方言选择 / 降级）

**Interfaces:**
```python
@dataclass
class SearchHit:
    id: str
    rank: float | None = None
    snippet: str | None = None
    # entity payload fields merged by SearchService

class SearchBackend(Protocol):
    async def search_issues(self, workspace_id: str, q: str, limit: int) -> list[dict]: ...
    async def search_projects(self, workspace_id: str, q: str, limit: int) -> list[dict]: ...
    async def search_docs(self, workspace_id: str, q: str, limit: int) -> list[dict]: ...

def resolve_search_backend(session: AsyncSession) -> SearchBackend:
    # postgresql → PostgresFTSBackend; sqlite → SQLiteFTSBackend; else → ILikeSearchBackend

INDEX_BODY_MAX = 16000  # Q4a
SNIPPET_MAX = 120
```

- Hit dict shape 对齐 E17 + 可选 `rank`/`snippet`
- Issue ILIKE（降级）含 **description**
- Project ILIKE 含 name+description
- Doc ILIKE title+body_md；snippet ≤120
- 空 q → 空分组；limit clamp 1..50
- exact ISSUE_CODE_RE 命中置顶（E17 D3 / Q5a）

- [ ] **Step 1: 红测** description 命中 / 空 q / 未知方言降级
- [ ] **Step 2:** Run → FAIL
- [ ] **Step 3:** backend + service 接线
- [ ] **Step 4:** Run → PASS；E17 回归绿
- [ ] **Step 5:** Commit `feat(E60): SearchBackend abstract + ILIKE description`

---

### Task 3 — C+B：PG tsvector+GIN alembic + PostgresFTSBackend（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_4500-s5b6c7d8e9f3_search_fts_mid.py`（revises `r4a5b6c7d8e2`）
- Modify: `backend/opentask/services/search/backend.py` — `PostgresFTSBackend`
- Modify: `backend/tests/conftest.py` — ADD search_tsv GENERATED + GIN（测库 create_all 不生成）
- Extend: `backend/tests/api/test_e60_search_fts.py`

**Migration (PG branch):**
```sql
-- issues
ALTER TABLE issues ADD COLUMN IF NOT EXISTS search_tsv tsvector
  GENERATED ALWAYS AS (
    to_tsvector('simple',
      coalesce(title,'') || ' ' ||
      coalesce(issue_code,'') || ' ' ||
      coalesce(legacy_issue_code,'') || ' ' ||
      left(coalesce(description,''), 16000)
    )
  ) STORED;
CREATE INDEX IF NOT EXISTS ix_issues_search_tsv ON issues USING GIN (search_tsv);
-- projects: name + description
-- entity_documents: title + body_md
```

**Query (Q1a/Q5a):**
```python
tsv = Issue.__table__.c.search_tsv  # or text column
q = plainto_tsquery('simple', query)
WHERE workspace_id == ws AND search_tsv @@ q
ORDER BY ts_rank(search_tsv, q) DESC, updated_at DESC
```

- SQLite branch of migration: CREATE FTS5 virtual tables + triggers（Task 4 共用同一 revision）
- backfill：GENERATED STORED 自带；FTS5 INSERT SELECT 一次性

- [ ] 红→绿→commit `feat(E60): PG tsvector+GIN + PostgresFTSBackend`

---

### Task 4 — SQLite FTS5 + triggers + 单元测（TDD）

**Files:**
- Extend migration SQLite branch
- Extend: `backend/opentask/services/search/backend.py` — `SQLiteFTSBackend`
- Extend: `backend/tests/services/test_e60_search_backend.py` — in-memory FTS5 MATCH / delete 后不命中 / trigger 同步

**SQLite DDL (Q3a):**
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS issues_fts USING fts5(
  id UNINDEXED, workspace_id UNINDEXED,
  title, issue_code, legacy_issue_code, description,
  tokenize='unicode61'
);
-- triggers AFTER INSERT/UPDATE/DELETE on issues
-- same for projects_fts, entity_documents_fts
```

**Query:** `issues_fts MATCH :q` + `bm25(issues_fts)` as rank；join/filter workspace_id；ORDER BY rank ASC (bm25 lower better → invert to rank DESC semantics) then updated_at.

- [ ] 红→绿→commit `feat(E60): SQLite FTS5 + triggers backend`

---

### Task 5 — D+G：API rank/snippet + 租户隔离 + no-emit spy

**Files:**
- Modify: `backend/opentask/api/search/router.py`（若需；通常透传 service）
- Extend tests：跨租户 403；description 命中带 rank；spy `fire_webhooks` 不触发；不触 E57/E58/E59

- [ ] 红→绿→commit `feat(E60): search API rank/snippet + isolation spies`

---

### Task 6 — E：FE 薄接 rank/snippet

**Files:**
- Modify: `frontend/src/service/api/search.ts` — optional `rank?`/`snippet?`
- Modify: `frontend/src/utils/global-search.ts` — flatten 兼容缺省 rank；issue/project subtitle 可用 snippet；同组若有 rank 则已由 API 排序（FE 不重排强制，但测试兼容）
- Modify: `frontend/src/utils/global-search.test.ts`
- Thin：`views/search/index.vue` / global-search 若展示 subtitle 已够

- [ ] vitest 绿 → commit `feat(E60): FE search rank/snippet thin`

---

### Task 7 — F：CLI 1.44.0 `search`

**Files:**
- Bump：`pyproject.toml` / `__init__.py` / `setup.py` / `VERSION` / `opentask_cli.VERSION`
- Sync：全部历史 `1.43.0` 断言 → `1.44.0`（`rg -l` 批量）
- Create：`agent-harness/opentask-cli/opentask/core/search.py`
- Modify：`opentask_cli.py` — `cli.add_command(search_cli)`
- Modify：`api_client.py` — `async def global_search(q, limit=10)`
- Create：`tests/test_e60_search.py`

**Command (Q6a):**
```bash
opentask search <q> [--limit N] [--json]
```

- [ ] CLI 绿 → commit `feat(E60): CLI 1.44.0 top-level search`

---

### Task 8 — 门禁 + acceptance tip

- BE full + targeted E60+E17；CLI；FE vitest+build
- 填 tip SHA / 测数；`superpowers: design/plan/TDD/verify/acceptance = ok`
- Final tip commit 记录 HEAD
- **STOP**；不 push；不开 E61

