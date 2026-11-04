"""E66: Issue attachment ACL + signed URL mid."""
from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e66"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
        "username": uname,
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _create_issue(client: AsyncClient, user: dict, title: str = "Att") -> dict:
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": title, "type": "bug", "reporter_id": user["userId"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


class _FakeStorage:
    def __init__(self, content: bytes = b"hello-e66"):
        self.content = content
        self.root_files: dict[str, bytes] = {}

    async def save_upload_file(self, upload_file, subdir=""):
        data = await upload_file.read()
        stored = f"{subdir}/{uuid.uuid4().hex}_{upload_file.filename or 'f.bin'}".replace("//", "/")
        self.root_files[stored] = data
        return stored, upload_file.filename or "f.bin", len(data)

    def get_file_stream(self, path):
        data = self.root_files.get(path, self.content)
        return io.BytesIO(data)


async def _upload_attachment(client: AsyncClient, user: dict, issue_id: str, storage: _FakeStorage) -> str:
    content = b"payload-e66-bytes"
    storage.content = content
    storage.root_files["pending"] = content
    with patch("opentask.api.issue.router.get_storage_service", return_value=storage):
        files = {"file": ("note.txt", content, "text/plain")}
        resp = await client.post(
            f"/api/issues/{issue_id}/attachments",
            headers=_auth(user["token"], user["workspaceId"]),
            files=files,
        )
    assert resp.status_code == 200, resp.text
    aid = resp.json()["data"]["id"]
    # ensure stream path is known
    # re-fetch attachment file_path via list
    listed = await client.get(
        f"/api/issues/{issue_id}/attachments",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]
    row = next(r for r in rows if r["id"] == aid)
    storage.root_files[row["file_path"]] = content
    return aid


@pytest.mark.asyncio
async def test_e66_download_requires_auth(test_client: AsyncClient):
    resp = await test_client.get(f"/api/attachments/{uuid.uuid4()}/download")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_e66_preview_requires_auth(test_client: AsyncClient):
    resp = await test_client.get(f"/api/attachments/{uuid.uuid4()}/preview")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_e66_member_download_preview_200(test_client: AsyncClient):
    user = await _register(test_client, "e66_ok")
    issue = await _create_issue(test_client, user, "HasAtt")
    storage = _FakeStorage()
    aid = await _upload_attachment(test_client, user, issue["id"], storage)
    h = _auth(user["token"], user["workspaceId"])
    with patch("opentask.api.attachment.router.get_storage_service", return_value=storage):
        dl = await test_client.get(f"/api/attachments/{aid}/download", headers=h)
        assert dl.status_code == 200, dl.text
        assert dl.content == b"payload-e66-bytes"
        pv = await test_client.get(f"/api/attachments/{aid}/preview", headers=h)
        assert pv.status_code == 200, pv.text
        assert pv.content == b"payload-e66-bytes"
        assert "inline" in pv.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_e66_non_member_gets_404(test_client: AsyncClient):
    owner = await _register(test_client, "e66_own")
    stranger = await _register(test_client, "e66_str")
    issue = await _create_issue(test_client, owner, "SecretAtt")
    storage = _FakeStorage()
    aid = await _upload_attachment(test_client, owner, issue["id"], storage)
    h = _auth(stranger["token"], stranger["workspaceId"])
    with patch("opentask.api.attachment.router.get_storage_service", return_value=storage):
        dl = await test_client.get(f"/api/attachments/{aid}/download", headers=h)
        assert dl.status_code == 404, dl.text
        pv = await test_client.get(f"/api/attachments/{aid}/preview", headers=h)
        assert pv.status_code == 404, pv.text


@pytest.mark.asyncio
async def test_e66_issue_scoped_download_requires_auth(test_client: AsyncClient):
    owner = await _register(test_client, "e66_iss")
    issue = await _create_issue(test_client, owner, "IssAtt")
    storage = _FakeStorage()
    aid = await _upload_attachment(test_client, owner, issue["id"], storage)
    # unauth
    bare = await test_client.get(f"/api/issues/{issue['id']}/attachments/{aid}/download")
    assert bare.status_code == 401
    # stranger
    stranger = await _register(test_client, "e66_iss2")
    with patch("opentask.api.issue.router.get_storage_service", return_value=storage):
        denied = await test_client.get(
            f"/api/issues/{issue['id']}/attachments/{aid}/download",
            headers=_auth(stranger["token"], stranger["workspaceId"]),
        )
        assert denied.status_code in (403, 404), denied.text
        ok = await test_client.get(
            f"/api/issues/{issue['id']}/attachments/{aid}/download",
            headers=_auth(owner["token"], owner["workspaceId"]),
        )
        assert ok.status_code == 200, ok.text
        assert ok.content == b"payload-e66-bytes"
