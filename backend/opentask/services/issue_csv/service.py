"""Issue CSV import / export (E28)."""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any, Iterable, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from opentask.models.cycle.model import Cycle
from opentask.models.issue.enums import IssuePriority, IssueStatus
from opentask.models.issue.model import Issue, IssueTag
from opentask.services.tag.service import load_tags_for_issues
from opentask.models.issue.schema import IssueCreate, IssueUpdate
from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.issue_service import IssueService

logger = logging.getLogger(__name__)

CSV_COLUMNS = [
    "issue_code",
    "title",
    "status",
    "priority",
    "assignee_email",
    "reporter_email",
    "labels",
    "cycle",
    "estimate",
    "due_date",
    "created_at",
    "updated_at",
]

EXPORT_MAX_ROWS = 10_000

_STATUS_VALUES = {s.value for s in IssueStatus}
_PRIORITY_VALUES = {p.value for p in IssuePriority}


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def _fmt_dt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    return str(value)


def _parse_due(raw: str) -> Optional[datetime]:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        cleaned = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except ValueError as exc:
        raise ValueError(f"due_date 无法解析: {text}") from exc


def _split_labels(raw: str) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    parts: list[str] = []
    for chunk in str(raw).replace(";", ",").split(","):
        name = chunk.strip()
        if name:
            parts.append(name)
    # preserve order, unique
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


class IssueCsvService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.issues = IssueService(db)

    # ------------------------------------------------------------------ export

    async def build_export_csv(
        self,
        *,
        workspace_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        type: Optional[str] = None,
        project_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        cycle_id: Optional[str] = None,
        search: Optional[str] = None,
        max_rows: int = EXPORT_MAX_ROWS,
    ) -> tuple[str, bool]:
        """Return (csv_text, truncated)."""
        query = (
            select(Issue)
            .options(
                joinedload(Issue.assignee),
                joinedload(Issue.reporter),
            )
            .where(
                Issue.is_deleted == False,  # noqa: E712
                Issue.workspace_id == workspace_id,
            )
        )
        if status:
            query = query.where(Issue.status == status)
        if priority:
            query = query.where(Issue.priority == priority)
        if type:
            query = query.where(Issue.type == type)
        if project_id:
            query = query.where(Issue.project_id == project_id)
        if assignee_id:
            query = query.where(Issue.assignee_id == assignee_id)
        if cycle_id:
            if cycle_id == "__none__":
                query = query.where(Issue.cycle_id.is_(None))
            else:
                query = query.where(Issue.cycle_id == cycle_id)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    Issue.title.ilike(pattern),
                    Issue.description.ilike(pattern),
                    Issue.issue_code.ilike(pattern),
                    Issue.legacy_issue_code.ilike(pattern),
                )
            )

        count_q = select(func.count()).select_from(query.order_by(None).subquery())
        total = int((await self.db.execute(count_q)).scalar() or 0)
        truncated = total > max_rows

        query = query.order_by(Issue.created_at.desc()).limit(max_rows)
        issues = list((await self.db.execute(query)).unique().scalars().all())
        tag_map = await load_tags_for_issues(self.db, issues)

        cycle_ids = {i.cycle_id for i in issues if i.cycle_id}
        cycle_names: dict[str, str] = {}
        if cycle_ids:
            rows = (
                await self.db.execute(
                    select(Cycle.id, Cycle.name).where(
                        Cycle.workspace_id == workspace_id,
                        Cycle.id.in_(list(cycle_ids)),
                    )
                )
            ).all()
            cycle_names = {r[0]: r[1] for r in rows}

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for issue in issues:
            labels = [t.name for t in tag_map.get(issue.id, []) if t.name]
            assignee = issue.assignee
            reporter = issue.reporter
            writer.writerow(
                {
                    "issue_code": issue.issue_code or "",
                    "title": issue.title or "",
                    "status": issue.status if isinstance(issue.status, str) else getattr(issue.status, "value", ""),
                    "priority": issue.priority if isinstance(issue.priority, str) else getattr(issue.priority, "value", ""),
                    "assignee_email": (assignee.username if assignee else "") or "",
                    "reporter_email": (reporter.username if reporter else "") or "",
                    "labels": ";".join(labels),
                    "cycle": cycle_names.get(issue.cycle_id or "", ""),
                    "estimate": "" if issue.estimate_points is None else str(issue.estimate_points),
                    "due_date": _fmt_dt(issue.due_date)[:10] if issue.due_date else "",
                    "created_at": _fmt_dt(issue.created_at),
                    "updated_at": _fmt_dt(issue.updated_at),
                }
            )
        return buf.getvalue(), truncated

    def template_csv(self) -> str:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "issue_code": "",
                "title": "Example issue",
                "status": "open",
                "priority": "medium",
                "assignee_email": "",
                "reporter_email": "",
                "labels": "bug;frontend",
                "cycle": "",
                "estimate": "1",
                "due_date": "2026-12-31",
                "created_at": "",
                "updated_at": "",
            }
        )
        return buf.getvalue()

    # ------------------------------------------------------------------ import

    async def import_csv(
        self,
        *,
        workspace_id: str,
        user_id: str,
        content: bytes | str,
    ) -> dict[str, Any]:
        if isinstance(content, bytes):
            try:
                text = content.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise HTTPException(status_code=400, detail="CSV 须为 UTF-8") from exc
        else:
            text = content

        text = text.strip("\ufeff")
        if not text.strip():
            raise HTTPException(status_code=400, detail="CSV 为空")

        try:
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames:
                raise HTTPException(status_code=400, detail="CSV 缺少表头")
            field_map = {((f or "").strip().lower()): f for f in reader.fieldnames}
            if "title" not in field_map:
                raise HTTPException(status_code=400, detail="CSV 缺少必填列 title")
            rows = list(reader)
        except HTTPException:
            raise
        except csv.Error as exc:
            raise HTTPException(status_code=400, detail=f"CSV 语法错误: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"CSV 解析失败: {exc}") from exc

        created = 0
        updated = 0
        errors: list[dict[str, Any]] = []

        # Preload WS members → username
        member_rows = (
            await self.db.execute(
                select(WorkspaceMember.user_id, UserModel.username).join(
                    UserModel, UserModel.id == WorkspaceMember.user_id
                ).where(WorkspaceMember.workspace_id == workspace_id)
            )
        ).all()
        username_to_id: dict[str, str] = {}
        for uid, uname in member_rows:
            if uname:
                username_to_id[uname.strip().lower()] = uid

        # Preload cycles by name
        cycle_rows = (
            await self.db.execute(
                select(Cycle.id, Cycle.name).where(Cycle.workspace_id == workspace_id)
            )
        ).all()
        cycle_by_name = {name.strip().lower(): cid for cid, name in cycle_rows if name}

        # Preload tags by name
        tag_rows = list(
            (
                await self.db.execute(select(Tag).where(Tag.workspace_id == workspace_id))
            ).scalars().all()
        )
        tag_by_name: dict[str, Tag] = {t.name.strip().lower(): t for t in tag_rows}

        for idx, raw in enumerate(rows, start=2):  # header = row 1
            try:
                def col(key: str) -> str:
                    src = field_map.get(key)
                    if src is None:
                        return ""
                    val = raw.get(src)
                    return "" if val is None else str(val).strip()

                title = col("title")
                if not title:
                    raise ValueError("title 必填")

                issue_code = col("issue_code")
                status = col("status") or "open"
                priority = col("priority") or "medium"
                if status not in _STATUS_VALUES:
                    raise ValueError(f"非法 status: {status}")
                if priority not in _PRIORITY_VALUES:
                    raise ValueError(f"非法 priority: {priority}")

                assignee_email = col("assignee_email")
                assignee_id = None
                if assignee_email:
                    assignee_id = username_to_id.get(assignee_email.lower())
                    if assignee_id is None:
                        raise ValueError(f"assignee 非本工作区成员: {assignee_email}")

                labels = _split_labels(col("labels"))
                cycle_name = col("cycle")
                cycle_id = None
                if cycle_name:
                    cycle_id = cycle_by_name.get(cycle_name.lower())
                    if cycle_id is None:
                        raise ValueError(f"cycle 不存在: {cycle_name}")

                estimate_raw = col("estimate")
                estimate_points = None
                if estimate_raw:
                    try:
                        estimate_points = float(estimate_raw)
                    except ValueError as exc:
                        raise ValueError(f"estimate 须为数字: {estimate_raw}") from exc

                due_raw = col("due_date")
                due_date = _parse_due(due_raw) if due_raw else None

                existing = None
                if issue_code:
                    existing = await self.issues.get_issue(
                        issue_code, by_code=True, workspace_id=workspace_id
                    )

                tag_ids = await self._ensure_tags(
                    workspace_id=workspace_id,
                    names=labels,
                    tag_by_name=tag_by_name,
                )

                if existing is not None:
                    patch_data: dict[str, Any] = {
                        "title": title,
                        "status": status,
                        "priority": priority,
                    }
                    if "assignee_email" in field_map:
                        patch_data["assignee_id"] = assignee_id
                    if "cycle" in field_map:
                        patch_data["cycle_id"] = cycle_id
                    if "estimate" in field_map:
                        patch_data["estimate_points"] = estimate_points
                    if "due_date" in field_map:
                        patch_data["due_date"] = due_date
                    upd = IssueUpdate(**patch_data)
                    await self.issues.update_issue(existing.id, upd, user_id)
                    if "labels" in field_map:
                        await self._set_issue_tags(
                            issue_id=existing.id,
                            workspace_id=workspace_id,
                            tag_ids=tag_ids,
                            user_id=user_id,
                        )
                    updated += 1
                else:
                    create = IssueCreate(
                        title=title,
                        type="feature",  # type: ignore[arg-type]
                        status=status,  # type: ignore[arg-type]
                        priority=priority,  # type: ignore[arg-type]
                        assignee_id=assignee_id,
                        reporter_id=user_id,
                        cycle_id=cycle_id,
                        estimate_points=estimate_points,
                        due_date=due_date,
                    )
                    issue = await self.issues.create_issue(
                        create, user_id=user_id, workspace_id=workspace_id
                    )
                    if labels:
                        await self._set_issue_tags(
                            issue_id=issue.id,
                            workspace_id=workspace_id,
                            tag_ids=tag_ids,
                            user_id=user_id,
                        )
                    created += 1
            except HTTPException as exc:
                await self.db.rollback()
                errors.append({"row": idx, "message": str(exc.detail)})
            except Exception as exc:  # noqa: BLE001
                await self.db.rollback()
                errors.append({"row": idx, "message": str(exc)})

        return {"created": created, "updated": updated, "errors": errors}

    async def _ensure_tags(
        self,
        *,
        workspace_id: str,
        names: Iterable[str],
        tag_by_name: dict[str, Tag],
    ) -> list[int]:
        ids: list[int] = []
        for name in names:
            key = name.strip().lower()
            tag = tag_by_name.get(key)
            if tag is None:
                tag = Tag(
                    name=name.strip()[:100],
                    workspace_id=workspace_id,
                    color="#3b82f6",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.db.add(tag)
                await self.db.flush()
                tag_by_name[key] = tag
            ids.append(int(tag.id))
        return ids

    async def _set_issue_tags(
        self,
        *,
        issue_id: str,
        workspace_id: str,
        tag_ids: list[int],
        user_id: str,
    ) -> None:
        """Replace tags without firing automations (import path); commit with issue write."""
        from sqlalchemy import delete

        desired = list(dict.fromkeys(tag_ids))
        current = list(
            (
                await self.db.execute(
                    select(IssueTag).where(IssueTag.issue_id == issue_id)
                )
            )
            .scalars()
            .all()
        )
        current_ids = {it.tag_id for it in current}
        desired_set = set(desired)
        to_remove = current_ids - desired_set
        to_add = [tid for tid in desired if tid not in current_ids]
        if to_remove:
            await self.db.execute(
                delete(IssueTag).where(
                    IssueTag.issue_id == issue_id,
                    IssueTag.tag_id.in_(list(to_remove)),
                )
            )
        for tid in to_add:
            self.db.add(IssueTag(issue_id=issue_id, tag_id=tid))
        await self.db.commit()
