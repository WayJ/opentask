# E70 Plan：子问题进度汇总 mid — childProgress · CLI 1.54.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`076f0f6`（全文 `076f0f6a5fb01c888b9297fa71377a7fec6818af`）· 分支 `sprint/E70-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e70-subissue-progress-rollup-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E71**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** 有子项的 Issue 在详情默认返回 `childProgress`；列表可 `?include=childProgress` opt-in；语义 total/done/open/percent（+byStatus）；FE 父详情进度条+分数、列表/看板有 payload 时徽章；CLI **1.54.0** `issue show` 展示；无 alembic / Push / 新 webhook / formula children rollup；不改 E57–E69 邻面主表面。

**Architecture:** 纯函数 `compute_child_progress(statuses)` + 服务层 `child_progress_for_parent` / `child_progress_for_parents`（直接子、软删除外、done=resolved|closed|rejected）。详情 GET 在已有 `list_child_issues` 上附 `childProgress`；列表在 `include` 含 `childProgress` 时一次 `parent_issue_id IN (…) GROUP BY` 批量聚合。FE 纯函数 format + 详情子问题区进度条；列表/看板仅当 payload 有字段时徽章。CLI pins 1.54.0 + show 打印。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E71；中文 docs；CLI **1.54.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；不做 formula children rollup；无 alembic
- 不改 E57–E69 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- Q5a：不新增 webhook 事件名；读路径不 fire
- 非目标见 design §2；无递归孙项；不自动改父 status

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/child_progress.py` | `CHILD_PROGRESS_DONE_STATUSES` + `compute_child_progress` |
| `backend/tests/unit/test_e70_child_progress.py` | 纯函数单测 |
| `backend/opentask/services/issue_service.py` | `child_progress_for_parent` / `child_progress_for_parents` |
| `backend/opentask/models/issue/schema.py` | `ChildProgress` schema + IssueResponse 可选字段 |
| `backend/opentask/api/issue/router.py` | 详情默认嵌入；列表 include；children 根可选同构 |
| `backend/tests/api/test_e70_child_progress.py` | API TDD |
| `frontend/src/utils/childProgress.ts` (+test) | formatChildProgress |
| `frontend/src/typings/api/issue.d.ts` | `ChildProgress` + Issue.childProgress? |
| `frontend/src/views/issue/detail/index.vue` | 子问题区 + 进度条 |
| `frontend/src/views/issue/list/index.vue` | 标题列徽章（有 payload 时） |
| `frontend/src/views/issue/list/modules/IssueBoard.vue` | 卡片徽章（有 payload 时） |
| `agent-harness/opentask-cli/**` | 1.54.0 + show ChildProgress + list --include |
| `docs/superpowers/acceptances/2026-11-05-E70-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E70-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e70-subissue-progress-rollup-mid.md \
  docs/superpowers/acceptances/2026-11-05-E70-acceptance.md
git commit -m "docs(E70): plan + acceptance skeleton"
```

---

### Task 2 — A：compute_child_progress helper（TDD）

**Files:**
- Create: `backend/opentask/services/child_progress.py`
- Create: `backend/tests/unit/test_e70_child_progress.py`

**Interfaces:**
- `CHILD_PROGRESS_DONE_STATUSES = frozenset({"resolved", "closed", "rejected"})`
- `compute_child_progress(statuses: Iterable[str | Any]) -> dict`
  - 归一化：`getattr(s, "value", s)` → `str`
  - 返回 `{total, done, open, percent, byStatus}`
  - `done` = 状态 ∈ DONE 集的计数；`open` = total − done
  - `percent` = `round(done/total*100)` if total>0 else **None**（Q3a）
  - `byStatus`: status → count（含 0 计数的不强制；只出实际出现的）

- [ ] **Step 1: 红测**

```python
"""E70: childProgress pure helper — done=resolved|closed|rejected; 0 kids percent=null."""
from __future__ import annotations

from opentask.services.child_progress import (
    CHILD_PROGRESS_DONE_STATUSES,
    compute_child_progress,
)


def test_done_set_matches_e39():
    assert CHILD_PROGRESS_DONE_STATUSES == frozenset({"resolved", "closed", "rejected"})


def test_empty_percent_null():
    out = compute_child_progress([])
    assert out == {
        "total": 0,
        "done": 0,
        "open": 0,
        "percent": None,
        "byStatus": {},
    }


def test_mixed_five_children_percent_60():
    # 2 resolved + 1 closed + 2 open → done=3, total=5, percent=60
    statuses = ["resolved", "resolved", "closed", "open", "in_progress"]
    out = compute_child_progress(statuses)
    assert out["total"] == 5
    assert out["done"] == 3
    assert out["open"] == 2
    assert out["percent"] == 60
    assert out["byStatus"]["resolved"] == 2
    assert out["byStatus"]["closed"] == 1
    assert out["byStatus"]["open"] == 1
    assert out["byStatus"]["in_progress"] == 1


def test_all_done_percent_100():
    out = compute_child_progress(["resolved", "closed", "rejected"])
    assert out["total"] == 3
    assert out["done"] == 3
    assert out["open"] == 0
    assert out["percent"] == 100


def test_enum_like_value_attr():
    class S:
        def __init__(self, v):
            self.value = v

    out = compute_child_progress([S("resolved"), S("open")])
    assert out["done"] == 1
    assert out["total"] == 2
    assert out["percent"] == 50
```

- [ ] **Step 2: Run → FAIL**（module missing）

```bash
cd backend && python -m pytest tests/unit/test_e70_child_progress.py -v
```

- [ ] **Step 3: 最小实现**

```python
"""E70: sub-issue childProgress aggregation helpers (direct children only)."""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

CHILD_PROGRESS_DONE_STATUSES = frozenset({"resolved", "closed", "rejected"})


def _norm_status(s: Any) -> str:
    if s is None:
        return ""
    if hasattr(s, "value"):
        return str(s.value)
    return str(s)


def compute_child_progress(statuses: Iterable[Any]) -> dict:
    norms = [_norm_status(s) for s in statuses]
    by_status = dict(Counter(norms))
    # drop empty key if any
    by_status.pop("", None)
    total = len(norms)
    done = sum(by_status.get(s, 0) for s in CHILD_PROGRESS_DONE_STATUSES)
    open_count = total - done
    percent = round(done / total * 100) if total > 0 else None
    return {
        "total": total,
        "done": done,
        "open": open_count,
        "percent": percent,
        "byStatus": by_status,
    }
```

- [ ] **Step 4: Run → PASS** + commit

```bash
cd backend && python -m pytest tests/unit/test_e70_child_progress.py -v
git add backend/opentask/services/child_progress.py backend/tests/unit/test_e70_child_progress.py
git commit -m "feat(E70): compute_child_progress helper (Q1a/Q3a)"
```

---

### Task 3 — B：详情默认 + 列表 include + children 同构（TDD）

**Files:**
- Modify: `backend/opentask/models/issue/schema.py` — add `ChildProgress`
- Modify: `backend/opentask/services/issue_service.py` — batch helpers
- Modify: `backend/opentask/api/issue/router.py` — wire detail/list/children
- Create: `backend/tests/api/test_e70_child_progress.py`

**Interfaces:**
- Schema:

```python
class ChildProgress(BaseModel):
    total: int
    done: int
    open: int
    percent: Optional[int] = None
    byStatus: Optional[Dict[str, int]] = None
```

- `IssueService.child_progress_for_parent(parent_id: str) -> dict`  
  用 `list_child_issues` → statuses → `compute_child_progress`（软删已排除；仅直接子）
- `IssueService.child_progress_for_parents(parent_ids: list[str]) -> dict[str, dict]`  
  单查：`select(Issue.parent_issue_id, Issue.status).where(parent_issue_id.in_(...), is_deleted==False)` 再按 parent 聚合；无子父返回 `compute_child_progress([])`
- 详情 GET：在现有 children 填充后设 `issue_dict["childProgress"] = await service.child_progress_for_parent(issue.id)`（可用已取 children 的 status，避免双查）
- 列表：`include_set` 含 `childProgress` 时批量填 `payload["childProgress"]`；否则 **不** 带该 key
- `GET /{id}/children`：响应根加同构 `childProgress`（薄）：`data: {rows, total, childProgress}`
- include 描述更新：`custom_fields,childProgress`
- **不** fire webhook；无 alembic

- [ ] **Step 1: 红测**

```python
"""E70: childProgress on issue detail / list include / children endpoint."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e70"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-Id"] = workspace_id
    return h


async def _issue(client, user, title="E70", **extra):
    body = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        "reporter_id": user["userId"],
        **extra,
    }
    r = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


@pytest.mark.asyncio
async def test_detail_default_child_progress_mixed(test_client: AsyncClient):
    user = await _register(test_client, "mix")
    parent = await _issue(test_client, user, "parent")
    for title, st in [
        ("c1", "resolved"),
        ("c2", "resolved"),
        ("c3", "closed"),
        ("c4", "open"),
        ("c5", "in_progress"),
    ]:
        child = await _issue(test_client, user, title, parent_issue_id=parent["id"])
        if st != "open":
            ur = await test_client.put(
                f"/api/issues/{child['id']}",
                headers=_auth(user["token"], user["workspaceId"]),
                json={"status": st},
            )
            assert ur.status_code == 200, ur.text

    got = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    cp = got.json()["data"]["childProgress"]
    assert cp["total"] == 5
    assert cp["done"] == 3
    assert cp["open"] == 2
    assert cp["percent"] == 60


@pytest.mark.asyncio
async def test_detail_zero_children_percent_null(test_client: AsyncClient):
    user = await _register(test_client, "z")
    parent = await _issue(test_client, user, "lonely")
    got = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    cp = got.json()["data"]["childProgress"]
    assert cp["total"] == 0
    assert cp["done"] == 0
    assert cp["open"] == 0
    assert cp["percent"] is None


@pytest.mark.asyncio
async def test_soft_deleted_child_excluded(test_client: AsyncClient):
    user = await _register(test_client, "del")
    parent = await _issue(test_client, user, "p-del")
    live = await _issue(test_client, user, "live", parent_issue_id=parent["id"])
    gone = await _issue(test_client, user, "gone", parent_issue_id=parent["id"])
    dr = await test_client.delete(
        f"/api/issues/{gone['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert dr.status_code == 200, dr.text
    got = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    cp = got.json()["data"]["childProgress"]
    assert cp["total"] == 1
    assert live["id"]  # sanity
    assert cp["percent"] == 0  # still open


@pytest.mark.asyncio
async def test_list_without_include_omits_key(test_client: AsyncClient):
    user = await _register(test_client, "li0")
    parent = await _issue(test_client, user, "p-li0")
    await _issue(test_client, user, "c", parent_issue_id=parent["id"])
    lst = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"page_size": 50},
    )
    assert lst.status_code == 200
    rows = lst.json()["data"]["rows"]
    row = next(r for r in rows if r["id"] == parent["id"])
    assert "childProgress" not in row


@pytest.mark.asyncio
async def test_list_include_matches_detail(test_client: AsyncClient):
    user = await _register(test_client, "li1")
    parent = await _issue(test_client, user, "p-li1")
    c = await _issue(test_client, user, "c-done", parent_issue_id=parent["id"])
    await test_client.put(
        f"/api/issues/{c['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"status": "resolved"},
    )
    detail = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    dcp = detail.json()["data"]["childProgress"]
    lst = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"include": "childProgress", "page_size": 50},
    )
    row = next(r for r in lst.json()["data"]["rows"] if r["id"] == parent["id"])
    assert row["childProgress"]["total"] == dcp["total"]
    assert row["childProgress"]["done"] == dcp["done"]
    assert row["childProgress"]["percent"] == dcp["percent"]


@pytest.mark.asyncio
async def test_children_endpoint_embeds_progress(test_client: AsyncClient):
    user = await _register(test_client, "ch")
    parent = await _issue(test_client, user, "p-ch")
    await _issue(test_client, user, "c1", parent_issue_id=parent["id"])
    r = await test_client.get(
        f"/api/issues/{parent['id']}/children",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total"] == 1
    assert data["childProgress"]["total"] == 1
    assert data["childProgress"]["percent"] == 0


@pytest.mark.asyncio
async def test_grandchild_not_counted(test_client: AsyncClient):
    user = await _register(test_client, "gc")
    parent = await _issue(test_client, user, "p-gc")
    child = await _issue(test_client, user, "c-gc", parent_issue_id=parent["id"])
    await _issue(test_client, user, "gc1", parent_issue_id=child["id"])
    got = await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    cp = got.json()["data"]["childProgress"]
    assert cp["total"] == 1  # only direct child


@pytest.mark.asyncio
async def test_detail_read_no_new_webhook(test_client: AsyncClient, monkeypatch):
    from unittest.mock import AsyncMock

    fired = []

    async def _spy(*args, **kwargs):
        fired.append((args, kwargs))

    monkeypatch.setattr(
        "opentask.services.issue_service.fire_webhooks",
        AsyncMock(side_effect=_spy),
    )
    user = await _register(test_client, "wh")
    parent = await _issue(test_client, user, "p-wh")
    await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    # create may have fired; detail GET must not add new fires after create
    before = len(fired)
    await test_client.get(
        f"/api/issues/{parent['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert len(fired) == before
```

- [ ] **Step 2: Run → FAIL**（missing childProgress）

```bash
cd backend && python -m pytest tests/api/test_e70_child_progress.py -v
```

- [ ] **Step 3: 实现**

1. schema：在 `IssueChildSummary` 后加 `ChildProgress`；`IssueResponse` 加可选 `childProgress: Optional[ChildProgress] = None`（详情/列表由 router 手动塞 dict 亦可，schema 可选）

2. `issue_service.py` 末尾附近：

```python
async def child_progress_for_parent(self, parent_id: str) -> dict:
    children = await self.list_child_issues(parent_id)
    statuses = [c.status for c in children]
    from opentask.services.child_progress import compute_child_progress
    return compute_child_progress(statuses)

async def child_progress_for_parents(self, parent_ids: list[str]) -> dict[str, dict]:
    from opentask.services.child_progress import compute_child_progress
    if not parent_ids:
        return {}
    q = await self.db.execute(
        select(Issue.parent_issue_id, Issue.status).where(
            Issue.parent_issue_id.in_(parent_ids),
            Issue.is_deleted == False,  # noqa: E712
        )
    )
    buckets: dict[str, list] = {pid: [] for pid in parent_ids}
    for pid, status in q.all():
        if pid in buckets:
            buckets[pid].append(status)
    return {pid: compute_child_progress(sts) for pid, sts in buckets.items()}
```

3. router 详情：children 填充后：

```python
from opentask.services.child_progress import compute_child_progress
issue_dict["childProgress"] = compute_child_progress(
    [c.status for c in children]
)
```

4. router 列表：

```python
progress_map = {}
if "childProgress" in include_set:
    progress_map = await service.child_progress_for_parents([i.id for i in issues])
# in loop:
if "childProgress" in include_set:
    payload["childProgress"] = progress_map.get(
        issue.id, {"total": 0, "done": 0, "open": 0, "percent": None, "byStatus": {}}
    )
```

5. children endpoint：

```python
from opentask.services.child_progress import compute_child_progress
cp = compute_child_progress([c.status for c in children])
return {..., "data": {"rows": rows, "total": len(rows), "childProgress": cp}, ...}
```

6. Update include Query description to mention `childProgress`.

- [ ] **Step 4: PASS** + commit

```bash
cd backend && python -m pytest tests/api/test_e70_child_progress.py tests/unit/test_e70_child_progress.py -v
git add backend/opentask/models/issue/schema.py \
  backend/opentask/services/issue_service.py \
  backend/opentask/api/issue/router.py \
  backend/tests/api/test_e70_child_progress.py
git commit -m "feat(E70): childProgress on detail/list/children (Q2a/Q4a)"
```

---

### Task 4 — C：FE 进度条 / 徽章 + vitest

**Files:**
- Create: `frontend/src/utils/childProgress.ts`
- Create: `frontend/src/utils/childProgress.test.ts`
- Modify: `frontend/src/typings/api/issue.d.ts`
- Modify: `frontend/src/views/issue/detail/index.vue`
- Modify: `frontend/src/views/issue/list/index.vue`
- Modify: `frontend/src/views/issue/list/modules/IssueBoard.vue`

**Interfaces:**
- `formatChildProgress(cp: {total:number; done:number; percent:number|null} | null|undefined): string | null`  
  - null/undefined/total===0 → `null`（不渲染）  
  - else → `"${done}/${total}"`；若 percent!=null 可另有 `formatChildProgressLabel` → `"2/5 (40%)"`
- `childProgressPercent(cp): number` — 进度条用，total===0 → 0（但 UI 不渲染）

Types:

```typescript
export interface ChildProgress {
  total: number;
  done: number;
  open: number;
  percent: number | null;
  byStatus?: Record<string, number>;
}
// on Issue:
childProgress?: ChildProgress;
```

Detail UI（主内容区 attachments 之上或之下新增「子问题」卡片）：
- `v-if="childSummaries.length > 0 || (issue.childProgress && issue.childProgress.total > 0)"` 或始终显示区但条仅 total>0
- Design：无子项不渲染条；有子项：`NProgress` + `done/total` 文本；列表 `childSummaries`；`+ 添加` 开 modal
- **不**默认给 list API 加 `include=childProgress`（Q4a 加重由调用方 opt-in；详情自带）

List 标题列：若 `row.childProgress && row.childProgress.total > 0`，旁挂小 `NTag` `2/5`  
Board 卡片：同条件小 tag

- [ ] **Step 1: 红测 vitest**

```typescript
import { describe, expect, it } from 'vitest';
import { formatChildProgress, formatChildProgressLabel } from './childProgress';

describe('childProgress', () => {
  it('returns null for empty / missing', () => {
    expect(formatChildProgress(null)).toBeNull();
    expect(formatChildProgress(undefined)).toBeNull();
    expect(formatChildProgress({ total: 0, done: 0, open: 0, percent: null })).toBeNull();
  });

  it('formats mixed and all-done', () => {
    expect(formatChildProgress({ total: 5, done: 3, open: 2, percent: 60 })).toBe('3/5');
    expect(formatChildProgressLabel({ total: 5, done: 3, open: 2, percent: 60 })).toBe('3/5 (60%)');
    expect(formatChildProgress({ total: 3, done: 3, open: 0, percent: 100 })).toBe('3/3');
  });
});
```

- [ ] **Step 2: FAIL → 实现 util → PASS**

```typescript
export interface ChildProgressLike {
  total: number;
  done: number;
  open?: number;
  percent: number | null;
}

export function formatChildProgress(cp?: ChildProgressLike | null): string | null {
  if (!cp || !cp.total) return null;
  return `${cp.done}/${cp.total}`;
}

export function formatChildProgressLabel(cp?: ChildProgressLike | null): string | null {
  const base = formatChildProgress(cp);
  if (!base || !cp) return null;
  if (cp.percent == null) return base;
  return `${base} (${cp.percent}%)`;
}

export function childProgressPercent(cp?: ChildProgressLike | null): number {
  if (!cp || !cp.total) return 0;
  return cp.percent ?? 0;
}
```

- [ ] **Step 3: Wire FE detail/list/board + types**

Detail（示意，插在 attachments 卡后）：

```vue
<NCard v-if="issue" class="mt-12px" size="small" title="子问题">
  <template #header-extra>
    <NButton text size="tiny" @click="showAddSubIssue = true">+ 添加</NButton>
  </template>
  <div v-if="(issue.childProgress?.total || 0) > 0" class="mb-8px">
    <NSpace align="center" :size="8">
      <NProgress
        type="line"
        :percentage="childProgressPercent(issue.childProgress)"
        :show-indicator="false"
        style="width: 160px"
      />
      <NText depth="3" style="font-size: 12px">
        {{ formatChildProgressLabel(issue.childProgress) }}
      </NText>
    </NSpace>
  </div>
  <NEmpty v-if="!childSummaries.length" description="暂无子问题" size="small" />
  <NSpace v-else vertical :size="4">
    <div v-for="c in childSummaries" :key="c.id" class="linked-issue">
      <NButton text size="tiny" type="primary"
        @click="router.push({ path: '/issue/detail', query: { id: c.id } })">
        {{ c.issue_code }} · {{ c.title }}
      </NButton>
      <NTag size="tiny" :bordered="false">{{ c.status }}</NTag>
    </div>
  </NSpace>
</NCard>
```

Import `NProgress`；import helpers from `@/utils/childProgress`.

List title render：在 relation badges 后追加 childProgress tag（有 total 时）。  
Board：在 blocks meta 旁加 tag。

- [ ] **Step 4: vitest + build；若 elegant-router 丢 f/r 则还原**

```bash
cd frontend && pnpm exec vitest run src/utils/childProgress.test.ts
pnpm run build
# spy f+r in elegant-router.d.ts; restore if dropped
git add frontend/...
git commit -m "feat(E70): FE childProgress bar + badges + vitest"
```

---

### Task 5 — D：CLI 1.54.0

**Files:**
- Bump all `1.53.0` → `1.54.0` under `agent-harness/opentask-cli`
- Modify: `opentask/core/issue.py` — `_display_issue_details` 打印 ChildProgress；`list_issues` 加 `--include`
- Modify: `opentask/utils/api_client.py` — list_issues 已有 include，确认透传
- Create: `tests/test_e70_child_progress.py`

```python
"""E70 CLI: childProgress on issue show + version 1.54.0."""
from click.testing import CliRunner
from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1540():
    r = CliRunner().invoke(cli, ["--version"])
    assert r.exit_code == 0
    assert "1.54.0" in r.output
    assert VERSION == "1.54.0"
    assert __version__ == "1.54.0"


def test_issue_list_include_help():
    r = CliRunner().invoke(cli, ["issue", "list", "--help"])
    assert r.exit_code == 0
    assert "include" in r.output.lower()
```

`_display_issue_details` 在 Statistics 后：

```python
cp = issue.get("childProgress") or issue.get("child_progress")
if cp and cp.get("total"):
    pct = cp.get("percent")
    label = f"{cp.get('done', 0)}/{cp.get('total', 0)}"
    if pct is not None:
        label = f"{label} ({pct}%)"
    skin.info("ChildProgress")
    skin.status_block({"ChildProgress": label})
elif cp is not None and cp.get("total") == 0:
    pass  # omit per design（无子项省略）
```

list command：

```python
@click.option("--include", "include", default=None, help="Comma extras: custom_fields,childProgress")
# pass include=include to client; if both cf-need and include, merge uniquely
```

- [ ] PASS directed + commit `feat(E70): CLI 1.54.0 childProgress show + pins`

---

### Task 6 — Verify + acceptance

- [ ] BE full suite；定向 e70 + unit
- [ ] CLI full suite
- [ ] FE vitest + build；确认 `f`+`r`
- [ ] 填 acceptance tip SHA + 门禁；`superpowers: design/plan/TDD/verify/acceptance = ok`
- [ ] tip commit；**STOP** — 不 push / 不开 PR / 不自开 E71

## Spec coverage self-check
| Spec | Task |
|------|------|
| A semantics done/open/percent/direct/soft-del | T2+T3 |
| B detail default + list include + children 同构 + 无 alembic | T3 |
| C FE bar/badge + vitest + build + f+r | T4 |
| D CLI 1.54.0 show + pins + optional list include | T5 |
| E tenant/no webhook/no-emit/邻面不动 | T3 spy + T6 |
| Q1a–Q6a / D1–D7 | 全文锁定 |

