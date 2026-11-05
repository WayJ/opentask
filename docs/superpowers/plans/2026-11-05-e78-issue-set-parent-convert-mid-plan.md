# E78 Plan：Issue 父子转换 mid — set-parent / convert · CLI 1.62.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`d2e30be`（全文 `d2e30bea3bf5a1aef9c2339419b2be7086a5a527`；含 E78 design；E77 tip `04d5118` ⊂ HEAD）· 分支 `sprint/E78-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e78-issue-set-parent-convert-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E79**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 可将同 WS Issue 设为另一 Issue 子项、更换父、或清空父（提升为根）；环/自环/跨 WS 拒；软删父 400；viewer 写 403；timeline `parent_changed`；FE 详情入口；CLI **1.62.0** `issue parent set|clear`；不改 E70 childProgress；无新 webhook 名；formula no-emit；不重开 E63–E77。

**Architecture:** 复用既有 `PUT /api/issues/{id}` `parent_issue_id` + `_validate_parent_issue_id`；update 时写 timeline `parent_changed`（alembic ADD VALUE，无新表）；软删父显式 400；FE 详情「设为子项 / 更换父 / 提升为根」；CLI nested `issue parent` group + pins 1.62.0。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E79；中文 docs；CLI **1.62.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：复用 PUT · JSON null 清父 · 软删父 400 · 无新 webhook · 无 max-depth · CLI `issue parent set|clear` 1.62.0
- **无新业务表**；仅 timeline enum ADD VALUE `parent_changed`
- formula 永不 emit；无 Activity Push；无门户/甘特；不改 E70 `childProgress` 计算；不改 E74 comment `parent_id`
- 不改 E63–E77 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search`（及序污染）记入 acceptance，不挡
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/alembic/versions/2026_11_05_5600-d7e8f9a0b1c2_timeline_parent_changed.py` | ADD VALUE `parent_changed` |
| `backend/opentask/models/issue/enums.py` | `TimelineAction.PARENT_CHANGED` |
| `backend/opentask/models/issue/model.py` | ENUM 字面量补 `parent_changed` |
| `backend/tests/conftest.py` | ADD VALUE `parent_changed` |
| `backend/opentask/services/issue_service.py` | 软删父拒；update 写 `parent_changed` timeline |
| `backend/tests/api/test_e78_issue_set_parent.py` | API TDD |
| `frontend/src/utils/issueParentMeta.ts` (+test) | 选择器排除 / toast 文案 |
| `frontend/src/views/issue/detail/index.vue` | 设为子项 / 换父 / 提升为根 |
| `frontend/src/service/api/issue.ts` | 已有 `updateIssue`；无新端点 |
| `agent-harness/opentask-cli/**` | 1.62.0 + `issue parent set\|clear` |
| `docs/superpowers/acceptances/2026-11-05-e78-issue-set-parent-convert-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e78-issue-set-parent-convert-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e78-issue-set-parent-convert-mid-acceptance.md
git commit -m "docs(E78): plan + acceptance skeleton"
```

---

### Task 2 — A：TimelineAction.PARENT_CHANGED + alembic（随 API 红测）

**Files:**
- Create: `backend/alembic/versions/2026_11_05_5600-d7e8f9a0b1c2_timeline_parent_changed.py`（down=`c6d7e8f9a0b1`）
- Modify: `enums.py`；`model.py` ENUM；`tests/conftest.py`

```python
# enums.py
PARENT_CHANGED = "parent_changed"  # E78：父子关系变更
```

Alembic：`ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS 'parent_changed'`（upgrade）；downgrade no-op。

- [ ] **Step 1–2:** 随 Task 3 落地；commit `feat(E78): timeline parent_changed enum + alembic`

---

### Task 3 — A：update_issue parent timeline + 软删父拒（TDD）

**Files:**
- Modify: `issue_service.py`（`_validate_parent_issue_id` + `update_issue`）
- Create: `backend/tests/api/test_e78_issue_set_parent.py`

**Interfaces（增量）:**
```python
async def _validate_parent_issue_id(...):
    # 既有：同 WS、禁自环、祖先环
    # E78 Q3a：若 id 仅在 include_deleted 下可见且 is_deleted →
    #   raise ValueError("不能将已删除的 Issue 设为父")
    # 仍不存在 → "父 Issue 不存在"

# update_issue 内，当 "parent_issue_id" in update_data 且 from!=to：
await self._add_timeline(
    issue_id=issue_id,
    action_type=TimelineAction.PARENT_CHANGED,
    user_id=user_id,
    action_data={"from": old_parent, "to": new_parent},  # to=None = 根
)
# 不 publish 新 webhook 事件名；不改 child_progress.py
```

**红测覆盖：**
1. set-parent A→B：`parent_issue_id` 更新；timeline 含 `parent_changed`（from/to）
2. clear：`parent_issue_id: null` → null；timeline to=null
3. 省略字段不改 parent；同值不写重复 timeline（或可写但 from==to 跳过）
4. 自环 / 祖先环 → 400；跨 WS 父 → 400
5. 软删父 → 400（Q3a，文案含「删除」）
6. viewer 写 → 403（若成员路由已有则复用既有成员校验）
7. spy：无 `issue.parent_changed` webhook 新名；`child_progress.py` 未被本 epic 改（验收文件断言 / git）
8. 不触 trash/links/duplicate/comment parent_id

- [ ] **Step 1:** 写红测 → FAIL
- [ ] **Step 2:** 实现 → 绿
- [ ] **Step 3:** commit `feat(E78): parent_changed timeline + reject deleted parent`

---

### Task 4 — B：FE 设为子项 / 提升为根 + vitest + f/r

**Files:**
- Create: `frontend/src/utils/issueParentMeta.ts` + `.test.ts`
- Modify: `frontend/src/views/issue/detail/index.vue`

**Helper:**
```ts
export function excludeSelfFromPicker(
  rows: { id: string }[],
  selfId: string
): { id: string }[];

export function canPromoteToRoot(parentIssueId: string | null | undefined): boolean;

export function setParentSuccessMessage(parentCode: string | null): string;
// parentCode null → 「已提升为根」；否则 「已设为 XXX 的子项」
```

- 详情 `issue-actions`：按钮「设为子项…」/「更换父」（有父时）→ NModal + NSelect filterable（`getIssues({ search })`；排除自身）
- 「提升为根」仅 `canPromoteToRoot`；`updateIssue({ parent_issue_id: null })`
- 成功：toast + `loadIssue` / `loadParentAndChildren`
- build 后确认 `routes/index.ts` 仍含 `/f/:token` + `/r/:token`

- [ ] TDD helper → FE 页 → vitest+build → commit `feat(E78): FE set-parent / promote-to-root`

---

### Task 5 — C：CLI 1.62.0

**Files:**
- Bump all pins 1.61.0 → 1.62.0（含历史 epic 版本断言；`sed`/批量替换）
- `core/issue.py`：`@issue_cli.group("parent")` + `set` / `clear`
- `tests/test_e78_issue_parent.py`

```
opentask issue parent set <issue> <parent> [--json]
opentask issue parent clear <issue> [--json]
```

实现：resolve code→id；`client.update_issue(id, parent_issue_id=parent_id|None)`；打印新 parent / null。

- [ ] 红测 version + help → 实现 → 绿 → commit `feat(E78): CLI 1.62.0 issue parent set|clear`

---

### Task 6 — Verify + acceptance

- Directed E78 BE；full BE；CLI；FE vitest+build
- 记门禁数 / flake；写 acceptance；tip SHA；`superpowers: design/plan/TDD/verify/acceptance = ok`
- **STOP** — 不 push / 不开 PR / 不自开 E79

