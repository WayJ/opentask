"""Cycle commands (E14)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id, unwrap_rows
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


@click.group(name="cycle")
def cycle_cli():
    """迭代 Cycle（需已 workspace use）。"""
    pass


@cycle_cli.command(name="list")
@click.option("--status", "-s", help="Filter status")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_list(obj, status, as_json):
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_cycles(status=status))
        rows = unwrap_rows(data) if not (isinstance(data, dict) and "rows" in data) else data.get("rows", [])
        if isinstance(data, dict) and "rows" in data:
            rows = data["rows"]
            total = data.get("total", len(rows))
        else:
            total = len(rows)
        if json_mode:
            echo_json(True, data={"rows": rows, "total": total})
            return
        if not rows:
            skin.info("暂无 Cycle")
            return
        skin.section("Cycles")
        skin.table(
            ["ID", "Name", "Status", "Starts", "Ends"],
            [[
                (r.get("id") or "")[:8],
                r.get("name") or "",
                r.get("status") or "",
                str(r.get("startsAt") or r.get("starts_at") or "")[:10],
                str(r.get("endsAt") or r.get("ends_at") or "")[:10],
            ] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@cycle_cli.command(name="show")
@click.argument("cycle_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_show(obj, cycle_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_cycle(cycle_id))
        if json_mode:
            echo_json(True, data=data)
            return
        d = data or {}
        hint = {}
        try:
            hint = asyncio.run(client.get_cycle_capacity_hint(cycle_id)) or {}
        except APIError:
            hint = {}
        block = {
            "ID": d.get("id", ""),
            "Name": d.get("name", ""),
            "Status": d.get("status", ""),
            "Starts": str(d.get("startsAt") or d.get("starts_at") or ""),
            "Ends": str(d.get("endsAt") or d.get("ends_at") or ""),
        }
        if hint:
            block["CapacityUnit"] = hint.get("unit", "")
            block["SuggestedCapacity"] = hint.get("suggestedCapacity", "")
            load = hint.get("currentLoad") or {}
            if load:
                block["LoadPoints"] = load.get("points", "")
                block["LoadIssues"] = load.get("issueCount", "")
        obj.skin.status_block(block)
    except APIError as e:
        handle_api_error(e, json_mode)


@cycle_cli.command(name="create")
@click.option("--name", "-n", default=None)
@click.option("--starts-at", required=True, help="ISO datetime")
@click.option("--ends-at", required=True, help="ISO datetime")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_create(obj, name, starts_at, ends_at, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.create_cycle(starts_at=starts_at, ends_at=ends_at, name=name))
        if json_mode:
            echo_json(True, data=data, message="cycle created")
            return
        obj.skin.success(f"Cycle 已创建: {data.get('id', '')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@cycle_cli.command(name="activate")
@click.argument("cycle_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_activate(obj, cycle_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.activate_cycle(cycle_id))
        if json_mode:
            echo_json(True, data=data, message="activated")
            return
        obj.skin.success("Cycle 已激活")
    except APIError as e:
        handle_api_error(e, json_mode)


@cycle_cli.command(name="complete")
@click.argument("cycle_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_complete(obj, cycle_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.complete_cycle(cycle_id))
        if json_mode:
            echo_json(True, data=data, message="completed")
            return
        obj.skin.success("Cycle 已完成")
    except APIError as e:
        handle_api_error(e, json_mode)


@cycle_cli.command(name="capacity")
@click.option("--cycle-id", default=None, help="Optional cycle id for currentLoad")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_capacity(obj, cycle_id, as_json):
    """Show points-first capacity / velocity hint for the workspace."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_cycle_capacity_hint(cycle_id))
        if json_mode:
            echo_json(True, data=data)
            return
        d = data or {}
        skin.section("Cycle capacity")
        skin.status_block({
            "Basis": d.get("basis", ""),
            "Unit": d.get("unit", ""),
            "Suggested": d.get("suggestedCapacity", ""),
            "LookbackN": d.get("lookbackN", ""),
        })
        samples = d.get("samples") or []
        if samples:
            skin.table(
                ["Cycle", "Points", "Issues", "Hours"],
                [[
                    (s.get("name") or s.get("cycleId") or "")[:24],
                    s.get("completedPoints", ""),
                    s.get("completedIssueCount", ""),
                    s.get("completedHours", ""),
                ] for s in samples],
            )
        load = d.get("currentLoad")
        if load:
            skin.info("Current load")
            skin.status_block({
                "Points": load.get("points", ""),
                "Issues": load.get("issueCount", ""),
                "Hours": load.get("hours", ""),
            })
    except APIError as e:
        handle_api_error(e, json_mode)



@cycle_cli.command(name="generate-upcoming")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_generate_upcoming(obj, as_json):
    """Generate the next upcoming Cycle for the workspace."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.generate_upcoming_cycle())
        if json_mode:
            echo_json(True, data=data, message="generated upcoming")
            return
        d = data or {}
        obj.skin.success(f"已生成下一 Cycle: {d.get('id', '')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@cycle_cli.command(name="update")
@click.argument("cycle_id")
@click.option("--name", "-n", default=None)
@click.option("--starts-at", default=None, help="ISO datetime")
@click.option("--ends-at", default=None, help="ISO datetime")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_update(obj, cycle_id, name, starts_at, ends_at, as_json):
    """Partial-update a Cycle (only send fields you pass)."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {}
    if name is not None:
        body["name"] = name
    if starts_at is not None:
        body["starts_at"] = starts_at
    if ends_at is not None:
        body["ends_at"] = ends_at
    if not body:
        raise click.UsageError("至少提供一个更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_cycle(cycle_id, **body))
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success("Cycle 已更新")
    except APIError as e:
        handle_api_error(e, json_mode)


@cycle_cli.command(name="delete")
@click.argument("cycle_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def cycle_delete(obj, cycle_id, as_json):
    """Delete a Cycle without interactive confirmation (script-friendly)."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_cycle(cycle_id))
        if json_mode:
            echo_json(True, data=data or {"id": cycle_id}, message="deleted")
            return
        obj.skin.success("Cycle 已删除")
    except APIError as e:
        handle_api_error(e, json_mode)
