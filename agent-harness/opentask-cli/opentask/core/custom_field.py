"""Custom field commands (E25 + E40 formula + E89 reorder)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config

_FIELD_TYPES = [
    "text",
    "number",
    "single_select",
    "multi_select",
    "date",
    "boolean",
    "formula",
]
_RESULT_TYPES = ["number", "boolean", "text", "date"]


@click.group(name="custom-field")
def custom_field_cli():
    """Workspace Issue 自定义字段。"""
    pass



def _parse_ordered_ids(ids_csv: str | None, positional: tuple[str, ...] | None) -> list[str]:
    ids: list[str] = []
    if ids_csv is not None and str(ids_csv).strip() != "":
        ids.extend([p.strip() for p in str(ids_csv).split(",") if p.strip()])
    for p in positional or ():
        s = str(p).strip()
        if s:
            ids.append(s)
    return ids


@custom_field_cli.command(name="list")
@click.option("--include-archived", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def custom_field_list(obj, include_archived, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_custom_fields(include_archived=include_archived))
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无自定义字段")
            return
        obj.skin.table(
            ["Key", "Name", "Type", "Pos", "Archived"],
            [
                [
                    r.get("key") or "",
                    r.get("name") or "",
                    r.get("type") or "",
                    str(r.get("position") if r.get("position") is not None else ""),
                    "yes" if r.get("archivedAt") else "",
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@custom_field_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option(
    "--type",
    "field_type",
    required=True,
    type=click.Choice(_FIELD_TYPES, case_sensitive=False),
)
@click.option("--key", "key", default=None, help="slug；默认从 name 生成")
@click.option(
    "--option",
    "-o",
    multiple=True,
    help="select 选项；可重复，或 value=label",
)
@click.option(
    "--expr",
    default=None,
    help=(
        "formula 表达式。示例："
        "'IF(issue.priority == \"urgent\", 10, COALESCE(cf.weight, 0) * COALESCE(cf.impact, 0))'"
    ),
)
@click.option(
    "--result-type",
    "result_type",
    default=None,
    type=click.Choice(_RESULT_TYPES, case_sensitive=False),
    help="formula 结果类型（默认 number）",
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def custom_field_create(obj, name, field_type, key, option, expr, result_type, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    kwargs = {}
    if key:
        kwargs["key"] = key
    if option:
        opts = []
        for raw in option:
            if "=" in raw:
                value, label = raw.split("=", 1)
                opts.append({"value": value.strip(), "label": label.strip() or value.strip()})
            else:
                opts.append(raw.strip())
        kwargs["options"] = opts
    if field_type.lower() == "formula":
        if not expr:
            raise click.ClickException("formula 类型需要 --expr")
        kwargs["formulaExpr"] = expr
        kwargs["formulaResultType"] = (result_type or "number").lower()
    try:
        data = asyncio.run(client.create_custom_field(name, field_type, **kwargs))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建字段: {data.get('key')} ({data.get('id', '')[:8]})")
    except APIError as e:
        handle_api_error(e, json_mode)


@custom_field_cli.command(name="update")
@click.argument("field_ref")
@click.option("--name", "-n", default=None)
@click.option("--expr", default=None, help="更新 formula 表达式")
@click.option(
    "--result-type",
    "result_type",
    default=None,
    type=click.Choice(_RESULT_TYPES, case_sensitive=False),
)
@click.option("--archive/--unarchive", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def custom_field_update(obj, field_ref, name, expr, result_type, archive, as_json):
    """更新字段；FIELD_REF 为 id 或 key。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    body = {}
    if name:
        body["name"] = name
    if expr is not None:
        body["formulaExpr"] = expr
    if result_type is not None:
        body["formulaResultType"] = result_type.lower()
    if archive is not None:
        body["archive"] = archive
    if not body:
        raise click.ClickException("请提供 --name / --expr / --result-type / --archive")

    async def _resolve_and_update():
        fid = field_ref
        listed = await client.list_custom_fields(include_archived=True)
        rows = (listed or {}).get("rows", []) if isinstance(listed, dict) else []
        match = next((r for r in rows if r.get("id") == field_ref or r.get("key") == field_ref), None)
        if match:
            fid = match["id"]
        return await client.update_custom_field(fid, **body)

    try:
        data = asyncio.run(_resolve_and_update())
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success(f"已更新: {data.get('key') or field_ref}")
    except APIError as e:
        handle_api_error(e, json_mode)


@custom_field_cli.command(name="validate-formula")
@click.option("--expr", required=True, help="待校验表达式")
@click.option(
    "--result-type",
    "result_type",
    default=None,
    type=click.Choice(_RESULT_TYPES, case_sensitive=False),
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def custom_field_validate_formula(obj, expr, result_type, as_json):
    """调用 POST /api/custom-fields/validate-formula。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(
            client.validate_formula(
                expr, result_type=result_type.lower() if result_type else None
            )
        )
        if json_mode:
            echo_json(True, data=data)
            return
        if (data or {}).get("ok"):
            deps = ", ".join((data or {}).get("dependencies") or []) or "—"
            obj.skin.success(f"ok · deps: {deps}")
        else:
            obj.skin.error((data or {}).get("error") or "invalid")
            raise SystemExit(1)
    except APIError as e:
        handle_api_error(e, json_mode)


@custom_field_cli.command(name="reorder")
@click.option("--ids", "ids_csv", default=None, help="Comma-separated custom-field ids in new order")
@click.argument("positional_ids", nargs=-1)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def custom_field_reorder(obj, ids_csv, positional_ids, as_json):
    """E89: 按 orderedIds 重排工作区自定义字段（软更新；未知 id 忽略）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    ordered_ids = _parse_ordered_ids(ids_csv, positional_ids)
    if not ordered_ids:
        raise click.ClickException("Specify --ids ID1,ID2,... or positional custom-field ids")
    client = make_client(config)
    try:
        data = asyncio.run(client.reorder_custom_fields(ordered_ids))
        if json_mode:
            echo_json(True, data=data, message="reordered")
            return
        obj.skin.success("顺序已更新")
    except APIError as e:
        handle_api_error(e, json_mode)
