"""Issue template service (E9-S2)"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue_template.model import IssueTemplate
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.issue_template.seeds import BUILTIN_SEEDS, builtin_payload


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def serialize_issue_template(row: IssueTemplate) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "name": row.name,
        "description": row.description,
        "icon": row.icon,
        "payload": row.payload or {},
        "sortOrder": row.sort_order,
        "source": row.source,
        "seedKey": row.seed_key,
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


class IssueTemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_seeds(self, *, workspace_id: str, user_id: str | None = None) -> None:
        result = await self.db.execute(
            select(IssueTemplate.seed_key).where(
                IssueTemplate.workspace_id == workspace_id,
                IssueTemplate.seed_key.is_not(None),
            )
        )
        existing = {k for k in result.scalars().all() if k}
        now = datetime.utcnow()
        added = False
        for seed in BUILTIN_SEEDS:
            if seed["seed_key"] in existing:
                continue
            row = IssueTemplate(
                workspace_id=workspace_id,
                name=seed["name"],
                description=seed["description"],
                icon=seed["icon"],
                payload=builtin_payload(seed),
                sort_order=seed["sort_order"],
                source="seed",
                seed_key=seed["seed_key"],
                created_by=user_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
            added = True
        if added:
            try:
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                # race / already seeded
                return

    async def list(
        self, *, workspace_id: str, user_id: str | None = None, ensure: bool = True
    ) -> list[IssueTemplate]:
        if ensure:
            await self.ensure_seeds(workspace_id=workspace_id, user_id=user_id)
        result = await self.db.execute(
            select(IssueTemplate)
            .where(IssueTemplate.workspace_id == workspace_id)
            .order_by(IssueTemplate.sort_order.asc(), IssueTemplate.name.asc())
        )
        return list(result.scalars().all())

    async def get(self, *, workspace_id: str, template_id: str) -> IssueTemplate:
        result = await self.db.execute(
            select(IssueTemplate).where(
                IssueTemplate.id == template_id,
                IssueTemplate.workspace_id == workspace_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
        return row

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        name: str,
        description: str | None = None,
        icon: str | None = None,
        payload: dict[str, Any] | None = None,
        sort_order: int = 0,
    ) -> IssueTemplate:
        row = IssueTemplate(
            workspace_id=workspace_id,
            name=name,
            description=description,
            icon=icon,
            payload=payload or {},
            sort_order=sort_order,
            source="custom",
            seed_key=None,
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(row)
        try:
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="模板名称已存在",
            ) from e
        await self.db.refresh(row)
        return row

    async def update(
        self,
        *,
        workspace_id: str,
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        sort_order: Optional[int] = None,
    ) -> IssueTemplate:
        row = await self.get(workspace_id=workspace_id, template_id=template_id)
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        if icon is not None:
            row.icon = icon
        if payload is not None:
            row.payload = payload
        if sort_order is not None:
            row.sort_order = sort_order
        row.updated_at = datetime.utcnow()
        try:
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="模板名称已存在",
            ) from e
        await self.db.refresh(row)
        return row

    async def delete(self, *, workspace_id: str, template_id: str) -> None:
        row = await self.get(workspace_id=workspace_id, template_id=template_id)
        await self.db.delete(row)
        await self.db.commit()

    def merge_payload_into_create_dict(
        self, payload: dict[str, Any], body: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply template payload then overlay explicit body fields."""
        merged = dict(body)
        if payload.get("type") and (
            "type" not in body or body.get("type") in (None, "bug")
        ):
            # IssueCreate defaults type=bug; treat default bug as overridable when
            # template provides type and caller didn't send a non-default intent.
            # Safer: if template_id present, always apply type/priority/description
            # unless body explicitly set non-empty description / non-default fields.
            pass
        # Explicit merge policy for tests: template fills type, priority, description
        # when body omits them or leaves description empty; title always from body if set.
        if payload.get("type"):
            merged["type"] = payload["type"] if body.get("_use_template_type", True) else body.get("type")
        # Simpler fixed policy used by router:
        return merged

    @staticmethod
    def apply_template_defaults(payload: dict[str, Any], data_dict: dict[str, Any]) -> dict[str, Any]:
        """
        data_dict is IssueCreate.model_dump().
        Overlay: template type/priority always applied; description if empty;
        title if empty and payload.title set.
        Caller may then re-apply explicit overrides.
        """
        out = dict(data_dict)
        if payload.get("type"):
            out["type"] = payload["type"]
        if payload.get("priority"):
            out["priority"] = payload["priority"]
        if payload.get("projectId") and not out.get("project_id"):
            out["project_id"] = payload["projectId"]
        desc = out.get("description")
        if (desc is None or desc == "") and payload.get("description"):
            out["description"] = payload["description"]
        title = out.get("title")
        if (title is None or title == "") and payload.get("title"):
            out["title"] = payload["title"]
        return out
