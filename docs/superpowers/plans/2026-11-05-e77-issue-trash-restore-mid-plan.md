# E77 Plan：Issue 回收站 mid — trash/restore · CLI 1.61.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`b1754a5`（全文 `b1754a58e1faefd28ceb308c659af5a1c36e09cf`；含 E77 design；E76 tip `d7c718c` ⊂ HEAD）· 分支 `sprint/E77-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e77-issue-trash-restore-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E78**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 可列出本 WS 已软删 Issue 并 restore（`is_deleted=false`）；viewer 可读 trash、不可 restore（403）；不级联子树；restore 幂等 200；timeline `restored`；无新 webhook 名；FE 回收站 + 恢复；CLI **1.61.0** `issue trash` / `issue restore`；CLI `issue delete` 仍拒；无新表；formula no-emit；不重开 E63–E76。

**Architecture:** 复用 `issues.is_deleted`；`IssueService.list_trashed` / `restore_issue` + `get_issue(..., include_deleted=)`；静态路由 `GET /api/issues/trash`（须在 `/{id}` 前）与 `POST /api/issues/{id}/restore`；timeline enum 加 `restored`（小 alembic ADD VALUE）；FE `/issue/trash` 页 + list 入口；CLI pins 全钉 1.61.0。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E78；中文 docs；CLI **1.61.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：viewer 可读不可 restore · 不级联 · restore 幂等 200 · 无 bulk · timeline `restored` 无新 webhook · CLI 1.61.0 + delete 仍拒
- **无新表**；仅 timeline enum ADD VALUE（不可避免）
- formula 永不 emit；无 Activity Push；无门户/甘特；无 hard-delete / purge / `archived_at`
- 不改 E63–E76 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search`（及序污染）记入 acceptance，不挡
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/alembic/versions/2026_11_05_5500-c6d7e8f9a0b1_timeline_restored.py` | ADD VALUE `restored` |
| `backend/opentask/models/issue/enums.py` | `TimelineAction.RESTORED` |
| `backend/opentask/models/issue/model.py` | ENUM 字面量补 `restored` |
| `backend/tests/conftest.py` | ADD VALUE `restored` |
| `backend/opentask/services/issue_service.py` | `list_trashed` / `restore_issue`；`get_issue(include_deleted=)` |
| `backend/opentask/api/issue/router.py` | `GET /trash`；`POST /{id}/restore`；GET 可选 `include_deleted` |
| `backend/tests/api/test_e77_issue_trash_restore.py` | API TDD |
| `frontend/src/service/api/issue.ts` | `listTrash` / `restoreIssue` |
| `frontend/src/views/issue/trash/index.vue` | 回收站页 |
| `frontend/src/views/issue/list/index.vue` | 「回收站」入口 |
| `frontend/src/views/issue/detail/index.vue` | deleted 只读条 + 恢复 |
| `frontend/src/router/**` + locales | `issue_trash` 路由；守 `f`+`r` |
| `frontend/src/utils/issueTrashMeta.ts` (+test) | 文案/helper |
| `agent-harness/opentask-cli/**` | 1.61.0 + `issue trash` / `issue restore` |
| `docs/superpowers/acceptances/2026-11-05-e77-issue-trash-restore-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e77-issue-trash-restore-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e77-issue-trash-restore-mid-acceptance.md
git commit -m "docs(E77): plan + acceptance skeleton"
```

---

### Task 2 — A：TimelineAction.RESTORED + alembic（随 API 红测）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_5500-c6d7e8f9a0b1_timeline_restored.py`（down=`b5c6d7e8f9a0`）
- Modify: `enums.py`；`model.py` ENUM；`tests/conftest.py`

```python
# enums.py
RESTORED = "restored"  # E77：从回收站恢复
```

Alembic：`ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS 'restored'`（upgrade）；downgrade no-op（PG enum 不可轻易 DROP VALUE）。

- [ ] **Step 1–2:** 随 Task 3 落地；commit `feat(E77): timeline restored enum + alembic`

---

### Task 3 — A：list_trashed + restore_issue + API（TDD）

**Files:**
- Modify: `issue_service.py`；`api/issue/router.py`
- Create: `backend/tests/api/test_e77_issue_trash_restore.py`

**Interfaces:**
```python
async def get_issue(..., include_deleted: bool = False) -> Optional[Issue]:
    # include_deleted=False → 现行为（排除 deleted）
    # True → 不按 is_deleted 过滤（仍可按 id/code + workspace）

async def list_trashed(
    self, *, workspace_id: str, page: int = 1, page_size: int = 20
) -> tuple[list[Issue], int]:
    # is_deleted=True AND workspace_id；order updated_at DESC；paginate

async def restore_issue(
    self, issue_id: str, user_id: str, *, workspace_id: str
) -> Issue:
    # 跨 WS / 缺失 → LookupError
    # 已活 → 返回原 Issue（幂等，无新 timeline）
    # 软删 → is_deleted=False；_add_timeline(RESTORED, action_data={"from": "trash"})
    # 不级联子项；不发 issue.restored webhook；不 publish 新事件名
```

**Routes**（静态 `/trash` 放在 `/{issue_id}` 之前，与 `/export.csv` 同区）：
- `GET /api/issues/trash?page=&page_size=` — `require_workspace_context`；viewer+；slim rows
- `POST /api/issues/{issue_id}/restore` — member+（`role in owner|member`）；viewer → 403
- `GET /api/issues/{id}?include_deleted=true` — 可选；deleted 同 WS 可读

**红测覆盖：**
1. 软删后默认 list/get 不可见；trash 可见；restore 后 list 可见、trash 消失
2. restore 幂等 200（已活再 restore）
3. 跨 WS 404；viewer trash GET 200；viewer restore 403；member restore 200
4. 父+子皆删：只 restore 父 → 子仍 deleted / 仍在 trash
5. timeline 有 `restored`；无 `issue.restored` webhook 新名（spy publish / outbound）
6. 无 hard DELETE；无新表

- [ ] **Step 1:** 写红测 → FAIL
- [ ] **Step 2:** 实现 → 绿
- [ ] **Step 3:** commit `feat(E77): trash list + restore API + timeline`

---

### Task 4 — B：FE 回收站 + vitest + f/r

**Files:**
- Create: `frontend/src/utils/issueTrashMeta.ts` + `.test.ts`
- Create: `frontend/src/views/issue/trash/index.vue`
- Modify: `issue.ts` API；`list/index.vue` 入口；`detail/index.vue` banner；router + locales

**Helper:**
```ts
export function trashEmptyHint(): string; // 「回收站为空」
export function restoreSuccessMessage(code: string): string; // 「已恢复 XXX」
```

- 路由 `issue_trash` → `/issue/trash`（menu 可见，在 issue 子树）
- 表格：code/title/status/priority/updated_at + 「恢复」
- 详情：`include_deleted` 拉到 deleted → 只读条 + 恢复按钮
- build 后确认 `routes/index.ts` 仍含 `/f/:token` + `/r/:token`

- [ ] TDD helper → FE 页 → vitest+build → commit `feat(E77): FE trash page + restore`

---

### Task 5 — C：CLI 1.61.0

**Files:**
- Bump all pins 1.60.0 → 1.61.0（含历史 epic 版本断言）
- `api_client.py`：`list_issue_trash` / `restore_issue`
- `core/issue.py`：`issue trash` / `issue restore`；update delete help 提 restore
- `tests/test_e77_issue_trash.py`

```
opentask issue trash [--json] [--limit N]
opentask issue restore <id|code> [--json]
```

- [ ] 红测 version + help → 实现 → 绿 → commit `feat(E77): CLI 1.61.0 trash/restore`

---

### Task 6 — Verify + acceptance

- Directed E77 BE；full BE；CLI；FE vitest+build
- 记门禁数 / flake；写 acceptance；tip SHA；`superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP** — 不 push / 不开 PR / 不自开 E78

