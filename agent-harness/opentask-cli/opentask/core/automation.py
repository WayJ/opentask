"""Automation commands (E26 + E33 CF)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config

TRIGGERS = [
    "issue.created",
    "issue.status_changed",
    "issue.assignee_changed",
    "label_added",
    "custom_field_changed",
    "issue.sla_breached",  # E45; set_status may re-enter start — configure carefully
]
ACTIONS = [
    "set_status",
    "set_assignee",
    "add_label",
    "set_priority",
    "add_comment",
    "set_custom_field",
]


@click.group(name="automation")
def automation_cli():
    """Workspace 自动化规则。"""
    pass


@automation_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_automations())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无自动化规则")
            return
        obj.skin.table(
            ["Name", "Trigger", "Action", "Enabled", "Id"],
            [
                [
                    r.get("name") or "",
                    r.get("triggerType") or "",
                    r.get("actionType") or "",
                    "yes" if r.get("enabled") else "no",
                    (r.get("id") or "")[:8],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@automation_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--trigger", "trigger_type", required=True, type=click.Choice(TRIGGERS, case_sensitive=False))
@click.option("--action", "action_type", required=True, type=click.Choice(ACTIONS, case_sensitive=False))
@click.option("--trigger-config", default="{}", help='JSON object；cf-changed 例 {"field_key":"tier","from":"free","to":"pro"}')
@click.option(
    "--action-config",
    default="{}",
    help='JSON；含 delay_minutes 例 {"priority":"high","delay_minutes":60}',
)
@click.option(
    "--condition",
    default=None,
    help='JSON object；CF 例 {"customField":{...}} 或 {"customFields":[...]}（≤5）',
)
@click.option("--disabled", is_flag=True, help="创建为禁用")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_create(
    obj, name, trigger_type, action_type, trigger_config, action_config, condition, disabled, as_json
):
    """创建规则。action-config 可含 delay_minutes（0=即时，1…10080）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    try:
        tcfg = json.loads(trigger_config or "{}")
        acfg = json.loads(action_config or "{}")
        cond = json.loads(condition) if condition else None
    except json.JSONDecodeError as e:
        raise click.ClickException(f"JSON 无效: {e}") from e
    client = make_client(config)
    try:
        data = asyncio.run(
            client.create_automation(
                name,
                trigger_type,
                action_type,
                trigger_config=tcfg,
                action_config=acfg,
                condition=cond,
                enabled=not disabled,
            )
        )
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建规则: {data.get('name')} ({(data.get('id') or '')[:8]})")
    except APIError as e:
        handle_api_error(e, json_mode)


@automation_cli.command(name="update")
@click.argument("rule_id")
@click.option("--name", "-n", default=None)
@click.option("--trigger", "trigger_type", default=None, type=click.Choice(TRIGGERS, case_sensitive=False))
@click.option("--action", "action_type", default=None, type=click.Choice(ACTIONS, case_sensitive=False))
@click.option("--trigger-config", default=None, help="JSON object；提供则覆盖")
@click.option("--action-config", default=None, help="JSON object；提供则覆盖")
@click.option("--condition", default=None, help="JSON object；提供则覆盖；传空对象可清条件请用 {}")
@click.option("--clear-condition", is_flag=True, help="清空条件")
@click.option("--enable", "enable_flag", is_flag=True, help="启用规则")
@click.option("--disable", "disable_flag", is_flag=True, help="禁用规则")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_update(
    obj,
    rule_id,
    name,
    trigger_type,
    action_type,
    trigger_config,
    action_config,
    condition,
    clear_condition,
    enable_flag,
    disable_flag,
    as_json,
):
    """更新规则（含 CF condition / set_custom_field actionConfig）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    payload: dict = {}
    if name is not None:
        payload["name"] = name
    if trigger_type is not None:
        payload["triggerType"] = trigger_type
    if action_type is not None:
        payload["actionType"] = action_type
    try:
        if trigger_config is not None:
            payload["triggerConfig"] = json.loads(trigger_config or "{}")
            payload["setTriggerConfig"] = True
        if action_config is not None:
            payload["actionConfig"] = json.loads(action_config or "{}")
            payload["setActionConfig"] = True
        if clear_condition:
            payload["condition"] = None
            payload["setCondition"] = True
        elif condition is not None:
            payload["condition"] = json.loads(condition)
            payload["setCondition"] = True
    except json.JSONDecodeError as e:
        raise click.ClickException(f"JSON 无效: {e}") from e
    if enable_flag and disable_flag:
        raise click.ClickException("--enable 与 --disable 不能同时使用")
    if enable_flag:
        payload["enabled"] = True
    elif disable_flag:
        payload["enabled"] = False
    if not payload:
        raise click.ClickException("请至少提供一个更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_automation(rule_id, payload))
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success(f"已更新: {data.get('name') or rule_id} ({(data.get('id') or rule_id)[:8]})")
    except APIError as e:
        handle_api_error(e, json_mode)


@automation_cli.command(name="enable")
@click.argument("rule_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_enable(obj, rule_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.enable_automation(rule_id))
        if json_mode:
            echo_json(True, data=data, message="enabled")
            return
        obj.skin.success(f"已启用: {(data.get('id') or rule_id)[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@automation_cli.command(name="disable")
@click.argument("rule_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_disable(obj, rule_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.disable_automation(rule_id))
        if json_mode:
            echo_json(True, data=data, message="disabled")
            return
        obj.skin.success(f"已禁用: {(data.get('id') or rule_id)[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@automation_cli.command(name="run-due")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_run_due(obj, as_json):
    """执行到期的延迟动作（UTC）。外部 tick，无进程内 cron。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.run_due_automations())
        if json_mode:
            echo_json(True, data=data, message="run-due")
            return
        processed = (data or {}).get("processed", 0)
        executed = (data or {}).get("executed", 0)
        cancelled = (data or {}).get("cancelled", 0)
        failed = (data or {}).get("failed", 0)
        obj.skin.success(
            f"processed={processed} executed={executed} cancelled={cancelled} failed={failed}"
        )
        for err in (data or {}).get("errors") or []:
            obj.skin.info(
                f"  pending={err.get('pendingId')} issue={err.get('issueId')} {err.get('message')}"
            )
    except APIError as e:
        handle_api_error(e, json_mode)


@automation_cli.command(name="pending")
@click.option("--status", default="pending", show_default=True, help="pending|done|cancelled|failed")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_pending(obj, status, as_json):
    """列出当前工作区延迟动作队列（默认 pending，最多 100）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_automation_pending(status=status))
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无 pending 动作")
            return
        obj.skin.table(
            ["Status", "RunAt", "Action", "Rule", "Issue", "Id"],
            [
                [
                    r.get("status") or "",
                    (r.get("runAt") or "")[:19],
                    r.get("actionType") or "",
                    (r.get("ruleId") or "")[:8],
                    (r.get("issueId") or "")[:8],
                    (r.get("id") or "")[:8],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)

