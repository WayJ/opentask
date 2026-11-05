"""Shared JSON / error helpers for CLI commands (E14)."""
from __future__ import annotations

import json
import sys
from typing import Any

import click

from .api_client import APIError, OpenTaskClient
from .config import Config


def json_response(
    success: bool,
    data: Any = None,
    error: str | None = None,
    message: str | None = None,
    status_code: int | None = None,
) -> str:
    payload: dict[str, Any] = {
        "success": success,
        "data": data,
        "error": error,
        "message": message,
    }
    if status_code is not None:
        payload["status_code"] = status_code
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def echo_json(success: bool, data: Any = None, error: str | None = None, message: str | None = None, status_code: int | None = None):
    click.echo(json_response(success, data=data, error=error, message=message, status_code=status_code))


def make_client(config: Config) -> OpenTaskClient:
    return OpenTaskClient(base_url=config.api_url, token=config.token, config=config)


def require_workspace_id(config: Config, json_mode: bool = False) -> str | None:
    """Return active workspace id or print error and return None."""
    ws = config.active_workspace_id
    if ws:
        return ws
    msg = "未选择工作区。请先执行: opentask workspace use <id>"
    if json_mode:
        echo_json(False, error=msg, message=msg, status_code=400)
    else:
        click.echo(f"Error: {msg}", err=True)
    return None


def handle_api_error(e: APIError, json_mode: bool, human_prefix: str = "Request failed") -> None:
    if json_mode:
        click.echo(e.to_json())
    else:
        click.echo(f"Error: {human_prefix}: {e.message}", err=True)
    sys.exit(1)


def unwrap_rows(data: Any) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("rows"), list):
            return data["rows"]
        if isinstance(data.get("data"), list):
            return data["data"]
    return []
