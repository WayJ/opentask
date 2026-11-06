"""E98: resolve a reliable writable Workspace for Issue create (KEY-N scope).

Never uses cross-tenant fallbacks (_resolve_fallback_workspace_id / earliest / Default).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.workspace.model import Workspace, WorkspaceMember

WRITABLE_ROLES = frozenset({"owner", "member"})

WORKSPACE_REQUIRED_DETAIL = (
    "workspace_required: Issue identifiers are KEY-N scoped to a workspace. "
    "Provide X-Workspace-Id, or ensure the caller has exactly one writable workspace. "
    "Year-prefixed ISSUE{year}-N allocation is removed."
)


class WorkspaceRequiredError(ValueError):
    """Raised when Issue create cannot reliably bind a workspace. Map to HTTP 400."""

    def __init__(self, detail: str = WORKSPACE_REQUIRED_DETAIL) -> None:
        super().__init__(detail)
        self.detail = detail


async def list_writable_workspace_ids(
    session: AsyncSession, user_id: str
) -> list[str]:
    result = await session.execute(
        select(WorkspaceMember.workspace_id).where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.role.in_(tuple(WRITABLE_ROLES)),
        )
    )
    return [row[0] for row in result.all()]


async def _user_can_write(session: AsyncSession, user_id: str, workspace_id: str) -> bool:
    result = await session.execute(
        select(WorkspaceMember.id).where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role.in_(tuple(WRITABLE_ROLES)),
        ).limit(1)
    )
    return result.first() is not None


async def resolve_workspace_for_issue_create(
    session: AsyncSession,
    user_id: str,
    *,
    explicit_workspace_id: str | None = None,
    project_id: str | None = None,
) -> str:
    """Return workspace_id for KEY-N allocation.

    Priority (Scheme A / Q2a / Q5a):
    1. explicit_workspace_id (header / already-resolved context)
    2. project_id → project.workspace_id when set and caller is writable there
       (reliable, not a cross-tenant guess)
    3. exactly one personal-default WS (created_by == user, role=owner) when
       the user has multiple writable memberships
    4. exactly one writable membership (owner|member; viewer excluded)
    Otherwise raise WorkspaceRequiredError.
    """
    if explicit_workspace_id:
        return explicit_workspace_id

    if project_id:
        from opentask.models.requirement.model import Project

        proj = (
            await session.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if proj is not None and proj.workspace_id:
            if await _user_can_write(session, user_id, proj.workspace_id):
                return proj.workspace_id
            # Project has WS but caller cannot write → still 400 (do not guess another)

    writable = await list_writable_workspace_ids(session, user_id)
    if len(writable) == 1:
        return writable[0]
    if len(writable) == 0:
        raise WorkspaceRequiredError()

    personal = await session.execute(
        select(Workspace.id)
        .join(
            WorkspaceMember,
            WorkspaceMember.workspace_id == Workspace.id,
        )
        .where(
            Workspace.created_by == user_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.role == "owner",
            Workspace.id.in_(writable),
        )
    )
    personal_ids = [row[0] for row in personal.all()]
    if len(personal_ids) == 1:
        return personal_ids[0]

    raise WorkspaceRequiredError()
