# E86 Plan：Label Set/Multi CLI mid · CLI 1.70.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`f8b1b27`（全文 `f8b1b27c806aa3b22688f8e6a34fc747aeee76df`；含 E86 design；E85 tip `5fa6e3b` ⊂ HEAD）· 分支 `sprint/E86-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e86-label-set-multi-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E87**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer+ 可用 CLI **1.70.0** 做 `label set`（PUT replace）、`label update`（PATCH tag）、attach/detach **多 `--tag-id`**（位置参数兼容）；api_client 有 `replace_issue_tags` / `update_tag`；可选 `label issue` 读路径；**不**改 E85 project-health / E84 cycle / E83 project-watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead 主表面；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；不重开 E63–E85。

**Architecture:** 复用既有 `PUT /api/issues/{id}/tags` + `PATCH /api/tags/{id}` + POST/DELETE attach（Q1a）；CLI `label set|update` + multi attach/detach（Q2a/Q4a）；空/`--clear` → `tag_ids=[]`（Q3a）；pins 1.70.0（Q5a）；FE 零改（Q6a）。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E87；中文 docs；CLI **1.70.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `label set|update` + multi · 空/`--clear` 清空 · 可重复 `--tag-id`+位置兼容 · pins 1.70.0 · 零产品 FE
- **不**改 project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members 主表面；**不**改既有 `label list|create|delete` 默认行为
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | `replace_issue_tags` / `update_tag`（既有 attach/detach/list_issue_tags 保留） |
| `agent-harness/opentask-cli/opentask/core/label.py` | `set` / `update` / multi attach·detach / 可选 `issue` |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.70.0** + 历史 epic 断言级联 |
| `agent-harness/opentask-cli/tests/test_e86_label_set_multi.py` | CLI TDD |
| `backend/tests/api/test_e86_label_set_multi_cli_mid.py` | 邻面 spy + 既有端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e86-label-set-multi-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e86-label-set-multi-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e86-label-set-multi-cli-mid-acceptance.md
git commit -m "docs(E86): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client helpers + label set/update/multi + pins 1.70.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Tags 段）
- Modify: `agent-harness/opentask-cli/opentask/core/label.py`
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.70.0**
- Cascade 历史 epic 测试里的 `1.69.0` → `1.70.0`
- Create: `agent-harness/opentask-cli/tests/test_e86_label_set_multi.py`

**Interfaces (api_client):**
```python
async def replace_issue_tags(self, issue_id: str, tag_ids: list[int]) -> dict:
    """E86: PUT /api/issues/{id}/tags — whole-set replace."""
    return await self.put(f"/api/issues/{issue_id}/tags", data={"tag_ids": tag_ids})

async def update_tag(
    self,
    tag_id: str | int,
    *,
    name: str | None = None,
    color: str | None = None,
    group_id: int | None = None,
    clear_group: bool = False,
) -> dict:
    """E86: PATCH /api/tags/{id}."""
    body: dict = {}
    if name is not None:
        body["name"] = name
    if color is not None:
        body["color"] = color
    if group_id is not None:
        body["group_id"] = group_id
    if clear_group:
        body["clear_group"] = True
    return await self.patch(f"/api/tags/{tag_id}", data=body)
```

**CLI commands:**
```python
@label_cli.command(name="set")
@click.argument("issue_ref")
@click.option("--ids", default=None, help="Comma-separated tag ids (replace); empty clears")
@click.option("--clear", is_flag=True, default=False, help="Clear all tags (PUT tag_ids=[])")
@click.option("--json", "as_json", is_flag=True)
def label_set(...):
    # require --ids or --clear; --clear or ids=="" → []; else parse ints
    # resolve issue → client.replace_issue_tags(iid, tag_ids)

@label_cli.command(name="update")
@click.argument("tag_id")
@click.option("--name", default=None)
@click.option("--color", default=None)
@click.option("--group-id", "group_id", type=int, default=None)
@click.option("--clear-group", is_flag=True, default=False)
@click.option("--json", "as_json", is_flag=True)
def label_update(...):
    # require at least one field; client.update_tag(...)

# attach/detach: keep positional tag_id optional when --tag-id given
@click.argument("issue_ref")
@click.argument("tag_id", required=False, default=None)
@click.option("--tag-id", "tag_ids_opt", multiple=True, help="Tag id (repeatable)")
# collect ids = [*tag_ids_opt]; if tag_id: prepend; require non-empty; loop attach/detach

@label_cli.command(name="issue")
@click.argument("issue_ref")
@click.option("--json", "as_json", is_flag=True)
def label_issue(...):
    # resolve → client.list_issue_tags(iid)
```

**Tests (at least):**
- `hasattr` `replace_issue_tags` / `update_tag`
- `label --help` 含 `set` / `update` / `issue`；attach/detach 仍在
- `label set ISSUE --ids 1,2,3 --json` → replace 被调且 tag_ids=[1,2,3]
- `label set ISSUE --clear` / `--ids ""` → tag_ids=[]
- `label set` 缺 `--ids`/`--clear` → exit ≠ 0
- `label update TAG --name X --color #fff --json` → update_tag 被调
- `label attach ISSUE --tag-id 1 --tag-id 2` → attach 两次
- `label attach ISSUE 9` 位置参数仍绿
- `label detach` 对称
- `label issue ISSUE --json` → list_issue_tags
- pins 1.70.0（VERSION + pyproject + setup + `__init__` + `--version`）

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helpers/commands / pins 仍 1.69.0）
- [ ] **Step 3:** Implement helpers + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E86): CLI 1.70.0 label set|update + multi attach/detach`

---

### Task 3 — A：BE 邻面 spy + 既有 tags/issue-tags 端点存在性

**Files:**
- Create: `backend/tests/api/test_e86_label_set_multi_cli_mid.py`

**Tests:**
- spy：`api/issue/router.py` 仍含 `replace_tags` / `add_tag` / `remove_tag` / `get_tags`；`api/tags/router.py` 仍含 `update_tag`；无 alembic 新文件命名 e86；邻面 markers 仍在（project health / cycles generate-upcoming / project_watcher enrich / issue_templates / milestone / issue_project_move）
- 附跑既有：`tests/api/test_tags.py`（若存在且稳）

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E86): BE label-set-multi mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e86_label_set_multi_cli_mid.py` + `test_tags.py`
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e86）
- FE：零产品改动 → vitest smoke + production build；确认 `frontend/src/router/routes/index.ts` 仍有 `/f/:token` + `/r/:token`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行）
- commit `docs(E86): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E87

---

## Self-review
1. Spec coverage：A 无新路由 + smoke；C set/update/multi + api_client + 1.70.0；B 零 FE；D 邻面不动；E 门禁 — 均有 task
2. Placeholder scan：无 TBD
3. Types：helpers 名 `replace_issue_tags` / `update_tag`；commands `set`/`update`/`issue`；pins 1.70.0 一致；`--tag-id` multiple + 位置兼容
