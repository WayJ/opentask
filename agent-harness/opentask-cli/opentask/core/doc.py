"""Entity document commands (E14)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="doc")
def doc_cli():
    """实体文档 Entity Documents（Issue/Project/Initiative MD）。"""
    pass


@doc_cli.command(name="list")
@click.option("--parent-type", required=True, type=click.Choice(["issue", "project", "initiative"]))
@click.option("--parent-id", required=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def doc_list(obj, parent_type, parent_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_entity_docs(parent_type, parent_id))
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无文档")
            return
        obj.skin.table(
            ["ID", "Title"],
            [[(r.get("id") or "")[:8], r.get("title") or ""] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@doc_cli.command(name="show")
@click.argument("doc_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def doc_show(obj, doc_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_entity_doc(doc_id))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.section(data.get("title") or "Doc")
        click.echo(data.get("bodyMd") or data.get("body_md") or "")
    except APIError as e:
        handle_api_error(e, json_mode)


@doc_cli.command(name="create")
@click.option("--parent-type", required=True, type=click.Choice(["issue", "project", "initiative"]))
@click.option("--parent-id", required=True)
@click.option("--title", "-t", required=True)
@click.option("--body", "-b", default="")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def doc_create(obj, parent_type, parent_id, title, body, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.create_entity_doc(parent_type, parent_id, title, body))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"文档已创建: {data.get('id', '')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@doc_cli.command(name="update")
@click.argument("doc_id")
@click.option("--title", "-t", default=None)
@click.option("--body", "-b", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def doc_update(obj, doc_id, title, body, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if title is None and body is None:
        raise click.UsageError("需要 --title 或 --body")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_entity_doc(doc_id, title=title, body_md=body))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已更新")
    except APIError as e:
        handle_api_error(e, json_mode)


@doc_cli.command(name="delete")
@click.argument("doc_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def doc_delete(obj, doc_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_entity_doc(doc_id))
        if json_mode:
            echo_json(True, data=data or {"id": doc_id})
            return
        obj.skin.success("已删除")
    except APIError as e:
        handle_api_error(e, json_mode)
