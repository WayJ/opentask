"""Triage commands (E14)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="triage")
def triage_cli():
    """分诊队列 Triage。"""
    pass


@triage_cli.command(name="list")
@click.option("--page", default=1)
@click.option("--page-size", default=50)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def triage_list(obj, page, page_size, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_triage(page=page, page_size=page_size))
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("分诊队列为空")
            return
        obj.skin.table(
            ["Issue", "Title", "Priority", "Type"],
            [[
                (r.get("issueCode") or r.get("issue_code") or r.get("id") or "")[:16],
                (r.get("title") or "")[:40],
                r.get("priority") or "",
                r.get("type") or "",
            ] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@triage_cli.command(name="enqueue")
@click.option("--issue", "issue_id", default=None, help="Existing issue id")
@click.option("--title", "-t", default=None, help="Create + enqueue title")
@click.option("--type", "issue_type", default="feedback")
@click.option("--priority", "-p", default="medium")
@click.option("--description", "-d", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def triage_enqueue(obj, issue_id, title, issue_type, priority, description, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if not issue_id and not title:
        raise click.UsageError("需要 --issue 或 --title")
    client = make_client(config)
    try:
        data = asyncio.run(client.enqueue_triage(
            issue_id=issue_id, title=title, type=issue_type, priority=priority, description=description
        ))
        if json_mode:
            echo_json(True, data=data, message="enqueued")
            return
        obj.skin.success("已加入分诊")
    except APIError as e:
        handle_api_error(e, json_mode)


@triage_cli.command(name="accept")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def triage_accept(obj, issue_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.accept_triage(issue_id))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已接受")
    except APIError as e:
        handle_api_error(e, json_mode)


@triage_cli.command(name="decline")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def triage_decline(obj, issue_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.decline_triage(issue_id))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已拒绝")
    except APIError as e:
        handle_api_error(e, json_mode)


@triage_cli.command(name="duplicate")
@click.argument("issue_id")
@click.option("--of", "duplicate_of", required=True, help="Canonical issue id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def triage_duplicate(obj, issue_id, duplicate_of, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.duplicate_triage(issue_id, duplicate_of))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已标记重复")
    except APIError as e:
        handle_api_error(e, json_mode)
