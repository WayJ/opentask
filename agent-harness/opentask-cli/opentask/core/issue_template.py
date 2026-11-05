"""Issue template commands (E82) — CLI 1.66.0."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError, OpenTaskClient
from ..utils.cli_output import echo_json, handle_api_error
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


@click.group(name="issue-template")
def issue_template_cli():
    """Issue template management (workspace-level create templates)."""
    pass


@issue_template_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def list_templates(obj, as_json: bool):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    try:
        data = asyncio.run(client.list_issue_templates())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("No issue templates")
            return
        obj.skin.table(
            ["Id", "Name", "Type", "Source"],
            [
                [
                    (r.get("id") or "")[:8],
                    r.get("name") or "",
                    (r.get("payload") or {}).get("type") or "",
                    r.get("source") or "",
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@issue_template_cli.command(name="show")
@click.argument("template_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def show_template(obj, template_id: str, as_json: bool):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    try:
        data = asyncio.run(client.get_issue_template(template_id))
        if json_mode:
            echo_json(True, data=data)
            return
        skin: ReplSkin = obj.skin
        skin.section("Issue Template")
        payload = data.get("payload") or {}
        skin.status_block(
            {
                "ID": data.get("id", ""),
                "Name": data.get("name", ""),
                "Description": data.get("description") or "N/A",
                "Source": data.get("source") or "",
                "Type": payload.get("type") or "",
                "Priority": payload.get("priority") or "",
            }
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@issue_template_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--description", "-d", default=None)
@click.option("--icon", default=None)
@click.option(
    "--payload-json",
    default=None,
    help='Payload JSON e.g. {"type":"bug","priority":"high","title":"Bug: "}',
)
@click.option("--sort-order", default=0, type=int)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def create_template(obj, name, description, icon, payload_json, sort_order, as_json):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    payload = json.loads(payload_json) if payload_json else {}
    try:
        data = asyncio.run(
            client.create_issue_template(
                name=name,
                description=description,
                icon=icon,
                payload=payload,
                sort_order=sort_order,
            )
        )
        if json_mode:
            echo_json(True, data=data, message="issue template created")
            return
        obj.skin.success(f"Created template: {data.get('name')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@issue_template_cli.command(name="update")
@click.argument("template_id")
@click.option("--name", "-n", default=None)
@click.option("--description", "-d", default=None)
@click.option("--icon", default=None)
@click.option("--payload-json", default=None)
@click.option("--sort-order", default=None, type=int)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def update_template(obj, template_id, name, description, icon, payload_json, sort_order, as_json):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    payload = json.loads(payload_json) if payload_json else None
    try:
        data = asyncio.run(
            client.update_issue_template(
                template_id,
                name=name,
                description=description,
                icon=icon,
                payload=payload,
                sort_order=sort_order,
            )
        )
        if json_mode:
            echo_json(True, data=data, message="issue template updated")
            return
        obj.skin.success(f"Updated template: {data.get('name')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@issue_template_cli.command(name="delete")
@click.argument("template_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def delete_template(obj, template_id, as_json):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    try:
        data = asyncio.run(client.delete_issue_template(template_id))
        if json_mode:
            echo_json(True, data=data, message="issue template deleted")
            return
        obj.skin.success(f"Deleted template: {template_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@issue_template_cli.command(name="seed")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def seed_templates(obj, as_json):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    try:
        data = asyncio.run(client.seed_issue_templates())
        if json_mode:
            echo_json(True, data=data, message="issue templates seeded")
            return
        total = (data or {}).get("total") if isinstance(data, dict) else None
        obj.skin.success(f"Seeded issue templates (total={total})")
    except APIError as e:
        handle_api_error(e, json_mode)
