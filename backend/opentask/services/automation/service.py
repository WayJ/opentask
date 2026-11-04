"""Automation rules CRUD + after-commit executor (E26)."""
from __future__ import annotations

import contextvars
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.automation.model import (
    ACTION_TYPES,
    TRIGGER_TYPES,
    AutomationRule,
)
from opentask.models.issue.model import Issue, IssueTag
from opentask.models.issue.schema import IssueUpdate
from opentask.models.tag.model import Tag
from opentask.models.workspace.model import WorkspaceMember

logger = logging.getLogger(__name__)

# Anti-loop: user write depth=0 may fire rules; while executing actions depth>=1 → skip.
_automation_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
    "automation_depth", default=0
)


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def serialize_rule(row: AutomationRule) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "name": row.name,
        "enabled": bool(row.enabled),
        "triggerType": row.trigger_type,
        "triggerConfig": row.trigger_config_json or {},
        "condition": row.condition_json,
        "actionType": row.action_type,
        "actionConfig": row.action_config_json or {},
        "createdBy": row.created_by,
        "position": row.position,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _enum_val(v: Any) -> Any:
    return getattr(v, "value", v)


class AutomationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, *, workspace_id: str) -> list[AutomationRule]:
        stmt = (
            select(AutomationRule)
            .where(AutomationRule.workspace_id == workspace_id)
            .order_by(AutomationRule.position.asc(), AutomationRule.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get(self, *, workspace_id: str, rule_id: str) -> AutomationRule:
        row = await self._get_or_404(workspace_id, rule_id)
        return row

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        name: str,
        trigger_type: str,
        action_type: str,
        trigger_config: dict | None = None,
        condition: dict | None = None,
        action_config: dict | None = None,
        enabled: bool = True,
        position: int | None = None,
    ) -> AutomationRule:
        self._validate_enums(trigger_type, action_type)
        if position is None:
            q = await self.db.execute(
                select(func.coalesce(func.max(AutomationRule.position), -1)).where(
                    AutomationRule.workspace_id == workspace_id
                )
            )
            position = int(q.scalar_one()) + 1
        row = AutomationRule(
            workspace_id=workspace_id,
            name=name.strip(),
            enabled=bool(enabled),
            trigger_type=trigger_type,
            trigger_config_json=dict(trigger_config or {}),
            condition_json=condition,
            action_type=action_type,
            action_config_json=dict(action_config or {}),
            created_by=user_id,
            position=position,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update(
        self,
        *,
        workspace_id: str,
        rule_id: str,
        name: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_config: Optional[dict] = None,
        set_trigger_config: bool = False,
        condition: Optional[dict] = None,
        set_condition: bool = False,
        action_type: Optional[str] = None,
        action_config: Optional[dict] = None,
        set_action_config: bool = False,
        enabled: Optional[bool] = None,
        position: Optional[int] = None,
    ) -> AutomationRule:
        row = await self._get_or_404(workspace_id, rule_id)
        if name is not None:
            row.name = name.strip()
        if trigger_type is not None:
            if trigger_type not in TRIGGER_TYPES:
                raise HTTPException(status_code=400, detail=f"非法 trigger: {trigger_type}")
            row.trigger_type = trigger_type
        if set_trigger_config:
            row.trigger_config_json = dict(trigger_config or {})
        if set_condition:
            row.condition_json = condition
        if action_type is not None:
            if action_type not in ACTION_TYPES:
                raise HTTPException(status_code=400, detail=f"非法 action: {action_type}")
            row.action_type = action_type
        if set_action_config:
            row.action_config_json = dict(action_config or {})
        if enabled is not None:
            row.enabled = bool(enabled)
        if position is not None:
            row.position = position
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def set_enabled(
        self, *, workspace_id: str, rule_id: str, enabled: bool
    ) -> AutomationRule:
        return await self.update(
            workspace_id=workspace_id, rule_id=rule_id, enabled=enabled
        )

    async def delete(self, *, workspace_id: str, rule_id: str) -> None:
        row = await self._get_or_404(workspace_id, rule_id)
        await self.db.delete(row)
        await self.db.commit()

    async def _get_or_404(self, workspace_id: str, rule_id: str) -> AutomationRule:
        stmt = select(AutomationRule).where(
            AutomationRule.id == rule_id,
            AutomationRule.workspace_id == workspace_id,
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="规则不存在")
        return row

    @staticmethod
    def _validate_enums(trigger_type: str, action_type: str) -> None:
        if trigger_type not in TRIGGER_TYPES:
            raise HTTPException(status_code=400, detail=f"非法 trigger: {trigger_type}")
        if action_type not in ACTION_TYPES:
            raise HTTPException(status_code=400, detail=f"非法 action: {action_type}")

    # ── match / execute ──────────────────────────────────────────────

    async def run_for_event(
        self,
        *,
        workspace_id: str,
        trigger_type: str,
        issue: Issue,
        actor_user_id: Optional[str] = None,
        event: Optional[dict[str, Any]] = None,
    ) -> None:
        """Best-effort: match enabled rules and run actions. Never raises to caller."""
        if _automation_depth.get() >= 1:
            return
        if not workspace_id or not issue:
            return
        event = event or {}
        try:
            stmt = (
                select(AutomationRule)
                .where(
                    AutomationRule.workspace_id == workspace_id,
                    AutomationRule.enabled.is_(True),
                    AutomationRule.trigger_type == trigger_type,
                )
                .order_by(AutomationRule.position.asc(), AutomationRule.created_at.asc())
            )
            rules = list((await self.db.execute(stmt)).scalars().all())
        except Exception:
            logger.exception("automation: load rules failed ws=%s", workspace_id)
            return

        for rule in rules:
            try:
                if not self._match_trigger(rule, event):
                    continue
                if not await self._match_condition(rule, issue):
                    continue
                await self._execute_action(
                    rule, issue=issue, actor_user_id=actor_user_id or rule.created_by
                )
            except Exception:
                logger.exception(
                    "automation: rule %s failed on issue %s", rule.id, getattr(issue, "id", None)
                )

    def _match_trigger(self, rule: AutomationRule, event: dict[str, Any]) -> bool:
        cfg = rule.trigger_config_json or {}
        t = rule.trigger_type
        if t == "issue.created":
            return True
        if t == "issue.status_changed":
            if cfg.get("from") is not None and str(event.get("from")) != str(cfg["from"]):
                return False
            if cfg.get("to") is not None and str(event.get("to")) != str(cfg["to"]):
                return False
            return True
        if t == "issue.assignee_changed":
            if cfg.get("to") is not None and str(event.get("to") or "") != str(cfg["to"]):
                return False
            return True
        if t == "label_added":
            want = cfg.get("tagId")
            if want is None:
                want = cfg.get("tag_id")
            if want is not None and int(want) != int(event.get("tagId") or event.get("tag_id") or -1):
                return False
            return True
        return False

    async def _match_condition(self, rule: AutomationRule, issue: Issue) -> bool:
        cond = rule.condition_json
        if not cond:
            return True
        status_in = cond.get("statusIn") or cond.get("status_in")
        if status_in is not None:
            cur = str(_enum_val(issue.status))
            allowed = [str(x) for x in status_in]
            if cur not in allowed:
                return False
        priority_is = cond.get("priorityIs") or cond.get("priority_is")
        if priority_is is not None:
            if str(_enum_val(issue.priority)) != str(priority_is):
                return False
        has_label = cond.get("hasLabel")
        if has_label is None:
            has_label = cond.get("has_label")
        if has_label is not None:
            if not await self._issue_has_label(issue.id, issue.workspace_id, has_label):
                return False
        return True

    async def _issue_has_label(
        self, issue_id: str, workspace_id: str, has_label: Any
    ) -> bool:
        if isinstance(has_label, int) or (isinstance(has_label, str) and has_label.isdigit()):
            tag_id = int(has_label)
            q = await self.db.execute(
                select(IssueTag).where(
                    IssueTag.issue_id == issue_id, IssueTag.tag_id == tag_id
                )
            )
            return q.scalar_one_or_none() is not None
        name = str(has_label).strip()
        stmt = (
            select(IssueTag)
            .join(Tag, Tag.id == IssueTag.tag_id)
            .where(
                IssueTag.issue_id == issue_id,
                Tag.workspace_id == workspace_id,
                Tag.name == name,
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def _execute_action(
        self,
        rule: AutomationRule,
        *,
        issue: Issue,
        actor_user_id: Optional[str],
    ) -> None:
        token = _automation_depth.set(_automation_depth.get() + 1)
        try:
            # Refresh issue in case prior rules mutated it
            fresh = await self.db.get(Issue, issue.id)
            if not fresh or getattr(fresh, "is_deleted", False):
                return
            issue = fresh
            action = rule.action_type
            cfg = rule.action_config_json or {}
            actor = actor_user_id or rule.created_by or issue.created_by
            if not actor:
                logger.warning("automation: no actor for rule %s", rule.id)
                return

            # Lazy import to avoid circular deps
            from opentask.services.issue_service import IssueService
            from opentask.services.tag.service import TagService

            if action == "set_status":
                status = cfg.get("status")
                if not status:
                    raise ValueError("set_status 需要 status")
                await IssueService(self.db).update_issue(
                    issue.id, IssueUpdate(status=status), actor
                )
            elif action == "set_assignee":
                assignee_id = cfg.get("assigneeId") or cfg.get("assignee_id")
                await IssueService(self.db).update_issue(
                    issue.id, IssueUpdate(assignee_id=assignee_id), actor
                )
            elif action == "set_priority":
                priority = cfg.get("priority")
                if not priority:
                    raise ValueError("set_priority 需要 priority")
                await IssueService(self.db).update_issue(
                    issue.id, IssueUpdate(priority=priority), actor
                )
            elif action == "add_label":
                tag_id = cfg.get("tagId") if "tagId" in cfg else cfg.get("tag_id")
                if tag_id is None:
                    raise ValueError("add_label 需要 tagId")
                await TagService(self.db).attach_tag(
                    issue_id=issue.id,
                    tag_id=int(tag_id),
                    workspace_id=issue.workspace_id,
                    user_id=actor,
                )
            elif action == "add_comment":
                content = (cfg.get("content") or "").strip()
                if not content:
                    raise ValueError("add_comment 需要 content")
                body = content if content.startswith("[automation]") else f"[automation] {content}"
                await IssueService(self.db).add_comment(
                    issue.id,
                    body,
                    actor,
                    comment_type="system",
                    meta_data={
                        "source": "automation",
                        "ruleId": rule.id,
                        "ruleName": rule.name,
                    },
                )
            else:
                raise ValueError(f"未知 action: {action}")
        finally:
            _automation_depth.reset(token)


async def fire_automations(
    db: AsyncSession,
    *,
    workspace_id: Optional[str],
    trigger_type: str,
    issue: Optional[Issue],
    actor_user_id: Optional[str] = None,
    event: Optional[dict[str, Any]] = None,
) -> None:
    """Module-level helper for write-path hooks."""
    if not workspace_id or issue is None:
        return
    try:
        await AutomationService(db).run_for_event(
            workspace_id=workspace_id,
            trigger_type=trigger_type,
            issue=issue,
            actor_user_id=actor_user_id,
            event=event,
        )
    except Exception:
        logger.exception("automation fire failed trigger=%s", trigger_type)
