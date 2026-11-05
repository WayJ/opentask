# E90 Plan：Initiative Projects CLI mid · CLI 1.74.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`a4dd51e`（全文 `a4dd51ecd8e9cbeb979df0073ee32e94a4804dac`；含 E90 design；E89 tip `d8337ea` ⊂ HEAD）· 分支 `sprint/E90-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e90-initiative-projects-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E91**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer+ 可用 CLI **1.74.0** 做 `initiative projects set --ids …` + `initiative project attach|detach`；api_client 有 `set_initiative_projects` / `attach_initiative_project` / `detach_initiative_project` → **PUT**+`projectIds` / **POST** / **DELETE**；`initiative show` 人类表薄补 Projects；**不**改 E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 health / E84 cycle / E83 watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead / **E65 relations 主语义**；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；**不做** Initiative health/甘特；不重开 E63–E89。

**Architecture:** 复用既有 `PUT /api/initiatives/{id}/projects` body `{projectIds}`（全集替换；`[]` 清空；未知 project **400**）+ `POST …/projects/{project_id}` attach（幂等）+ `DELETE …/projects/{project_id}` detach（Q1a）；CLI 挂 `initiative projects set` + `initiative project attach|detach`（Q2a）；`--ids` 为主、空=清空（Q3a）；show 薄补 Projects（Q4a）；pins 1.74.0（Q5a）；FE 零改（Q6a）。语义**勿**套 CF soft-ignore 或 Favorites 全集 400——本端点空合法、未知 400。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E91；中文 docs；CLI **1.74.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `projects set` + `project attach|detach` · `--ids`（空=清空）· show 薄补 · pins 1.74.0 · 零产品 FE
- **不**改 E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members / **E65 relations helpers 与命令**
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特；**不做** Initiative health CLI / 甘特
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- **务必** set 用 **PUT** + JSON key **`projectIds`**（camelCase；勿发 `project_ids`）；attach **POST**；detach **DELETE**
- 空 `projectIds`/`--ids ""` **合法清空**；未知 project 透传 BE **400**

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | 三 helper：`set_initiative_projects` / `attach_initiative_project` / `detach_initiative_project` |
| `agent-harness/opentask-cli/opentask/core/initiative.py` | `projects set` + `project attach|detach`；`show` 薄补 Projects |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.74.0** + 历史 epic 断言级联 `1.73.0`→`1.74.0` |
| `agent-harness/opentask-cli/tests/test_e90_initiative_projects.py` | CLI TDD |
| `backend/tests/api/test_e90_initiative_projects_cli_mid.py` | 邻面 spy + PUT/POST/DELETE 端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e90-initiative-projects-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e90-initiative-projects-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e90-initiative-projects-cli-mid-acceptance.md
git commit -m "docs(E90): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client 三 helper + initiative projects/project 命令 + show 薄补 + pins 1.74.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Initiatives 段追加三 helper）
- Modify: `agent-harness/opentask-cli/opentask/core/initiative.py`
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.74.0**
- Cascade 历史 epic 测试里的 `1.73.0` → `1.74.0`
- Create: `agent-harness/opentask-cli/tests/test_e90_initiative_projects.py`

**Interfaces (api_client):**
```python
async def set_initiative_projects(self, initiative_id: str, project_ids: list[str]) -> dict:
    """E90: PUT /api/initiatives/{id}/projects — full replace (empty clears; unknown → 400)."""
    return await self.put(
        f"/api/initiatives/{initiative_id}/projects",
        data={"projectIds": list(project_ids)},
    )

async def attach_initiative_project(self, initiative_id: str, project_id: str) -> dict:
    """E90: POST /api/initiatives/{id}/projects/{project_id} — idempotent attach."""
    return await self.post(
        f"/api/initiatives/{initiative_id}/projects/{project_id}"
    )

async def detach_initiative_project(self, initiative_id: str, project_id: str) -> dict:
    """E90: DELETE /api/initiatives/{id}/projects/{project_id}."""
    return await self.delete(
        f"/api/initiatives/{initiative_id}/projects/{project_id}"
    )
```

**CLI commands:**
```python
def _parse_project_ids(ids_csv: str | None, positional: tuple[str, ...] | None) -> list[str]:
    ids: list[str] = []
    if ids_csv is not None:
        ids.extend([p.strip() for p in str(ids_csv).split(",") if p.strip()])
    for p in positional or ():
        s = str(p).strip()
        if s:
            ids.append(s)
    return ids

@initiative_cli.group(name="projects")
def projects_cli():
    """Set Initiative↔Projects association (full replace)."""
    pass

@projects_cli.command(name="set")
@click.argument("initiative_id")
@click.option("--ids", "ids_csv", default=None, help="Comma-separated project ids (replace); empty clears")
@click.argument("positional_ids", nargs=-1)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def projects_set(obj, initiative_id, ids_csv, positional_ids, as_json):
    # require_workspace_id
    # if ids_csv is None and not positional_ids → ClickException / exit 1（须显式 --ids，哪怕空）
    # project_ids = _parse_project_ids(ids_csv if ids_csv is not None else "", positional_ids)
    #   注意：传了 --ids "" → [] 清空；未传 --ids 且无位置参数 → 报错
    # client.set_initiative_projects(initiative_id, project_ids)
    # json → echo_json; human → success "关联项目已更新"

@initiative_cli.group(name="project")
def project_cli():
    """Attach / detach a single Project to an Initiative."""
    pass

@project_cli.command(name="attach")
@click.argument("initiative_id")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def project_attach(...):
    # client.attach_initiative_project(initiative_id, project_id)

@project_cli.command(name="detach")
@click.argument("initiative_id")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def project_detach(...):
    # client.detach_initiative_project(initiative_id, project_id)
```

**show 薄补（Q4a）:**
```python
# initiative_show human status_block 追加：
# "Projects": 摘要 —— prefer projectIds 逗号串；若有 projects[] 则用 name 列表；空则 ""
pids = data.get("projectIds") or []
projs = data.get("projects") or []
if projs:
    summary = ", ".join([(p.get("name") or p.get("id") or "")[:40] for p in projs if isinstance(p, dict)])
else:
    summary = ", ".join(str(x) for x in pids)
obj.skin.status_block({..., "Projects": summary})
```

**Tests (at least):**
- `hasattr` 三 helper；set 源码含 `self.put` + `/projects` + `projectIds`；**禁** `project_ids` JSON key；**禁** set 用 `self.post`
- attach 源码含 `self.post`；detach 含 `self.delete`
- `initiative --help` 含 `projects` 与 `project`；`projects set --help` 含 `--ids`；`project attach|detach --help` 绿
- `initiative projects set INIT --ids a,b --json` → `set_initiative_projects("INIT", ["a","b"])`
- `initiative projects set INIT --ids "" --json` → `set_initiative_projects("INIT", [])`（清空）
- 位置参数：`initiative projects set INIT p1 p2 --json` → `["p1","p2"]`（若实现双通道）
- 无 `--ids` 且无位置参数 → exit ≠ 0
- attach / detach 调用对应 helper
- show human 输出含 `Projects`（mock get_initiative 返回 projectIds）
- pins 1.74.0（VERSION + pyproject + setup + `__init__` + `--version`）
- **不**改 relations 命令断言仍在（help 仍含 relations/relation）

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.73.0）
- [ ] **Step 3:** Implement helpers + commands + show 薄补 + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E90): CLI 1.74.0 initiative projects set/attach/detach`

---

### Task 3 — A：BE 邻面 spy + 既有 initiatives PUT/POST/DELETE projects 端点存在性

**Files:**
- Create: `backend/tests/api/test_e90_initiative_projects_cli_mid.py`

**Tests:**
- spy：`api/initiatives/router.py` 仍含 `@router.put("/{initiative_id}/projects")` + `async def set_projects` + `projectIds`；`@router.post("/{initiative_id}/projects/{project_id}")` + `attach_project`；`@router.delete(...)` + `detach_project`
- **无**新 `@router.get/post/.../health` initiative health 路由
- 无 alembic 新文件命名 e90
- 邻面 markers 仍在（custom-fields POST reorder / favorites PUT reorder / tag-groups / replace_tags / project health / cycles generate-upcoming / project_watcher enrich / issue_templates / milestone / issue_project_move / E65 relations）
- formula no-emit soft guard
- 附跑既有：`tests/api/test_initiatives.py` smoke（若存在）

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E90): BE initiative-projects mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e90_initiative_projects_cli_mid.py` + `test_initiatives.py`（可选）
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e90）
- FE：零产品改动 → vitest smoke + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行；**勿留** `_pending_`/骨架）
- commit `docs(E90): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E91

---

## Self-review
1. Spec coverage：A 无新路由 + PUT/POST/DELETE；C set/attach/detach + api_client + 1.74.0 + show 薄补；B 零 FE；D 邻面不动（含 E65）；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：`set_initiative_projects(initiative_id, project_ids)` PUT+`projectIds`；attach POST；detach DELETE；pins 1.74.0；空 ids 清空；未知 400 透传；与 E89 soft / E88 favorites 全集 400 刻意不同
