# E82 Plan：Issue Templates CLI mid · CLI 1.66.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`9e76efc`（全文 `9e76efc9641559a726fa86053e58b2bdc14e7acb`；含 E82 design；E81 tip `69b2112` ⊂ HEAD）· 分支 `sprint/E82-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e82-issue-templates-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E83**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 可用 CLI **1.66.0** 做 `issue-template list|show|create|update|delete|seed`；`issue create --template-id` 合并模板 payload；BE `GET /api/issue-templates/{id}`；FE 工作区模板页一键 seed；viewer 写 403；跨租户 404；**不**改 E81/E80/E79/E72 主表面；**无**新 webhook；formula no-emit；不重开 E63–E81。

**Architecture:** BE 补 GET by id（复用 `IssueTemplateService.get`）；CLI 顶层组 `issue-template` 对称 E72 `project-template`；api_client CRUD+seed + `create_issue(template_id=)`；FE seed 按钮 + `fetchSeedIssueTemplates` + 薄 helper；pins 1.66.0。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E83；中文 docs；CLI **1.66.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：GET by id · 顶层 `issue-template` · delete 允许含 seed · CLI seed + FE 按钮 · `issue create --template-id` + pins 1.66.0 · FE 仅 seed 薄刀
- **不**改 milestone / `apply_project_move_integrity` / lead/members / parent / trash / E72 project-template 语义
- 无新 webhook / 无新表 / 无 alembic；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/api/issue_templates/router.py` | 新增 `GET /{template_id}` |
| `backend/tests/api/test_e82_issue_templates.py` | API TDD（GET + seed viewer 403 + 邻面 spy） |
| `frontend/src/utils/issueTemplateSourceLabel.ts` (+test) | source 标签 + seed 确认文案 |
| `frontend/src/service/api/issue-templates.ts` | `fetchSeedIssueTemplates` |
| `frontend/src/views/workspace/issue-templates/index.vue` | Seed 按钮 |
| `agent-harness/opentask-cli/opentask/core/issue_template.py` | 顶层组 CRUD+seed |
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | issue-template helpers + `create_issue(template_id=)` |
| `agent-harness/opentask-cli/opentask/core/issue.py` | `--template-id` |
| `agent-harness/opentask-cli/opentask/opentask_cli.py` | register group + VERSION |
| VERSION / pyproject / setup / `__init__` | pins **1.66.0** + 历史 epic 断言级联 |
| `agent-harness/opentask-cli/tests/test_e82_issue_templates.py` | CLI TDD |
| `docs/superpowers/acceptances/2026-11-05-e82-issue-templates-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e82-issue-templates-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e82-issue-templates-cli-mid-acceptance.md
git commit -m "docs(E82): plan + acceptance skeleton"
```

---

### Task 2 — A：BE `GET /{template_id}`（TDD）

**Files:**
- Modify: `backend/opentask/api/issue_templates/router.py`
- Create: `backend/tests/api/test_e82_issue_templates.py`

**Interfaces:**
```python
@router.get("/{template_id}")
async def get_template(template_id: str, ...) -> success_response(data=serialize_issue_template(row))
# 复用 IssueTemplateService.get；跨租户/缺失 → 404；只读，viewer 可读
```

**API tests (at least):**
- create custom → GET by id 200 + serialize 字段齐全
- 跨 WS GET → 404；缺失 id → 404
- viewer GET 200；viewer POST/PATCH/DELETE/seed → 403
- seed POST → list 含 builtin seedKey
- spy：`services/milestone/service.py` / `issue_project_move.py` / E72 project-template CLI 文件未因本 epic 改动内容哈希基线；无新 webhook 名；formula no-emit 不变

- [ ] **Step 1:** Write failing API tests
- [ ] **Step 2:** Run directed → FAIL（缺 GET）
- [ ] **Step 3:** Implement GET route
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E82): GET issue-template by id`

---

### Task 3 — B：FE seed 按钮 + vitest（TDD）

**Files:**
- Create: `frontend/src/utils/issueTemplateSourceLabel.ts`
- Create: `frontend/src/utils/issueTemplateSourceLabel.test.ts`
- Modify: `frontend/src/service/api/issue-templates.ts`（`fetchSeedIssueTemplates`）
- Modify: `frontend/src/views/workspace/issue-templates/index.vue`

```typescript
export function issueTemplateSourceLabel(source: string | null | undefined): string {
  return source === 'seed' ? '内置' : '自定义';
}

export function issueTemplateSeedConfirmText(): string {
  return '将补齐缺失的内置 Issue 模板（已有 seedKey 不覆盖）。继续？';
}
```

- 工具栏增加 **恢复内置** 按钮 → confirm → `fetchSeedIssueTemplates` → reload
- 来源列可用 `issueTemplateSourceLabel`
- 不重做 CRUD 页

- [ ] **Step 1:** Write failing vitest
- [ ] **Step 2:** FAIL
- [ ] **Step 3:** Implement helper + api + button
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E82): FE issue-template seed button`

---

### Task 4 — C：CLI 1.66.0 `issue-template *` + api_client（TDD）

**Files:**
- Create: `agent-harness/opentask-cli/opentask/core/issue_template.py`
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`
- Modify: `agent-harness/opentask-cli/opentask/opentask_cli.py`
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.VERSION` → **1.66.0**
- Cascade 历史 epic 测试里的 `1.65.0` → `1.66.0`
- Create: `agent-harness/opentask-cli/tests/test_e82_issue_templates.py`

**api_client:**
```python
async def list_issue_templates(self) -> dict
async def get_issue_template(self, template_id: str) -> dict
async def create_issue_template(self, *, name: str, description=None, icon=None, payload=None, sort_order=0) -> dict
async def update_issue_template(self, template_id: str, **kwargs) -> dict
async def delete_issue_template(self, template_id: str) -> dict
async def seed_issue_templates(self) -> dict
# create_issue(..., template_id: str | None = None)
```

**CLI:**
- `issue-template list [--json]`
- `issue-template show <templateId> [--json]`
- `issue-template create --name NAME [--description ...] [--icon ...] [--payload-json '{...}'] [--sort-order N] [--json]`
- `issue-template update <templateId> [...] [--json]`
- `issue-template delete <templateId> [--json]`  # Q3a 允许含 seed
- `issue-template seed [--json]`  # Q4a

- [ ] **Step 1:** Write failing CLI tests（help + mocked CRUD/seed + version pins）
- [ ] **Step 2:** FAIL
- [ ] **Step 3:** Implement api_client + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E82): CLI 1.66.0 issue-template CRUD+seed`

---

### Task 5 — C：`issue create --template-id`（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/core/issue.py`
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（`create_issue(template_id=)`）
- Modify: `agent-harness/opentask-cli/tests/test_e82_issue_templates.py`（追加）

- `--title` 保持可用；`--template-id` 透传 body `template_id`
- 非法/跨租户随 BE 404/400

- [ ] **Step 1:** Write failing tests（create help 含 --template-id；mock 透传 template_id）
- [ ] **Step 2:** FAIL
- [ ] **Step 3:** Wire flag + client param
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E82): issue create --template-id`

---

### Task 6 — E：门禁 + acceptance

- Directed BE `tests/api/test_e82_issue_templates.py`（+既有 `test_issue_templates.py` 可附跑）
- Full BE `pytest tests`（flake 记入）
- CLI suite
- FE vitest + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行）
- commit `docs(E82): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E83

---

## Self-review
1. Spec coverage：A GET；B seed 按钮；C issue-template + create --template-id + 1.66.0；D 邻面不动；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：serialize 字段与 E9 一致；CLI 组名 `issue-template`；pins 1.66.0 一致
