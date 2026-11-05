"""Customer Request commands (E22)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="request")
def request_cli():
    """Customer Requests（客户需求）。"""
    pass


@request_cli.command(name="list")
@click.option("--customer", "customer_id", default=None, help="按客户 ID 过滤")
@click.option("--status", default=None, type=click.Choice(["open", "completed", "canceled"]))
@click.option("--issue", "issue_id", default=None, help="按关联 Issue ID 过滤")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def request_list(obj, customer_id, status, issue_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(
            client.list_customer_requests(
                customer_id=customer_id, status=status, issue_id=issue_id
            )
        )
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无客户需求")
            return
        obj.skin.table(
            ["ID", "Title", "Customer", "Status", "Issues"],
            [
                [
                    (r.get("id") or "")[:8],
                    (r.get("title") or "")[:40],
                    (r.get("customerName") or (r.get("customerId") or "")[:8]),
                    r.get("status") or "",
                    str(r.get("issueCount") or 0),
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@request_cli.command(name="create")
@click.option("--customer", "customer_id", required=True, help="客户 ID")
@click.option("--title", "-t", required=True)
@click.option("--body", "-b", default=None)
@click.option("--priority", default=None, type=click.Choice(["low", "medium", "high", "urgent"]))
@click.option("--link-issue", "create_and_link", is_flag=True, help="创建并链到新 Issue")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def request_create(obj, customer_id, title, body, priority, create_and_link, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        kwargs = {"createAndLinkIssue": create_and_link}
        if body is not None:
            kwargs["body"] = body
        if priority is not None:
            kwargs["priority"] = priority
        data = asyncio.run(client.create_customer_request(customer_id, title, **kwargs))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建需求: {data.get('id', '')}")
        if data.get("issueIds"):
            obj.skin.info(f"关联 Issue: {', '.join(data.get('issueIds') or [])}")
    except APIError as e:
        handle_api_error(e, json_mode)


@request_cli.command(name="link-issue")
@click.argument("request_id")
@click.argument("issue_ref")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def request_link_issue(obj, request_id, issue_ref, as_json):
    """将 Request 关联到 Issue（UUID 或 KEY-N）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        issue_id = issue_ref
        # Resolve KEY-N → id when looks like code
        if "-" in issue_ref and not _looks_uuid(issue_ref):
            found = asyncio.run(client.get_issue(issue_ref, by_code=True))
            issue_id = found.get("id") or issue_ref
        data = asyncio.run(client.link_customer_request_issue(request_id, issue_id))
        if json_mode:
            echo_json(True, data=data, message="linked")
            return
        obj.skin.success(f"已关联 Issue {issue_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


def _looks_uuid(value: str) -> bool:
    parts = value.split("-")
    return len(parts) == 5 and len(value) >= 32


@request_cli.group(name="status-link")
def request_status_link():
    """公开状态链接 enable|rotate|revoke|show（E63）。"""
    pass


@request_status_link.command(name="enable")
@click.argument("request_id")
@click.option("--allow-public-replies", is_flag=True, help="启用时同时打开公开回复")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def status_link_enable(obj, request_id, allow_public_replies, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        kwargs = {}
        if allow_public_replies:
            kwargs["public_replies_enabled"] = True
        data = asyncio.run(client.enable_customer_request_status_link(request_id, **kwargs))
        if json_mode:
            echo_json(True, data=data, message="enabled")
            return
        sl = (data or {}).get("statusLink") or {}
        token = (data or {}).get("token") or ""
        obj.skin.success(f"已启用 status-link url={sl.get('url')} token={token[:8]}…")
    except APIError as e:
        handle_api_error(e, json_mode)


@request_status_link.command(name="rotate")
@click.argument("request_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def status_link_rotate(obj, request_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.rotate_customer_request_status_link(request_id))
        if json_mode:
            echo_json(True, data=data, message="rotated")
            return
        sl = (data or {}).get("statusLink") or {}
        obj.skin.success(f"已轮换 status-link url={sl.get('url')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@request_status_link.command(name="revoke")
@click.argument("request_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def status_link_revoke(obj, request_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.revoke_customer_request_status_link(request_id))
        if json_mode:
            echo_json(True, data=data, message="revoked")
            return
        obj.skin.success("已撤销 status-link")
    except APIError as e:
        handle_api_error(e, json_mode)


@request_status_link.command(name="show")
@click.argument("request_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def status_link_show(obj, request_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_customer_request(request_id, include_token=True))
        if json_mode:
            echo_json(True, data=data)
            return
        sl = (data or {}).get("statusLink") or {}
        obj.skin.info(
            f"enabled={sl.get('enabled')} url={sl.get('url')} "
            f"publicReplies={sl.get('publicRepliesEnabled')} token={(data or {}).get('token') or ''}"
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@request_cli.command(name="public-status")
@click.argument("token")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def request_public_status(obj, token, as_json):
    """探测公开状态卡（无需工作区，E63）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    client = make_client(config)
    try:
        data = asyncio.run(client.public_customer_request_status(token))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.info(
            f"{(data or {}).get('title')} · status={(data or {}).get('status')} "
            f"codes={','.join((data or {}).get('linkedIssueCodes') or [])}"
        )
    except APIError as e:
        handle_api_error(e, json_mode)
