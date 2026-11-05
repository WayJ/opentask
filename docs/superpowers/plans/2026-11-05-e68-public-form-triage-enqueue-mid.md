# E68 Plan：公开表单 → Triage 入队 mid — enqueue_triage · CLI 1.52.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`6e3d1a6`（全文 `6e3d1a6a311c436559aad90bc860e356fa266d78`）· 分支 `sprint/E68-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e68-public-form-triage-enqueue-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E69**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** 表单开启 `enqueue_triage` 后，公开 submit 创建的 Issue 进入 Triage（`triage_status=pending`）；默认 false 行为不变；可与 `create_customer_request` 并存；FE 设置开关 + 成功文案；CLI **1.52.0**；无 status 深链 / Push / 甘特 / 新 webhook；不改 E57–E67 邻面主表面；formula no-emit。

**Architecture:** alembic 增列 `issue_forms.enqueue_triage` Boolean NOT NULL DEFAULT false。serialize/create/patch 暴露 `enqueueTriage`。`IssueFormService.submit` 在 `create_issue`（及可选 CR）之后，若 flag 开则调用 `TriageService.enqueue`（已 pending 幂等），响应增 `triageEnqueued`。FE 设置开关 + 成功页文案纯函数；CLI pins→1.52.0 + `--enqueue-triage`。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E69；中文 docs；CLI **1.52.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；不改 E57–E67 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- Q5a：不新增 webhook 事件名、入队不 fire 新出站
- 非目标见 design §2；无 status URL 深链；不改 recurrence advance

## File map
| Path | Role |
|------|------|
| `backend/alembic/versions/2026_11_05_5000-x1a2b3c4d5e6_issue_forms_enqueue_triage.py` | alembic 列 |
| `backend/opentask/models/issue_form/model.py` | `enqueue_triage` |
| `backend/opentask/services/issue_form/service.py` | serialize/create/update/submit |
| `backend/opentask/api/forms/router.py` | FormCreate/Update `enqueueTriage` |
| `backend/tests/api/test_e68_form_triage_enqueue.py` | BE TDD |
| `frontend/src/service/api/forms.ts` | types + `formSubmitSuccessCopy` |
| `frontend/src/service/api/forms.test.ts` | vitest |
| `frontend/src/views/settings/forms/index.vue` | 设置开关 |
| `frontend/src/views/f/[token].vue` | 成功文案 |
| `agent-harness/opentask-cli/**` | 1.52.0 + flags |
| `docs/superpowers/acceptances/2026-11-05-E68-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E68-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e68-public-form-triage-enqueue-mid.md \
  docs/superpowers/acceptances/2026-11-05-E68-acceptance.md
git commit -m "docs(E68): plan + acceptance skeleton"
```

---

### Task 2 — A：alembic + model + serialize/create/patch（TDD）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_5000-x1a2b3c4d5e6_issue_forms_enqueue_triage.py`
- Modify: `backend/opentask/models/issue_form/model.py`
- Modify: `backend/opentask/services/issue_form/service.py`（serialize/create/update）
- Modify: `backend/opentask/api/forms/router.py`
- Create: `backend/tests/api/test_e68_form_triage_enqueue.py`（先测 CRUD 字段）

**Interfaces:**
- Column: `IssueForm.enqueue_triage: bool` NOT NULL default False
- Serialize key: `enqueueTriage: bool`
- Create/Update kwargs: `enqueue_triage: bool | None`

- [ ] **Step 1: 红测**（CRUD exposes enqueueTriage default false）

```python
"""E68: public form → triage enqueue mid."""
from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

os.environ["OPENTASK_FORM_RATE_LIMIT"] = "0"

DEFAULT_FIELDS = [
    {"key": "title", "type": "title", "label": "标题", "required": True},
    {"key": "description", "type": "description", "label": "描述"},
]


async def _register(client: AsyncClient, prefix: str = "e68"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
        "username": uname,
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


@pytest.mark.asyncio
async def test_e68_form_enqueue_triage_default_false_and_patch(test_client: AsyncClient):
    user = await _register(test_client, "e68_crud")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "TriageForm", "fields": DEFAULT_FIELDS},
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row.get("enqueueTriage") is False
    fid = row["id"]

    patched = await test_client.patch(
        f"/api/forms/{fid}",
        headers=h,
        json={"enqueueTriage": True},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["enqueueTriage"] is True

    got = await test_client.get(f"/api/forms/{fid}", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["enqueueTriage"] is True

    created_on = await test_client.post(
        "/api/forms",
        headers=h,
        json={
            "name": "TriageOn",
            "fields": DEFAULT_FIELDS,
            "enqueueTriage": True,
        },
    )
    assert created_on.status_code == 200, created_on.text
    assert created_on.json()["data"]["enqueueTriage"] is True
```

- [ ] **Step 2: Run → FAIL**（字段缺失）

```bash
cd backend && python -m pytest tests/api/test_e68_form_triage_enqueue.py::test_e68_form_enqueue_triage_default_false_and_patch -v
```

- [ ] **Step 3: alembic + model + serialize/create/update + router**

Alembic（revises `w9f0a1b2c3d7`）:

```python
"""issue_forms.enqueue_triage (E68)

Revision ID: x1a2b3c4d5e6
Revises: w9f0a1b2c3d7
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "x1a2b3c4d5e6"
down_revision: Union[str, None] = "w9f0a1b2c3d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("issue_forms")} if "issue_forms" in inspector.get_table_names() else set()
    if "enqueue_triage" not in cols:
        op.add_column(
            "issue_forms",
            sa.Column(
                "enqueue_triage",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("issue_forms")} if "issue_forms" in inspector.get_table_names() else set()
    if "enqueue_triage" in cols:
        op.drop_column("issue_forms", "enqueue_triage")
```

Model add after `create_customer_request`:

```python
    enqueue_triage: Mapped[bool] = mapped_column(
        Boolean, nullable=False, insert_default=False
    )
```

`serialize_form` add `"enqueueTriage": bool(row.enqueue_triage)`.

`create(...)` add `enqueue_triage: bool = False` and set on IssueForm.
`update(...)` add `enqueue_triage: bool | None = None` and patch when not None.

Router FormCreate: `enqueueTriage: bool = False`；FormUpdate: `enqueueTriage: Optional[bool] = None`；wire to service.

- [ ] **Step 4: Run → PASS** + commit

```bash
cd backend && python -m pytest tests/api/test_e68_form_triage_enqueue.py::test_e68_form_enqueue_triage_default_false_and_patch -v
git add backend/alembic/versions/2026_11_05_5000-x1a2b3c4d5e6_issue_forms_enqueue_triage.py \
  backend/opentask/models/issue_form/model.py \
  backend/opentask/services/issue_form/service.py \
  backend/opentask/api/forms/router.py \
  backend/tests/api/test_e68_form_triage_enqueue.py
git commit -m "feat(E68): issue_forms.enqueue_triage column + CRUD serialize"
```

---

### Task 3 — B：submit → TriageService.enqueue + CR 并存（TDD）

**Files:**
- Modify: `backend/opentask/services/issue_form/service.py` (`submit`)
- Modify: `backend/tests/api/test_e68_form_triage_enqueue.py`

**Interfaces:**
- submit return adds `triageEnqueued: bool`
- When `form.enqueue_triage`: after create (+ optional CR), call `TriageService(self.db).enqueue(workspace_id=..., issue_id=str(issue.id), actor_user_id=actor)` before final commit/refresh; response `triageEnqueued=True`
- Default false → `triageEnqueued=False`；issue.triage_status is null/None；not in Triage list

- [ ] **Step 1: 红测**

```python
@pytest.mark.asyncio
async def test_e68_submit_default_not_enqueued(test_client: AsyncClient):
    user = await _register(test_client, "e68_off")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "Off", "fields": DEFAULT_FIELDS},
    )
    token = created.json()["data"]["token"]
    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"title": "plain"}},
    )
    assert submitted.status_code == 200, submitted.text
    data = submitted.json()["data"]
    assert data.get("triageEnqueued") is False
    issue = await test_client.get(f"/api/issues/{data['issueId']}", headers=h)
    assert issue.status_code == 200, issue.text
    body = issue.json()["data"]
    assert body.get("triageStatus") in (None, "", "null")
    triage = await test_client.get("/api/triage", headers=h)
    assert triage.status_code == 200, triage.text
    ids = [r["id"] for r in triage.json()["data"]["rows"]]
    assert data["issueId"] not in ids


@pytest.mark.asyncio
async def test_e68_submit_enqueue_pending_and_list(test_client: AsyncClient):
    user = await _register(test_client, "e68_on")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "On", "fields": DEFAULT_FIELDS, "enqueueTriage": True},
    )
    token = created.json()["data"]["token"]
    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"title": "needs triage"}},
    )
    assert submitted.status_code == 200, submitted.text
    data = submitted.json()["data"]
    assert data.get("triageEnqueued") is True
    issue = await test_client.get(f"/api/issues/{data['issueId']}", headers=h)
    assert issue.json()["data"].get("triageStatus") == "pending"
    triage = await test_client.get("/api/triage", headers=h)
    ids = [r["id"] for r in triage.json()["data"]["rows"]]
    assert data["issueId"] in ids
    # accept clears
    acc = await test_client.post(f"/api/triage/{data['issueId']}/accept", headers=h)
    assert acc.status_code == 200, acc.text
    assert acc.json()["data"].get("triageStatus") in (None, "")


@pytest.mark.asyncio
async def test_e68_enqueue_with_customer_request(test_client: AsyncClient):
    user = await _register(test_client, "e68_cr")
    h = _auth(user["token"], user["workspaceId"])
    cust = await test_client.post(
        "/api/customers", headers=h, json={"name": f"C-{uuid.uuid4().hex[:6]}"}
    )
    assert cust.status_code == 200, cust.text
    cid = cust.json()["data"]["id"]
    fields = list(DEFAULT_FIELDS) + [
        {"key": "customer_id", "type": "customer_id", "label": "客户", "required": True}
    ]
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={
            "name": "Both",
            "fields": fields,
            "enqueueTriage": True,
            "createCustomerRequest": True,
        },
    )
    assert created.status_code == 200, created.text
    token = created.json()["data"]["token"]
    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"title": "both paths", "customer_id": cid}},
    )
    assert submitted.status_code == 200, submitted.text
    data = submitted.json()["data"]
    assert data.get("triageEnqueued") is True
    assert data.get("requestId")
    issue = await test_client.get(f"/api/issues/{data['issueId']}", headers=h)
    assert issue.json()["data"].get("triageStatus") == "pending"


@pytest.mark.asyncio
async def test_e68_enqueue_idempotent_already_pending(test_client: AsyncClient):
    """Calling enqueue twice (via TriageService) must not explode — covered by submit once + re-enqueue."""
    user = await _register(test_client, "e68_idemp")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "Idemp", "fields": DEFAULT_FIELDS, "enqueueTriage": True},
    )
    token = created.json()["data"]["token"]
    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"title": "once"}},
    )
    iid = submitted.json()["data"]["issueId"]
    again = await test_client.post(
        "/api/triage",
        headers=h,
        json={"issueId": iid},
    )
    assert again.status_code == 200, again.text
    assert again.json()["data"].get("triageStatus") == "pending"
```

- [ ] **Step 2: Run → FAIL**（triageEnqueued missing / not pending）

- [ ] **Step 3: 最小实现 in submit**（after CR block, before final commit）:

```python
        triage_enqueued = False
        if form.enqueue_triage:
            from opentask.services.triage.service import TriageService

            await TriageService(self.db).enqueue(
                workspace_id=form.workspace_id,
                issue_id=str(issue.id),
                actor_user_id=actor,
            )
            triage_enqueued = True

        await self.db.commit()
        await self.db.refresh(issue)

        return {
            "issueId": str(issue.id),
            "issueCode": issue.issue_code,
            "requestId": request_id,
            "title": issue.title,
            "triageEnqueued": triage_enqueued,
        }
```

Note: `TriageService.enqueue` already commits; if called, the later `commit` is harmless. Prefer calling enqueue **after** CR create and keep a final refresh. If enqueue commits mid-flight, CR must be committed first — current CR path does not commit until end; so either:
1. commit once before enqueue, or
2. set `issue.triage_status = "pending"` inline without nested commit.

**Preferred (Q2a reuse):** call `TriageService.enqueue` which commits (matches create_and_enqueue pattern). Ensure CR `create` has flushed/committed: `CustomerRequestService.create` typically commits — verify; if not, `await self.db.commit()` before enqueue.

Inspected: CR create may commit internally. IssueService.create_issue commits. Labels/custom may be pending. Safest:

```python
        await self.db.commit()
        await self.db.refresh(issue)

        triage_enqueued = False
        if form.enqueue_triage:
            from opentask.services.triage.service import TriageService

            await TriageService(self.db).enqueue(
                workspace_id=form.workspace_id,
                issue_id=str(issue.id),
                actor_user_id=actor,
            )
            triage_enqueued = True
            await self.db.refresh(issue)

        return {
            "issueId": str(issue.id),
            "issueCode": issue.issue_code,
            "requestId": request_id,
            "title": issue.title,
            "triageEnqueued": triage_enqueued,
        }
```

Also return `triageEnqueued: False` on default path (always include key).

- [ ] **Step 4: PASS + commit**

```bash
cd backend && python -m pytest tests/api/test_e68_form_triage_enqueue.py -v
git add backend/opentask/services/issue_form/service.py backend/tests/api/test_e68_form_triage_enqueue.py
git commit -m "feat(E68): form submit enqueues triage when flag on"
```

---

### Task 4 — C：FE 设置开关 + 成功文案 + vitest

**Files:**
- Modify: `frontend/src/service/api/forms.ts`
- Modify: `frontend/src/service/api/forms.test.ts`
- Modify: `frontend/src/views/settings/forms/index.vue`
- Modify: `frontend/src/views/f/[token].vue`

- [ ] **Step 1: 红测** — add to forms.test.ts

```typescript
import {
  buildPublicUrl,
  ensureTitleField,
  FORM_FIELD_TYPES,
  formSubmitSuccessCopy
} from './forms';

describe('formSubmitSuccessCopy', () => {
  it('distinguishes triage enqueued vs plain create', () => {
    expect(formSubmitSuccessCopy({ issueCode: 'OT-1', title: 'A', triageEnqueued: true })).toContain(
      '受理队列'
    );
    expect(formSubmitSuccessCopy({ issueCode: 'OT-1', title: 'A', triageEnqueued: false })).toContain(
      'OT-1'
    );
    expect(formSubmitSuccessCopy({ issueCode: 'OT-1', title: 'A', triageEnqueued: false })).not.toContain(
      '受理队列'
    );
  });
});
```

- [ ] **Step 2: FAIL → implement**

```typescript
export function formSubmitSuccessCopy(input: {
  issueCode: string;
  title: string;
  triageEnqueued?: boolean | null;
}): string {
  if (input.triageEnqueued) {
    return `已进入受理队列，请等待处理（${input.issueCode} · ${input.title}）`;
  }
  return `已创建 ${input.issueCode} · ${input.title}`;
}
```

Extend `IssueFormRow` + create/update bodies with `enqueueTriage?: boolean`.
Extend `submitPublicForm` return with `triageEnqueued?: boolean`.

Settings page: add `enqueueTriage: false` to reactive form; NSwitch labeled「提交后进入 Triage」; pass on create; add table column toggle calling `fetchUpdateForm(id, { enqueueTriage: v })`.

Public page: store `triageEnqueued` on success; render `formSubmitSuccessCopy(success)`.

- [ ] **Step 3: vitest PASS + commit**

```bash
cd frontend && pnpm exec vitest run src/service/api/forms.test.ts
git add frontend/src/service/api/forms.ts frontend/src/service/api/forms.test.ts \
  frontend/src/views/settings/forms/index.vue frontend/src/views/f/[token].vue
git commit -m "feat(E68): FE enqueueTriage toggle + success copy"
```

---

### Task 5 — D：CLI 1.52.0 + `--enqueue-triage`

**Files:**
- Modify: all CLI version pins `1.51.0` → `1.52.0`（`__init__.py`, `opentask_cli.py`, `setup.py`, tests）
- Modify: `agent-harness/opentask-cli/opentask/core/form.py`
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`
- Create: `agent-harness/opentask-cli/tests/test_e68_form_triage.py`

- [ ] **Step 1: 红测**

```python
"""E68 CLI: form --enqueue-triage + version 1.52.0."""
from click.testing import CliRunner

from opentask import __version__
from opentask.opentask_cli import VERSION, cli


def test_version_1520():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.52.0" in result.output
    assert VERSION == "1.52.0"
    assert __version__ == "1.52.0"


def test_form_create_help_enqueue_triage():
    runner = CliRunner()
    result = runner.invoke(cli, ["form", "create", "--help"])
    assert result.exit_code == 0
    assert "--enqueue-triage" in result.output


def test_form_update_help_enqueue_triage():
    runner = CliRunner()
    result = runner.invoke(cli, ["form", "update", "--help"])
    assert result.exit_code == 0
    assert "--enqueue-triage" in result.output
```

- [ ] **Step 2: bump pins** — `rg -l '1\.51\.0' agent-harness/opentask-cli | xargs sed -i 's/1\.51\.0/1.52.0/g'`（仅 CLI 树；不动邻面主逻辑）

- [ ] **Step 3: form flags**

`form create`: add `@click.option("--enqueue-triage/--no-enqueue-triage", default=False)`；pass to client.
`form update`: `@click.option("--enqueue-triage", type=click.BOOL, default=None)` → body `enqueueTriage`.
`form list`: add column `EnqueueTriage` yes/no.
`api_client.create_form`: add `enqueue_triage: bool = False` → `"enqueueTriage": enqueue_triage`.

- [ ] **Step 4: PASS + commit**

```bash
cd agent-harness/opentask-cli && python -m pytest tests/test_e68_form_triage.py tests/test_e31_forms.py -v
git add agent-harness/opentask-cli
git commit -m "feat(E68): CLI 1.52.0 form --enqueue-triage"
```

---

### Task 6 — E：no-emit / 邻面 spy + FE build + acceptance + 门禁

**Files:**
- Modify: `backend/tests/api/test_e68_form_triage_enqueue.py` — webhook spy
- Modify: acceptance with tip SHA + counts
- Possibly restore elegant-router `f`/`r` after build

- [ ] **Step 1: spy test**

```python
@pytest.mark.asyncio
async def test_e68_enqueue_no_new_webhook_fire(test_client: AsyncClient):
    user = await _register(test_client, "e68_spy")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "Spy", "fields": DEFAULT_FIELDS, "enqueueTriage": True},
    )
    token = created.json()["data"]["token"]
    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fw:
        submitted = await test_client.post(
            f"/api/public/forms/{token}/submit",
            json={"values": {"title": "spy"}},
        )
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["data"]["triageEnqueued"] is True
        # Q5a: enqueue itself must not fire new outbound webhooks
        fw.assert_not_called()
```

Note: if `create_issue` fires `issue.created` via same symbol, spy may see calls — design says 不新增事件、入队不 fire 新出站. Assert no call with event name containing `triage`, or patch only around enqueue by unit-testing enqueue path. Prefer: record call args and assert no event in `{"triage.enqueued", "triage.created"}`. If create_issue fires issue.created, filter:

```python
        triage_events = [
            c for c in fw.call_args_list
            if any("triage" in str(a).lower() for a in c.args + tuple(c.kwargs.values()))
        ]
        assert triage_events == []
```

Also assert `advance_once` source unchanged (grep smoke in acceptance, not runtime).

- [ ] **Step 2: full gates**

```bash
cd backend && python -m pytest -q --tb=no 2>&1 | tee /tmp/e68-be.txt
cd agent-harness/opentask-cli && python -m pytest -q --tb=no 2>&1 | tee /tmp/e68-cli.txt
cd frontend && pnpm exec vitest run 2>&1 | tee /tmp/e68-fe.txt
cd frontend && pnpm run build 2>&1 | tee /tmp/e68-build.txt
# restore f/r if elegant-router dropped them from imports.ts / elegant-router.d.ts / routes
```

- [ ] **Step 3: fill acceptance + tip commit**

```bash
git add docs/superpowers/acceptances/2026-11-05-E68-acceptance.md backend/tests/api/test_e68_form_triage_enqueue.py
# + any f/r restores
git commit -m "docs(E68): acceptance + gate counts"
git rev-parse HEAD
git rev-parse --short HEAD
```

---

## Spec coverage self-check
| Spec | Task |
|------|------|
| A model/alembic/serialize | T2 |
| B submit enqueue + triageEnqueued + CR | T3 |
| C FE toggle + copy + vitest + f/r | T4 + T6 |
| D CLI 1.52.0 + flag | T5 |
| E tenant/no-emit/邻面/no deep-link | T3 tenant via existing + T6 spy |
| Q1a–Q6a / D1–D7 | 全任务遵守 |
| 门禁 + acceptance | T6 |

## Placeholder scan
无 TBD / TODO / 「similar to」空洞步骤。

