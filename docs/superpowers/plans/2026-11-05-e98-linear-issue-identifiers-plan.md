# E98 Plan：Linear-style Issue Identifiers harden

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (本会话 inline) + test-driven-development + verification-before-completion。Steps use checkbox (`- [ ]`) syntax。禁止 push/PR；不自开 E99。

**Goal:** 所有新建 Issue 只分配 `KEY-N`（`^[A-Z0-9]{2,6}-\d+$`）；删除 `_generate_issue_code` 年号回退；无显式 WS 时仅可靠唯一可写/个人默认 WS 自动绑定，否则可行动 400；legacy 双读无限期保留；回填仅年号主码行；样例改 KEY-N。

**Architecture:** Harden E12：抽出可复用 `resolve_workspace_for_issue_create`；`_generate_issue_code(workspace_id)` 必填（None→ValueError）；堵 POST `/api/issues` / Jira / Tasks / collection；Alembic data revision 回填；不动 Team/真 Git/OAuth2/E79–E97 邻面。

**Tech Stack:** FastAPI + SQLAlchemy async；Alembic；pytest/httpx；Click CLI；Vue3/vitest。

## Global Constraints
- 基线：`sprint/E98-S1` @ `46848a80ed632088f4435a9a86fb00e0482d4428`（E97 tip `f8d5232` ⊂ HEAD）
- Scheme A / Q1a–Q6a；本地 only；不 push/PR；不开 E99；不停 7377/9527
- CLI VERSION **保持 1.81.0**（本 Epic 未要求 bump）
- 无 Team 模型；不改 Requirement 年号；不做真 Git/OAuth2/Push/门户/甘特；formula no-emit
- 禁止 `_resolve_fallback_workspace_id` / 库内最早 / Default 跨租户猜编号
- 守 E63 `f`+`r`；FE build 后恢复 elegant-router imports；WT 干净
- 测试只用假码；migration 空库可跑、幂等、不可靠孤儿跳过不删
- SQLite 不保证真实 FOR UPDATE：directed 测验证调用路径/唯一性/锁 API 使用；边界写入 acceptance

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/workspace/issue_create_ws.py` | **新增** 可靠唯一可写 WS 解析 + `WorkspaceRequiredError` |
| `backend/opentask/services/issue_service.py` | `_generate_issue_code` 删年号；`create_issue` 仍要求已解析 ws |
| `backend/opentask/api/issue/router.py` | POST create：无头→解析；400 文案；docstring 样例 KEY-N |
| `backend/opentask/api/jira/router.py` | create 前解析 ws 并传入 |
| `backend/opentask/api/tasks/router.py` | create_task 同策略 |
| `backend/opentask/api/tasks/service.py` | `ContractIssueService.create_issue` 接受/转发 `workspace_id`；更新注释（不再依赖年号重试） |
| `backend/opentask/services/issue_collection_service.py` | 每条解析/要求 ws；INSERT 写 `workspace_id` |
| `backend/alembic/versions/2026_11_05_5800-f9a0b1c2d3e4_e98_backfill_year_issue_codes.py` | data migration；`down_revision=e8f9a0b1c2d3` |
| `backend/tests/api/test_e98_linear_issue_identifiers.py` | 主 directed 套件 |
| `backend/tests/api/test_e98_backfill_migration.py` | migration 幂等/安全 |
| `backend/tests/issue/test_issues_api.py` | 年号断言 → KEY-N |
| `backend/tests/tasks/test_tasks_review_fixes.py` | None→ValueError；撞号测带 ws |
| `backend/tests/tasks/test_tasks_contract.py` | create 响应 KEY-N（保留 seed legacy 读） |
| CLI help 主例 / FE demo 字符串 | 主路径 KEY-N；legacy 双读测保留 |
| `docs/superpowers/acceptances/2026-11-05-e98-linear-issue-identifiers-acceptance.md` | 填满 |

### 解析语义（实现契约）
```python
WRITABLE_ROLES = frozenset({"owner", "member"})  # viewer 不可写
WORKSPACE_REQUIRED_DETAIL = (
    "workspace_required: Issue identifiers are KEY-N scoped to a workspace. "
    "Provide X-Workspace-Id, or ensure the caller has exactly one writable workspace. "
    "Year-prefixed ISSUE{year}-N allocation is removed."
)

class WorkspaceRequiredError(ValueError):
    """路由层转 HTTP 400；detail = WORKSPACE_REQUIRED_DETAIL"""

async def resolve_workspace_for_issue_create(
    session: AsyncSession,
    user_id: str,
    *,
    explicit_workspace_id: str | None = None,
) -> str:
    """Priority: explicit → sole personal-default(owner+created_by) when multiple writable
    → sole writable membership. Else raise WorkspaceRequiredError.
    Never call _resolve_fallback_workspace_id / earliest / Default."""
```

---

### Task 1 — Docs：plan + acceptance 骨架

- [ ] **Step 1:** 入库本 plan + acceptance 骨架（后填满，禁止留 `_pending_`）
- [ ] **Step 2:** commit `docs(E98): plan + acceptance skeleton`

---

### Task 2 — TDD：WS 解析 helper + `_generate_issue_code(None)` ValueError

**Files:**
- Create: `backend/opentask/services/workspace/issue_create_ws.py`
- Modify: `backend/opentask/services/issue_service.py`（删 year/LIKE 分支）
- Create: `backend/tests/api/test_e98_linear_issue_identifiers.py`（先写红测）

**Tests (至少):**
- `test_generate_issue_code_none_raises`
- `test_resolve_sole_writable_binds`
- `test_resolve_zero_writable_raises`
- `test_resolve_multi_writable_raises`（两 owner/member WS，无显式）
- `test_resolve_viewer_only_raises`（仅 viewer 成员不算可写）
- `test_resolve_explicit_wins`
- `test_resolve_personal_default_when_multi_writable`（可选：多可写但仅一个 created_by=user 且 role=owner → 绑个人默认）

- [ ] **Step 1:** Write failing tests
- [ ] **Step 2:** Run → FAIL
- [ ] **Step 3:** Implement helper + harden `_generate_issue_code`
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E98): require KEY-N workspace for issue codes`

---

### Task 3 — TDD：堵 POST /api/issues + Jira + Tasks + collection

**Files:** 上述 routers + ContractIssueService + collection

**Tests:**
- API 显式 `X-Workspace-Id` → KEY-N 前缀=issue_key
- API 单可写无头 → 自动绑定 KEY-N + 落库 workspace_id
- API 多可写无头 → 400 含 `workspace_required` / `X-Workspace-Id`
- API 零可写 → 400
- Jira create / Tasks create 同策略，响应 key/metadata 为 KEY-N
- collection 缺 ws 且不可靠 → 失败/跳过不产年号；有可靠 ws → KEY-N 且写 workspace_id
- 邻面：legacy GET by_code / Jira key_to_issue_code 解码 / FE looksLikeIssueCode legacy 仍 true（断言源码或既有测）

- [ ] **Step 1–4:** 红→实现→绿
- [ ] **Step 5:** commit `feat(E98): bind or 400 on issue create surfaces`

---

### Task 4 — TDD：data migration 回填

**Files:**
- Create alembic `2026_11_05_5800-f9a0b1c2d3e4_e98_backfill_year_issue_codes.py`（revision `f9a0b1c2d3e4`, down `e8f9a0b1c2d3`）
- Create: `backend/tests/api/test_e98_backfill_migration.py`

**Migration 规则（Q4a）:**
1. 选 `issue_code ~ '^ISSUE[0-9]{4}-[0-9]+$'`
2. 若 `legacy_issue_code` 非空且 ≠ 当前年号码 → **跳过改码**
3. 否则设 `legacy_issue_code = issue_code`（若空或相等）
4. 有 `workspace_id`：按 WS、`ORDER BY created_at, id`，从现 `issue_counter` 后递增分配新 KEY-N；**不**重排已有 KEY-N
5. 无 WS：创建者唯一可写/个人默认可绑则挂+改码；否则 skip 计数，**不删**
6. 更新 `workspaces.issue_counter = max(counter, max N assigned)`
7. 幂等；空库 no-op

**Tests:** 年号主码改写+legacy 保留；已 KEY-N+异 legacy 不变；不可靠孤儿跳过不删；再跑幂等

- [ ] **Step 1–4:** 红→migration→绿
- [ ] **Step 5:** commit `feat(E98): backfill year issue_codes to KEY-N`

---

### Task 5 — 更新既有年号断言 + 样例清理 + 并发 directed

**Files:**
- `backend/tests/issue/test_issues_api.py`：格式断言 → `^[A-Z0-9]{2,6}-\d+$`
- `backend/tests/tasks/test_tasks_review_fixes.py`：`_generate_issue_code()` → ValueError；撞号测传入 ws
- `backend/tests/tasks/test_tasks_contract.py`：create 断言 KEY-N（seed `ISSUE2026-77` 读路径保留）
- `backend/opentask/api/issue/router.py` docstring：`ISSUE2026-32` 主例 → `OT-32` + legacy 说明
- CLI `core/issue.py` 主 help 例优先 KEY-N（保留至少一处 legacy 说明/测）
- FE：`IssueCardsDemo.vue` / `MarkdownEditor.vue` 演示串 → KEY-N；`command-palette-entities.test.ts` **保留** `ISSUE2026-32` true
- Directed 并发：同 WS 两次 create → 两枚不同连续 N；断言源码含 `with_for_update`（SQLite 边界说明）

- [ ] **Step 1–4:** 修红测 + 样例
- [ ] **Step 5:** commit `test(E98): align fixtures and samples to KEY-N`

---

### Task 6 — 门禁 + acceptance 填满 + STOP

- Directed：`test_e98_*` + `test_issue_key.py` + issue create / Jira / Tasks / collection 相关
- Full BE `pytest tests`（flake `test_user_search` 记入，不挡）
- CLI full（若触 help/样例）+ VERSION 仍 1.81.0
- FE vitest + production build；恢复 `f`+`r`；`git status` 干净
- 确认无新年号分配路径（rg `ISSUE{current_year}` / year LIKE 分配）；legacy 读仍在
- 填满 acceptance（tip SHA、门禁数、Q1a–Q6a、安全、禁区、superpowers 行；无 `_pending_`）
- commit `docs(E98): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E99；不停服务

---

## Self-review
- Spec §1–§3 / Q1a–Q6a / 验收草案均有任务
- 无 TBD 占位；解析签名与路由 400 一致
- 禁：跨租户猜 WS、新 ISSUE{year} 分配、删 legacy 读、Team、push/PR/E99、停 7377/9527
