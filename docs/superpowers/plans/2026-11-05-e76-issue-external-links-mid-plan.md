# E76 Plan：Issue 外链 mid — issue_links · CLI 1.60.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`83273b4`（全文 `83273b451265c876d3e53253d8ec334f6252dbd3`；含 E76 design；E75 tip `6de4382` ⊂ HEAD）· 分支 `sprint/E76-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e76-issue-external-links-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E77**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** member+ 对可见 Issue 增删改查外链（url + 可选 title）；viewer+ 只读；`issue_links` 表 + CRUD API；详情「链接」区；CLI **1.60.0** `issue link list|add|rm`；timeline 仅 add/remove；无新 webhook；formula no-emit；≠ 附件/VCS/IssueRelation；不重开 E63–E75。

**Architecture:** 镜像 `IssueVcsLink` 栈：独立 model `IssueLink` + service（URL 校验 / 上限 50 / position 追加）+ router under `/api/issues/{id}/links`；timeline 经 `IssueService._add_timeline`；FE 详情卡 + hostname helper；CLI group `issue link` + pins 1.60.0。不复用附件存储 / VCS / relations。

**Tech Stack:** FastAPI + SQLAlchemy + alembic；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E77；中文 docs；CLI **1.60.0**（`VERSION`/`pyproject.toml`/`setup.py`/`opentask/__init__.py`/`opentask_cli.VERSION` 全钉）
- ADR D1–D6；Q1a–Q6a 全关（不得改）
- formula 永不 emit；无 Activity Push；无门户/甘特
- 不改 E63–E75 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- 非目标见 design §2
- 可选 `PUT .../links/reorder` **后置**（Q2a PATCH position 够用）

## File map
| Path | Role |
|------|------|
| `backend/alembic/versions/2026_11_05_5400-b5c6d7e8f9a0_issue_links.py` | alembic：`issue_links` + timeline enum `link_added`/`link_removed` |
| `backend/opentask/models/issue_link/model.py` (+`__init__.py`) | `IssueLink` ORM |
| `backend/opentask/models/__init__.py` | 注册 metadata |
| `backend/opentask/models/issue/enums.py` | `TimelineAction.LINK_ADDED/LINK_REMOVED` |
| `backend/opentask/models/issue/model.py` | ENUM 字面量补齐 |
| `backend/opentask/services/issue_link/service.py` | CRUD + URL 校验 + 上限 + serialize |
| `backend/opentask/api/issue_links/router.py` (+`__init__.py`) | GET/POST/PATCH/DELETE |
| `backend/opentask/app.py` | include_router |
| `backend/tests/conftest.py` | import IssueLink；ADD VALUE link_* |
| `backend/tests/unit/test_e76_issue_link_url.py` | URL 校验纯函数 |
| `backend/tests/api/test_e76_issue_links.py` | API TDD |
| `frontend/src/utils/issueLinkUrl.ts` (+test) | isHttpUrl / hostnameFromUrl |
| `frontend/src/service/api/issue-links.ts` | FE API |
| `frontend/src/views/issue/detail/index.vue` | 「链接」卡 |
| `agent-harness/opentask-cli/**` | 1.60.0 + `issue link *` |
| `docs/superpowers/acceptances/2026-11-05-e76-issue-external-links-mid-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: acceptance 骨架

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e76-issue-external-links-mid-plan.md \
  docs/superpowers/acceptances/2026-11-05-e76-issue-external-links-mid-acceptance.md
git commit -m "docs(E76): plan + acceptance skeleton"
```

---

### Task 2 — A：URL 校验纯函数（TDD）

**Files:**
- Create: `backend/opentask/services/issue_link/__init__.py`
- Create: `backend/opentask/services/issue_link/service.py`（先只放校验）
- Create: `backend/tests/unit/test_e76_issue_link_url.py`

**Interfaces:**
```python
MAX_LINKS_PER_ISSUE = 50
MAX_URL_LEN = 2048
MAX_TITLE_LEN = 255

def validate_http_url(url: str) -> str:
    """Q4a: strip; require http:// or https://; reject javascript:/relative/empty; max 2048.
    Returns normalized url. Raises ValueError with Chinese message.
    """
```

- [ ] **Step 1: 红测**

```python
"""E76: issue link URL validation (Q4a)."""
import pytest
from opentask.services.issue_link.service import validate_http_url

def test_https_ok():
    assert validate_http_url("https://figma.com/file/x") == "https://figma.com/file/x"

def test_http_ok_strips():
    assert validate_http_url("  http://example.com/a  ") == "http://example.com/a"

@pytest.mark.parametrize("bad", ["", "   ", "javascript:alert(1)", "/relative", "ftp://x", "notaurl", "https://"])
def test_rejects_bad(bad):
    # https:// alone may pass scheme check if we only check startswith —
    # require netloc via urlparse
    with pytest.raises(ValueError):
        validate_http_url(bad)
```

- [ ] **Step 2:** `pytest backend/tests/unit/test_e76_issue_link_url.py -v` → FAIL (import)

- [ ] **Step 3: 实现** — `urllib.parse.urlparse`；scheme ∈ {http,https}；netloc 非空；len≤2048

- [ ] **Step 4:** 绿 → commit `feat(E76): validate_http_url helper`

---

### Task 3 — A：alembic + IssueLink model + TimelineAction（TDD 随 API）

**Files:**
- Create: alembic `2026_11_05_5400-b5c6d7e8f9a0_issue_links.py`（down=`a4b5c6d7e8f9`）
- Create: `backend/opentask/models/issue_link/model.py` + `__init__.py`
- Modify: `models/__init__.py`；`enums.py`；`issue/model.py` ENUM；`tests/conftest.py`

**Model:**
```python
class IssueLink(DBModel):
    __tablename__ = "issue_links"
    id: str PK uuid
    workspace_id: FK workspaces CASCADE
    issue_id: FK issues CASCADE
    url: String(2048) required
    title: String(255) nullable
    position: Integer not null
    created_by: String(36) nullable
    created_at / updated_at
    __table_args__ = (
        Index("idx_issue_links_issue_position", "issue_id", "position"),
        Index("idx_issue_links_workspace_issue", "workspace_id", "issue_id"),
    )
```

**Alembic:** create table + indexes；`ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS 'link_added'|'link_removed'`

**Enums:** `LINK_ADDED = "link_added"`；`LINK_REMOVED = "link_removed"`；同步 SQLAlchemy ENUM 字面量；conftest ADD VALUE。

- [ ] **Step 1–4:** 随 Task 4 红测驱动；本任务可先落地 model/migration 再跑红测（表不存在时 API 红）。

- [ ] **Step 5:** commit `feat(E76): issue_links model + alembic + timeline enums`

---

### Task 4 — A：Service CRUD + API routes（TDD）

**Files:**
- Expand: `services/issue_link/service.py`（list/create/update/delete + serialize + require_writer）
- Create: `api/issue_links/router.py` + `__init__.py`
- Modify: `app.py` include_router
- Create: `backend/tests/api/test_e76_issue_links.py`

**Interfaces:**
```python
def serialize_issue_link(row: IssueLink) -> dict:  # camelCase

class IssueLinkService:
    async def get_issue(self, *, workspace_id, issue_id) -> Issue  # 404
    async def list_links(self, *, workspace_id, issue_id) -> list[IssueLink]  # order by position ASC, created_at ASC
    async def create_link(self, *, workspace_id, issue_id, user_id, url, title=None) -> IssueLink
        # validate url; count>=50 → ValueError; position = max+1 or 0; timeline LINK_ADDED
    async def update_link(self, *, workspace_id, issue_id, link_id, url=None, title=None, position=None) -> IssueLink
        # title-only：无 timeline；url 变更可不记（Q5a 默认仅 add/remove）
    async def delete_link(self, *, workspace_id, issue_id, link_id, user_id) -> None
        # timeline LINK_REMOVED with action_data {link_id, url, title?}
```

**Routes** (`prefix=/api/issues`):
- GET `/{issue_id}/links` — viewer+
- POST — member+ body `{url, title?}`
- PATCH `/{issue_id}/links/{link_id}` — member+ `{url?, title?, position?}`
- DELETE — member+

Auth：`require_workspace_context`；写 `require_writer`；跨 WS / 缺 Issue → **404**。

**红测覆盖：**
1. POST 两条 → GET 顺序稳定（position 0,1）；title 空仍 200
2. 第 51 条 → 400
3. `javascript:alert(1)` / 相对路径 / 空 → 400
4. 跨 WS 404；viewer POST 403；viewer GET 200；member DELETE 200
5. timeline：add 后有 `link_added`；delete 后有 `link_removed`；PATCH 仅 title → 无新 timeline
6. spy：不写 `issue_vcs_links` / attachments / `issue_relations`；webhook 无新事件名（可选：不触发新名）
7. formula no-emit（无需触 formula）

- [ ] **Step 1:** 写红测 → FAIL
- [ ] **Step 2:** 实现 service + router → 绿
- [ ] **Step 3:** commit `feat(E76): issue links CRUD API + timeline`

---

### Task 5 — B：FE 链接区 + vitest

**Files:**
- Create: `frontend/src/utils/issueLinkUrl.ts` + `issueLinkUrl.test.ts`
- Create: `frontend/src/service/api/issue-links.ts`
- Modify: `frontend/src/views/issue/detail/index.vue`（附件卡旁「链接」卡）

**Helper:**
```ts
export function isHttpUrl(url: string): boolean;
export function hostnameFromUrl(url: string): string; // fallback raw
```

**UI：**
- 列表：title 或 hostname；点击新标签打开；编辑（url/title）；删除
- 添加：url 必填 + 可选 title；非法 url toast
- 空态：「添加设计稿、文档或仪表盘链接」

- [ ] **Step 1:** vitest 红 → 实现 helper 绿
- [ ] **Step 2:** API + 详情卡
- [ ] **Step 3:** vitest；build；若 elegant-router 误删 `f`+`r` 则还原
- [ ] **Step 4:** commit `feat(E76): FE issue links section + url helpers`

---

### Task 6 — C：CLI 1.60.0

**Files:**
- Pin: `VERSION` / `pyproject.toml` / `setup.py` / `opentask/__init__.py` / `opentask_cli.VERSION` → **1.60.0**
- Cascade: 所有历史 epic 测试里的 `1.59.0` 断言 → `1.60.0`
- Modify: `opentask/utils/api_client.py` — `list/add/update/rm_issue_links`
- Modify: `opentask/core/issue.py` — `@issue_cli.group(name="link")` + list/add/rm（可选 update）
- Create: `tests/test_e76_issue_links.py`

```bash
opentask issue link list <issue> [--json]
opentask issue link add <issue> <url> [--title …] [--json]
opentask issue link rm <issue> <link-id> [--json]
```

- [ ] **Step 1:** 红测 version pins + help
- [ ] **Step 2:** 实现 + 级联 pins
- [ ] **Step 3:** CLI 套件绿 → commit `feat(E76): CLI 1.60.0 issue link`

---

### Task 7 — Verify + Acceptance

- [ ] Directed: `pytest backend/tests/unit/test_e76_issue_link_url.py backend/tests/api/test_e76_issue_links.py -v`
- [ ] Full BE；CLI；FE vitest + `pnpm run build`
- [ ] 填 acceptance：tip SHA、门禁数、flake 说明、`superpowers: design/plan/TDD/verify/acceptance = ok`
- [ ] commit `docs(E76): acceptance`
- [ ] **STOP** — 不 push / 不开 PR / 不自开 E77

---

## Self-review
1. Spec A–E / Q1a–Q6a → Tasks 2–6 覆盖；reorder 端点后置符合 Q2a
2. 无 TBD/placeholder
3. Timeline 仅 add/remove；无新 webhook 名；≠ 附件/VCS/relations；CLI VERSION 文件必钉
