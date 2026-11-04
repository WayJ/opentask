"""Project management commands for OpenTask CLI."""
import asyncio
import click
from ..utils.api_client import OpenTaskClient, APIError
from ..utils.cli_output import echo_json, handle_api_error
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


def format_project(project: dict) -> dict:
    """Format project for display.

    Args:
        project: Project data dictionary

    Returns:
        Formatted project dictionary
    """
    return {
        "id": project.get("id", "")[:8],
        "name": project.get("name", ""),
        "description": project.get("description", "") or "",
        "is_active": project.get("is_active", True),
        "created_at": project.get("created_at", "")[:10] if project.get("created_at") else ""
    }


def format_active_status(is_active: bool) -> str:
    """Format active status for Windows compatibility."""
    return "[OK]" if is_active else "[X]"


@click.group(name="project")
def project_cli():
    """Project management commands."""
    pass


@project_cli.command(name="list")
@click.option("--active-only", is_flag=True, default=True, help="Show only active projects")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_projects(obj: "Context", active_only: bool, as_json: bool):
    """List all projects."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    try:
        result = asyncio.run(client.list_projects(active_only=active_only))
        if isinstance(result, dict):
            projects = result.get("rows") or result.get("data") or []
        elif isinstance(result, list):
            projects = result
        else:
            projects = []

        if json_mode:
            import json
            click.echo(json.dumps({"rows": projects, "total": len(projects)}, indent=2, ensure_ascii=False, default=str))
            return

        if not projects:
            skin.info("No projects found")
            skin.hint("Ensure workspace is selected: opentask workspace use <id>")
            return

        skin.section("Projects")
        if config.active_workspace_name:
            skin.hint(f"workspace: {config.active_workspace_name}")

        headers = ["ID", "Name", "Description", "Active", "Created"]
        rows = []
        for p in projects:
            fp = format_project(p)
            rows.append([
                fp["id"],
                fp["name"],
                fp["description"][:30],
                format_active_status(fp["is_active"]),
                fp["created_at"]
            ])

        skin.table(headers, rows, max_col_width=30)

    except APIError as e:
        if json_mode:
            click.echo(e.to_json())
        else:
            skin.error(f"Failed to list projects: {e.message}")


@project_cli.command(name="show")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def show_project(obj: "Context", project_id: str, as_json: bool):
    """Show project details."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    try:
        project = asyncio.run(client.get_project(project_id))

        if as_json:
            import json
            click.echo(json.dumps(project, indent=2, ensure_ascii=False))
            return

        skin.section("Project Details")

        skin.status_block({
            "ID": project.get("id", ""),
            "Name": project.get("name", ""),
            "Description": project.get("description", "") or "N/A",
            "Active": "Yes" if project.get("is_active") else "No",
            "Created": project.get("created_at", "")[:19] if project.get("created_at") else "N/A",
            "Updated": project.get("updated_at", "")[:19] if project.get("updated_at") else "N/A"
        })

    except APIError as e:
        skin.error(f"Failed to get project: {e.message}")


@project_cli.command(name="create")
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--description", "-d", default="", help="Project description")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def create_project(obj: "Context", name: str, description: str, as_json: bool):
    """Create a new project."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or getattr(obj, "json_mode", False)
    try:
        project = asyncio.run(client.create_project(name, description))

        if json_mode:
            echo_json(True, data=project, message="project created")
            return

        skin.success(f"Project created: {name}")

        skin.section("Project Details")
        skin.status_block({
            "ID": project.get("id", ""),
            "Name": project.get("name", ""),
            "Description": project.get("description", "") or "N/A"
        })

    except APIError as e:
        skin.error(f"Failed to create project: {e.message}")


@project_cli.command(name="update")
@click.argument("project_id")
@click.option("--name", "-n", help="New project name")
@click.option("--description", "-d", help="New project description")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def update_project(obj: "Context", project_id: str, name: str | None, description: str | None, as_json: bool):
    """Update project."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    if not name and not description:
        skin.error("At least one of --name or --description must be provided")
        return

    try:
        project = asyncio.run(client.update_project(project_id, name=name, description=description))

        if as_json:
            import json
            click.echo(json.dumps(project, indent=2, ensure_ascii=False))
            return

        skin.success(f"Project updated: {project.get('name', project_id)}")

        skin.section("Updated Details")
        skin.status_block({
            "ID": project.get("id", ""),
            "Name": project.get("name", ""),
            "Description": project.get("description", "") or "N/A"
        })

    except APIError as e:
        skin.error(f"Failed to update project: {e.message}")


@project_cli.command(name="use")
@click.argument("project_id")
@click.pass_obj
def use_project(obj: "Context", project_id: str):
    """Set active project context."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    try:
        project = asyncio.run(client.get_project(project_id))

        config.active_project_id = project.get("id", "")
        config.active_project_name = project.get("name", "")

        skin.success(f"Active project set: {project.get('name', project_id)}")

    except APIError as e:
        skin.error(f"Failed to set project: {e.message}")


@project_cli.command(name="current")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def current_project(obj: "Context", as_json: bool):
    """Show current active project."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin

    project_id = config.active_project_id
    project_name = config.active_project_name

    if as_json:
        import json
        data = {
            "project_id": project_id,
            "project_name": project_name
        }
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if project_id:
        skin.section("Active Project")
        skin.status_block({
            "ID": project_id[:8] if project_id else "",
            "Name": project_name or ""
        })
    else:
        skin.info("No active project set")
        skin.hint("Use 'project use <id>' to set active project")


@project_cli.command(name="delete")
@click.argument("project_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def delete_project(obj: "Context", project_id: str, force: bool, as_json: bool):
    """Delete a project (SECURITY: Not allowed via CLI).

    For security reasons, deletion operations are not allowed through CLI.
    This protects against accidental deletions by AI assistants.

    Examples:
        project delete PROJECT-ID
        project delete PROJ-1
        project delete PROJECT-ID --force
        project delete PROJECT-ID --json
    """
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # 构建错误信息
    error_lines = [
        "❌ ERROR: Cannot delete project via CLI",
        "",
        "For security reasons, deletion operations are not allowed through CLI.",
        "",
        "Please use the Web UI to delete this project:",
        f"  1. Open: {obj.config.api_url.rstrip('/')}/projects/{project_id}",
        "  2. Click the delete button",
        "  3. Confirm the deletion",
        "",
        "This protects against accidental deletions by AI assistants.",
    ]

    for line in error_lines:
        skin.error(line)

    # 如果是 JSON 模式，返回结构化错误
    if json_mode:
        error_data = {
            "success": False,
            "error": "CLI_DELETE_NOT_ALLOWED",
            "message": "Cannot delete project via CLI for security reasons",
            "web_ui_url": f"{obj.config.api_url.rstrip('/')}/projects/{project_id}",
            "reason": "AI assistant protection"
        }
        click.echo(json.dumps(error_data, indent=2, ensure_ascii=False))

    # 返回错误码
    raise SystemExit(1)
