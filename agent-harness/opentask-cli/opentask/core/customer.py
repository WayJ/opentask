"""Customer commands (E22)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="customer")
def customer_cli():
    """Customers（客户账户）。"""
    pass


@customer_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def customer_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_customers())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无客户")
            return
        obj.skin.table(
            ["ID", "Name", "Domains", "Requests"],
            [
                [
                    (r.get("id") or "")[:8],
                    r.get("name") or "",
                    ",".join(r.get("domains") or []),
                    str(r.get("requestCount") or 0),
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@customer_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--domain", "-d", multiple=True, help="可重复；客户域名")
@click.option("--url", "external_url", default=None, help="外链")
@click.option("--notes", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def customer_create(obj, name, domain, external_url, notes, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        kwargs = {}
        if domain:
            kwargs["domains"] = list(domain)
        if external_url is not None:
            kwargs["externalUrl"] = external_url
        if notes is not None:
            kwargs["notes"] = notes
        data = asyncio.run(client.create_customer(name, **kwargs))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建客户: {data.get('id', '')}")
    except APIError as e:
        handle_api_error(e, json_mode)
