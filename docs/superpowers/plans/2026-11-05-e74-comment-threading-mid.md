# E74 Plan：评论线程 mid — nested replies · CLI 1.58.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`52e0b1d`（全文 `52e0b1dc22e3ad671604d1e6add13520b7305502`）· 分支 `sprint/E74-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e74-comment-threading-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E75**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** 对顶层评论发回复（`parent_id`）；BE 拒绝跨 Issue parent、软删父、对回复再回（深度>1）、缺失父；GET 仍扁平含 `parent_id`；软删父后用户侧不见子；通知 recipients ∪ 父评作者；FE 组树+回复 UX；CLI **1.58.0** `--parent-id`；无 alembic；无新 webhook 名；formula no-emit；不重开 E63–E73 / E69 附件主表面。

**Architecture:** 复用既有 `issue_comments.parent_id`；在 `IssueService.add_comment` 增加 `validate_comment_parent`（同 issue / 未软删 / 父为根）；`delete_comment` 级联软删直接子；`get_comments` 防御过滤孤儿子；`notify_comment` 增 `parent_author_user_id`；FE `buildCommentTree` 纯函数 + 详情回复入口；CLI pins 全钉 1.58.0 + `--parent-id`。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E75；中文 docs；CLI **1.58.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- **无 alembic**（`parent_id` 已在）
- formula 永不 emit；无 Activity Push；无门户/甘特；不重开 E69 附件 ACL/上传主表面
- 不改 E63–E73 邻面主表面（仅 CLI version pins）
- Q5a：不新增 webhook 事件名（沿用 `comment.created`）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/comment_threading.py` | `validate_comment_parent` 纯校验（可单测） |
| `backend/opentask/services/issue_service.py` | add_comment 校验；delete 级联软删子；get_comments 过滤；notify 传父作者 |
| `backend/opentask/services/notification/service.py` | `notify_comment(..., parent_author_user_id=)` |
| `backend/opentask/api/issue/router.py` | 透传 HTTPException 400（勿吞成 500） |
| `backend/tests/unit/test_e74_comment_parent_validate.py` | unit TDD |
| `backend/tests/api/test_e74_comment_threading.py` | API TDD |
| `frontend/src/utils/buildCommentTree.ts` (+test) | 扁平→树 |
| `frontend/src/views/issue/detail/index.vue` | 树渲染 + Reply + parentId 提交 |
| `frontend/src/views/issue/detail/components/CommentsCard.vue` | 同款树/回复（demo 卡） |
| `agent-harness/opentask-cli/**` | 1.58.0 + `--parent-id` + list Parent |
| `docs/superpowers/acceptances/2026-11-05-E74-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E74-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e74-comment-threading-mid.md \
  docs/superpowers/acceptances/2026-11-05-E74-acceptance.md
git commit -m "docs(E74): plan + acceptance skeleton"
```

---

### Task 2 — A：validate_comment_parent 纯函数（TDD）

**Files:**
- Create: `backend/opentask/services/comment_threading.py`
- Create: `backend/tests/unit/test_e74_comment_parent_validate.py`

**Interfaces:**
```python
@dataclass(frozen=True)
class ParentCommentView:
    id: str
    issue_id: str
    parent_id: str | None
    is_deleted: bool
    user_id: str | None = None

def validate_comment_parent(
    *,
    issue_id: str,
    parent: ParentCommentView | None,
    parent_id: str | None,
) -> None:
    """Raise HTTPException(400) if parent_id set but invalid for depth=1 threading.
    - parent_id is None → OK (root)
    - parent is None → 400 code=parent_not_found
    - parent.issue_id != issue_id → 400 code=parent_cross_issue
    - parent.is_deleted → 400 code=parent_deleted
    - parent.parent_id is not None → 400 code=parent_not_root (Q1a depth=1)
    """
```

- [ ] **Step 1: 红测**

```python
"""E74: comment parent validation (depth=1)."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from opentask.services.comment_threading import ParentCommentView, validate_comment_parent


def test_no_parent_ok():
    validate_comment_parent(issue_id="i1", parent=None, parent_id=None)


def test_root_parent_ok():
    p = ParentCommentView(id="c1", issue_id="i1", parent_id=None, is_deleted=False)
    validate_comment_parent(issue_id="i1", parent=p, parent_id="c1")


def test_parent_not_found_400():
    with pytest.raises(HTTPException) as ei:
        validate_comment_parent(issue_id="i1", parent=None, parent_id="missing")
    assert ei.value.status_code == 400
    assert ei.value.detail["code"] == "parent_not_found"


def test_cross_issue_400():
    p = ParentCommentView(id="c1", issue_id="other", parent_id=None, is_deleted=False)
    with pytest.raises(HTTPException) as ei:
        validate_comment_parent(issue_id="i1", parent=p, parent_id="c1")
    assert ei.value.detail["code"] == "parent_cross_issue"


def test_deleted_parent_400():
    p = ParentCommentView(id="c1", issue_id="i1", parent_id=None, is_deleted=True)
    with pytest.raises(HTTPException) as ei:
        validate_comment_parent(issue_id="i1", parent=p, parent_id="c1")
    assert ei.value.detail["code"] == "parent_deleted"


def test_reply_to_reply_400():
    p = ParentCommentView(id="c2", issue_id="i1", parent_id="c1", is_deleted=False)
    with pytest.raises(HTTPException) as ei:
        validate_comment_parent(issue_id="i1", parent=p, parent_id="c2")
    assert ei.value.detail["code"] == "parent_not_root"
```

- [ ] **Step 2: Run → FAIL (import)**
- [ ] **Step 3: Minimal impl → PASS**
- [ ] **Step 4: Commit** `feat(E74): validate_comment_parent depth=1`

---

### Task 3 — A：Service + API threading（TDD）

**Files:**
- Modify: `backend/opentask/services/issue_service.py`
- Modify: `backend/opentask/services/notification/service.py`
- Modify: `backend/opentask/api/issue/router.py`
- Create: `backend/tests/api/test_e74_comment_threading.py`

**Behavior:**
1. `add_comment`: if `parent_id`，load parent by id；`validate_comment_parent`；再 insert
2. `delete_comment`: soft-delete target **and** children where `parent_id == comment_id`（Q3a）
3. `get_comments`: when not include_deleted，额外排除「父评已软删」的子（防御脏数据）
4. `notify_comment(..., parent_author_user_id: str | None = None)`：若设且 ≠ actor → recipients.setdefault
5. router `add_comment`：`except HTTPException: raise` 再 `except Exception`→500

**API 红测要点：**
1. 根→回复 200，`parent_id` 正确；list 扁平两行均含 `parent_id`
2. parent 他 Issue / 软删父 / 对回复再回 → 400（对应 code）
3. 软删父 → list 不见子
4. spy notify：父作者在 recipients；webhook 仍 `comment.created`（无新事件名）
5. 无 parent → 行为不变

- [ ] **Step 1: 红测文件** → FAIL
- [ ] **Step 2: 实现** → PASS
- [ ] **Step 3: commit** `feat(E74): BE comment threading validate + soft-delete hide + notify parent author`

---

### Task 4 — B：FE buildCommentTree + 回复 UX（TDD）

**Files:**
- Create: `frontend/src/utils/buildCommentTree.ts`
- Create: `frontend/src/utils/buildCommentTree.test.ts`
- Modify: `frontend/src/views/issue/detail/index.vue`
- Modify: `frontend/src/views/issue/detail/components/CommentsCard.vue`（树+回复，不改附件契约）

**Interfaces:**
```ts
export interface CommentLike {
  id: string;
  parent_id?: string | null;
  [key: string]: unknown;
}

export interface CommentTreeNode<T extends CommentLike = CommentLike> {
  comment: T;
  depth: 0 | 1;
  replies: T[];
}

/** Flat → roots with depth-1 replies. Orphan/depth>1 → append as root (defensive). */
export function buildCommentTree<T extends CommentLike>(comments: T[]): CommentTreeNode<T>[];
```

**UI:**
- `replyToId` ref；根评「回复」设 replyTo + 聚焦编辑器
- `handleAddComment` 传 `parentId: replyToId ?? undefined`；成功后清 replyTo
- 渲染：根 + 缩进 replies；复用 AttachmentList / IssueReactions（不改 E69/E27 契约）

- [ ] **Step 1: vitest 红** → implement → 绿
- [ ] **Step 2: detail + CommentsCard UI**
- [ ] **Step 3: commit** `feat(E74): FE comment tree + reply UX`

---

### Task 5 — C：CLI 1.58.0

**Files:**
- `agent-harness/opentask-cli/VERSION` → `1.58.0`
- `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask/opentask_cli.py` VERSION
- Cascade historical epic test asserts `1.57.0` → `1.58.0`
- `opentask/utils/api_client.py`：`add_comment(..., parent_id: str | None = None)`
- `opentask/core/issue.py`：`comment add --parent-id`；`comment list` 显示 `Parent:`；json 已含字段
- Create: `agent-harness/opentask-cli/tests/test_e74_comment_threading.py`

```python
def test_version_pins_1_58_0():
    assert __version__ == "1.58.0"
    assert VERSION == "1.58.0"
    assert (ROOT / "VERSION").read_text().strip() == "1.58.0"
    assert 'version = "1.58.0"' in (ROOT / "pyproject.toml").read_text()
    assert "1.58.0" in (ROOT / "setup.py").read_text()

def test_comment_add_help_has_parent_id():
    result = CliRunner().invoke(cli, ["issue", "comment", "add", "--help"])
    assert result.exit_code == 0
    assert "--parent-id" in result.output
```

- [ ] **Step 1: 测红** → pins + flags → 绿
- [ ] **Step 2: commit** `feat(E74): CLI 1.58.0 comment --parent-id`

---

### Task 6 — D/E verify + acceptance

**Verify:**
```bash
cd backend && python -m pytest tests/unit/test_e74_comment_parent_validate.py tests/api/test_e74_comment_threading.py -v
cd backend && python -m pytest -q
cd ../agent-harness/opentask-cli && python -m pytest -q
cd ../../frontend && pnpm exec vitest run && pnpm run build
# restore f+r if elegant-router dropped them
```

- [ ] **Step 1:** 全门禁记录；formula no-emit / 无新 webhook 名 在 API 测中钉
- [ ] **Step 2:** acceptance 填 tip + gates
- [ ] **Step 3:** tip commit；**STOP**（不 push / 不开 E75）

---

## Self-review
- Spec A–E / Q1a–Q6a / ADR D1–D7 均有对应 Task
- 无 TBD；无 alembic；无新 webhook 名；不重开 E69 附件主表面
- CLI 五处 pins 全列；f+r 守门在 Task 6
- router 必须透传 HTTPException，否则 400 变 500
