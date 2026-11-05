"""Saved Views commands — list/show/use (E14) + create/update/delete/favorite/save-as (E92)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="view")
def view_cli():
    """Saved Views（list/show/use + create/update/delete/favorite/save-as）。"""
    pass


def _parse_json_option(raw: str | None, label: str):
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"JSON 无效 ({label}): {e}") from e


def _fav_shared_flags(favorite: bool | None, shared: bool | None) -> dict:
    out: dict = {}
    if favorite is not None:
        out["is_favorite"] = favorite
    if shared is not None:
        out["is_shared"] = shared
    return out


@view_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_saved_views())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = data if isinstance(data, list) else (data or {}).get("rows", [])
        if not rows:
            obj.skin.info("无 Saved View")
            return
        obj.skin.table(
            ["ID", "Name", "Favorite", "Shared"],
            [
                [
                    (r.get("id") or "")[:8],
                    r.get("name") or "",
                    str(r.get("isFavorite") if r.get("isFavorite") is not None else r.get("is_favorite") or ""),
                    str(r.get("isShared") if r.get("isShared") is not None else r.get("is_shared") or r.get("shared") or ""),
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@view_cli.command(name="show")
@click.argument("view_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_show(obj, view_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_saved_view(view_id))
        if json_mode:
            echo_json(True, data=data)
            return
        fav = data.get("isFavorite")
        if fav is None:
            fav = data.get("is_favorite")
        shared = data.get("isShared")
        if shared is None:
            shared = data.get("is_shared")
        obj.skin.status_block({
            "ID": data.get("id", ""),
            "Name": data.get("name", ""),
            "Favorite": fav if fav is not None else "",
            "Shared": shared if shared is not None else "",
            "Filters": str(data.get("filters") or data.get("filter") or "")[:120],
        })
    except APIError as e:
        handle_api_error(e, json_mode)


@view_cli.command(name="use")
@click.argument("view_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_use(obj, view_id, as_json):
    """打印视图 filter JSON，供 agent 后续拼 issue list 参数。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_saved_view(view_id))
        filters = data.get("filters") if isinstance(data, dict) else None
        if filters is None and isinstance(data, dict):
            filters = data.get("filter") or data
        payload = {"viewId": view_id, "name": (data or {}).get("name"), "filters": filters}
        # always JSON-ish for agent consumption
        echo_json(True, data=payload, message="use this filter with issue list")
    except APIError as e:
        handle_api_error(e, json_mode)


@view_cli.command(name="create")
@click.option("--name", required=True, help="View name")
@click.option("--filter", "filter_json", default=None, help="Filter JSON object")
@click.option("--sort", "sort_json", default=None, help="Sort JSON object")
@click.option("--display", "display_json", default=None, help="Display JSON object")
@click.option("--favorite/--no-favorite", "favorite", default=None)
@click.option("--shared/--no-shared", "shared", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_create(obj, name, filter_json, sort_json, display_json, favorite, shared, as_json):
    """Create a Saved View (POST /api/saved-views)."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    filt = _parse_json_option(filter_json, "filter")
    sort = _parse_json_option(sort_json, "sort")
    display = _parse_json_option(display_json, "display")
    client = make_client(config)
    try:
        data = asyncio.run(
            client.create_saved_view(
                name,
                filter=filt,
                sort=sort,
                display=display,
                is_favorite=favorite,
                is_shared=shared,
            )
        )
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"视图已创建：{(data or {}).get('name') or name}")
        obj.skin.status_block({
            "ID": (data or {}).get("id", ""),
            "Name": (data or {}).get("name", name),
            "Favorite": (data or {}).get("isFavorite", favorite),
            "Shared": (data or {}).get("isShared", shared),
        })
    except APIError as e:
        handle_api_error(e, json_mode)


@view_cli.command(name="update")
@click.argument("view_id")
@click.option("--name", default=None)
@click.option("--filter", "filter_json", default=None, help="Filter JSON object")
@click.option("--sort", "sort_json", default=None, help="Sort JSON object")
@click.option("--display", "display_json", default=None, help="Display JSON object")
@click.option("--favorite/--no-favorite", "favorite", default=None)
@click.option("--shared/--no-shared", "shared", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_update(obj, view_id, name, filter_json, sort_json, display_json, favorite, shared, as_json):
    """Update a Saved View (PATCH /api/saved-views/{id})."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    kwargs = _fav_shared_flags(favorite, shared)
    if name is not None:
        kwargs["name"] = name
    filt = _parse_json_option(filter_json, "filter")
    if filt is not None:
        kwargs["filter"] = filt
    sort = _parse_json_option(sort_json, "sort")
    if sort is not None:
        kwargs["sort"] = sort
    display = _parse_json_option(display_json, "display")
    if display is not None:
        kwargs["display"] = display
    if not kwargs:
        raise click.ClickException("请至少提供一个更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_saved_view(view_id, **kwargs))
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success(f"视图已更新：{(data or {}).get('name') or view_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@view_cli.command(name="delete")
@click.argument("view_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_delete(obj, view_id, as_json):
    """Delete a Saved View (DELETE /api/saved-views/{id})."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_saved_view(view_id))
        if json_mode:
            echo_json(True, data=data, message="deleted")
            return
        obj.skin.success(f"视图已删除：{view_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@view_cli.command(name="favorite")
@click.argument("view_id")
@click.option("--on", "fav_on", is_flag=True, default=False, help="Mark as favorite")
@click.option("--off", "fav_off", is_flag=True, default=False, help="Unmark favorite")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_favorite(obj, view_id, fav_on, fav_off, as_json):
    """Set favorite on a personal Saved View (POST .../favorite). Shared views → 403."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if fav_on == fav_off:
        raise click.ClickException("请指定 --on 或 --off（二选一）")
    is_favorite = bool(fav_on)
    client = make_client(config)
    try:
        data = asyncio.run(client.set_saved_view_favorite(view_id, is_favorite))
        if json_mode:
            echo_json(True, data=data, message="favorite updated")
            return
        obj.skin.success("已收藏" if is_favorite else "已取消收藏")
    except APIError as e:
        handle_api_error(e, json_mode)


@view_cli.command(name="save-as")
@click.argument("view_id")
@click.option("--name", default=None, help="Optional name for the personal copy")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_save_as(obj, view_id, name, as_json):
    """Save a view as a personal copy (POST .../save-as)."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.save_as_saved_view(view_id, name=name))
        if json_mode:
            echo_json(True, data=data, message="saved as")
            return
        obj.skin.success(f"已另存为个人视图：{(data or {}).get('name') or name or view_id}")
    except APIError as e:
        handle_api_error(e, json_mode)
