# E79 Plan：Project lead + members mid · CLI 1.63.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`c07f94b`（全文 `c07f94b87797155e7e0fd03ba693733c02ceb76a`；含 E79 design；E78 tip `6fe2b57` ⊂ HEAD）· 分支 `sprint/E79-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e79-project-lead-members-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E80**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 可为同 WS Project 设置 **lead**、增删 **members**（roster-only）；show 含 lead+members、list 含 lead_id+member_count；FE 项目详情可编辑；CLI **1.63.0**；跨 WS / 非成员用户拒；viewer 写 403；**不**改 WS/Issue ACL；不改 E72 template apply；无新 webhook 名；formula no-emit；不重开 E63–E78。

**Architecture:** `projects.lead_id` FK + `project_members` 表（≠ `project_watchers`）；设 lead 时 upsert member（清 lead 保留 member）；PATCH/PUT `lead_id`；nested `/{id}/members` CRUD；序列化 show 完整 / list 精简；FE 详情 Lead/Members 编辑；CLI nested `project lead|member` + pins 1.63.0。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E80；中文 docs；CLI **1.63.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：单 lead_id · project_members 表 · set lead upsert member · list 精简/show 完整 · 无新 webhook · CLI lead/member + 1.63.0
- **roster-only**：不改 WS/Issue ACL；不做私有项目；不按 membership 过滤可见 Issue/Project
- 不改 E72 template apply；不把 lead/members 写入模板；≠ project_watchers
- formula 永不 emit；无 Activity Push；无门户/甘特
- 不改 E63–E78 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search`（及序污染）记入 acceptance，不挡
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/alembic/versions/2026_11_05_5700-e8f9a0b1c2d3_project_lead_members.py` | `lead_id` + `project_members` |
| `backend/opentask/models/requirement/model.py` | `Project.lead_id` |
| `backend/opentask/models/project_member/` | `ProjectMember` 模型 |
| `backend/opentask/models/__init__.py` | 注册 ProjectMember |
| `backend/opentask/services/project_member/service.py` | set/clear lead；add/remove/list members；serialize |
| `backend/opentask/services/project_service.py` | update 支持 lead_id；list/show 序列化钩子 |
| `backend/opentask/api/project/router.py` | PATCH/PUT lead_id；members nested router |
| `backend/opentask/models/requirement/schema.py` | ProjectResponse 可选 lead 字段（或 dict 扩展） |
| `backend/tests/conftest.py` | additive `lead_id`（create_all 已建表则靠 metadata） |
| `backend/tests/api/test_e79_project_lead_members.py` | API TDD |
| `frontend/src/utils/projectLeadMembers.ts` (+test) | lead/member 标签 helper |
| `frontend/src/service/api/project.ts` + typings | members API + lead_id |
| `frontend/src/views/workflow/project-detail/index.vue` | Lead 选择器 + Members 增删 |
| `frontend/src/views/workflow/projects/index.vue` | 可选 lead 展示（轻量） |
| `agent-harness/opentask-cli/**` | 1.63.0 + `project lead|member *` |
| `docs/superpowers/acceptances/2026-11-05-e79-project-lead-members-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e79-project-lead-members-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e79-project-lead-members-mid-acceptance.md
git commit -m "docs(E79): plan + acceptance skeleton"
```

---

### Task 2 — A：alembic + Project.lead_id + ProjectMember（随 API 红测）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_5700-e8f9a0b1c2d3_project_lead_members.py`（down=`d7e8f9a0b1c2`）
- Create: `backend/opentask/models/project_member/__init__.py` + `model.py`
- Modify: `requirement/model.py` 加 `lead_id`
- Modify: `models/__init__.py` 注册
- Modify: `tests/conftest.py` 若需 additive `lead_id`（create_all 通常够）

```python
# project_member/model.py
class ProjectMember(DBModel):
    __tablename__ = "project_members"
    id: str PK
    workspace_id: str FK workspaces CASCADE
    project_id: str FK projects CASCADE
    user_id: str
    role: str | None  # optional roster role label; unused by ACL
    created_at: datetime
    UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user")

# Project
lead_id: Mapped[str | None] = mapped_column(
    String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    comment="E79 project lead (roster-only)",
)
```

Alembic：ADD COLUMN `lead_id`；CREATE TABLE `project_members`（idempotent IF NOT EXISTS 风格同 E71）。

- [ ] **Step 1–2:** 随 Task 3 落地；commit `feat(E79): lead_id + project_members schema`

---

### Task 3 — A：set lead / members CRUD + 序列化（TDD）

**Files:**
- Create: `backend/opentask/services/project_member/service.py`
- Modify: `project_service.py`（update `lead_id`；async enrich list/show）
- Modify: `api/project/router.py`（ProjectUpdateBody.lead_id；PATCH+PUT；members_router）
- Create: `backend/tests/api/test_e79_project_lead_members.py`

**Interfaces:**
```python
# project_member/service.py
async def set_lead(*, project_id, workspace_id, user_id: str | None) -> Project:
    # user_id None → clear lead_id; keep member rows
    # user_id set → validate same-WS WorkspaceMember (any role incl viewer);
    #   cross-WS / non-member → ValueError("必须为同工作区成员") → 400
    #   upsert ProjectMember; set project.lead_id

async def add_member(*, project_id, workspace_id, user_id) -> ProjectMember:  # idempotent
async def remove_member(*, project_id, workspace_id, user_id) -> None:  # missing = no-op 200
async def list_members(*, project_id, workspace_id) -> list[dict]:  # user summaries; skip missing users

def user_summary(u: UserModel | None, user_id: str) -> dict | None:
    # missing user → None (soft); caller skips

# serialization (Q4a)
# show: {..., "lead_id", "lead": summary|null, "members": [...], "member_count": N}
# list: {..., "lead_id", "member_count"}  # no full members[] / lead object
```

**Router:**
```python
# PUT + PATCH /api/projects/{id} — lead_id in body (null clears); when lead_id in fields_set → require_writer via WS ctx
members_router = APIRouter(prefix="/{project_id}/members")
GET "" → list (any WS member)
POST "" body {user_id} → add (writer)
DELETE "/{user_id}" → remove (writer)
```

**红测覆盖：**
1. set lead → lead_id；自动出现在 members（Q3a）
2. clear lead → lead_id null；原用户仍在 members
3. add/remove member；重复 add 幂等；跨 WS user → 400
4. viewer 写 lead/member → 403；跨租户 project → 404
5. show 含 lead+members；list 含 lead_id + member_count（无完整 members[]）
6. spy：无新 webhook 事件名；不改 issue 读 ACL；formula no-emit
7. 不触 E78 parent / E77 trash / E76 links / E75 duplicate / E72 apply

- [ ] **Step 1:** 写红测 → FAIL
- [ ] **Step 2:** 实现 → 绿
- [ ] **Step 3:** commit `feat(E79): project lead + members API`

---

### Task 4 — B：FE Lead/Members + vitest + f/r

**Files:**
- Create: `frontend/src/utils/projectLeadMembers.ts` + `.test.ts`
- Modify: `frontend/src/typings/api/project.d.ts`；`service/api/project.ts`
- Modify: `frontend/src/views/workflow/project-detail/index.vue`
- Optionally light lead chip on `projects/index.vue`

**Helper:**
```typescript
export function leadLabel(u: { id: string; name?: string | null; sso_name?: string | null } | null | undefined): string
export function memberIds(members: { id: string }[] | null | undefined): string[]
```

**UI：** 详情卡「负责人 / 成员」：NSelect WS members（`fetchWorkspaceMembers`）；set lead → `updateProject({lead_id})`；add/remove → members API。不据此隐藏项目。

- [ ] **Step 1:** vitest helper 红→绿
- [ ] **Step 2:** wiring + build；确认 `routes/index.ts` 仍含 `/f/:token`+`/r/:token`
- [ ] **Step 3:** commit `feat(E79): FE project lead + members`

---

### Task 5 — C：CLI 1.63.0

**Files:**
- Modify: `VERSION` / `pyproject.toml` / `setup.py` / `__init__.py` / `opentask_cli.py` → **1.63.0**
- Cascade 历史 epic 测试里的 `1.62.0` → `1.63.0`
- Modify: `opentask/core/project.py` — nested `lead` + `member` groups
- Modify: `api_client.py` — `update_project(lead_id=...)`；`list/add/remove_project_members`
- Create: `tests/test_e79_project_lead_members.py`

```
opentask project lead set <project> <user>
opentask project lead clear <project>
opentask project member add|remove <project> <user>
opentask project member list <project>
```

- [ ] **Step 1:** 红测 help + version pins + mocked API calls
- [ ] **Step 2:** 实现 → 绿
- [ ] **Step 3:** commit `feat(E79): CLI 1.63.0 project lead|member`

---

### Task 6 — verify + acceptance

- [ ] Directed E79 BE；full BE；CLI；FE vitest + build
- [ ] 写 acceptance（tip SHA + 门禁数 + superpowers 行）
- [ ] commit `docs(E79): acceptance`
- [ ] **STOP** — 不 push / 不开 PR / 不自开 E80

## Self-review
- Spec A–E / Q1a–Q6a / 非目标 / no-emit / E72 边界 / watchers 边界 → 均有任务
- 无 TBD 占位；类型名前后一致（ProjectMember / lead_id / members_router）
