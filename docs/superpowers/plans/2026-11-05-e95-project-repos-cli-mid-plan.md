# E95 Plan：Project Repos CLI mid · CLI 1.79.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`490bf30`（全文 `490bf30ccfaca44c28624f82eb951ea5dd0789f6`；含 E95 design；E94 tip `315d459` ⊂ HEAD）· 分支 `sprint/E95-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e95-project-repos-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E96**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 可用 CLI **1.79.0** 做 Project **repo list / show / add / update / remove**；api_client 五 helpers → 复用既有五端点；human 薄表 id/name/url/main_branch；**不**改 E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 health / E84 cycle / E83 watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；**不做** Initiative health/甘特 / bulk project_id / watching filter / requirement-repos / 真 Git；不重开 E63–E94。

**Architecture:** 复用既有 `repo_router` GET/POST/PUT/DELETE（Q1a）；CLI 挂 `project` 下子组 `repo`（Q2a，与 milestone/health 同构）；api_client create body 含 `project_id`（Q3a）；human 薄表；**不**改 `project show`（Q4a）；pins 1.79.0（Q5a）；FE 零改（Q6a）。**不要**停 7377/9527。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E96；中文 docs；CLI **1.79.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `project repo list|show|add|update|remove` · create body 带 `project_id` · human 薄表、不改 FE / show · pins 1.79.0 · 零产品 FE
- **不**改 E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特；**不做** Initiative health CLI / 甘特 / bulk project_id / watching filter / requirement-repos / `/api/repositories/*/git/*`
- 守 E63 `f`+`r`（FE build 冲掉 imports → **必须 checkout 恢复**；收尾 `git status` 干净）；已知 flake `test_user_search` 记入 acceptance，不挡
- **不要**停 7377 后端或 9527 前端
- 缺 `--name`/`--url`（add）本地失败不打 BE；`update` 无任何变更 flag → CLI 侧失败不打 BE
- 既有 `project milestone` / `project health` / `project lead` / `project member` 组**别破坏**

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | 五 project-repo helpers |
| `agent-harness/opentask-cli/opentask/core/project.py` | 新组 `repo` 挂 `project_cli` |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.79.0** + 历史 epic 断言级联 `1.78.0`→`1.79.0` |
| `agent-harness/opentask-cli/tests/test_e95_project_repos.py` | CLI TDD |
| `backend/tests/api/test_e95_project_repos_cli_mid.py` | 邻面 spy + repos 五端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e95-project-repos-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e95-project-repos-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e95-project-repos-cli-mid-acceptance.md
git commit -m "docs(E95): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client 五 helpers + `project repo` + pins 1.79.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（milestones 段附近追加五 helpers）
- Modify: `agent-harness/opentask-cli/opentask/core/project.py`（`repo` 组 + 五命令）
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.79.0**
- Cascade 历史 epic 测试里的 `1.78.0` → `1.79.0`
- Create: `agent-harness/opentask-cli/tests/test_e95_project_repos.py`

**Interfaces (api_client):**
```python
async def list_project_repos(self, project_id: str) -> list | dict:
    """E95: GET /api/projects/{id}/repos"""
    return await self.get(f"/api/projects/{project_id}/repos")

async def get_project_repo(self, project_id: str, repo_id: str | int) -> dict:
    """E95: GET /api/projects/{id}/repos/{repo_id}"""
    return await self.get(f"/api/projects/{project_id}/repos/{repo_id}")

async def create_project_repo(
    self,
    project_id: str,
    *,
    name: str,
    url: str,
    main_branch: str = "main",
) -> dict:
    """E95: POST /api/projects/{id}/repos body {name,url,main_branch,project_id}"""
    return await self.post(
        f"/api/projects/{project_id}/repos",
        data={
            "name": name,
            "url": url,
            "main_branch": main_branch,
            "project_id": project_id,
        },
    )

async def update_project_repo(
    self, project_id: str, repo_id: str | int, **fields
) -> dict:
    """E95: PUT /api/projects/{id}/repos/{repo_id} body 仅提供字段"""
    return await self.put(
        f"/api/projects/{project_id}/repos/{repo_id}",
        data=fields,
    )

async def delete_project_repo(self, project_id: str, repo_id: str | int) -> bool:
    """E95: DELETE /api/projects/{id}/repos/{repo_id}"""
    await self.delete(f"/api/projects/{project_id}/repos/{repo_id}")
    return True
```

**CLI commands (project.py):**
- `@project_cli.group(name="repo")` → `list|show|add|update|remove`（`remove` 可兼 alias `rm`）
- 形状：
  - `project repo list PROJECT [--json]`
  - `project repo show PROJECT REPO_ID [--json]`
  - `project repo add PROJECT --name NAME --url URL [--main-branch BRANCH] [--json]`
  - `project repo update PROJECT REPO_ID [--name NAME] [--url URL] [--main-branch BRANCH] [--json]`
  - `project repo remove PROJECT REPO_ID [--json]`
- `--name`/`--url` required on add → 缺参本地 Click 失败，不打 BE
- `update` 无任何变更 flag → CLI 本地失败（`click.UsageError` / SystemExit），不打 BE
- `main_branch` 默认 `main`（add）
- human：list/show 薄表 id/name/url/main_branch；add/update/remove 薄回显
- `--json` 全量；**不**改 `project show` / milestone / health / lead / member

**Tests (at least):**
- pins 1.79.0（VERSION + pyproject + setup + `__init__` + `--version`）
- 五 helpers 存在；源码含正确 method+path；POST body 键 name/url/main_branch/project_id；PUT 用 `self.put`
- `project --help` 含 `repo`；仍含 `milestone` / `health` / `lead` / `member`
- `project repo --help` 含 list/show/add/update/remove
- list/show/add/update/remove 调用对应 helper（mock）
- 缺 `--name`/`--url` → exit ≠ 0 且不调 helper
- `update` 无 flag → exit ≠ 0 且不调 helper
- list human 含 id/name/url/main_branch
- 邻面：`issue reaction --help` 仍含 list；`display-prefs --help` 仍含 get/set

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.78.0）
- [ ] **Step 3:** Implement helpers + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E95): CLI 1.79.0 project repo list|show|add|update|remove`

---

### Task 3 — A：BE 邻面 spy + 既有五 repos 端点存在性

**Files:**
- Create: `backend/tests/api/test_e95_project_repos_cli_mid.py`

**Tests:**
- spy：`api/project/router.py` 仍含：
  - `repo_router = APIRouter(prefix="/{project_id}/repos"`
  - `@repo_router.post("")` + `async def create_repo_config`
  - `@repo_router.get("")` + `async def list_repo_configs`
  - `@repo_router.get("/{repo_id}")` + `async def get_repo_config`
  - `@repo_router.put("/{repo_id}")` + `async def update_repo_config`
  - `@repo_router.delete("/{repo_id}")` + `async def delete_repo_config`
- **无**新 alembic 命名 e95；无新 initiative `/health`
- 邻面 markers 仍在（issue reactions 六端点 · display-prefs GET/PUT · saved-views write · board/move · initiatives projects · CF reorder · favorites reorder · tag-groups · replace_tags · project health · cycles · project_watcher · issue_templates · milestone · issue_project_move · E65 relations）
- formula no-emit soft guard
- **不**新增 requirement-repos CLI 断言为「未改」；确认未引入 `/api/repositories` git helpers 到本 epic（CLI 不增 `git_clone` 绑定到 project repo）
- 附跑既有：`tests/project/test_project_api.py::TestRepoConfigCRUD`（可选定向）

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E95): BE project-repos mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e95_project_repos_cli_mid.py` + `TestRepoConfigCRUD`
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e95）
- FE：零产品改动 → vitest smoke + production build；确认 `f`+`r`（若 build 冲掉 elegant imports → **checkout 恢复**）；收尾 `git status` 干净
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行；**勿留** `_pending_`/骨架）
- commit `docs(E95): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E96；不停 7377/9527

---

## Self-review
- Spec A–D / Q1a–Q6a / ADR D1–D6 均有对应任务
- 无 TBD/TODO 占位
- api_client 签名与 CLI 参数一致（create 含 `project_id`；update 用 PUT）
- 明确禁：新路由、initiative health、bulk project_id、watching filter、requirement-repos、真 Git、push/PR/E96、停 7377/9527
