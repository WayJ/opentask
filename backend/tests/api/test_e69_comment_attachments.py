"""E69: comment attachments mid — issue_comment Documents + ACL reuse."""
from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select


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


async def _issue(client: AsyncClient, user: dict, title: str = "E69") -> dict:
    r = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": title, "type": "bug", "reporter_id": user["userId"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


async def _comment(client: AsyncClient, user: dict, issue_id: str, content: str = "hi") -> dict:
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
        stored = f"{subdir}/{uuid.uuid4().hex}_{upload_file.filename or 'f.bin'}".replace(
            "//", "/"
        )
        self.root_files[stored] = data
        return stored, upload_file.filename or "f.bin", len(data)

    def get_file_stream(self, path):
        return io.BytesIO(self.root_files.get(path, self.content))

    def delete_file(self, path):
        self.deleted.append(path)
        self.root_files.pop(path, None)


async def _upload_comment_att(
    client: AsyncClient,
    user: dict,
    issue_id: str,
    comment_id: str,
    storage: _FakeStorage,
    content: bytes = b"payload-e69",
    filename: str = "a.txt",
) -> str:
    storage.content = content
    with patch("opentask.api.issue.router.get_storage_service", return_value=storage):
        resp = await client.post(
            f"/api/issues/{issue_id}/comments/{comment_id}/attachments",
            headers=_auth(user["token"], user["workspaceId"]),
            files={"file": (filename, content, "text/plain")},
        )
    assert resp.status_code == 200, resp.text
    aid = resp.json()["data"]["id"]
    listed = await client.get(
        f"/api/issues/{issue_id}/comments/{comment_id}/attachments",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    row = next(r for r in listed.json()["data"] if r["id"] == aid)
    storage.root_files[row["file_path"]] = content
    return aid


@pytest.mark.asyncio
async def test_e69_upload_list_scoped_to_comment(test_client: AsyncClient):
    user = await _register(test_client, "e69_u")
    issue = await _issue(test_client, user)
    c1 = await _comment(test_client, user, issue["id"], "c1")
    c2 = await _comment(test_client, user, issue["id"], "c2")
    storage = _FakeStorage()
    aid = await _upload_comment_att(test_client, user, issue["id"], c1["id"], storage)
    h = _auth(user["token"], user["workspaceId"])
    listed = await test_client.get(
        f"/api/issues/{issue['id']}/comments/{c1['id']}/attachments", headers=h
    )
    assert listed.status_code == 200
    assert any(r["id"] == aid for r in listed.json()["data"])
    assert all(r.get("entity_type") == "issue_comment" for r in listed.json()["data"])
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
    aid = await _upload_comment_att(
        test_client, owner, issue["id"], c["id"], storage, content=b"secret-e69"
    )
    h = _auth(owner["token"], owner["workspaceId"])
    with patch("opentask.api.attachment.router.get_storage_service", return_value=storage):
        ok = await test_client.get(f"/api/attachments/{aid}/download", headers=h)
        assert ok.status_code == 200
        assert ok.content == b"secret-e69"
        pv = await test_client.get(f"/api/attachments/{aid}/preview", headers=h)
        assert pv.status_code == 200
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
    await _upload_comment_att(
        test_client, user, issue["id"], c["id"], storage, filename="note.txt"
    )
    h = _auth(user["token"], user["workspaceId"])
    listed = await test_client.get(f"/api/issues/{issue['id']}/comments", headers=h)
    assert listed.status_code == 200
    rows = listed.json()["data"]["rows"]
    target = next(r for r in rows if r["id"] == c["id"])
    assert "attachments" in target
    assert len(target["attachments"]) >= 1
    assert set(target["attachments"][0].keys()) >= {
        "id",
        "file_name",
        "file_size",
        "file_type",
    }


@pytest.mark.asyncio
async def test_e69_delete_comment_attachment(test_client: AsyncClient):
    user = await _register(test_client, "e69_del")
    issue = await _issue(test_client, user)
    c = await _comment(test_client, user, issue["id"])
    storage = _FakeStorage()
    aid = await _upload_comment_att(test_client, user, issue["id"], c["id"], storage)
    h = _auth(user["token"], user["workspaceId"])
    with patch("opentask.api.issue.router.get_storage_service", return_value=storage):
        with patch(
            "opentask.services.issue_service.get_storage_service", return_value=storage
        ):
            resp = await test_client.delete(
                f"/api/issues/{issue['id']}/comments/{c['id']}/attachments/{aid}",
                headers=h,
            )
    assert resp.status_code == 200, resp.text
    listed = await test_client.get(
        f"/api/issues/{issue['id']}/comments/{c['id']}/attachments", headers=h
    )
    assert listed.json()["data"] == []


@pytest.mark.asyncio
async def test_e69_signed_url_works_for_comment_attachment(test_client: AsyncClient):
    user = await _register(test_client, "e69_sig")
    issue = await _issue(test_client, user)
    c = await _comment(test_client, user, issue["id"])
    storage = _FakeStorage(b"signed-e69")
    aid = await _upload_comment_att(
        test_client, user, issue["id"], c["id"], storage, content=b"signed-e69"
    )
    h = _auth(user["token"], user["workspaceId"])
    mint = await test_client.post(
        f"/api/attachments/{aid}/signed-url",
        headers=h,
        json={"purpose": "preview"},
    )
    assert mint.status_code == 200, mint.text
    url = mint.json()["data"]["url"]
    assert url.startswith("/api/attachments/signed/")
    with patch("opentask.api.attachment.router.get_storage_service", return_value=storage):
        got = await test_client.get(url)
    assert got.status_code == 200
    assert got.content == b"signed-e69"


@pytest.mark.asyncio
async def test_e69_soft_delete_comment_keeps_documents(test_client: AsyncClient):
    user = await _register(test_client, "e69_soft")
    issue = await _issue(test_client, user)
    c = await _comment(test_client, user, issue["id"])
    storage = _FakeStorage(b"keep-e69")
    aid = await _upload_comment_att(
        test_client, user, issue["id"], c["id"], storage, content=b"keep-e69"
    )
    h = _auth(user["token"], user["workspaceId"])
    deleted = await test_client.delete(f"/api/issues/comments/{c['id']}", headers=h)
    assert deleted.status_code == 200, deleted.text
    with patch("opentask.api.attachment.router.get_storage_service", return_value=storage):
        ok = await test_client.get(f"/api/attachments/{aid}/download", headers=h)
    assert ok.status_code == 200
    assert ok.content == b"keep-e69"


@pytest.mark.asyncio
async def test_e69_hard_delete_comment_cascades_documents(test_client: AsyncClient):
    from opentask.models.document.model import Document
    from opentask.repositories.base import SessionCreator
    from opentask.services.issue_service import IssueService

    user = await _register(test_client, "e69_hard")
    issue = await _issue(test_client, user)
    c = await _comment(test_client, user, issue["id"])
    storage = _FakeStorage(b"gone-e69")
    aid = await _upload_comment_att(
        test_client, user, issue["id"], c["id"], storage, content=b"gone-e69"
    )

    async with SessionCreator() as session:
        svc = IssueService(session)
        with patch(
            "opentask.services.issue_service.get_storage_service", return_value=storage
        ):
            ok = await svc.hard_delete_comment(c["id"], user["userId"])
        assert ok is True
        row = await session.execute(select(Document).where(Document.id == aid))
        assert row.scalar_one_or_none() is None
    assert any(storage.deleted), "expected MinIO delete_file cascade"


@pytest.mark.asyncio
async def test_e69_upload_no_new_webhook_event_names(test_client: AsyncClient):
    user = await _register(test_client, "e69_spy")
    issue = await _issue(test_client, user)
    c = await _comment(test_client, user, issue["id"])
    storage = _FakeStorage()
    with patch(
        "opentask.services.issue_service.fire_webhooks", new_callable=AsyncMock
    ) as fw:
        with patch("opentask.api.issue.router.get_storage_service", return_value=storage):
            resp = await test_client.post(
                f"/api/issues/{issue['id']}/comments/{c['id']}/attachments",
                headers=_auth(user["token"], user["workspaceId"]),
                files={"file": ("spy.txt", b"s", "text/plain")},
            )
        assert resp.status_code == 200, resp.text
        blob = " ".join(str(c) for c in fw.call_args_list)
        assert "comment.attachment" not in blob
        for call in fw.call_args_list:
            et = call.kwargs.get("event_type")
            if et is None and len(call.args) >= 3:
                et = call.args[2] if isinstance(call.args[2], str) else call.kwargs.get(
                    "event_type"
                )
            if et:
                assert et not in {
                    "comment.attachment_added",
                    "comment.attachment_removed",
                    "attachment.comment_added",
                }
