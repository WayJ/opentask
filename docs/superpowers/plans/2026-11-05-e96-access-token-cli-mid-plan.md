# E96 Plan：Access Token CLI mid · CLI 1.80.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`0f8b28f`（全文 `0f8b28f1a7f0afcce59bd4a5cd399f525f0180f1`；含 E96 design；E95 tip `2809068` ⊂ HEAD）· 分支 `sprint/E96-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e96-access-token-cli-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E97**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member（已鉴权）可用 CLI **1.80.0** 做 Access Token **list / create / revoke**；api_client 三 helpers → 复用既有三端点；create 一次性打印 `token`；仅显式 `--save` 才写本地 `config.access_token`；**不**改 E79–E95 邻面；**无**新 webhook/表/**无新 BE 路由**；formula no-emit；零产品 FE；**不做** OAuth2 client / 真 Git / requirement-repos；不改 `config set-access-token` 既有语义。

**Architecture:** 复用既有 `GET/POST/DELETE /api/access-tokens`（Q1a）；CLI **新顶层组** `access-token`（Q2a，与 `config set-access-token` 并存）；api_client create body `{name, description?}` snake_case（Q3a）；human list 薄表 id/name/token_prefix/expires_at/last_used_at；create 醒目一次打印完整 token +「仅此一次可见」；`--save` opt-in（Q3a/Q4a）；pins 1.80.0（Q5a）；FE 零改（Q6a）。**测试只用假 token** `vk_TEST_ONLY_NOT_A_REAL_TOKEN`。**不要**停 7377/9527。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E97；中文 docs；CLI **1.80.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关：无新路由 · `access-token list|create|revoke`（`rm`）· 仅 `--save` 写 config · human 薄表 + 一次明文 · pins 1.80.0 · 零产品 FE
- **不**改 E95 project-repos / E94 reactions / E93 display-prefs / E92 view write / E91 board-move / E90 initiative-projects / E89 CF reorder / E88 favorite / E87 tag-group / E86 set/multi / E85 health / E84 cycle / E83 watchers / E82 issue-templates / E81 milestones / E80 project-move / E79 lead
- **不**改 `config set-access-token` 既有语义（可交叉提示）
- 无新 webhook / 无新表 / 无 alembic / **无新 BE 路由**；formula 永不 emit；无 Activity Push / 无门户 / 无甘特；**不做** OAuth2 client CRUD / SSO / 真 Git / requirement-repos / PATCH rename/续期
- **禁止真实 token**：测试/文档/acceptance/日志仅用假值或 `<one-time-token>` 占位；隔离 HOME/config；默认 create **绝不**写 config
- 守 E63 `f`+`r`（FE build 冲掉 imports → **必须 checkout 恢复**；收尾 `git status` 干净）；已知 flake `test_user_search` 记入 acceptance，不挡
- **不要**停 7377 后端或 9527 前端
- 缺 `--name`（create）本地 Click 失败不打 BE

## File map
| Path | Role |
|------|------|
| `agent-harness/opentask-cli/opentask/utils/api_client.py` | 三 access-token helpers |
| `agent-harness/opentask-cli/opentask/core/access_token.py` | **新**顶层组 `access-token` list\|create\|revoke(+rm) |
| `agent-harness/opentask-cli/opentask/opentask_cli.py` | import + `cli.add_command`；VERSION → 1.80.0 |
| VERSION / pyproject / setup / `__init__` | pins **1.80.0** + 历史 epic 断言级联 `1.79.0`→`1.80.0` |
| `agent-harness/opentask-cli/tests/test_e96_access_token.py` | CLI TDD（fake token only） |
| `backend/tests/api/test_e96_access_token_cli_mid.py` | 邻面 spy + 三端点存在性 |
| `docs/superpowers/acceptances/2026-11-05-e96-access-token-cli-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架（后填满，禁止留下 `_pending_`）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e96-access-token-cli-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e96-access-token-cli-mid-acceptance.md
git commit -m "docs(E96): plan + acceptance skeleton"
```

---

### Task 2 — C：CLI api_client 三 helpers + `access-token` 顶层组 + pins 1.80.0（TDD）

**Files:**
- Modify: `agent-harness/opentask-cli/opentask/utils/api_client.py`（project-repos 段附近或独立 Access Token 段追加三 helpers）
- Create: `agent-harness/opentask-cli/opentask/core/access_token.py`
- Modify: `agent-harness/opentask-cli/opentask/opentask_cli.py`（import + add_command；VERSION）
- Modify: VERSION / pyproject.toml / setup.py / `__init__.py` → **1.80.0**
- Cascade 历史 epic 测试里的 `1.79.0` → `1.80.0`
- Create: `agent-harness/opentask-cli/tests/test_e96_access_token.py`

**Interfaces (api_client):**
```python
async def list_access_tokens(self) -> list | dict:
    """E96: GET /api/access-tokens (metadata only; never raw token)."""
    return await self.get("/api/access-tokens")

async def create_access_token(
    self, name: str, description: str | None = None
) -> dict:
    """E96: POST /api/access-tokens body {name, description?}."""
    body: dict = {"name": name}
    if description is not None:
        body["description"] = description
    return await self.post("/api/access-tokens", data=body)

async def delete_access_token(self, token_id: str) -> bool:
    """E96: DELETE /api/access-tokens/{token_id}."""
    await self.delete(f"/api/access-tokens/{token_id}")
    return True
```

**CLI commands (`core/access_token.py`):**
- `@click.group(name="access-token")` → `list|create|revoke`；`revoke` 兼 alias `rm`
- 形状：
  - `access-token list [--json]`
  - `access-token create --name NAME [--description TEXT] [--save] [--json]`
  - `access-token revoke TOKEN_ID [--json]`（别名 `rm`）
- `--name` required on create → 缺参本地 Click 失败，不打 BE
- human list：薄表 ID / Name / Prefix / Expires / Last Used；**绝不**打印 `token` 字段
- create human：醒目打印一次完整 token + 「仅此一次可见」提示；可交叉提示 `config set-access-token` / `--save`
- `--save`：仅当 flag 存在时 `config.access_token = token`（复用既有 setter）；默认不写/不覆盖
- `--json`：create 输出完整 data（含一次性 token）；list 输出 rows（元数据）
- 用户级 API（authenticate）；**不强制** `require_workspace_id`
- **不**改 `config set-access-token` 命令体

**Fake token（测试唯一允许值）:** `vk_TEST_ONLY_NOT_A_REAL_TOKEN`

**Tests (at least):**
- pins 1.80.0（VERSION + pyproject + setup + `__init__` + `--version`）
- 三 helpers 存在；源码含正确 method+path；POST body 键 name（+ optional description）；无 GET-by-id / update helper
- `opentask --help` / 顶层含 `access-token`；`config --help` 仍含 `set-access-token`
- `access-token --help` 含 list/create/revoke
- list/create/revoke/rm 调用对应 helper（mock）
- 缺 `--name` → exit ≠ 0 且不调 helper
- list human 含 id/name/token_prefix/expires；**不含**完整假 token 原文作为「token=」字段（list 响应本无 token）
- create 默认：**不**写 config.access_token（隔离 HOME；先设 sentinel 或 None，create 后不变）
- create `--save`：写入假 token 到临时 config
- create human 输出含假 token + 「仅此一次」类提示
- create `--json` 含 `token` 键
- 邻面：`project repo --help` 仍含 list；`issue reaction --help` 仍含 list；`display-prefs --help` 仍含 get/set

- [ ] **Step 1:** Write failing CLI tests
- [ ] **Step 2:** Run directed → FAIL（缺 helper/command / pins 仍 1.79.0）
- [ ] **Step 3:** Implement helpers + commands + pins cascade
- [ ] **Step 4:** PASS
- [ ] **Step 5:** commit `feat(E96): CLI 1.80.0 access-token list|create|revoke`

---

### Task 3 — A：BE 邻面 spy + 既有三 access-tokens 端点存在性

**Files:**
- Create: `backend/tests/api/test_e96_access_token_cli_mid.py`

**Tests:**
- spy：`api/access_token/__init__.py` 仍含：
  - `router = APIRouter(prefix="/api/access-tokens"`
  - `@router.post("")` + `async def create_access_token`
  - `@router.get("")` + `async def list_access_tokens`
  - `@router.delete("/{token_id}")` + `async def delete_access_token`
- **无**新 alembic 命名 e96；无新 initiative `/health`；无 OAuth2 client CLI 路由冒充 access-tokens
- 邻面 markers 仍在（E95 repos 五端点 · E94 reactions · E93 display-prefs · E92 saved-views · E91 board/move · E90 initiatives projects · E89 CF reorder · E88 favorites reorder · E87 tag-groups · E86 replace_tags · E85 project health · E84 cycles · E83 project_watcher · E82 issue_templates · E81 milestone · E80 issue_project_move · E65 relations）
- formula no-emit soft guard
- **确认**未引入 access-token PATCH/rename；未引入 requirement-repos / git clone 绑定本 epic

- [ ] **Step 1:** Write spy tests
- [ ] **Step 2–4:** 绿
- [ ] **Step 5:** commit `test(E96): BE access-token mid spy`

---

### Task 4 — E：门禁 + acceptance

- Directed BE：`test_e96_access_token_cli_mid.py`（+ 若有既有 access-token BE tests 则附跑）
- Full BE `pytest tests`（flake 记入）
- CLI suite（含 directed e96）
- FE：零产品改动 → vitest smoke + production build；确认 `f`+`r`（若 build 冲掉 elegant imports → **checkout 恢复**）；收尾 `git status` 干净
- 扫描本次 diff/文档：确认无真实 `vk_` 密钥（仅假值 / 占位）
- 写满 acceptance（tip SHA + 门禁数 + Q1a–Q6a + 安全确认 + superpowers 行；**勿留** `_pending_`/骨架）
- commit `docs(E96): acceptance`
- **STOP** — 不 push / 不开 PR / 不自开 E97；不停 7377/9527

---

## Self-review
- Spec A–D / Q1a–Q6a / ADR D1–D6 均有对应任务
- 无 TBD/TODO 占位
- api_client 签名与 CLI 参数一致（create 含 name + optional description；delete 按 id）
- 明确禁：新路由、OAuth2 client CRUD、真 Git、requirement-repos、改 set-access-token、默认写 config、真实 token 入库、push/PR/E97、停 7377/9527
