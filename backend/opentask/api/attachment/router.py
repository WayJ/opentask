"""Attachment API — authenticated workspace-member reads (E66); optional signed URL."""
import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.attachment_acl import require_attachment_read
from opentask.services.issue_service import IssueService
from opentask.services.storage.service import get_storage_service

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
