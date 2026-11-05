# E92 Plan：Saved View Write CLI mid · CLI 1.76.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`4df134a`（全文 `4df134a776dfc629c080091b73eefd4bf461f5f0`；含 E92 design；E91 tip `6acec05` ⊂ HEAD）· 分支 `sprint/E92-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e92-saved-view-write-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E93**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer+ 可用 CLI **1.76.0** 做 Saved View **create / update / delete / favorite / save-as**；api_client 五 helpers → 复用既有 `/api/saved-views` 写端点（请求体 **snake_case**）；list/show 可薄补 Favorite/Shared；**不**改 `view use`；**不**改 E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 health / E84 cycle / E83 watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；**不做** Initiative health/甘特 / Display prefs / bulk project_id；不重开 E63–E91。

**Architecture:** 复用既有 POST/PATCH/DELETE + `/{id}/favorite` + `/{id}/save-as`（Q1a）；挂既有 `view` 组补五写命令，保留 list/show/use（Q2a）；api_client 发 **snake_case** `is_favorite`/`is_shared`/`filter`…（Q3a）；list/show 薄补 Favorite/Shared，**不**改 use（Q4a）；pins 1.76.0（Q5a）；FE 零改（Q6a）。语义 = 既有 BE（writer；共享 favorite→403；save-as 个人副本）。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E93；中文 docs；CLI **1.76.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `view` 组写命令 · snake_case 请求 · list/show 可薄补、不改 use · pins 1.76.0 · 零产品 FE
- **不**改 E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / project-health / cycle / project-watchers / issue-template / milestone / `apply_project_move_integrity` / lead-members
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特；**不做** Initiative health CLI / 甘特 / Display prefs / bulk project_id
- 守 E63 `f`+`r`；已知 flake `test_user_search` 记入 acceptance，不挡
- **务必** api_client 发 **snake_case**（禁误用响应侧 camelCase `isFavorite`/`isShared` 作为请求唯一键）
- **不要**改 `view use` 默认行为

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | 五 write helpers（create/update/delete/set_favorite/save_as） |
| `agent-harness/opentask-cli/opentask/core/view.py` | `create|update|delete|favorite|save-as`；list/show 薄补 Favorite/Shared |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.76.0** + 历史 epic 断言级联 `1.75.0`→`1.76.0` |
| `agent-harness/opentask-cli/tests/test_e92_saved_view_write.py` | CLI TDD |
| `backend/tests/api/test_e92_saved_view_write_cli_mid.py` | 邻面 spy + saved-views write 端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e92-saved-view-write-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e92-saved-view-write-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e92-saved-view-write-cli-mid-acceptance.md
git commit -m "docs(E92): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client 五 helpers + `view` 写命令 + list/show 薄补 + pins 1.76.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（Saved Views 段追加五 helpers）
- Modify: `agent-harness/opentask-cli/opentask/core/view.py`（五写命令 + list/show Favorite/Shared）
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.76.0**
- Cascade 历史 epic 测试里的 `1.75.0` → `1.76.0`
- Create: `agent-harness/opentask-cli/tests/test_e92_saved_view_write.py`

**Interfaces (api_client):**
```python
async def create_saved_view(
    self,
    name: str,
    filter: dict | None = None,
    sort: dict | None = None,
    display: dict | None = None,
    is_favorite: bool | None = None,
    is_shared: bool | None = None,
) -> dict:
    body: dict = {"name": name, "filter": filter if filter is not None else {}}
    if sort is not None:
        body["sort"] = sort
    if display is not None:
        body["display"] = display
    if is_favorite is not None:
        body["is_favorite"] = bool(is_favorite)
    if is_shared is not None:
        body["is_shared"] = bool(is_shared)
    return await self.post("/api/saved-views", data=body)

async def update_saved_view(self, view_id: str, **kwargs) -> dict:
    # kwargs keys: name, filter, sort, display, is_favorite, is_shared (snake only)
    body = {k: v for k, v in kwargs.items() if v is not None and k in {
        "name", "filter", "sort", "display", "is_favorite", "is_shared"
    }}
    return await self.patch(f"/api/saved-views/{view_id}", data=body)

async def delete_saved_view(self, view_id: str) -> dict:
    return await self.delete(f"/api/saved-views/{view_id}")

async def set_saved_view_favorite(self, view_id: str, is_favorite: bool) -> dict:
    return await self.post(
        f"/api/saved-views/{view_id}/favorite",
        data={"is_favorite": bool(is_favorite)},
    )

async def save_as_saved_view(self, view_id: str, name: str | None = None) -> dict:
    body: dict = {}
    if name is not None:
        body["name"] = name
    return await self.post(f"/api/saved-views/{view_id}/save-as", data=body)
```

**CLI commands (view.py):**
- `view create --name NAME [--filter JSON] [--sort JSON] [--display JSON] [--favorite/--no-favorite] [--shared/--no-shared] [--json]`
- `view update <view_id> [--name …] [--filter …] [--sort …] [--display …] [--favorite/--no-favorite] [--shared/--no-shared] [--json]`
- `view delete <view_id> [--json]`
- `view favorite <view_id> --on|--off [--json]`（缺 --on/--off → 非零退出）
- `view save-as <view_id> [--name NAME] [--json]`
- 非法 JSON → `click.ClickException("JSON 无效: …")`（不打 BE）
- list 人类表列：`["ID", "Name", "Favorite", "Shared"]`
- show 人类 status_block 追加 Favorite / Shared
- **不**改 `view use`

**Tests (at least):**
- pins 1.76.0（VERSION + pyproject + setup + `__init__` + `--version`）
- 五 helpers 存在；源码含正确 method+path；body 含 `is_favorite`/`is_shared`；禁 `"isFavorite"`/`"isShared"` 作为请求键；create 用 `self.post`；update 用 `self.patch`；delete 用 `self.delete`
- `view --help` 含 `create|update|delete|favorite|save-as|list|show|use`
- create/update/delete/favorite/save-as 调用对应 helper（mock）
- favorite 缺 --on/--off → exit ≠ 0；`--on` → True；`--off` → False
- 非法 `--filter` JSON → exit ≠ 0 且不调 helper
- list/show human 含 Favorite（及 Shared）
- `view use --help` 仍在；use 行为断言仍打印 filter（回归）
- 邻面：`issue board-move` 仍在 help

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.75.0）
- [ ] **Step 3:** Implement helpers + commands + list/show 薄补 + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E92): CLI 1.76.0 saved view write`

---

### Task 3 — A：BE 邻面 spy + 既有 saved-views 写端点存在性

**Files:**
- Create: `backend/tests/api/test_e92_saved_view_write_cli_mid.py`

**Tests:**
- spy：`api/saved_views/router.py` 仍含 `@router.post("")` create、`@router.patch("/{view_id}")`、`@router.delete("/{view_id}")`、`@router.post("/{view_id}/favorite")`、`@router.post("/{view_id}/save-as")`；schema `is_favorite`/`is_shared` snake；**无** `isFavorite:`/`isShared:` 作为 model 字段
- **无**新 alembic 命名 e92；无新 initiative `/health`
- 邻面 markers 仍在（board/move · initiatives projects · CF reorder · favorites reorder · tag-groups · replace_tags · project health · cycles · project_watcher · issue_templates · milestone · issue_project_move · E65 relations）
- formula no-emit soft guard
- 附跑既有：`tests/api/test_saved_views.py` smoke

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E92): BE saved-view-write mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e92_saved_view_write_cli_mid.py` + `test_saved_views.py`
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e92）
- FE：零产品改动 → vitest smoke + production build；确认 `f`+`r`（若 build 冲掉 elegant imports → checkout 恢复）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + superpowers 行；**勿留** `_pending_`/骨架）
- commit `docs(E92): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E93

---

## Self-review
- Spec A–D / Q1a–Q6a / ADR D1–D6 均有对应任务
- 无 TBD/TODO 占位
- api_client 签名与 CLI 参数一致（snake_case body）
- 明确禁：改 use、新路由、initiative health、Display prefs、bulk project_id、push/PR/E93
