"""
Webhook 处理器

处理 Git Push 事件，自动同步知识库
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from pydantic import BaseModel

from opentask.repositories.base import get_session
from opentask.services.git_knowledge_service import GitKnowledgeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhook", tags=["Webhooks"])


async def sync_knowledge_files(kb_id: str, git_service: GitKnowledgeService) -> int:
    """
    同步知识库文件到数据库

    遍历 Git 仓库中的所有 Markdown 文件，更新数据库记录

    Args:
        kb_id: 知识库 ID
        git_service: Git 服务实例

    Returns:
        同步的文件数量
    """
    from git import Repo
    from opentask.models.knowledge.model import Knowledge
    from opentask.models.knowledge_base.model import KnowledgeBase

    repo_path = git_service._get_repo_path(kb_id)
    if not repo_path.exists():
        logger.warning(f"本地缓存不存在: {kb_id}")
        return 0

    repo = Repo(repo_path)

    # 查找所有 .md 文件
    md_files = list(repo_path.rglob("*.md"))
    logger.info(f"找到 {len(md_files)} 个 Markdown 文件")

    sync_count = 0

    async with get_session() as db:
        for md_file in md_files:
            try:
                # 计算相对路径
                rel_path = md_file.relative_to(repo_path)
                file_path_str = str(rel_path).replace('\\', '/')

                # 解析文档 ID（通常是目录名）
                parts = file_path_str.split('/')
                if len(parts) >= 2:
                    doc_id = parts[-2]  # 倒数第二部分是文档 ID

                    # 检查数据库中是否存在
                    result = await db.execute(
                        select(Knowledge).where(Knowledge.id == doc_id)
                    )
                    knowledge = result.scalar_one_or_none()

                    # 读取文件内容
                    content = md_file.read_text(encoding='utf-8')

                    # 解析 front matter（如果存在）
                    title = doc_id
                    if content.startswith('---'):
                        try:
                            _, front_matter, body = content.split('---', 2)
                            for line in front_matter.strip().split('\n'):
                                if line.startswith('title:'):
                                    title = line.split(':', 1)[1].strip().strip('"\'')
                                    break
                        except:
                            body = content
                    else:
                        body = content

                    if knowledge:
                        # 更新现有记录
                        knowledge.content = body
                        knowledge.title = title
                        logger.info(f"更新文档: {doc_id}")
                    else:
                        # 创建新记录
                        new_knowledge = Knowledge(
                            id=doc_id,
                            title=title,
                            content=body,
                            knowledge_base_id=kb_id,
                            status='published'
                        )
                        db.add(new_knowledge)
                        logger.info(f"创建文档: {doc_id}")

                    sync_count += 1

            except Exception as e:
                logger.error(f"同步文件 {md_file} 失败: {e}")

        # 提交数据库更改
        await db.commit()
        logger.info(f"知识库 {kb_id} 同步完成，共处理 {sync_count} 个文件")

    return sync_count


class WebhookResponse(BaseModel):
    """Webhook 响应模型"""
    status: str
    message: str
    kb_id: str | None = None


@router.post("/git-push")
async def git_push_webhook(request: Request):
    """
    处理 Git Push 事件

    支持 GitLab 和 GitHub 的 webhook 格式
    """
    # 检测 webhook 类型
    event_type = request.headers.get("X-GitLab-Event") or request.headers.get("X-GitHub-Event")

    if not event_type:
        raise HTTPException(status_code=400, detail="不支持的 webhook 类型")

    payload = await request.json()

    if event_type == "Push Hook":  # GitLab
        return await handle_gitlab_push(payload)
    elif event_type == "push":  # GitHub
        return await handle_github_push(payload)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的事件类型: {event_type}")


async def handle_gitlab_push(payload: Dict[str, Any]) -> WebhookResponse:
    """处理 GitLab Push 事件"""
    try:
        # 获取项目信息
        project_id = payload.get('project_id')
        project_url = payload.get('project', {}).get('web_url')

        if not project_id or not project_url:
            logger.warning("GitLab webhook payload 缺少必要字段")
            return WebhookResponse(
                status="ignored",
                message="Webhook payload 缺少必要字段"
            )

        logger.info(f"收到 GitLab Push 事件: {project_url} (项目 ID: {project_id})")

        # 查找对应的知识库
        from opentask.models.knowledge_base.model import KnowledgeBase

        async with get_session() as db:
            # 尝试通过 project_id 匹配
            result = await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.repository_url.contains(str(project_id))
                )
            )
            kb = result.scalar_one_or_none()

            # 如果没有找到，尝试通过 URL 匹配
            if not kb:
                # 提取项目路径进行匹配
                project_path = payload.get('project', {}).get('path_with_namespace')
                if project_path:
                    result = await db.execute(
                        select(KnowledgeBase).where(
                            KnowledgeBase.repository_url.contains(project_path.replace('/', ''))
                        )
                    )
                    kb = result.scalar_one_or_none()

            if not kb:
                logger.warning(f"未找到对应的知识库: {project_url}")
                return WebhookResponse(
                    status="ignored",
                    message="未找到对应知识库"
                )

            # 同步知识库
            git_service = GitKnowledgeService()

            try:
                # 拉取最新代码
                await git_service.ensure_cloned(kb.repository_url, kb.id)

                # 同步到数据库
                sync_count = await sync_knowledge_files(kb.id, git_service)

                logger.info(f"知识库 {kb.id} 同步完成，处理了 {sync_count} 个文件")

                return WebhookResponse(
                    status="success",
                    message=f"已同步知识库 {kb.name}，处理了 {sync_count} 个文件",
                    kb_id=kb.id
                )

            except Exception as e:
                logger.error(f"同步知识库 {kb.id} 失败: {e}")
                return WebhookResponse(
                    status="error",
                    message=f"同步失败: {str(e)}",
                    kb_id=kb.id
                )

    except Exception as e:
        logger.error(f"处理 GitLab webhook 失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理 webhook 失败: {str(e)}")


async def handle_github_push(payload: Dict[str, Any]) -> WebhookResponse:
    """处理 GitHub Push 事件"""
    try:
        # 获取仓库信息
        repository = payload.get('repository', {})
        repo_url = repository.get('html_url')
        repo_id = repository.get('id')
        repo_name = repository.get('full_name')

        if not repo_url:
            logger.warning("GitHub webhook payload 缺少仓库信息")
            return WebhookResponse(
                status="ignored",
                message="Webhook payload 缺少仓库信息"
            )

        logger.info(f"收到 GitHub Push 事件: {repo_name}")

        # 查找对应的知识库
        from opentask.models.knowledge_base.model import KnowledgeBase

        async with get_session() as db:
            # 尝试通过 URL 匹配
            result = await db.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.repository_url.contains(repo_name.replace('/', ''))
                )
            )
            kb = result.scalar_one_or_none()

            if not kb:
                logger.warning(f"未找到对应的知识库: {repo_name}")
                return WebhookResponse(
                    status="ignored",
                    message="未找到对应知识库"
                )

            # 同步知识库
            git_service = GitKnowledgeService()

            try:
                # 拉取最新代码
                await git_service.ensure_cloned(kb.repository_url, kb.id)

                # 同步到数据库
                sync_count = await sync_knowledge_files(kb.id, git_service)

                logger.info(f"知识库 {kb.id} 同步完成，处理了 {sync_count} 个文件")

                return WebhookResponse(
                    status="success",
                    message=f"已同步知识库 {kb.name}，处理了 {sync_count} 个文件",
                    kb_id=kb.id
                )

            except Exception as e:
                logger.error(f"同步知识库 {kb.id} 失败: {e}")
                return WebhookResponse(
                    status="error",
                    message=f"同步失败: {str(e)}",
                    kb_id=kb.id
                )

    except Exception as e:
        logger.error(f"处理 GitHub webhook 失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理 webhook 失败: {str(e)}")


@router.get("/test")
async def webhook_test():
    """Webhook 测试端点"""
    return {
        "status": "ok",
        "message": "Webhook 服务正常运行"
    }
