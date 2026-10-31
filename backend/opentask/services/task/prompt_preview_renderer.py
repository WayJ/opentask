"""
提示词预览渲染器

用于在创建任务前预览提示词（不需要创建实际任务）
"""

import logging
from opentask.models.task.schema import SUPERPOWER_SKILLS

logger = logging.getLogger(__name__)


# 导入原有的 pge_prompt 模板
from opentask.services.task.prompt import pge_prompt


async def render_preview_prompt(
    requirement_title: str,
    requirement_id: str,
    description: str | None = None,
    required_skills: list[str] | None = None,
) -> str:
    """
    渲染 PGE 任务提示词预览（使用原有的 pge_prompt 模板）

    Args:
        requirement_title: 需求标题
        requirement_id: 需求ID
        description: 任务描述
        required_skills: 必需技能列表

    Returns:
        渲染后的提示词
    """
    # 填充模板变量
    prompt = pge_prompt

    # 1. 替换需求标题
    prompt = prompt.replace(
        "{你的需求标题，例如：用户登录功能}",
        requirement_title
    )

    # 2. 替换任务 ID（预览模式）
    prompt = prompt.replace(
        "（创建后自动生成）",
        "preview"
    )

    # 3. 替换需求 ID
    prompt = prompt.replace(
        "{需求ID，可留空}",
        requirement_id
    )

    # 4. 替换任务描述
    prompt = prompt.replace(
        "{这里粘贴具体需求描述，例如：实现用户登录功能，包括用户名/邮箱+密码登录，支持记住我，失败提示等}",
        description or "无描述"
    )

    # 5. 构建技能列表
    skills_list = []
    if required_skills:
        for skill_id in required_skills:
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

            skills_list.append(f"- ✅ {skill_name} ({skill_id})")
            skills_list.append(f"  - {skill_description}")

    skills_text = "\n".join(skills_list) if skills_list else "无"

    # 6. 替换技能列表
    prompt = prompt.replace(
        "{列出需要的技能，例如：superpowers:test-driven-development, superpowers:systematic-debugging}",
        skills_text
    )

    # 7. 替换 {技能列表} 占位符
    prompt = prompt.replace(
        "{技能列表}",
        ", ".join(required_skills) if required_skills else "无"
    )

    logger.info(f"渲染预览提示词成功: {requirement_title}")

    return prompt
