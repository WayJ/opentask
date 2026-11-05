"""Access Token management commands (E96).

Creates / lists / revokes personal API keys via /api/access-tokens.
Create returns the raw token once; optional --save writes local config.access_token.
Does not change `config set-access-token` semantics.
"""
from __future__ import annotations

import asyncio

import click

from ..utils.api_client import OpenTaskClient, APIError
from ..utils.cli_output import echo_json, handle_api_error
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


@click.group(name="access-token")
def access_token_cli():
    """个人 Access Token（API Key）list / create / revoke。

    与 `config set-access-token` 并存：本命令负责签发/枚举/吊销；
    config 命令仅粘贴既有明文到本地配置。
    """
    pass


def _rows_from_list_result(result) -> list:
    if isinstance(result, dict):
        rows = result.get("rows") or result.get("data") or result.get("tokens") or []
        if not isinstance(rows, list):
            rows = []
        return rows
    if isinstance(result, list):
        return result
    return []


@access_token_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def access_token_list(obj, as_json: bool):
    """列出当前用户的 Access Token 元数据（不含原文）。"""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        result = asyncio.run(client.list_access_tokens())
        rows = _rows_from_list_result(result)
        if json_mode:
            echo_json(True, data={"rows": rows, "total": len(rows)})
            return
        if not rows:
            skin.info("No access tokens")
            return
        headers = ["ID", "Name", "Prefix", "Expires", "Last Used"]
        table_rows = []
        for r in rows:
            table_rows.append(
                [
                    str(r.get("id", "")),
                    r.get("name") or "",
                    r.get("token_prefix") or "",
                    str(r.get("expires_at") or ""),
                    str(r.get("last_used_at") or ""),
                ]
            )
        skin.table(headers, table_rows, max_col_width=40)
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to list access tokens")


@access_token_cli.command(name="create")
@click.option("--name", required=True, help="Token display name")
@click.option("--description", default=None, help="Optional description")
@click.option(
    "--save",
    "do_save",
    is_flag=True,
    default=False,
    help="Write the one-time token into local config.access_token (opt-in)",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def access_token_create(
    obj,
    name: str,
    description: str | None,
    do_save: bool,
    as_json: bool,
):
    """创建 Access Token；原文仅此一次可见。默认不写本地 config（需 --save）。"""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        result = asyncio.run(
            client.create_access_token(name, description=description)
        )
        data = result if isinstance(result, dict) else {"result": result}
        raw = data.get("token") if isinstance(data, dict) else None

        if do_save and raw:
            # Reuse existing config setter (same as set-access-token)
            config.access_token = raw

        if json_mode:
            echo_json(True, data=data, message="created" + ("+saved" if do_save and raw else ""))
            return

        skin.success(f"[OK] Access token created: {data.get('name') or name}")
        if raw:
            skin.warning("Token（仅此一次可见 / shown only once）:")
            click.echo(raw)
            if do_save:
                skin.success("已写入本地 config.access_token（--save）")
            else:
                skin.info(
                    "未写入本地配置。需要时可：opentask access-token create … --save "
                    "或 opentask config set-access-token <token>"
                )
        else:
            skin.warning("响应未含 token 字段；请检查 API 返回")
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to create access token")


@access_token_cli.command(name="revoke")
@click.argument("token_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def access_token_revoke(obj, token_id: str, as_json: bool):
    """吊销（删除）指定 Access Token。"""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        asyncio.run(client.delete_access_token(token_id))
        if json_mode:
            echo_json(True, data={"ok": True, "id": token_id})
            return
        skin.success(f"[OK] Access token revoked: {token_id}")
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to revoke access token")


access_token_cli.add_command(access_token_revoke, name="rm")
