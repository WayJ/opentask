"""Insights commands (E24 + E55 + E59 + E61 shared reports)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="insights")
def insights_cli():
    """Workspace Insights（效能 / 报表 / digest）。"""
    pass


def _parse_label_ids(label_ids: str | None) -> list[int] | None:
    if not label_ids:
        return None
    out: list[int] = []
    for part in str(label_ids).split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out or None


@insights_cli.command(name="summary")
@click.option("--cycle", "cycle_id", default=None, help="Cycle ID；默认 active")
@click.option("--project-id", "project_id", default=None, help="Project 切片")
@click.option("--label-id", "label_id", default=None, type=int, help="Label(Tag) 单切片")
@click.option("--label-ids", "label_ids", default=None, help="多 Label OR，逗号分隔")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def insights_summary(obj, cycle_id, project_id, label_id, label_ids, as_json):
    """拉取 Insights summary。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if label_id is not None and label_ids:
        raise click.ClickException("不可同时传 --label-id 与 --label-ids")
    client = make_client(config)
    try:
        data = asyncio.run(
            client.insights_summary(
                cycle_id=cycle_id,
                project_id=project_id,
                label_id=label_id,
                label_ids=_parse_label_ids(label_ids),
            )
        )
        if json_mode:
            echo_json(True, data=data)
            return
        if not isinstance(data, dict):
            obj.skin.info(str(data))
            return
        status = data.get("statusCounts") or {}
        priority = data.get("priorityCounts") or {}
        snap = data.get("cycleSnapshot")
        status_s = ", ".join(f"{k}={v}" for k, v in status.items()) or "(empty)"
        priority_s = ", ".join(f"{k}={v}" for k, v in priority.items()) or "(empty)"
        obj.skin.info("Status: " + status_s)
        obj.skin.info("Priority: " + priority_s)
        if snap:
            obj.skin.info(
                f"Cycle {snap.get('cycleName')} · issues={snap.get('issueCount')} "
                f"completed={snap.get('completedCount')} points={snap.get('estimatePointsSum')}"
            )
        else:
            obj.skin.info("Cycle: (none)")
        trend = data.get("createdVsCompleted") or []
        created = sum(int(d.get("created") or 0) for d in trend)
        completed = sum(int(d.get("completed") or 0) for d in trend)
        obj.skin.info(f"Last 14d created={created} completed={completed}")
        vel = data.get("estimateVelocity") or {}
        buckets = vel.get("buckets") or []
        pts = sum(float(b.get("completedPoints") or 0) for b in buckets)
        obj.skin.info(f"Last {vel.get('windowDays', 14)}d completed points={pts}")
    except APIError as e:
        handle_api_error(e, json_mode)


@insights_cli.command(name="export")
@click.option("--cycle", "cycle_id", default=None, help="Cycle ID；默认 active")
@click.option("--project-id", "project_id", default=None, help="Project 切片")
@click.option("--label-id", "label_id", default=None, type=int, help="Label(Tag) 单切片")
@click.option("--label-ids", "label_ids", default=None, help="多 Label OR，逗号分隔")
@click.option("-o", "--output", "out_path", default=None, help="写入文件；默认 stdout")
@click.pass_obj
def insights_export(obj, cycle_id, project_id, label_id, label_ids, out_path):
    """导出 Insights CSV（默认 stdout）。"""
    config: Config = obj.config
    json_mode = obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if label_id is not None and label_ids:
        raise click.ClickException("不可同时传 --label-id 与 --label-ids")
    client = make_client(config)
    try:
        content = asyncio.run(
            client.insights_export(
                cycle_id=cycle_id,
                project_id=project_id,
                label_id=label_id,
                label_ids=_parse_label_ids(label_ids),
            )
        )
        text = content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else str(content)
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            obj.skin.success(f"Exported to {out_path}")
        else:
            click.echo(text, nl=False if text.endswith("\n") else True)
    except APIError as e:
        handle_api_error(e, json_mode)


@insights_cli.group(name="reports")
def insights_reports_cli():
    """Insights 报表（personal + workspace shared）。"""
    pass


@insights_reports_cli.command(name="list")
@click.option("--mine", "scope", flag_value="mine", help="仅本人报表")
@click.option("--shared", "scope", flag_value="shared", help="仅他人共享")
@click.option("--all", "scope", flag_value="all", default=True, help="本人∪共享（默认）")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def insights_reports_list(obj, scope, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.insights_reports_list())
        rows = list((data or {}).get("rows") or [])
        # Client-side scope filter (API returns mine∪shared)
        if scope == "mine":
            rows = [r for r in rows if r.get("canEdit") is True]
        elif scope == "shared":
            rows = [
                r
                for r in rows
                if (r.get("visibility") or "personal") == "workspace"
                and r.get("canEdit") is not True
            ]
        data = {**(data or {}), "rows": rows}
        if json_mode:
            echo_json(True, data=data)
            return
        if not rows:
            obj.skin.info("(no reports)")
            return
        for r in rows:
            flag = " ★" if r.get("isDefault") else ""
            vis = r.get("visibility") or "personal"
            edit = "rw" if r.get("canEdit") else "ro"
            obj.skin.info(f"{r.get('id')}  {r.get('name')}{flag}  [{vis}/{edit}]")
    except APIError as e:
        handle_api_error(e, json_mode)


@insights_reports_cli.command(name="create")
@click.option("--name", required=True, help="报表名称")
@click.option("--filters-json", "filters_json", default="{}", help="filters JSON")
@click.option("--default", "is_default", is_flag=True, help="设为 digest 默认")
@click.option(
    "--visibility",
    type=click.Choice(["personal", "workspace"], case_sensitive=False),
    default="personal",
    show_default=True,
    help="personal 或 workspace",
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def insights_reports_create(obj, name, filters_json, is_default, visibility, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    try:
        filters = json.loads(filters_json or "{}")
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"filters-json 非法: {exc}") from exc
    client = make_client(config)
    try:
        data = asyncio.run(
            client.insights_reports_create(
                name=name,
                filters=filters,
                is_default=is_default,
                visibility=visibility,
            )
        )
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success(
            f"Created {data.get('id')} {data.get('name')} [{data.get('visibility')}]"
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@insights_reports_cli.command(name="set-visibility")
@click.argument("report_id")
@click.argument("visibility", type=click.Choice(["personal", "workspace"], case_sensitive=False))
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def insights_reports_set_visibility(obj, report_id, visibility, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(
            client.insights_reports_set_visibility(report_id, visibility)
        )
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success(f"{report_id} → {data.get('visibility')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@insights_reports_cli.command(name="fork")
@click.argument("report_id")
@click.option("--name", default=None, help="副本名称")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def insights_reports_fork(obj, report_id, name, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.insights_reports_fork(report_id, name=name))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success(f"Forked → {data.get('id')} {data.get('name')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@insights_reports_cli.command(name="delete")
@click.argument("report_id")
@click.option("--yes", is_flag=True, help="跳过确认")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def insights_reports_delete(obj, report_id, yes, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if not yes and not json_mode:
        click.confirm(f"Delete report {report_id}?", abort=True)
    client = make_client(config)
    try:
        data = asyncio.run(client.insights_reports_delete(report_id))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success(f"Deleted {report_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@insights_cli.command(name="run-digest")
@click.option("--yes", is_flag=True, help="跳过确认")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def insights_run_digest(obj, yes, as_json):
    """触发 Insights digest tick（writer+）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if not yes and not json_mode:
        click.confirm("Run insights digest for this workspace?", abort=True)
    client = make_client(config)
    try:
        data = asyncio.run(client.insights_run_digest())
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success(
            f"created={data.get('created')} skipped={data.get('skipped')} "
            f"bucket={data.get('bucketDate')}"
        )
    except APIError as e:
        handle_api_error(e, json_mode)
