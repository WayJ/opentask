"""Requirement management commands for OpenTask CLI."""
import asyncio
import json
import click
from ..utils.api_client import OpenTaskClient, APIError
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


@click.group(name="requirement")
def requirement_cli():
    """Requirement management commands."""
    pass


@requirement_cli.group(name="comment")
def requirement_comment():
    """Requirement comment commands."""
    pass


@requirement_cli.group(name="document")
def requirement_document():
    """Requirement document management commands."""
    pass


# ============================================================================
# Helper Functions
# ============================================================================

def _get_current_user_id(client: OpenTaskClient) -> str | None:
    """Get current user ID using standardized method.

    Args:
        client: API client

    Returns:
        User ID as string, or None if not found
    """
    user_info = asyncio.run(client.get_me())
    return client.get_user_id_from_response(user_info)


def _format_json_response(success: bool, data: dict | None = None, error: str | None = None, message: str | None = None) -> str:
    """Format JSON response in standard structure for AI consumption.

    Args:
        success: Whether the operation succeeded
        data: Response data (for successful operations)
        error: Error message (for failed operations)
        message: Optional human-readable message

    Returns:
        JSON string with standardized format
    """
    response = {
        "success": success,
        "data": data,
        "error": error,
        "message": message or ("Operation successful" if success else "Operation failed")
    }
    return json.dumps(response, indent=2, ensure_ascii=False)


def _resolve_requirement_id(skin: ReplSkin, client: OpenTaskClient, requirement_input: str) -> str:
    """Resolve requirement input to ID.

    Supports:
    - Code (需求2026-116, REQ2026-116, etc.): Auto-convert to ID
    - UUID: Return as-is

    Args:
        skin: REPL skin for output
        client: API client
        requirement_input: User input (code or uuid)

    Returns:
        Requirement ID as UUID string
    """
    import re

    # Check if it's already a UUID
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    if uuid_pattern.match(requirement_input):
        return requirement_input

    # Try to resolve as code (需求2026-116, REQ2026-116, etc.)
    try:
        requirement = asyncio.run(client.get_requirement(requirement_input))
        req_id = requirement.get("id")
        if req_id:
            return req_id
        skin.error(f"Requirement found but has no ID: {requirement_input}")
        raise SystemExit(1)
    except APIError as e:
        skin.error(f"Failed to resolve requirement identifier '{requirement_input}': {e.message}")
        skin.hint("Use a valid requirement code (需求2026-116) or UUID")
        raise SystemExit(1)


def _resolve_user_id(skin: ReplSkin, client: OpenTaskClient, assignee_input: str) -> str | None:
    """Resolve assignee input to user ID.

    Supports:
    - "me": Current user
    - "none": Unassign (returns None)
    - UUID: Direct user ID
    - Username/JNPF account: Search and return user ID

    Args:
        skin: REPL skin for output
        client: API client
        assignee_input: User input (me/none/uuid/username)

    Returns:
        User ID as string, or None for unassign
    """
    # Handle "none" - unassign
    if assignee_input.lower() == "none":
        return None

    # Handle "me" - current user
    if assignee_input.lower() == "me":
        try:
            user_info = asyncio.run(client.get_me())
            user_id = (user_info.get("data") or user_info).get("id") or \
                      user_info.get("userId") or \
                      user_info.get("user_id")
            if user_id:
                return user_id
            skin.error("Could not get current user ID")
            return None
        except APIError as e:
            skin.error(f"Failed to get current user: {e.message}")
            return None

    # Handle UUID format - return as-is
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    if uuid_pattern.match(assignee_input):
        return assignee_input

    # Search user by name or account
    try:
        search_result = asyncio.run(client.search_users(assignee_input))
        users = search_result.get("data", [])

        if not users:
            skin.error(f"User not found: {assignee_input}")
            skin.hint("Use 'me' for yourself, 'none' to unassign, or a valid UUID")
            return None

        if len(users) == 1:
            # Only one match - use it
            user_id = users[0].get("id")
            user_name = users[0].get("jnpf_name") or users[0].get("jnpf_account")
            skin.info(f"Found user: {user_name}")
            return user_id

        # Multiple matches - return error (no interactive selection for AI)
        skin.error(f"Multiple users found matching '{assignee_input}' ({len(users)} matches)")
        skin.hint("Use 'me' for yourself, 'none' to unassign, or a valid UUID")
        matched_names = [u.get('jnpf_account', u.get('jnpf_name', 'Unknown')) for u in users[:3]]
        skin.hint(f"Matched users: {', '.join(matched_names)}...")
        return None

    except APIError as e:
        skin.error(f"Failed to search user: {e.message}")
        return None


@requirement_cli.command(name="list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--priority", "-p", help="Filter by priority")
@click.option("--project", "-P", "project_id", help="Filter by project ID")
@click.option("--assignee", "-a", help="Filter by assignee ID (use 'me' for current user)")
@click.option("--recent", is_flag=True, help="Show requirements created in last 7 days")
@click.option("--updated-today", is_flag=True, help="Show requirements updated today")
@click.option("--unassigned", is_flag=True, help="Show unassigned requirements")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=50, help="Page size")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_requirements(obj: "Context", status, priority, project_id, assignee, recent, updated_today, unassigned, page, page_size, as_json):
    """List requirements with filtering.

    Advanced filters:
        --recent: Requirements created in last 7 days
        --updated-today: Requirements updated today
        --unassigned: Requirements without assignee

    Assignee filter supports:
        --assignee me: Current user
        --assignee none: Unassigned requirements (same as --unassigned)
        --assignee <uuid>: Direct user ID
        --assignee <name>: Search by username (prompts if multiple matches)

    Examples:
        # Show my open requirements
        requirement list --assignee me --status open

        # Show recent high-priority requirements
        requirement list --recent --priority high

        # Show requirements updated today
        requirement list --updated-today

        # Show unassigned requirements
        requirement list --unassigned
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Use active project if not specified
    if not project_id and config.active_project_id:
        project_id = config.active_project_id

    # Resolve assignee_id if provided
    resolved_assignee_id = assignee
    if assignee:
        resolved_assignee_id = _resolve_user_id(skin, client, assignee)

    try:
        result = asyncio.run(client.list_requirements(
            page=page,
            page_size=page_size,
            status=status,
            priority=priority,
            project_id=project_id,
            assignee_id=resolved_assignee_id,
            recent=recent,
            updated_today=updated_today,
            unassigned=unassigned
        ))

        if json_mode:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return

        # Handle both 'data' and 'rows' fields
        rows = result.get("data", result.get("rows", []))
        total = result.get("total", len(rows))

        if not rows:
            skin.info("No requirements found")
            return

        skin.section(f"Requirements ({total} total)")

        headers = ["Code", "Title", "Status", "Priority", "Project", "Assignee", "Created"]
        table_rows = []
        for req in rows:
            project_name = req.get("project_name", "") or req.get("project_id", "")[:8] if req.get("project_id") else "N/A"
            table_rows.append([
                req.get("code", "N/A"),
                req.get("title", "")[:30],
                req.get("status", "draft"),
                req.get("priority", "medium"),
                project_name,
                req.get("assignee_id", "")[:8] if req.get("assignee_id") else "Unassigned",
                req.get("created_at", "")[:10] if req.get("created_at") else ""
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        skin.error(f"Failed to list requirements: {e.message}")


@requirement_cli.command(name="find")
@click.argument("keyword")
@click.option("--in-title", is_flag=True, help="Search in title only")
@click.option("--in-description", is_flag=True, help="Search in description only")
@click.option("--status", "-s", help="Filter by status")
@click.option("--priority", "-p", help="Filter by priority")
@click.option("--project", "-P", "project_id", help="Filter by project ID")
@click.option("--limit", "-l", default=20, help="Maximum results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def find_requirements(obj: "Context", keyword: str, in_title: bool, in_description: bool, status: str, priority: str, project_id: str, limit: int, as_json: bool):
    """Find requirements by keyword search.

    Examples:
        requirement find "API design"               # Search everywhere
        requirement find "auth" --in-title          # Search in title only
        requirement find "UI" --status draft --limit 50
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Use active project if not specified
    if not project_id and config.active_project_id:
        project_id = config.active_project_id

    try:
        result = asyncio.run(client.search_requirements(
            keyword=keyword,
            limit=limit
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Found {len(result)} requirement(s) matching '{keyword}'"
            ))
            return

        rows = result if isinstance(result, list) else []
        total = len(rows)

        if not rows:
            skin.info(f"No requirements found matching '{keyword}'")
            return

        skin.section(f"Requirements matching '{keyword}' ({total} total)")

        headers = ["Code", "Title", "Status", "Priority", "Project"]
        table_rows = []
        for req in rows:
            pid = req.get("project_id", "")
            table_rows.append([
                req.get("code", "N/A"),
                req.get("title", "")[:30],
                req.get("status", "draft"),
                req.get("priority", "medium"),
                pid[:8] if pid else "N/A",
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        if json_mode:
            click.echo(_format_json_response(
                success=False,
                error=e.message,
                message=f"Failed to search requirements: {e.message}"
            ))
        else:
            skin.error(f"Failed to search requirements: {e.message}")


@requirement_cli.command(name="show")
@click.argument("requirement_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--comments", "-c", "show_comments", is_flag=True, help="Show full comments (default: summary only)")
@click.pass_obj
def show_requirement(obj: "Context", requirement_id: str, as_json: bool, show_comments: bool):
    """Show requirement details.

    Examples:
        requirement show 需求2026-81           # Show with comment summary
        requirement show 需求2026-81 --comments # Show with full comments
        requirement show 需求2026-81 --json     # JSON output
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    try:
        requirement = asyncio.run(client.get_requirement(requirement_id))

        # Fetch comments to include in output (for both JSON and table mode)
        comments = []
        try:
            comments = asyncio.run(client.get_requirement_comments(requirement_id))
        except APIError as e:
            # Comments are optional, don't fail if they can't be loaded
            skin.warn(f"Failed to load comments: {e.message}")

        if json_mode:
            # Include comments in JSON output for agent context
            output = requirement.copy()
            output["comments"] = comments
            click.echo(json.dumps(output, indent=2, ensure_ascii=False))
            return

        skin.section("Requirement Details")

        skin.status_block({
            "ID": requirement.get("id", ""),
            "Code": requirement.get("code", "N/A"),
            "Title": requirement.get("title", ""),
            "Description": requirement.get("description", "") or "N/A",
            "Status": requirement.get("status", "planning"),
            "Priority": requirement.get("priority", "medium"),
            "Project": requirement.get("project_id", "")[:8] if requirement.get("project_id") else "N/A",
            "Assignee": requirement.get("assignee_id", "")[:8] if requirement.get("assignee_id") else "Unassigned",
            "Created": requirement.get("created_at", "")[:19] if requirement.get("created_at") else "N/A",
            "Updated": requirement.get("updated_at", "")[:19] if requirement.get("updated_at") else "N/A"
        })

        # Comments - Display the comments we already fetched
        if comments:
            # Get rows from response if it's a paginated result
            if isinstance(comments, dict) and "rows" in comments:
                comment_list = comments.get("rows", [])
            elif isinstance(comments, list):
                comment_list = comments
            else:
                comment_list = []

            if comment_list:
                skin.info(f"Comments ({len(comment_list)}) - {'Full' if show_comments else 'Summary (use --comments for full)'}")
                for idx, comment in enumerate(comment_list, 1):
                    # Try to get author from user_info object (requirement comments structure)
                    user_info = comment.get("user_info", {})
                    author_name = (
                        user_info.get("name") or
                        user_info.get("jnpf_name") or
                        user_info.get("jnpf_account") or
                        comment.get("user_id", "Unknown")[:8]  # Fallback to user_id
                    )
                    content = comment.get("content", "")
                    created_at = comment.get("created_at", "")

                    click.echo(f"\n--- Comment #{idx} ---")
                    click.echo(f"Author: {author_name}")
                    if created_at:
                        click.echo(f"Date: {created_at[:10]}")

                    # Show full content or summary
                    if show_comments:
                        click.echo(f"\n{content}\n")
                    else:
                        # Show summary: first 150 characters or first 3 lines
                        lines = content.split('\n')
                        if len(content) <= 150:
                            summary = content
                        else:
                            # Take first 3 lines, whichever is shorter
                            summary_lines = lines[:3]
                            summary = '\n'.join(summary_lines)
                            if len(summary) > 150:
                                summary = content[:150] + "..."
                        click.echo(f"\n{summary}\n")
            else:
                skin.info("Comments")
                click.echo("No comments yet.\n")
        else:
            skin.info("Comments")
            click.echo("No comments yet.\n")

    except APIError as e:
        skin.error(f"Failed to get requirement: {e.message}")


@requirement_cli.command(name="create")
@click.option("--title", "-t", required=True, help="Requirement title [REQUIRED]")
@click.option("--description", "-d", default="", help="Requirement description [RECOMMENDED]")
@click.option("--status", default="planning",
              type=click.Choice([
                  "planning",        # PLANNING - 规划中
                  "generating",      # GENERATING - 生成中
                  "evaluating",      # EVALUATING - 评审中
                  "completed",       # COMPLETED - 已完成
                  "closed",          # CLOSED - 已关闭
                  "archived"         # ARCHIVED - 已归档
              ], case_sensitive=False),
              help="Requirement status (default: planning). "
                   "planning=PLANNING, generating=GENERATING, evaluating=EVALUATING, "
                   "completed=COMPLETED, closed=CLOSED, archived=ARCHIVED")
@click.option("--priority", default="medium", type=click.Choice(["low", "medium", "high", "critical"]),
              help="Requirement priority (default: medium)")
@click.option("--project", "-P", "project_id",
              help="Project ID [Optional: uses active project if set]")
@click.option("--assignee", help="Assignee ID [Optional]")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def create_requirement(obj: "Context", title, description, status, priority, project_id, assignee, verbose: bool, as_json: bool):
    """Create a new requirement.

    Required fields:
        -t, --title TEXT         Requirement title

    Optional fields:
        -d, --description TEXT   Requirement description
        --status                 Requirement status (default: draft)
        --priority               Requirement priority (default: medium)
        -P, --project TEXT       Project ID (uses active project if set)
        --assignee TEXT          Assignee user ID
        -v, --verbose            Show detailed information (default: concise output)

    Status options:
        planning        PLANNING           规划中
        generating      GENERATING         生成中
        evaluating      EVALUATING         评审中
        completed       COMPLETED          已完成
        closed          CLOSED             已关闭
        archived        ARCHIVED           已归档

    Examples:
        opentask requirement create -t "User authentication" -d "Implement login"
        opentask requirement create -t "API" --status clarifying --priority high
        opentask requirement create -t "Frontend" --project PROJECT-001
        opentask requirement create -t "Task" --verbose  # Show full details

    Note: Status and priority values are automatically converted to API format.
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Use active project if not specified
    if not project_id and config.active_project_id:
        project_id = config.active_project_id

    try:
        requirement = asyncio.run(client.create_requirement(
            title=title,
            description=description,
            status=status,
            priority=priority,
            project_id=project_id,
            assignee_id=assignee
        ))

        if json_mode:
            click.echo(json.dumps(requirement, indent=2, ensure_ascii=False))
            return

        # Always show requirement details with code
        req_code = requirement.get('code', requirement.get('id', ''))
        skin.success(f"[OK] Requirement created: {requirement.get('title', req_code)}")

        skin.section("Requirement Details")
        skin.status_block({
            "ID": requirement.get("id", ""),
            "Code": requirement.get("code", "N/A"),
            "Title": requirement.get("title", ""),
            "Status": requirement.get("status", ""),
            "Priority": requirement.get("priority", "")
        })

        # Show description only in verbose mode or if it exists
        if verbose and requirement.get("description"):
            skin.section("Description")
            click.echo(f"  {requirement['description']}")

    except APIError as e:
        if json_mode:
            error_dict = {
                "success": False,
                "error": f"HTTP {e.status_code}" if e.status_code else "API Error",
                "message": e.message,
                "status_code": e.status_code,
                "suggestions": []
            }
            click.echo(json.dumps(error_dict, indent=2, ensure_ascii=False))
        else:
            from ..utils.api_client import _get_diagnostic_suggestions
            suggestions = _get_diagnostic_suggestions(e, "requirement")

            skin.error(f"Failed to create requirement: {e.message}")

            if e.status_code:
                skin.hint(f"Status Code: HTTP {e.status_code}")

            if suggestions:
                skin.hint("Possible causes:")
                for suggestion in suggestions:
                    skin.hint(f"  {suggestion}")


@requirement_cli.command(name="update")
@click.argument("requirement_id")
@click.option("--title", "-t", help="New title")
@click.option("--description", "-d", help="New description (⚠️ AI助手: 请使用 'requirement comments add' 提交分析结果)")
@click.option("--status", "-s",
              type=click.Choice([
                  "planning", "generating", "evaluating",
                  "completed", "closed", "archived"
              ], case_sensitive=False),
              help="New status. "
                   "Options: planning, generating, evaluating, completed, closed, archived")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high", "critical"]), help="New priority")
@click.option("--project", "-P", "project_id", help="Project ID")
@click.option("--assignee", help="Assignee ID")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--force-description", is_flag=True, hidden=True, help="Bypass AI assistant warning for description updates")
@click.pass_obj
def update_requirement(obj: "Context", requirement_id, title, description, status, priority, project_id, assignee, verbose: bool, as_json, force_description):
    """Update requirement.

    Supports both requirement codes (需求2026-116) and UUIDs.

    \b
    ⚠️  For AI Assistants:
    - Use 'requirement comments add <id> <content>' to submit analysis results
    - Only use --description for official requirement descriptions
    - Comments are better for: analysis, questions, discussions, progress updates

    Examples:
        requirement update 需求2026-116 --title "New title"
        requirement update 需求2026-116 --status designing --priority high
        requirement update REQ-ID --title "New" --verbose  # Show full details
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    kwargs = {}
    if title:
        kwargs["title"] = title
    if description:
        # Warn AI assistants about using comments instead
        if not force_description:
            skin.warning("⚠️  AI Assistant Detected")
            skin.warning("")
            skin.warning("You are updating the requirement description. For AI-generated content:")
            skin.warning("  → Use: requirement comments add " + requirement_id + " \"<your content>\"")
            skin.warning("")
            skin.warning("Benefits of using comments:")
            skin.warning("  • Preserves original requirement description")
            skin.warning("  • Maintains discussion history")
            skin.warning("  • Allows multiple analysis iterations")
            skin.warning("  • Better for collaborative review")
            skin.warning("")
            skin.warning("To proceed anyway, add --force-description flag")
            skin.error("Update cancelled. Use comments instead, or add --force-description to override.")
            return
        kwargs["description"] = description
    if status:
        kwargs["status"] = status
    if priority:
        kwargs["priority"] = priority
    if project_id:
        kwargs["project_id"] = project_id
    if assignee:
        kwargs["assignee_id"] = assignee

    if not kwargs:
        skin.error("At least one field must be specified for update")
        return

    try:
        requirement = asyncio.run(client.update_requirement(real_req_id, **kwargs))

        if json_mode:
            click.echo(json.dumps(requirement, indent=2, ensure_ascii=False))
            return

        # Concise output (default)
        req_code = requirement.get('code', requirement.get('id', requirement_id))
        skin.success(f"✓ Updated {req_code}")

        # Verbose output
        if verbose:
            skin.section("Updated Details")
            skin.status_block({
                "ID": requirement.get("id", ""),
                "Code": requirement.get("code", "N/A"),
                "Title": requirement.get("title", ""),
                "Status": requirement.get("status", ""),
                "Priority": requirement.get("priority", ""),
                "Project": requirement.get("project_id", "")[:8] if requirement.get("project_id") else "N/A"
            })

            if requirement.get("description"):
                skin.section("Description")
                click.echo(f"  {requirement['description']}")

    except APIError as e:
        skin.error(f"Failed to update requirement: {e.message}")


@requirement_cli.command(name="resolve")
@click.argument("requirement_id")
@click.option("--reason", "-r", help="Reason for resolution")
@click.option("--commit-id", "-c", help="Related commit ID")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def resolve_requirement(obj: "Context", requirement_id: str, reason: str, commit_id: str, as_json: bool):
    """Resolve a requirement (set status to REVIEWING).

    Indicates the requirement has been implemented and is ready for review.

    Supports both requirement codes (需求2026-116) and UUIDs.

    Examples:
        requirement resolve 需求2026-116
        requirement resolve 需求2026-116 --reason "Implementation completed"
        requirement resolve REQ-ID -r "Ready for review" -c "abc123"
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        # Update requirement status to REVIEWING
        requirement = asyncio.run(client.update_requirement(real_req_id, status="reviewing"))

        # Add comment if reason or commit-id provided
        if reason or commit_id:
            comment_parts = ["## 状态变更：REVIEWING"]
            if reason:
                comment_parts.append(f"\n**原因**：{reason}")
            if commit_id:
                comment_parts.append(f"\n**Commit**: {commit_id}")

            try:
                asyncio.run(client.add_requirement_comment(
                    requirement_id=real_req_id,
                    content="\n".join(comment_parts)
                ))
            except APIError as e:
                skin.warn(f"Status updated but failed to add comment: {e.message}")

        if json_mode:
            click.echo(json.dumps(requirement, indent=2, ensure_ascii=False))
            return

        skin.success(f"Requirement resolved: {requirement.get('code', requirement_id)}")

        skin.section("Updated Details")
        skin.status_block({
            "ID": requirement.get("id", ""),
            "Code": requirement.get("code", "N/A"),
            "Title": requirement.get("title", ""),
            "Status": requirement.get("status", ""),
        })

    except APIError as e:
        skin.error(f"Failed to resolve requirement: {e.message}")


@requirement_cli.command(name="start")
@click.argument("requirement_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def start_requirement(obj: "Context", requirement_id: str, as_json: bool):
    """Start working on a requirement (draft/clarifying → spec_ready).

    Supports both requirement codes (需求2026-116) and UUIDs.

    Examples:
        requirement start 需求2026-116
        requirement start REQ-ID
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        requirement = asyncio.run(client.update_requirement(real_req_id, status="spec_ready"))

        if json_mode:
            click.echo(json.dumps(requirement, indent=2, ensure_ascii=False))
            return

        skin.success(f"Requirement started: {requirement.get('code', requirement_id)}")

        skin.section("Updated Details")
        skin.status_block({
            "ID": requirement.get("id", ""),
            "Code": requirement.get("code", "N/A"),
            "Title": requirement.get("title", ""),
            "Status": requirement.get("status", ""),
        })

    except APIError as e:
        skin.error(f"Failed to start requirement: {e.message}")


@requirement_cli.command(name="reopen")
@click.argument("requirement_id")
@click.option("--reason", "-r", help="Reason for reopening")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def reopen_requirement(obj: "Context", requirement_id: str, reason: str, as_json: bool):
    """Reopen a requirement (released/completed → clarifying).

    Supports both requirement codes (需求2026-116) and UUIDs.

    Examples:
        requirement reopen 需求2026-116
        requirement reopen REQ-ID --reason "Need more clarification"
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        requirement = asyncio.run(client.update_requirement(real_req_id, status="clarifying"))

        if json_mode:
            click.echo(json.dumps(requirement, indent=2, ensure_ascii=False))
            return

        skin.success(f"Requirement reopened: {requirement.get('code', requirement_id)}")

        skin.section("Updated Details")
        skin.status_block({
            "ID": requirement.get("id", ""),
            "Code": requirement.get("code", "N/A"),
            "Title": requirement.get("title", ""),
            "Status": requirement.get("status", ""),
        })

    except APIError as e:
        skin.error(f"Failed to reopen requirement: {e.message}")


# ============================================================================
# Workflow Commands
# ============================================================================

@requirement_cli.command(name="todo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--limit", "-l", default=20, help="Maximum number of requirements to show")
@click.pass_obj
def requirement_todo(obj: "Context", as_json: bool, limit: int):
    """Show my TODO requirements (draft/clarifying + assigned to me).

    Examples:
        requirement todo
        requirement todo --limit 50
        requirement todo --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    try:
        # Get current user ID
        user_id = _get_current_user_id(client)

        if not user_id:
            skin.error("Could not get current user ID")
            return

        # List planning requirements assigned to me
        result = asyncio.run(client.list_requirements(
            page=1,
            page_size=limit,
            assignee_id=user_id
        ))

        if json_mode:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return

        rows = result.get("rows", [])
        total = result.get("total", 0)

        # Filter to only show draft/clarifying status
        todo_rows = [r for r in rows if r.get("status") in ["planning", "PLANNING"]]

        if not todo_rows:
            skin.info("✓ No TODO requirements! You're all caught up.")
            return

        skin.section(f"My TODO Requirements ({len(todo_rows)} total)")

        headers = ["Code", "Title", "Status", "Priority"]
        table_rows = []
        for req in todo_rows[:limit]:
            table_rows.append([
                req.get("code", "N/A"),
                req.get("title", "")[:40],
                req.get("status", "")[:12],
                req.get("priority", "")[:10]
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        skin.error(f"Failed to get TODO requirements: {e.message}")


@requirement_cli.command(name="in-progress")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--limit", "-l", default=20, help="Maximum number of requirements to show")
@click.pass_obj
def requirement_in_progress(obj: "Context", as_json: bool, limit: int):
    """Show requirements currently in progress (assigned to me).

    Examples:
        requirement in-progress
        requirement in-progress --limit 50
        requirement in-progress --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    try:
        # Get current user ID
        user_id = _get_current_user_id(client)

        if not user_id:
            skin.error("Could not get current user ID")
            return

        # List designing/coding requirements assigned to me
        result = asyncio.run(client.list_requirements(
            page=1,
            page_size=limit,
            assignee_id=user_id,
            sort_by="updated_at",
            sort_order="desc"
        ))

        if json_mode:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return

        rows = result.get("rows", [])
        total = result.get("total", 0)

        # Filter to only show in-progress statuses
        progress_rows = [r for r in rows if r.get("status") in ["designing", "coding", "DESIGNING", "CODING"]]

        if not progress_rows:
            skin.info("No requirements in progress")
            return

        skin.section(f"In Progress Requirements ({len(progress_rows)} total)")

        headers = ["ID", "Code", "Title", "Status", "Updated"]
        table_rows = []
        for req in progress_rows[:limit]:
            table_rows.append([
                req.get("id", "")[:8],
                req.get("code", "N/A")[:12],
                req.get("title", "")[:40],
                req.get("status", "")[:12],
                req.get("updated_at", "")[:10] if req.get("updated_at") else ""
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        skin.error(f"Failed to get in-progress requirements: {e.message}")


@requirement_cli.command(name="close")
@click.argument("requirement_id")
@click.option("--reason", "-r", help="Reason for closing")
@click.option("--commit-id", "-c", help="Related commit ID")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def close_requirement(obj: "Context", requirement_id: str, reason: str, commit_id: str, as_json: bool):
    """Close a requirement (set status to RELEASED).

    Indicates the requirement has been completed and released.

    Supports both requirement codes (需求2026-116) and UUIDs.

    Examples:
        requirement close 需求2026-116
        requirement close 需求2026-116 --reason "Released to production"
        requirement close REQ-ID -r "Deployed" -c "def456"
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        # Update requirement status to RELEASED
        requirement = asyncio.run(client.update_requirement(real_req_id, status="released"))

        # Add comment if reason or commit-id provided
        if reason or commit_id:
            comment_parts = ["## 状态变更：RELEASED"]
            if reason:
                comment_parts.append(f"\n**原因**：{reason}")
            if commit_id:
                comment_parts.append(f"\n**Commit**: {commit_id}")

            try:
                asyncio.run(client.add_requirement_comment(
                    requirement_id=real_req_id,
                    content="\n".join(comment_parts)
                ))
            except APIError as e:
                skin.warn(f"Status updated but failed to add comment: {e.message}")

        if json_mode:
            click.echo(json.dumps(requirement, indent=2, ensure_ascii=False))
            return

        skin.success(f"Requirement closed: {requirement.get('code', requirement_id)}")

        skin.section("Updated Details")
        skin.status_block({
            "ID": requirement.get("id", ""),
            "Code": requirement.get("code", "N/A"),
            "Title": requirement.get("title", ""),
            "Status": requirement.get("status", ""),
        })

    except APIError as e:
        skin.error(f"Failed to close requirement: {e.message}")


@requirement_cli.command(name="assign")
@click.argument("requirement_id")
@click.option("--assignee", "-a", "assignee_input", required=True,
              help="Assignee (user ID, username, 'me', or 'none' to unassign)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def assign_requirement(obj: "Context", requirement_id: str, assignee_input: str, as_json: bool):
    """Assign requirement to user.

    Supports both requirement codes (需求2026-116) and UUIDs.

    Assignee formats:
    - User ID (UUID): Direct assignment
    - Username: Search by name or JNPF account
    - 'me': Assign to current user
    - 'none': Unassign the requirement

    Examples:
        requirement assign 需求2026-116 --assignee jiangwei
        requirement assign REQ-ID -a me
        requirement assign REQ-ID --assignee none
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    # Resolve assignee input to user ID
    assignee_id = _resolve_user_id(skin, client, assignee_input)
    if assignee_id == "CANCELLED":
        return

    if assignee_id is None:
        # Unassign
        skin.info("Unassigning requirement...")
        # Note: This would require API support for unassign
        skin.error("Unassign not yet supported for requirements")
        return

    try:
        requirement = asyncio.run(client.assign_requirement(real_req_id, assignee_id))

        if json_mode:
            # Ensure assignee_id is explicitly included in the response
            response_data = requirement.copy()
            if "assignee" in response_data and response_data["assignee"]:
                response_data["assignee_id"] = response_data["assignee"].get("id")
            else:
                response_data["assignee_id"] = assignee_id

            click.echo(_format_json_response(
                success=True,
                data=response_data,
                message=f"Requirement assigned to: {assignee_id[:8]}"
            ))
            return

        skin.success(f"Assigned to {assignee_id[:8]}")

    except APIError as e:
        skin.error(f"Failed to assign requirement: {e.message}")


@requirement_cli.command(name="set-project")
@click.argument("requirement_id")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def set_requirement_project(obj: "Context", requirement_id: str, project_id: str, as_json: bool):
    """Set requirement project (shortcut for update --project).

    Supports both requirement codes (需求2026-116) and UUIDs.
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        requirement = asyncio.run(client.update_requirement(
            real_req_id,
            project_id=project_id
        ))

        if json_mode:
            click.echo(json.dumps(requirement, indent=2, ensure_ascii=False))
            return

        skin.success(f"Project updated for requirement: {requirement.get('title', requirement_id)}")

        skin.section("Updated Details")
        skin.status_block({
            "ID": requirement.get("id", ""),
            "Title": requirement.get("title", ""),
            "Project": requirement.get("project_id", "")
        })

    except APIError as e:
        skin.error(f"Failed to set project: {e.message}")


@requirement_comment.command(name="list")
@click.argument("requirement_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_comments(obj: "Context", requirement_id: str, as_json: bool):
    """List requirement comments.

    Supports both requirement codes (需求2026-116) and UUIDs.
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        result = asyncio.run(client.get_requirement_comments(real_req_id))

        if json_mode:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return

        comments = result.get("rows", [])
        total = result.get("total", 0)

        if not comments:
            skin.info(f"No comments found (requirement: {requirement_id[:8]})")
            return

        skin.section(f"Comments ({total} total)")

        for comment in comments:
            comment_id = comment.get("id", "")[:8]
            user_id = comment.get("user_id", "Unknown")[:8]
            content = comment.get("content", "")[:100]
            created_at = comment.get("created_at", "")[:19] if comment.get("created_at") else "N/A"

            skin.hint(f"[{comment_id}] {user_id} @ {created_at}")
            skin.hint(f"  {content}")
            print()

    except APIError as e:
        skin.error(f"Failed to list comments: {e.message}")


@requirement_comment.command(name="add")
@click.argument("requirement_id")
@click.argument("content")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def add_comment(obj: "Context", requirement_id: str, content: str, as_json: bool):
    """Add a comment to requirement.

    Supports both requirement codes (需求2026-116) and UUIDs.

    \b
    ✅ Recommended for AI Assistants to submit:
    - Requirement analysis results
    - Clarification questions
    - Technical suggestions
    - Progress updates
    - Implementation notes

    \b
    Example:
        requirement comments add 需求2026-116 "## Analysis Report\\n\\nDetails here..."
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        result = asyncio.run(client.add_requirement_comment(
            requirement_id=real_req_id,
            content=content
        ))

        if json_mode:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return

        skin.success(f"Comment added to requirement: {requirement_id[:8]}")

        skin.section("Comment Details")
        skin.status_block({
            "ID": result.get("id", "")[:8],
            "Content": result.get("content", "")[:100] + "..." if len(result.get("content", "")) > 100 else result.get("content", ""),
            "Created": result.get("created_at", "N/A")[:19]
        })

    except APIError as e:
        skin.error(f"Failed to add comment: {e.message}")


@requirement_comment.command(name="update")
@click.argument("comment_id")
@click.argument("content")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def update_comment(obj: "Context", comment_id: str, content: str, as_json: bool):
    """Update a requirement comment."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    try:
        result = asyncio.run(client.update_requirement_comment(
            comment_id=comment_id,
            content=content
        ))

        if json_mode:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return

        skin.success(f"Comment updated: {comment_id[:8]}")

        skin.section("Updated Details")
        skin.status_block({
            "ID": result.get("id", "")[:8],
            "Content": result.get("content", "")[:100] + "..." if len(result.get("content", "")) > 100 else result.get("content", ""),
            "Updated": result.get("updated_at", "N/A")[:19]
        })

    except APIError as e:
        skin.error(f"Failed to update comment: {e.message}")


@requirement_comment.command(name="delete")
@click.argument("comment_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def delete_comment(obj: "Context", comment_id: str, as_json: bool):
    """Delete a requirement comment."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    try:
        result = asyncio.run(client.delete_requirement_comment(comment_id))

        if json_mode:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return

        skin.success(f"Comment deleted: {comment_id[:8]}")

    except APIError as e:
        skin.error(f"Failed to delete comment: {e.message}")


@requirement_document.command(name="list")
@click.argument("requirement_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_requirement_documents(obj: "Context", requirement_id: str, as_json: bool):
    """List requirement documents.

    Supports both requirement codes (需求2026-116) and UUIDs.

    Examples:
        requirement document list 需求2026-116
        requirement document list REQ-ID --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        result = asyncio.run(client.get_requirement_documents(real_req_id))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Found {result.get('total', 0)} document(s)"
            ))
            return

        documents = result.get("data", [])
        total = result.get("total", 0)

        if not documents:
            skin.info(f"No documents found (requirement: {requirement_id})")
            return

        skin.section(f"Documents ({total} total)")

        for doc in documents:
            doc_id = doc.get("id", "")[:8]
            file_name = doc.get("file_name", "Unknown")
            status = doc.get("status", "DRAFT")
            created_at = doc.get("created_at", "")[:10] if doc.get("created_at") else "N/A"

            skin.hint(f"[{doc_id}] {file_name}")
            skin.hint(f"  Status: {status} | Created: {created_at}")

    except APIError as e:
        skin.error(f"Failed to list documents: {e.message}")


@requirement_document.command(name="upload")
@click.argument("requirement_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--status", "-s", default="DRAFT",
              type=click.Choice(["DRAFT", "PUBLISHED", "ARCHIVED"], case_sensitive=False),
              help="Document status (default: DRAFT)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def upload_requirement_document(obj: "Context", requirement_id: str, file_path: str, status: str, as_json: bool):
    """Upload a document to a requirement.

    Supports both requirement codes (需求2026-116) and UUIDs.

    Examples:
        requirement document upload 需求2026-116 /path/to/file.pdf
        requirement document upload REQ-ID report.pdf --status PUBLISHED
        requirement document upload REQ-ID design.png --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        # Upload document
        result = asyncio.run(client.upload_requirement_document(
            requirement_id=real_req_id,
            file_path=file_path,
            doc_status=status.upper()
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Document uploaded successfully"
            ))
            return

        import os
        filename = os.path.basename(file_path)
        skin.success(f"Document uploaded: {filename}")

        skin.section("Document Details")
        skin.status_block({
            "ID": result.get("id", "")[:8],
            "File Name": result.get("file_name", filename),
            "File Type": result.get("file_type", ""),
            "Status": result.get("status", status),
        })

    except FileNotFoundError as e:
        skin.error(str(e))
    except APIError as e:
        skin.error(f"Failed to upload document: {e.message}")


@requirement_document.command(name="delete")
@click.argument("requirement_id")
@click.argument("document_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def delete_requirement_document(obj: "Context", requirement_id: str, document_id: str, as_json: bool):
    """Delete a document from a requirement.

    Supports both requirement codes (需求2026-116) and UUIDs for requirement_id.

    Examples:
        requirement document delete 需求2026-116 DOCUMENT-ID
        requirement document delete REQ-ID abc123 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        success = asyncio.run(client.delete_requirement_document(real_req_id, document_id))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data={"document_id": document_id},
                message=f"Document deleted: {document_id[:8]}"
            ))
            return

        skin.success(f"Document deleted: {document_id[:8]}")

    except APIError as e:
        skin.error(f"Failed to delete document: {e.message}")


@requirement_document.command(name="download")
@click.argument("requirement_id")
@click.argument("document_id")
@click.argument("save_path", type=click.Path())
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def download_requirement_document(obj: "Context", requirement_id: str, document_id: str, save_path: str, as_json: bool):
    """Download a document from a requirement.

    Supports both requirement codes (需求2026-116) and UUIDs for requirement_id.

    If save_path is a directory, the original filename will be used.
    If save_path is a file path, the file will be saved to that path.

    Examples:
        requirement document download 需求2026-116 DOCUMENT-ID ./downloads/
        requirement document download REQ-ID abc123 /path/to/save.pdf
        requirement document download 需求2026-116 abc123 . --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        # Download document
        saved_path = asyncio.run(client.download_requirement_document(
            requirement_id=real_req_id,
            document_id=document_id,
            save_path=save_path
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data={"saved_path": saved_path, "document_id": document_id},
                message=f"Document downloaded to: {saved_path}"
            ))
            return

        import os
        filename = os.path.basename(saved_path)
        file_size = os.path.getsize(saved_path)
        size_mb = file_size / (1024 * 1024)

        skin.success(f"Document downloaded: {filename}")
        skin.section("Download Details")
        skin.status_block({
            "Saved to": saved_path,
            "File size": f"{size_mb:.2f} MB",
            "Document ID": document_id[:8],
        })

    except APIError as e:
        skin.error(f"Failed to download document: {e.message}")
    except Exception as e:
        skin.error(f"Download failed: {str(e)}")


@requirement_document.command(name="download-all")
@click.argument("requirement_id")
@click.argument("save_dir", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def download_all_requirement_documents(obj: "Context", requirement_id: str, save_dir: str, as_json: bool):
    """Download all documents from a requirement to a directory.

    Supports both requirement codes (需求2026-116) and UUIDs for requirement_id.

    All documents will be saved to the specified directory with their original filenames.

    Examples:
        requirement document download-all 需求2026-116 ./downloads/
        requirement document download-all REQ-ID /path/to/downloads
        requirement document download-all 需求2026-116 . --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Resolve requirement_id to UUID if it's a code
    real_req_id = _resolve_requirement_id(skin, client, requirement_id)

    try:
        # Get all documents
        result = asyncio.run(client.get_requirement_documents(real_req_id))
        documents = result.get("data", [])

        if not documents:
            skin.info(f"No documents found for requirement: {requirement_id}")
            return

        # Download each document
        downloaded = []
        failed = []

        for doc in documents:
            doc_id = doc.get("id")
            file_name = doc.get("file_name", f"document_{doc_id}")

            try:
                saved_path = asyncio.run(client.download_requirement_document(
                    requirement_id=real_req_id,
                    document_id=doc_id,
                    save_path=save_dir
                ))
                downloaded.append({
                    "document_id": doc_id[:8],
                    "file_name": file_name,
                    "saved_path": saved_path
                })
            except Exception as e:
                failed.append({
                    "document_id": doc_id[:8],
                    "file_name": file_name,
                    "error": str(e)
                })

        if json_mode:
            click.echo(_format_json_response(
                success=len(failed) == 0,
                data={
                    "downloaded": downloaded,
                    "failed": failed,
                    "total": len(documents),
                    "success_count": len(downloaded),
                    "failed_count": len(failed)
                },
                message=f"Downloaded {len(downloaded)}/{len(documents)} document(s)"
            ))
            return

        # Show results
        skin.section(f"Download Summary ({len(downloaded)}/{len(documents)} succeeded)")

        if downloaded:
            skin.success("Successfully downloaded:")
            for item in downloaded:
                skin.hint(f"  ✓ {item['file_name']}")

        if failed:
            skin.error(f"\nFailed to download {len(failed)} document(s):")
            for item in failed:
                skin.hint(f"  ✗ {item['file_name']}: {item['error']}")

    except APIError as e:
        skin.error(f"Failed to get documents: {e.message}")
    except Exception as e:
        skin.error(f"Batch download failed: {str(e)}")


@requirement_cli.command(name="delete")
@click.argument("requirement_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def delete_requirement(obj: "Context", requirement_id: str, force: bool, as_json: bool):
    """Delete a requirement (SECURITY: Not allowed via CLI).

    Supports both requirement codes (需求2026-116) and UUIDs.

    For security reasons, deletion operations are not allowed through CLI.
    This protects against accidental deletions by AI assistants.

    Examples:
        requirement delete 需求2026-116
        requirement delete REQ-ID
        requirement delete REQ-ID --force
        requirement delete REQ-ID --json
    """
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # 构建错误信息
    error_lines = [
        "❌ ERROR: Cannot delete requirement via CLI",
        "",
        "For security reasons, deletion operations are not allowed through CLI.",
        "",
        "Please use the Web UI to delete this requirement:",
        f"  1. Open: http://localhost:9527/requirement/detail?id={requirement_id}",
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
            "message": "Cannot delete requirement via CLI for security reasons",
            "web_ui_url": f"http://localhost:9527/requirement/detail?id={requirement_id}",
            "reason": "AI assistant protection"
        }
        click.echo(json.dumps(error_data, indent=2, ensure_ascii=False))

    # 返回错误码
    raise SystemExit(1)
