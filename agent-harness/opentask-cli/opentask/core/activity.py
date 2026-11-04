"""Activity commands (E47)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="activity")
def activity_cli():
    """Workspace Activity Feed（只读 timeline）。"""
    pass


@activity_cli.command(name="list")
@click.option("--since", default=None, help="ISO lower bound on created_at")
@click.option("--action-type", "action_types", multiple=True, help="Filter action_type (repeatable)")
@click.option("--issue", "issue_id", default=None, help="Filter to one issue id")
@click.option("--limit", default=50, show_default=True, type=int, help="Page size (server clamps to 200)")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def activity_list(obj, since, action_types, issue_id, limit, as_json):
    """List workspace activity feed.

    Examples:
      opentask activity list --since 2026-11-01T00:00:00 --action-type status_changed
      opentask activity list --issue <id> --limit 20 --json
    """
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    params = {"limit": limit}
    if since:
        params["since"] = since
    if issue_id:
        params["issueId"] = issue_id
    if action_types:
        params["actionType"] = list(action_types)
    try:
        data = asyncio.run(client.list_workspace_activity(params))
        if json_mode:
            echo_json(True, data=data)
            return
        if not isinstance(data, dict):
            obj.skin.info(str(data))
            return
        items = data.get("items") or []
        if not items:
            obj.skin.info("No activity")
            return
        for it in items:
            actor = (it.get("actor") or {}).get("displayName") or (it.get("actor") or {}).get("username") or "-"
            code = it.get("issueCode") or it.get("issueId") or "-"
            action = it.get("actionType") or "-"
            created = it.get("createdAt") or ""
            obj.skin.info(f"{created}  {code}  {actor}  {action}")
        nxt = data.get("nextCursor")
        if nxt:
            obj.skin.info(f"(nextCursor available: {nxt[:24]}…)")
    except APIError as e:
        handle_api_error(e, json_mode)
