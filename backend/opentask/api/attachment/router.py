"""Attachment API 路由 - 公共访问，不需要认证"""
import logging
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.services.issue_service import IssueService
from opentask.services.storage.service import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/attachments", tags=["附件管理"])


async def get_issue_service(
    db: AsyncSession = Depends(get_session)
) -> IssueService:
    """获取 Issue 服务依赖"""
    return IssueService(db)


# ========================================================================
# 附件下载（公共访问，无需认证）
# ========================================================================

@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    service: IssueService = Depends(get_issue_service),
):
    """下载附件（公共访问，通过附件 ID 的随机性保证基本安全性）

    注意：此接口不需要认证，允许通过附件 ID 直接访问。
    适合内部系统使用，UUID 的随机性提供了基本的安全保护。
    """
    attachment = await service.get_attachment_by_id(attachment_id)

    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    storage_service = get_storage_service()

    try:
        file_stream = storage_service.get_file_stream(attachment.file_path)

        def iter_file():
            """生成器函数：分块读取文件数据"""
            chunk_size = 8192  # 8KB chunks
            while True:
                data = file_stream.read(chunk_size)
                if not data:
                    break
                yield data
            file_stream.close()

        # 使用RFC 5987编码支持中文文件名
        encoded_filename = quote(attachment.file_name)
        return StreamingResponse(
            iter_file(),
            media_type=attachment.file_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename*=UTF-8\'\'{encoded_filename}'
            }
        )
    except Exception as e:
        logger.error(f"MinIO 下载附件失败: {e}")
        raise HTTPException(status_code=500, detail="附件下载失败")


@router.get("/{attachment_id}/preview")
async def preview_attachment(
    attachment_id: str,
    service: IssueService = Depends(get_issue_service),
):
    """预览附件（内联显示，适合图片等浏览器可直接展示的文件）

    与下载接口的区别在于 Content-Disposition 设置为 inline，
    浏览器会直接在页面中显示而非触发下载。
    """
    attachment = await service.get_attachment_by_id(attachment_id)

    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

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
        return StreamingResponse(
            iter_file(),
            media_type=attachment.file_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'inline; filename*=UTF-8\'\'{encoded_filename}'
            }
        )
    except Exception as e:
        logger.error(f"MinIO 预览附件失败: {e}")
        raise HTTPException(status_code=500, detail="附件预览失败")
