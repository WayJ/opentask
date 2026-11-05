# E69 Plan：评论附件 mid — issue_comment Documents · ACL 复用 · CLI 1.53.0

日期：2026-11-05（Asia/Shanghai）  
基线 tip：`a5d1a91`（全文 `a5d1a91e09884fe6c78b57aeb512be30a9e04a69`）· 分支 `sprint/E69-S1` · worktree `/workspace/opentask-worktrees/E11-S4`  
Yuri：**design ok，开写**（`docs/superpowers/specs/2026-11-05-e69-comment-attachments-mid-design.md`）

> **For agentic workers:** REQUIRED 本会话 inline 执行；**TDD**；频繁 commit；**禁止 push/PR**；**不自开 E70**。REQUIRED SUB-SKILL: executing-plans / test-driven-development / verification-before-completion。

**Goal:** WS writer+ 可在 Issue 评论上上传/列表/删除附件；viewer+ 可读（download/preview/signed-url）；`entity_type=issue_comment` 复用 documents；扩 E66 `require_attachment_read`；评论 list 嵌薄 attachments 摘要；FE 评论区上传+预览；CLI **1.53.0**；无新 webhook / Push / 门户 / 甘特 / Form 再开；formula no-emit；不改 E57–E68 邻面主表面。

**Architecture:** documents 多态挂 `issue_comment`；嵌套 CRUD `/api/issues/{issue_id}/comments/{comment_id}/attachments`；上传校验 comment.issue_id == path issue_id；`require_attachment_read` 识别 comment→父 Issue→WS；`get_attachment_by_id` 放开 entity_type 过滤以服务 signed-url；软删评论不扫文件，`hard_delete_comment` 级联 Document+MinIO；评论序列化 `attachments: [{id,file_name,file_size,file_type}]` cap 20；FE CommentsCard + detail activity 挂 AttachmentList（commentId）；CLI `issue comment attachment list|upload|download`。

**Tech Stack:** FastAPI + SQLAlchemy；Vue3/Naive + vitest；Click CLI；pytest/httpx。

## Global Constraints
- 本地 tip；禁止 push/PR；不自开 E70；中文 docs；CLI **1.53.0**
- ADR D1–D7；Q1a–Q6a 全关（不得改）
- formula 永不 emit；不改 E57–E68 邻面主表面（仅 CLI version pins）
- 已知 flake `test_user_search` 记入 acceptance，不挡
- Q5a：不新增 webhook 事件名
- 不把评论附件暴露给公开 `/r` 或 `/f`
- 非目标见 design §2

## File map
| Path | Role |
|------|------|
| `backend/opentask/services/attachment_acl.py` | 扩 issue_comment ACL |
| `backend/opentask/services/issue_service.py` | comment attachment CRUD + hard_delete cascade；get_attachment_by_id 放开 |
| `backend/opentask/api/issue/router.py` | 嵌套 attachments API + 评论 list 摘要 |
| `backend/opentask/models/issue/schema.py` | IssueCommentResponse.attachments |
| `backend/tests/api/test_e69_comment_attachments.py` | BE TDD |
| `frontend/src/utils/attachmentUrls.ts` (+test) | flattenCommentAttachments |
| `frontend/src/service/api/issue.ts` | comment attachment API |
| `frontend/src/components/common/AttachmentList.vue` | optional commentId |
| `frontend/src/views/issue/detail/components/CommentsCard.vue` | 上传+列表 |
| `frontend/src/views/issue/detail/index.vue` | activity 评论下挂附件 |
| `frontend/src/typings/api/issue.d.ts` | attachments? on IssueComment |
| `agent-harness/opentask-cli/**` | 1.53.0 + comment attachment cmds |
| `docs/superpowers/acceptances/2026-11-05-E69-acceptance.md` | acceptance |

---

### Task 1 — Docs 骨架

**Files:**
- Create: 本 plan
- Create: `docs/superpowers/acceptances/2026-11-05-E69-acceptance.md`（骨架）

- [ ] **Step 1:** 入库 plan + acceptance 骨架并 commit

```bash
git add docs/superpowers/plans/2026-11-05-e69-comment-attachments-mid.md \
  docs/superpowers/acceptances/2026-11-05-E69-acceptance.md
git commit -m "docs(E69): plan + acceptance skeleton"
```

---

### Task 2 — A/B：ACL 扩 issue_comment + 嵌套 CRUD（TDD）

**Files:**
- Modify: `backend/opentask/services/attachment_acl.py`
- Modify: `backend/opentask/services/issue_service.py`
- Modify: `backend/opentask/api/issue/router.py`
- Modify: `backend/opentask/models/issue/schema.py`
- Create: `backend/tests/api/test_e69_comment_attachments.py`

**Interfaces:**
- `get_attachment_by_id(attachment_id)` → Document where id=…（**不再**强制 `entity_type=issue`；保留 issue 与 issue_comment）
- `require_attachment_read`: if `entity_type=="issue"` → issue path（不变）；if `entity_type=="issue_comment"` → load IssueComment → parent Issue → WS member；else 404
- `get_comment_attachments(comment_id) -> List[Document]`
- `add_comment_attachment(issue_id, comment_id, …) -> Document`（校验 comment.issue_id==issue_id；entity_type=issue_comment；**不** fire 新 webhook；可不写 timeline 或写既有 ATTACHMENT_ADDED 带 commentId — 默认 **不**新事件名，timeline 可选带 comment_id）
- `delete_comment_attachment(issue_id, comment_id, attachment_id, user_id) -> bool`
- `hard_delete_comment(comment_id, user_id) -> bool`：物理删评论 + 级联 Document+MinIO（Q3a）；软删路径不变
- Routes:
  - `GET/POST /api/issues/{issue_id}/comments/{comment_id}/attachments`
  - `DELETE /api/issues/{issue_id}/comments/{comment_id}/attachments/{attachment_id}`
- Comment list：每评嵌 `attachments: [{id, file_name, file_size, file_type}]`，cap 20

- [ ] **Step 1: 红测**

```python
"""E69: comment attachments mid — issue_comment Documents + ACL reuse."""
from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e69"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-Id"] = workspace_id
    return h


async def _issue(client, user, title="E69"):
    r = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": title, "type": "bug", "reporter_id": user["userId"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def _comment(client, user, issue_id, content="hi"):
    r = await client.post(
        f"/api/issues/{issue_id}/comments",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"content": content},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


class _FakeStorage:
    def __init__(self, content: bytes = b"e69-bytes"):
        self.content = content
        self.root_files: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def save_upload_file(self, upload_file, subdir=""):
        data = await upload_file.read()
        stored = f"{subdir}/{uuid.uuid4().hex}_{upload_file.filename or 'f.bin'}".replace("//", "/")
        self.root_files[stored] = data
        return stored, upload_file.filename or "f.bin", len(data)

    def get_file_stream(self, path):
        return io.BytesIO(self.root_files.get(path, self.content))

    def delete_file(self, path):
        self.deleted.append(path)
        self.root_files.pop(path, None)


@pytest.mark.asyncio
async def test_e69_upload_list_scoped_to_comment(test_client: AsyncClient):
    user = await _register(test_client, "e69_u")
    issue = await _issue(test_client, user)
    c1 = await _comment(test_client, user, issue["id"], "c1")
    c2 = await _comment(test_client, user, issue["id"], "c2")
    storage = _FakeStorage()
    h = _auth(user["token"], user["workspaceId"])
    with patch("opentask.api.issue.router.get_storage_service", return_value=storage):
        up = await test_client.post(
            f"/api/issues/{issue['id']}/comments/{c1['id']}/attachments",
            headers=h,
            files={"file": ("a.txt", b"payload-e69", "text/plain")},
        )
    assert up.status_code == 200, up.text
    aid = up.json()["data"]["id"]
    listed = await test_client.get(
        f"/api/issues/{issue['id']}/comments/{c1['id']}/attachments", headers=h
    )
    assert listed.status_code == 200
    assert any(r["id"] == aid for r in listed.json()["data"])
    other = await test_client.get(
        f"/api/issues/{issue['id']}/comments/{c2['id']}/attachments", headers=h
    )
    assert other.status_code == 200
    assert other.json()["data"] == []


@pytest.mark.asyncio
async def test_e69_wrong_issue_comment_binding_404(test_client: AsyncClient):
    user = await _register(test_client, "e69_bind")
    i1 = await _issue(test_client, user, "I1")
    i2 = await _issue(test_client, user, "I2")
    c = await _comment(test_client, user, i1["id"])
    h = _auth(user["token"], user["workspaceId"])
    storage = _FakeStorage()
    with patch("opentask.api.issue.router.get_storage_service", return_value=storage):
        resp = await test_client.post(
            f"/api/issues/{i2['id']}/comments/{c['id']}/attachments",
            headers=h,
            files={"file": ("x.txt", b"x", "text/plain")},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_e69_download_acl_member_and_stranger(test_client: AsyncClient):
    owner = await _register(test_client, "e69_o")
    stranger = await _register(test_client, "e69_s")
    issue = await _issue(test_client, owner)
    c = await _comment(test_client, owner, issue["id"])
    storage = _FakeStorage(b"secret-e69")
    h = _auth(owner["token"], owner["workspaceId"])
    with patch("opentask.api.issue.router.get_storage_service", return_value=storage):
        up = await test_client.post(
            f"/api/issues/{issue['id']}/comments/{c['id']}/attachments",
            headers=h,
            files={"file": ("s.txt", b"secret-e69", "text/plain")},
        )
    aid = up.json()["data"]["id"]
    # sync path into storage for stream
    listed = await test_client.get(
        f"/api/issues/{issue['id']}/comments/{c['id']}/attachments", headers=h
    )
    row = next(r for r in listed.json()["data"] if r["id"] == aid)
    storage.root_files[row["file_path"]] = b"secret-e69"
    with patch("opentask.api.attachment.router.get_storage_service", return_value=storage):
        ok = await test_client.get(f"/api/attachments/{aid}/download", headers=h)
        assert ok.status_code == 200
        assert ok.content == b"secret-e69"
        deny = await test_client.get(
            f"/api/attachments/{aid}/download",
            headers=_auth(stranger["token"], stranger["workspaceId"]),
        )
        assert deny.status_code == 404
        unauth = await test_client.get(f"/api/attachments/{aid}/download")
        assert unauth.status_code == 401


@pytest.mark.asyncio
async def test_e69_comment_list_embeds_attachments_summary(test_client: AsyncClient):
    user = await _register(test_client, "e69_emb")
    issue = await _issue(test_client, user)
    c = await _comment(test_client, user, issue["id"])
    storage = _FakeStorage()
    h = _auth(user["token"], user["workspaceId"])
    with patch("opentask.api.issue.router.get_storage_service", return_value=storage):
        await test_client.post(
            f"/api/issues/{issue['id']}/comments/{c['id']}/attachments",
            headers=h,
            files={"file": ("note.txt", b"n", "text/plain")},
        )
    listed = await test_client.get(f"/api/issues/{issue['id']}/comments", headers=h)
    assert listed.status_code == 200
    rows = listed.json()["data"]["rows"]
    target = next(r for r in rows if r["id"] == c["id"])
    assert "attachments" in target
    assert len(target["attachments"]) >= 1
    assert set(target["attachments"][0].keys()) >= {"id", "file_name", "file_size", "file_type"}
```

- [ ] **Step 2:** Run → FAIL（404 on nested routes / ACL still assumes issue entity）

```bash
cd backend && python -m pytest tests/api/test_e69_comment_attachments.py -v --tb=short
```

- [ ] **Step 3: 实现**

`attachment_acl.py`:

```python
async def require_attachment_read(session, *, user_id, attachment_id, issue_service) -> Document:
    attachment = await issue_service.get_attachment_by_id(attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="附件不存在")

    if attachment.entity_type == "issue":
        issue = await issue_service.get_issue(attachment.entity_id)
    elif attachment.entity_type == "issue_comment":
        comment = await issue_service.get_comment_by_id(attachment.entity_id)
        if comment is None:
            raise HTTPException(status_code=404, detail="附件不存在")
        issue = await issue_service.get_issue(comment.issue_id)
    else:
        raise HTTPException(status_code=404, detail="附件不存在")

    if issue is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    if issue.workspace_id:
        member = await WorkspaceService(session).get_membership(issue.workspace_id, user_id)
        if member is None:
            raise HTTPException(status_code=404, detail="附件不存在")
    return attachment
```

`issue_service.py` 要点：
- `get_attachment_by_id`: drop `entity_type == "issue"` filter（或 `in_("issue","issue_comment")`）
- `get_comment_by_id(comment_id, *, include_deleted=False)`
- comment attachment CRUD as above；subdir `issues/{issue_id}/comments/{comment_id}`
- `hard_delete_comment`: load attachments for comment, delete_file each, delete Document rows, delete IssueComment row
- `get_comments_attachments_map(comment_ids, cap_per=20) -> dict[str, list[dict]]`

Router nested endpoints mirror issue attachment handlers with comment binding check.

Schema: add to `IssueCommentResponse`:
```python
attachments: Optional[List[dict]] = Field(default=None, description="E69 thin attachment summary")
```

- [ ] **Step 4: PASS + commit**

```bash
cd backend && python -m pytest tests/api/test_e69_comment_attachments.py tests/api/test_e66_attachment_acl.py -v
git add backend/opentask/services/attachment_acl.py backend/opentask/services/issue_service.py \
  backend/opentask/api/issue/router.py backend/opentask/models/issue/schema.py \
  backend/tests/api/test_e69_comment_attachments.py
git commit -m "feat(E69): comment attachments CRUD + ACL reuse"
```

---

### Task 3 — Q3a 硬删级联 + signed-url 回归 + webhook spy（TDD）

**Files:**
- Modify: `backend/tests/api/test_e69_comment_attachments.py`
- Modify: `backend/opentask/services/issue_service.py`（若未完成 hard_delete）

- [ ] **Step 1: 红测**

```python
@pytest.mark.asyncio
async def test_e69_hard_delete_comment_cascades_documents(test_client: AsyncClient, db_session):
    # upload then call service.hard_delete_comment; assert Document gone + storage.delete_file called
    ...

@pytest.mark.asyncio
async def test_e69_soft_delete_comment_keeps_documents(test_client: AsyncClient):
    # DELETE /api/issues/comments/{id} soft; attachment still downloadable by member
    ...

@pytest.mark.asyncio
async def test_e69_signed_url_works_for_comment_attachment(test_client: AsyncClient):
    # POST /api/attachments/{id}/signed-url → GET signed → 200
    ...

@pytest.mark.asyncio
async def test_e69_upload_no_new_webhook_event_names(test_client: AsyncClient):
    with patch("opentask.services.issue_service.fire_webhooks", new_callable=AsyncMock) as fw:
        # upload comment attachment
        forbidden = {"comment.attachment_added", "comment.attachment_removed", "attachment.comment_added"}
        for c in fw.call_args_list:
            et = c.kwargs.get("event_type") or (c.args[2] if len(c.args) > 2 else None)
            # also scan args
            blob = str(c)
            assert "comment.attachment" not in blob
```

- [ ] **Step 2–4:** implement hard_delete if needed → PASS → commit `feat(E69): hard-delete cascade + signed-url + no new webhook`

---

### Task 4 — C：FE CommentsCard + AttachmentList commentId + vitest

**Files:**
- Modify: `frontend/src/utils/attachmentUrls.ts`
- Modify: `frontend/src/utils/attachmentUrls.test.ts`
- Modify: `frontend/src/service/api/issue.ts`
- Modify: `frontend/src/typings/api/issue.d.ts`
- Modify: `frontend/src/components/common/AttachmentList.vue`
- Modify: `frontend/src/views/issue/detail/components/CommentsCard.vue`
- Modify: `frontend/src/views/issue/detail/index.vue`

**Interfaces:**
```typescript
export function flattenCommentAttachments(
  comments: Array<{ id: string; attachments?: Array<{ id: string; file_name: string; file_size: number; file_type: string }> | null }>
): Array<{ commentId: string; id: string; file_name: string; file_size: number; file_type: string }> {
  const out = [];
  for (const c of comments) {
    for (const a of c.attachments || []) {
      out.push({ commentId: c.id, id: a.id, file_name: a.file_name, file_size: a.file_size, file_type: a.file_type });
    }
  }
  return out;
}
```

`issueApi`:
- `getCommentAttachments(issueId, commentId)`
- `uploadCommentAttachment(issueId, commentId, {file})`
- `deleteCommentAttachment(issueId, commentId, attachmentId)`

`AttachmentList`: optional `commentId?: string`；when set, use comment APIs；preview still signed-url.

`CommentsCard`: show AttachmentList per comment；simple file input near editor that uploads after comment exists（或挂在已有评论下）。最小：每条评论下只读/可传 AttachmentList。

`index.vue` activity 评论块：在 reactions 下挂 `<AttachmentList :issue-id="issueId" :comment-id="comment.id" :attachments="mapSummary(comment.attachments)" @refresh="loadComments" />`。

- [ ] **Step 1: 红测** in `attachmentUrls.test.ts`
- [ ] **Step 2: FAIL → implement → PASS**
- [ ] **Step 3: commit** `feat(E69): FE comment attachments + flatten vitest`

---

### Task 5 — D：CLI 1.53.0 + `issue comment attachment`

**Files:**
- Bump all `1.52.0` → `1.53.0` under `agent-harness/opentask-cli`
- Modify: `opentask/core/issue.py` — `@comment_cli.group(name="attachment")` + list/upload/download
- Modify: `opentask/utils/api_client.py` — client methods
- Create: `tests/test_e69_comment_attachments.py`

```python
"""E69 CLI: issue comment attachment + version 1.53.0."""
from click.testing import CliRunner
from opentask import __version__
from opentask.opentask_cli import VERSION, cli

def test_version_1530():
    r = CliRunner().invoke(cli, ["--version"])
    assert r.exit_code == 0
    assert "1.53.0" in r.output
    assert VERSION == "1.53.0"
    assert __version__ == "1.53.0"

def test_comment_attachment_help():
    r = CliRunner().invoke(cli, ["issue", "comment", "attachment", "--help"])
    assert r.exit_code == 0
    assert "list" in r.output
    assert "upload" in r.output
    assert "download" in r.output
```

Client:
```python
async def list_comment_attachments(self, issue_id, comment_id):
    return await self.get(f"/api/issues/{issue_id}/comments/{comment_id}/attachments")

async def upload_comment_attachment(self, issue_id, comment_id, file_path):
    # multipart like upload_issue_document

async def download_comment_attachment(self, issue_id, comment_id, attachment_id, out_path):
    # may reuse download via /api/attachments/{id}/download or nested if added;
    # design: CLI download uses authenticated path — use /api/attachments/{aid}/download
```

- [ ] PASS + commit `feat(E69): CLI 1.53.0 comment attachment commands`

---

### Task 6 — E：门禁 + f/r + acceptance

```bash
cd backend && python -m pytest -q --tb=no 2>&1 | tee /tmp/e69-be.txt
cd agent-harness/opentask-cli && python -m pytest -q --tb=no 2>&1 | tee /tmp/e69-cli.txt
cd frontend && pnpm exec vitest run 2>&1 | tee /tmp/e69-fe.txt
cd frontend && pnpm run build 2>&1 | tee /tmp/e69-build.txt
# restore elegant-router f/r if dropped
```

Fill acceptance with tip SHA + gate counts；tip commit；**STOP**（不 push / 不开 E70）。

---

## Spec coverage self-check
| Spec | Task |
|------|------|
| A storage issue_comment | T2 |
| B nested CRUD + E66 ACL | T2–T3 |
| C list embed + FE + vitest | T2 embed + T4 |
| D CLI 1.53.0 | T5 |
| E tenant/no-emit/邻面/f+r | T3 spy + T6 |
| Q1a–Q6a / D1–D7 | 全任务 |
| 门禁 + acceptance | T6 |

## Placeholder scan
无 TBD / TODO / 「similar to」空洞步骤。
