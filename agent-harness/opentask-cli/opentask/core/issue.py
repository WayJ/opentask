"""Issue management commands for OpenTask CLI."""
import asyncio
import json
import sys
import click
from ..utils.api_client import OpenTaskClient, APIError
from ..utils.cli_output import echo_json, handle_api_error, require_workspace_id
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


@click.group(name="issue")
def issue_cli():
    """Issue management commands."""
    pass


@issue_cli.group(name="comment")
def comment_cli():
    """Comment management commands."""
    pass


@issue_cli.group(name="document")
def document_cli():
    """Document management commands."""
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


def _handle_error(skin: ReplSkin, error: APIError, message: str, json_mode: bool = False) -> None:
    """Handle API error and exit with proper status code.

    Args:
        skin: REPL skin for output
        error: The API error
        message: Context message (e.g., "Failed to create issue")
        json_mode: Whether to output JSON format
    """
    if json_mode:
        click.echo(_format_json_response(
            success=False,
            error=error.message,
            message=f"{message}: {error.message}"
        ))
    else:
        skin.error(f"{message}: {error.message}")

    # Exit with error code for automation
    sys.exit(1)


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


def _display_issue_details(skin: ReplSkin, client: OpenTaskClient, issue: dict, show_comments: bool = False) -> None:
    """Display issue details in table format.

    Helper function to avoid code duplication between show and interactive modes.

    Args:
        skin: REPL skin for output
        client: API client
        issue: Issue data
        show_comments: Whether to show full comments (default: summary only)
    """
    real_issue_id = issue.get("id", "")

    # Fetch comments
    comments = []
    try:
        comments = asyncio.run(client.get_comments(real_issue_id))
    except APIError as e:
        skin.warn(f"Failed to load comments: {e.message}")

    # Display issue
    skin.section(f"Issue: {issue.get('issue_code', issue.get('id', ''))}")

    # Basic info
    skin.info("Basic Information")
    watching_label = "—"
    try:
        watchers = asyncio.run(client.list_issue_watchers(real_issue_id))
        if isinstance(watchers, dict):
            watchers = watchers.get("data") or watchers.get("rows") or []
        watching_label = f"yes ({len(watchers)} watchers)" if watchers else "no"
    except (APIError, TypeError, ValueError):
        watching_label = "—"

    skin.status_block({
        "ID": issue.get("id", ""),
        "Code": issue.get("issue_code", "N/A"),
        "Title": issue.get("title", ""),
        "Type": issue.get("type", "N/A"),
        "Status": issue.get("status", "N/A"),
        "Priority": issue.get("priority", "N/A"),
        "EstimatePoints": issue.get("estimate_points", "—"),
        "Watching": watching_label,
    })

    # People
    assignee = issue.get("assignee")
    reporter = issue.get("reporter")
    skin.info("People")
    skin.status_block({
        "Assignee": assignee.get("name", "Unassigned") if assignee else "Unassigned",
        "Reporter": reporter.get("name", "N/A") if reporter else "N/A",
    })

    # Dates
    skin.info("Dates")
    dates = {}
    if issue.get("created_at"):
        dates["Created"] = issue["created_at"][:10]
    if issue.get("started_at"):
        dates["Started"] = issue["started_at"][:10]
    if issue.get("resolved_at"):
        dates["Resolved"] = issue["resolved_at"][:10]
    if issue.get("closed_at"):
        dates["Closed"] = issue["closed_at"][:10]
    if issue.get("due_date"):
        dates["Due"] = issue["due_date"][:10]
    skin.status_block(dates if dates else {"No dates": "available"})

    # Statistics
    skin.info("Statistics")
    skin.status_block({
        "View Count": issue.get("view_count", 0),
        "Comment Count": issue.get("comment_count", 0),
        "Attachment Count": issue.get("attachment_count", 0),
    })

    # Description
    if issue.get("description"):
        skin.info("Description")
        click.echo(f"\n{issue['description']}\n")

    # Comments
    if comments:
        skin.info(f"Comments ({len(comments)}) - {'Full' if show_comments else 'Summary (use --comments for full)'}")
        for idx, comment in enumerate(comments, 1):
            author = comment.get("author", {})
            author_name = (
                author.get("name") or
                author.get("sso_name") or
                author.get("username") or
                comment.get("user_id", "Unknown")
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


def _resolve_user_id(skin: ReplSkin, client: OpenTaskClient, assignee_input: str) -> str | None:
    """Resolve assignee input to user ID.

    Supports:
    - "me": Current user
    - "none": Unassign (returns None)
    - UUID: Direct user ID
    - Username/SSO account: Search and return user ID

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
            user_id = _get_current_user_id(client)
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
            user_name = users[0].get("sso_name") or users[0].get("sso_account")
            skin.info(f"Found user: {user_name}")
            return user_id

        # Multiple matches - return error (no interactive selection for AI)
        skin.error(f"Multiple users found matching '{assignee_input}' ({len(users)} matches)")
        skin.hint("Use 'me' for yourself, 'none' to unassign, or a valid UUID")
        matched_names = [u.get('sso_account', u.get('sso_name', 'Unknown')) for u in users[:3]]
        skin.hint(f"Matched users: {', '.join(matched_names)}...")
        return None

    except APIError as e:
        skin.error(f"Failed to search user: {e.message}")
        return None


@issue_cli.command(name="list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--type", "-t", "issue_type", help="Filter by type")
@click.option("--priority", "-p", help="Filter by priority")
@click.option("--project", "-P", "project_id", help="Filter by project ID")
@click.option("--assignee", "-a", "assignee_id", help="Filter by assignee ID (use 'me' for current user)")
@click.option("--mine", is_flag=True, help="E19: assigned to me (assignee=me)")
@click.option("--watching", is_flag=True, help="E19: issues I watch")
@click.option("--due-soon", "due_soon", is_flag=True, help="E19: due within 3 days (open)")
@click.option("--search", help="Search keyword")
@click.option("--open-only", is_flag=True, help="Show only open issues (shorthand for --status open)")
@click.option("--recent", is_flag=True, help="Show issues created in last 7 days")
@click.option("--updated-today", is_flag=True, help="Show issues updated today")
@click.option("--overdue", is_flag=True, help="Show overdue issues (due_date < today AND status IN (open, in_progress))")
@click.option("--unassigned", is_flag=True, help="Show unassigned issues")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=20, help="Page size")
@click.option("--sort-by", default="created_at", help="Sort field")
@click.option("--sort-order", default="desc", help="Sort order (asc/desc)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_issues(obj: "Context", status, issue_type, priority, project_id, assignee_id, mine, watching, due_soon, search, open_only, recent, updated_today, overdue, unassigned, page, page_size, sort_by, sort_order, as_json):
    """List issues with filtering and pagination.

    Advanced filters:
        --recent: Issues created in last 7 days
        --updated-today: Issues updated today
        --overdue: Overdue issues (due_date < today AND status IN (open, in_progress))
        --unassigned: Issues without assignee

    Assignee filter supports:
        --assignee me: Current user
        --assignee none: Unassigned issues (same as --unassigned)
        --assignee <uuid>: Direct user ID
        --assignee <name>: Search by username (prompts if multiple matches)

    Examples:
        # Show my open issues
        issue list --assignee me --status open

        # Show recent high-priority issues
        issue list --recent --priority high

        # Show overdue issues
        issue list --overdue

        # Show issues updated today
        issue list --updated-today

        # Show unassigned bug reports
        issue list --unassigned --type bug
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # --open-only is a shorthand for --status open
    if open_only:
        status = "open"

    # Use active project if not specified
    if not project_id and config.active_project_id:
        project_id = config.active_project_id

    # --mine → assignee me
    if mine and not assignee_id:
        assignee_id = "me"

    # Resolve assignee_id if provided
    resolved_assignee_id = assignee_id
    if assignee_id and assignee_id != "me":
        resolved_assignee_id = _resolve_user_id(skin, client, assignee_id)

    try:
        result = asyncio.run(client.list_issues(
            page=page,
            page_size=page_size,
            type=issue_type,
            status=status,
            priority=priority,
            project_id=project_id,
            assignee_id=resolved_assignee_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            recent=recent,
            updated_today=updated_today,
            overdue=overdue,
            unassigned=unassigned,
            watching=watching,
            due_soon=due_soon,
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Found {result.get('total', 0)} issue(s)"
            ))
            return

        rows = result.get("rows", [])
        total = result.get("total", 0)

        if not rows:
            skin.info("No issues found")
            return

        skin.section(f"Issues ({total} total, Page {page})")

        headers = ["Code", "Title", "Type", "Priority", "Status", "Pts", "Created"]
        table_rows = []
        for issue in rows:
            pts = issue.get("estimate_points")
            table_rows.append([
                issue.get("issue_code", "N/A"),
                issue.get("title", "")[:30],
                issue.get("type", "")[:10],
                issue.get("priority", "")[:10],
                issue.get("status", "")[:10],
                "" if pts is None else str(pts),
                issue.get("created_at", "")[:10] if issue.get("created_at") else ""
            ])

        skin.table(headers, table_rows, max_col_width=30)

    except APIError as e:
        skin.error(f"Failed to list issues: {e.message}")


@issue_cli.command(name="batch")
@click.option("--ids", "-i", required=True, help="Comma-separated issue IDs, e.g. id1,id2,id3")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def batch_get_issues(obj: "Context", ids, as_json):
    """Batch get issues by IDs (max 100, optimized for performance)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # 解析 ID 列表
    issue_ids = [id.strip() for id in ids.split(",")]

    if len(issue_ids) > 100:
        skin.error("Maximum 100 IDs allowed per batch request")
        return

    try:
        result = asyncio.run(client.get_issues_by_ids(issue_ids))

        if as_json:
            data = result.get("data", result)
            click.echo(_format_json_response(
                success=True,
                data=data,
                message=f"Retrieved {data.get('total', 0)} issue(s)"
            ))
            return

        data = result.get("data", result)
        rows = data.get("rows", [])
        total = data.get("total", 0)

        if not rows:
            skin.info("No issues found")
            return

        skin.section(f"Issues ({total} total)")

        headers = ["Code", "Title", "Type", "Priority", "Status"]
        table_rows = []
        for issue in rows:
            table_rows.append([
                issue.get("issue_code", "N/A"),
                issue.get("title", "")[:40],
                issue.get("type", ""),
                issue.get("priority", ""),
                issue.get("status", ""),
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        skin.error(f"Failed to batch get issues: {e.message}")


@issue_cli.command(name="find")
@click.argument("keyword")
@click.option("--in-title", is_flag=True, help="Search in title only")
@click.option("--in-description", is_flag=True, help="Search in description only")
@click.option("--type", "-t", "issue_type", type=click.Choice(["bug", "feature", "question", "feedback", "incident", "improvement"], case_sensitive=False), help="Filter by type")
@click.option("--status", "-s", help="Filter by status")
@click.option("--priority", "-p", help="Filter by priority")
@click.option("--project", "-P", "project_id", help="Filter by project ID")
@click.option("--limit", "-l", default=20, help="Maximum results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def find_issues(obj: "Context", keyword: str, in_title: bool, in_description: bool, issue_type: str, status: str, priority: str, project_id: str, limit: int, as_json: bool):
    """Find issues by keyword search.

    Examples:
        issue find "login bug"                    # Search everywhere
        issue find "crash" --in-title            # Search in title only
        issue find "memory" --type bug --status open
        issue find "API" --priority high --limit 50
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
        result = asyncio.run(client.list_issues(
            page=1,
            page_size=limit,
            search=keyword,
            type=issue_type,
            status=status,
            priority=priority,
            project_id=project_id
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Found {result.get('total', 0)} issue(s) matching '{keyword}'"
            ))
            return

        rows = result.get("rows", [])
        total = result.get("total", 0)

        if not rows:
            skin.info(f"No issues found matching '{keyword}'")
            return

        skin.section(f"Issues matching '{keyword}' ({total} total)")

        headers = ["Code", "Title", "Type", "Priority", "Status"]
        table_rows = []
        for issue in rows:
            table_rows.append([
                issue.get("issue_code", "N/A"),
                issue.get("title", "")[:40],
                issue.get("type", ""),
                issue.get("priority", ""),
                issue.get("status", ""),
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        if json_mode:
            click.echo(_format_json_response(
                success=False,
                error=e.message,
                message=f"Failed to search issues: {e.message}"
            ))
        else:
            skin.error(f"Failed to search issues: {e.message}")

        sys.exit(1)


@issue_cli.command(name="my")
@click.option("--status", "-s", help="Filter by status")
@click.option("--type", "-t", "issue_type", help="Filter by type")
@click.option("--priority", "-p", help="Filter by priority")
@click.option("--project", "-P", "project_id", help="Filter by project ID")
@click.option("--open-only", is_flag=True, help="Show only open issues")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=20, help="Page size")
@click.option("--sort-by", default="created_at", help="Sort field")
@click.option("--sort-order", default="desc", help="Sort order (asc/desc)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_my_issues(obj: "Context", status, issue_type, priority, project_id, open_only, page, page_size, sort_by, sort_order, as_json):
    """List issues assigned to the current user."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    if not config.token:
        skin.error("Not authenticated. Use 'config login' first.")
        return

    try:
        # Get current user info
        user_info = asyncio.run(client.get_me())
        user_data = user_info.get("data", user_info) if isinstance(user_info, dict) else user_info
        user_id = client.get_user_id_from_response(user_info)

        # Try multiple fields for user display name
        user_name = (
            user_data.get("sso_name") if isinstance(user_data, dict) else None or
            user_data.get("name") if isinstance(user_data, dict) else None or
            user_data.get("username") if isinstance(user_data, dict) else None or
            user_data.get("sso_account") if isinstance(user_data, dict) else None or
            user_id[:8] if user_id else "Unknown"
        )

        if not user_id:
            skin.error("Failed to get user information")
            return

        # If open_only flag is set, override status
        if open_only:
            status = "open"

        # Use active project if not specified
        if not project_id and config.active_project_id:
            project_id = config.active_project_id

        # Get issues assigned to current user
        result = asyncio.run(client.list_issues(
            page=page,
            page_size=page_size,
            type=issue_type,
            status=status,
            priority=priority,
            project_id=project_id,
            assignee_id=user_id,
            sort_by=sort_by,
            sort_order=sort_order
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Found {result.get('total', 0)} issue(s) assigned to you"
            ))
            return

        rows = result.get("rows", [])
        total = result.get("total", 0)

        if not rows:
            skin.info(f"No issues assigned to {user_name}")
            return

        skin.section(f"My Issues ({total} total, Page {page})")
        skin.info(f"Assigned to: {user_name}")

        headers = ["Code", "Title", "Type", "Priority", "Status", "Created"]
        table_rows = []
        for issue in rows:
            table_rows.append([
                issue.get("issue_code", "N/A"),
                issue.get("title", "")[:30],
                issue.get("type", "")[:10],
                issue.get("priority", "")[:10],
                issue.get("status", "")[:10],
                issue.get("created_at", "")[:10] if issue.get("created_at") else ""
            ])

        skin.table(headers, table_rows, max_col_width=30)

    except APIError as e:
        skin.error(f"Failed to list my issues: {e.message}")


@issue_cli.command(name="create")
@click.option("--title", "-t", required=True, help="Issue title [REQUIRED]")
@click.option("--description", "-d", help="Issue description [RECOMMENDED]")
@click.option("--type", "-ty", "issue_type", default="feature",
              type=click.Choice(["bug", "feature", "question", "feedback", "incident", "improvement"], case_sensitive=False),
              help="Issue type (default: task)")
@click.option("--status", "-s", default="open",
              type=click.Choice(["open", "in_progress", "resolved", "closed"], case_sensitive=False),
              help="Issue status (default: open)")
@click.option("--priority", "-p", default="medium",
              type=click.Choice(["low", "medium", "high", "critical"], case_sensitive=False),
              help="Issue priority (default: medium)")
@click.option("--project", "-P", "project_id",
              help="Project ID [Optional: uses active project if set]")
@click.option("--assignee", "-a", "assignee_id",
              help="Assignee user ID [Optional]")
@click.option("--estimate-points", type=float, default=None,
              help="Story points estimate (e.g. 1/2/3/5/8)")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def create_issue(obj: "Context", title: str, description: str, issue_type: str, status: str, priority: str, project_id: str, assignee_id: str, estimate_points, verbose: bool, as_json: bool):
    """Create a new issue.

    Required fields:
        -t, --title TEXT         Issue title

    Optional fields:
        -d, --description TEXT   Issue description
        --type                   Issue type (task/bug/feature/improvement)
        -s, --status             Issue status (default: open)
        -p, --priority           Issue priority (default: medium)
        -P, --project TEXT       Project ID (uses active project if set)
        -a, --assignee TEXT      Assignee user ID
        -v, --verbose            Show detailed information (default: concise output)

    Examples:
        opentask issue create -t "Fix login bug" -d "Users cannot login"
        opentask issue create -t "New feature" --type feature --priority high
        opentask issue create -t "Bug" --project PROJECT-001 --assignee USER-123
        opentask issue create -t "Task" --verbose  # Show full details

    Note: Enum values (priority) are automatically normalized to lowercase API format.
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
        result = asyncio.run(client.create_issue(
            title=title,
            description=description or "",
            type=issue_type,
            status=status,
            priority=priority,
            project_id=project_id,
            assignee_id=assignee_id,
            estimate_points=estimate_points,
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Issue created: {result.get('issue_code', result.get('id', ''))}"
            ))
            return

        # Always show issue details with code
        issue_code = result.get('issue_code', result.get('id', ''))
        skin.success(f"[OK] Issue created: {result.get('title', issue_code)}")

        skin.section("Issue Details")
        skin.status_block({
            "ID": result.get("id", ""),
            "Code": result.get("issue_code", "N/A"),
            "Title": result.get("title", ""),
            "Type": result.get("type", ""),
            "Priority": result.get("priority", ""),
            "Status": result.get("status", ""),
            "EstimatePoints": result.get("estimate_points", "—"),
        })

        # Show description only in verbose mode or if it exists
        if verbose and result.get("description"):
            skin.section("Description")
            click.echo(f"  {result['description']}")

    except APIError as e:
        if json_mode:
            click.echo(_format_json_response(
                success=False,
                error=e.message,
                message=f"Failed to create issue: {e.message}"
            ))
        else:
            from ..utils.api_client import _get_diagnostic_suggestions
            suggestions = _get_diagnostic_suggestions(e, "issue")

            skin.error(f"Failed to create issue: {e.message}")

            if e.status_code:
                skin.hint(f"Status Code: HTTP {e.status_code}")

            if suggestions:
                skin.hint("Possible causes:")
                for suggestion in suggestions:
                    skin.hint(f"  {suggestion}")

        # Exit with error code
        sys.exit(1)


@issue_cli.command(name="update")
@click.argument("issue_id")
@click.option("--title", "-t", help="New title")
@click.option("--description", "-d", help="New description")
@click.option("--type", "-ty", "issue_type", type=click.Choice(["bug", "feature", "question", "feedback", "incident", "improvement"], case_sensitive=False), help="New issue type")
@click.option("--status", "-s", type=click.Choice(["open", "in_progress", "resolved", "closed"], case_sensitive=False), help="New status")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high", "critical"], case_sensitive=False), help="New priority")
@click.option("--assignee", "-a", "assignee_id", help="New assignee user ID")
@click.option("--reporter", "-r", "reporter_id", help="New reporter user ID")
@click.option("--estimate-points", type=float, default=None,
              help="Story points estimate (e.g. 1/2/3/5/8); omit to leave unchanged")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def update_issue(obj: "Context", issue_id: str, title, description, issue_type, status, priority, assignee_id, reporter_id, estimate_points, verbose: bool, as_json: bool):
    """Update an issue.

    Issue identifier format is auto-detected:
    - If KEY-N or legacy ISSUE{year}-N: treated as issue code (e.g., OT-1, ISSUE2026-32)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Examples:
        issue update ISSUE-ID --title "New title"
        issue update ISSUE-ID --status in_progress --priority high
        issue update ISSUE-ID --assignee user123 --type bug
        issue update ISSUE-ID --title "New" --verbose  # Show full details
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code (ISSUE + digits + hyphen + digits)
    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    if issue_code_pattern.match(issue_id):
        # It's a code, need to get the real ID first
        try:
            issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
            issue_id = issue_info.get("id", issue_id)
            issue_code = issue_info.get("issue_code", issue_id)
        except APIError as e:
            skin.error(f"Failed to resolve issue code {issue_id}: {e.message}")
            return
    else:
        issue_code = issue_id

    # Build update data
    kwargs = {}
    if title:
        kwargs["title"] = title
    if description:
        kwargs["description"] = description
    if issue_type:
        kwargs["type"] = issue_type
    if status:
        kwargs["status"] = status
    if priority:
        kwargs["priority"] = priority
    if assignee_id:
        kwargs["assignee_id"] = assignee_id
    if reporter_id:
        kwargs["reporter_id"] = reporter_id
    if estimate_points is not None:
        kwargs["estimate_points"] = estimate_points

    if not kwargs:
        skin.error("At least one field must be specified for update")
        return

    try:
        issue = asyncio.run(client.update_issue(issue_id, **kwargs))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=issue,
                message=f"Issue updated: {issue.get('issue_code', issue_code)}"
            ))
            return

        # Concise output (default)
        updated_code = issue.get('issue_code', issue_code)
        skin.success(f"✓ Updated {updated_code}")

        # Verbose output
        if verbose:
            skin.section("Updated Details")
            skin.status_block({
                "ID": issue.get("id", ""),
                "Code": issue.get("issue_code", "N/A"),
                "Title": issue.get("title", ""),
                "Type": issue.get("type", ""),
                "Status": issue.get("status", ""),
                "Priority": issue.get("priority", ""),
            })

            if issue.get("description"):
                skin.section("Description")
                click.echo(f"  {issue['description']}")

    except APIError as e:
        if json_mode:
            click.echo(_format_json_response(
                success=False,
                error=e.message,
                message=f"Failed to update issue: {e.message}"
            ))
        else:
            skin.error(f"Failed to update issue: {e.message}")

        sys.exit(1)


@issue_cli.command(name="start")
@click.argument("issue_ids", nargs=-1, required=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def start_issue(obj: "Context", issue_ids: tuple, as_json: bool):
    """Start working on one or more issues (open → in_progress).

    Examples:
        issue start ISSUE-ID
        issue start ISSUE-ID1 ISSUE-ID2 ISSUE-ID3
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)

    # Start all issues
    results = []
    for issue_id in issue_ids:
        real_issue_id = issue_id

        # Auto-detect: check if it's an issue code
        if issue_code_pattern.match(issue_id):
            try:
                issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
                real_issue_id = issue_info.get("id", issue_id)
            except APIError as e:
                results.append({"issue_id": issue_id, "success": False, "error": str(e.message)})
                continue

        try:
            # Update issue status to IN_PROGRESS
            issue = asyncio.run(client.update_issue(real_issue_id, status="in_progress"))
            results.append({
                "issue_id": issue_id,
                "success": True,
                "code": issue.get('issue_code', issue_id)
            })

        except APIError as e:
            results.append({"issue_id": issue_id, "success": False, "error": str(e.message)})

    # Output results
    if json_mode:
        success_count = sum(1 for r in results if r["success"])
        click.echo(_format_json_response(
            success=success_count > 0,
            data={"results": results, "total": len(results), "successful": success_count, "failed": len(results) - success_count},
            message=f"Started {success_count}/{len(results)} issue(s)"
        ))
        return

    # Show summary
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    if success_count == total_count:
        skin.success(f"✓ Started {total_count} issue(s)")
    else:
        skin.warning(f"Started {success_count}/{total_count} issues")

    # Show details for failures
    if success_count < total_count:
        click.echo("\nFailed to start:")
        for r in results:
            if not r["success"]:
                click.echo(f"  ❌ {r['issue_id']}: {r.get('error', 'Unknown error')}")

    # Show details for successes (if multiple)
    if total_count > 1 and success_count > 0:
        click.echo("\nSuccessfully started:")
        for r in results:
            if r["success"]:
                click.echo(f"  ✓ {r['issue_id']} ({r.get('code', 'N/A')})")


@issue_cli.command(name="reopen")
@click.argument("issue_ids", nargs=-1, required=True)
@click.option("--reason", "-r", help="Reason for reopening")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def reopen_issue(obj: "Context", issue_ids: tuple, reason: str, as_json: bool):
    """Reopen one or more issues (resolved/closed → open).

    Examples:
        issue reopen ISSUE-ID
        issue reopen ISSUE-ID1 ISSUE-ID2
        issue reopen ISSUE-ID --reason "Need more work"
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)

    # Prepare comment if reason provided
    comment_text = None
    if reason:
        comment_text = f"## 状态变更：OPEN\n\n**原因**：{reason}"

    # Reopen all issues
    results = []
    for issue_id in issue_ids:
        real_issue_id = issue_id

        # Auto-detect: check if it's an issue code
        if issue_code_pattern.match(issue_id):
            try:
                issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
                real_issue_id = issue_info.get("id", issue_id)
            except APIError as e:
                results.append({"issue_id": issue_id, "success": False, "error": str(e.message)})
                continue

        try:
            # Update issue status to OPEN
            issue = asyncio.run(client.update_issue(real_issue_id, status="open"))

            # Add comment if provided
            if comment_text:
                try:
                    asyncio.run(client.add_comment(real_issue_id, comment_text))
                except APIError:
                    pass  # Comment failure is not critical

            results.append({
                "issue_id": issue_id,
                "success": True,
                "code": issue.get('issue_code', issue_id)
            })

        except APIError as e:
            results.append({"issue_id": issue_id, "success": False, "error": str(e.message)})

    # Output results
    if json_mode:
        success_count = sum(1 for r in results if r["success"])
        click.echo(_format_json_response(
            success=success_count > 0,
            data={"results": results, "total": len(results), "successful": success_count, "failed": len(results) - success_count},
            message=f"Reopened {success_count}/{len(results)} issue(s)"
        ))
        return

    # Show summary
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    if success_count == total_count:
        skin.success(f"✓ Reopened {total_count} issue(s)")
    else:
        skin.warning(f"Reopened {success_count}/{total_count} issues")

    # Show details for failures
    if success_count < total_count:
        click.echo("\nFailed to reopen:")
        for r in results:
            if not r["success"]:
                click.echo(f"  ❌ {r['issue_id']}: {r.get('error', 'Unknown error')}")

    # Show details for successes (if multiple)
    if total_count > 1 and success_count > 0:
        click.echo("\nSuccessfully reopened:")
        for r in results:
            if r["success"]:
                click.echo(f"  ✓ {r['issue_id']} ({r.get('code', 'N/A')})")


# ============================================================================
# Workflow Commands
# ============================================================================

@issue_cli.command(name="todo")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--limit", "-l", default=20, help="Maximum number of issues to show")
@click.pass_obj
def issue_todo(obj: "Context", as_json: bool, limit: int):
    """Show my TODO list (open + assigned to me).

    This is a convenient alias for:
        issue list --status open --assignee me

    Examples:
        issue todo
        issue todo --limit 50
        issue todo --json
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

        # List open issues assigned to me
        result = asyncio.run(client.list_issues(
            page=1,
            page_size=limit,
            status="open",
            assignee_id=user_id,
            sort_by="priority",
            sort_order="desc"
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Found {result.get('total', 0)} TODO item(s)"
            ))
            return

        rows = result.get("rows", [])
        total = result.get("total", 0)

        if not rows:
            skin.info("🎉 No TODOs! You're all caught up.")
            return

        skin.section(f"My TODOs ({total} total)")

        headers = ["Code", "Title", "Priority", "Created"]
        table_rows = []
        for issue in rows:
            table_rows.append([
                issue.get("issue_code", "N/A"),
                issue.get("title", "")[:40],
                issue.get("priority", "")[:10],
                issue.get("created_at", "")[:10] if issue.get("created_at") else ""
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        skin.error(f"Failed to get TODOs: {e.message}")


@issue_cli.command(name="in-progress")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--limit", "-l", default=20, help="Maximum number of issues to show")
@click.pass_obj
def issue_in_progress(obj: "Context", as_json: bool, limit: int):
    """Show issues currently in progress (assigned to me).

    This is a convenient alias for:
        issue list --status in_progress --assignee me

    Examples:
        issue in-progress
        issue in-progress --limit 50
        issue in-progress --json
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

        # List in-progress issues assigned to me
        result = asyncio.run(client.list_issues(
            page=1,
            page_size=limit,
            status="in_progress",
            assignee_id=user_id,
            sort_by="updated_at",
            sort_order="desc"
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Found {result.get('total', 0)} issue(s) in progress"
            ))
            return

        rows = result.get("rows", [])
        total = result.get("total", 0)

        if not rows:
            skin.info("No issues in progress")
            return

        skin.section(f"In Progress ({total} total)")

        headers = ["ID", "Code", "Title", "Priority", "Updated"]
        table_rows = []
        for issue in rows:
            table_rows.append([
                issue.get("id", "")[:8],
                issue.get("issue_code", "")[:10],
                issue.get("title", "")[:40],
                issue.get("priority", "")[:10],
                issue.get("updated_at", "")[:10] if issue.get("updated_at") else ""
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        skin.error(f"Failed to get in-progress issues: {e.message}")


@issue_cli.command(name="blocking")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--limit", "-l", default=20, help="Maximum number of issues to show")
@click.pass_obj
def issue_blocking(obj: "Context", as_json: bool, limit: int):
    """Show issues blocking me (open + high priority + assigned to me).

    This shows high-priority issues that need your attention.

    Examples:
        issue blocking
        issue blocking --limit 50
        issue blocking --json
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

        # List high-priority open issues assigned to me
        result = asyncio.run(client.list_issues(
            page=1,
            page_size=limit,
            status="open",
            priority="high",
            assignee_id=user_id,
            sort_by="priority",
            sort_order="desc"
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Found {result.get('total', 0)} blocking issue(s)"
            ))
            return

        rows = result.get("rows", [])
        total = result.get("total", 0)

        if not rows:
            skin.info("✓ No blocking issues! All clear.")
            return

        skin.warning(f"Blocking Issues ({total} total)")
        skin.hint("High-priority issues that need your attention:")
        click.echo("")

        headers = ["ID", "Code", "Title", "Priority", "Created"]
        table_rows = []
        for issue in rows:
            table_rows.append([
                issue.get("id", "")[:8],
                issue.get("issue_code", "")[:10],
                issue.get("title", "")[:40],
                issue.get("priority", "")[:10],
                issue.get("created_at", "")[:10] if issue.get("created_at") else ""
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        skin.error(f"Failed to get blocking issues: {e.message}")


@issue_cli.command(name="resolve")
@click.argument("issue_ids", nargs=-1, required=True)
@click.option("--reason", "-r", help="Reason for resolution")
@click.option("--commit-id", "-c", help="Related commit ID")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def resolve_issue(obj: "Context", issue_ids: tuple, reason: str, commit_id: str, as_json: bool):
    """Resolve one or more issues (set status to RESOLVED).

    Optionally adds a comment with reason and/or commit ID.

    Examples:
        issue resolve ISSUE-ID
        issue resolve ISSUE-ID1 ISSUE-ID2 ISSUE-ID3
        issue resolve ISSUE-ID --reason "Fixed the bug"
        issue resolve ISSUE-ID -r "Completed" -c "abc123"
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)

    # Prepare comment if reason or commit-id provided
    comment_text = None
    if reason or commit_id:
        comment_parts = ["## 状态变更：RESOLVED"]
        if reason:
            comment_parts.append(f"\n**原因**：{reason}")
        if commit_id:
            comment_parts.append(f"\n**Commit**: {commit_id}")
        comment_text = "\n".join(comment_parts)

    # Resolve all issues
    results = []
    for issue_id in issue_ids:
        real_issue_id = issue_id

        # Auto-detect: check if it's an issue code
        if issue_code_pattern.match(issue_id):
            try:
                issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
                real_issue_id = issue_info.get("id", issue_id)
            except APIError as e:
                results.append({"issue_id": issue_id, "success": False, "error": str(e.message)})
                continue

        try:
            # Update issue status to RESOLVED
            issue = asyncio.run(client.update_issue(real_issue_id, status="resolved"))

            # Add comment if provided
            if comment_text:
                try:
                    asyncio.run(client.add_comment(real_issue_id, comment_text))
                except APIError:
                    pass  # Comment failure is not critical

            results.append({
                "issue_id": issue_id,
                "success": True,
                "code": issue.get('issue_code', issue_id)
            })

        except APIError as e:
            results.append({"issue_id": issue_id, "success": False, "error": str(e.message)})

    # Output results
    if json_mode:
        success_count = sum(1 for r in results if r["success"])
        click.echo(_format_json_response(
            success=success_count > 0,
            data={"results": results, "total": len(results), "successful": success_count, "failed": len(results) - success_count},
            message=f"Resolved {success_count}/{len(results)} issue(s)"
        ))
        return

    # Show summary
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    if success_count == total_count:
        skin.success(f"✓ Resolved {total_count} issue(s)")
    else:
        skin.warning(f"Resolved {success_count}/{total_count} issues")

    # Show details for failures
    if success_count < total_count:
        click.echo("\nFailed to resolve:")
        for r in results:
            if not r["success"]:
                click.echo(f"  ❌ {r['issue_id']}: {r.get('error', 'Unknown error')}")

    # Show details for successes (if multiple)
    if total_count > 1 and success_count > 0:
        click.echo("\nSuccessfully resolved:")
        for r in results:
            if r["success"]:
                click.echo(f"  ✓ {r['issue_id']} ({r.get('code', 'N/A')})")


@issue_cli.command(name="close")
@click.argument("issue_ids", nargs=-1, required=True)
@click.option("--reason", "-r", help="Reason for closing")
@click.option("--commit-id", "-c", help="Related commit ID")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def close_issue(obj: "Context", issue_ids: tuple, reason: str, commit_id: str, as_json: bool):
    """Close one or more issues (set status to CLOSED).

    Optionally adds a comment with reason and/or commit ID.

    Examples:
        issue close ISSUE-ID
        issue close ISSUE-ID1 ISSUE-ID2 ISSUE-ID3
        issue close ISSUE-ID --reason "Completed"
        issue close ISSUE-ID -r "Done" -c "def456"
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)

    # Prepare comment if reason or commit-id provided
    comment_text = None
    if reason or commit_id:
        comment_parts = ["## 状态变更：CLOSED"]
        if reason:
            comment_parts.append(f"\n**原因**：{reason}")
        if commit_id:
            comment_parts.append(f"\n**Commit**: {commit_id}")
        comment_text = "\n".join(comment_parts)

    # Close all issues
    results = []
    for issue_id in issue_ids:
        real_issue_id = issue_id

        # Auto-detect: check if it's an issue code
        if issue_code_pattern.match(issue_id):
            try:
                issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
                real_issue_id = issue_info.get("id", issue_id)
            except APIError as e:
                results.append({"issue_id": issue_id, "success": False, "error": str(e.message)})
                continue

        try:
            # Update issue status to CLOSED
            issue = asyncio.run(client.update_issue(real_issue_id, status="closed"))

            # Add comment if provided
            if comment_text:
                try:
                    asyncio.run(client.add_comment(real_issue_id, comment_text))
                except APIError:
                    pass  # Comment failure is not critical

            results.append({
                "issue_id": issue_id,
                "success": True,
                "code": issue.get('issue_code', issue_id)
            })

        except APIError as e:
            results.append({"issue_id": issue_id, "success": False, "error": str(e.message)})

    # Output results
    if json_mode:
        success_count = sum(1 for r in results if r["success"])
        click.echo(_format_json_response(
            success=success_count > 0,
            data={"results": results, "total": len(results), "successful": success_count, "failed": len(results) - success_count},
            message=f"Closed {success_count}/{len(results)} issue(s)"
        ))
        return

    # Show summary
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)

    if success_count == total_count:
        skin.success(f"✓ Closed {total_count} issue(s)")
    else:
        skin.warning(f"Closed {success_count}/{total_count} issues")

    # Show details for failures
    if success_count < total_count:
        click.echo("\nFailed to close:")
        for r in results:
            if not r["success"]:
                click.echo(f"  ❌ {r['issue_id']}: {r.get('error', 'Unknown error')}")

    # Show details for successes (if multiple)
    if total_count > 1 and success_count > 0:
        click.echo("\nSuccessfully closed:")
        for r in results:
            if r["success"]:
                click.echo(f"  ✓ {r['issue_id']} ({r.get('code', 'N/A')})")


@issue_cli.command(name="show")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--comments", "-c", "show_comments", is_flag=True, help="Show full comments (default: summary only)")
@click.pass_obj
def show_issue(obj: "Context", issue_id: str, as_json: bool, show_comments: bool):
    """Show issue details by ID or code (auto-detected).

    Issue identifier format is auto-detected:
    - If KEY-N or legacy ISSUE{year}-N: treated as issue code (e.g., OT-1, ISSUE2026-32)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Examples:
        issue show ISSUE2026-32                         # Auto-detected as code
        issue show 5ee3420e-2d69-4509-9ae7-524e8c40d6d1 # Auto-detected as ID
        issue show ISSUE2026-32 --json                  # JSON output
        issue show ISSUE2026-32 --comments               # Show full comments
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    by_code = issue_code_pattern.match(issue_id) is not None

    try:
        # Get issue by ID or code
        issue = asyncio.run(client.get_issue(issue_id, by_code=by_code))

        if json_mode:
            # Fetch comments for JSON output
            real_issue_id = issue.get("id", issue_id)
            comments = []
            try:
                comments = asyncio.run(client.get_comments(real_issue_id))
            except APIError:
                pass

            output = issue.copy()
            output["comments"] = comments
            try:
                watchers = asyncio.run(client.list_issue_watchers(real_issue_id))
                if isinstance(watchers, dict):
                    watchers = watchers.get("data") or watchers.get("rows") or []
                output["watchers"] = watchers
                output["watching_count"] = len(watchers) if isinstance(watchers, list) else 0
            except (APIError, TypeError, ValueError):
                output["watchers"] = []
                output["watching_count"] = 0
            click.echo(_format_json_response(
                success=True,
                data=output,
                message=f"Issue: {output.get('issue_code', output.get('id', ''))}"
            ))
            return

        # Display in table format
        _display_issue_details(skin, client, issue, show_comments)

    except APIError as e:
        if json_mode:
            click.echo(_format_json_response(
                success=False,
                error=e.message,
                message=f"Failed to get issue: {e.message}"
            ))
        elif e.status_code == 404:
            skin.error(f"Issue not found: {issue_id}")
            if by_code:
                skin.hint("Make sure the issue code is correct (e.g., ISSUE2026-32)")
            else:
                skin.hint("Use 'issue list' to browse issues")
        else:
            skin.error(f"Failed to get issue: {e.message}")

        sys.exit(1)



@issue_cli.command(name="watch")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def watch_issue_cmd(obj: "Context", issue_id: str, as_json: bool):
    """关注 Issue（Inbox 收评论/状态/指派更新）。支持 KEY-N。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        real_id, _info = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(client.watch_issue(real_id))
        if json_mode:
            echo_json(True, data=data, message="watching")
            return
        skin.success(f"已关注 {issue_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@issue_cli.command(name="unwatch")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def unwatch_issue_cmd(obj: "Context", issue_id: str, as_json: bool):
    """取消关注 Issue。支持 KEY-N。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        real_id, _info = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(client.unwatch_issue(real_id))
        if json_mode:
            echo_json(True, data=data or {"id": real_id}, message="unwatched")
            return
        skin.success(f"已取消关注 {issue_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@issue_cli.command(name="watchers")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_issue_watchers_cmd(obj: "Context", issue_id: str, as_json: bool):
    """列出 Issue 关注者。支持 KEY-N。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        real_id, _info = asyncio.run(_resolve_issue_id(client, issue_id))
        rows = asyncio.run(client.list_issue_watchers(real_id))
        if isinstance(rows, dict):
            rows = rows.get("data") or rows.get("rows") or []
        if json_mode:
            echo_json(True, data={"rows": rows})
            return
        if not rows:
            skin.info("无关注者")
            return
        skin.table(
            ["User", "Since"],
            [[r.get("user_id", "")[:8], str(r.get("created_at") or "")[:19]] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@issue_cli.command(name="assign")
@click.argument("issue_id")
@click.option("--assignee", "-a", "assignee_input", required=True,
              help="Assignee (user ID, username, 'me', or 'none' to unassign)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def assign_issue(obj: "Context", issue_id: str, assignee_input: str, as_json: bool):
    """Assign an issue to a user.

    Issue identifier format is auto-detected:
    - If KEY-N or legacy ISSUE{year}-N: treated as issue code (e.g., OT-1, ISSUE2026-32)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Assignee formats:
    - User ID (UUID): Direct assignment
    - Username: Search by name or SSO account
    - 'me': Assign to current user
    - 'none': Unassign the issue

    Examples:
        issue assign ISSUE-ID --assignee jiangwei
        issue assign ISSUE2026-32 -a me
        issue assign ISSUE-ID --assignee none
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code (ISSUE + digits + hyphen + digits)
    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    if issue_code_pattern.match(issue_id):
        # It's a code, need to get the real ID first
        try:
            issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
            issue_id = issue_info.get("id", issue_id)
        except APIError as e:
            if json_mode:
                click.echo(_format_json_response(
                    success=False,
                    error=e.message,
                    message=f"Failed to resolve issue code {issue_id}"
                ))
            else:
                skin.error(f"Failed to resolve issue code {issue_id}: {e.message}")

            sys.exit(1)

    # Resolve assignee input to user ID
    assignee_id = _resolve_user_id(skin, client, assignee_input)
    if assignee_id == "CANCELLED":
        return

    try:
        issue = asyncio.run(client.update_issue_assignee(issue_id, assignee_id))

        if json_mode:
            assignee_name = "Unassigned"
            if assignee_id:
                assignee = issue.get("assignee", {})
                assignee_name = assignee.get("name") or assignee.get("sso_name") or assignee_id

            # Ensure assignee_id is explicitly included in the response
            response_data = issue.copy()
            if assignee_id and "assignee" in response_data:
                response_data["assignee_id"] = response_data["assignee"].get("id") if response_data["assignee"] else assignee_id
            else:
                response_data["assignee_id"] = assignee_id

            click.echo(_format_json_response(
                success=True,
                data=response_data,
                message=f"Issue {'assigned to ' + assignee_name if assignee_id else 'unassigned'}"
            ))
            return

        if assignee_id:
            assignee = issue.get("assignee", {})
            assignee_name = assignee.get("name") or assignee.get("sso_name") or assignee_id
            skin.success(f"Issue assigned to: {assignee_name}")
        else:
            skin.success("Issue unassigned")

        skin.section("Updated Details")
        skin.status_block({
            "ID": issue.get("id", ""),
            "Code": issue.get("issue_code", "N/A"),
            "Title": issue.get("title", ""),
            "Status": issue.get("status", ""),
            "Assignee": assignee_name if assignee_id else "Unassigned",
        })

    except APIError as e:
        if json_mode:
            click.echo(_format_json_response(
                success=False,
                error=e.message,
                message=f"Failed to assign issue: {e.message}"
            ))
        else:
            skin.error(f"Failed to assign issue: {e.message}")

        sys.exit(1)


@issue_cli.command(name="batch-assign")
@click.argument("issue_ids", nargs=-1, required=True)
@click.option("--assignee", "-a", "assignee_input", required=True,
              help="Assignee (user ID, 'me', or 'none' to unassign)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def batch_assign_issues(obj: "Context", issue_ids: tuple, assignee_input: str, as_json: bool):
    """Batch assign multiple issues to a user.

    Issue identifier format is auto-detected:
    - If KEY-N or legacy ISSUE{year}-N: treated as issue code (e.g., OT-1, ISSUE2026-32)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Assignee formats:
    - User ID (UUID): Direct assignment
    - 'me': Assign to current user
    - 'none': Unassign the issues

    Examples:
        issue batch-assign ISSUE-ID1 ISSUE-ID2 ISSUE-ID3 --assignee me
        issue batch-assign ISSUE2026-32 ISSUE2026-33 -a jiangwei
        issue batch-assign ISSUE-ID1 ISSUE-ID2 --assignee none
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Resolve assignee input to user ID
    assignee_id = _resolve_user_id(skin, client, assignee_input)
    if assignee_id == "CANCELLED":
        return

    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)

    # Assign all issues
    results = []
    for issue_id in issue_ids:
        real_issue_id = issue_id

        # Auto-detect: check if it's an issue code
        if issue_code_pattern.match(issue_id):
            try:
                issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
                real_issue_id = issue_info.get("id", issue_id)
            except APIError as e:
                results.append({
                    "issue_id": issue_id,
                    "success": False,
                    "error": str(e.message)
                })
                continue

        try:
            # Update issue assignee
            issue = asyncio.run(client.update_issue_assignee(real_issue_id, assignee_id))

            results.append({
                "issue_id": issue_id,
                "success": True,
                "code": issue.get('issue_code', issue_id)
            })

        except APIError as e:
            results.append({
                "issue_id": issue_id,
                "success": False,
                "error": str(e.message)
            })

    # Output results
    if json_mode:
        success_count = sum(1 for r in results if r["success"])
        click.echo(_format_json_response(
            success=success_count > 0,
            data={
                "results": results,
                "total": len(results),
                "successful": success_count,
                "failed": len(results) - success_count,
                "assignee_id": assignee_id
            },
            message=f"Assigned {success_count}/{len(results)} issue(s)"
        ))
        return

    # Text mode output
    success_count = sum(1 for r in results if r["success"])
    failed_results = [r for r in results if not r["success"]]

    if success_count > 0:
        assignee_name = assignee_id or "Unassigned"
        skin.success(f"✓ Assigned {success_count} issue(s) to: {assignee_name}")

        # Show successfully assigned issues
        for result in results:
            if result["success"]:
                code = result.get("code", result["issue_id"])
                skin.hint(f"  • {code}")

    if failed_results:
        skin.error(f"\n✗ Failed to assign {len(failed_results)} issue(s):")
        for result in failed_results:
            skin.hint(f"  • {result['issue_id']}: {result.get('error', 'Unknown error')}")

    # Summary
    skin.info(f"\nSummary: {success_count} succeeded, {len(failed_results)} failed out of {len(results)} total")

    # Exit with error if any failed
    if failed_results:
        sys.exit(1)


@comment_cli.command(name="add")
@click.argument("issue_id")
@click.argument("content", required=False)
@click.option("--message", "-m", "message_content", help="Comment content (alternative to positional arg)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def add_comment(obj: "Context", issue_id: str, content: str, message_content: str, as_json: bool):
    """Add a comment to an issue.

    Issue identifier format is auto-detected:
    - If KEY-N or legacy ISSUE{year}-N: treated as issue code (e.g., OT-1, ISSUE2026-32)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Examples:
        issue comment add ISSUE-ID "This is a comment"
        issue comment add ISSUE-ID -m "Another comment"
        opentask issue comment add ISSUE-ID "Fixed the bug"
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Get comment content from either argument or option
    comment_text = content or message_content
    if not comment_text:
        skin.error("Comment content is required. Use: issue comment <issue-id> <content>")
        return

    # Auto-detect: check if it's an issue code (ISSUE + digits + hyphen + digits)
    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    if issue_code_pattern.match(issue_id):
        # It's a code, need to get the real ID first
        try:
            issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
            issue_id = issue_info.get("id", issue_id)
        except APIError as e:
            skin.error(f"Failed to resolve issue code {issue_id}: {e.message}")
            return

    try:
        comment = asyncio.run(client.add_comment(issue_id, comment_text))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=comment,
                message=f"Comment added: {comment.get('id', '')[:8]}"
            ))
            return

        skin.success("Comment added successfully")

        skin.section("Comment Details")
        skin.status_block({
            "ID": comment.get("id", "")[:8],
            "Issue ID": comment.get("issue_id", "")[:8],
            "Content": comment_text[:50] + "..." if len(comment_text) > 50 else comment_text,
        })

    except APIError as e:
        skin.error(f"Failed to add comment: {e.message}")


@comment_cli.command(name="list")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_comments(obj: "Context", issue_id: str, as_json: bool):
    """List all comments for an issue.

    Issue identifier format is auto-detected:
    - If KEY-N or legacy ISSUE{year}-N: treated as issue code (e.g., OT-1, ISSUE2026-32)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Examples:
        issue comment list ISSUE-ID
        issue comment list ISSUE2026-32 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    by_code = issue_code_pattern.match(issue_id) is not None

    try:
        comments = asyncio.run(client.get_comments(issue_id))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data={"comments": comments, "total": len(comments)},
                message=f"Found {len(comments)} comment(s)"
            ))
            return

        if not comments:
            skin.info("No comments found")
            return

        skin.section(f"Comments ({len(comments)} total)")

        for idx, comment in enumerate(comments, 1):
            # Try to get author from nested author object
            author = comment.get("author", {})
            author_name = (
                author.get("name") or
                author.get("sso_name") or
                comment.get("user_id", "Unknown")[:8]
            )

            created_at = comment.get("created_at", "")
            content = comment.get("content", "")

            click.echo(f"\n--- Comment #{idx} ---")
            click.echo(f"Author: {author_name}")
            if created_at:
                click.echo(f"Date: {created_at[:10]}")
            click.echo(f"\n{content}\n")

    except APIError as e:
        skin.error(f"Failed to get comments: {e.message}")


@comment_cli.command(name="delete")
@click.argument("comment_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def delete_comment(obj: "Context", comment_id: str, as_json: bool):
    """Delete a comment.

    You can only delete your own comments.

    Examples:
        issue comment delete COMMENT-ID
        issue comment delete a91b3cb3 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    try:
        success = asyncio.run(client.delete_comment(comment_id))

        if json_mode:
            click.echo(_format_json_response(
                success=success,
                data={"comment_id": comment_id},
                message=f"Comment deleted: {comment_id[:8]}" if success else "Failed to delete comment"
            ))
            return

        if success:
            skin.success(f"Comment deleted: {comment_id[:8]}")
        else:
            skin.error("Failed to delete comment")

    except APIError as e:
        skin.error(f"Failed to delete comment: {e.message}")


@document_cli.command(name="list")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_documents(obj: "Context", issue_id: str, as_json: bool):
    """List issue documents (attachments).

    Supports both issue codes (ISSUE2026-32) and UUIDs.

    Examples:
        issue document list ISSUE-ID
        issue document list ISSUE2026-32 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    by_code = issue_code_pattern.match(issue_id) is not None

    try:
        # Get real issue ID if using code
        real_issue_id = issue_id
        if by_code:
            issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
            real_issue_id = issue_info.get("id", issue_id)

        documents = asyncio.run(client.get_issue_documents(real_issue_id))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data={"documents": documents, "total": len(documents)},
                message=f"Found {len(documents)} document(s)"
            ))
            return

        if not documents:
            skin.info(f"No documents found (issue: {issue_id})")
            return

        skin.section(f"Documents ({len(documents)} total)")

        for doc in documents:
            doc_id = doc.get("id", "")[:8]
            file_name = doc.get("file_name", "Unknown")
            file_type = doc.get("file_type", "")
            file_size = doc.get("file_size", 0)
            created_at = doc.get("created_at", "")[:10] if doc.get("created_at") else "N/A"

            # Format file size
            size_mb = file_size / (1024 * 1024) if file_size else 0

            skin.hint(f"[{doc_id}] {file_name}")
            skin.hint(f"  Type: {file_type} | Size: {size_mb:.2f} MB | Created: {created_at}")

    except APIError as e:
        skin.error(f"Failed to list documents: {e.message}")


@document_cli.command(name="upload")
@click.argument("issue_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--description", "-d", help="Document description")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def upload_document(obj: "Context", issue_id: str, file_path: str, description: str, as_json: bool):
    """Upload a document to an issue.

    Supports both issue codes (ISSUE2026-32) and UUIDs.

    Examples:
        issue document upload ISSUE-ID /path/to/file.pdf
        issue document upload ISSUE-ID report.pdf --description "Weekly report"
        issue document upload ISSUE2026-32 design.png --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    import os
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    by_code = issue_code_pattern.match(issue_id) is not None

    try:
        # Get real issue ID if using code
        real_issue_id = issue_id
        if by_code:
            issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
            real_issue_id = issue_info.get("id", issue_id)

        # Upload document
        result = asyncio.run(client.upload_issue_document(
            issue_id=real_issue_id,
            file_path=file_path,
            description=description
        ))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Document uploaded successfully"
            ))
            return

        filename = os.path.basename(file_path)
        skin.success(f"Document uploaded: {filename}")

        skin.section("Document Details")
        skin.status_block({
            "ID": result.get("id", "")[:8],
            "File Name": result.get("file_name", filename),
            "File Type": result.get("file_type", ""),
            "File Size": f"{result.get('file_size', 0) / (1024*1024):.2f} MB" if result.get("file_size") else "N/A",
        })

    except FileNotFoundError as e:
        skin.error(str(e))
    except APIError as e:
        skin.error(f"Failed to upload document: {e.message}")


@document_cli.command(name="delete")
@click.argument("issue_id")
@click.argument("document_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def delete_document(obj: "Context", issue_id: str, document_id: str, as_json: bool):
    """Delete a document from an issue.

    Supports both issue codes (ISSUE2026-32) and UUIDs for issue_id.

    Examples:
        issue document delete ISSUE-ID DOCUMENT-ID
        issue document delete ISSUE2026-32 abc123 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    by_code = issue_code_pattern.match(issue_id) is not None

    try:
        # Get real issue ID if using code
        real_issue_id = issue_id
        if by_code:
            issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
            real_issue_id = issue_info.get("id", issue_id)

        success = asyncio.run(client.delete_issue_document(real_issue_id, document_id))

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


@document_cli.command(name="download")
@click.argument("issue_id")
@click.argument("document_id")
@click.argument("save_path", type=click.Path())
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def download_document(obj: "Context", issue_id: str, document_id: str, save_path: str, as_json: bool):
    """Download a document from an issue.

    Supports both issue codes (ISSUE2026-32) and UUIDs for issue_id.

    If save_path is a directory, the original filename will be used.
    If save_path is a file path, the file will be saved to that path.

    Examples:
        issue document download ISSUE-ID DOCUMENT-ID ./downloads/
        issue document download ISSUE-ID abc123 /path/to/save.pdf
        issue document download ISSUE2026-32 abc123 . --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    import os
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    by_code = issue_code_pattern.match(issue_id) is not None

    try:
        # Get real issue ID if using code
        real_issue_id = issue_id
        if by_code:
            issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
            real_issue_id = issue_info.get("id", issue_id)

        # Download document
        saved_path = asyncio.run(client.download_issue_document(
            issue_id=real_issue_id,
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


@document_cli.command(name="download-all")
@click.argument("issue_id")
@click.argument("save_dir", type=click.Path(exists=True))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def download_all_documents(obj: "Context", issue_id: str, save_dir: str, as_json: bool):
    """Download all documents from an issue to a directory.

    Supports both issue codes (ISSUE2026-32) and UUIDs for issue_id.

    All documents will be saved to the specified directory with their original filenames.

    Examples:
        issue document download-all ISSUE-ID ./downloads/
        issue document download-all ISSUE2026-32 /path/to/downloads
        issue document download-all ISSUE-ID . --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    import os
    issue_code_pattern = re.compile(r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$', re.IGNORECASE)
    by_code = issue_code_pattern.match(issue_id) is not None

    try:
        # Get real issue ID if using code
        real_issue_id = issue_id
        if by_code:
            issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
            real_issue_id = issue_info.get("id", issue_id)

        # Get all documents
        documents = asyncio.run(client.get_issue_documents(real_issue_id))

        if not documents:
            skin.info(f"No documents found for issue: {issue_id}")
            return

        # Download each document
        downloaded = []
        failed = []

        for doc in documents:
            doc_id = doc.get("id")
            file_name = doc.get("file_name", f"document_{doc_id}")

            try:
                saved_path = asyncio.run(client.download_issue_document(
                    issue_id=real_issue_id,
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


@issue_cli.command(name="delete")
@click.argument("issue_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def delete_issue(obj: "Context", issue_id: str, force: bool, as_json: bool):
    """Delete an issue (SECURITY: Not allowed via CLI).

    For security reasons, deletion operations are not allowed through CLI.
    This protects against accidental deletions by AI assistants.

    Examples:
        issue delete ISSUE-ID
        issue delete ISSUE2026-1
        issue delete ISSUE-ID --force
        issue delete ISSUE-ID --json
    """
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # 构建错误信息
    error_lines = [
        "❌ ERROR: Cannot delete issue via CLI",
        "",
        "For security reasons, deletion operations are not allowed through CLI.",
        "",
        "Please use the Web UI to delete this issue:",
        f"  1. Open: {obj.config.api_url.rstrip('/')}/issues/{issue_id}",
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
            "message": "Cannot delete issue via CLI for security reasons",
            "web_ui_url": f"{obj.config.api_url.rstrip('/')}/issues/{issue_id}",
            "reason": "AI assistant protection"
        }
        click.echo(json.dumps(error_data, indent=2, ensure_ascii=False))

    # 返回错误码
    raise SystemExit(1)



def _looks_like_issue_code(issue_id: str) -> bool:
    import re
    return (
        re.compile(r"^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$", re.IGNORECASE).match(issue_id)
        is not None
    )


async def _resolve_issue_id(client: OpenTaskClient, issue_id: str) -> tuple[str, dict]:
    """Return (uuid, issue_dict) resolving KEY-N / legacy codes."""
    by_code = _looks_like_issue_code(issue_id)
    issue = await client.get_issue(issue_id, by_code=by_code)
    return issue.get("id", issue_id), issue


@issue_cli.command(name="branch-name")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--copy", "do_copy", is_flag=True, help="Also print hint to copy (stdout is the name)")
@click.pass_obj
def issue_branch_name(obj: "Context", issue_id: str, as_json: bool, do_copy: bool):
    """Suggest Linear-like git branch name for an Issue (same HTTP as FE).

    Examples:
        issue branch-name WAY-42
        issue branch-name WAY-42 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        real_id, _issue = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(client.get_issue_branch_name(real_id))
        if json_mode:
            click.echo(_format_json_response(success=True, data=data, message="branch-name"))
            return
        name = data.get("branchName") or data.get("branch_name") or ""
        click.echo(name)
        if do_copy:
            skin.hint(f"Copied suggestion: {name}")
    except APIError as e:
        _handle_error(skin, e, "Failed to get branch name", json_mode)
        sys.exit(1)


@issue_cli.command(name="link-branch")
@click.argument("issue_id")
@click.argument("branch_name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_link_branch(obj: "Context", issue_id: str, branch_name: str, as_json: bool):
    """Attach a branch name to an Issue via POST /vcs/links (same HTTP as FE).

    Examples:
        issue link-branch WAY-42 WAY-42-fix-login
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        real_id, _issue = asyncio.run(_resolve_issue_id(client, issue_id))
        row = asyncio.run(
            client.create_issue_vcs_link(
                real_id, kind="branch", branchName=branch_name, provider="manual"
            )
        )
        if json_mode:
            click.echo(_format_json_response(success=True, data=row, message="linked branch"))
            return
        skin.success(f"Linked branch {branch_name} → {row.get('id', '')}")
    except APIError as e:
        _handle_error(skin, e, "Failed to link branch", json_mode)
        sys.exit(1)


@issue_cli.command(name="link-pr")
@click.argument("issue_id")
@click.argument("pr_url")
@click.option("--status", default="open", help="PR status: open|draft|merged|closed")
@click.option("--title", default=None, help="Optional PR title cache")
@click.option("--provider", default="github", help="Provider: github|gitlab|gitea|manual")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_link_pr(
    obj: "Context",
    issue_id: str,
    pr_url: str,
    status: str,
    title: str | None,
    provider: str,
    as_json: bool,
):
    """Attach a pull request URL to an Issue via POST /vcs/links (same HTTP as FE).

    Examples:
        issue link-pr WAY-42 https://github.com/org/repo/pull/12
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        real_id, _issue = asyncio.run(_resolve_issue_id(client, issue_id))
        kwargs = {
            "kind": "pull_request",
            "prUrl": pr_url,
            "provider": provider,
            "status": status,
        }
        if title:
            kwargs["title"] = title
        row = asyncio.run(client.create_issue_vcs_link(real_id, **kwargs))
        if json_mode:
            click.echo(_format_json_response(success=True, data=row, message="linked pr"))
            return
        skin.success(f"Linked PR {pr_url} → {row.get('id', '')}")
    except APIError as e:
        _handle_error(skin, e, "Failed to link PR", json_mode)
        sys.exit(1)


@issue_cli.command(name="vcs-links")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_vcs_links(obj: "Context", issue_id: str, as_json: bool):
    """List VCS links on an Issue (same HTTP as FE)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        real_id, _issue = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(client.list_issue_vcs_links(real_id))
        if json_mode:
            click.echo(_format_json_response(success=True, data=data, message="vcs-links"))
            return
        rows = data.get("rows") or []
        if not rows:
            skin.info("No VCS links")
            return
        for r in rows:
            skin.info(
                f"{r.get('kind')}: {r.get('branchName') or r.get('prUrl')} [{r.get('status')}] id={r.get('id')}"
            )
    except APIError as e:
        _handle_error(skin, e, "Failed to list VCS links", json_mode)
        sys.exit(1)


@issue_cli.command(name="children")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_children(obj: "Context", issue_id: str, as_json: bool):
    """List direct child issues (sub-issues)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        real_id, _ = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(client.list_issue_children(real_id))
        if json_mode:
            click.echo(_format_json_response(success=True, data=data, message="children"))
            return
        rows = (data or {}).get("rows") or []
        if not rows:
            skin.info("No children")
            return
        skin.table(
            ["Code", "Title", "Status"],
            [[r.get("issue_code") or "", (r.get("title") or "")[:40], r.get("status") or ""] for r in rows],
        )
    except APIError as e:
        _handle_error(skin, e, "Failed to list children", json_mode)
        sys.exit(1)


@issue_cli.group(name="relation")
def relation_cli():
    """Issue relations (blocks / related / …)."""
    pass


@relation_cli.command(name="list")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def relation_list(obj: "Context", issue_id: str, as_json: bool):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        real_id, _ = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(client.list_issue_relations(real_id))
        if json_mode:
            click.echo(_format_json_response(success=True, data=data, message="relations"))
            return
        skin.section("Relations")
        click.echo(str(data))
    except APIError as e:
        _handle_error(skin, e, "Failed to list relations", json_mode)
        sys.exit(1)


@relation_cli.command(name="add")
@click.argument("issue_id")
@click.option("--target", required=True, help="Target issue id or KEY-N")
@click.option("--type", "relation_type", required=True, help="Relation type")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def relation_add(obj: "Context", issue_id: str, target: str, relation_type: str, as_json: bool):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        async def run():
            src, _ = await _resolve_issue_id(client, issue_id)
            tgt, _ = await _resolve_issue_id(client, target)
            return await client.add_issue_relation(src, tgt, relation_type)
        data = asyncio.run(run())
        if json_mode:
            click.echo(_format_json_response(success=True, data=data, message="relation added"))
            return
        skin.success("Relation added")
    except APIError as e:
        _handle_error(skin, e, "Failed to add relation", json_mode)
        sys.exit(1)


@relation_cli.command(name="remove")
@click.argument("issue_id")
@click.option("--target", required=True)
@click.option("--type", "relation_type", required=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def relation_remove(obj: "Context", issue_id: str, target: str, relation_type: str, as_json: bool):
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        async def run():
            src, _ = await _resolve_issue_id(client, issue_id)
            tgt, _ = await _resolve_issue_id(client, target)
            return await client.remove_issue_relation(src, tgt, relation_type)
        data = asyncio.run(run())
        if json_mode:
            click.echo(_format_json_response(success=True, data=data, message="relation removed"))
            return
        skin.success("Relation removed")
    except APIError as e:
        _handle_error(skin, e, "Failed to remove relation", json_mode)
        sys.exit(1)
