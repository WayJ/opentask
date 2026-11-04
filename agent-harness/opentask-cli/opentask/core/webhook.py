"""Outbound webhook commands (E29)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config

EVENTS = [
    "issue.created",
    "issue.updated",
    "issue.status_changed",
    "comment.created",
    "issue.custom_field_changed",
    "issue.sla_breached",
    "issue.assignee_changed",
    "issue.label_added",
    "issue.label_removed",
    "issue.cycle_changed",
    "issue.estimate_changed",
    "issue.project_changed",
    "issue.sla_paused",
    "issue.sla_resumed",
]


@click.group(name="webhook")
def webhook_cli():
    """工作区出站 Webhook。"""
    pass


@webhook_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_webhooks())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无 Webhook")
            return
        obj.skin.table(
            ["Name", "URL", "Events", "Enabled", "Id"],
            [
                [
                    r.get("name") or "",
                    (r.get("url") or "")[:48],
                    ",".join(r.get("events") or []),
                    "yes" if r.get("enabled") else "no",
                    (r.get("id") or "")[:8],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="create")
@click.option("--url", "-u", required=True)
@click.option(
    "--events",
    "-e",
    required=True,
    help="逗号分隔事件（见 webhook events），如 issue.created,issue.cycle_changed",
)
@click.option("--name", "-n", default=None)
@click.option("--disabled", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_create(obj, url, events, name, disabled, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    ev_list = [x.strip() for x in events.split(",") if x.strip()]
    for ev in ev_list:
        if ev not in EVENTS:
            raise click.ClickException(f"未知事件: {ev}；允许: {', '.join(EVENTS)}")
    client = make_client(config)
    try:
        data = asyncio.run(
            client.create_webhook(url, ev_list, name=name, enabled=not disabled)
        )
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        secret = (data or {}).get("secret")
        obj.skin.success(
            f"已创建: {(data.get('id') or '')[:8]} url={data.get('url')}"
        )
        if secret:
            obj.skin.warning(f"Signing secret（仅此一次）: {secret}")
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="update")
@click.argument("webhook_id")
@click.option("--url", default=None)
@click.option("--events", default=None, help="逗号分隔；省略则不改")
@click.option("--name", default=None)
@click.option("--enabled", type=click.BOOL, default=None, help="true/false")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_update(obj, webhook_id, url, events, name, enabled, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {}
    if url is not None:
        body["url"] = url
    if events is not None:
        body["events"] = [x.strip() for x in events.split(",") if x.strip()]
    if name is not None:
        body["name"] = name
        body["setName"] = True
    if enabled is not None:
        body["enabled"] = enabled
    if not body:
        raise click.ClickException("无更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_webhook(webhook_id, body))
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success(f"已更新: {(data.get('id') or webhook_id)[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="delete")
@click.argument("webhook_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_delete(obj, webhook_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_webhook(webhook_id))
        if json_mode:
            echo_json(True, data=data, message="deleted")
            return
        obj.skin.success(f"已删除: {webhook_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="test")
@click.argument("webhook_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_test(obj, webhook_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.test_webhook(webhook_id))
        if json_mode:
            echo_json(True, data=data, message="tested")
            return
        if (data or {}).get("success"):
            obj.skin.success(
                f"测试成功 HTTP {data.get('statusCode')} attempt={data.get('attempt')}"
            )
        else:
            obj.skin.error(f"测试失败: {data.get('error') or data}")
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="deliveries")
@click.argument("webhook_id")
@click.option(
    "--status",
    default=None,
    help="过滤 status：pending_retry|dead|success|success_after_retry",
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_deliveries(obj, webhook_id, status, as_json):
    """列出投递账本（含 status / replayable）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_webhook(webhook_id))
        rows = (data or {}).get("deliveries") or []
        if status:
            rows = [r for r in rows if (r.get("status") or "") == status]
        if json_mode:
            echo_json(True, data={"rows": rows, "total": len(rows)})
            return
        if not rows:
            obj.skin.info("无投递记录")
            return
        obj.skin.table(
            ["Status", "Event", "Attempt", "HTTP", "Replay", "Id"],
            [
                [
                    r.get("status") or ("ok" if r.get("success") else "fail"),
                    (r.get("eventType") or "")[:28],
                    r.get("attempt"),
                    r.get("statusCode") or "",
                    "yes" if r.get("replayable") else "no",
                    (r.get("id") or "")[:8],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="retry")
@click.argument("webhook_id")
@click.argument("delivery_log_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_retry(obj, webhook_id, delivery_log_id, as_json):
    """立即重试一条失败/死信投递。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.retry_webhook_delivery(webhook_id, delivery_log_id))
        if json_mode:
            echo_json(True, data=data, message="retried")
            return
        if (data or {}).get("success"):
            obj.skin.success(
                f"重试成功 HTTP {data.get('statusCode')} attempt={data.get('attempt')}"
            )
        else:
            obj.skin.error(f"重试失败: {data.get('error') or data}")
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="run-due")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_run_due(obj, as_json):
    """执行到期 pending_retry 投递（外部 tick）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.run_due_webhook_deliveries())
        if json_mode:
            echo_json(True, data=data, message="run-due")
            return
        obj.skin.success(
            "processed={processed} succeeded={succeeded} failed={failed} dead={dead}".format(
                processed=(data or {}).get("processed"),
                succeeded=(data or {}).get("succeeded"),
                failed=(data or {}).get("failed"),
                dead=(data or {}).get("dead"),
            )
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="events")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_events(obj, as_json):
    """列出允许订阅的 webhook 事件名。"""
    json_mode = as_json or obj.json_mode
    if json_mode:
        echo_json(True, data={"events": list(EVENTS)})
        return
    obj.skin.table(
        ["Event"],
        [[ev] for ev in EVENTS],
    )


@webhook_cli.command(name="stats")
@click.option("--webhook-id", default=None, help="单钩子；省略则 WS 汇总")
@click.option(
    "--window",
    default="7d",
    show_default=True,
    type=click.Choice(["24h", "7d", "30d"], case_sensitive=False),
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_stats(obj, webhook_id, window, as_json):
    """投递指标（成功率 / 计数 / 可选延迟分位）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(
            client.get_webhook_stats(window=window, webhook_id=webhook_id)
        )
        if json_mode:
            echo_json(True, data=data)
            return
        totals = (data or {}).get("totals") or {}
        rate = totals.get("successRate")
        rate_s = "—" if rate is None else f"{float(rate) * 100:.1f}%"
        obj.skin.success(
            "window={w} successRate={r} success={s} dead={d} pending={p} attempts={a}".format(
                w=(data or {}).get("window"),
                r=rate_s,
                s=totals.get("success"),
                d=totals.get("dead"),
                p=totals.get("pending_retry"),
                a=totals.get("attempts"),
            )
        )
        lat = totals.get("latencyMs") or {}
        if lat:
            obj.skin.info(f"latency p50={lat.get('p50')}ms p95={lat.get('p95')}ms")
        by = (data or {}).get("byWebhook") or []
        if by and not webhook_id:
            obj.skin.table(
                ["Hook", "Rate", "Success", "Dead", "Pending", "Id"],
                [
                    [
                        (b.get("name") or b.get("url") or "")[:32],
                        (
                            "—"
                            if (b.get("totals") or {}).get("successRate") is None
                            else f"{float((b.get('totals') or {}).get('successRate')) * 100:.1f}%"
                        ),
                        (b.get("totals") or {}).get("success"),
                        (b.get("totals") or {}).get("dead"),
                        (b.get("totals") or {}).get("pending_retry"),
                        (b.get("webhookId") or "")[:8],
                    ]
                    for b in by
                ],
            )
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.group(name="dead-letter")
def webhook_dead_letter():
    """跨钩子死信箱。"""
    pass


@webhook_dead_letter.command(name="list")
@click.option("--webhook-id", default=None)
@click.option("--event", default=None, help="按 event_type 过滤")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_dead_letter_list(obj, webhook_id, event, as_json):
    """列出 status=dead 投递。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(
            client.list_webhook_dead_letter(webhook_id=webhook_id, event=event)
        )
        rows = (data or {}).get("rows") or []
        if json_mode:
            echo_json(True, data=data)
            return
        if not rows:
            obj.skin.info("无死信")
            return
        obj.skin.table(
            ["Hook", "Event", "HTTP", "Error", "Id"],
            [
                [
                    (r.get("webhookName") or r.get("webhookId") or "")[:20],
                    (r.get("eventType") or "")[:28],
                    r.get("statusCode") or "",
                    (r.get("error") or "")[:24],
                    (r.get("id") or "")[:8],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_dead_letter.command(name="retry")
@click.option("--id", "ids", multiple=True, help="delivery log id（可重复）")
@click.option("--ids", "ids_csv", default=None, help="逗号分隔 ids")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_dead_letter_retry(obj, ids, ids_csv, as_json):
    """批量重试死信（cap 50）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    collected: list[str] = []
    for i in ids:
        if i and i not in collected:
            collected.append(i)
    if ids_csv:
        for part in ids_csv.split(","):
            p = part.strip()
            if p and p not in collected:
                collected.append(p)
    if not collected:
        raise click.ClickException("请提供 --id 或 --ids")
    client = make_client(config)
    try:
        data = asyncio.run(client.bulk_retry_webhook_dead_letter(collected))
        if json_mode:
            echo_json(True, data=data, message="bulk-retry")
            return
        obj.skin.success(
            "succeeded={s} failed={f}".format(
                s=(data or {}).get("succeeded"),
                f=(data or {}).get("failed"),
            )
        )
        for r in (data or {}).get("results") or []:
            mark = "ok" if r.get("ok") else "FAIL"
            obj.skin.info(
                f"  [{mark}] {(r.get('deliveryLogId') or '')[:8]} {r.get('error') or ''}"
            )
    except APIError as e:
        handle_api_error(e, json_mode)

