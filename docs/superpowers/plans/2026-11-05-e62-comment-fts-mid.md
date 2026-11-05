# E62 Plan：评论全文入索 mid — IssueComment → SearchBackend · CLI 1.46.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`6fdeba8` · 分支 `sprint/E62-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e62-comment-fts-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E63**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Workspace viewer+ 对 `GET /api/search` 可命中本 WS Issue 的评论正文；结果以新分组 `comments` 返回（含 issueId/issueCode/snippet）；PG tsvector + SQLite FTS5 + ILike 降级；FE/⌘K 薄接；CLI **1.46.0**；无 Meili / Push / Insights·E57–E58 主表面改动 / formula emit。

**Architecture:** 扩展 E60 `SearchBackend` 加 `search_comments`；租户经 `JOIN issues.workspace_id`；过滤 `comment_type=COMMENT`、评论/Issue `is_deleted=false`；`SearchService.search` 加法返回 `comments`；exact issue_code 置顶仍仅 issues 组。

**Tech Stack:** FastAPI + SQLAlchemy async；Postgres tsvector / SQLite FTS5；Vue3 + vitest；Click CLI；pytest；alembic。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E63；中文 docs；CLI **1.46.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；不改 E57 告警 / E58 假日包 / E61 Insights 主表面；无 Meili/Elastic；无 Push
- 复用 E60 SearchBackend — 仅加法；不改 Issue/Project/Doc 语义
- 已知 flake `test_user_search` 记入 acceptance，不挡
- 非目标见 design §2

---

### Task 1 — Docs 骨架

**Files:**
- Create: `docs/superpowers/plans/2026-11-05-e62-comment-fts-mid.md`（本文件）
- Create: `docs/superpowers/acceptances/2026-11-05-E62-acceptance.md`（骨架；收口补 tip/测数）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e62-comment-fts-mid.md \
  docs/superpowers/acceptances/2026-11-05-E62-acceptance.md
git commit -m "docs(E62): plan + acceptance skeleton"
```

---

### Task 2 — A：alembic + conftest + SearchBackend.search_comments（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_4700-u7d8e9f0a1b5_comment_fts_mid.py`（revises `t6c7d8e9f0a4`）
- Modify: `backend/tests/conftest.py` — PG `issue_comments.search_tsv`+GIN bootstrap
- Modify: `backend/opentask/services/search/backend.py` — Protocol + 三后端 `search_comments`
- Create: `backend/tests/api/test_e62_comment_fts.py`
- Extend: `backend/tests/services/test_e60_search_backend.py` — SQLite FTS5 comments trigger sync

**Interfaces:**
```python
# Protocol addition
async def search_comments(self, workspace_id: str, q: str, limit: int) -> list[dict]: ...

# Hit shape (Q1a)
{
  "id": str,              # comment id
  "issueId": str,
  "issueCode": str,
  "snippet": str,         # ≤ SNIPPET_MAX (120)
  "rank": float | None,
  "authorUserId": str | None,
  "createdAt": str | None,  # ISO optional
}

# Filters (Q2a/Q3a/Q4a)
# - JOIN issues ON issues.id = issue_comments.issue_id
# - issues.workspace_id = :ws AND issues.is_deleted = false
# - issue_comments.is_deleted = false
# - issue_comments.comment_type = 'comment'  (CommentType.COMMENT)
# - content truncated to INDEX_BODY_MAX (16000) at index time
```

**Migration PG:**
```sql
ALTER TABLE issue_comments ADD COLUMN IF NOT EXISTS search_tsv tsvector
  GENERATED ALWAYS AS (
    to_tsvector('simple', left(coalesce(content,''), 16000))
  ) STORED;
CREATE INDEX IF NOT EXISTS ix_issue_comments_search_tsv
  ON issue_comments USING GIN (search_tsv);
```

**Migration SQLite:**
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS issue_comments_fts USING fts5(
  id UNINDEXED, issue_id UNINDEXED,
  content,
  tokenize='unicode61'
);
-- AFTER INSERT/UPDATE/DELETE triggers on issue_comments
-- backfill INSERT SELECT where not present
```

**ILike fallback:**
```python
select(IssueComment, Issue)
  .join(Issue, Issue.id == IssueComment.issue_id)
  .where(
    Issue.workspace_id == workspace_id,
    Issue.is_deleted == False,
    IssueComment.is_deleted == False,
    IssueComment.comment_type == CommentType.COMMENT,
    IssueComment.content.ilike(f"%{q}%"),
  )
  .order_by(IssueComment.created_at.desc())
  .limit(limit)
```

**PG query:**
```sql
SELECT c.id, c.issue_id, i.issue_code, c.content, c.user_id, c.created_at,
       ts_rank(c.search_tsv, plainto_tsquery('simple', :q)) AS rank
FROM issue_comments c
JOIN issues i ON i.id = c.issue_id
WHERE i.workspace_id = :ws
  AND i.is_deleted = false
  AND c.is_deleted = false
  AND c.comment_type = 'comment'
  AND c.search_tsv @@ plainto_tsquery('simple', :q)
ORDER BY rank DESC, c.created_at DESC
LIMIT :lim
```

**SQLite query:**
```sql
SELECT c.id, c.issue_id, i.issue_code, c.content, c.user_id, c.created_at,
       bm25(issue_comments_fts) AS rank
FROM issue_comments_fts
JOIN issue_comments c ON c.id = issue_comments_fts.id
JOIN issues i ON i.id = c.issue_id
WHERE issue_comments_fts MATCH :q
  AND i.workspace_id = :ws
  AND i.is_deleted = 0
  AND c.is_deleted = 0
  AND c.comment_type = 'comment'
ORDER BY rank ASC, c.created_at DESC
LIMIT :lim
```

- [ ] **Step 1: 红测** `test_e62_search_hits_comment_body` — comment needle 命中 `comments` 组；title-only 不误伤
- [ ] **Step 2:** Run → FAIL（无 comments 键 / 无命中）
- [ ] **Step 3:** migration + backend.search_comments + conftest PG bootstrap
- [ ] **Step 4:** Run → PASS（至少 ILike/PG 路径）
- [ ] **Step 5:** Commit `feat(E62): comment FTS backend + alembic`

---

### Task 3 — B+C：SearchService + API 契约 + 过滤边界（TDD）

**Files:**
- Modify: `backend/opentask/services/search/service.py` — 空 q 含 `comments: []`；装配 `backend.search_comments`
- Extend: `backend/tests/api/test_e62_comment_fts.py`
- Modify: `backend/tests/api/test_e60_search_fts.py` — empty q 断言加 `comments: []`（加法契约）

**Interfaces:**
```python
async def search(...) -> dict:
    if not query:
        return {
            "issues": [], "projects": [], "docs": [], "members": [],
            "comments": [],
        }
    return {
        "issues": await self._search_issues(...),
        "projects": await self.backend.search_projects(...),
        "docs": await self.backend.search_docs(...),
        "members": await self._search_members(...),
        "comments": await self.backend.search_comments(...),
    }
```

**Red tests:**
```python
async def test_e62_search_hits_comment_body(...): ...

async def test_e62_soft_deleted_issue_comments_hidden(...):
    # create issue+comment → DELETE issue → search needle → comments empty

async def test_e62_system_comment_type_excluded(...):
    # insert CommentType.SYSTEM via session OR service with comment_type
    # COMMENT hit; SYSTEM does not

async def test_e62_nested_reply_is_own_hit(...):
    # parent + reply both COMMENT with needle → two Hits

async def test_e62_empty_q_includes_comments_key(...):
    data == {..., "comments": []}

async def test_e62_cross_tenant_forbidden(...):  # 403 on foreign WS header

async def test_e62_e60_groups_still_present(...):
    # issues/projects/docs/members keys still returned

async def test_e62_no_emit_fire_webhooks(...):
    # spy fire_webhooks not called on search
```

- [ ] 红→绿→commit `feat(E62): search API comments group + filters`

---

### Task 4 — D：FE comments 组 + 深链 Issue（TDD）

**Files:**
- Modify: `frontend/src/service/api/search.ts` — `SearchCommentHit` + `comments?:`
- Modify: `frontend/src/utils/global-search.ts` — `SearchGroupId` 加 `'comments'`；flatten；缺键安全
- Modify: `frontend/src/utils/global-search.test.ts`
- Modify: `frontend/src/views/search/index.vue` — 分组顺序含 comments；默认空含 comments
- Modify: `frontend/src/locales/langs/en-us.ts` / `zh-cn.ts` — `groupComments`

**Interfaces:**
```typescript
export type SearchGroupId = 'issues' | 'projects' | 'docs' | 'members' | 'comments';

export interface SearchCommentHit {
  id: string;
  issueId: string;
  issueCode: string;
  snippet?: string;
  rank?: number;
  authorUserId?: string;
  createdAt?: string;
}

// flatten: missing data.comments → treat as []
// href: { path: '/issue/detail', query: { id: issueId } }  // Q5a — no comment anchor yet
// subtitle: `${issueCode} · ${snippet}`
```

- [ ] vitest 绿 → commit `feat(E62): FE search comments group`

---

### Task 5 — E：CLI 1.46.0

**Files:**
- Bump: `pyproject.toml` / `__init__.py` / `setup.py` / `VERSION` / `opentask_cli.VERSION`
- Sync: 全部历史 `1.45.0` 断言 → `1.46.0`（`rg -l '1\.45\.0'`）
- Modify: `opentask/core/search.py` — 人类输出增 `comments:` 行 `issueCode · snippet`
- Create/Extend: `tests/test_e62_comment_search.py`（version pin + search help 仍绿）

**Human output (Q6a):**
```
comments: N
  OT-12 · snippet text…
```

- [ ] CLI 绿 → commit `feat(E62): CLI 1.46.0 comments search output`

---

### Task 6 — F：门禁 + acceptance tip

- BE full + targeted E62+E60 search；CLI；FE vitest+build
- 填 tip SHA / 测数；`superpowers: design/plan/TDD/verify/acceptance = ok`
- Final tip commit 记录 HEAD
- **STOP**；不 push；不开 E63

---

## Spec coverage self-check
| Spec | Task |
|------|------|
| A SearchBackend + PG/SQLite/ILike + alembic + conftest | T2 |
| B API comments 组 + empty q + limit + code boost issues-only | T3 |
| C COMMENT only / soft-delete / nested / no MC/Req | T3 |
| D FE group + deep-link Issue + missing key + vitest/build | T4 |
| E CLI 1.46.0 | T5 |
| F tenant / no-emit / no Meili/Push / no E57–E58/E61 primary | T3+T6 |
