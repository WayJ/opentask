# E87 Plan：Tag Group CLI mid · CLI 1.71.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`efd94ba`（全文 `efd94ba9589d565642f0785df4762a3f7c487030`；含 E87 design；E86 tip `a353f82` ⊂ HEAD）· 分支 `sprint/E87-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e87-tag-group-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E88**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer+ 可用 CLI **1.71.0** 做 `label group list|create|update|delete`；api_client 有 tag-group helpers；`label list --group-id` / `label create --group-id` 接线既有 BE；`label update --group-id` 接受 **str UUID**（修 E86 int 漂移）；**不**改 E86 set/multi 主语义（除 group-id 类型）/ E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；不重开 E63–E86。

**Architecture:** 复用既有 `GET/POST /api/tag-groups` + `PATCH/DELETE /api/tag-groups/{id}` + tags `group_id`（Q1a）；CLI 挂 `label group …`（Q2a）；`--group-id`→str UUID（Q3a）；薄补 list/create `--group-id`（Q4a）；pins 1.71.0（Q5a）；FE 零改（Q6a）。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E88；中文 docs；CLI **1.71.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `label group …` · `--group-id` str UUID · list/create `--group-id` · pins 1.71.0 · 零产品 FE
- **不**改 E86 set/multi 主语义（**仅** `--group-id` 类型对齐）/ project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | `list/create/update/delete_tag_group(s)`；`update_tag(group_id: str\|None)` |
| `agent-harness/opentask-cli/opentask/core/label.py` | `label group …` + list/create `--group-id` + update `--group-id` str |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.71.0** + 历史 epic 断言级联 |
| `agent-harness/opentask-cli/tests/test_e87_tag_group.py` | CLI TDD |
| `backend/tests/api/test_e87_tag_group_cli_mid.py` | 邻面 spy + 既有 tag-groups 端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e87-tag-group-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e87-tag-group-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e87-tag-group-cli-mid-acceptance.md
git commit -m "docs(E87): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client tag-group helpers + label group + list/create --group-id + update str + pins 1.71.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Tags 段后追加 Tag Groups；`update_tag` 的 `group_id: int` → `str`）
- Modify: `agent-harness/opentask-cli/opentask/core/label.py`
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.71.0**
- Cascade 历史 epic 测试里的 `1.70.0` → `1.71.0`
- Create: `agent-harness/opentask-cli/tests/test_e87_tag_group.py`

**Interfaces (api_client):**
```python
async def list_tag_groups(self) -> dict:
    """E87: GET /api/tag-groups."""
    return await self.get("/api/tag-groups")

async def create_tag_group(
    self, name: str, color: str | None = None, position: int = 0
) -> dict:
    """E87: POST /api/tag-groups."""
    data: dict = {"name": name, "position": position}
    if color is not None:
        data["color"] = color
    return await self.post("/api/tag-groups", data=data)

async def update_tag_group(
    self,
    group_id: str,
    *,
    name: str | None = None,
    color: str | None = None,
    position: int | None = None,
) -> dict:
    """E87: PATCH /api/tag-groups/{id}."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if color is not None:
        body["color"] = color
    if position is not None:
        body["position"] = position
    return await self.patch(f"/api/tag-groups/{group_id}", data=body)

async def delete_tag_group(self, group_id: str) -> dict:
    """E87: DELETE /api/tag-groups/{id}."""
    return await self.delete(f"/api/tag-groups/{group_id}")

# update_tag: group_id: int | None = None  →  group_id: str | None = None
```

**CLI commands:**
```python
@label_cli.group(name="group")
def label_group_cli():
    """E87: label group list|create|update|delete."""
    pass

@label_group_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
def label_group_list(...):
    # client.list_tag_groups()

@label_group_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--color", "-c", default=None)
@click.option("--position", type=int, default=0)
@click.option("--json", "as_json", is_flag=True)
def label_group_create(...):
    # client.create_tag_group(name=..., color=..., position=...)

@label_group_cli.command(name="update")
@click.argument("group_id")
@click.option("--name", default=None)
@click.option("--color", default=None)
@click.option("--position", type=int, default=None)
@click.option("--json", "as_json", is_flag=True)
def label_group_update(...):
    # require ≥1 field; client.update_tag_group(...)

@label_group_cli.command(name="delete")
@click.argument("group_id")
@click.option("--json", "as_json", is_flag=True)
def label_group_delete(...):
    # client.delete_tag_group(group_id)

# label list: add --group-id (str); pass to list_tags(group_id=)
# label create: add --group-id (str); pass to create_tag(group_id=)
# label update: --group-id type=str (was int); keep --clear-group
```

**Tests (at least):**
- `hasattr` `list_tag_groups` / `create_tag_group` / `update_tag_group` / `delete_tag_group`
- `label --help` 含 `group`；`label group --help` 含 list/create/update/delete
- `label group list --json` → list_tag_groups
- `label group create --name G --color #abc --position 1 --json` → create_tag_group
- `label group update GID --name G2 --json` → update_tag_group
- `label group delete GID --json` → delete_tag_group
- `label list --group-id UUID --json` → list_tags(group_id=UUID)
- `label create --name T --group-id UUID --json` → create_tag(group_id=UUID)
- `label update TAG --group-id UUID --json` → update_tag(group_id=str UUID)（非 int）
- `label update TAG --clear-group --json` 仍绿
- pins 1.71.0（VERSION + pyproject + setup + `__init__` + `--version`）

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helpers/commands / pins 仍 1.70.0）
- [ ] **Step 3:** Implement helpers + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E87): CLI 1.71.0 label group CRUD + group-id str`

---

### Task 3 — A：BE 邻面 spy + 既有 tag-groups 端点存在性

**Files:**
- Create: `backend/tests/api/test_e87_tag_group_cli_mid.py`

**Tests:**
- spy：`api/tags/router.py` 仍含 `list_tag_groups` / `create_tag_group` / `update_tag_group` / `delete_tag_group`；`groups_router` prefix `/api/tag-groups`；`TagUpdate.group_id: Optional[str]`；`list_tags` 有 `group_id` Query；无 alembic 新文件命名 e87
- 邻面 markers 仍在（replace_tags / project health / cycles generate-upcoming / project_watcher enrich / issue_templates / milestone / issue_project_move / E86 update_tag）
- 附跑既有：`tests/api/test_tags.py`（若存在且稳）

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E87): BE tag-group mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e87_tag_group_cli_mid.py` + `test_tags.py`
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e87）
- FE：零产品改动 → vitest smoke + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行）
- commit `docs(E87): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E88

---

## Self-review
1. Spec coverage：A 无新路由 + smoke；C group CRUD + list/create --group-id + update str + api_client + 1.71.0；B 零 FE；D 邻面不动；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：helpers 名 `list/create/update/delete_tag_group(s)`；`update_tag(group_id: str)`；commands `label group list|create|update|delete`；pins 1.71.0 一致
