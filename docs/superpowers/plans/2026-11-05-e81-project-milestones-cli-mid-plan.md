# E81 Plan：Project milestones CLI mid · CLI 1.65.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`4a9a1fa`（全文 `4a9a1fa728fc13d912c39bfd60fd183ce3a3c281`；含 E81 design；E80 tip `f929dc8` ⊂ HEAD）· 分支 `sprint/E81-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e81-project-milestones-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E82**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 可用 CLI **1.65.0** 对某 Project 做 milestone `list|create|show|update|delete`；`issue create --milestone` / `issue list --milestone`（含 `__none__`）可用；serialize/列表含 **`issue_count`**；FE 项目详情里程碑表展示占用；viewer 写 403；跨租户/跨项目 404；删里程碑依赖 DB `SET NULL`；**不**改 E80 helper；**无**新 webhook；formula no-emit；不重开 E63–E80。

**Architecture:** `serialize_milestone(..., issue_count=)` + 批量 `count_issues_by_milestone`；list 可选 `?status=`；CLI nested `project milestone *` + api_client CRUD；issue create/list 透传 `milestone_id`；FE 占用列 + `formatMilestoneIssueCount`；pins 1.65.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E82；中文 docs；CLI **1.65.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：serialize 均带 issue_count · list `?status=` · 删靠 FK SET NULL · CLI 允许 delete · `project milestone …` 子组 · create/list `--milestone` + pins 1.65.0
- **不**改 `apply_project_move_integrity` / `milestone_for_duplicate`
- 不重开 E79 lead/members / E78 parent / E77 trash 主表面；FE 仅加占用列（不重做 CRUD 页）
- 无新 webhook / 无新 timeline enum；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 不改 E63–E80 邻面主表面（仅 CLI version pins）；守 E63 `f`+`r`
- 已知 flake `test_user_search`（及序污染）记入 acceptance，不挡
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/milestone/service.py` | `serialize_milestone` + `issue_count`；`list(status=)`；`count_issues_by_milestone` |
| `backend/opentask/api/project/router.py` | list `?status=`；所有 serialize 传入 count；health 可默认 0 或批量 |
| `backend/tests/api/test_e81_project_milestones.py` | API TDD |
| `frontend/src/utils/formatMilestoneIssueCount.ts` (+test) | 占用列 helper |
| `frontend/src/typings/api/project.d.ts` | `issue_count?: number` |
| `frontend/src/views/workflow/project-detail/index.vue` | 占用列 + 删除确认文案 |
| `agent-harness/opentask-cli/**` | 1.65.0 + `project milestone *` + issue create/list `--milestone` |
| `docs/superpowers/acceptances/2026-11-05-e81-project-milestones-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e81-project-milestones-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e81-project-milestones-cli-mid-acceptance.md
git commit -m "docs(E81): plan + acceptance skeleton"
```

---

### Task 2 — A：`issue_count` + status filter（TDD）

**Files:**
- Modify: `backend/opentask/services/milestone/service.py`
- Modify: `backend/opentask/api/project/router.py`
- Create: `backend/tests/api/test_e81_project_milestones.py`

**Interfaces:**
```python
def serialize_milestone(m: Milestone, *, issue_count: int = 0) -> dict:
    """Q1a: always include issue_count (non-deleted issues same project+workspace)."""

async def count_issues_by_milestone(
    self, *, project_id: str, workspace_id: str, milestone_ids: list[str]
) -> dict[str, int]:
    """GROUP BY milestone_id WHERE NOT is_deleted; missing ids → 0."""

async def list(
    self, *, project_id: str, workspace_id: str, status: str | None = None
) -> list[Milestone]:
    """Q2a: optional status in {planned, done}; omit = all; invalid → 400."""
```

**API tests (at least):**
- create → list/get 含 `issue_count == 0`
- 两 issue 挂同一 milestone → list/get count=2；create/update 响应也带 count
- `?status=done` 仅 done；`?status=bogus` → 400
- delete milestone → 两 issue `milestone_id` null；get milestone → 404
- 跨项目 milestone id → 404；跨 WS → 403/404；viewer POST → 403
- spy：`issue_project_move.py` 文件内容未因本 epic 改动（或 helper 行为不变）；无新 webhook 名

- [ ] **Step 1:** Write failing API tests
- [ ] **Step 2:** Run directed → FAIL（缺 issue_count / status）
- [ ] **Step 3:** Implement serialize + count + list filter + router wire
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E81): milestone issue_count + status filter`

---

### Task 3 — B：FE 占用列 + vitest（TDD）

**Files:**
- Create: `frontend/src/utils/formatMilestoneIssueCount.ts`
- Create: `frontend/src/utils/formatMilestoneIssueCount.test.ts`
- Modify: `frontend/src/typings/api/project.d.ts`（`issue_count?: number`）
- Modify: `frontend/src/views/workflow/project-detail/index.vue`

```typescript
export function formatMilestoneIssueCount(n: number | null | undefined): string {
  const v = typeof n === 'number' && Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
  return String(v);
}

export function milestoneDeleteConfirmText(issueCount: number | null | undefined): string {
  const n = typeof issueCount === 'number' && issueCount > 0 ? Math.floor(issueCount) : 0;
  if (n > 0) return `确定删除此里程碑吗？将清空 ${n} 个 Issue 的里程碑引用。`;
  return '确定删除此里程碑吗?';
}
```

- 表增加列 **占用**（`key: 'issue_count'`，render `formatMilestoneIssueCount`）
- NPopconfirm default 用 `milestoneDeleteConfirmText(row.issue_count)`
- 不重做 CRUD 页

- [ ] **Step 1:** Write failing vitest
- [ ] **Step 2:** FAIL
- [ ] **Step 3:** Implement helper + column + confirm
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E81): FE milestone occupancy column`

---

### Task 4 — C：CLI 1.65.0 `project milestone *` + api_client（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（list/create/get/update/delete milestone）
- Modify: `agent-harness/opentask-cli/opentask/core/project.py`（`@project_cli.group(name="milestone")` + 5 cmds）
- Modify: `VERSION` / `pyproject.toml` / `setup.py` / `__init__.py` / `opentask_cli.py` → **1.65.0**
- Cascade 历史 epic 测试里的 `1.64.0` → `1.65.0`
- Create: `agent-harness/opentask-cli/tests/test_e81_project_milestones.py`

**api_client:**
```python
async def list_project_milestones(self, project_id: str, *, status: str | None = None) -> list | dict
async def create_project_milestone(self, project_id: str, **kwargs) -> dict
async def get_project_milestone(self, project_id: str, milestone_id: str) -> dict
async def update_project_milestone(self, project_id: str, milestone_id: str, **kwargs) -> dict
async def delete_project_milestone(self, project_id: str, milestone_id: str) -> bool
```

**CLI:**
- `project milestone list <projectId> [--status planned|done] [--json]`
- `project milestone create <projectId> --name NAME [--description ...] [--target-date YYYY-MM-DD] [--status planned|done] [--position N] [--json]`
- `project milestone show <projectId> <milestoneId> [--json]`
- `project milestone update <projectId> <milestoneId> [...] [--json]`
- `project milestone delete <projectId> <milestoneId> [--json]`  # Q4a 允许

- [ ] **Step 1:** Write failing CLI tests（help + mocked CRUD + version pins）
- [ ] **Step 2:** FAIL
- [ ] **Step 3:** Implement api_client + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E81): CLI 1.65.0 project milestone CRUD`

---

### Task 5 — C：`issue create|list --milestone`（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/issue.py`（create `--milestone`；list `--milestone`）
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（`create_issue(milestone_id=)`；`list_issues(milestone_id=)`）
- Modify: `agent-harness/opentask-cli/tests/test_e81_project_milestones.py`（追加）

- [ ] **Step 1:** Write failing tests（create passes milestone_id；list passes milestone_id/`__none__`）
- [ ] **Step 2:** FAIL
- [ ] **Step 3:** Wire flags + client params
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E81): issue create/list --milestone`

---

### Task 6 — E：门禁 + acceptance

- Directed BE `tests/api/test_e81_project_milestones.py`
- Full BE `pytest tests`（flake 记入）
- CLI suite
- FE vitest + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行）
- commit `docs(E81): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E82

---

## Self-review
1. Spec coverage：A issue_count+status+SET NULL；B 占用列；C project milestone + issue flags + 1.65.0；D 邻面不动；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：`issue_count: int`；CLI 子组名 `milestone`；pins 1.65.0 一致
