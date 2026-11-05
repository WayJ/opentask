"""Project template commands (E72) — CLI 1.56.0."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError, OpenTaskClient
from ..utils.cli_output import echo_json, handle_api_error
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


@click.group(name="project-template")
def project_template_cli():
    """Project template management (milestones skeleton)."""
    pass


@project_template_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def list_templates(obj, as_json: bool):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    try:
        data = asyncio.run(client.list_project_templates())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("No project templates")
            return
        obj.skin.table(
            ["Id", "Name", "Milestones", "Source"],
            [
                [
                    (r.get("id") or "")[:8],
                    r.get("name") or "",
                    str(len((r.get("payload") or {}).get("milestones") or [])),
                    r.get("source") or "",
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@project_template_cli.command(name="show")
@click.argument("template_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def show_template(obj, template_id: str, as_json: bool):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    try:
        data = asyncio.run(client.get_project_template(template_id))
        if json_mode:
            echo_json(True, data=data)
            return
        skin: ReplSkin = obj.skin
        skin.section("Project Template")
        skin.status_block(
            {
                "ID": data.get("id", ""),
                "Name": data.get("name", ""),
                "Description": data.get("description") or "N/A",
                "Source": data.get("source") or "",
                "Milestones": str(len((data.get("payload") or {}).get("milestones") or [])),
            }
        )
        miles = (data.get("payload") or {}).get("milestones") or []
        if miles:
            skin.table(
                ["Pos", "Name", "OffsetDays"],
                [
                    [
                        str(m.get("position", i)),
                        m.get("name") or "",
                        "" if m.get("targetOffsetDays") is None else str(m.get("targetOffsetDays")),
                    ]
                    for i, m in enumerate(miles)
                ],
            )
    except APIError as e:
        handle_api_error(e, json_mode)


@project_template_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--description", "-d", default=None)
@click.option("--icon", default=None)
@click.option(
    "--payload-json",
    default=None,
    help='Payload JSON e.g. {"milestones":[{"name":"Kickoff","targetOffsetDays":0}]}',
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def create_template(obj, name, description, icon, payload_json, as_json):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    payload = json.loads(payload_json) if payload_json else {"milestones": []}
    try:
        data = asyncio.run(
            client.create_project_template(
                name=name, description=description, icon=icon, payload=payload
            )
        )
        if json_mode:
            echo_json(True, data=data, message="project template created")
            return
        obj.skin.success(f"Created template: {data.get('name')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@project_template_cli.command(name="update")
@click.argument("template_id")
@click.option("--name", "-n", default=None)
@click.option("--description", "-d", default=None)
@click.option("--icon", default=None)
@click.option("--payload-json", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def update_template(obj, template_id, name, description, icon, payload_json, as_json):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    payload = json.loads(payload_json) if payload_json else None
    try:
        data = asyncio.run(
            client.update_project_template(
                template_id,
                name=name,
                description=description,
                icon=icon,
                payload=payload,
            )
        )
        if json_mode:
            echo_json(True, data=data, message="project template updated")
            return
        obj.skin.success(f"Updated template: {data.get('name')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@project_template_cli.command(name="delete")
@click.argument("template_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def delete_template(obj, template_id, as_json):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    try:
        data = asyncio.run(client.delete_project_template(template_id))
        if json_mode:
            echo_json(True, data=data, message="project template deleted")
            return
        obj.skin.success(f"Deleted template: {template_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@project_template_cli.command(name="apply")
@click.option("--id", "template_id", required=True, help="Template id")
@click.option("--name", "-n", required=True, help="New project name")
@click.option("--description", "-d", default=None)
@click.option("--starts-at", default=None, help="ISO start date for offset base")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def apply_template(obj, template_id, name, description, starts_at, as_json):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    try:
        data = asyncio.run(
            client.apply_project_template(
                template_id, name=name, description=description, starts_at=starts_at
            )
        )
        if json_mode:
            echo_json(True, data=data, message="project created from template")
            return
        proj = (data or {}).get("project") or {}
        miles = (data or {}).get("milestones") or []
        obj.skin.success(f"Created project: {proj.get('name')} ({len(miles)} milestones)")
    except APIError as e:
        handle_api_error(e, json_mode)


@project_template_cli.command(name="from-project")
@click.option("--project-id", required=True)
@click.option("--name", "-n", required=True)
@click.option("--description", "-d", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def from_project(obj, project_id, name, description, as_json):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    json_mode = as_json or obj.json_mode
    try:
        data = asyncio.run(
            client.project_template_from_project(
                project_id, name=name, description=description
            )
        )
        if json_mode:
            echo_json(True, data=data, message="template saved from project")
            return
        obj.skin.success(f"Saved template: {data.get('name')}")
    except APIError as e:
        handle_api_error(e, json_mode)
