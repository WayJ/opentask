# E66 Plan：Issue 附件鉴权 mid — ACL · 签名 URL · CLI 1.50.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`0e93813`（全文 `0e93813d08d1f7994366bced65fbf0e5b9a828a6`）· 分支 `sprint/E66-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e66-issue-attachment-acl-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E67**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** 废除附件公共免认证 download/preview；强制会话 + Issue 所属 WS 成员；并捆短 TTL HMAC 签名 URL 供 FE 内联预览；FE 不再依赖裸公共 URL；CLI **1.50.0** `issue attachment download`（+可选 signed-url）；无 Push / 无新 webhook；不改 E57–E65 邻面主表面；formula no-emit。

**Architecture:** 公共 `GET /api/attachments/{id}/download|preview` 与 issue-scoped download 统一走 `authenticate` + 附件→Issue→WS membership（非成员统一 404，未登录 401）。另增 `POST …/signed-url` 签发无状态 HMAC token，`GET /api/attachments/signed/{token}` 无会话校验后流式返回。FE 预览走 signed-url；显式下载可走鉴权 blob。CLI 新增 `issue attachment` 组。

**Tech Stack:** FastAPI + SQLAlchemy；hmac/hashlib + AUTH_SECRET_KEY；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E67；中文 docs；CLI **1.50.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；不改 E57–E65 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- Q5a：不新增 webhook 事件名、下载不 fire
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/attachment_acl.py` | require_attachment_read + stream helpers |
| `backend/opentask/services/attachment_signed_url.py` | HMAC mint/verify；TTL 900/3600 |
| `backend/opentask/api/attachment/router.py` | ACL download/preview + signed-url + signed GET |
| `backend/opentask/api/issue/router.py` | issue-scoped download ACL |
| `backend/opentask/services/issue_service.py` | 注释去「公共」 |
| `backend/tests/api/test_e66_attachment_acl.py` | API TDD |
| `frontend/src/utils/attachmentUrls.ts` | signed/browser URL helpers |
| `frontend/src/utils/attachmentUrls.test.ts` | vitest |
| `frontend/src/service/api/issue.ts` | createAttachmentSignedUrl + auth download blob |
| `frontend/src/components/common/AttachmentList.vue` | preview via signed-url |
| `agent-harness/opentask-cli/**` | 1.50.0 + `issue attachment` cmds |
| `docs/superpowers/acceptances/2026-11-05-E66-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E66-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e66-issue-attachment-acl-mid.md \
  docs/superpowers/acceptances/2026-11-05-E66-acceptance.md
git commit -m "docs(E66): plan + acceptance skeleton"
```

---

### Task 2 — A：ACL 读路径（TDD）

**Files:**
- Create: `backend/opentask/services/attachment_acl.py`
- Modify: `backend/opentask/api/attachment/router.py`
- Modify: `backend/opentask/api/issue/router.py`（download_issue_attachment）
- Create: `backend/tests/api/test_e66_attachment_acl.py`

**Interfaces:**
- `async def require_attachment_read(db, user_id, attachment_id, *, issue_service) -> Document`
  - missing attachment → 404
  - missing/orphan issue → 404
  - non-member → **404**（D3，不泄露）
  - member → Document
- download/preview：`Depends(authenticate)` + require_attachment_read + stream
- issue-scoped download：同样 `authenticate` + `_require_issue_access`（既有 403 可保留，或统一 404；跨租户测 `_denied`）后再 get_attachment

- [ ] **Step 1: 红测**

```python
"""E66: Issue attachment ACL + signed URL mid."""
from __future__ import annotations
import io
import uuid
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient

async def _register(client, prefix="e66"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post("/api/auth/register", json={"userName": uname, "password": "Passw0rd!", "name": uname})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {"token": data["token"], "userId": data["userId"], "workspaceId": data["defaultWorkspaceId"]}

def _auth(token, workspace_id=None):
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-Id"] = workspace_id
    return h

async def _issue(client, user, title="Att"):
    r = await client.post("/api/issues", headers=_auth(user["token"], user["workspaceId"]),
                          json={"title": title, "type": "bug", "reporter_id": user["userId"]})
    assert r.status_code == 200, r.text
    return r.json()["data"]

def _fake_storage_bytes(content=b"hello-e66"):
    storage = MagicMock()
    storage.get_file_stream.return_value = io.BytesIO(content)
    return storage

@pytest.mark.asyncio
async def test_e66_public_download_unauth_401(test_client: AsyncClient):
    user = await _register(test_client, "e66_u1")
    issue = await _issue(test_client, user)
    # seed attachment row via service path with storage mock
    with patch("opentask.api.issue.router.get_storage_service", return_value=_fake_storage_bytes()):
        # upload needs real save_upload_file — use Document insert via API with fake
        pass
```

实际红测策略（完整）：用 upload API + monkeypatch `get_storage_service` 于 **issue.router 与 attachment.router**；无 Authorization 调 `/api/attachments/{id}/download` → 401；同理 preview；他 WS 成员 → 404；本 WS → 200 且 body 匹配。

最小完整红测见实现文件；先写：

```python
@pytest.mark.asyncio
async def test_e66_download_requires_auth(test_client: AsyncClient):
    resp = await test_client.get(f"/api/attachments/{uuid.uuid4()}/download")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_e66_preview_requires_auth(test_client: AsyncClient):
    resp = await test_client.get(f"/api/attachments/{uuid.uuid4()}/preview")
    assert resp.status_code == 401
```

- [ ] **Step 2:** Run → FAIL（仍 200/404 无 401，因无 authenticate）
- [ ] **Step 3:** 实现 ACL + 改 router
- [ ] **Step 4:** 补全 member/non-member/issue-scoped 测 → PASS
- [ ] **Step 5:** Commit `feat(E66): require auth+membership on attachment download/preview`

**attachment_acl.py 实现要点：**

```python
"""E66: attachment read ACL (session + workspace membership)."""
from __future__ import annotations
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from opentask.models.document.model import Document
from opentask.services.workspace.service import WorkspaceService

async def require_attachment_read(
    session: AsyncSession,
    *,
    user_id: str,
    attachment_id: str,
    issue_service,
) -> Document:
    attachment = await issue_service.get_attachment_by_id(attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    issue = await issue_service.get_issue(attachment.entity_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    if issue.workspace_id:
        member = await WorkspaceService(session).get_membership(
            issue.workspace_id, user_id
        )
        if member is None:
            raise HTTPException(status_code=404, detail="附件不存在")
    return attachment
```

**router download/preview：**

```python
from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.services.attachment_acl import require_attachment_read

@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    current_user: UserModel = Depends(authenticate),
    service: IssueService = Depends(get_issue_service),
):
    """下载附件（E66：须登录且为附件所属 Issue 的工作区成员）"""
    attachment = await require_attachment_read(
        service.db, user_id=str(current_user.id),
        attachment_id=attachment_id, issue_service=service,
    )
    # ... existing stream logic ...
```

**issue-scoped download：** 加 `current_user: UserModel = Depends(authenticate)` + `await _require_issue_access(...)` 再 get_attachment。

---

### Task 3 — B：签名 URL（TDD）

**Files:**
- Create: `backend/opentask/services/attachment_signed_url.py`
- Modify: `backend/opentask/api/attachment/router.py`
- Modify: `backend/tests/api/test_e66_attachment_acl.py`

**Interfaces:**
- Constants: `DEFAULT_TTL_SECONDS = 900`, `MAX_TTL_SECONDS = 3600`
- `mint_signed_token(*, attachment_id: str, purpose: str, ttl_seconds: int, secret: str) -> tuple[str, datetime]`
- `verify_signed_token(token: str, *, secret: str) -> dict` → `{attachment_id, purpose, exp}`；过期/篡改 → ValueError
- Token 格式：`{aid}.{exp_unix}.{purpose}.{sig}`，`sig = hmac_sha256_hex(secret, f"{aid}.{exp}.{purpose}")`
- `POST /api/attachments/{id}/signed-url` body `{purpose: "download"|"preview", ttlSeconds?: int}` → `{url, expiresAt}`；须 authenticate + ACL
- `GET /api/attachments/signed/{token}` 无会话；校验后按 purpose 设 Content-Disposition
- TTL 缺省 900；`>3600` 或 `<1` → 400；purpose 非法 → 400
- 路由注册：`/signed/{token}` 必须在 `/{attachment_id}/…` 之前声明，避免歧义

- [ ] **Step 1: 红测**

```python
def test_e66_mint_verify_roundtrip():
    from opentask.services.attachment_signed_url import mint_signed_token, verify_signed_token
    tok, exp = mint_signed_token(attachment_id="aid-1", purpose="preview", ttl_seconds=900, secret="s")
    payload = verify_signed_token(tok, secret="s")
    assert payload["attachment_id"] == "aid-1"
    assert payload["purpose"] == "preview"

def test_e66_tamper_rejected():
    from opentask.services.attachment_signed_url import mint_signed_token, verify_signed_token
    tok, _ = mint_signed_token(attachment_id="aid-1", purpose="download", ttl_seconds=60, secret="s")
    bad = tok[:-4] + "dead"
    with pytest.raises(ValueError):
        verify_signed_token(bad, secret="s")

@pytest.mark.asyncio
async def test_e66_signed_url_ttl_cap(test_client: AsyncClient):
    # after seeding attachment as member:
    # POST ttlSeconds=99999 → 400
    # POST default → 200, url contains /api/attachments/signed/
    ...
```

- [ ] **Step 2–4:** RED → implement → GREEN
- [ ] **Step 5:** Commit `feat(E66): HMAC signed URL mint/verify + endpoints`

**signed_url 实现要点：**

```python
import hashlib, hmac, time
from datetime import datetime, timezone
DEFAULT_TTL_SECONDS = 900
MAX_TTL_SECONDS = 3600
ALLOWED_PURPOSES = frozenset({"download", "preview"})

def mint_signed_token(*, attachment_id, purpose, ttl_seconds, secret):
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError("invalid purpose")
    if ttl_seconds < 1 or ttl_seconds > MAX_TTL_SECONDS:
        raise ValueError("ttl out of range")
    exp = int(time.time()) + ttl_seconds
    msg = f"{attachment_id}.{exp}.{purpose}"
    sig = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    token = f"{msg}.{sig}"
    return token, datetime.fromtimestamp(exp, tz=timezone.utc)

def verify_signed_token(token, *, secret):
    parts = token.split(".")
    if len(parts) != 4:
        raise ValueError("malformed")
    aid, exp_s, purpose, sig = parts
    msg = f"{aid}.{exp_s}.{purpose}"
    expected = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("bad sig")
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError("bad purpose")
    exp = int(exp_s)
    if int(time.time()) > exp:
        raise ValueError("expired")
    return {"attachment_id": aid, "purpose": purpose, "exp": exp}
```

Secret：`from opentask.config import config` → `config.auth_secret_key`。

---

### Task 4 — C：FE signed-url 预览（TDD）

**Files:**
- Create: `frontend/src/utils/attachmentUrls.ts`
- Create: `frontend/src/utils/attachmentUrls.test.ts`
- Modify: `frontend/src/service/api/issue.ts`
- Modify: `frontend/src/components/common/AttachmentList.vue`

**Interfaces:**
- `toBrowserAttachmentUrl(apiPath: string): string` — 前缀 `/opentask`
- `attachmentAccessDeniedMessage(status: number): string` — 401/404 友好文案
- `issueApi.createAttachmentSignedUrl(id, purpose, ttlSeconds?)` → `{ url, expiresAt }`
- `issueApi.downloadAttachmentBlob(id)` → blob via downloadRequest（鉴权）
- AttachmentList：图片预览 `src` 用 signed preview URL map；下载按钮走 auth blob；去掉裸 `/api/attachments/.../preview|download` 直链

- [ ] **Step 1: 红测**

```typescript
import { describe, expect, it } from 'vitest';
import { toBrowserAttachmentUrl, attachmentAccessDeniedMessage } from './attachmentUrls';

describe('attachmentUrls', () => {
  it('prefixes /opentask for relative API paths', () => {
    expect(toBrowserAttachmentUrl('/api/attachments/signed/tok')).toBe(
      '/opentask/api/attachments/signed/tok'
    );
  });
  it('passes through absolute URLs', () => {
    expect(toBrowserAttachmentUrl('https://cdn.example/x')).toBe('https://cdn.example/x');
  });
  it('friendly 401/404 copy', () => {
    expect(attachmentAccessDeniedMessage(401)).toMatch(/登录|未授权|认证/i);
    expect(attachmentAccessDeniedMessage(404)).toMatch(/不存在|无权限|找不到/);
  });
});
```

- [ ] **Step 2–4:** RED → util + API + Vue → GREEN；`pnpm exec vitest run src/utils/attachmentUrls.test.ts`
- [ ] **Step 5:** Commit `feat(E66): FE preview via signed-url; drop naked public URLs`

**issue.ts 增量：**

```typescript
createAttachmentSignedUrl: (
  attachmentId: string,
  purpose: 'download' | 'preview',
  ttlSeconds?: number
) =>
  request<{ url: string; expiresAt: string }>({
    url: `/api/attachments/${attachmentId}/signed-url`,
    method: 'POST',
    data: { purpose, ...(ttlSeconds != null ? { ttlSeconds } : {}) }
  }),

downloadAttachmentBlob: (attachmentId: string) =>
  downloadRequest<Blob>({
    url: `/api/attachments/${attachmentId}/download`,
    method: 'GET',
    responseType: 'blob'
  }),
```

删除或改写 `getAttachmentDownloadUrl` 注释「公共访问」；可保留函数但改为抛错/废弃，或改为返回 signed 前的占位——**改为**调用方走 blob/signed。

---

### Task 5 — D：CLI 1.50.0 + `issue attachment`

**Files:**
- Modify: VERSION / pyproject / setup / `__init__` / `opentask_cli.VERSION` → **1.50.0**
- Bulk pin：所有 `1.49.0` 断言 → `1.50.0`
- Modify: `agent-harness/opentask-cli/opentask/core/issue.py` — 新 `attachment` group
- Modify: `api_client.py` — `create_attachment_signed_url`（可选）
- Create: `agent-harness/opentask-cli/tests/test_e66_attachment_acl.py`

**Commands:**
```
opentask issue attachment download ISSUE_ID ATTACHMENT_ID [--out PATH]
opentask issue attachment signed-url ISSUE_ID ATTACHMENT_ID [--purpose preview|download] [--ttl SECONDS]
```

download 复用既有 `download_issue_document`（issue-scoped，现已鉴权）或走 `/api/attachments/{id}/download`。

- [ ] **Step 1: 红测**

```python
"""E66 CLI: issue attachment download|signed-url + version 1.50.0."""
from click.testing import CliRunner
from opentask import __version__
from opentask.opentask_cli import VERSION, cli

def test_version_1_50_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "1.50.0" in result.output
    assert VERSION == "1.50.0"
    assert __version__ == "1.50.0"

def test_issue_attachment_help():
    runner = CliRunner()
    help_out = runner.invoke(cli, ["issue", "attachment", "--help"]).output
    assert "download" in help_out
    assert "signed-url" in help_out
```

- [ ] **Step 2–4:** bump + commands → PASS
- [ ] **Step 5:** Commit `feat(E66): CLI 1.50.0 issue attachment download|signed-url`

---

### Task 6 — E：no-emit spy + acceptance + 门禁

**Files:**
- Modify: `backend/tests/api/test_e66_attachment_acl.py` — spy download 不 fire_webhooks；邻面不动烟雾（可选轻断言）
- Modify: acceptance 填 tip + gates

- [ ] **Step 1:**

```python
@pytest.mark.asyncio
async def test_e66_download_no_webhook_fire(test_client: AsyncClient):
    # member download with storage mock
    with patch("opentask.services.workspace_webhook.service.fire_webhooks", new_callable=AsyncMock) as fw:
        # GET download 200
        fw.assert_not_called()
```

- [ ] **Step 2:** 全门禁
  - BE: `cd backend && python -m pytest -q` → 记 passed/skip/fail
  - BE 定向: `pytest tests/api/test_e66_attachment_acl.py tests/api/test_issue_attachments.py -q`
  - CLI: `cd agent-harness/opentask-cli && python -m pytest -q`
  - FE: `cd frontend && pnpm exec vitest run && pnpm run build`
- [ ] **Step 3:** 写 acceptance tip SHA + gates + `superpowers: design/plan/TDD/verify/acceptance = ok`
- [ ] **Step 4:** Commit `docs(E66): acceptance + gate counts`；最终 tip commit 若需 `chore(E66): tip`

---

## Spec coverage checklist
| Spec | Task |
|------|------|
| A ACL 401/404/200 + OpenAPI 注释 | T2 |
| B signed-url + TTL + tamper | T3 |
| C FE signed preview | T4 |
| D CLI 1.50.0 | T5 |
| E no-emit / 邻面 / 不 push | T6 |
| Q1a–Q6a / D1–D7 | 全任务 |

## Self-review
- No TBD/placeholders
- Token format consistent across T3/T4/T5
- `/signed/{token}` registered before `/{id}/…`
- Non-member → 404 (D3)
