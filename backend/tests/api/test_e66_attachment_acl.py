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


# ---------------------------------------------------------------------------
# B · signed URL
# ---------------------------------------------------------------------------


def test_e66_mint_verify_roundtrip():
    from opentask.services.attachment_signed_url import mint_signed_token, verify_signed_token

    tok, exp = mint_signed_token(
        attachment_id="aid-1", purpose="preview", ttl_seconds=900, secret="s"
    )
    payload = verify_signed_token(tok, secret="s")
    assert payload["attachment_id"] == "aid-1"
    assert payload["purpose"] == "preview"
    assert payload["exp"] == int(exp.timestamp())


def test_e66_tamper_rejected():
    from opentask.services.attachment_signed_url import mint_signed_token, verify_signed_token

    tok, _ = mint_signed_token(
        attachment_id="aid-1", purpose="download", ttl_seconds=60, secret="s"
    )
    bad = tok[:-4] + "dead"
    with pytest.raises(ValueError):
        verify_signed_token(bad, secret="s")


def test_e66_expired_rejected():
    from opentask.services.attachment_signed_url import mint_signed_token, verify_signed_token
    import time

    tok, _ = mint_signed_token(
        attachment_id="aid-1", purpose="preview", ttl_seconds=1, secret="s"
    )
    # force expiry by verifying with manipulated clock via rewriting exp in token
    parts = tok.split(".")
    # set exp in the past
    past = str(int(time.time()) - 10)
    msg = f"{parts[0]}.{past}.{parts[2]}"
    import hashlib
    import hmac as hm

    sig = hm.new(b"s", msg.encode(), hashlib.sha256).hexdigest()
    expired = f"{msg}.{sig}"
    with pytest.raises(ValueError):
        verify_signed_token(expired, secret="s")


@pytest.mark.asyncio
async def test_e66_signed_url_issue_and_fetch(test_client: AsyncClient):
    user = await _register(test_client, "e66_sig")
    issue = await _create_issue(test_client, user, "SignedAtt")
    storage = _FakeStorage()
    aid = await _upload_attachment(test_client, user, issue["id"], storage)
    h = _auth(user["token"], user["workspaceId"])

    bad_ttl = await test_client.post(
        f"/api/attachments/{aid}/signed-url",
        headers=h,
        json={"purpose": "preview", "ttlSeconds": 99999},
    )
    assert bad_ttl.status_code == 400, bad_ttl.text

    minted = await test_client.post(
        f"/api/attachments/{aid}/signed-url",
        headers=h,
        json={"purpose": "preview"},
    )
    assert minted.status_code == 200, minted.text
    body = minted.json()["data"]
    assert "url" in body and "expiresAt" in body
    assert "/api/attachments/signed/" in body["url"]
    token = body["url"].rstrip("/").split("/")[-1]

    with patch("opentask.api.attachment.router.get_storage_service", return_value=storage):
        ok = await test_client.get(f"/api/attachments/signed/{token}")
        assert ok.status_code == 200, ok.text
        assert ok.content == b"payload-e66-bytes"
        assert "inline" in ok.headers.get("content-disposition", "")

        # tampered
        bad = await test_client.get(f"/api/attachments/signed/{token[:-4]}dead")
        assert bad.status_code in (401, 404), bad.text

    # stranger cannot mint
    stranger = await _register(test_client, "e66_sig2")
    denied = await test_client.post(
        f"/api/attachments/{aid}/signed-url",
        headers=_auth(stranger["token"], stranger["workspaceId"]),
        json={"purpose": "download"},
    )
    assert denied.status_code == 404, denied.text


@pytest.mark.asyncio
async def test_e66_download_no_webhook_fire(test_client: AsyncClient):
    user = await _register(test_client, "e66_spy")
    issue = await _create_issue(test_client, user, "SpyAtt")
    storage = _FakeStorage()
    aid = await _upload_attachment(test_client, user, issue["id"], storage)
    h = _auth(user["token"], user["workspaceId"])
    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fw:
        with patch("opentask.api.attachment.router.get_storage_service", return_value=storage):
            dl = await test_client.get(f"/api/attachments/{aid}/download", headers=h)
            assert dl.status_code == 200, dl.text
            signed = await test_client.post(
                f"/api/attachments/{aid}/signed-url",
                headers=h,
                json={"purpose": "download"},
            )
            assert signed.status_code == 200, signed.text
            token = signed.json()["data"]["url"].rstrip("/").split("/")[-1]
            got = await test_client.get(f"/api/attachments/signed/{token}")
            assert got.status_code == 200, got.text
        fw.assert_not_called()
