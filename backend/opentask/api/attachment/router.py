"""Attachment API — authenticated workspace-member reads (E66); optional signed URL."""
from __future__ import annotations

import logging
from typing import Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.config import config
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.attachment_acl import require_attachment_read
from opentask.services.attachment_signed_url import (
    DEFAULT_TTL_SECONDS,
    MAX_TTL_SECONDS,
    ALLOWED_PURPOSES,
    mint_signed_token,
    verify_signed_token,
)
from opentask.services.issue_service import IssueService
from opentask.services.storage.service import get_storage_service
from opentask.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/attachments", tags=["附件管理"])


async def get_issue_service(
    db: AsyncSession = Depends(get_session),
) -> IssueService:
    return IssueService(db)


def _stream_attachment(attachment, *, inline: bool) -> StreamingResponse:
    storage_service = get_storage_service()
    try:
        file_stream = storage_service.get_file_stream(attachment.file_path)

        def iter_file():
            chunk_size = 8192
            while True:
                data = file_stream.read(chunk_size)
                if not data:
                    break
                yield data
            file_stream.close()

        encoded_filename = quote(attachment.file_name)
        disposition = "inline" if inline else "attachment"
        return StreamingResponse(
            iter_file(),
            media_type=attachment.file_type or "application/octet-stream",
            headers={
                "Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded_filename}"
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MinIO attachment stream failed: {e}")
        raise HTTPException(status_code=500, detail="附件读取失败")


class SignedUrlBody(BaseModel):
    purpose: Literal["download", "preview"]
    ttlSeconds: Optional[int] = None


@router.get("/signed/{token}")
async def fetch_signed_attachment(
    token: str,
    service: IssueService = Depends(get_issue_service),
):
    """无会话短链读取（E66）：校验 HMAC + exp + aid 后流式返回。"""
    try:
        payload = verify_signed_token(token, secret=config.auth_secret_key)
    except ValueError:
        raise HTTPException(status_code=401, detail="签名无效或已过期")

    attachment = await service.get_attachment_by_id(payload["attachment_id"])
    if attachment is None:
        raise HTTPException(status_code=404, detail="附件不存在")

    return _stream_attachment(attachment, inline=(payload["purpose"] == "preview"))


@router.post("/{attachment_id}/signed-url")
async def create_signed_url(
    attachment_id: str,
    body: SignedUrlBody,
    current_user: UserModel = Depends(authenticate),
    service: IssueService = Depends(get_issue_service),
):
    """签发短 TTL HMAC 签名 URL（仅工作区成员；无状态，不入库）。"""
    await require_attachment_read(
        service.db,
        user_id=str(current_user.id),
        attachment_id=attachment_id,
        issue_service=service,
    )
    if body.purpose not in ALLOWED_PURPOSES:
        raise HTTPException(status_code=400, detail="purpose 无效")
    ttl = body.ttlSeconds if body.ttlSeconds is not None else DEFAULT_TTL_SECONDS
    if ttl < 1 or ttl > MAX_TTL_SECONDS:
        raise HTTPException(
            status_code=400,
            detail=f"ttlSeconds 须在 1–{MAX_TTL_SECONDS} 之间",
        )
    try:
        token, expires_at = mint_signed_token(
            attachment_id=attachment_id,
            purpose=body.purpose,
            ttl_seconds=ttl,
            secret=config.auth_secret_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return success_response(
        data={
            "url": f"/api/attachments/signed/{token}",
            "expiresAt": expires_at.isoformat(),
        }
    )


@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    current_user: UserModel = Depends(authenticate),
    service: IssueService = Depends(get_issue_service),
):
    """下载附件（E66：须登录且为附件所属 Issue 的工作区成员）"""
    attachment = await require_attachment_read(
        service.db,
        user_id=str(current_user.id),
        attachment_id=attachment_id,
        issue_service=service,
    )
    return _stream_attachment(attachment, inline=False)


@router.get("/{attachment_id}/preview")
async def preview_attachment(
    attachment_id: str,
    current_user: UserModel = Depends(authenticate),
    service: IssueService = Depends(get_issue_service),
):
    """预览附件（E66：须登录且为附件所属 Issue 的工作区成员；Content-Disposition: inline）"""
    attachment = await require_attachment_read(
        service.db,
        user_id=str(current_user.id),
        attachment_id=attachment_id,
        issue_service=service,
    )
    return _stream_attachment(attachment, inline=True)
