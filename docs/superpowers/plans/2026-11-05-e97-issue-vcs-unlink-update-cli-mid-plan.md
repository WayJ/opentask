# E97 Plan：Issue VCS unlink + update CLI mid · CLI 1.81.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`0f6248c`（全文 `0f6248cb3ae695e6ab8ed5ebe0ea8429b53d4743`；含 E97 design；E96 tip `d864818` ⊂ HEAD）· 分支 `sprint/E97-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E98**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** writer（既有会话鉴权）可用 CLI **1.81.0** 对 Issue VCS link 做 **unlink** 与 **update**；api_client 接线既有 `delete_issue_vcs_link` + **新增** `update_issue_vcs_link` → PATCH（camelCase）；复用既有 DELETE/PATCH `/api/issues/{id}/vcs/links/{link_id}`；保留既有 `branch-name`/`link-branch`/`link-pr`/`vcs-links`；空 update CLI 拒绝；**不**改 E79–E96 邻面；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；**不做**真 Git / OAuth2 / requirement-repos。

**Architecture:** 复用既有 BE DELETE + PATCH（Q1a）；CLI **扁平**补 `issue unlink-vcs`（别名 `vcs-unlink`）+ `issue update-vcs`（Q2a）；api_client PATCH 发 camelCase `branchName`/`prUrl`/`provider`/`externalId`/`status`/`title`（Q3a）；空 update 本地非零退出不发空 PATCH；human 薄回显 id/kind/status/url-or-branch；`--json` 全量（Q4a）；pins **1.81.0**（Q5a）；FE 零改（Q6a）。**不要**停 7377/9527。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E98；中文 docs；CLI **1.81.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · 扁平 `unlink-vcs`/`update-vcs` · camelCase PATCH · 空 update 拒绝 · pins 1.81.0 · 零产品 FE
- **不**改 E96 access-token / E95 project-repos / E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 health / E84 cycle / E83 watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead
- **不**改既有 `branch-name` / `link-branch` / `link-pr` / `vcs-links` 默认语义；**不**强制重组 `issue vcs` 子组
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特；**不做** OAuth2 / 真 Git / requirement-repos / Initiative health / bulk project_id / watching filter
- 守 E63 `f`+`r`（FE build 冲掉 imports → **必须 checkout 恢复**；收尾 `git status` 干净）；已知 flake `test_user_search` 记入 acceptance，不挡
- **不要**停 7377 后端或 9527 前端
- ISSUE_REF 经既有 `_resolve_issue_id`（issue_code / uuid）
- status 文档示例 `open|draft|merged|closed|unknown`；按现有 BE 语义透传（CLI 可不硬拦未知值）

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | 既有 delete；**新增** `update_issue_vcs_link` |
| `agent-harness/opentask-cli/opentask/core/issue.py` | 补 `unlink-vcs`（`vcs-unlink`）+ `update-vcs`（紧挨既有 VCS 命令） |
| VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` | pins **1.81.0** + 历史 epic 断言级联 `1.80.0`→`1.81.0` |
| `agent-harness/opentask-cli/tests/test_e97_issue_vcs_unlink_update.py` | CLI TDD directed |
| `agent-harness/opentask-cli/tests/test_issue_vcs_commands.py` | 可选增补 delete/update helper 契约（或并入 e97） |
| `backend/tests/api/test_e97_issue_vcs_unlink_update_cli_mid.py` | 邻面 spy + DELETE/PATCH 端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架（后填满，禁止留下 `_pending_`）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e97-issue-vcs-unlink-update-cli-mid-acceptance.md
git commit -m "docs(E97): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client `update_issue_vcs_link` + `unlink-vcs`/`update-vcs` + pins 1.81.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（紧挨既有 VCS helpers）
- Modify: `agent-harness/opentask-cli/opentask/core/issue.py`（在 `vcs-links` 命令之后追加）
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` / `opentask_cli.py` → **1.81.0**
- Cascade 历史 epic 测试里的 `1.80.0` → `1.81.0`
- Create: `agent-harness/opentask-cli/tests/test_e97_issue_vcs_unlink_update.py`

**Interfaces (api_client):**
```python
async def delete_issue_vcs_link(self, issue_id: str, link_id: str) -> dict:
    """Already exists — DELETE /api/issues/{id}/vcs/links/{link_id}."""
    return await self.delete(f"/api/issues/{issue_id}/vcs/links/{link_id}")

async def update_issue_vcs_link(self, issue_id: str, link_id: str, **kwargs) -> dict:
    """E97: PATCH /api/issues/{id}/vcs/links/{link_id}; kwargs camelCase
    (branchName, prUrl, provider, externalId, status, title)."""
    return await self.patch(
        f"/api/issues/{issue_id}/vcs/links/{link_id}", data=kwargs
    )
```

**CLI commands (`core/issue.py`, flat under `issue_cli`):**
- `unlink-vcs` + alias `vcs-unlink` via `issue_cli.add_command(..., name="vcs-unlink")`
- `update-vcs`
- 形状：
  - `opentask issue unlink-vcs ISSUE_REF LINK_ID [--json]`
  - `opentask issue update-vcs ISSUE_REF LINK_ID [--status STATUS] [--title TEXT] [--pr-url URL] [--branch-name NAME] [--provider PROVIDER] [--external-id ID] [--json]`
- ISSUE_REF → `_resolve_issue_id`
- update：收集非 None 字段 → camelCase kwargs；**若 fields 空** → `skin.error(...)` + `sys.exit(1)`（json_mode 时 `_format_json_response(success=False, ...)`），**不**调用 helper
- human unlink：薄回显 `Unlinked VCS link {id}`（或含 kind 若响应有）
- human update：薄回显 `id/kind/status` + `prUrl|branchName`
- `--json`：全量 data
- **不**改 `branch-name` / `link-branch` / `link-pr` / `vcs-links` 命令体

**Tests (at least):**
- pins 1.81.0（VERSION + pyproject + setup + `__init__` + `--version`）
- `delete_issue_vcs_link` 仍在；源码含 DELETE path
- **新增** `update_issue_vcs_link`；源码含 `self.patch` + `/vcs/links/`；kwargs 透传 camelCase（mock 断言 `branchName`/`prUrl`/`externalId`）
- `issue --help` 含 `unlink-vcs` / `update-vcs`；别名 `vcs-unlink` 可用（`--help` 或 invoke）
- 既有 `branch-name` / `link-branch` / `link-pr` / `vcs-links` help 仍绿
- unlink 调用 `delete_issue_vcs_link`（mock resolve + delete）
- update 调用 `update_issue_vcs_link` 且 body camelCase
- 空 update（无字段 flag）→ exit ≠ 0 且 **不**调 update helper
- update human 含 id/status；`--json` 含全量
- 邻面：`access-token --help` 仍含 list；`project repo --help` 仍含 list；`issue reaction --help` 仍含 list

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.80.0）
- [ ] **Step 3:** Implement helper + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E97): CLI 1.81.0 issue unlink-vcs|update-vcs`

---

### Task 3 — A：BE 邻面 spy + 既有 DELETE/PATCH 端点存在性

**Files:**
- Create: `backend/tests/api/test_e97_issue_vcs_unlink_update_cli_mid.py`

**Tests:**
- spy：`api/issue_vcs/router.py` 仍含：
  - `router = APIRouter(prefix="/api/issues"`
  - `@router.delete("/{issue_id}/vcs/links/{link_id}")` + `async def delete_link`
  - `@router.patch("/{issue_id}/vcs/links/{link_id}")` + `async def update_link`
  - `VcsLinkUpdate` 含 `branchName` / `prUrl` / `externalId` / `status` / `title` / `provider`
  - 既有 GET branch-name / GET+POST links 仍在
- **无**新 alembic 命名 e97；无新 initiative `/health`
- 邻面 markers 仍在（E96 access-tokens 三端点 · E95 repos 五端点 · E94 reactions · E93 display-prefs · E92 saved-views · E91 board/move · E90 initiatives projects · E89 CF reorder · E88 favorites reorder · E87 tag-groups · E86 replace_tags · E85 project health · E84 cycles · E83 project_watcher · E82 issue_templates · E81 milestone · E80 issue_project_move · E65 relations）
- formula no-emit soft guard
- **确认**未引入 requirement-repos CLI 绑定本 epic；未引入 `/api/repositories` git clone 新路由冒充本 epic

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E97): BE issue-vcs unlink+update mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e97_issue_vcs_unlink_update_cli_mid.py` + 既有 `test_issue_vcs*.py`（可选 smoke）
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e97 + 既有 `test_issue_vcs_commands.py`）
- FE：零产品改动 → vitest smoke + production build；确认 `f`+`r`（若 build 冲掉 elegant imports → **checkout 恢复**）；收尾 `git status` 干净
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + 禁区 + superpowers 行；**勿留** `_pending_`/骨架）
- commit `docs(E97): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E98；不停 7377/9527

---

## Self-review
- Spec A–D / Q1a–Q6a / ADR D1–D6 均有对应任务
- 无 TBD/TODO 占位
- api_client 签名与 CLI 参数一致（PATCH camelCase；空 update 本地拒绝）
- 明确禁：新路由、改既有 link/list 语义、`issue vcs` 子组重组、OAuth2、真 Git、requirement-repos、push/PR/E98、停 7377/9527
