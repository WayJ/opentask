"""Project management commands for OpenTask CLI."""
import asyncio
import click
from ..utils.api_client import OpenTaskClient, APIError
from ..utils.cli_output import echo_json, handle_api_error, require_workspace_id
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


@project_cli.group(name="lead")
def lead_cli():
    """E79: set or clear project lead (roster-only)."""
    pass


@project_cli.group(name="member")
def member_cli():
    """E79: add/remove/list project members (roster-only)."""
    pass


@project_cli.group(name="milestone")
def milestone_cli():
    """E81: project milestone list|create|show|update|delete."""
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
    json_mode = as_json or getattr(obj, "json_mode", False)

    try:
        project = asyncio.run(client.get_project(project_id)) or {}
        watchers = []
        watching_count = 0
        try:
            watchers = asyncio.run(client.list_project_watchers(project.get("id") or project_id))
            if isinstance(watchers, dict):
                watchers = watchers.get("data") or watchers.get("rows") or []
            watching_count = len(watchers) if isinstance(watchers, list) else 0
        except (APIError, TypeError, ValueError):
            watchers = []
            watching_count = 0

        if json_mode:
            import json
            output = dict(project) if isinstance(project, dict) else {"project": project}
            output["watchers"] = watchers if isinstance(watchers, list) else []
            output["watching_count"] = watching_count
            click.echo(json.dumps(output, indent=2, ensure_ascii=False, default=str))
            return

        skin.section("Project Details")

        skin.status_block({
            "ID": project.get("id", ""),
            "Name": project.get("name", ""),
            "Description": project.get("description", "") or "N/A",
            "Active": "Yes" if project.get("is_active") else "No",
            "Watching": str(watching_count),
            "Created": project.get("created_at", "")[:19] if project.get("created_at") else "N/A",
            "Updated": project.get("updated_at", "")[:19] if project.get("updated_at") else "N/A"
        })

    except APIError as e:
        if json_mode:
            handle_api_error(e, json_mode, "Failed to get project")
        else:
            skin.error(f"Failed to get project: {e.message}")


@project_cli.command(name="create")
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--description", "-d", default="", help="Project description")
@click.option("--template-id", default=None, help="E72: apply project template milestones")
@click.option("--starts-at", default=None, help="E72: ISO start for template offsets")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def create_project(obj: "Context", name: str, description: str, template_id: str | None, starts_at: str | None, as_json: bool):
    """Create a new project."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or getattr(obj, "json_mode", False)
    try:
        project = asyncio.run(
            client.create_project(
                name, description, template_id=template_id, starts_at=starts_at
            )
        )

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




@project_cli.command(name="watch")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def watch_project_cmd(obj: "Context", project_id: str, as_json: bool):
    """关注 Project（Inbox 收健康/更新）。E83."""
    config: Config = obj.config
    json_mode = as_json or getattr(obj, "json_mode", False)
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        data = asyncio.run(client.watch_project(project_id))
        if json_mode:
            echo_json(True, data=data, message="watching")
            return
        skin.success(f"已关注项目 {project_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@project_cli.command(name="unwatch")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def unwatch_project_cmd(obj: "Context", project_id: str, as_json: bool):
    """取消关注 Project。E83."""
    config: Config = obj.config
    json_mode = as_json or getattr(obj, "json_mode", False)
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        data = asyncio.run(client.unwatch_project(project_id))
        if json_mode:
            echo_json(True, data=data or {"id": project_id}, message="unwatched")
            return
        skin.success(f"已取消关注项目 {project_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@project_cli.command(name="watchers")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_project_watchers_cmd(obj: "Context", project_id: str, as_json: bool):
    """列出 Project 关注者。E83."""
    config: Config = obj.config
    json_mode = as_json or getattr(obj, "json_mode", False)
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        rows = asyncio.run(client.list_project_watchers(project_id))
        if isinstance(rows, dict):
            rows = rows.get("data") or rows.get("rows") or []
        if json_mode:
            echo_json(True, data={"rows": rows})
            return
        if not rows:
            skin.info("无关注者")
            return
        skin.table(
            ["User", "Username", "Since"],
            [
                [
                    str(r.get("user_id", ""))[:8],
                    r.get("username") or r.get("name") or "",
                    str(r.get("created_at") or "")[:19],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


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


@lead_cli.command(name="set")
@click.argument("project_id")
@click.argument("user_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_lead_set(obj: "Context", project_id: str, user_id: str, as_json: bool):
    """E79: Set project lead (upserts into members).

    Examples:
        opentask project lead set <project> <user>
        opentask project lead set <project> <user> --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        result = asyncio.run(client.update_project(project_id, lead_id=user_id))
        if json_mode:
            echo_json(True, data=result if isinstance(result, dict) else {"result": result})
            return
        lead = (result or {}).get("lead") if isinstance(result, dict) else None
        lead_id = (result or {}).get("lead_id") if isinstance(result, dict) else user_id
        label = (lead or {}).get("sso_name") or (lead or {}).get("name") or lead_id
        skin.success(f"[OK] Lead set: {label}")
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to set lead")


@lead_cli.command(name="clear")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_lead_clear(obj: "Context", project_id: str, as_json: bool):
    """E79: Clear project lead (keeps member row).

    Examples:
        opentask project lead clear <project>
        opentask project lead clear <project> --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        result = asyncio.run(client.update_project(project_id, lead_id=None))
        if json_mode:
            echo_json(True, data=result if isinstance(result, dict) else {"result": result})
            return
        skin.success("[OK] Lead cleared")
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to clear lead")


@member_cli.command(name="add")
@click.argument("project_id")
@click.argument("user_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_member_add(obj: "Context", project_id: str, user_id: str, as_json: bool):
    """E79: Add project roster member."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        result = asyncio.run(client.add_project_member(project_id, user_id))
        if json_mode:
            echo_json(True, data=result if isinstance(result, dict) else {"result": result})
            return
        skin.success(f"[OK] Member added: {user_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to add member")


@member_cli.command(name="remove")
@click.argument("project_id")
@click.argument("user_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_member_remove(obj: "Context", project_id: str, user_id: str, as_json: bool):
    """E79: Remove project roster member."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        result = asyncio.run(client.remove_project_member(project_id, user_id))
        if json_mode:
            echo_json(True, data=result if isinstance(result, dict) else {"ok": True})
            return
        skin.success(f"[OK] Member removed: {user_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to remove member")


@member_cli.command(name="list")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_member_list(obj: "Context", project_id: str, as_json: bool):
    """E79: List project roster members."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        result = asyncio.run(client.list_project_members(project_id))
        if isinstance(result, dict):
            rows = result.get("rows") or result.get("data") or result.get("members") or []
            if not isinstance(rows, list):
                rows = []
        elif isinstance(result, list):
            rows = result
        else:
            rows = []
        project = asyncio.run(client.get_project(project_id)) or {}
        if json_mode:
            echo_json(
                True,
                data={
                    "lead_id": project.get("lead_id"),
                    "lead": project.get("lead"),
                    "members": rows,
                    "member_count": project.get("member_count", len(rows)),
                },
            )
            return
        skin.section("Project members")
        lead = project.get("lead") or {}
        lead_id = project.get("lead_id")
        if lead_id:
            label = lead.get("sso_name") or lead.get("name") or lead_id
            skin.hint(f"lead: {label}")
        if not rows:
            skin.info("No members")
            return
        headers = ["ID", "Name"]
        table_rows = []
        for m in rows:
            table_rows.append([
                str(m.get("id", ""))[:8],
                m.get("sso_name") or m.get("name") or m.get("sso_account") or "",
            ])
        skin.table(headers, table_rows, max_col_width=40)
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to list members")


@milestone_cli.command(name="list")
@click.argument("project_id")
@click.option(
    "--status",
    type=click.Choice(["planned", "done"], case_sensitive=False),
    default=None,
    help="E81: filter planned|done",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_milestone_list(obj: "Context", project_id: str, status: str | None, as_json: bool):
    """E81: List project milestones."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        result = asyncio.run(client.list_project_milestones(project_id, status=status))
        if isinstance(result, dict):
            rows = result.get("rows") or result.get("data") or result.get("milestones") or []
            if not isinstance(rows, list):
                rows = []
        elif isinstance(result, list):
            rows = result
        else:
            rows = []
        if json_mode:
            echo_json(True, data={"rows": rows, "total": len(rows)})
            return
        if not rows:
            skin.info("No milestones")
            return
        headers = ["ID", "Name", "Status", "Issues", "Target"]
        table_rows = []
        for m in rows:
            table_rows.append([
                str(m.get("id", ""))[:8],
                m.get("name") or "",
                m.get("status") or "",
                str(m.get("issue_count", 0)),
                str(m.get("target_date") or "")[:10],
            ])
        skin.table(headers, table_rows, max_col_width=40)
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to list milestones")


@milestone_cli.command(name="create")
@click.argument("project_id")
@click.option("--name", required=True, help="Milestone name")
@click.option("--description", default=None, help="Description")
@click.option("--target-date", default=None, help="Target date YYYY-MM-DD")
@click.option(
    "--status",
    type=click.Choice(["planned", "done"], case_sensitive=False),
    default="planned",
    help="planned|done",
)
@click.option("--position", type=int, default=None, help="Sort position")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_milestone_create(
    obj: "Context",
    project_id: str,
    name: str,
    description: str | None,
    target_date: str | None,
    status: str,
    position: int | None,
    as_json: bool,
):
    """E81: Create a project milestone."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    kwargs = {"name": name, "status": status}
    if description is not None:
        kwargs["description"] = description
    if target_date is not None:
        kwargs["target_date"] = target_date
    if position is not None:
        kwargs["position"] = position
    try:
        result = asyncio.run(client.create_project_milestone(project_id, **kwargs))
        if json_mode:
            echo_json(True, data=result if isinstance(result, dict) else {"result": result})
            return
        skin.success(f"[OK] Milestone created: {(result or {}).get('name') or name}")
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to create milestone")


@milestone_cli.command(name="show")
@click.argument("project_id")
@click.argument("milestone_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_milestone_show(
    obj: "Context", project_id: str, milestone_id: str, as_json: bool
):
    """E81: Show a project milestone."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        result = asyncio.run(client.get_project_milestone(project_id, milestone_id))
        if json_mode:
            echo_json(True, data=result if isinstance(result, dict) else {"result": result})
            return
        skin.section("Milestone")
        skin.status_block({
            "ID": (result or {}).get("id", ""),
            "Name": (result or {}).get("name", ""),
            "Status": (result or {}).get("status", ""),
            "Issues": (result or {}).get("issue_count", 0),
            "Target": (result or {}).get("target_date") or "",
        })
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to show milestone")


@milestone_cli.command(name="update")
@click.argument("project_id")
@click.argument("milestone_id")
@click.option("--name", default=None, help="Milestone name")
@click.option("--description", default=None, help="Description")
@click.option("--target-date", default=None, help="Target date YYYY-MM-DD")
@click.option(
    "--status",
    type=click.Choice(["planned", "done"], case_sensitive=False),
    default=None,
    help="planned|done",
)
@click.option("--position", type=int, default=None, help="Sort position")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_milestone_update(
    obj: "Context",
    project_id: str,
    milestone_id: str,
    name: str | None,
    description: str | None,
    target_date: str | None,
    status: str | None,
    position: int | None,
    as_json: bool,
):
    """E81: Update a project milestone."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description
    if target_date is not None:
        kwargs["target_date"] = target_date
    if status is not None:
        kwargs["status"] = status
    if position is not None:
        kwargs["position"] = position
    try:
        result = asyncio.run(
            client.update_project_milestone(project_id, milestone_id, **kwargs)
        )
        if json_mode:
            echo_json(True, data=result if isinstance(result, dict) else {"result": result})
            return
        skin.success(f"[OK] Milestone updated: {(result or {}).get('name') or milestone_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to update milestone")


@milestone_cli.command(name="delete")
@click.argument("project_id")
@click.argument("milestone_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def project_milestone_delete(
    obj: "Context", project_id: str, milestone_id: str, as_json: bool
):
    """E81: Delete a project milestone (issues lose milestone via SET NULL)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        asyncio.run(client.delete_project_milestone(project_id, milestone_id))
        if json_mode:
            echo_json(True, data={"ok": True, "id": milestone_id})
            return
        skin.success(f"[OK] Milestone deleted: {milestone_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode, "Failed to delete milestone")
