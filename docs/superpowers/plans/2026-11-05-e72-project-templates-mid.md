# E72 Plan：Project 模板 mid — project_templates · CLI 1.56.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`91bea39`（全文 `91bea3924df93461dad0da01736a1b0b97630111`）· 分支 `sprint/E72-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e72-project-templates-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E73**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Workspace 可 CRUD Project 模板；apply / `POST /projects`+`template_id` 建 Project 并按 `targetOffsetDays` 种子 Milestones；from-project 另存为（仅里程碑骨架）；FE 设置页 + 创建选模板 + 另存；CLI **1.56.0**；不复制 Issues/附件/成员；无新 webhook 名；formula no-emit；不改 E63–E71 邻面主表面。

**Architecture:** 表 `project_templates`（对齐 `issue_templates`）；payload `{description?, milestones:[{name, description?, position?, targetOffsetDays?}]}`；`ProjectTemplateService` 负责 validate/CRUD/apply/from_project；apply 调既有 Project+Milestone 创建路径；API camelCase；CLI pins 全钉 1.56.0。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E73；中文 docs；CLI **1.56.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；无 Activity Push；无门户/甘特/多指派再开；不复制 Issues/附件/成员/watchers/health 历史
- 不改 E63–E71 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- Q5a：不新增 webhook 事件名
- Q3a：milestones ≤ **30**；跨租户 404；viewer 只读；member+ 写
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/models/project_template/` | ORM `ProjectTemplate` |
| `backend/alembic/versions/2026_11_05_5200-z3c4d5e6f7a8_project_templates.py` | alembic |
| `backend/opentask/services/project_template/service.py` | validate / CRUD / apply / from_project |
| `backend/opentask/api/project_templates/router.py` | REST |
| `backend/opentask/models/requirement/schema.py` | `ProjectCreate.template_id` (+ optional `starts_at`) |
| `backend/opentask/api/project/router.py` | create 带 template_id → apply |
| `backend/opentask/app.py` + `models/__init__.py` | register |
| `backend/tests/unit/test_e72_project_template_payload.py` | payload validate TDD |
| `backend/tests/api/test_e72_project_templates.py` | API TDD |
| `frontend/src/utils/projectTemplate.ts` (+test) | offset→date / payload validate |
| `frontend/src/service/api/project-templates.ts` | API client |
| `frontend/src/views/workspace/project-templates/index.vue` | 设置页 |
| `frontend/src/views/workflow/projects/index.vue` | 创建对话框选模板 |
| `frontend/src/views/workflow/project-detail/index.vue` | 另存为模板 |
| `frontend/src/router/**` + locales | route `workspace_project-templates`；守 f+r |
| `agent-harness/opentask-cli/**` | 1.56.0 + project-template + create --template-id |
| `docs/superpowers/acceptances/2026-11-05-E72-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E72-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e72-project-templates-mid.md \
  docs/superpowers/acceptances/2026-11-05-E72-acceptance.md
git commit -m "docs(E72): plan + acceptance skeleton"
```

---

### Task 2 — A：payload validate helper（TDD）

**Files:**
- Create: `backend/opentask/services/project_template/__init__.py`
- Create: `backend/opentask/services/project_template/service.py`（先纯函数）
- Create: `backend/tests/unit/test_e72_project_template_payload.py`

**Interfaces:**
- `MAX_PROJECT_TEMPLATE_MILESTONES = 30`
- `validate_project_template_payload(payload: dict | None) -> dict`
  - 允许 `None` → `{"milestones": []}`
  - `milestones` 必须 list；每项 `name` 非空 str；`targetOffsetDays` 若有则 int；`position` 默认 index
  - `len(milestones) > 30` → `HTTPException(400)`
  - 返回规范化 `{description?, milestones:[{name, description?, position, targetOffsetDays?}]}`
- `compute_milestone_target_date(*, base_date: date, offset_days: int | None) -> datetime | None`
  - offset None → None；else `datetime.combine(base_date + timedelta(days=offset), time.min)`

- [ ] **Step 1: 红测**

```python
"""E72: project template payload validate + offset→date."""
from __future__ import annotations

from datetime import date, datetime

import pytest
from fastapi import HTTPException

from opentask.services.project_template.service import (
    MAX_PROJECT_TEMPLATE_MILESTONES,
    compute_milestone_target_date,
    validate_project_template_payload,
)


def test_validate_normalizes_and_caps():
    out = validate_project_template_payload(
        {
            "description": "Ship",
            "milestones": [
                {"name": "Kickoff", "targetOffsetDays": 0},
                {"name": "Beta", "targetOffsetDays": 30},
            ],
        }
    )
    assert out["description"] == "Ship"
    assert out["milestones"][0]["position"] == 0
    assert out["milestones"][1]["targetOffsetDays"] == 30


def test_validate_rejects_over_30():
    payload = {"milestones": [{"name": f"M{i}"} for i in range(31)]}
    with pytest.raises(HTTPException) as ei:
        validate_project_template_payload(payload)
    assert ei.value.status_code == 400


def test_validate_rejects_empty_name():
    with pytest.raises(HTTPException) as ei:
        validate_project_template_payload({"milestones": [{"name": "  "}]})
    assert ei.value.status_code == 400


def test_offset_date():
    assert compute_milestone_target_date(base_date=date(2026, 1, 1), offset_days=None) is None
    dt = compute_milestone_target_date(base_date=date(2026, 1, 1), offset_days=30)
    assert dt == datetime(2026, 1, 31, 0, 0, 0)


def test_max_constant():
    assert MAX_PROJECT_TEMPLATE_MILESTONES == 30
```

- [ ] **Step 2: Run → FAIL**（module missing）

```bash
cd backend && python -m pytest tests/unit/test_e72_project_template_payload.py -v
```

- [ ] **Step 3: 最小实现**

```python
# backend/opentask/services/project_template/__init__.py
from opentask.services.project_template.service import (
    MAX_PROJECT_TEMPLATE_MILESTONES,
    compute_milestone_target_date,
    validate_project_template_payload,
)

__all__ = [
    "MAX_PROJECT_TEMPLATE_MILESTONES",
    "compute_milestone_target_date",
    "validate_project_template_payload",
]
```

```python
# backend/opentask/services/project_template/service.py (pure helpers first)
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status

MAX_PROJECT_TEMPLATE_MILESTONES = 30


def compute_milestone_target_date(
    *, base_date: date, offset_days: int | None
) -> datetime | None:
    if offset_days is None:
        return None
    return datetime.combine(base_date + timedelta(days=int(offset_days)), time.min)


def validate_project_template_payload(payload: dict | None) -> dict[str, Any]:
    raw = dict(payload or {})
    milestones_in = raw.get("milestones")
    if milestones_in is None:
        milestones_in = []
    if not isinstance(milestones_in, list):
        raise HTTPException(status_code=400, detail="milestones must be a list")
    if len(milestones_in) > MAX_PROJECT_TEMPLATE_MILESTONES:
        raise HTTPException(
            status_code=400,
            detail=f"milestones max {MAX_PROJECT_TEMPLATE_MILESTONES}",
        )
    milestones: list[dict[str, Any]] = []
    for i, item in enumerate(milestones_in):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="milestone must be object")
        name = str(item.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="milestone name required")
        entry: dict[str, Any] = {"name": name[:255]}
        if item.get("description") is not None:
            entry["description"] = item.get("description")
        pos = item.get("position")
        entry["position"] = int(pos) if pos is not None else i
        if "targetOffsetDays" in item and item.get("targetOffsetDays") is not None:
            try:
                entry["targetOffsetDays"] = int(item["targetOffsetDays"])
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=400, detail="targetOffsetDays must be int"
                ) from exc
        else:
            entry["targetOffsetDays"] = None
        milestones.append(entry)
    out: dict[str, Any] = {"milestones": milestones}
    if raw.get("description") is not None:
        out["description"] = raw.get("description")
    return out
```

- [ ] **Step 4: Run → PASS**

- [ ] **Step 5: Commit** `test(E72): payload validate + offset date helpers`

---

### Task 3 — A：model + alembic

**Files:**
- Create: `backend/opentask/models/project_template/__init__.py`
- Create: `backend/opentask/models/project_template/model.py`
- Create: `backend/alembic/versions/2026_11_05_5200-z3c4d5e6f7a8_project_templates.py`
- Modify: `backend/opentask/models/__init__.py`（import + `__all__`）

**Interfaces:**
- `ProjectTemplate` 字段对齐 design §A（同构 IssueTemplate）
- revision `z3c4d5e6f7a8`；`down_revision = "y2b3c4d5e6f7"`

- [ ] **Step 1:** 写 model（镜像 IssueTemplate；表名 `project_templates`；约束 `uq_project_templates_ws_name` / `uq_project_templates_ws_seed`）
- [ ] **Step 2:** 写 alembic（idempotent create_table + indexes）
- [ ] **Step 3:** register in `models/__init__.py`
- [ ] **Step 4: Commit** `feat(E72): project_templates model + alembic`

---

### Task 4 — A/B：Service CRUD + apply + from_project（TDD via API）

**Files:**
- Expand: `backend/opentask/services/project_template/service.py`
- Create: `backend/opentask/api/project_templates/__init__.py` + `router.py`
- Modify: `backend/opentask/app.py`（include_router）
- Modify: `backend/opentask/models/requirement/schema.py` — `ProjectCreate.template_id: str | None = None`；`starts_at: datetime | None = None`
- Modify: `backend/opentask/api/project/router.py` — create 若 `template_id` 则走 apply
- Create: `backend/tests/api/test_e72_project_templates.py`

**Service methods:**
- `require_writer(member)`（同 issue templates）
- `serialize_project_template(row) -> dict`（camelCase）
- `list / get / create / update / delete`
- `apply(*, workspace_id, template_id, name, description=None, starts_at=None, user_id, dept_id=None) -> dict`
  - 建 Project（name 必填；description = body or payload.description or template.description）
  - 若 starts_at 传入则写 Project.starts_at
  - base_date = starts_at.date() if starts_at else utcnow().date()
  - 每个 milestone：`MilestoneService`-style 直插；`target_date = compute_milestone_target_date(...)`
  - **不**建 Issues；返回 `{project, milestones: [...]}`（serialize）
- `from_project(*, workspace_id, project_id, name, description=None, icon=None, user_id) -> ProjectTemplate`
  - 抽 milestones；base = project.starts_at.date() or first milestone target.date() or today
  - `targetOffsetDays = (m.target_date.date() - base).days` if target else None
  - source=`custom`；**不**复制 Issues

**API:**
- `GET/POST /api/project-templates`
- `GET /api/project-templates/{id}`（可选；CLI show 用）
- `PATCH/DELETE /api/project-templates/{id}`
- `POST /api/project-templates/{id}/apply` body `{name, description?, startsAt?}`
- `POST /api/project-templates/from-project/{project_id}` body `{name, description?, icon?}`
- 列表 `{rows, total}`；跨 WS 404；viewer POST→403

**Project create:**
```python
# ProjectCreate
class ProjectCreate(ProjectBase):
    template_id: str | None = None
    starts_at: datetime | None = None
```
若 `dto.template_id` 且有 workspace → `ProjectTemplateService.apply(...)`；否则既有 create。

- [ ] **Step 1: 红测 API**（摘录）

```python
"""E72: project_templates CRUD + apply + from-project."""
from __future__ import annotations
import uuid
from datetime import date, datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from opentask.models.issue.model import Issue
from opentask.models.milestone.model import Milestone

async def _register(client, prefix="pt"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post("/api/auth/register", json={"userName": uname, "password": "Passw0rd!", "name": uname})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {"token": data["token"], "userId": data["userId"], "workspaceId": data["defaultWorkspaceId"]}

def _auth(token, workspace_id=None):
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-Id"] = workspace_id
    return h

@pytest.mark.asyncio
async def test_crud_and_name_conflict(test_client: AsyncClient):
    user = await _register(test_client, "pt_crud")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post("/api/project-templates", headers=h, json={
        "name": "Launch Kit",
        "description": "std",
        "payload": {"milestones": [{"name": "Kickoff", "targetOffsetDays": 0}, {"name": "GA", "targetOffsetDays": 45}]},
    })
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["name"] == "Launch Kit"
    assert len(row["payload"]["milestones"]) == 2
    dup = await test_client.post("/api/project-templates", headers=h, json={"name": "Launch Kit", "payload": {"milestones": []}})
    assert dup.status_code == 409
    listed = await test_client.get("/api/project-templates", headers=h)
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] >= 1

@pytest.mark.asyncio
async def test_apply_seeds_milestones_zero_issues(test_client: AsyncClient, db_session):
    user = await _register(test_client, "pt_apply")
    h = _auth(user["token"], user["workspaceId"])
    tpl = (await test_client.post("/api/project-templates", headers=h, json={
        "name": "Two Mile",
        "payload": {"description": "from tpl", "milestones": [
            {"name": "Kickoff", "targetOffsetDays": 0},
            {"name": "Beta", "targetOffsetDays": 30},
        ]},
    })).json()["data"]
    starts = "2026-03-01T00:00:00"
    applied = await test_client.post(f"/api/project-templates/{tpl['id']}/apply", headers=h, json={
        "name": "Proj From Tpl", "startsAt": starts,
    })
    assert applied.status_code == 200, applied.text
    data = applied.json()["data"]
    assert data["project"]["name"] == "Proj From Tpl"
    miles = data["milestones"]
    assert len(miles) == 2
    d0 = datetime.fromisoformat(str(miles[0]["target_date"]).replace("Z", "")).date()
    d1 = datetime.fromisoformat(str(miles[1]["target_date"]).replace("Z", "")).date()
    assert (d1 - d0).days == 30
    # via create + template_id
    created = await test_client.post("/api/projects", headers=h, json={
        "name": "Via Create", "template_id": tpl["id"], "starts_at": starts,
    })
    assert created.status_code == 200, created.text
    # Issues count for new project stays 0
    pid = data["project"]["id"]
    count = (await db_session.execute(select(func.count()).select_from(Issue).where(Issue.project_id == pid))).scalar()
    assert count == 0

@pytest.mark.asyncio
async def test_milestones_31_rejected(test_client: AsyncClient):
    user = await _register(test_client, "pt_cap")
    h = _auth(user["token"], user["workspaceId"])
    resp = await test_client.post("/api/project-templates", headers=h, json={
        "name": "Too Many",
        "payload": {"milestones": [{"name": f"M{i}"} for i in range(31)]},
    })
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_from_project_roundtrip(test_client: AsyncClient):
    user = await _register(test_client, "pt_fp")
    h = _auth(user["token"], user["workspaceId"])
    proj = (await test_client.post("/api/projects", headers=h, json={"name": "Src", "description": "d"})).json()["data"]
    await test_client.put(f"/api/projects/{proj['id']}", headers=h, json={"starts_at": "2026-01-01T00:00:00"})
    await test_client.post(f"/api/projects/{proj['id']}/milestones", headers=h, json={"name": "A", "target_date": "2026-01-01T00:00:00", "position": 0})
    await test_client.post(f"/api/projects/{proj['id']}/milestones", headers=h, json={"name": "B", "target_date": "2026-01-31T00:00:00", "position": 1})
    await test_client.post(f"/api/projects/{proj['id']}/milestones", headers=h, json={"name": "C", "position": 2})
    saved = await test_client.post(f"/api/project-templates/from-project/{proj['id']}", headers=h, json={"name": "From Src"})
    assert saved.status_code == 200, saved.text
    payload = saved.json()["data"]["payload"]
    assert len(payload["milestones"]) == 3
    assert payload["milestones"][1]["targetOffsetDays"] == 30

@pytest.mark.asyncio
async def test_cross_ws_404_and_viewer_403(test_client: AsyncClient):
    owner = await _register(test_client, "pt_o")
    other = await _register(test_client, "pt_x")
    viewer = await _register(test_client, "pt_v")
    # add viewer to owner ws
    await test_client.post(f"/api/workspaces/{owner['workspaceId']}/members", headers=_auth(owner["token"]), json={"userId": viewer["userId"], "role": "viewer"})
    h = _auth(owner["token"], owner["workspaceId"])
    tpl = (await test_client.post("/api/project-templates", headers=h, json={"name": "Priv", "payload": {"milestones": []}})).json()["data"]
    cross = await test_client.get(f"/api/project-templates/{tpl['id']}", headers=_auth(other["token"], other["workspaceId"]))
    assert cross.status_code == 404
    denied = await test_client.post("/api/project-templates", headers=_auth(viewer["token"], owner["workspaceId"]), json={"name": "Nope", "payload": {"milestones": []}})
    assert denied.status_code == 403
```

（实现时按实际 fixture 名 `test_client`/`db_session` 对齐 E71 测试；若无 db_session 则用 API list milestones + issues 断言。）

- [ ] **Step 2: Run → FAIL**
- [ ] **Step 3: 实现 service + router + ProjectCreate.template_id + create hook**
- [ ] **Step 4: Run → PASS**
- [ ] **Step 5: Commit** `feat(E72): project-templates API CRUD/apply/from-project`

---

### Task 5 — C：FE utils + settings + create picker + save-as

**Files:**
- Create: `frontend/src/utils/projectTemplate.ts`
- Create: `frontend/src/utils/projectTemplate.test.ts`
- Create: `frontend/src/service/api/project-templates.ts`
- Create: `frontend/src/views/workspace/project-templates/index.vue`
- Modify: routes (`routes/index.ts`, `elegant/routes.ts`, `elegant/imports.ts`, `elegant/transform.ts`, `typings/elegant-router.d.ts`)
- Modify: locales zh-cn / en-us
- Modify: `frontend/src/views/workflow/projects/index.vue`（模板下拉 + 预览）
- Modify: `frontend/src/views/workflow/project-detail/index.vue`（另存为）
- Modify: `frontend/src/typings/api/project.d.ts` — `CreateProject.template_id?` / `starts_at?`
- Modify: `frontend/src/service/api/index.ts` export
- Optional: command-palette nav entry

**Utils:**
```typescript
export const MAX_PROJECT_TEMPLATE_MILESTONES = 30;

export function addDaysIso(baseIsoDate: string, offsetDays: number | null | undefined): string | null {
  if (offsetDays === null || offsetDays === undefined) return null;
  const d = new Date(`${baseIsoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export function validateMilestonePayload(milestones: { name?: string }[]): string | null {
  if (milestones.length > MAX_PROJECT_TEMPLATE_MILESTONES) return `max ${MAX_PROJECT_TEMPLATE_MILESTONES} milestones`;
  for (const m of milestones) {
    if (!String(m.name || '').trim()) return 'milestone name required';
  }
  return null;
}
```

- [ ] **Step 1: 红测 vitest** `projectTemplate.test.ts`
- [ ] **Step 2: 实现 utils + 设置页 + 创建选模板 + 另存**
- [ ] **Step 3: routes/i18n；守 f+r（build 后检查并还原）**
- [ ] **Step 4: Commit** `feat(E72): FE project-templates settings + picker + save-as`

---

### Task 6 — D：CLI 1.56.0

**Files:**
- Create: `agent-harness/opentask-cli/opentask/core/project_template.py`
- Modify: `opentask_cli.py`（add_command + VERSION）
- Modify: `opentask/core/project.py`（`--template-id` / `--starts-at`）
- Modify: `opentask/utils/api_client.py`（methods）
- Modify: VERSION / pyproject.toml / setup.py / `opentask/__init__.py` → **1.56.0**
- Create: `agent-harness/opentask-cli/tests/test_e72_project_templates.py`

**Commands:**
- `project-template list|show|create|update|delete`
- `project-template apply --id … --name … [--description] [--starts-at]`
- `project-template from-project --project-id … --name …`
- `project create --template-id …`

- [ ] **Step 1: 红测 version pins + help**
- [ ] **Step 2: 实现 + pins**
- [ ] **Step 3: PASS**
- [ ] **Step 4: Commit** `feat(E72): CLI 1.56.0 project-template + create --template-id`

---

### Task 7 — Verify + acceptance

- [ ] BE full suite + directed E72
- [ ] CLI full suite；确认 VERSION 文件 = 1.56.0
- [ ] FE vitest + `pnpm run build`；还原 f+r 若被 elegant-router 丢掉
- [ ] 填 acceptance tip SHA + 门禁数
- [ ] Commit tip：`docs(E72): acceptance — project templates mid local-complete`
- [ ] **STOP**：不 push / 不开 PR / 不自开 E73

## Spec coverage checklist
- [x] Q1a payload shape
- [x] Q2a POST /projects template_id + apply endpoint
- [x] Q3a max 30
- [x] Q4a from-project；无强制 builtin
- [x] Q5a 无新 webhook 名
- [x] Q6a CLI 1.56.0 全 pins
- [x] 不复制 Issues
- [x] 跨 WS 404 / viewer 403
- [x] FE 设置 + 创建选 + 另存
- [x] formula no-emit / 邻面不动
