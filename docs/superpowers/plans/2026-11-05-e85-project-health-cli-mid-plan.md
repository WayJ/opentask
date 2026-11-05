# E85 Plan：Project Health CLI mid · CLI 1.69.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`3a0add2`（全文 `3a0add215d27463e8f8be34f3fa751c8ce59ba1f`；含 E85 design；E84 tip `dde41b1` ⊂ HEAD）· 分支 `sprint/E85-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e85-project-health-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E86**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer+ 可用 CLI **1.69.0** 做 `project health get|set`（含 `--history`）与 `project timeline`；api_client 有三 helpers；`project show` 附 latest health / health_status（失败降级）；**不**改 E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead 主表面；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；不重开 E63–E84。

**Architecture:** 复用既有 `GET/POST /api/projects/{id}/health` + `GET /api/projects/{id}/timeline`（Q1a）；CLI nested `project health get|set` + 顶层 `project timeline`（Q2a，对齐 lead/member/milestone 组）；`project show` 附 health（Q3a）；timeline 本轮薄接线（Q4a）；pins 1.69.0（Q5a）；FE 零改（Q6a）。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E86；中文 docs；CLI **1.69.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · nested health 组 · show 附 health · timeline 本轮 · pins 1.69.0 · 零产品 FE
- **不**改 cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members 主表面；**不**改既有 list/create/update/delete/watch/unwatch/watchers/lead/member/milestone
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- status 枚举：`on_track` / `at_risk` / `off_track`

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | `get_project_health` / `post_project_health` / `get_project_timeline` |
| `agent-harness/opentask-cli/opentask/core/project.py` | nested `health` 组 get\|set；`timeline` 命令；`show` 附 health |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.69.0** + 历史 epic 断言级联 |
| `agent-harness/opentask-cli/tests/test_e85_project_health.py` | CLI TDD |
| `backend/tests/api/test_e85_project_health_cli_mid.py` | 邻面 spy + 既有端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e85-project-health-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e85-project-health-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e85-project-health-cli-mid-acceptance.md
git commit -m "docs(E85): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client 三 helpers + nested health + timeline + show 附 health + pins 1.69.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（接在 Project Watchers 段后）
- Modify: `agent-harness/opentask-cli/opentask/core/project.py`
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.69.0**
- Cascade 历史 epic 测试里的 `1.68.0` → `1.69.0`
- Create: `agent-harness/opentask-cli/tests/test_e85_project_health.py`

**Interfaces (api_client):**
```python
async def get_project_health(self, project_id: str, *, history: bool = False) -> dict:
    params = {"history": "true" if history else "false"}
    return await self.get(f"/api/projects/{project_id}/health", params=params)

async def post_project_health(
    self, project_id: str, *, status: str, note: str | None = None
) -> dict:
    body: dict = {"status": status}
    if note is not None:
        body["note"] = note
    return await self.post(f"/api/projects/{project_id}/health", data=body)

async def get_project_timeline(self, project_id: str) -> dict:
    return await self.get(f"/api/projects/{project_id}/timeline")
```

**CLI commands (nested health group + timeline):**
```python
@project_cli.group(name="health")
def health_cli():
    """E85: project health get|set."""
    pass

@health_cli.command(name="get")
@click.argument("project_id")
@click.option("--history", is_flag=True, help="Include health history")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def project_health_get(obj, project_id, history, as_json):
    data = asyncio.run(client.get_project_health(project_id, history=history))
    # json → echo_json; human → status_block of latest + optional history table

@health_cli.command(name="set")
@click.argument("project_id")
@click.option("--status", type=click.Choice(["on_track", "at_risk", "off_track"]), required=True)
@click.option("--note", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def project_health_set(obj, project_id, status, note, as_json):
    data = asyncio.run(client.post_project_health(project_id, status=status, note=note))

@project_cli.command(name="timeline")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def project_timeline(obj, project_id, as_json):
    data = asyncio.run(client.get_project_timeline(project_id))
```

**`project show` enrichment (Q3a):**
```python
# after watchers enrichment, degrade-safe:
health = None
health_status = None
try:
    h = asyncio.run(client.get_project_health(project.get("id") or project_id, history=False))
    if isinstance(h, dict):
        latest = h.get("latest") if "latest" in h else h
        # tolerate wrapped {data: {latest:...}}
        if isinstance(h.get("data"), dict) and "latest" in h["data"]:
            latest = h["data"]["latest"]
        health = latest
        if isinstance(latest, dict):
            health_status = latest.get("status")
except (APIError, TypeError, ValueError):
    health = None
    health_status = None
# JSON output adds health / health_status; human status_block adds Health line
```

**Tests (at least):**
- `hasattr` api_client 三方法
- `project --help` 含 `health` / `timeline`；`project health --help` 含 `get` / `set`
- mock health get（默认 + `--history`）/ set（status+note）/ timeline 调用路径
- set 缺 `--status` → exit ≠ 0
- `project show --json` 含 `health` / `health_status`；health 拉取失败降级不阻断
- pins 1.69.0（VERSION + pyproject + setup + `__init__` + `--version`）

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helpers/commands / pins 仍 1.68.0）
- [ ] **Step 3:** Implement helpers + commands + show enrichment + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E85): CLI 1.69.0 project health get|set + timeline`

---

### Task 3 — A：BE 邻面 spy + 既有 project_health smoke

**Files:**
- Create: `backend/tests/api/test_e85_project_health_cli_mid.py`

**Tests:**
- spy：`api/project/router.py` 仍含 `health_router` / `post_project_health` / `get_project_health` / `get_project_timeline`；无 alembic 新文件命名 e85；邻面 markers 仍在（cycles generate-upcoming、project_watcher enrich、issue_templates、milestone、issue_project_move）
- 附跑既有：`tests/api/test_project_health.py`

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E85): BE project-health mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e85_project_health_cli_mid.py` + `test_project_health.py`
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e85）
- FE：零产品改动 → vitest smoke + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行）
- commit `docs(E85): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E86

---

## Self-review
1. Spec coverage：A 无新路由 + smoke；C nested health + timeline + api_client + show + 1.69.0；B 零 FE；D 邻面不动；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：helpers 名 `get_project_health` / `post_project_health` / `get_project_timeline`；nested `health` 组；pins 1.69.0 一致；status Choice 三枚举
