"""Builtin Issue template seeds (from FE ISSUE_TEMPLATES; NOT PGE prompts)."""
from __future__ import annotations

from typing import Any


def _fields_bug() -> list[dict[str, Any]]:
    return [
        {"name": "title", "label": "问题标题", "type": "text", "placeholder": "简要描述问题", "required": True},
        {"name": "description", "label": "问题描述", "type": "textarea", "placeholder": "详细描述遇到的问题", "required": True},
        {"name": "environment", "label": "环境信息", "type": "textarea", "placeholder": "- 操作系统:\n- 浏览器:\n- 版本:", "required": False},
        {"name": "steps_to_reproduce", "label": "复现步骤", "type": "textarea", "placeholder": "1. \n2. \n3. ", "required": True},
        {"name": "expected_behavior", "label": "期望行为", "type": "textarea", "placeholder": "描述期望的正确行为", "required": True},
        {"name": "actual_behavior", "label": "实际行为", "type": "textarea", "placeholder": "描述实际发生的错误行为", "required": True},
    ]


def _fields_feature() -> list[dict[str, Any]]:
    return [
        {"name": "title", "label": "功能标题", "type": "text", "placeholder": "简要描述功能请求", "required": True},
        {"name": "description", "label": "功能描述", "type": "textarea", "placeholder": "详细描述功能", "required": True},
        {"name": "motivation", "label": "动机", "type": "textarea", "placeholder": "为什么需要", "required": False},
        {"name": "proposed_solution", "label": "方案", "type": "textarea", "placeholder": "建议实现", "required": False},
    ]


def _fields_improvement() -> list[dict[str, Any]]:
    return [
        {"name": "title", "label": "标题", "type": "text", "placeholder": "改进点", "required": True},
        {"name": "current_state", "label": "现状", "type": "textarea", "placeholder": "当前行为", "required": True},
        {"name": "proposed_improvement", "label": "改进", "type": "textarea", "placeholder": "期望改进", "required": True},
    ]


def _fields_question() -> list[dict[str, Any]]:
    return [
        {"name": "title", "label": "问题", "type": "text", "placeholder": "你的问题", "required": True},
        {"name": "description", "label": "详情", "type": "textarea", "placeholder": "补充说明", "required": True},
        {"name": "context", "label": "上下文", "type": "textarea", "placeholder": "相关背景", "required": False},
    ]


def _fields_task() -> list[dict[str, Any]]:
    return [
        {"name": "title", "label": "任务标题", "type": "text", "placeholder": "任务名称", "required": True},
        {"name": "description", "label": "描述", "type": "textarea", "placeholder": "任务说明", "required": True},
        {"name": "acceptance_criteria", "label": "验收标准", "type": "textarea", "placeholder": "- [ ]", "required": False},
    ]


def _desc_from_fields(fields: list[dict[str, Any]]) -> str:
    parts = []
    for f in fields:
        if f["name"] == "title":
            continue
        ph = f.get("placeholder") or ""
        parts.append(f"## {f['label']}\n{ph}".rstrip())
    return "\n\n".join(parts)


BUILTIN_SEEDS: list[dict[str, Any]] = [
    {
        "seed_key": "bug_report",
        "name": "Bug 报告",
        "description": "报告系统中的问题或错误",
        "icon": "i-carbon-bug",
        "sort_order": 0,
        "issue_type": "bug",
        "fields": _fields_bug(),
    },
    {
        "seed_key": "feature_request",
        "name": "功能请求",
        "description": "提出新功能或改进建议",
        "icon": "i-carbon-light",
        "sort_order": 1,
        "issue_type": "feature",
        "fields": _fields_feature(),
    },
    {
        "seed_key": "improvement",
        "name": "改进建议",
        "description": "对现有功能的改进",
        "icon": "i-carbon-improve-relevance",
        "sort_order": 2,
        "issue_type": "improvement",
        "fields": _fields_improvement(),
    },
    {
        "seed_key": "question",
        "name": "问题咨询",
        "description": "提出疑问或寻求帮助",
        "icon": "i-carbon-help",
        "sort_order": 3,
        "issue_type": "question",
        "fields": _fields_question(),
    },
    {
        "seed_key": "task",
        "name": "任务分配",
        "description": "分配具体执行任务",
        "icon": "i-carbon-task",
        "sort_order": 4,
        "issue_type": "feedback",  # IssueType 无 task
        "fields": _fields_task(),
    },
]


def builtin_payload(seed: dict[str, Any]) -> dict[str, Any]:
    fields = seed["fields"]
    return {
        "type": seed["issue_type"],
        "priority": "medium",
        "title": "",
        "description": _desc_from_fields(fields),
        "fields": fields,
    }
