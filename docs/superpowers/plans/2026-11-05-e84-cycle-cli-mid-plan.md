# E84 Plan：Cycle CLI mid · CLI 1.68.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`02cd994`（全文 `02cd994c08ef1e8f1b59cf871538bd4060c2a849`；含 E84 design；E83 tip `f066e88` ⊂ HEAD）· 分支 `sprint/E84-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e84-cycle-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E85**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer+ 可用 CLI **1.68.0** 做 `cycle generate-upcoming|update|delete`；api_client 有三 helpers；跨租户/缺 cycle 404（既有 BE）；**不**改 E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead 主表面；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；不重开 E63–E83。

**Architecture:** 复用既有 `POST /api/cycles/generate-upcoming`、`PATCH /api/cycles/{id}`、`DELETE /api/cycles/{id}`（Q1a）；CLI 扁平挂既有 `cycle` 组（Q2a）；delete 不强制 `--yes`（Q3a）；update 仅发显式字段 PATCH partial（Q4a）；pins 1.68.0（Q5a）；FE 零改（Q6a）。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E85；中文 docs；CLI **1.68.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · 扁平三命令 · 无强制 `--yes` · PATCH partial · pins 1.68.0 · 零产品 FE
- **不**改 project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members 主表面；**不**改既有 list/show/create/activate/complete/capacity
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- 非目标见 design §2（含 Project health CLI → E85）

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | `generate_upcoming_cycle` / `update_cycle` / `delete_cycle` |
| `agent-harness/opentask-cli/opentask/core/cycle.py` | `generate-upcoming` / `update` / `delete` 三命令 |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.68.0** + 历史 epic 断言级联 |
| `agent-harness/opentask-cli/tests/test_e84_cycle_cli.py` | CLI TDD |
| `backend/tests/api/test_e84_cycle_cli_mid.py`（可选） | 邻面 spy + 既有端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e84-cycle-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e84-cycle-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e84-cycle-cli-mid-acceptance.md
git commit -m "docs(E84): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client 三 helpers + 三命令 + pins 1.68.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Cycles 段，接在 `complete_cycle` 后）
- Modify: `agent-harness/opentask-cli/opentask/core/cycle.py`
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.VERSION` → **1.68.0**
- Cascade 历史 epic 测试里的 `1.67.0` → `1.68.0`
- Create: `agent-harness/opentask-cli/tests/test_e84_cycle_cli.py`

**Interfaces (api_client):**
```python
async def generate_upcoming_cycle(self) -> dict:
    return await self.post("/api/cycles/generate-upcoming")

async def update_cycle(self, cycle_id: str, **kwargs) -> dict:
    # kwargs 仅含显式字段：name / starts_at / ends_at
    return await self.patch(f"/api/cycles/{cycle_id}", data=kwargs)

async def delete_cycle(self, cycle_id: str) -> dict:
    return await self.delete(f"/api/cycles/{cycle_id}")
```

**CLI commands:**
```python
@cycle_cli.command(name="generate-upcoming")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_generate_upcoming(obj, as_json):
    ...
    data = asyncio.run(client.generate_upcoming_cycle())
    # json → echo_json; human → skin.success

@cycle_cli.command(name="update")
@click.argument("cycle_id")
@click.option("--name", "-n", default=None)
@click.option("--starts-at", default=None)
@click.option("--ends-at", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_update(obj, cycle_id, name, starts_at, ends_at, as_json):
    body = {}
    if name is not None:
        body["name"] = name
    if starts_at is not None:
        body["starts_at"] = starts_at
    if ends_at is not None:
        body["ends_at"] = ends_at
    if not body:
        raise click.UsageError("至少提供一个更新字段")
    data = asyncio.run(client.update_cycle(cycle_id, **body))

@cycle_cli.command(name="delete")
@click.argument("cycle_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_delete(obj, cycle_id, as_json):
    # Q3a：无 --yes；对齐 label/initiative delete
    data = asyncio.run(client.delete_cycle(cycle_id))
```

**Tests (at least):**
- `hasattr` api_client 三方法
- help 含 `generate-upcoming` / `update` / `delete`
- mock generate-upcoming / update（partial body） / delete 调用路径
- update 无字段 → UsageError / exit ≠ 0
- pins 1.68.0（VERSION + pyproject + setup + `__init__` + `--version`）

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helpers/commands / pins 仍 1.67.0）
- [ ] **Step 3:** Implement helpers + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E84): CLI 1.68.0 cycle generate-upcoming|update|delete`

---

### Task 3 — A：BE 邻面 spy（可选定向）+ 既有 cycles smoke

**Files:**
- Create: `backend/tests/api/test_e84_cycle_cli_mid.py`（轻量 spy，无新路由断言）

**Tests:**
- spy：`api/cycles/router.py` 仍含 `generate-upcoming` / PATCH / DELETE 路径字符串；无 alembic 新文件本 epic；未改 `services/project_watcher` / `issue_template` / `milestone` / `issue_project_move` 主模块签名为「本 epic 不触碰」用文件 mtime/内容关键字检查或简单 import 存在性
- 附跑既有：`tests/api/test_cycles.py` + `test_cycle_complete.py`（含 generate-upcoming / update / delete）

- [ ] **Step 1:** Write spy tests（若选用）
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E84): BE cycles mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e84_cycle_cli_mid.py` + `test_cycles.py` + `test_cycle_complete.py`（或至少 cycles smoke）
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e84）
- FE：零产品改动 → vitest smoke + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行）
- commit `docs(E84): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E85

---

## Self-review
1. Spec coverage：A 无新路由 + smoke；C 三命令 + api_client + 1.68.0；B 零 FE；D 邻面不动；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：helpers 名 `generate_upcoming_cycle` / `update_cycle` / `delete_cycle`；命令扁平；pins 1.68.0 一致；PATCH partial 仅显式字段
