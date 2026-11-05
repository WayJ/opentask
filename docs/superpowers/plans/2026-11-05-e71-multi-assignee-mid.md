# E71 Plan：多指派人 mid — issue_assignees · CLI 1.55.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`f84a233`（全文 `f84a233a4a9a8dea4c63bd470fde1c737c1b796e`）· 分支 `sprint/E71-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e71-multi-assignee-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E72**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Issue 支持多名有序指派人（首=primary 镜像 `assignee_id`）；结表 `issue_assignees`；详情/列表嵌 `assignees[]`；Create/Update 接受 `assignee_ids`；过滤 `assignee_id`/`me`=primary、`assignee_any`=任一；通知 fanout 新加入；复用 `issue.assignee_changed`；FE 多选+叠头像；CLI **1.55.0**；无 Push / 无新 webhook 名 / formula no-emit；不改 E63–E70 邻面主表面。

**Architecture:** 结表 `issue_assignees(position)` + 服务 `replace_issue_assignees` 原子替换并镜像 primary。写 `assignee_ids` 全量替换；只写 `assignee_id`（无 `assignee_ids`）→ primary + **清协作者**（Q2a）。API 默认嵌 `assignees: UserInfo[]`。通知对集合差集新加入发 `assigned`；recipients 并入全部 assignees。Webhook 复用 `issue.assignee_changed`，payload 增 `assignee_ids`。FE 多选；CLI pins **1.55.0**（含 VERSION 文件）。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E72；中文 docs；CLI **1.55.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py` 全钉）
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；无 Activity Push；无门户/甘特/递归孙项/附件再开
- 不改 E63–E70 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- Q5a：不新增 webhook 事件名；集合变 → 既有 `issue.assignee_changed`
- Q4a：bulk 仍只 primary（设 `assignee_id` 时按 Q2a 同步结表）
- 非目标见 design §2；max **10**；跨租户 404；非 WS 成员 → 400

## File map
| Path | Role |
|------|------|
| `backend/opentask/models/issue_assignee/` | ORM `IssueAssignee` |
| `backend/alembic/versions/2026_11_05_5100-y2b3c4d5e6f7_issue_assignees.py` | 表 + 既有 `assignee_id` → position=0 回填 |
| `backend/opentask/services/issue_assignee/service.py` | normalize / validate / replace / list / user infos |
| `backend/opentask/models/issue/schema.py` | `assignee_ids` on Create/Update；`assignees` on Response；`assignee_any` on Query |
| `backend/opentask/services/issue_service.py` | create/update/list 接入；bulk Q2a 同步 |
| `backend/opentask/api/issue/router.py` | embed assignees；`assignee_any` query |
| `backend/opentask/services/notification/service.py` | fanout assigned；recipients 全员 |
| `backend/tests/api/test_e71_multi_assignee.py` | API TDD |
| `backend/tests/unit/test_e71_assignee_normalize.py` | normalize/cap 纯函数 |
| `frontend/src/utils/assignees.ts` (+test) | formatAssigneesStack / primary |
| `frontend/src/components/UserSelect.vue` | multiple 模式 |
| `frontend/src/views/issue/detail/index.vue` | 多选 + 叠头像 |
| `frontend/src/views/issue/list/**` | 有 payload 时叠头像 |
| `frontend/src/typings/api/issue.d.ts` | assignees? / assignee_ids? |
| `frontend/src/store/modules/issue.ts` + api | updateAssignees |
| `agent-harness/opentask-cli/**` | 1.55.0 + `--assignees` + show |
| `docs/superpowers/acceptances/2026-11-05-E71-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E71-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e71-multi-assignee-mid.md \
  docs/superpowers/acceptances/2026-11-05-E71-acceptance.md
git commit -m "docs(E71): plan + acceptance skeleton"
```

---

### Task 2 — A：normalize helper（TDD）

**Files:**
- Create: `backend/opentask/services/issue_assignee/__init__.py`
- Create: `backend/opentask/services/issue_assignee/service.py`（先纯函数）
- Create: `backend/tests/unit/test_e71_assignee_normalize.py`

**Interfaces:**
- `MAX_ISSUE_ASSIGNEES = 10`
- `normalize_assignee_ids(ids: Iterable[str | None]) -> list[str]`
  - strip；去空；**保序去重**；若 `len > 10` → raise `ValueError("max 10 assignees")`

- [ ] **Step 1: 红测**

```python
"""E71: assignee_ids normalize — order-preserving dedupe; max 10."""
from __future__ import annotations

import pytest

from opentask.services.issue_assignee.service import (
    MAX_ISSUE_ASSIGNEES,
    normalize_assignee_ids,
)


def test_max_constant():
    assert MAX_ISSUE_ASSIGNEES == 10


def test_dedupe_preserves_order():
    assert normalize_assignee_ids(["a", "b", "a", "c"]) == ["a", "b", "c"]


def test_strips_empty():
    assert normalize_assignee_ids(["a", "", None, "  ", "b"]) == ["a", "b"]


def test_max_11_raises():
    ids = [f"u{i}" for i in range(11)]
    with pytest.raises(ValueError, match="max 10"):
        normalize_assignee_ids(ids)


def test_empty():
    assert normalize_assignee_ids([]) == []
    assert normalize_assignee_ids(None) == []
```

- [ ] **Step 2: Run → FAIL**（module missing）

```bash
cd backend && python -m pytest tests/unit/test_e71_assignee_normalize.py -v
```

- [ ] **Step 3: 最小实现**

```python
# backend/opentask/services/issue_assignee/service.py
from __future__ import annotations
from typing import Iterable, Optional

MAX_ISSUE_ASSIGNEES = 10


def normalize_assignee_ids(ids: Optional[Iterable[str | None]]) -> list[str]:
    if not ids:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in ids:
        if raw is None:
            continue
        uid = str(raw).strip()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        out.append(uid)
    if len(out) > MAX_ISSUE_ASSIGNEES:
        raise ValueError(f"max {MAX_ISSUE_ASSIGNEES} assignees")
    return out
```

- [ ] **Step 4: PASS + commit**

```bash
git add backend/opentask/services/issue_assignee backend/tests/unit/test_e71_assignee_normalize.py
git commit -m "feat(E71): normalize_assignee_ids helper (max 10)"
```

---

### Task 3 — A：Model + alembic + backfill（TDD via API later；migration self-check）

**Files:**
- Create: `backend/opentask/models/issue_assignee/model.py`
- Create: `backend/opentask/models/issue_assignee/__init__.py`
- Modify: `backend/opentask/models/__init__.py` — import `IssueAssignee`
- Create: `backend/alembic/versions/2026_11_05_5100-y2b3c4d5e6f7_issue_assignees.py`
  - `down_revision = "x1a2b3c4d5e6"`
  - create table `issue_assignees`：`id`, `workspace_id` FK, `issue_id` FK, `user_id`, `position` Int, `created_at`
  - UNIQUE(`issue_id`,`user_id`)；index (`workspace_id`,`user_id`)；index `issue_id`
  - data migration：`INSERT … SELECT` 从 `issues` where `assignee_id IS NOT NULL` → `position=0`

**Model sketch:**

```python
class IssueAssignee(DBModel):
    __tablename__ = "issue_assignees"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("issue_id", "user_id", name="uq_issue_assignees_issue_user"),
        Index("ix_issue_assignees_ws_user", "workspace_id", "user_id"),
    )
```

- [ ] **Step 1: 写 model + migration + register**
- [ ] **Step 2: commit**

```bash
git add backend/opentask/models/issue_assignee backend/opentask/models/__init__.py \
  backend/alembic/versions/2026_11_05_5100-y2b3c4d5e6f7_issue_assignees.py
git commit -m "feat(E71): issue_assignees table + backfill migration"
```

---

### Task 4 — A：replace_issue_assignees service（TDD）

**Files:**
- Modify: `backend/opentask/services/issue_assignee/service.py`
- Create: `backend/tests/api/test_e71_multi_assignee.py`（先写红测，本 task 跑 service 相关部分；完整 API 在 Task 5）

**Interfaces:**
- `async def list_assignee_ids(db, issue_id) -> list[str]` 按 position ASC
- `async def list_assignee_user_infos(db, issue_id) -> list[dict]`（UserInfo 形）
- `async def list_assignee_user_infos_for_issues(db, issue_ids) -> dict[str, list[dict]]`
- `async def validate_assignee_members(db, workspace_id, user_ids) -> None`  
  - 任一非本 WS 成员 → `HTTPException(400, "assignee must be workspace member")`
- `async def replace_issue_assignees(db, *, issue: Issue, user_ids: list[str], actor_user_id: str | None = None) -> list[str]`
  - normalize；validate members；delete existing rows for issue；insert new with position；`issue.assignee_id = ids[0] if ids else None`；flush（caller commits）
  - returns normalized ids

- [ ] **Step 1–4:** 在 API 测试里覆盖（Task 5 红→绿一并）；本 task 先落地 service 实现并 commit

```bash
git commit -m "feat(E71): replace_issue_assignees + member validation"
```

---

### Task 5 — A/B：API create/update/list + filters + notify + webhook（TDD）

**Files:**
- Modify: `backend/opentask/models/issue/schema.py`
  - `IssueCreate.assignee_ids: Optional[List[str]] = None`
  - `IssueUpdate.assignee_ids: Optional[List[str]] = None`
  - `IssueResponse.assignees: Optional[List[UserInfo]] = None`
  - `IssueQueryParams.assignee_any: Optional[str] = None`
- Modify: `backend/opentask/services/issue_service.py`
  - `create_issue`: pop `assignee_ids`；创建后 `replace_issue_assignees`；若有 ids → fanout `notify_assigned` 每位；若集合变 fire webhook（create 路径已有 created；指派集合非空时额外 `issue.assignee_changed` 可选——**仅当 update 集合变必 fire**；create 有 assignee 时也 fire `assignee_changed` 以利订阅）
  - `update_issue`:
    - 若 `"assignee_ids" in update_data`：pop；`new_ids = normalize(...)`；old=list；replace；mirror 已在 replace；`assignee_did_change = set(old)!=set(new) or order changed`；notify **差集新加入** 每位；webhook payload 带 `assignee_ids`/`from`/`to`（to=primary）
    - elif `"assignee_id" in update_data`（无 assignee_ids）：`new_ids = [assignee_id] if assignee_id else []`；同上（Q2a 清协作者）
  - `get_issues`: if `params.assignee_any`: join/exists `issue_assignees` OR primary（`me` 已在 router resolve）
  - `bulk_update_issues`: if sets `assignee_id` → per-issue `replace_issue_assignees` to `[id]` or `[]`（Q4a+镜像）
- Modify: `backend/opentask/api/issue/router.py`
  - list/detail/create/update responses：embed `assignees` via batch helper
  - list query：`assignee_any: Optional[str] = Query(None)`；resolve `me`
- Modify: `backend/opentask/services/notification/service.py`
  - `notify_assigned(..., new_assignee_ids: list[str] | None = None)`：兼容旧 `new_assignee_id`；对列表每位发 assigned；watchers exclude 全集
  - `notify_comment` / `notify_status_changed` / `_recipients_for_issue`：并入 `list_assignee_ids`

**红测要点（`backend/tests/api/test_e71_multi_assignee.py`）：**

```python
async def test_create_with_assignee_ids_mirrors_primary(...):
    # POST assignee_ids=[a,b] → assignee_id==a；assignees 有序 2

async def test_patch_assignee_ids_replaces(...):
    # [a,b] → [b] ；assignee_id==b

async def test_patch_assignee_id_only_clears_collaborators(...):
    # Q2a

async def test_max_11_returns_400(...): ...

async def test_assignee_id_filter_primary_only(...):
    # 协作者 a 的 issue 不被 assignee_id=a 命中

async def test_assignee_any_includes_collaborator(...): ...

async def test_non_member_assignee_400(...): ...

async def test_notify_fanout_new_assignees(monkeypatch): ...

async def test_webhook_reuses_assignee_changed_no_new_event(monkeypatch):
    # spy fire_webhooks；事件名仅 issue.assignee_changed；payload 含 assignee_ids
```

- [ ] **Step 1: 红测文件入库并跑 → FAIL**
- [ ] **Step 2: 实现至绿**
- [ ] **Step 3: commit**

```bash
git commit -m "feat(E71): multi-assignee API + filters + notify + webhook payload"
```

---

### Task 6 — C：FE 多选 + 叠头像 + vitest

**Files:**
- Create: `frontend/src/utils/assignees.ts`
  - `formatAssigneesStack(assignees, maxVisible=3) -> { visible, overflow, primaryId }`
- Create: `frontend/src/utils/assignees.test.ts`
- Modify: `frontend/src/components/UserSelect.vue` — `multiple?: boolean`；modelValue `string | string[] | null`
- Modify: `frontend/src/typings/api/issue.d.ts` — `assignees?: UserInfo[]`；Create/Update `assignee_ids?`
- Modify: `frontend/src/service/api/issue.ts` + store — update 可传 `assignee_ids`
- Modify: `frontend/src/views/issue/detail/index.vue` — 多选；展示叠头像；save → `assignee_ids`
- Modify: list/board — 有 `assignees?.length` 时叠头像，否则退化为单 assignee

- [ ] **Step 1: vitest 红→绿**
- [ ] **Step 2: UI 接线**
- [ ] **Step 3: `pnpm run build`；若 elegant-router 丢 `f`/`r` → 还原**
- [ ] **Step 4: commit**

```bash
git commit -m "feat(E71): FE multi-assignee select + avatar stack"
```

---

### Task 7 — D：CLI 1.55.0

**Files:**
- `agent-harness/opentask-cli/VERSION` → `1.55.0`
- `pyproject.toml` / `setup.py` / `opentask/__init__.py` → `1.55.0`
- `opentask/core/issue.py`：create/update `--assignees`（逗号分隔；首=primary）；show 打印 `Assignees:`（primary 标注）
- `opentask/utils/api_client.py`：create/update 传 `assignee_ids`
- tests：version pin + create/update/show 行为

- [ ] **Step 1: pins + flags + show**
- [ ] **Step 2: CLI 全量 pytest**
- [ ] **Step 3: commit**

```bash
git commit -m "feat(E71): CLI 1.55.0 --assignees + show Assignees"
```

---

### Task 8 — E：邻面不动 / verify / acceptance

- [ ] BE full suite；定向 E71
- [ ] CLI full；确认 VERSION=1.55.0
- [ ] FE vitest + build；`f`+`r` 仍在
- [ ] 写满 acceptance（tip SHA + 门禁数）
- [ ] tip commit；**STOP** — 不 push / 不开 PR / 不自开 E72

```bash
git commit -m "docs(E71): acceptance — multi-assignee mid local-complete"
```

---

## Self-review
1. Spec A–E → Tasks 3–7；Q1a–Q6a 全覆盖  
2. 无 TBD；VERSION 四钉明示  
3. webhook 无新事件名；bulk 仍 primary；formula no-emit  
