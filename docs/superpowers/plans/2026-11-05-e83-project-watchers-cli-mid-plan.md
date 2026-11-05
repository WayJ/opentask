# E83 Plan：Project Watchers CLI mid · CLI 1.67.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`dd3e920`（全文 `dd3e920ec92ba93e6c841199cc22d8a913ca8c95`；含 E83 design；E82 tip `bcd8f88` ⊂ HEAD）· 分支 `sprint/E83-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e83-project-watchers-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E84**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+/viewer（自订）可用 CLI **1.67.0** 做 `project watch|unwatch|watchers`；`project show` 可见 `watching_count`；api_client 有 list/watch/unwatch；BE list/watch 富化 username/name；跨租户/缺项目 404；**不**改 E82/E81/E80/E79 主表面；**无**新 webhook/表；formula no-emit；零产品 FE；不重开 E63–E82。

**Architecture:** 复用既有 `GET/POST/DELETE /api/projects/{id}/watchers`（Q1a）；`ProjectWatcherService` 加 `enrich_watchers` 对齐 Issue（Q3a）；CLI 扁平三命令对齐 Issue（Q2a）；`project show` 额外 GET watchers 计 `watching_count`（Q4a，失败降级）；pins 1.67.0（Q5a）；FE 零改（Q6a）。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E84；中文 docs；CLI **1.67.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：复用三端点 · 扁平 `project watch|unwatch|watchers` · enrich username · show `watching_count` · pins 1.67.0 · 零产品 FE
- **不**改 issue-template / milestone / `apply_project_move_integrity` / lead-members / cycle / tag 主表面
- 无新 webhook / 无新表 / 无 alembic；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- 非目标见 design §2（含 `project list --watching` BE 过滤）

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/project_watcher/service.py` | `serialize_watcher` 增 username/name；新增 `enrich_watchers` |
| `backend/opentask/api/project/router.py` | list/watch 改用 enrich（不改路径/动词） |
| `backend/tests/api/test_e83_project_watchers.py` | BE TDD：enrich + 幂等/404/邻面 spy |
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | `list_project_watchers` / `watch_project` / `unwatch_project` |
| `agent-harness/opentask-cli/opentask/core/project.py` | `watch|unwatch|watchers` + show `watching_count` |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.67.0** + 历史 epic 断言级联 |
| `agent-harness/opentask-cli/tests/test_e83_project_watchers.py` | CLI TDD |
| `docs/superpowers/acceptances/2026-11-05-e83-project-watchers-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e83-project-watchers-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e83-project-watchers-cli-mid-acceptance.md
git commit -m "docs(E83): plan + acceptance skeleton"
```

---

### Task 2 — A：BE enrich username/name（TDD）

**Files:**
- Modify: `backend/opentask/services/project_watcher/service.py`
- Modify: `backend/opentask/api/project/router.py`（list + watch 响应）
- Create: `backend/tests/api/test_e83_project_watchers.py`

**Interfaces:**
```python
def serialize_watcher(
    w: ProjectWatcher, *, username: str | None = None, name: str | None = None
) -> dict:
    return {
        "id": w.id,
        "workspace_id": w.workspace_id,
        "project_id": w.project_id,
        "user_id": w.user_id,
        "username": username,
        "name": name,
        "created_at": w.created_at,
    }

async def enrich_watchers(db: AsyncSession, rows: list[ProjectWatcher]) -> list[dict]:
    # 对齐 issue_watcher.enrich_watchers：批量查 UserModel，填 username/name|sso_name
    ...
```

**Router:**
```python
# GET list → await enrich_watchers(db, rows)
# POST watch → enrich 单行（或 enrich([row])[0]）
# DELETE 不变
```

**API tests (at least):**
- watch → list 行含 `username`/`name`（对齐注册名）
- watch 幂等 200；unwatch no-op 绿；list 行数
- 跨 WS / 缺项目 → 404
- spy：未改 `services/milestone/service.py` / `issue_project_move.py` / issue-template router / E79 roster 语义；无新 webhook；formula no-emit 不变；无 alembic 新文件

- [ ] **Step 1:** Write failing API tests
- [ ] **Step 2:** Run directed → FAIL（缺 username）
- [ ] **Step 3:** Implement enrich + wire list/watch
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E83): project watchers enrich username`

---

### Task 3 — C：CLI api_client + `project watch|unwatch|watchers` + pins 1.67.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`
- Modify: `agent-harness/opentask-cli/opentask/core/project.py`
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.VERSION` → **1.67.0**
- Cascade 历史 epic 测试里的 `1.66.0` → `1.67.0`
- Create: `agent-harness/opentask-cli/tests/test_e83_project_watchers.py`

**api_client:**
```python
async def list_project_watchers(self, project_id: str) -> list:
    data = await self.get(f"/api/projects/{project_id}/watchers")
    ...

async def watch_project(self, project_id: str) -> dict:
    return await self.post(f"/api/projects/{project_id}/watchers")

async def unwatch_project(self, project_id: str) -> dict:
    return await self.delete(f"/api/projects/{project_id}/watchers")
```

**CLI（对齐 issue 扁平）：**
- `opentask project watch <projectId> [--json]`
- `opentask project unwatch <projectId> [--json]`
- `opentask project watchers <projectId> [--json]`
- 需 `require_workspace_id`；table 列可用 User/Username/Since

**Tests:**
- `hasattr` api_client 三方法
- mock watch/unwatch/watchers 调用路径
- help 含三命令
- pins 1.67.0（VERSION + pyproject + setup + `__init__` + `--version`）

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** FAIL
- [ ] **Step 3:** Implement helpers + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E83): CLI 1.67.0 project watch|unwatch|watchers`

---

### Task 4 — C：`project show` watching_count（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/project.py`（`show_project`）
- Modify: `agent-harness/opentask-cli/tests/test_e83_project_watchers.py`（追加）

**Behavior:**
```python
# json 模式：额外 list_project_watchers → watching_count / watchers
# 失败（APIError/TypeError/ValueError）→ watching_count=0 / watchers=[]，不阻断 show
# 人机模式：status_block 可带 Watching count（可选，不挡）
```

- [ ] **Step 1:** Write failing test（show --json 含 watching_count）
- [ ] **Step 2:** FAIL
- [ ] **Step 3:** Wire show
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E83): project show watching_count`

---

### Task 5 — E：门禁 + acceptance

- Directed BE `tests/api/test_e83_project_watchers.py`（+既有 `test_project_health.py` watchers 段可附跑）
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e83）
- FE：零产品改动 → vitest smoke + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行）
- commit `docs(E83): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E84

---

## Self-review
1. Spec coverage：A enrich；C 三命令 + show count + 1.67.0；B 零 FE；D 邻面不动；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：serialize 字段与 Issue enrich 对齐；命令名扁平；pins 1.67.0 一致
