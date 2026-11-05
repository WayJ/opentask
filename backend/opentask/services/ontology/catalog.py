"""Versioned business vocabulary exposed by OpenTask MCP."""

from copy import deepcopy
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from opentask.models.issue.enums import IssuePriority, IssueStatus, IssueType, RelationType

VERSION = "1.0.0"
ObjectType = Literal["Issue", "Project", "Member"]
INVERSES = {
    "blocks": "is_blocked_by",
    "is_blocked_by": "blocks",
    "depends_on": "is_depended_by",
    "is_depended_by": "depends_on",
    "duplicates": "is_duplicated_by",
    "is_duplicated_by": "duplicates",
    "relates_to": "relates_to",
}
RELATIONS = {
    "Issue": {
        "project": ("Project", "issues", "zero_or_one"),
        "assignee": ("Member", "assigned_issues", "zero_or_one"),
        "reporter": ("Member", "reported_issues", "zero_or_one"),
        "parent": ("Issue", "children", "zero_or_one"),
        "children": ("Issue", "parent", "many"),
        **{r.value: ("Issue", INVERSES[r.value], "many") for r in RelationType},
    },
    "Project": {"issues": ("Issue", "project", "many")},
    "Member": {"assigned_issues": ("Issue", "assignee", "many"), "reported_issues": ("Issue", "reporter", "many")},
}
TYPE_SCOPES = {"Issue": ["read:tasks"], "Project": ["read:projects"], "Member": ["profile", "read:members"]}
PROPERTIES = {
    "Issue": {
        "issue_code": {"type": "string", "description": "OpenTask 业务单号；对象主键仍为 id。"},
        "title": {"type": "string"},
        "description": {"type": ["string", "null"], "maxLength": 8000},
        "status": {
            "type": "string",
            "enum": [x.value for x in IssueStatus],
            "description": "OpenTask 原生状态；与旧 list_issues 的契约状态不同。",
        },
        "type": {"type": "string", "enum": [x.value for x in IssueType]},
        "priority": {"type": "string", "enum": [x.value for x in IssuePriority]},
        **{
            name: {"type": ["string", "null"], "format": "date-time"}
            for name in ["due_date", "start_date", "created_at", "updated_at"]
        },
    },
    "Project": {
        "name": {"type": "string"},
        "description": {"type": ["string", "null"], "maxLength": 8000},
        "is_active": {"type": "boolean"},
        **{
            name: {"type": ["string", "null"], "format": "date-time"}
            for name in ["starts_at", "target_date", "created_at", "updated_at"]
        },
    },
    "Member": {"username": {"type": ["string", "null"]}, "name": {"type": ["string", "null"]}},
}
FILTERS = {"Issue": ["status", "priority", "type", "project_id", "assignee_id"], "Project": ["is_active"], "Member": []}
OBJECT_SET_FIELDS = {
    "Issue": ["issue_code", "title", "status", "type", "priority", "project_id", "assignee_id"],
    "Project": ["name", "is_active"],
    "Member": ["username", "name"],
}
DESCRIPTIONS = {
    "Issue": "需要跟踪、分配和解决的业务问题。查询返回未删除且当前成员可见的对象。",
    "Project": "组织一组问题的项目。按成员工作区和部门范围读取，含停用项目。",
    "Member": "OpenTask 启用用户的最小身份。profile 仅可见本人；read:members 可读共享工作区且符合部门范围的成员。",
}


def describe_type(name):
    return deepcopy(
        {
            "version": VERSION,
            "name": name,
            "description": DESCRIPTIONS[name],
            "primary_key": "id",
            "properties": PROPERTIES[name],
            "filterable_properties": FILTERS[name],
            "object_set_filter_sort_group_fields": OBJECT_SET_FIELDS[name],
            "object_set_relation_filter": name == "Issue",
            "scope_options": TYPE_SCOPES[name],
            "relations": [
                {
                    "name": k,
                    "target_type": v[0],
                    "inverse": v[1],
                    "cardinality": v[2],
                    **(
                        {"description": "主负责人关系，不含额外协作者。"}
                        if k in ("assignee", "assigned_issues")
                        else {}
                    ),
                }
                for k, v in RELATIONS[name].items()
            ],
            "actions": ([{"name": "update_issue_status", "description": "修改 Issue 状态，产生时间线记录。", "required_scopes": ["read:tasks", "write:tasks"], "permission": "issue:update"}] if name == "Issue" else []),
        }
    )


def discover():
    return {
        "name": "OpenTask",
        "version": VERSION,
        "read_only": False,
        "object_types": [
            {"name": name, "description": DESCRIPTIONS[name], "scope_options": TYPE_SCOPES[name]} for name in PROPERTIES
        ],
        "next_step": "使用 describe_object_type 读取字段、关系和动作；query_object_set 查询，describe_action 了解动作参数。",
        "pagination": {
            "max_limit": 50,
            "max_offset": 100000,
            "order": "created_at ASC, id ASC（Member 按 id）",
            "list_description_max_length": 1000,
        },
        "visibility": "对象与关系目标均按当前 OAuth 成员权限过滤；total 不包含不可见对象。",
    }


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Discover(Arguments):
    pass


class Describe(Arguments):
    object_type: ObjectType = Field(description="业务对象类型；可先调用 discover_ontology。")


class Filters(Arguments):
    status: str | None = None
    priority: str | None = None
    type: str | None = None
    project_id: str | None = Field(None, max_length=128)
    assignee_id: str | None = Field(None, max_length=128)
    is_active: bool | None = None


class Page(Arguments):
    limit: int = Field(20, ge=1, le=50, description="每页最多 50 个可见对象。")
    offset: int = Field(0, ge=0, le=100000)


class Search(Page, Describe):
    query: str | None = Field(
        None, max_length=200, description="Issue 搜标题、描述或单号；Project 搜名称、描述；Member 搜用户名、姓名。"
    )
    filters: Filters = Field(
        default_factory=Filters, description="各类型允许的筛选字段由 describe_object_type 返回；不适用字段会被拒绝。"
    )


class Get(Describe):
    object_id: str = Field(min_length=1, max_length=128, description="search_objects 返回的 id，不是业务单号。")


class Condition(Arguments):
    field: str = Field(min_length=1, max_length=64, description="对象类型中允许筛选的字段。")
    op: Literal["eq", "in"] = Field(description="eq 仅接受一个值；in 接受 1 至 20 个值。")
    values: list[str | bool] = Field(min_length=1, max_length=20)


class RelatedCondition(Arguments):
    relation: str = Field(min_length=1, max_length=64, description="Issue 的关系名，目标必须对当前成员可见。")
    where: list[Condition] = Field(default_factory=list, max_length=8, description="目标对象的 AND 条件。")


class Sort(Arguments):
    field: str = Field(min_length=1, max_length=64)
    direction: Literal["asc", "desc"] = "asc"


class Aggregate(Arguments):
    group_by: str = Field(min_length=1, max_length=64, description="按此字段分组计数，最多返回 50 组。")


class ObjectSet(Page, Describe):
    select: list[str] | None = Field(None, min_length=1, max_length=20, description="返回的属性白名单；id 和 object_type 总会返回。")
    where: list[Condition] = Field(default_factory=list, max_length=8, description="AND 条件，可按 eq 或 in 筛选。")
    related: RelatedCondition | None = Field(None, description="Issue 沿一条关系筛选存在的可见目标；需两端 scope。")
    order_by: Sort | None = None
    aggregate: Aggregate | None = Field(None, description="指定后按字段分组计数，不返回对象明细。")


class DescribeAction(Arguments):
    action: Literal["update_issue_status"] = Field(description="从 Issue 类型的 actions 获取动作名称。")


class UpdateIssueStatus(Arguments):
    object_id: str = Field(min_length=1, max_length=128, description="目标 Issue 的对象 id，先通过 search_objects 按单号查找。")
    status: Literal["open", "in_progress", "feedback", "resolved", "closed", "rejected"] = Field(description="OpenTask 原生目标状态：resolved 为已解决，closed 为已关闭；两者均视作完成。")


class Related(Get, Page):
    relation: str = Field(min_length=1, max_length=64, description="describe_object_type 返回的关系名；逐次遍历一跳。")


TOOLS = {
    "query_object_set": (ObjectSet, "查询可见对象集：组合字段条件、选择字段、排序分页、关联筛选或分组计数；关联查询检查两端权限。"),
    "describe_action": (DescribeAction, "读取类型化业务动作的参数 schema、权限及副作用；执行前可调用。"),
    "update_issue_status": (UpdateIssueStatus, "修改可见 Issue 的状态，写入时间线并触发既有业务逻辑；需要 read:tasks、write:tasks 和 issue:update 权限。"),
    "discover_ontology": (Discover, "发现 OpenTask 业务本体：返回版本、对象类型、权限范围及后续查询入口。"),
    "describe_object_type": (Describe, "读取一个业务类型的字段、原生枚举、筛选字段和有方向的关系定义。"),
    "search_objects": (Search, "按类型搜索当前成员可见对象，返回稳定 id 和有界分页；需对应类型 scope。"),
    "get_object": (Get, "按类型和 id 获取可见业务对象；不可见与不存在均返回 404。"),
    "get_related_objects": (
        Related,
        "从可见对象沿指定关系读取一跳目标；同时检查两端 scope 与数据范围，返回可见目标分页。",
    ),
}


def tool_definitions():
    return [
        {
            "name": name,
            "description": description,
            "inputSchema": model.model_json_schema(),
            "annotations": {"readOnlyHint": name != "update_issue_status", "destructiveHint": name == "update_issue_status", "idempotentHint": True},
        }
        for name, (model, description) in TOOLS.items()
    ]
