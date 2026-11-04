"""E60/E62: dialect-aware search backends (PG tsvector / SQLite FTS5 / ILIKE fallback)."""
from __future__ import annotations

import re
from typing import Any, Protocol

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.entity_document.model import EntityDocument
from opentask.models.issue.enums import CommentType
from opentask.models.issue.model import Issue, IssueComment
from opentask.models.requirement.model import Project

INDEX_BODY_MAX = 16000
SNIPPET_MAX = 120

ISSUE_CODE_RE = re.compile(
    r"^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$", re.IGNORECASE
)


def _clip(value: str | None, n: int = SNIPPET_MAX) -> str:
    return (value or "").strip().replace("\n", " ")[:n]


def _truncate_for_index(value: str | None) -> str:
    return (value or "")[:INDEX_BODY_MAX]


class SearchBackend(Protocol):
    async def search_issues(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]: ...

    async def search_projects(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]: ...

    async def search_docs(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]: ...

    async def search_comments(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]: ...


def resolve_search_backend(session: AsyncSession) -> SearchBackend:
    bind = session.bind
    dialect = getattr(getattr(bind, "dialect", None), "name", None) or ""
    if dialect == "postgresql":
        return PostgresFTSBackend(session)
    if dialect == "sqlite":
        return SQLiteFTSBackend(session)
    return ILikeSearchBackend(session)


def _issue_payload(i: Issue, *, rank: float | None = None, snippet: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": i.id,
        "issueCode": i.issue_code,
        "title": i.title,
        "status": i.status.value if hasattr(i.status, "value") else i.status,
        "priority": i.priority.value if hasattr(i.priority, "value") else i.priority,
    }
    if rank is not None:
        out["rank"] = float(rank)
    if snippet is not None:
        out["snippet"] = snippet
    return out


def _project_payload(p: Project, *, rank: float | None = None, snippet: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": p.id,
        "name": p.name,
        "description": (p.description or "")[:160],
        "isActive": bool(p.is_active),
    }
    if rank is not None:
        out["rank"] = float(rank)
    if snippet is not None:
        out["snippet"] = snippet
    return out


def _doc_payload(d: EntityDocument, *, rank: float | None = None, snippet: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": d.id,
        "title": d.title,
        "parentType": d.parent_type,
        "parentId": d.parent_id,
        "snippet": snippet if snippet is not None else _clip(d.body_md),
    }
    if rank is not None:
        out["rank"] = float(rank)
    return out


def _comment_payload(
    *,
    comment_id: str,
    issue_id: str,
    issue_code: str,
    content: str | None,
    author_user_id: str | None = None,
    created_at: Any = None,
    rank: float | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": comment_id,
        "issueId": issue_id,
        "issueCode": issue_code,
        "snippet": _clip(content),
    }
    if rank is not None:
        out["rank"] = float(rank)
    if author_user_id is not None:
        out["authorUserId"] = author_user_id
    if created_at is not None:
        out["createdAt"] = (
            created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
        )
    return out


class ILikeSearchBackend:
    """Safe fallback (unknown dialect) + baseline behavior with description."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_issues(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        pattern = f"%{q}%"
        result = await self.session.execute(
            select(Issue)
            .where(
                Issue.workspace_id == workspace_id,
                or_(
                    Issue.title.ilike(pattern),
                    Issue.issue_code.ilike(pattern),
                    Issue.legacy_issue_code.ilike(pattern),
                    Issue.description.ilike(pattern),
                ),
            )
            .order_by(Issue.updated_at.desc())
            .limit(limit)
        )
        return [
            _issue_payload(i, rank=0.0, snippet=_clip(i.description))
            for i in result.scalars().all()
        ]

    async def search_projects(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        pattern = f"%{q}%"
        result = await self.session.execute(
            select(Project)
            .where(
                Project.workspace_id == workspace_id,
                or_(
                    Project.name.ilike(pattern),
                    Project.description.ilike(pattern),
                ),
            )
            .order_by(Project.updated_at.desc())
            .limit(limit)
        )
        return [
            _project_payload(p, rank=0.0, snippet=_clip(p.description))
            for p in result.scalars().all()
        ]

    async def search_docs(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        pattern = f"%{q}%"
        result = await self.session.execute(
            select(EntityDocument)
            .where(
                EntityDocument.workspace_id == workspace_id,
                or_(
                    EntityDocument.title.ilike(pattern),
                    EntityDocument.body_md.ilike(pattern),
                ),
            )
            .order_by(EntityDocument.updated_at.desc())
            .limit(limit)
        )
        return [
            _doc_payload(d, rank=0.0)
            for d in result.scalars().all()
        ]

    async def search_comments(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        pattern = f"%{q}%"
        result = await self.session.execute(
            select(IssueComment, Issue)
            .join(Issue, Issue.id == IssueComment.issue_id)
            .where(
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
                IssueComment.is_deleted == False,  # noqa: E712
                IssueComment.comment_type == CommentType.COMMENT,
                IssueComment.content.ilike(pattern),
            )
            .order_by(IssueComment.created_at.desc())
            .limit(limit)
        )
        out: list[dict[str, Any]] = []
        for comment, issue in result.all():
            out.append(
                _comment_payload(
                    comment_id=comment.id,
                    issue_id=issue.id,
                    issue_code=issue.issue_code,
                    content=comment.content,
                    author_user_id=comment.user_id,
                    created_at=comment.created_at,
                    rank=0.0,
                )
            )
        return out


class PostgresFTSBackend:
    """Q1a: simple config + plainto_tsquery; Q5a rank DESC then updated_at."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_issues(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT id, issue_code, title, status, priority, description,
                   ts_rank(search_tsv, plainto_tsquery('simple', :q)) AS rank
            FROM issues
            WHERE workspace_id = :ws
              AND search_tsv @@ plainto_tsquery('simple', :q)
            ORDER BY rank DESC, updated_at DESC
            LIMIT :lim
            """
        )
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    sql, {"q": q, "ws": workspace_id, "lim": limit}
                )
                rows = list(result.mappings().all())
        except Exception:
            return await ILikeSearchBackend(self.session).search_issues(
                workspace_id, q, limit
            )
        return [
            {
                "id": r["id"],
                "issueCode": r["issue_code"],
                "title": r["title"],
                "status": r["status"],
                "priority": r["priority"],
                "rank": float(r["rank"] or 0),
                "snippet": _clip(r["description"]),
            }
            for r in rows
        ]

    async def search_projects(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT id, name, description, is_active,
                   ts_rank(search_tsv, plainto_tsquery('simple', :q)) AS rank
            FROM projects
            WHERE workspace_id = :ws
              AND search_tsv @@ plainto_tsquery('simple', :q)
            ORDER BY rank DESC, updated_at DESC
            LIMIT :lim
            """
        )
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    sql, {"q": q, "ws": workspace_id, "lim": limit}
                )
                rows = list(result.mappings().all())
        except Exception:
            return await ILikeSearchBackend(self.session).search_projects(
                workspace_id, q, limit
            )
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": (r["description"] or "")[:160],
                "isActive": bool(r["is_active"]),
                "rank": float(r["rank"] or 0),
                "snippet": _clip(r["description"]),
            }
            for r in rows
        ]

    async def search_docs(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT id, title, parent_type, parent_id, body_md,
                   ts_rank(search_tsv, plainto_tsquery('simple', :q)) AS rank
            FROM entity_documents
            WHERE workspace_id = :ws
              AND search_tsv @@ plainto_tsquery('simple', :q)
            ORDER BY rank DESC, updated_at DESC
            LIMIT :lim
            """
        )
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    sql, {"q": q, "ws": workspace_id, "lim": limit}
                )
                rows = list(result.mappings().all())
        except Exception:
            return await ILikeSearchBackend(self.session).search_docs(
                workspace_id, q, limit
            )
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "parentType": r["parent_type"],
                "parentId": r["parent_id"],
                "snippet": _clip(r["body_md"]),
                "rank": float(r["rank"] or 0),
            }
            for r in rows
        ]

    async def search_comments(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT c.id, c.issue_id, i.issue_code, c.content, c.user_id, c.created_at,
                   ts_rank(c.search_tsv, plainto_tsquery('simple', :q)) AS rank
            FROM issue_comments c
            JOIN issues i ON i.id = c.issue_id
            WHERE i.workspace_id = :ws
              AND i.is_deleted = false
              AND c.is_deleted = false
              AND c.comment_type = 'comment'
              AND c.search_tsv @@ plainto_tsquery('simple', :q)
            ORDER BY rank DESC, c.created_at DESC
            LIMIT :lim
            """
        )
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    sql, {"q": q, "ws": workspace_id, "lim": limit}
                )
                rows = list(result.mappings().all())
        except Exception:
            return await ILikeSearchBackend(self.session).search_comments(
                workspace_id, q, limit
            )
        return [
            _comment_payload(
                comment_id=r["id"],
                issue_id=r["issue_id"],
                issue_code=r["issue_code"],
                content=r["content"],
                author_user_id=r["user_id"],
                created_at=r["created_at"],
                rank=float(r["rank"] or 0),
            )
            for r in rows
        ]


class SQLiteFTSBackend:
    """Q3a FTS5 external-content-style tables (id UNINDEXED) + MATCH/bm25."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_issues(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT i.id, i.issue_code, i.title, i.status, i.priority, i.description,
                   bm25(issues_fts) AS rank
            FROM issues_fts
            JOIN issues i ON i.id = issues_fts.id
            WHERE issues_fts MATCH :q
              AND issues_fts.workspace_id = :ws
            ORDER BY rank ASC, i.updated_at DESC
            LIMIT :lim
            """
        )
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    sql, {"q": q, "ws": workspace_id, "lim": limit}
                )
                rows = list(result.mappings().all())
        except Exception:
            return await ILikeSearchBackend(self.session).search_issues(
                workspace_id, q, limit
            )
        out = []
        for r in rows:
            # bm25: lower is better → invert for rank DESC semantics
            bm = float(r["rank"] or 0)
            out.append(
                {
                    "id": r["id"],
                    "issueCode": r["issue_code"],
                    "title": r["title"],
                    "status": r["status"],
                    "priority": r["priority"],
                    "rank": -bm,
                    "snippet": _clip(r["description"]),
                }
            )
        return out

    async def search_projects(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT p.id, p.name, p.description, p.is_active,
                   bm25(projects_fts) AS rank
            FROM projects_fts
            JOIN projects p ON p.id = projects_fts.id
            WHERE projects_fts MATCH :q
              AND projects_fts.workspace_id = :ws
            ORDER BY rank ASC, p.updated_at DESC
            LIMIT :lim
            """
        )
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    sql, {"q": q, "ws": workspace_id, "lim": limit}
                )
                rows = list(result.mappings().all())
        except Exception:
            return await ILikeSearchBackend(self.session).search_projects(
                workspace_id, q, limit
            )
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": (r["description"] or "")[:160],
                "isActive": bool(r["is_active"]),
                "rank": -float(r["rank"] or 0),
                "snippet": _clip(r["description"]),
            }
            for r in rows
        ]

    async def search_docs(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT d.id, d.title, d.parent_type, d.parent_id, d.body_md,
                   bm25(entity_documents_fts) AS rank
            FROM entity_documents_fts
            JOIN entity_documents d ON d.id = entity_documents_fts.id
            WHERE entity_documents_fts MATCH :q
              AND entity_documents_fts.workspace_id = :ws
            ORDER BY rank ASC, d.updated_at DESC
            LIMIT :lim
            """
        )
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    sql, {"q": q, "ws": workspace_id, "lim": limit}
                )
                rows = list(result.mappings().all())
        except Exception:
            return await ILikeSearchBackend(self.session).search_docs(
                workspace_id, q, limit
            )
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "parentType": r["parent_type"],
                "parentId": r["parent_id"],
                "snippet": _clip(r["body_md"]),
                "rank": -float(r["rank"] or 0),
            }
            for r in rows
        ]

    async def search_comments(
        self, workspace_id: str, q: str, limit: int
    ) -> list[dict[str, Any]]:
        sql = text(
            """
            SELECT c.id, c.issue_id, i.issue_code, c.content, c.user_id, c.created_at,
                   bm25(issue_comments_fts) AS rank
            FROM issue_comments_fts
            JOIN issue_comments c ON c.id = issue_comments_fts.id
            JOIN issues i ON i.id = c.issue_id
            WHERE issue_comments_fts MATCH :q
              AND i.workspace_id = :ws
              AND i.is_deleted = 0
              AND c.is_deleted = 0
              AND c.comment_type = 'comment'
            ORDER BY rank ASC, c.created_at DESC
            LIMIT :lim
            """
        )
        try:
            async with self.session.begin_nested():
                result = await self.session.execute(
                    sql, {"q": q, "ws": workspace_id, "lim": limit}
                )
                rows = list(result.mappings().all())
        except Exception:
            return await ILikeSearchBackend(self.session).search_comments(
                workspace_id, q, limit
            )
        return [
            _comment_payload(
                comment_id=r["id"],
                issue_id=r["issue_id"],
                issue_code=r["issue_code"],
                content=r["content"],
                author_user_id=r["user_id"],
                created_at=r["created_at"],
                rank=-float(r["rank"] or 0),
            )
            for r in rows
        ]

