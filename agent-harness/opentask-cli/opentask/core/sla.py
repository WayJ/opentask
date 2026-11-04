"""SLA policy + clocks + run-due commands (E42)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="sla")
def sla_cli():
    """SLA 策略 / Issue 时钟 / run-due / business-hours（E50）。

示例: opentask sla policy create --name FR --start in_progress --metric first_response --minutes 60
营业时: opentask sla business-hours show | set | exceptions list|add|remove（E53）
"""
    pass


@sla_cli.group(name="policy")
def policy_cli():
    """SLA 策略 CRUD。"""
    pass


@policy_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_sla_policies())
        rows = (data or {}).get("rows") or []
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.section(f"SLA policies ({len(rows)})")
        table = []
        for r in rows:
            table.append(
                [
                    (r.get("id") or "")[:8],
                    r.get("name") or "",
                    "on" if r.get("enabled") else "off",
                    r.get("metric") or "",
                    str(r.get("targetMinutes") or ""),
                    ",".join(r.get("startStatuses") or []),
                    ",".join(r.get("pauseStatuses") or []) or "—",
                ]
            )
        obj.skin.table(["ID", "Name", "Enabled", "Metric", "Minutes", "Start", "Pause"], table)
    except APIError as e:
        handle_api_error(e, json_mode)


@policy_cli.command(name="show")
@click.argument("policy_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_show(obj, policy_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_sla_policies())
        rows = (data or {}).get("rows") or []
        row = next((r for r in rows if r.get("id") == policy_id or (r.get("id") or "").startswith(policy_id)), None)
        if not row:
            raise click.ClickException("策略不存在")
        if json_mode:
            echo_json(True, data=row)
            return
        obj.skin.section(row.get("name") or policy_id)
        for k, v in row.items():
            obj.skin.info(f"{k}: {v}")
    except APIError as e:
        handle_api_error(e, json_mode)


@policy_cli.command(name="create")
@click.option("--name", required=True)
@click.option("--start", "starts", multiple=True, required=True, help="start status (repeatable)")
@click.option("--stop", "stops", multiple=True, help="stop status (repeatable; empty=closed-class)")
@click.option("--pause", "pauses", multiple=True, help="pause status (repeatable; empty=no pause)")
@click.option(
    "--metric",
    default="time_in_status",
    show_default=True,
    type=click.Choice(["time_in_status", "first_response"]),
    help="SLA metric (first_response = 非创建者首评)",
)
@click.option("--minutes", default=1440, show_default=True, type=int)
@click.option("--notify-assignee/--no-notify-assignee", default=True)
@click.option("--notify-watchers/--no-notify-watchers", default=False)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_create(obj, name, starts, stops, pauses, metric, minutes, notify_assignee, notify_watchers, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {
        "name": name,
        "startStatuses": list(starts),
        "stopStatuses": list(stops),
        "pauseStatuses": list(pauses),
        "targetMinutes": minutes,
        "metric": metric,
        "notifyAssignee": notify_assignee,
        "notifyWatchers": notify_watchers,
    }
    client = make_client(config)
    try:
        data = asyncio.run(client.create_sla_policy(body))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建: {(data or {}).get('id', '')[:8]} {name}")
    except APIError as e:
        handle_api_error(e, json_mode)


@policy_cli.command(name="update")
@click.argument("policy_id")
@click.option("--name", default=None)
@click.option("--minutes", default=None, type=int)
@click.option("--pause", "pauses", multiple=True, help="replace pause statuses (repeatable; omit=unchanged; empty flag not supported — use --json-body)")
@click.option(
    "--metric",
    default=None,
    type=click.Choice(["time_in_status", "first_response"]),
    help="SLA metric",
)
@click.option("--enabled/--disabled", "enabled", default=None)
@click.option("--json-body", default=None, help="raw JSON patch body (may include pauseStatuses/metric)")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_update(obj, policy_id, name, minutes, pauses, metric, enabled, json_body, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {}
    if json_body:
        try:
            body = json.loads(json_body)
        except json.JSONDecodeError as e:
            raise click.ClickException(f"无效 JSON: {e}") from e
    if name is not None:
        body["name"] = name
    if minutes is not None:
        body["targetMinutes"] = minutes
    if enabled is not None:
        body["enabled"] = enabled
    if pauses:
        body["pauseStatuses"] = list(pauses)
    if metric is not None:
        body["metric"] = metric
    if not body:
        raise click.ClickException("无更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_sla_policy(policy_id, body))
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success(f"已更新: {policy_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@policy_cli.command(name="delete")
@click.argument("policy_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_delete(obj, policy_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_sla_policy(policy_id))
        if json_mode:
            echo_json(True, data=data, message="deleted")
            return
        obj.skin.success(f"已删除: {policy_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@sla_cli.command(name="issue")
@click.argument("issue_ref")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def sla_issue(obj, issue_ref, as_json):
    """列出 Issue 的 SLA 时钟（id 或 issue code）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_issue_sla(issue_ref))
        rows = (data or {}).get("rows") or []
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.section(f"SLA clocks for {issue_ref} ({len(rows)})")
        table = []
        for r in rows:
            table.append(
                [
                    (r.get("id") or "")[:8],
                    r.get("policyName") or (r.get("policyId") or "")[:8],
                    r.get("metric") or "",
                    r.get("status"),
                    (r.get("deadlineAt") or "")[:19],
                    str(r.get("elapsedBeforePauseMinutes") if r.get("elapsedBeforePauseMinutes") is not None else ""),
                    (r.get("pausedAt") or "")[:19],
                ]
            )
        obj.skin.table(["Clock", "Policy", "Metric", "Status", "Deadline", "Elapsed", "PausedAt"], table)
    except APIError as e:
        handle_api_error(e, json_mode)


@sla_cli.command(name="run-due")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def sla_run_due(obj, as_json):
    """将到期 running 时钟标为 breached 并投递 Inbox（UTC；无内置 cron）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.run_due_sla())
        if json_mode:
            echo_json(True, data=data, message="run-due")
            return
        obj.skin.success(
            f"scanned={data.get('scanned')} breached={data.get('breached')} "
            f"notifications={data.get('notificationsCreated')} skipped={data.get('skipped')}"
        )
        for err in data.get("errors") or []:
            obj.skin.warn(f"  error {err.get('clockId')}: {err.get('message')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@sla_cli.group(name="business-hours")
def business_hours_cli():
    """工作区营业时段（E50）+ 例外日（E53），挂在 Workspace。"""
    pass


@business_hours_cli.command(name="show")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def business_hours_show(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_workspace(config.active_workspace_id))
        payload = {
            "timezone": (data or {}).get("timezone"),
            "businessHours": (data or {}).get("businessHours") or {"enabled": False, "windows": {}},
        }
        if json_mode:
            echo_json(True, data=payload)
            return
        bh = payload["businessHours"] or {}
        obj.skin.section("SLA business hours")
        obj.skin.status_block({
            "Timezone": payload.get("timezone") or "—",
            "Enabled": "on" if bh.get("enabled") else "off",
            "Windows": json.dumps(bh.get("windows") or {}, ensure_ascii=False),
            "Exceptions": json.dumps(bh.get("exceptions") or [], ensure_ascii=False),
        })
        obj.skin.hint("run-due 仍比 UTC deadline_at；启用营业时后 deadline 按营业分钟写出；exceptions=closed|forced_open")
    except APIError as e:
        handle_api_error(e, json_mode)


@business_hours_cli.command(name="set")
@click.option("--timezone", default=None, help="IANA timezone")
@click.option("--enabled/--disabled", "enabled", default=None)
@click.option("--windows-json", default=None, help="windows JSON object mon..sun")
@click.option("--exceptions-json", default=None, help="exceptions JSON array (E53)")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def business_hours_set(obj, timezone, enabled, windows_json, exceptions_json, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {}
    if timezone is not None:
        body["timezone"] = timezone
    if enabled is not None or windows_json is not None or exceptions_json is not None:
        client0 = make_client(config)
        current = asyncio.run(client0.get_workspace(config.active_workspace_id)) or {}
        cur_bh = current.get("businessHours") or {}
        bh = {
            "enabled": bool(enabled) if enabled is not None else bool(cur_bh.get("enabled")),
            "windows": cur_bh.get("windows") or {},
            "exceptions": cur_bh.get("exceptions") or [],
        }
        if windows_json:
            bh["windows"] = json.loads(windows_json)
        if exceptions_json is not None:
            bh["exceptions"] = json.loads(exceptions_json)
        if enabled is not None:
            bh["enabled"] = bool(enabled)
        body["businessHours"] = bh
    if not body:
        raise click.ClickException("请提供 --timezone / --enabled / --windows-json / --exceptions-json")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_workspace(config.active_workspace_id, **body))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("business hours 已更新")
    except APIError as e:
        handle_api_error(e, json_mode)


@business_hours_cli.group(name="exceptions")
def exceptions_cli():
    """例外日 CRUD（E53：closed | forced_open）。"""
    pass


@exceptions_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def exceptions_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_workspace(config.active_workspace_id))
        bh = (data or {}).get("businessHours") or {}
        rows = bh.get("exceptions") or []
        if json_mode:
            echo_json(True, data={"exceptions": rows})
            return
        obj.skin.section(f"business-hours exceptions ({len(rows)})")
        if not rows:
            obj.skin.hint("暂无例外日")
            return
        table = []
        for r in rows:
            wins = r.get("windows") or []
            win_s = ",".join(f"{w.get('start')}-{w.get('end')}" for w in wins) if wins else "—"
            table.append([r.get("date") or "", r.get("kind") or "", win_s])
        obj.skin.table(["Date", "Kind", "Windows"], table)
    except APIError as e:
        handle_api_error(e, json_mode)


@exceptions_cli.command(name="add")
@click.option("--date", "date_s", required=True, help="YYYY-MM-DD local WS day")
@click.option(
    "--kind",
    required=True,
    type=click.Choice(["closed", "forced_open"]),
    help="closed = 全日非营业; forced_open = 覆盖周窗",
)
@click.option("--windows-json", default=None, help='optional windows JSON e.g. [{"start":"09:00","end":"18:00"}]')
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def exceptions_add(obj, date_s, kind, windows_json, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_workspace(config.active_workspace_id)) or {}
        bh = dict(data.get("businessHours") or {})
        rows = list(bh.get("exceptions") or [])
        entry = {"date": date_s, "kind": kind}
        if windows_json:
            entry["windows"] = json.loads(windows_json)
        # replace same date if present
        rows = [r for r in rows if r.get("date") != date_s]
        rows.append(entry)
        bh["exceptions"] = rows
        if "windows" not in bh:
            bh["windows"] = {}
        if "enabled" not in bh:
            bh["enabled"] = False
        updated = asyncio.run(
            client.update_workspace(
                config.active_workspace_id,
                businessHours=bh,
                timezone=data.get("timezone"),
            )
        )
        if json_mode:
            echo_json(True, data=updated, message="exception added")
            return
        obj.skin.success(f"已添加例外 {date_s} ({kind})")
    except APIError as e:
        handle_api_error(e, json_mode)


@exceptions_cli.command(name="remove")
@click.option("--date", "date_s", required=True, help="YYYY-MM-DD to remove")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def exceptions_remove(obj, date_s, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_workspace(config.active_workspace_id)) or {}
        bh = dict(data.get("businessHours") or {})
        before = list(bh.get("exceptions") or [])
        rows = [r for r in before if r.get("date") != date_s]
        if len(rows) == len(before):
            raise click.ClickException(f"未找到例外日: {date_s}")
        bh["exceptions"] = rows
        if "windows" not in bh:
            bh["windows"] = {}
        if "enabled" not in bh:
            bh["enabled"] = False
        updated = asyncio.run(
            client.update_workspace(
                config.active_workspace_id,
                businessHours=bh,
                timezone=data.get("timezone"),
            )
        )
        if json_mode:
            echo_json(True, data=updated, message="exception removed")
            return
        obj.skin.success(f"已删除例外 {date_s}")
    except APIError as e:
        handle_api_error(e, json_mode)
