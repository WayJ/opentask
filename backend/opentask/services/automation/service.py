"""Automation rules CRUD + after-commit executor (E26)."""
from __future__ import annotations

import contextvars
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.automation.model import (
    ACTION_TYPES,
    CF_CONDITION_OPS,
    MAX_DELAY_MINUTES,
    TRIGGER_TYPES,
    AutomationPendingAction,
    AutomationRule,
)
from opentask.models.custom_field.model import CustomField, IssueCustomFieldValue
from opentask.models.issue.model import Issue, IssueTag
from opentask.models.issue.schema import IssueUpdate
from opentask.models.tag.model import Tag
from opentask.models.workspace.model import WorkspaceMember

logger = logging.getLogger(__name__)

MAX_CUSTOM_FIELD_CONDITIONS = 5

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


def serialize_pending(row: AutomationPendingAction) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "ruleId": row.rule_id,
        "issueId": row.issue_id,
        "actionType": row.action_type,
        "actionConfig": row.action_config_json or {},
        "runAt": row.run_at.isoformat() if row.run_at else None,
        "status": row.status,
        "actorUserId": row.actor_user_id,
        "errorMessage": row.error_message,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "executedAt": row.executed_at.isoformat() if row.executed_at else None,
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
        self._validate_condition(condition)
        self._validate_action_config(action_config)
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
            self._validate_condition(condition)
            row.condition_json = condition
        if action_type is not None:
            if action_type not in ACTION_TYPES:
                raise HTTPException(status_code=400, detail=f"非法 action: {action_type}")
            row.action_type = action_type
        if set_action_config:
            self._validate_action_config(action_config)
            row.action_config_json = dict(action_config or {})
        if enabled is not None:
            row.enabled = bool(enabled)
        if position is not None:
            row.position = position
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        if enabled is not None and not enabled:
            await self.cancel_pending_for_rule(workspace_id=workspace_id, rule_id=rule_id)
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

    @staticmethod
    def _validate_condition(condition: Optional[dict]) -> None:
        """E36: customFields AND list max 5."""
        if not condition or not isinstance(condition, dict):
            return
        cfs = condition.get("customFields")
        if cfs is None:
            cfs = condition.get("custom_fields")
        if cfs is None:
            return
        if not isinstance(cfs, list):
            raise HTTPException(status_code=400, detail="customFields 须为数组")
        if len(cfs) > MAX_CUSTOM_FIELD_CONDITIONS:
            raise HTTPException(
                status_code=400,
                detail=f"customFields 最多 {MAX_CUSTOM_FIELD_CONDITIONS} 条",
            )

    @staticmethod
    def parse_delay_minutes(cfg: Optional[dict]) -> int:
        """Return delay minutes; 0 = immediate. Raises 400 if invalid."""
        if not cfg or not isinstance(cfg, dict):
            return 0
        raw = cfg.get("delay_minutes")
        if raw is None:
            raw = cfg.get("delayMinutes")
        if raw is None:
            return 0
        if isinstance(raw, bool):
            raise HTTPException(status_code=400, detail="delay_minutes 非法")
        if isinstance(raw, float):
            if not raw.is_integer():
                raise HTTPException(status_code=400, detail="delay_minutes 非法")
            raw = int(raw)
        if not isinstance(raw, int):
            raise HTTPException(status_code=400, detail="delay_minutes 非法")
        if raw < 0 or raw > MAX_DELAY_MINUTES:
            raise HTTPException(
                status_code=400,
                detail=f"delay_minutes 须在 0…{MAX_DELAY_MINUTES}",
            )
        return raw

    @staticmethod
    def strip_delay(cfg: Optional[dict]) -> dict:
        out = dict(cfg or {})
        out.pop("delay_minutes", None)
        out.pop("delayMinutes", None)
        return out

    @classmethod
    def _validate_action_config(cls, action_config: Optional[dict]) -> None:
        if action_config is None:
            return
        if not isinstance(action_config, dict):
            raise HTTPException(status_code=400, detail="actionConfig 须为对象")
        cls.parse_delay_minutes(action_config)

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
                await self._enqueue_or_execute(
                    rule,
                    issue=issue,
                    workspace_id=workspace_id,
                    actor_user_id=actor_user_id or rule.created_by,
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
        if t == "custom_field_changed":
            # Optional field filter: field_key / key / field_id / fieldId
            want_key = cfg.get("field_key")
            if want_key is None:
                want_key = cfg.get("key")
            want_id = cfg.get("field_id")
            if want_id is None:
                want_id = cfg.get("fieldId")
            ev_key = event.get("field_key") or event.get("key")
            ev_id = event.get("field_id") or event.get("fieldId")
            if want_key is not None and str(ev_key or "") != str(want_key):
                return False
            if want_id is not None and str(ev_id or "") != str(want_id):
                return False
            if cfg.get("from") is not None and event.get("from") != cfg.get("from"):
                # Also allow string compare for scalars
                if str(event.get("from")) != str(cfg.get("from")):
                    return False
            if cfg.get("to") is not None and event.get("to") != cfg.get("to"):
                if str(event.get("to")) != str(cfg.get("to")):
                    return False
            return True
        if t == "issue.sla_breached":
            # E45: no trigger_config filters in v1
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
        cf_list = cond.get("customFields")
        if cf_list is None:
            cf_list = cond.get("custom_fields")
        if cf_list is not None:
            if not isinstance(cf_list, list):
                return False
            for item in cf_list:
                if not await self._match_custom_field_condition(issue, item):
                    return False
        else:
            cf_cond = cond.get("customField")
            if cf_cond is None:
                cf_cond = cond.get("custom_field")
            if cf_cond is not None:
                if not await self._match_custom_field_condition(issue, cf_cond):
                    return False
        return True

    async def _resolve_custom_field(
        self, *, workspace_id: str, ref: dict[str, Any]
    ) -> Optional[CustomField]:
        """Resolve by fieldId/id or key. Unknown → None (no raise)."""
        if not isinstance(ref, dict):
            return None
        field_id = ref.get("fieldId") or ref.get("field_id") or ref.get("id")
        key = ref.get("key")
        if field_id:
            row = (
                await self.db.execute(
                    select(CustomField).where(
                        CustomField.id == str(field_id),
                        CustomField.workspace_id == workspace_id,
                    )
                )
            ).scalar_one_or_none()
            return row
        if key:
            row = (
                await self.db.execute(
                    select(CustomField).where(
                        CustomField.workspace_id == workspace_id,
                        CustomField.key == str(key),
                    )
                )
            ).scalar_one_or_none()
            return row
        return None

    async def _issue_cf_value(self, issue_id: str, field_id: str) -> Any:
        row = (
            await self.db.execute(
                select(IssueCustomFieldValue).where(
                    IssueCustomFieldValue.issue_id == issue_id,
                    IssueCustomFieldValue.field_id == field_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return row.value_json

    @staticmethod
    def _cf_is_empty(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and value == "":
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        return False

    async def _match_custom_field_condition(
        self, issue: Issue, cf_cond: Any
    ) -> bool:
        """E33: customField condition. Unknown field → False (no 500)."""
        if not isinstance(cf_cond, dict):
            return False
        field = await self._resolve_custom_field(
            workspace_id=issue.workspace_id, ref=cf_cond
        )
        if field is None:
            return False
        op = str(cf_cond.get("op") or "eq").strip().lower()
        if op not in CF_CONDITION_OPS:
            return False
        current = await self._issue_cf_value(issue.id, field.id)
        expected = cf_cond.get("value")

        if op == "is_set":
            return not self._cf_is_empty(current)
        if op == "is_empty":
            return self._cf_is_empty(current)
        if op == "eq":
            return current == expected
        if op == "neq":
            return current != expected
        if op == "contains":
            if field.type == "multi_select":
                if not isinstance(current, list):
                    return False
                return expected in current
            if field.type == "text":
                if not isinstance(current, str) or expected is None:
                    return False
                return str(expected) in current
            # other types: degrade to eq
            return current == expected
        return False

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
        config_override: Optional[dict] = None,
        action_type_override: Optional[str] = None,
    ) -> None:
        token = _automation_depth.set(_automation_depth.get() + 1)
        try:
            # Refresh issue in case prior rules mutated it
            fresh = await self.db.get(Issue, issue.id)
            if not fresh or getattr(fresh, "is_deleted", False):
                return
            issue = fresh
            action = action_type_override or rule.action_type
            if config_override is not None:
                cfg = dict(config_override)
            else:
                cfg = self.strip_delay(rule.action_config_json or {})
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
            elif action == "set_custom_field":
                from fastapi import HTTPException as FastAPIHTTPException

                from opentask.services.custom_field.service import (
                    CustomFieldService,
                    validate_value,
                )

                key = cfg.get("key")
                field_id = cfg.get("fieldId") if "fieldId" in cfg else cfg.get("field_id")
                if key is None and field_id is None:
                    raise ValueError("set_custom_field 需要 key 或 fieldId")
                svc = CustomFieldService(self.db)
                try:
                    if field_id is not None:
                        field = await svc.get(
                            workspace_id=issue.workspace_id, field_id=str(field_id)
                        )
                    else:
                        field = await svc.get_by_key(
                            workspace_id=issue.workspace_id, key=str(key)
                        )
                    if field.archived_at is not None:
                        raise FastAPIHTTPException(
                            status_code=400, detail=f"字段 {field.key} 已归档，不可写入"
                        )
                    # Pre-validate so we never dirty the shared request session
                    validate_value(field, cfg.get("value"))
                except FastAPIHTTPException as exc:
                    logger.warning(
                        "automation set_custom_field failed rule=%s issue=%s: %s",
                        rule.id,
                        issue.id,
                        getattr(exc, "detail", exc),
                    )
                    return
                entry: dict[str, Any] = {
                    "fieldId": field.id,
                    "value": cfg.get("value"),
                }
                await svc.upsert_issue_values(
                    workspace_id=issue.workspace_id,
                    issue_id=issue.id,
                    entries=[entry],
                )
            else:
                raise ValueError(f"未知 action: {action}")
        finally:
            _automation_depth.reset(token)


    async def _enqueue_or_execute(
        self,
        rule: AutomationRule,
        *,
        issue: Issue,
        workspace_id: str,
        actor_user_id: Optional[str],
    ) -> None:
        delay = self.parse_delay_minutes(rule.action_config_json)
        cfg_exec = self.strip_delay(rule.action_config_json or {})
        actor = actor_user_id or rule.created_by
        if delay <= 0:
            await self._execute_action(
                rule,
                issue=issue,
                actor_user_id=actor,
                config_override=cfg_exec,
            )
            return
        existing = (
            await self.db.execute(
                select(AutomationPendingAction).where(
                    AutomationPendingAction.rule_id == rule.id,
                    AutomationPendingAction.issue_id == issue.id,
                    AutomationPendingAction.status == "pending",
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            logger.debug(
                "automation: skip enqueue dedupe rule=%s issue=%s",
                rule.id,
                issue.id,
            )
            return
        row = AutomationPendingAction(
            workspace_id=workspace_id,
            rule_id=rule.id,
            issue_id=issue.id,
            action_type=rule.action_type,
            action_config_json=cfg_exec,
            run_at=datetime.utcnow() + timedelta(minutes=delay),
            status="pending",
            actor_user_id=actor,
        )
        self.db.add(row)
        await self.db.commit()

    async def cancel_pending_for_rule(self, *, workspace_id: str, rule_id: str) -> int:
        stmt = select(AutomationPendingAction).where(
            AutomationPendingAction.workspace_id == workspace_id,
            AutomationPendingAction.rule_id == rule_id,
            AutomationPendingAction.status == "pending",
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        for row in rows:
            row.status = "cancelled"
            row.executed_at = datetime.utcnow()
        if rows:
            await self.db.commit()
        return len(rows)

    async def list_pending(
        self,
        *,
        workspace_id: str,
        status: str = "pending",
        limit: int = 100,
    ) -> list[AutomationPendingAction]:
        stmt = (
            select(AutomationPendingAction)
            .where(
                AutomationPendingAction.workspace_id == workspace_id,
                AutomationPendingAction.status == status,
            )
            .order_by(
                AutomationPendingAction.run_at.asc(),
                AutomationPendingAction.created_at.asc(),
            )
            .limit(min(max(limit, 1), 100))
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def run_due(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now = now or datetime.utcnow()
        stmt = (
            select(AutomationPendingAction)
            .where(
                AutomationPendingAction.workspace_id == workspace_id,
                AutomationPendingAction.status == "pending",
                AutomationPendingAction.run_at <= now,
            )
            .order_by(
                AutomationPendingAction.run_at.asc(),
                AutomationPendingAction.created_at.asc(),
            )
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        processed = 0
        executed = 0
        cancelled = 0
        failed = 0
        errors: list[dict[str, str]] = []

        for row in rows:
            pending_id = row.id
            rule_id = row.rule_id
            issue_id = row.issue_id
            processed += 1
            try:
                outcome = await self._process_pending_one(
                    row, workspace_id=workspace_id, tick_actor_user_id=actor_user_id
                )
                if outcome == "executed":
                    executed += 1
                elif outcome == "cancelled":
                    cancelled += 1
                elif outcome == "failed":
                    failed += 1
            except Exception as exc:  # noqa: BLE001 — per-row isolation
                await self.db.rollback()
                msg = str(exc)
                logger.exception("automation pending %s failed: %s", pending_id, msg)
                try:
                    fresh = await self.db.get(AutomationPendingAction, pending_id)
                    if fresh and fresh.status == "pending":
                        fresh.status = "failed"
                        fresh.error_message = msg[:1000]
                        fresh.executed_at = datetime.utcnow()
                        await self.db.commit()
                except Exception:  # noqa: BLE001
                    await self.db.rollback()
                    logger.exception("failed to mark pending %s failed", pending_id)
                failed += 1
                errors.append(
                    {
                        "pendingId": pending_id,
                        "ruleId": rule_id,
                        "issueId": issue_id,
                        "message": msg,
                    }
                )

        return {
            "processed": processed,
            "executed": executed,
            "cancelled": cancelled,
            "failed": failed,
            "errors": errors,
        }

    async def _process_pending_one(
        self,
        row: AutomationPendingAction,
        *,
        workspace_id: str,
        tick_actor_user_id: str,
    ) -> str:
        """Process one due pending. Returns executed|cancelled|failed."""
        pending_id = row.id
        rule_id = row.rule_id
        issue_id = row.issue_id
        row_ws = row.workspace_id
        action_type = row.action_type
        action_cfg = dict(row.action_config_json or {})
        actor_snap = row.actor_user_id

        rule = (
            await self.db.execute(
                select(AutomationRule).where(AutomationRule.id == rule_id)
            )
        ).scalar_one_or_none()
        if rule is None or not rule.enabled:
            fresh = await self.db.get(AutomationPendingAction, pending_id)
            if fresh is not None:
                fresh.status = "cancelled"
                fresh.executed_at = datetime.utcnow()
                await self.db.commit()
            return "cancelled"

        issue = await self.db.get(Issue, issue_id)
        if (
            issue is None
            or getattr(issue, "is_deleted", False)
            or issue.workspace_id != workspace_id
            or issue.workspace_id != row_ws
        ):
            fresh = await self.db.get(AutomationPendingAction, pending_id)
            if fresh is not None:
                fresh.status = "cancelled"
                fresh.executed_at = datetime.utcnow()
                await self.db.commit()
            return "cancelled"

        if not await self._match_condition(rule, issue):
            fresh = await self.db.get(AutomationPendingAction, pending_id)
            if fresh is not None:
                fresh.status = "cancelled"
                fresh.executed_at = datetime.utcnow()
                await self.db.commit()
            return "cancelled"

        actor = actor_snap or rule.created_by or tick_actor_user_id
        try:
            await self._execute_action(
                rule,
                issue=issue,
                actor_user_id=actor,
                config_override=action_cfg,
                action_type_override=action_type,
            )
            fresh = await self.db.get(AutomationPendingAction, pending_id)
            if fresh is None:
                return "executed"
            fresh.status = "done"
            fresh.executed_at = datetime.utcnow()
            fresh.error_message = None
            await self.db.commit()
            return "executed"
        except Exception as exc:  # noqa: BLE001
            await self.db.rollback()
            msg = str(exc)
            fresh = await self.db.get(AutomationPendingAction, pending_id)
            if fresh is not None:
                fresh.status = "failed"
                fresh.error_message = msg[:1000]
                fresh.executed_at = datetime.utcnow()
                await self.db.commit()
            return "failed"



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
