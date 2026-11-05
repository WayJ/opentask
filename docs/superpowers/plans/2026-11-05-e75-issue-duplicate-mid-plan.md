# E75 Plan：Issue 复制 mid — duplicate · CLI 1.59.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`78e12bb`（全文 `78e12bb29300a6e0cd9a84db3e2befd69beb9702`；含 E75 design；E74 tip `98d5bf4` ⊂ HEAD）· 分支 `sprint/E75-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e75-issue-duplicate-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E76**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 对可见 Issue 调用 `POST /api/issues/{id}/duplicate` → 新 `issue_code` 的同 WS Issue；白名单字段复制；`status=open`；不复制评论/附件/时间线/子项/关系（除 Q4a `relates_to`→源）/watchers/SLA/VCS；FE 详情「复制 Issue」+ 跳转；CLI **1.59.0** `issue duplicate`；无 alembic；无新 webhook 名；formula no-emit；不重开 E63–E74。

**Architecture:** 纯函数 `build_duplicate_title`（` (copy)`）；`IssueService.duplicate_issue` 组 `IssueCreate` 后复用 `create_issue`（含 `created_action_extra.duplicated_from`）→ 复制 tags / 非 formula CF / `assignee_ids` → `add_relation(relates_to→源)`；路由与 triage `/triage/{id}/duplicate` 分路径；FE helper + 详情按钮；CLI pins 全钉 1.59.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E76；中文 docs；CLI **1.59.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D7；Q1a–Q6a 全关（不得改）：无 `duplicated_from_id` 列 · 保留 parent · 后缀 ` (copy)` · `relates_to`→源 · 无新 webhook · CLI 1.59.0
- **无 alembic**（Q1a）
- formula 永不 emit；跳过 formula CF 值；无 Activity Push；无门户/甘特
- 不改 E63–E74 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/issue_duplicate.py` | `COPY_TITLE_SUFFIX` / `build_duplicate_title` 纯函数 |
| `backend/opentask/services/issue_service.py` | `duplicate_issue`；`create_issue(..., created_action_extra=)` |
| `backend/opentask/models/issue/schema.py` | `IssueDuplicateRequest` |
| `backend/opentask/api/issue/router.py` | `POST /{issue_id}/duplicate`（member+；跨 WS 404） |
| `backend/tests/unit/test_e75_duplicate_title.py` | unit TDD |
| `backend/tests/api/test_e75_issue_duplicate.py` | API TDD |
| `frontend/src/utils/buildDuplicateTitle.ts` (+test) | 标题后缀 |
| `frontend/src/service/api/issue.ts` | `duplicateIssue` |
| `frontend/src/store/modules/issue.ts` | store wrap（可选薄） |
| `frontend/src/views/issue/detail/index.vue` | 「复制 Issue」按钮 + 跳转 |
| `agent-harness/opentask-cli/**` | 1.59.0 + `issue duplicate` |
| `docs/superpowers/acceptances/2026-11-05-e75-issue-duplicate-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e75-issue-duplicate-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e75-issue-duplicate-mid-acceptance.md
git commit -m "docs(E75): plan + acceptance skeleton"
```

---

### Task 2 — A：build_duplicate_title 纯函数（TDD）

**Files:**
- Create: `backend/opentask/services/issue_duplicate.py`
- Create: `backend/tests/unit/test_e75_duplicate_title.py`

**Interfaces:**
```python
COPY_TITLE_SUFFIX = " (copy)"

def build_duplicate_title(title: str, override: str | None = None) -> str:
    """Q3a: ASCII suffix ' (copy)' unless override provided (non-empty trimmed)."""
```

- [ ] **Step 1: 红测**

```python
"""E75: duplicate title suffix (Q3a)."""
from opentask.services.issue_duplicate import COPY_TITLE_SUFFIX, build_duplicate_title

def test_suffix_appended():
    assert build_duplicate_title("Login bug") == "Login bug (copy)"
    assert COPY_TITLE_SUFFIX == " (copy)"

def test_override_wins():
    assert build_duplicate_title("Login bug", override="Custom title") == "Custom title"

def test_empty_override_falls_back():
    assert build_duplicate_title("X", override="") == "X (copy)"
    assert build_duplicate_title("X", override="   ") == "X (copy)"
```

- [ ] **Step 2:** `pytest backend/tests/unit/test_e75_duplicate_title.py -v` → FAIL (import)

- [ ] **Step 3: 实现**

```python
"""E75: Issue duplicate helpers (title suffix; no DB)."""
from __future__ import annotations

COPY_TITLE_SUFFIX = " (copy)"

def build_duplicate_title(title: str, override: str | None = None) -> str:
    if override is not None and override.strip():
        return override.strip()
    return f"{title}{COPY_TITLE_SUFFIX}"
```

- [ ] **Step 4:** 绿 → commit `feat(E75): duplicate title suffix helper`

---

### Task 3 — A：duplicate_issue service + API（TDD）

**Files:**
- Modify: `backend/opentask/services/issue_service.py`（`create_issue` 增 `created_action_extra`；新 `duplicate_issue`）
- Modify: `backend/opentask/models/issue/schema.py`（`IssueDuplicateRequest`）
- Modify: `backend/opentask/api/issue/router.py`（route）
- Create: `backend/tests/api/test_e75_issue_duplicate.py`

**Interfaces:**
```python
class IssueDuplicateRequest(BaseModel):
    title: Optional[str] = None
    project_id: Optional[str] = None
    cycle_id: Optional[str] = None
    parent_issue_id: Optional[str] = None  # explicit null clears; omit=copy source
    assignee_ids: Optional[List[str]] = None

async def duplicate_issue(
    self,
    source_issue_id: str,
    *,
    user_id: str,
    workspace_id: str,
    dept_id: str | None = None,
    overrides: IssueDuplicateRequest | None = None,
) -> Issue:
    """Copy whitelist → create_issue(status=open, reporter=actor, action_data.duplicated_from)
    → tags / non-formula CF / relates_to(source). Raises LookupError if source missing in WS.
    """
```

**Copy whitelist:** title(+suffix), description, type, priority, project_id, cycle_id, milestone_id, estimate_points, estimated_hours, start_date, due_date, parent_issue_id (Q2a), assignee_ids, tag_ids, CF values (skip formula).

**Do NOT copy:** status→open, reporter→actor, comments/attachments/docs/timeline/children/relations(except Q4a)/watchers/SLA/VCS/triage_status/started_at/resolved_at/closed_at; counts=0 via fresh create.

- [ ] **Step 1: 红测**（`backend/tests/api/test_e75_issue_duplicate.py`）覆盖：
  - happy：白名单字段对齐；新 code；status=open；comment_count=0；timeline created 含 `duplicated_from`
  - 不复制评论/附件/子项；无 triage `duplicates`；有 `relates_to`→源
  - formula CF 值不落库
  - overrides title/project/parent/assignees
  - 跨 WS 404；viewer 403
  - spy：webhook 事件名仍 `issue.created`（无 `issue.duplicated`）

- [ ] **Step 2:** 红跑定向 FAIL

- [ ] **Step 3: 实现**
  - `create_issue(..., created_action_extra: dict | None = None)` 合并进 CREATED action_data
  - `duplicate_issue`：load source（workspace_id 过滤）→ build IssueCreate → create → list tags → replace → CF values_for_issues 过滤 type!="formula" → upsert → add_relation(new, source, RELATES_TO)
  - route：`require_workspace_context` + `require_writer`（复用 tag/issue_template 的 writer 检查，或本地同等）+ `_require_issue_access`/`get_issue` 跨 WS 404

- [ ] **Step 4:** 绿 → commit `feat(E75): POST /api/issues/{id}/duplicate`

---

### Task 4 — B：FE 入口 + vitest

**Files:**
- Create: `frontend/src/utils/buildDuplicateTitle.ts` + `.test.ts`
- Modify: `frontend/src/service/api/issue.ts`（`duplicateIssue`）
- Modify: `frontend/src/store/modules/issue.ts`（可选）
- Modify: `frontend/src/views/issue/detail/index.vue`（按钮「复制 Issue」→ POST → toast → `router.push` 新 id）

- [ ] **Step 1: 红测** vitest `buildDuplicateTitle`

```ts
import { describe, expect, it } from 'vitest';
import { buildDuplicateTitle, COPY_TITLE_SUFFIX } from './buildDuplicateTitle';

describe('buildDuplicateTitle', () => {
  it('appends ASCII copy suffix', () => {
    expect(COPY_TITLE_SUFFIX).toBe(' (copy)');
    expect(buildDuplicateTitle('Login')).toBe('Login (copy)');
  });
  it('override wins when non-empty', () => {
    expect(buildDuplicateTitle('Login', 'Custom')).toBe('Custom');
  });
});
```

- [ ] **Step 2:** 实现 helper + API + 详情按钮（失败 toast；成功轻 toast 带新 code）

- [ ] **Step 3:** vitest 绿；若 build 误删 elegant-router `f`+`r` 则按 E31/E63 还原

- [ ] **Step 4:** commit `feat(E75): FE duplicate Issue + title helper`

---

### Task 5 — C：CLI 1.59.0

**Files:**
- Pin: `VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION` → **1.59.0**
- Cascade：所有历史 epic 版本断言 `1.58.0` → `1.59.0`
- Add: `opentask issue duplicate <id> [--title …] [--json]`
- Add: `api_client.duplicate_issue`
- Create: `tests/test_e75_issue_duplicate.py`

- [ ] **Step 1: 红测** version pins + help 含 duplicate

- [ ] **Step 2:** 实现命令（打印新 issue_code / id）+ pins

- [ ] **Step 3:** CLI suite 绿 → commit `feat(E75): CLI 1.59.0 issue duplicate`

---

### Task 6 — Verify + Acceptance

- [ ] Directed E75 BE unit+API
- [ ] Full BE suite（记 flake `test_user_search`）
- [ ] CLI suite
- [ ] FE vitest + `pnpm run build`（确认 `f`+`r`）
- [ ] 写满 acceptance（tip SHA、门禁数、`superpowers: design/plan/TDD/verify/acceptance = ok`）
- [ ] commit `docs(E75): acceptance`
- [ ] **STOP** — 不 push / 不开 PR / 不自开 E76

## Self-review
- Spec A–F / Q1a–Q6a 均有任务覆盖
- 无 placeholder；无 alembic；≠ triage mark-duplicate
- VERSION 文件必须钉 1.59.0（E70 教训）
