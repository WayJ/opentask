"""EntityDocument service (E10-S3) — Issue/Project/Initiative only."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.entity_document.model import ENTITY_DOC_PARENT_TYPES, EntityDocument
from opentask.models.initiative.model import Initiative
from opentask.models.issue.model import Issue
from opentask.models.requirement.model import Project
from opentask.models.workspace.model import WorkspaceMember


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def serialize_entity_document(row: EntityDocument) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "parentType": row.parent_type,
        "parentId": row.parent_id,
        "title": row.title,
        "bodyMd": row.body_md or "",
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


class EntityDocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _assert_parent(self, *, workspace_id: str, parent_type: str, parent_id: str) -> None:
        if parent_type not in ENTITY_DOC_PARENT_TYPES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"parentType 仅允许: {', '.join(ENTITY_DOC_PARENT_TYPES)}（不含 requirement/PGE）",
            )
        if parent_type == "initiative":
            q = select(Initiative.id).where(
                Initiative.id == parent_id, Initiative.workspace_id == workspace_id
            )
        elif parent_type == "project":
            q = select(Project.id).where(
                Project.id == parent_id, Project.workspace_id == workspace_id
            )
        else:
            q = select(Issue.id).where(Issue.id == parent_id, Issue.workspace_id == workspace_id)
        found = (await self.db.execute(q)).scalar_one_or_none()
        if not found:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="父实体不存在或不属于当前工作区",
            )

    async def get(self, *, workspace_id: str, doc_id: str) -> EntityDocument:
        result = await self.db.execute(
            select(EntityDocument).where(
                EntityDocument.id == doc_id,
                EntityDocument.workspace_id == workspace_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="文档不存在")
        return row

    async def list(
        self, *, workspace_id: str, parent_type: str, parent_id: str
    ) -> list[EntityDocument]:
        if parent_type not in ENTITY_DOC_PARENT_TYPES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"parentType 仅允许: {', '.join(ENTITY_DOC_PARENT_TYPES)}",
            )
        # Soft isolation: if parent not in WS, return empty (or 404). Prefer empty for list.
        try:
            await self._assert_parent(
                workspace_id=workspace_id, parent_type=parent_type, parent_id=parent_id
            )
        except HTTPException as e:
            if e.status_code == 404:
                return []
            raise
        result = await self.db.execute(
            select(EntityDocument)
            .where(
                EntityDocument.workspace_id == workspace_id,
                EntityDocument.parent_type == parent_type,
                EntityDocument.parent_id == parent_id,
            )
            .order_by(EntityDocument.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        parent_type: str,
        parent_id: str,
        title: str,
        body_md: str = "",
    ) -> EntityDocument:
        await self._assert_parent(
            workspace_id=workspace_id, parent_type=parent_type, parent_id=parent_id
        )
        now = datetime.utcnow()
        row = EntityDocument(
            workspace_id=workspace_id,
            parent_type=parent_type,
            parent_id=parent_id,
            title=title.strip(),
            body_md=body_md or "",
            created_by=user_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update(
        self,
        *,
        workspace_id: str,
        doc_id: str,
        title: Optional[str] = None,
        body_md: Optional[str] = None,
    ) -> EntityDocument:
        row = await self.get(workspace_id=workspace_id, doc_id=doc_id)
        if title is not None:
            row.title = title.strip()
        if body_md is not None:
            row.body_md = body_md
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete(self, *, workspace_id: str, doc_id: str) -> None:
        row = await self.get(workspace_id=workspace_id, doc_id=doc_id)
        await self.db.delete(row)
        await self.db.commit()
