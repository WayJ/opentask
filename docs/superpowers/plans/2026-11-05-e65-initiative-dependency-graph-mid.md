# E65 Plan：Initiative 依赖图 mid — blocks/blocked_by/relates_to · CLI 1.49.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`c3c0b25`（全文 `c3c0b25424732a5aaa7959f5c39939f693d17331`）· 分支 `sprint/E65-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e65-initiative-dependency-graph-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E66**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** Workspace writer+ 可在同 WS 内为 Initiative 建立/删除 blocks / is_blocked_by / relates_to；viewer+ 可读；详情默认 counts；列表 opt-in relationCounts；禁自环；blocks 有向环检；FE 详情「依赖」折叠区；CLI **1.49.0**；无甘特/Push；不改 E57–E64 邻面；formula no-emit。

**Architecture:** 独立表 `initiative_relations`（勿混 `issue_relations`）；语义对齐 E20 子集；存调用方字面 type（Q2a），GET 双向展开；环检仅 directed blocks 链（is_blocked_by 规范化为反向 blocks 边参与图）；API 挂 `/api/initiatives/{id}/relations`；FE 轻量列表；CLI relations list/add/remove。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E66；中文 docs；CLI **1.49.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；不改 E64 假日包 / E63 公开门户 / E57 告警 / E60–E62 Search / E61 Insights 主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- 独立表 `initiative_relations`；禁止复用 `issue_relations`
- Q5a：不新增 webhook 事件名、本轮不 fire 新出站
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/models/initiative/model.py` | `InitiativeRelation` + `INITIATIVE_RELATION_TYPES` |
| `backend/opentask/models/initiative/__init__.py` | export |
| `backend/opentask/models/__init__.py` | register import |
| `backend/alembic/versions/2026_11_05_4900-w9f0a1b2c3d7_initiative_relations.py` | migration |
| `backend/opentask/services/initiative/service.py` | relations CRUD + cycle + counts |
| `backend/opentask/api/initiatives/router.py` | GET/POST/DELETE relations；list/detail counts |
| `backend/tests/api/test_e65_initiative_relations.py` | API TDD |
| `frontend/src/utils/initiativeRelations.ts` | flatten / direction labels |
| `frontend/src/utils/initiativeRelations.test.ts` | vitest |
| `frontend/src/service/api/initiatives.ts` | relation API + types |
| `frontend/src/views/initiatives/detail/index.vue` | 「依赖」折叠区 |
| `frontend/src/views/initiatives/index.vue` | optional count badges |
| `agent-harness/opentask-cli/**` | 1.49.0 + relations cmds |
| `docs/superpowers/acceptances/2026-11-05-E65-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E65-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e65-initiative-dependency-graph-mid.md \
  docs/superpowers/acceptances/2026-11-05-E65-acceptance.md
git commit -m "docs(E65): plan + acceptance skeleton"
```

---

### Task 2 — A：model + alembic `initiative_relations`（TDD）

**Files:**
- Modify: `backend/opentask/models/initiative/model.py`
- Modify: `backend/opentask/models/initiative/__init__.py`
- Modify: `backend/opentask/models/__init__.py`（import InitiativeRelation）
- Create: `backend/alembic/versions/2026_11_05_4900-w9f0a1b2c3d7_initiative_relations.py`
- Create: `backend/tests/api/test_e65_initiative_relations.py`（先写表可导入/CRUD 红测）

**Interfaces:**
- `INITIATIVE_RELATION_TYPES = ("blocks", "is_blocked_by", "relates_to")`
- `class InitiativeRelation(DBModel)`：`id:str(36)`, `workspace_id`, `source_initiative_id`, `target_initiative_id`, `relation_type:str(32)`, `created_by`, `created_at`
- Unique `(source_initiative_id, target_initiative_id, relation_type)` name `uq_initiative_relations_src_tgt_type`
- Indexes: `(workspace_id, source_initiative_id)`, `(workspace_id, target_initiative_id)`
- FK → `initiatives.id` CASCADE；`workspaces.id` CASCADE
- alembic rev `w9f0a1b2c3d7` · down_revision `v8e9f0a1b2c6`

- [ ] **Step 1: 红测** — `test_e65_model_constants_and_tablename`

```python
"""E65: Initiative relations mid (blocks / is_blocked_by / relates_to)."""
from __future__ import annotations
import uuid
import pytest
from httpx import AsyncClient
from opentask.models.initiative.model import INITIATIVE_RELATION_TYPES, InitiativeRelation

def test_e65_relation_types_q1a():
    assert INITIATIVE_RELATION_TYPES == ("blocks", "is_blocked_by", "relates_to")
    assert InitiativeRelation.__tablename__ == "initiative_relations"
```

- [ ] **Step 2:** Run → FAIL（缺常量/类）
- [ ] **Step 3:** 加 model + alembic + exports
- [ ] **Step 4:** Run → PASS
- [ ] **Step 5:** Commit `feat(E65): initiative_relations model + alembic w9f0a1b2c3d7`

**Model 实现要点：**

```python
INITIATIVE_RELATION_TYPES = ("blocks", "is_blocked_by", "relates_to")

class InitiativeRelation(DBModel):
    __tablename__ = "initiative_relations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    source_initiative_id: Mapped[str] = mapped_column(String(36), ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False)
    target_initiative_id: Mapped[str] = mapped_column(String(36), ForeignKey("initiatives.id", ondelete="CASCADE"), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, insert_default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("source_initiative_id", "target_initiative_id", "relation_type", name="uq_initiative_relations_src_tgt_type"),
        Index("idx_initiative_relations_ws_source", "workspace_id", "source_initiative_id"),
        Index("idx_initiative_relations_ws_target", "workspace_id", "target_initiative_id"),
    )
```

---

### Task 3 — B：API CRUD + 自环/跨租户/环检（TDD）

**Files:**
- Modify: `backend/opentask/services/initiative/service.py`
- Modify: `backend/opentask/api/initiatives/router.py`
- Extend: `backend/tests/api/test_e65_initiative_relations.py`

**Interfaces:**
- `GET /api/initiatives/{id}/relations` → `{ items: [{ id, type, direction, initiative: { id, name, status } }] }`
  - `direction`: `"outgoing"` if source==id else `"incoming"`
  - `type`: stored literal（Q2a）
- `POST /api/initiatives/{id}/relations` body `{ targetInitiativeId, type }` → created item（同 GET shape，direction=outgoing）
- `DELETE /api/initiatives/{id}/relations/{relationId}` → `{ id }`
- writer+ 写；viewer 读 OK / 写 403
- 自环 → 400；target 跨 WS / 不存在 → 404；非法 type → 400
- 环检（Q4a）：将 `blocks` 视为 source→target 有向边；`is_blocked_by` 视为 target→source；DFS/BFS depth cap 32；成环 → 400；`relates_to` 跳过
- 重复同 (src,tgt,type) → 409

**Service 方法：**
- `list_relations(workspace_id, initiative_id) -> list[dict]`
- `add_relation(workspace_id, initiative_id, target_initiative_id, relation_type, user_id) -> dict`
- `remove_relation(workspace_id, initiative_id, relation_id) -> None`
- `relation_counts(workspace_id, initiative_ids: list[str]) -> dict[str, dict]`
- `_would_create_blocks_cycle(...) -> bool`

Counts 语义（与双向展开一致）：
- `blocksCount` = outgoing `blocks` + incoming `is_blocked_by`
- `blockedByCount` = outgoing `is_blocked_by` + incoming `blocks`
- `relatesToCount` = outgoing+incoming `relates_to`（可选，详情可带）

- [ ] **Step 1: 红测**（关键用例）

```python
async def _register(client, prefix="e65"):
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

async def _ini(client, h, name):
    r = await client.post("/api/initiatives", headers=h, json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()["data"]

@pytest.mark.asyncio
async def test_e65_add_blocks_list_both_ends(test_client: AsyncClient):
    user = await _register(test_client, "e65_b")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "IniA")
    b = await _ini(test_client, h, "IniB")
    post = await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=h,
        json={"targetInitiativeId": b["id"], "type": "blocks"},
    )
    assert post.status_code == 200, post.text
    item = post.json()["data"]
    assert item["type"] == "blocks" and item["direction"] == "outgoing"
    assert item["initiative"]["id"] == b["id"]

    la = await test_client.get(f"/api/initiatives/{a['id']}/relations", headers=h)
    assert la.status_code == 200
    items_a = la.json()["data"]["items"]
    assert any(i["initiative"]["id"] == b["id"] and i["type"] == "blocks" and i["direction"] == "outgoing" for i in items_a)

    lb = await test_client.get(f"/api/initiatives/{b['id']}/relations", headers=h)
    items_b = lb.json()["data"]["items"]
    assert any(i["initiative"]["id"] == a["id"] and i["type"] == "blocks" and i["direction"] == "incoming" for i in items_b)

@pytest.mark.asyncio
async def test_e65_self_loop_400(test_client: AsyncClient):
    user = await _register(test_client, "e65_sl")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "Self")
    r = await test_client.post(
        f"/api/initiatives/{a['id']}/relations", headers=h,
        json={"targetInitiativeId": a["id"], "type": "relates_to"},
    )
    assert r.status_code == 400

@pytest.mark.asyncio
async def test_e65_cross_ws_target_404(test_client: AsyncClient):
    u1 = await _register(test_client, "e65_c1")
    u2 = await _register(test_client, "e65_c2")
    h1 = _auth(u1["token"], u1["workspaceId"])
    h2 = _auth(u2["token"], u2["workspaceId"])
    a = await _ini(test_client, h1, "A")
    b = await _ini(test_client, h2, "B")
    r = await test_client.post(
        f"/api/initiatives/{a['id']}/relations", headers=h1,
        json={"targetInitiativeId": b["id"], "type": "blocks"},
    )
    assert r.status_code == 404

@pytest.mark.asyncio
async def test_e65_blocks_cycle_400(test_client: AsyncClient):
    user = await _register(test_client, "e65_cy")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "CA"); b = await _ini(test_client, h, "CB")
    r1 = await test_client.post(f"/api/initiatives/{a['id']}/relations", headers=h, json={"targetInitiativeId": b["id"], "type": "blocks"})
    assert r1.status_code == 200, r1.text
    r2 = await test_client.post(f"/api/initiatives/{b['id']}/relations", headers=h, json={"targetInitiativeId": a["id"], "type": "blocks"})
    assert r2.status_code == 400, r2.text

@pytest.mark.asyncio
async def test_e65_relates_to_no_cycle_check(test_client: AsyncClient):
    user = await _register(test_client, "e65_rt")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "RA"); b = await _ini(test_client, h, "RB")
    assert (await test_client.post(f"/api/initiatives/{a['id']}/relations", headers=h, json={"targetInitiativeId": b["id"], "type": "relates_to"})).status_code == 200
    assert (await test_client.post(f"/api/initiatives/{b['id']}/relations", headers=h, json={"targetInitiativeId": a["id"], "type": "relates_to"})).status_code == 200

@pytest.mark.asyncio
async def test_e65_is_blocked_by_literal_store(test_client: AsyncClient):
    user = await _register(test_client, "e65_ibb")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "IA"); b = await _ini(test_client, h, "IB")
    post = await test_client.post(f"/api/initiatives/{a['id']}/relations", headers=h, json={"targetInitiativeId": b["id"], "type": "is_blocked_by"})
    assert post.status_code == 200, post.text
    assert post.json()["data"]["type"] == "is_blocked_by"
    # cycle via is_blocked_by A←B means B blocks A; then B blocks A via blocks should cycle if A blocks B... 
    # A is_blocked_by B ≡ B blocks A. Adding B blocks A directly = duplicate edge direction; adding A blocks B = cycle.
    r = await test_client.post(f"/api/initiatives/{a['id']}/relations", headers=h, json={"targetInitiativeId": b["id"], "type": "blocks"})
    assert r.status_code == 400, r.text

@pytest.mark.asyncio
async def test_e65_viewer_write_403_delete_ok(test_client: AsyncClient):
    owner = await _register(test_client, "e65_ow")
    viewer = await _register(test_client, "e65_vw")
    await test_client.post(f"/api/workspaces/{owner['workspaceId']}/members", headers=_auth(owner["token"]), json={"userId": viewer["userId"], "role": "viewer"})
    oh = _auth(owner["token"], owner["workspaceId"])
    vh = _auth(viewer["token"], owner["workspaceId"])
    a = await _ini(test_client, oh, "VA"); b = await _ini(test_client, oh, "VB")
    post = await test_client.post(f"/api/initiatives/{a['id']}/relations", headers=oh, json={"targetInitiativeId": b["id"], "type": "relates_to"})
    rid = post.json()["data"]["id"]
    assert (await test_client.get(f"/api/initiatives/{a['id']}/relations", headers=vh)).status_code == 200
    assert (await test_client.post(f"/api/initiatives/{a['id']}/relations", headers=vh, json={"targetInitiativeId": b["id"], "type": "blocks"})).status_code == 403
    assert (await test_client.delete(f"/api/initiatives/{a['id']}/relations/{rid}", headers=vh)).status_code == 403
    assert (await test_client.delete(f"/api/initiatives/{a['id']}/relations/{rid}", headers=oh)).status_code == 200
```

- [ ] **Step 2:** Run → FAIL（404 routes）
- [ ] **Step 3:** 实现 service + router
- [ ] **Step 4:** Run → PASS
- [ ] **Step 5:** Commit `feat(E65): initiative relations API CRUD + cycle check`

---

### Task 4 — B 续：详情默认 counts + 列表 opt-in（TDD）

**Files:**
- Modify: `serialize_initiative` / `to_response` / list+get router
- Extend tests

**Interfaces:**
- GET detail 默认带 `blocksCount`, `blockedByCount`（及可选 `relatesToCount`）
- GET list 默认 **不**带；`?include=relationCounts` 时每行带 counts
- 无关系时 counts=0

```python
@pytest.mark.asyncio
async def test_e65_detail_counts_default_list_opt_in(test_client: AsyncClient):
    user = await _register(test_client, "e65_ct")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "CntA"); b = await _ini(test_client, h, "CntB")
    await test_client.post(f"/api/initiatives/{a['id']}/relations", headers=h, json={"targetInitiativeId": b["id"], "type": "blocks"})
    detail = await test_client.get(f"/api/initiatives/{a['id']}", headers=h)
    d = detail.json()["data"]
    assert d["blocksCount"] == 1 and d["blockedByCount"] == 0
    detail_b = (await test_client.get(f"/api/initiatives/{b['id']}", headers=h)).json()["data"]
    assert detail_b["blocksCount"] == 0 and detail_b["blockedByCount"] == 1
    listed = await test_client.get("/api/initiatives", headers=h)
    row_a = next(r for r in listed.json()["data"]["rows"] if r["id"] == a["id"])
    assert "blocksCount" not in row_a
    listed2 = await test_client.get("/api/initiatives?include=relationCounts", headers=h)
    row_a2 = next(r for r in listed2.json()["data"]["rows"] if r["id"] == a["id"])
    assert row_a2["blocksCount"] == 1
```

- [ ] Commit `feat(E65): initiative relationCounts on detail + list opt-in`

---

### Task 5 — C：FE 依赖区 + vitest

**Files:**
- Create: `frontend/src/utils/initiativeRelations.ts` + `.test.ts`
- Modify: `frontend/src/service/api/initiatives.ts`
- Modify: `frontend/src/views/initiatives/detail/index.vue`
- Modify: `frontend/src/views/initiatives/index.vue`（有 counts 时小徽章）

**Interfaces:**
```typescript
export type InitiativeRelationType = 'blocks' | 'is_blocked_by' | 'relates_to';
export type InitiativeRelationDirection = 'outgoing' | 'incoming';
export interface InitiativeRelationItem {
  id: string;
  type: InitiativeRelationType;
  direction: InitiativeRelationDirection;
  initiative: { id: string; name: string; status: string };
}
export function relationDirectionLabel(type: InitiativeRelationType, direction: InitiativeRelationDirection): string;
export function groupRelationItems(items: InitiativeRelationItem[]): { blocks: ...; blockedBy: ...; relatesTo: ... };
```

文案：
- blocks+outgoing → 「阻塞」
- blocks+incoming → 「被阻塞」（对方阻塞我）
- is_blocked_by+outgoing → 「被阻塞」
- is_blocked_by+incoming → 「阻塞」
- relates_to → 「相关」

详情：NCollapse/NCard「依赖」——列表 + 类型选择 + 目标 Initiative select + 添加 + 删除；**无**甘特/力导向。

- [ ] vitest PASS；`pnpm run build` ok
- [ ] Commit `feat(E65): FE initiative relations fold + vitest`

---

### Task 6 — D：CLI **1.49.0**

**Files:**
- Bump all `1.48.0` → `1.49.0` pins（VERSION / __init__ / opentask_cli / setup / pyproject / 全部历史 eXX version asserts）
- Modify: `opentask/core/initiative.py` — `relations` group list；`relation` group add/remove
- Modify: `opentask/utils/api_client.py` — list/add/remove initiative relations
- Create: `tests/test_e65_initiative_relations.py`

```python
"""E65 CLI: initiative relations + version 1.49.0."""
from click.testing import CliRunner
from opentask import __version__
from opentask.opentask_cli import VERSION, cli

def test_version_1_49_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.49.0" in result.output
    assert VERSION == "1.49.0" and __version__ == "1.49.0"

def test_initiative_relations_help():
    runner = CliRunner()
    assert "relations" in runner.invoke(cli, ["initiative", "--help"]).output
    assert "--target" in runner.invoke(cli, ["initiative", "relation", "add", "--help"]).output
    assert "--relation-id" in runner.invoke(cli, ["initiative", "relation", "remove", "--help"]).output
```

CLI 形状（Q6a）：
- `opentask initiative relations list <id> [--json]`
- `opentask initiative relation add <id> --target <id> --type blocks|is_blocked_by|relates_to [--json]`
- `opentask initiative relation remove <id> --relation-id <rid> [--json]`

- [ ] Commit `feat(E65): CLI 1.49.0 initiative relations`

---

### Task 7 — E：no-emit spy + acceptance + 门禁

**Files:**
- Extend API test：patch `opentask.services.workspace_webhook.service.fire_webhooks`（或项目内实际路径）在 add/remove 时 assert_not_called；确认无新事件名字符串入库
- 不触碰 holiday-packs / public status / search / insights 主表面
- Fill acceptance tip SHA + gate counts

```python
@pytest.mark.asyncio
async def test_e65_relation_mutate_no_webhook_fire(test_client: AsyncClient):
    from unittest.mock import AsyncMock, patch
    user = await _register(test_client, "e65_spy")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "SA"); b = await _ini(test_client, h, "SB")
    with patch("opentask.services.workspace_webhook.service.fire_webhooks", new_callable=AsyncMock) as fw:
        post = await test_client.post(f"/api/initiatives/{a['id']}/relations", headers=h, json={"targetInitiativeId": b["id"], "type": "relates_to"})
        assert post.status_code == 200
        rid = post.json()["data"]["id"]
        await test_client.delete(f"/api/initiatives/{a['id']}/relations/{rid}", headers=h)
        fw.assert_not_called()
```

门禁命令：
```bash
cd backend && python -m pytest -q --tb=line 2>&1 | tee /tmp/e65-be.txt
python -m pytest tests/api/test_e65_initiative_relations.py tests/api/test_initiatives.py tests/api/test_initiative_health.py -q
cd ../agent-harness/opentask-cli && python -m pytest -q
cd ../../frontend && pnpm exec vitest run && pnpm run build
```

- [ ] Commit tip：`docs(E65): acceptance — tip + gates`
- [ ] STOP；不 push；不开 E66

---

## Spec coverage checklist
- [x] A model/alembic separate table
- [x] B CRUD + writer+ + same-WS + self-loop 400 + cross-tenant 404 + cycle Q4a + counts Q3a
- [x] C FE fold + optional badges + vitest + no gantt
- [x] D CLI 1.49.0 Q6a
- [x] E no webhook Q5a + no-emit + neighbor surfaces untouched
- [x] Q1a–Q6a / D1–D7 locked
