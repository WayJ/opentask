"""Insights commands (E24)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="insights")
def insights_cli():
    """Workspace Insights（只读效能）。"""
    pass


@insights_cli.command(name="summary")
@click.option("--cycle", "cycle_id", default=None, help="Cycle ID；默认 active")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def insights_summary(obj, cycle_id, as_json):
    """拉取 Insights summary。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.insights_summary(cycle_id=cycle_id))
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
    except APIError as e:
        handle_api_error(e, json_mode)
