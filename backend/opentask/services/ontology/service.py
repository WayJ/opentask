"""Member-scoped object and relationship queries over existing OpenTask tables."""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, or_, select

from opentask.models.issue.enums import IssuePriority, IssueStatus, IssueType
from opentask.models.issue.model import Issue, IssueRelation
from opentask.models.issue.schema import IssueUpdate
from opentask.services.issue_service import IssueService
from opentask.models.requirement.model import Project
from opentask.models.user.model import UserModel
from opentask.models.user_center.model import UserDept
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.user_center.rbac_service import RbacService
from opentask.services.workspace.service import WorkspaceService
from .catalog import FILTERS, INVERSES, PROPERTIES, RELATIONS, TYPE_SCOPES, OBJECT_SET_FIELDS, UpdateIssueStatus, describe_type, discover

MODELS = {"Issue": Issue, "Project": Project, "Member": UserModel}


class OntologyService:
    def __init__(self, session: AsyncSession, identity: tuple[dict, UserModel]):
        self.session = session
        self.payload, self.user = identity
        self.scopes = set((self.payload.get("scope") or "").split())
        self.depts: set[str] | None = None
        self.workspaces: list[str] = []

    def require_type(self, object_type):
        if not self.scopes.intersection(TYPE_SCOPES[object_type]):
            raise HTTPException(
                403,
                detail={"error": "insufficient_scope", "required_any": TYPE_SCOPES[object_type]},
                headers={"WWW-Authenticate": 'Bearer error="insufficient_scope"'},
            )

    async def prepare(self):
        self.depts = await RbacService(self.session).get_visible_dept_ids(self.user)
        self.workspaces = await WorkspaceService(self.session).member_workspace_ids(str(self.user.id))

    def visible(self, object_type):
        self.require_type(object_type)
        model = MODELS[object_type]
        stmt = select(model)
        if object_type in ("Issue", "Project"):
            stmt = stmt.where(or_(model.workspace_id.is_(None), model.workspace_id.in_(self.workspaces)))
            stmt = RbacService(session=None).apply_data_scope(
                stmt,
                self.depts,
                dept_col=model.dept_id,
                creator_col=Issue.created_by if object_type == "Issue" else None,
                user_id=str(self.user.id),
            )
            if object_type == "Issue":
                stmt = stmt.where(Issue.is_deleted.is_(False))
        else:
            stmt = stmt.where(UserModel.status == 1)
            if "read:members" not in self.scopes:
                return stmt.where(UserModel.id == str(self.user.id))
            shared = UserModel.id.in_(
                select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id.in_(self.workspaces))
            )
            if self.depts is not None:
                shared = and_(
                    shared, UserModel.id.in_(select(UserDept.user_id).where(UserDept.dept_id.in_(self.depts)))
                )
            stmt = stmt.where(or_(UserModel.id == str(self.user.id), shared))
        return stmt

    @staticmethod
    def serialize(object_type, row, description_limit=8000):
        props = {key: getattr(row, key) for key in PROPERTIES[object_type]}
        truncated = []
        if isinstance(props.get("description"), str) and len(props["description"]) > description_limit:
            props["description"] = props["description"][:description_limit]
            truncated.append("description")
        return {"object_type": object_type, "id": str(row.id), "properties": props, "truncated_properties": truncated}

    async def page(self, object_type, stmt, limit, offset):
        model = MODELS[object_type]
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        order = [model.id] if object_type == "Member" else [model.created_at, model.id]
        rows = (await self.session.execute(stmt.order_by(*order).limit(limit).offset(offset))).scalars().all()
        more = offset + len(rows) < total
        return {
            "object_type": object_type,
            "items": [self.serialize(object_type, row, description_limit=1000) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": more,
            "next_offset": offset + limit if more else None,
        }

    async def row(self, object_type, object_id):
        row = (
            await self.session.execute(self.visible(object_type).where(MODELS[object_type].id == object_id))
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, detail="Object not found")
        return row

    async def search(self, args):
        kind = args.object_type
        model = MODELS[kind]
        stmt = self.visible(kind)
        filters = args.filters.model_dump(exclude_none=True)
        if set(filters) - set(FILTERS[kind]):
            raise HTTPException(400, detail="Filter is not supported for this object type")
        enums = {"status": IssueStatus, "priority": IssuePriority, "type": IssueType}
        for key, value in filters.items():
            if key in enums and value not in {x.value for x in enums[key]}:
                raise HTTPException(400, detail="Invalid filter enum")
            stmt = stmt.where(getattr(model, key) == value)
        if args.query:
            # Escape LIKE metacharacters so user text is a literal substring.
            term = "%" + args.query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            cols = {
                "Issue": ["title", "description", "issue_code"],
                "Project": ["name", "description"],
                "Member": ["username", "name"],
            }[kind]
            stmt = stmt.where(or_(*[getattr(model, col).ilike(term, escape="\\") for col in cols]))
        return await self.page(kind, stmt, args.limit, args.offset)

    async def related(self, args):
        source = await self.row(args.object_type, args.object_id)
        definition = RELATIONS[args.object_type].get(args.relation)
        if definition is None:
            raise HTTPException(400, detail="Unknown relation for this object type")
        target_type = definition[0]
        stmt = self.visible(target_type)
        target_model = MODELS[target_type]
        relation = args.relation
        if args.object_type == "Issue":
            fields = {
                "project": "project_id",
                "assignee": "assignee_id",
                "reporter": "reporter_id",
                "parent": "parent_issue_id",
            }
            if relation in fields:
                stmt = stmt.where(target_model.id == getattr(source, fields[relation]))
            elif relation == "children":
                stmt = stmt.where(Issue.parent_issue_id == source.id)
            else:
                outgoing = select(IssueRelation.target_id).where(
                    IssueRelation.source_id == source.id, IssueRelation.relation_type == relation
                )
                incoming = select(IssueRelation.source_id).where(
                    IssueRelation.target_id == source.id, IssueRelation.relation_type == INVERSES[relation]
                )
                stmt = stmt.where(or_(Issue.id.in_(outgoing), Issue.id.in_(incoming)))
        elif args.object_type == "Project":
            stmt = stmt.where(Issue.project_id == source.id)
        else:
            col = Issue.assignee_id if relation == "assigned_issues" else Issue.reporter_id
            stmt = stmt.where(col == str(source.id))
        result = await self.page(target_type, stmt, args.limit, args.offset)
        return {**result, "source": {"object_type": args.object_type, "id": args.object_id}, "relation": relation}

    # Restrict filtering/sorting to predictable scalar columns; no arbitrary SQL or private fields.
    QUERY_FIELDS = OBJECT_SET_FIELDS

    def conditions(self, kind, conditions):
        expressions = []
        for condition in conditions:
            if condition.field not in self.QUERY_FIELDS[kind] or (condition.op == "eq" and len(condition.values) != 1):
                raise HTTPException(400, detail="Unsupported field or condition")
            values = condition.values
            if condition.field == "is_active":
                if any(type(v) is not bool for v in values):
                    raise HTTPException(400, detail="Expected boolean")
            elif any(type(v) is not str for v in values):
                raise HTTPException(400, detail="Expected string")
            enums = {"status": IssueStatus, "priority": IssuePriority, "type": IssueType}
            if condition.field in enums and any(v not in {e.value for e in enums[condition.field]} for v in values):
                raise HTTPException(400, detail="Invalid enum")
            column = getattr(MODELS[kind], condition.field)
            expressions.append(column == values[0] if condition.op == "eq" else column.in_(values))
        return expressions

    def relation_filter(self, related):
        relation = related.relation
        definition = RELATIONS["Issue"].get(relation)
        if not definition:
            raise HTTPException(400, detail="Unknown Issue relation")
        target = definition[0]
        target_ids = self.visible(target).where(*self.conditions(target, related.where)).with_only_columns(MODELS[target].id)
        columns = {"project": Issue.project_id, "assignee": Issue.assignee_id, "reporter": Issue.reporter_id, "parent": Issue.parent_issue_id}
        if relation in columns:
            return columns[relation].in_(target_ids)
        if relation == "children":
            return Issue.id.in_(select(Issue.parent_issue_id).where(Issue.id.in_(target_ids)))
        outgoing = select(IssueRelation.source_id).where(IssueRelation.relation_type == relation, IssueRelation.target_id.in_(target_ids))
        incoming = select(IssueRelation.target_id).where(IssueRelation.relation_type == INVERSES[relation], IssueRelation.source_id.in_(target_ids))
        return or_(Issue.id.in_(outgoing), Issue.id.in_(incoming))

    async def object_set(self, args):
        kind = args.object_type
        model = MODELS[kind]
        fields = args.select or list(PROPERTIES[kind])
        if len(set(fields)) != len(fields) or set(fields) - set(PROPERTIES[kind]):
            raise HTTPException(400, detail="Unsupported or duplicate selected property")
        stmt = self.visible(kind).where(*self.conditions(kind, args.where))
        if args.related:
            if kind != "Issue":
                raise HTTPException(400, detail="Relation filter supports Issue only")
            stmt = stmt.where(self.relation_filter(args.related))
        if args.aggregate:
            field = args.aggregate.group_by
            if field not in self.QUERY_FIELDS[kind]:
                raise HTTPException(400, detail="Unsupported grouping field")
            col = getattr(model, field)
            # Count visible IDs first to avoid counting hidden targets or duplicate joins.
            ids = stmt.with_only_columns(model.id).subquery()
            groups = (await self.session.execute(select(col, func.count()).where(model.id.in_(select(ids.c.id))).group_by(col).order_by(col).limit(51))).all()
            return {"object_type": kind, "group_by": field, "groups": [{"value": value, "count": count} for value, count in groups[:50]], "truncated": len(groups) > 50}
        total = (await self.session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        if args.order_by:
            if args.order_by.field not in self.QUERY_FIELDS[kind]:
                raise HTTPException(400, detail="Unsupported sort field")
            col = getattr(model, args.order_by.field)
            order = col.asc() if args.order_by.direction == "asc" else col.desc()
            stmt = stmt.order_by(order.nulls_last(), model.id.asc())
        else:
            stmt = stmt.order_by(model.id.asc())
        rows = (await self.session.execute(stmt.limit(args.limit).offset(args.offset))).scalars().all()
        items = []
        for row in rows:
            item = self.serialize(kind, row, description_limit=1000)
            item["properties"] = {field: item["properties"][field] for field in fields}
            item["truncated_properties"] = [field for field in item["truncated_properties"] if field in fields]
            items.append(item)
        more = args.offset + len(items) < total
        return {"object_type": kind, "items": items, "total": total, "limit": args.limit, "offset": args.offset, "has_more": more, "next_offset": args.offset + args.limit if more else None}

    async def update_status(self, args):
        if "write:tasks" not in self.scopes:
            raise HTTPException(403, detail={"error": "insufficient_scope", "required": "write:tasks"})
        issue = await self.row("Issue", args.object_id)
        if "issue:update" not in await RbacService(self.session).get_user_permissions(self.user):
            raise HTTPException(403, detail="Missing issue:update permission")
        if issue.workspace_id:
            member = await WorkspaceService(self.session).require_member(issue.workspace_id, str(self.user.id))
            if member.role not in ("member", "owner"):
                raise HTTPException(403, detail="Only workspace members and owners can update issues")
        previous = issue.status.value if hasattr(issue.status, "value") else issue.status
        target = args.status
        if previous != target:
            try:
                issue = await IssueService(self.session).update_issue(issue.id, IssueUpdate(status=args.status), str(self.user.id))
            except ValueError as error:
                raise HTTPException(400, detail=str(error)) from error
            if not issue:
                raise HTTPException(404, detail="Object not found")
        return {"object_type": "Issue", "id": str(issue.id), "issue_code": issue.issue_code, "previous_status": previous, "status": target, "changed": previous != target}

    async def execute(self, name, args):
        if name == "discover_ontology":
            return discover()
        if name == "describe_object_type":
            return describe_type(args.object_type)
        if name == "describe_action":
            return {"name": args.action, "object_type": "Issue", "input_schema": UpdateIssueStatus.model_json_schema(), "required_scopes": ["read:tasks", "write:tasks"], "permission": "issue:update", "workspace_roles": ["member", "owner"], "idempotent": True, "effects": ["更新状态", "记录时间线", "执行既有业务逻辑"]}
        await self.prepare()
        if name == "update_issue_status":
            return await self.update_status(args)
        if name == "query_object_set":
            return await self.object_set(args)
        if name == "search_objects":
            return await self.search(args)
        if name == "get_object":
            return self.serialize(args.object_type, await self.row(args.object_type, args.object_id))
        if name == "get_related_objects":
            return await self.related(args)
        raise ValueError("Unknown ontology operation")
