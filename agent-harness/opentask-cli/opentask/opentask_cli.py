"""OpenTask CLI - Main entry point.

A production-ready CLI for OpenTask platform with both interactive REPL
and one-shot command modes, plus JSON output for AI agents.
"""
import sys
import click
import asyncio
from typing import Optional
import os

# 确保 Windows 控制台使用 UTF-8 编码
# 但不在 pytest 环境中执行，避免与 pytest 的输出捕获冲突
_is_pytest = (
    'PYTEST_RUNNING' in os.environ or
    'PYTEST_CURRENT_TEST' in os.environ or
    '_pytest_session' in dir(sys.modules) or
    hasattr(sys, '_pytest')
)
if sys.platform == "win32" and not _is_pytest:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from .utils.api_client import OpenTaskClient, APIError
from .utils.config import Config
from .utils.repl_skin import ReplSkin
from .core.project import project_cli
from .core.project_template import project_template_cli
from .core.issue_template import issue_template_cli
from .core.issue import issue_cli
from .core.requirement import requirement_cli
from .core.update import update_cli
from .core.task import task_cli
from .core.workspace import workspace_cli
from .core.cycle import cycle_cli
from .core.label import label_cli
from .core.triage import triage_cli
from .core.inbox import inbox_cli
from .core.favorite import favorite_cli
from .core.view import view_cli
from .core.member import member_cli, invite_cli
from .core.initiative import initiative_cli
from .core.customer import customer_cli
from .core.insights import insights_cli
from .core.activity import activity_cli
from .core.custom_field import custom_field_cli
from .core.automation import automation_cli
from .core.webhook import webhook_cli
from .core.form import form_cli
from .core.recurrence import recurrence_cli
from .core.notif import notif_cli
from .core.sla import sla_cli
from .core.request import request_cli
from .core.doc import doc_cli
from .core.search import search_cli
from .core.display_prefs import display_prefs_cli
from .core.access_token import access_token_cli


# Global version
VERSION = "1.81.0"

# Context object passed to commands
class Context:
    """CLI context object."""

    def __init__(self, config: Config, skin: ReplSkin, json_mode: bool = False):
        self.config = config
        self.skin = skin
        self.json_mode = json_mode


# ============================================================================
# Main CLI Group
# ============================================================================

@click.group(invoke_without_command=True)
@click.option("--api-url", "-u", help="API base URL")
@click.option("--token", "-t", help="Authentication token")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def cli(ctx, api_url: Optional[str], token: Optional[str], as_json: bool, version: bool):
    """OpenTask CLI — Workspace + Issue 主轴（AI Agent / 人类）。

    \b
    Examples:
        opentask login
        opentask workspace list
        opentask workspace use <workspace-id>
        opentask project list
        opentask issue create -t "Fix bug"
        opentask issue show KEY-1
        opentask cycle list
        opentask label list
        opentask triage list

        # JSON for agents
        opentask --json issue list --status open
    """
    if version:
        click.echo(f"opentask v{VERSION}")
        sys.exit(0)

    # Initialize config
    config = Config()

    # Override with command-line options
    if api_url:
        config.api_url = api_url
    if token:
        config.token = token

    # Initialize skin
    skin = ReplSkin("opentask", version=VERSION)

    # Create context
    ctx.obj = Context(config=config, skin=skin, json_mode=as_json)

    # If no subcommand, enter REPL
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ============================================================================
# Configuration Commands
# ============================================================================

@cli.group(name="config")
def config_cli():
    """Configuration management."""
    pass


@config_cli.command(name="show")
@click.pass_obj
def config_show(obj: Context):
    """Show current configuration."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin

    skin.section("Configuration")
    skin.status_block({
        "API URL": config.api_url,
        "Token": f"{config.token[:20]}..." if config.token else "Not set",
        "Access Token": f"{config.access_token[:10]}..." if config.access_token else "Not set",
        "Active Workspace": (
            f"{config.active_workspace_name} ({config.active_workspace_id})"
            if config.active_workspace_id else "None"
        ),
        "Active Project": config.active_project_name or "None",
    })


@config_cli.command(name="set-api")
@click.argument("url")
@click.pass_obj
def config_set_api(obj: Context, url: str):
    """Set API base URL."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin

    config.api_url = url
    skin.success(f"API URL set: {url}")


@config_cli.command(name="set-token")
@click.argument("token")
@click.pass_obj
def config_set_token(obj: Context, token: str):
    """Set authentication token."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin

    config.token = token
    skin.success("Token set")


@config_cli.command(name="set-access-token")
@click.argument("token")
@click.pass_obj
def config_set_access_token(obj: Context, token: str):
    """Set access token for authentication.

    Access token takes priority over JWT token.
    Get your access token from the OpenTask web UI (Profile > Access Tokens).
    """
    config: Config = obj.config
    skin: ReplSkin = obj.skin

    if not token.startswith("vk_"):
        skin.warning("Warning: Access token should start with 'vk_'. Are you sure this is correct?")
    config.access_token = token
    skin.success("Access token set (takes priority over JWT token)")


# ============================================================================
# Authentication Commands (Top-Level)
# ============================================================================

@cli.command(name="login")
@click.option("--username", "-U", prompt=True, help="Username")
@click.option("--password", "-P", prompt=True, hide_input=True, help="Password")
@click.pass_obj
def login(obj: Context, username: str, password: str):
    """Login and store credentials (local auth with plaintext password).

    Credentials (username, plaintext password) are saved to keyring/config
    for automatic relogin when token expires.

    Example:
        opentask login
        opentask login -U username -P password
    """
    config: Config = obj.config
    skin: ReplSkin = obj.skin

    async def do_login():
        try:
            # 密码以明文提交（Phase 2 后端本地 bcrypt 校验）
            # 传递 config 给 API client，自动保存账号密码与 token
            client = OpenTaskClient(base_url=config.api_url, config=config)
            result = await client.login(username, password)
            token = result.get("token") or result.get("access_token")

            if token:
                # token 已经在 login 方法中自动保存到 config
                skin.success(f"Logged in as {username}")
                skin.hint("Credentials saved for automatic relogin")
            else:
                # ✅ Bug修复: 登录失败时清空token
                config.token = None
                skin.error("Login response did not contain token")

        except APIError as e:
            # ✅ Bug修复: 异常时也要清空token，避免密码被错误保存
            config.token = None
            skin.error(f"Login failed: {e.message}")

    asyncio.run(do_login())


@cli.command(name="logout")
@click.pass_obj
def logout(obj: Context):
    """Logout and clear token.

    Example:
        opentask logout
    """
    config: Config = obj.config
    skin: ReplSkin = obj.skin

    config.clear_auth()
    skin.success("Logged out")


# ============================================================================
# Auth Commands
# ============================================================================

@cli.group(name="auth")
def auth_cli():
    """Authentication commands."""
    pass


@auth_cli.command(name="me")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def auth_me(obj: Context, as_json: bool):
    """Get current user info."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin

    if not config.token:
        skin.error("Not authenticated. Use 'opentask login' first.")
        return

    async def get_user():
        client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
        try:
            user = await client.get_me()

            if as_json:
                import json
                click.echo(json.dumps(user, indent=2, ensure_ascii=False))
                return

            skin.section("Current User")

            # Try multiple fields for display
            display_name = (
                user.get("sso_name") or
                user.get("name") or
                user.get("username") or
                user.get("sso_account") or
                "Unknown"
            )

            skin.status_block({
                "ID": user.get("id", ""),
                "Name": display_name,
                "Account": user.get("sso_account", "N/A"),
                "Role": user.get("role", "N/A"),
                "Status": "Active" if user.get("status") == 1 else "Inactive"
            })

        except APIError as e:
            skin.error(f"Failed to get user info: {e.message}")

    asyncio.run(get_user())


# ============================================================================
# REPL Mode
# ============================================================================

@cli.command(name="repl")
@click.pass_context
def repl(ctx):
    """Enter interactive REPL mode."""
    config: Config = ctx.obj.config
    skin: ReplSkin = ctx.obj.skin

    skin.print_banner()

    # Create prompt session
    pt_session = skin.create_prompt_session()

    # Command mapping
    commands = {
        "help": "Show this help message",
        "quit": "Exit REPL",
        "exit": "Exit REPL",
        "project list": "List all projects",
        "project use <id>": "Set active project",
        "project current": "Show active project",
        "issue list": "List issues",
        "issue export [--out FILE]": "E28 export CSV",
        "issue import FILE": "E28 import CSV",
        "issue show <id>": "Show issue details",
        "issue create -t TITLE": "Create new issue",
        "config show": "Show configuration",
    }

    skin.help(commands)

    while True:
        try:
            # Build prompt
            project_name = config.active_project_name or ""
            prompt_text = skin.prompt(project_name=project_name)

            # Get input
            if pt_session:
                line = pt_session.prompt(skin.prompt_tokens(project_name=project_name))
            else:
                line = input(prompt_text)

            line = line.strip()

            if not line:
                continue

            # Parse command
            parts = line.split()
            cmd = parts[0].lower()

            if cmd in ["quit", "exit"]:
                skin.print_goodbye()
                break

            if cmd == "help":
                skin.help(commands)
                continue

            # Execute CLI command
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "opentask.opentask_cli"] + parts,
                capture_output=False,
                text=True
            )

        except KeyboardInterrupt:
            print()
            skin.hint("Type 'quit' or 'exit' to quit")
        except EOFError:
            skin.print_goodbye()
            break


# ============================================================================
# Register Command Groups
# ============================================================================

cli.add_command(workspace_cli)
cli.add_command(project_cli)
cli.add_command(project_template_cli)
cli.add_command(issue_template_cli)
cli.add_command(issue_cli)
cli.add_command(cycle_cli)
cli.add_command(label_cli)
cli.add_command(triage_cli)
cli.add_command(inbox_cli)
cli.add_command(favorite_cli)
cli.add_command(view_cli)
cli.add_command(member_cli)
cli.add_command(invite_cli)
cli.add_command(initiative_cli)
cli.add_command(customer_cli)
cli.add_command(insights_cli)
cli.add_command(activity_cli)
cli.add_command(custom_field_cli)
cli.add_command(automation_cli)
cli.add_command(webhook_cli)
cli.add_command(form_cli)
cli.add_command(recurrence_cli)
cli.add_command(notif_cli)
cli.add_command(sla_cli)
cli.add_command(request_cli)
cli.add_command(doc_cli)
cli.add_command(search_cli)
cli.add_command(display_prefs_cli)
cli.add_command(access_token_cli)
cli.add_command(requirement_cli)
cli.add_command(task_cli)
cli.add_command(config_cli)
cli.add_command(auth_cli)
cli.add_command(update_cli)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    cli()
