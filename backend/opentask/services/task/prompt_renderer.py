"""
提示词渲染器

用于渲染 pge_prompt 模板，填充变量占位符。
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.task.enums import TaskStatus, TaskType
from opentask.models.task.model import Task
from opentask.models.task.schema import SUPERPOWER_SKILLS

logger = logging.getLogger(__name__)


# 导入原有的 pge_prompt 模板
from opentask.services.task.prompt import pge_prompt


async def render_pge_prompt(
    task_id: str,
    db: AsyncSession,
) -> str:
    """
    渲染 PGE 任务提示词（使用原有的 pge_prompt 模板）

    Args:
        task_id: 任务 ID
        db: 数据库会话

    Returns:
        渲染后的提示词

    Raises:
        ValueError: 任务不存在
    """
    # 查询父任务
    stmt = select(Task).where(Task.id == task_id)
    result = await db.execute(stmt)
    parent_task = result.scalar_one_or_none()

    if not parent_task:
        raise ValueError(f"任务不存在: {task_id}")

    # 查询子任务
    stmt = select(Task).where(Task.parent_id == task_id).order_by(Task.code)
    result = await db.execute(stmt)
    subtasks = result.scalars().all()

    # 填充模板变量
    prompt = pge_prompt

    # 1. 替换需求标题
    prompt = prompt.replace(
        "{你的需求标题，例如：用户登录功能}",
        parent_task.title
    )

    # 2. 替换任务 ID
    prompt = prompt.replace(
        "（创建后自动生成）",
        parent_task.id
    )

    # 3. 替换需求 ID
    prompt = prompt.replace(
        "{需求ID，可留空}",
        parent_task.requirement_id
    )

    # 4. 替换任务描述
    prompt = prompt.replace(
        "{这里粘贴具体需求描述，例如：实现用户登录功能，包括用户名/邮箱+密码登录，支持记住我，失败提示等}",
        parent_task.description or "无描述"
    )

    # 5. 构建技能列表
    required_skills = []
    if parent_task.required_skills and "skills" in parent_task.required_skills:
        skills = parent_task.required_skills["skills"]
        for skill_id in skills:
            # 查找技能的中文说明
            skill_name = skill_id
            skill_description = ""
            for category_skills in SUPERPOWER_SKILLS.values():
                for skill in category_skills:
                    if skill["id"] == skill_id:
                        skill_name = skill["name"]
                        skill_description = skill["description"]
                        break
                if skill_name != skill_id:
                    break

            required_skills.append(f"- ✅ {skill_name} ({skill_id})")
            required_skills.append(f"  - {skill_description}")

    skills_text = "\n".join(required_skills) if required_skills else "无"

    # 6. 替换技能列表
    prompt = prompt.replace(
        "{列出需要的技能，例如：superpowers:test-driven-development, superpowers:systematic-debugging}",
        skills_text
    )

    # 7. 替换 {技能列表} 占位符（如果有的话）
    prompt = prompt.replace(
        "{技能列表}",
        ", ".join(
            parent_task.required_skills.get("skills", [])
        ) if parent_task.required_skills and "skills" in parent_task.required_skills else "无"
    )

    logger.info(f"渲染任务提示词成功: {task_id}")

    return prompt
