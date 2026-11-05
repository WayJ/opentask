# E67 Plan：Workspace 时区进 due/recurrence mid — 本地日历日 · CLI 1.51.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`1fa4a85`（全文 `1fa4a8575e695520783b652a24a39352b407353f`）· 分支 `sprint/E67-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e67-workspace-timezone-due-recurrence-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E68**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** WS 配置合法 IANA `timezone` 后，due reminders 的 soon/overdue/`bucket_date` 与 recurrence title `{date}`/`{yyyy-mm-dd}` 使用 **WS 本地日历日**；空/非法 TZ → UTC；`next_run_at` 仍 UTC naive（无 alembic）；FE 文案对齐；CLI **1.51.0**；无 Push / 无新 webhook；不改 E57–E66 邻面主表面；formula no-emit。

**Architecture:** 新增薄助手 `workspace_time.resolve_workspace_tz` / `local_today`（复用 `validate_timezone`，非法/空→UTC）。`NotificationService.run_due_reminders` 在未注入 `today=` 时按 WS 本地日分类与记账。`expand_title` 接受可选 `local_date`；`run_due`/`_spawn_one` 用同一本地日扩标题，advance 语义不变。FE 去「一律 UTC」文案并加纯函数 vitest。CLI pins → 1.51.0 + help 注明。

**Tech Stack:** FastAPI + SQLAlchemy；zoneinfo；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E68；中文 docs；CLI **1.51.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；无 alembic；不改 E57–E66 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- Q5a：不新增 webhook 事件名、tick 不 fire 新出站
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/workspace_time.py` | `resolve_workspace_tz` / `local_today` |
| `backend/tests/unit/test_e67_workspace_time.py` | 跨日边界单测 |
| `backend/opentask/services/notification/service.py` | `run_due_reminders` 接本地日 |
| `backend/opentask/services/issue_recurrence/service.py` | `expand_title` + `_spawn_one` 本地日 |
| `backend/tests/api/test_e67_workspace_timezone.py` | API/集成 TDD |
| `frontend/src/utils/workspaceLocalToday.ts` | FE 纯函数 |
| `frontend/src/utils/workspaceLocalToday.test.ts` | vitest 跨日 |
| `frontend/src/views/settings/notifications/index.vue` | 文案 |
| `frontend/src/views/settings/recurrences/index.vue` | 文案 |
| `agent-harness/opentask-cli/**` | 1.51.0 pins + help |
| `docs/superpowers/acceptances/2026-11-05-E67-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E67-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e67-workspace-timezone-due-recurrence-mid.md \
  docs/superpowers/acceptances/2026-11-05-E67-acceptance.md
git commit -m "docs(E67): plan + acceptance skeleton"
```

---

### Task 2 — A：workspace_time helper（TDD）

**Files:**
- Create: `backend/opentask/services/workspace_time.py`
- Create: `backend/tests/unit/test_e67_workspace_time.py`

**Interfaces:**
- `resolve_workspace_tz(ws) -> ZoneInfo` — `ws` 可为 Workspace 对象或 duck（`.timezone`）；None/空/非法 → `ZoneInfo("UTC")`（不抛）
- `local_today(ws, *, now_utc: datetime | None = None) -> date` — 将 `now_utc`（naive 视作 UTC）转到 WS TZ 取日历日

- [ ] **Step 1: 红测**

```python
"""E67: workspace local calendar day helpers."""
from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from opentask.services.workspace_time import local_today, resolve_workspace_tz


def test_resolve_none_empty_invalid_to_utc():
    assert resolve_workspace_tz(None) == ZoneInfo("UTC")
    assert resolve_workspace_tz(SimpleNamespace(timezone=None)) == ZoneInfo("UTC")
    assert resolve_workspace_tz(SimpleNamespace(timezone="")) == ZoneInfo("UTC")
    assert resolve_workspace_tz(SimpleNamespace(timezone="Not/A_Zone")) == ZoneInfo("UTC")


def test_resolve_asia_shanghai():
    assert resolve_workspace_tz(SimpleNamespace(timezone="Asia/Shanghai")) == ZoneInfo(
        "Asia/Shanghai"
    )


def test_local_today_crosses_utc_midnight_shanghai():
    # UTC 2026-11-05 16:30 → Shanghai 2026-11-06 00:30
    now = datetime(2026, 11, 5, 16, 30, 0, tzinfo=timezone.utc)
    ws = SimpleNamespace(timezone="Asia/Shanghai")
    assert local_today(ws, now_utc=now) == date(2026, 11, 6)


def test_local_today_none_tz_stays_utc_day():
    now = datetime(2026, 11, 5, 16, 30, 0)  # naive = UTC
    ws = SimpleNamespace(timezone=None)
    assert local_today(ws, now_utc=now) == date(2026, 11, 5)
```

- [ ] **Step 2: Run → FAIL**（module missing）

```bash
cd backend && python -m pytest tests/unit/test_e67_workspace_time.py -v
```

- [ ] **Step 3: 最小实现**

```python
"""E67: workspace timezone → local calendar day helpers."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from opentask.services.sla.business_hours import validate_timezone


def resolve_workspace_tz(ws: Any) -> ZoneInfo:
    raw: Optional[str] = None
    if ws is None:
        raw = None
    elif isinstance(ws, str):
        raw = ws
    else:
        raw = getattr(ws, "timezone", None)
    try:
        name = validate_timezone(raw)
    except ValueError:
        return ZoneInfo("UTC")
    if not name:
        return ZoneInfo("UTC")
    return ZoneInfo(name)


def local_today(ws: Any, *, now_utc: datetime | None = None) -> date:
    tz = resolve_workspace_tz(ws)
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    return now.astimezone(tz).date()
```

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit**

```bash
git add backend/opentask/services/workspace_time.py backend/tests/unit/test_e67_workspace_time.py
git commit -m "feat(E67): workspace_time resolve_tz + local_today"
```

---

### Task 3 — B：due reminders 接本地日（TDD）

**Files:**
- Modify: `backend/opentask/services/notification/service.py` (`run_due_reminders`)
- Create/extend: `backend/tests/api/test_e67_workspace_timezone.py`

**Interfaces:**
- `run_due_reminders(..., today=None, now_utc=None)`：若 `today` 注入则仍优先；否则 `select(Workspace)` + `local_today(ws, now_utc=now_utc)`
- soon/overdue/`bucket_date` 一律该 `today`（Q1a）

- [ ] **Step 1: 红测**（API：设 TZ Asia/Shanghai；服务层注入 `now_utc` 跨日）

```python
"""E67: workspace TZ into due reminders + recurrence title."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from opentask.models.workspace.model import Workspace
from opentask.services.notification.service import NotificationService


async def _register(client, prefix="e67"):
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


def _auth(token, workspace_id=None):
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-Id"] = workspace_id
    return h


async def _set_tz(client, user, tz: str | None):
    body = {"timezone": tz} if tz is not None else {"timezone": ""}
    r = await client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"]),
        json={"timezone": tz} if tz else {"timezone": None},
    )
    # workspace update may reject null — use empty via service if needed
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_e67_due_reminders_uses_shanghai_local_day(test_client: AsyncClient, db_session):
    """UTC 16:30 → Shanghai next day; due=local today → soon not overdue."""
    user = await _register(test_client, "e67_due")
    r = await test_client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"]),
        json={"timezone": "Asia/Shanghai"},
    )
    assert r.status_code == 200, r.text

    # due date = Shanghai local 2026-11-06
    due_iso = "2026-11-06T00:00:00"
    ir = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "e67-due-local",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
            "assignee_id": user["userId"],
            "due_date": due_iso,
        },
    )
    assert ir.status_code == 200, ir.text

    now = datetime(2026, 11, 5, 16, 30, 0, tzinfo=timezone.utc)
    svc = NotificationService(db_session)
    result = await svc.run_due_reminders(
        workspace_id=user["workspaceId"],
        actor_user_id=user["userId"],
        now_utc=now,
    )
    assert result["remindersCreated"] >= 1
    # bucket_date should be local 2026-11-06
    deliveries = await svc.list_due_reminder_deliveries(
        workspace_id=user["workspaceId"],
        bucket_date=date(2026, 11, 6),
    )
    assert len(deliveries) >= 1
```

（实现时按仓库 `db_session` fixture 实际名调整；若无 session fixture，则用 API tick + 直接改 WS TZ 并用 monkeypatch `datetime.utcnow` / `local_today` 注入。优先扩展 `run_due_reminders` 的 `now_utc=` 参数。）

另加：`timezone=None` 时同 `now` → bucket UTC `2026-11-05`；以及 `today=` 注入仍覆盖。

- [ ] **Step 2: Run → FAIL**（尚无 `now_utc` / 仍 UTC）

- [ ] **Step 3: 改 `run_due_reminders`**

在文件顶 import：
```python
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.workspace_time import local_today
```

方法签名加 `now_utc: Optional[datetime] = None`，开头：
```python
if today is None:
    ws_row = (
        await self.db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ).scalar_one_or_none()
    today = local_today(ws_row, now_utc=now_utc)
```

保留 `today=` 覆盖。

- [ ] **Step 4: PASS**

- [ ] **Step 5: Commit** `feat(E67): due reminders use workspace local calendar day`

---

### Task 4 — C：recurrence title 本地日（TDD）

**Files:**
- Modify: `backend/opentask/services/issue_recurrence/service.py`
- Extend: `backend/tests/api/test_e67_workspace_timezone.py` + unit `test_recurrence_schedule.py` or e67 unit

**Interfaces:**
- `expand_title(template, when, *, local_date: date | None = None) -> str`
- `_spawn_one`：load WS → `local_date=local_today(ws, now_utc=now)` 传入；**不**改 `advance_*` / `next_run_at` 比较（仍 UTC naive）

- [ ] **Step 1: 红测**

```python
def test_expand_title_local_date_override():
    from datetime import date, datetime
    from opentask.services.issue_recurrence.service import expand_title
    when = datetime(2026, 11, 5, 16, 30, 0)
    assert expand_title("A {date}", when, local_date=date(2026, 11, 6)) == "A 2026-11-06"
    assert expand_title("B {yyyy-mm-dd}", when) == "B 2026-11-05"  # default when.date()
```

集成：设 TZ Shanghai；创建 recurrence title `Daily {date}`，`next_run_at` 已到期；`run_due` 在固定 now → 创建 issue 标题含本地日；`next_run_at` 推进且无 migration。

- [ ] **Step 2–4: 实现 + PASS**

```python
def expand_title(template: str, when: datetime, *, local_date: date | None = None) -> str:
    d = local_date if local_date is not None else when.date()
    date_s = d.strftime("%Y-%m-%d")
    return (
        (template or "")
        .replace("{yyyy-mm-dd}", date_s)
        .replace("{date}", date_s)
    )
```

`_spawn_one`：
```python
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.workspace_time import local_today
...
ws = (await self.db.execute(select(Workspace).where(Workspace.id == row.workspace_id))).scalar_one_or_none()
title = expand_title(row.title_template, now, local_date=local_today(ws, now_utc=now))
```

- [ ] **Step 5: Commit** `feat(E67): recurrence title {date} uses workspace local day`

---

### Task 5 — D：FE 文案 + vitest 纯函数

**Files:**
- Create: `frontend/src/utils/workspaceLocalToday.ts`
- Create: `frontend/src/utils/workspaceLocalToday.test.ts`
- Modify: `frontend/src/views/settings/notifications/index.vue`
- Modify: `frontend/src/views/settings/recurrences/index.vue`

- [ ] **Step 1: 红测 vitest**

```ts
import { describe, expect, it } from 'vitest';
import { localTodayIso, resolveWorkspaceTzClient } from './workspaceLocalToday';

describe('workspaceLocalToday', () => {
  it('empty/invalid → UTC', () => {
    expect(resolveWorkspaceTzClient(null)).toBe('UTC');
    expect(resolveWorkspaceTzClient('')).toBe('UTC');
    expect(resolveWorkspaceTzClient('Not/A_Zone')).toBe('UTC');
  });

  it('Shanghai crosses UTC day', () => {
    const now = new Date(Date.UTC(2026, 10, 5, 16, 30, 0)); // Nov 5
    expect(localTodayIso('Asia/Shanghai', now)).toBe('2026-11-06');
    expect(localTodayIso(null, now)).toBe('2026-11-05');
  });
});
```

- [ ] **Step 2: 实现**

```ts
export function resolveWorkspaceTzClient(tz: string | null | undefined): string {
  const s = (tz ?? '').trim();
  if (!s) return 'UTC';
  try {
    // throws RangeError for invalid IANA in most engines
    Intl.DateTimeFormat('en-US', { timeZone: s }).format(new Date());
    return s;
  } catch {
    return 'UTC';
  }
}

export function localTodayIso(tz: string | null | undefined, now: Date = new Date()): string {
  const zone = resolveWorkspaceTzClient(tz);
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: zone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now);
  const y = parts.find(p => p.type === 'year')?.value;
  const m = parts.find(p => p.type === 'month')?.value;
  const d = parts.find(p => p.type === 'day')?.value;
  return `${y}-${m}-${d}`;
}
```

文案：
- notifications：`按工作区时区日历日扫描（未设时区则 UTC）；即将到期 = 今日起 3 日内；逾期每日至多一条。…` + 可选链到 SLA 设置
- recurrences：`标题日期按工作区时区；next_run_at 存 UTC · 外部调度调 run-due`；列头可保留 `(UTC)` 因存贮语义

**不**新开时区页（Q4a）。

- [ ] **Step 3–5: vitest PASS + commit** `feat(E67): FE local-day copy + workspaceLocalToday util`

---

### Task 6 — E：CLI 1.51.0 pins + help

**Files:**
- `agent-harness/opentask-cli/setup.py` / `opentask/__init__.py` / `opentask/opentask_cli.py` → **1.51.0**
- Bulk：所有测试中 `1.50.0` → `1.51.0`
- Create: `tests/test_e67_workspace_timezone.py`（version pin）
- Modify help：`notif.py` run-due-reminders / due-deliveries；`recurrence.py` run-due

```python
"""执行到期提醒 tick（工作区时区本地日历日；未设则 UTC；外部调度，无内置 cron）。"""
...
@click.option("--bucket-date", ..., help="账本 YYYY-MM-DD（工作区本地日）")
```

```python
def recurrence_run_due(...):
    """跑到期周期建单（标题 {date} 按工作区时区；next_run_at 仍 UTC naive）。"""
```

- [ ] Commit `feat(E67): CLI 1.51.0 pins + due/recurrence TZ help`

---

### Task 7 — F：安全 / no-emit / 邻面不动 + acceptance

- Spy：due/recurrence tick 路径不 `fire_webhooks`（patch assert not called）
- 不触 E66 signed-url / E65 relations / E64 holiday / E63 status 主表面
- formula 路径未改
- 守 elegant-router `f`+`r`（勿误删）
- 跑门禁：BE 全量 + 定向 e67/e39/recurrence；CLI 全量；FE vitest + build
- 填 acceptance tip SHA + 门禁数
- tip commit；**STOP**；不 push；不自开 E68

```bash
# BE
cd backend && python -m pytest tests/unit/test_e67_workspace_time.py tests/api/test_e67_workspace_timezone.py tests/api/test_e39_due_reminders.py tests/api/test_recurrences.py tests/unit/test_recurrence_schedule.py -v
cd backend && python -m pytest -q  # full
# CLI
cd agent-harness/opentask-cli && python -m pytest -q
# FE
cd frontend && pnpm exec vitest run && pnpm run build
```

---

## Spec coverage self-check
| Design | Task |
|--------|------|
| A helper | T2 |
| B due local | T3 |
| C recurrence title only | T4 |
| D FE copy + vitest | T5 |
| E CLI 1.51.0 | T6 |
| F no-emit / 邻面 | T7 |
| Q1a–Q6a / D1–D7 | 全任务 Global Constraints |
| 无 alembic / 无 Push | Global + T4 |

## Placeholder scan
无 TBD/TODO；代码块完整。
