# E73 Plan：Issue start_date mid — 计划开始日 · CLI 1.57.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`be2a150`（全文 `be2a150b212cc76379423405584947c86cc0e7ee`）· 分支 `sprint/E73-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e73-issue-start-date-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E74**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Issue 可读写一等字段 `start_date`（计划开始；独立于自动 `started_at`）；Create/Update/详情；start.date ≤ due.date（违则 400）；列表 `start_before`/`start_after` + 可选 `sort=start_date`；FE 详情可编 + Timeline 双端有值画条；CLI **1.57.0**；无新 webhook 事件名；formula no-emit；不驱动 due-reminder；不改 E63–E72 邻面主表面。

**Architecture:** alembic 加 `issues.start_date`（DateTime NULL + index，同 `due_date`）；纯函数 `validate_start_due` 做日历日校验；`IssueService` create/update 合并既有另一端后校验；list 过滤对齐 `due_before`；audit 扩 `TimelineAction.START_DATE_CHANGED` + PG enum ADD VALUE；Timeline API 返回 `start_date`；FE util `issueTimelinePlacement`；CLI pins 全钉 1.57.0。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E74；中文 docs；CLI **1.57.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；无 Activity Push；无门户/甘特/模板再开；**无 CSV**（Q2a）
- 语义 ≠ `started_at`；不改 recurrence/due-reminder 主语义；start_date **不**触发到期提醒 / SLA
- 不改 E63–E72 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- Q5a：不新增 webhook 事件名（走 `issue.updated`）
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/alembic/versions/2026_11_05_5300-a4b5c6d7e8f9_issue_start_date.py` | column + enum ADD VALUE |
| `backend/opentask/models/issue/model.py` | `Issue.start_date`；timeline ENUM 加值 |
| `backend/opentask/models/issue/enums.py` | `START_DATE_CHANGED` |
| `backend/opentask/models/issue/schema.py` | Create/Update/Response + query filters |
| `backend/opentask/services/issue_dates.py` | `validate_start_due` 纯函数 |
| `backend/opentask/services/issue_service.py` | create/update/list/sort + audit |
| `backend/opentask/api/issue/router.py` | `start_before`/`start_after` Query |
| `backend/opentask/services/project_health/service.py` | timeline issues 含 `start_date` |
| `backend/tests/unit/test_e73_start_due_validate.py` | unit TDD |
| `backend/tests/api/test_e73_issue_start_date.py` | API TDD |
| `frontend/src/utils/project-timeline.ts` (+test) | `start_date?` + placement |
| `frontend/src/utils/formatTimelineAction.ts` (+test) | `start_date_changed` |
| `frontend/src/views/issue/detail/index.vue` | 开始 EditableField |
| `frontend/src/views/workflow/project-detail/index.vue` | bar when start+due |
| `frontend/src/typings/api/issue.d.ts` / `project.d.ts` | types |
| `agent-harness/opentask-cli/**` | 1.57.0 + `--start-date` + show/list |
| `docs/superpowers/acceptances/2026-11-05-E73-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E73-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e73-issue-start-date-mid.md \
  docs/superpowers/acceptances/2026-11-05-E73-acceptance.md
git commit -m "docs(E73): plan + acceptance skeleton"
```

---

### Task 2 — A：validate_start_due 纯函数（TDD）

**Files:**
- Create: `backend/opentask/services/issue_dates.py`
- Create: `backend/tests/unit/test_e73_start_due_validate.py`

**Interfaces:**
- `validate_start_due(*, start_date: datetime | date | None, due_date: datetime | date | None) -> None`
  - 任一为 None → OK
  - 比较 `.date()`；`start > due` → `HTTPException(400, detail={"code":"start_after_due","message":"start_date must be on or before due_date"})`
  - 同日 OK

- [ ] **Step 1: 红测**

```python
"""E73: start_date vs due_date calendar validation."""
from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi import HTTPException

from opentask.services.issue_dates import validate_start_due


def test_both_none_ok():
    validate_start_due(start_date=None, due_date=None)


def test_only_start_ok():
    validate_start_due(start_date=datetime(2026, 11, 10), due_date=None)


def test_only_due_ok():
    validate_start_due(start_date=None, due_date=datetime(2026, 11, 10))


def test_same_day_ok():
    validate_start_due(
        start_date=datetime(2026, 11, 10, 8, 0),
        due_date=datetime(2026, 11, 10, 18, 0),
    )


def test_start_before_due_ok():
    validate_start_due(
        start_date=date(2026, 11, 9),
        due_date=date(2026, 11, 10),
    )


def test_start_after_due_400():
    with pytest.raises(HTTPException) as ei:
        validate_start_due(
            start_date=datetime(2026, 11, 10),
            due_date=datetime(2026, 11, 9),
        )
    assert ei.value.status_code == 400
    assert ei.value.detail["code"] == "start_after_due"
```

- [ ] **Step 2: Run → FAIL**（module missing）

```bash
cd backend && python -m pytest tests/unit/test_e73_start_due_validate.py -v
```

- [ ] **Step 3: 最小实现**

```python
# backend/opentask/services/issue_dates.py
"""E73: issue planned start_date helpers (independent of started_at)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Union

from fastapi import HTTPException

DateLike = Union[datetime, date, None]


def _as_date(value: DateLike) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise TypeError(f"unsupported date-like: {type(value)!r}")


def validate_start_due(*, start_date: DateLike, due_date: DateLike) -> None:
    """Q1a: when both set, require start.date <= due.date else 400."""
    s = _as_date(start_date)
    d = _as_date(due_date)
    if s is None or d is None:
        return
    if s > d:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "start_after_due",
                "message": "start_date must be on or before due_date",
            },
        )
```

- [ ] **Step 4: Run → PASS** + commit

```bash
git add backend/opentask/services/issue_dates.py backend/tests/unit/test_e73_start_due_validate.py
git commit -m "feat(E73): validate_start_due helper (TDD)"
```

---

### Task 3 — A：alembic + model + schema + enum

**Files:**
- Create: `backend/alembic/versions/2026_11_05_5300-a4b5c6d7e8f9_issue_start_date.py`
- Modify: `backend/opentask/models/issue/model.py`（列 + timeline ENUM 列表 + `__table_args__` index）
- Modify: `backend/opentask/models/issue/enums.py`（`START_DATE_CHANGED = "start_date_changed"`）
- Modify: `backend/opentask/models/issue/schema.py`（`start_date` on Base/Update/Response；QueryParams `start_before`/`start_after`）

- [ ] **Step 1:** alembic revision（down=`z3c4d5e6f7a8`）：
  - `op.add_column("issues", sa.Column("start_date", sa.DateTime(), nullable=True))`
  - `op.create_index("idx_issues_start_date", "issues", ["start_date"])`
  - PG: `ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS 'start_date_changed'`
- [ ] **Step 2:** model `start_date` 紧挨 `due_date`；Index；ENUM 字符串列表加 `"start_date_changed"`
- [ ] **Step 3:** schema 字段 + query filters
- [ ] **Step 4:** commit `feat(E73): alembic start_date + schema/enum`

---

### Task 4 — A：Service create/update/list + audit（TDD API）

**Files:**
- Modify: `backend/opentask/services/issue_service.py`
- Modify: `backend/opentask/api/issue/router.py`
- Modify: `backend/opentask/services/project_health/service.py`
- Create: `backend/tests/api/test_e73_issue_start_date.py`

**Interfaces / behavior:**
- create：`_naive_utc(start_date)`；`validate_start_due(start=…, due=…)`
- update：若 payload 含 `start_date` 或 `due_date`，合并另一端当前值后校验；写 timeline `START_DATE_CHANGED`（不调 `notify_due_date_changed`；不把 `start_date` 加入 formula_attrs）
- list：`start_before`/`start_after` 用 `func.date(Issue.start_date)`；`allowed_sort` 加 `"start_date"`
- timeline：issues 序列化含 `start_date`；查询改为 `(due_date IS NOT NULL OR start_date IS NOT NULL)`
- router：Query `start_before`/`start_after` 传入 IssueQueryParams

**API 红测要点（`test_e73_issue_start_date.py`）：**
1. create/update 读写 `start_date`；`started_at` 仍仅 status→in_progress 自动写
2. start=2026-11-10 due=2026-11-09 → 400；同日 OK；仅一侧 OK；清 start OK
3. `start_before`/`start_after` 边界（含当日）
4. `sort_by=start_date` 可选
5. update start → timeline `start_date_changed`；无新 webhook 事件名（仍 `issue.updated`）
6. 纯改 start **不**产生 due_date_changed inbox/notif（spy: 无 `due_date_changed` notif type）

- [ ] **Step 1: 红测文件** → FAIL
- [ ] **Step 2: 实现 service/router/timeline** → PASS
- [ ] **Step 3: commit** `feat(E73): start_date CRUD + filters + audit`

---

### Task 5 — B：FE util + detail + timeline（TDD）

**Files:**
- Modify: `frontend/src/utils/project-timeline.ts` + `.test.ts`
- Modify: `frontend/src/utils/formatTimelineAction.ts` (+ test if present)
- Modify: `frontend/src/typings/api/issue.d.ts` / `project.d.ts`
- Modify: `frontend/src/views/issue/detail/index.vue`（开始字段邻 due）
- Modify: `frontend/src/views/workflow/project-detail/index.vue`（双端 → bar）

**Interfaces:**
```ts
export interface TimelineIssueLike {
  id: string;
  due_date?: string | null;
  start_date?: string | null;
}

export type IssueTimelinePlacement =
  | { kind: 'bar'; start: string; end: string }
  | { kind: 'dot'; at: string }
  | null;

export function issueTimelinePlacement(issue: TimelineIssueLike): IssueTimelinePlacement;
```
- 有 start+due → `{kind:'bar', start, end:due}`
- 仅 due → `{kind:'dot', at:due}`
- 仅 start / 皆空 → `null`（本轮不画纯 start 点）
- `computeTimelineRange` / `isTimelineEmpty` 计入 `start_date`

Detail：`editingStartDate` / `tempStartDate` / `saveStartDate` 镜像 due；label「开始」。

Timeline Vue：若 placement.kind==='bar' 用 `barStyle`；else 若 dot 用现有 `timeline-dot`。

- [ ] **Step 1: vitest 红** → implement → 绿
- [ ] **Step 2: detail + project-detail UI**
- [ ] **Step 3: commit** `feat(E73): FE start_date detail + timeline bar`

---

### Task 6 — C：CLI 1.57.0

**Files:**
- `agent-harness/opentask-cli/VERSION` → `1.57.0`
- `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask/opentask_cli.py` VERSION
- `opentask/core/issue.py`：create/update `--start-date`；show Start/Due；list `--start-before/--start-after`
- `opentask/utils/api_client.py`：create_issue `start_date=`；list_issues filters
- Create: `agent-harness/opentask-cli/tests/test_e73_start_date.py`（version pin + option help / show formatting unit）

- [ ] **Step 1: 测 VERSION==1.57.0 + help 含 start-date**
- [ ] **Step 2: 实现 pins + flags**
- [ ] **Step 3: commit** `feat(E73): CLI 1.57.0 start-date`

---

### Task 7 — D/E spy + verify + acceptance

**Files:**
- Extend API tests：formula no-emit / no new webhook event name / reminders untouched
- Run gates；restore `f`+`r` if elegant-router drops them after build
- Fill acceptance with tip SHA + counts
- Final tip commit

**Verify commands:**
```bash
cd backend && python -m pytest tests/unit/test_e73_start_due_validate.py tests/api/test_e73_issue_start_date.py -v
cd backend && python -m pytest -q   # full；记 flake
cd ../agent-harness/opentask-cli && python -m pytest -q
cd ../../frontend && pnpm exec vitest run && pnpm run build
# after build: ensure routes index still has /f/:token and /r/:token
```

- [ ] **Step 1:** 全门禁记录
- [ ] **Step 2:** acceptance 填 tip + gates
- [ ] **Step 3:** `git commit` tip；**STOP**（不 push / 不开 E74）

---

## Self-review
- Spec A–E / Q1a–Q6a / ADR D1–D7 均有对应 Task
- 无 TBD；无 CSV；无新 webhook 名；started_at 不动；reminders 不因 start 触发
- CLI 五处 pins 全列；f+r 守门在 Task 7
