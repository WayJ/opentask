"""Workspace members + invites (E14)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="member")
def member_cli():
    """工作区成员。"""
    pass


def _ws(config: Config, json_mode: bool, workspace_id: str | None) -> str | None:
    return workspace_id or require_workspace_id(config, json_mode)


@member_cli.command(name="list")
@click.option("--workspace", "workspace_id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def member_list(obj, workspace_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    wid = _ws(config, json_mode, workspace_id)
    if not wid:
        raise SystemExit(1)
    client = make_client(config)
    try:
        rows = asyncio.run(client.list_workspace_members(wid))
        if json_mode:
            echo_json(True, data={"rows": rows, "total": len(rows)})
            return
        if not rows:
            obj.skin.info("无成员")
            return
        obj.skin.table(
            ["User", "Role"],
            [[r.get("userId") or r.get("user_id") or "", r.get("role") or ""] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@member_cli.command(name="add")
@click.option("--user", "user_id", required=True)
@click.option("--role", default="member", type=click.Choice(["owner", "member", "viewer"]))
@click.option("--workspace", "workspace_id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def member_add(obj, user_id, role, workspace_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    wid = _ws(config, json_mode, workspace_id)
    if not wid:
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.add_workspace_member(wid, user_id, role))
        if json_mode:
            echo_json(True, data=data, message="added")
            return
        obj.skin.success("已添加成员")
    except APIError as e:
        handle_api_error(e, json_mode)


@member_cli.command(name="remove")
@click.option("--user", "user_id", required=True)
@click.option("--workspace", "workspace_id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def member_remove(obj, user_id, workspace_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    wid = _ws(config, json_mode, workspace_id)
    if not wid:
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.remove_workspace_member(wid, user_id))
        if json_mode:
            echo_json(True, data=data or {"userId": user_id})
            return
        obj.skin.success("已移除成员")
    except APIError as e:
        handle_api_error(e, json_mode)


@member_cli.command(name="role")
@click.option("--user", "user_id", required=True)
@click.option("--role", required=True, type=click.Choice(["owner", "member", "viewer"]))
@click.option("--workspace", "workspace_id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def member_role(obj, user_id, role, workspace_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    wid = _ws(config, json_mode, workspace_id)
    if not wid:
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.update_workspace_member_role(wid, user_id, role))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success(f"角色已更新为 {role}")
    except APIError as e:
        handle_api_error(e, json_mode)


@click.group(name="invite")
def invite_cli():
    """工作区邀请。"""
    pass


@invite_cli.command(name="list")
@click.option("--workspace", "workspace_id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def invite_list(obj, workspace_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    wid = _ws(config, json_mode, workspace_id)
    if not wid:
        raise SystemExit(1)
    client = make_client(config)
    try:
        rows = asyncio.run(client.list_workspace_invites(wid))
        if json_mode:
            echo_json(True, data={"rows": rows, "total": len(rows)})
            return
        if not rows:
            obj.skin.info("无邀请")
            return
        obj.skin.table(
            ["ID", "Email", "Role", "Token"],
            [[
                (r.get("id") or "")[:8],
                r.get("email") or "",
                r.get("role") or "",
                (r.get("token") or "")[:12],
            ] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@invite_cli.command(name="create")
@click.option("--email", default=None)
@click.option("--role", default="member", type=click.Choice(["member", "viewer"]))
@click.option("--workspace", "workspace_id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def invite_create(obj, email, role, workspace_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    wid = _ws(config, json_mode, workspace_id)
    if not wid:
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.create_workspace_invite(wid, email=email, role=role))
        if json_mode:
            echo_json(True, data=data, message="invite created")
            return
        obj.skin.success(f"邀请已创建 token={(data or {}).get('token', '')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@invite_cli.command(name="revoke")
@click.argument("invite_id")
@click.option("--workspace", "workspace_id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def invite_revoke(obj, invite_id, workspace_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    wid = _ws(config, json_mode, workspace_id)
    if not wid:
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.revoke_workspace_invite(wid, invite_id))
        if json_mode:
            echo_json(True, data=data or {"id": invite_id})
            return
        obj.skin.success("邀请已撤销")
    except APIError as e:
        handle_api_error(e, json_mode)


@invite_cli.command(name="preview")
@click.argument("token")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def invite_preview(obj, token, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    client = make_client(config)
    try:
        data = asyncio.run(client.preview_invite(token))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.status_block({k: str(v) for k, v in (data or {}).items()})
    except APIError as e:
        handle_api_error(e, json_mode)


@invite_cli.command(name="accept")
@click.argument("token")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def invite_accept(obj, token, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    client = make_client(config)
    try:
        data = asyncio.run(client.accept_invite(token))
        if json_mode:
            echo_json(True, data=data, message="accepted")
            return
        obj.skin.success("已接受邀请")
    except APIError as e:
        handle_api_error(e, json_mode)
