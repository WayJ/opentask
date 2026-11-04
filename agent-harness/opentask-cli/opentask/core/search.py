"""E60: top-level global search command."""
from __future__ import annotations

import asyncio

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.command(name="search")
@click.argument("q")
@click.option("--limit", default=10, show_default=True, type=int, help="Max hits per group (1..50)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def search_cli(obj, q: str, limit: int, as_json: bool):
    """Workspace global search (issues / projects / docs / members)."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    lim = max(1, min(50, int(limit or 10)))
    client = make_client(config)
    try:
        data = asyncio.run(client.global_search(q, limit=lim))
        if json_mode:
            echo_json(True, data=data)
            return
        if not isinstance(data, dict):
            obj.skin.info(str(data))
            return
        for group in ("issues", "projects", "docs", "members"):
            rows = data.get(group) or []
            obj.skin.info(f"{group}: {len(rows)}")
            for row in rows:
                if group == "issues":
                    line = f"  {row.get('issueCode')} · {row.get('title')}"
                elif group == "projects":
                    line = f"  {row.get('name')}"
                elif group == "docs":
                    line = f"  {row.get('title')}"
                else:
                    line = f"  {row.get('name') or row.get('username') or row.get('userId')}"
                if row.get("rank") is not None:
                    line += f" (rank={row.get('rank')})"
                obj.skin.info(line)
    except APIError as e:
        handle_api_error(e, json_mode)
