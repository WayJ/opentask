"""Public Issue Form commands (E31)."""
from __future__ import annotations

import asyncio
import json
import os

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="form")
def form_cli():
    """公开 Issue 表单。"""
    pass


@form_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def form_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_forms())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无表单")
            return
        obj.skin.table(
            ["Name", "Slug", "Enabled", "Token", "Id"],
            [
                [
                    r.get("name") or "",
                    r.get("slug") or "",
                    "yes" if r.get("enabled") else "no",
                    (r.get("token") or "")[:10] + "…",
                    (r.get("id") or "")[:8],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@form_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--slug", default=None)
@click.option("--description", "-d", default=None)
@click.option(
    "--fields-json",
    default=None,
    help='字段 JSON 数组；默认仅 title+description',
)
@click.option("--create-request", is_flag=True, help="提交时尝试创建 Customer Request")
@click.option("--disabled", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def form_create(obj, name, slug, description, fields_json, create_request, disabled, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if fields_json:
        fields = json.loads(fields_json)
    else:
        fields = [
            {"key": "title", "type": "title", "label": "Title", "required": True},
            {"key": "description", "type": "description", "label": "Description"},
        ]
    client = make_client(config)
    try:
        data = asyncio.run(
            client.create_form(
                name,
                fields,
                description=description,
                slug=slug,
                enabled=not disabled,
                create_customer_request=create_request,
            )
        )
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(
            f"已创建: {(data.get('id') or '')[:8]} path={data.get('publicPath')}"
        )
        if data.get("token"):
            obj.skin.info(f"token: {data['token']}")
    except APIError as e:
        handle_api_error(e, json_mode)


@form_cli.command(name="update")
@click.argument("form_id")
@click.option("--name", default=None)
@click.option("--slug", default=None)
@click.option("--description", default=None)
@click.option("--fields-json", default=None)
@click.option("--enabled", type=click.BOOL, default=None)
@click.option("--create-request", type=click.BOOL, default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def form_update(
    obj, form_id, name, slug, description, fields_json, enabled, create_request, as_json
):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {}
    if name is not None:
        body["name"] = name
    if slug is not None:
        body["slug"] = slug
        body["setSlug"] = True
    if description is not None:
        body["description"] = description
    if fields_json is not None:
        body["fields"] = json.loads(fields_json)
    if enabled is not None:
        body["enabled"] = enabled
    if create_request is not None:
        body["createCustomerRequest"] = create_request
    if not body:
        raise click.ClickException("无更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_form(form_id, body))
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success(f"已更新: {(data.get('id') or form_id)[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@form_cli.command(name="delete")
@click.argument("form_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def form_delete(obj, form_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_form(form_id))
        if json_mode:
            echo_json(True, data=data, message="deleted")
            return
        obj.skin.success(f"已删除: {form_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@form_cli.command(name="url")
@click.argument("form_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def form_url(obj, form_id, as_json):
    """打印公开表单 URL（FRONTEND_BASE_URL + /f/{token}）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_form(form_id))
        token = (data or {}).get("token")
        path = (data or {}).get("publicPath") or (f"/f/{token}" if token else None)
        base = (
            os.getenv("FRONTEND_BASE_URL")
            or os.getenv("OPENTASK_FRONTEND_URL")
            or getattr(config, "frontend_base_url", None)
            or "http://localhost:5173"
        ).rstrip("/")
        url = f"{base}{path}" if path else None
        payload = {"id": form_id, "token": token, "path": path, "url": url}
        if json_mode:
            echo_json(True, data=payload)
            return
        if not url:
            obj.skin.error("无法解析公开 URL")
            raise SystemExit(1)
        click.echo(url)
    except APIError as e:
        handle_api_error(e, json_mode)
