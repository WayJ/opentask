"""Issue management commands for OpenTask CLI."""
import re
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


@comment_cli.group(name="attachment")
def comment_attachment_cli():
    """E69: comment attachment commands (list/upload/download)."""
    pass


@issue_cli.group(name="document")
def document_cli():
    """Document management commands."""
    pass


@issue_cli.group(name="attachment")
def attachment_cli():
    """Issue attachment commands (E66 ACL / signed URL)."""
    pass


@issue_cli.group(name="link")
def link_cli():
    """E76: Issue external links (list/add/rm)."""
    pass


@issue_cli.group(name="parent")
def parent_cli():
    """E78: set or clear Issue parent (set-parent / promote-to-root)."""
    pass


@issue_cli.group(name="reaction")
def reaction_cli():
    """E94: Issue emoji reactions (list/add/remove)."""
    pass


@issue_cli.group(name="comment-reaction")
def comment_reaction_cli():
    """E94: Comment emoji reactions (list/add/remove)."""
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

    pos = issue.get("position")
    skin.status_block({
        "ID": issue.get("id", ""),
        "Code": issue.get("issue_code", "N/A"),
        "Title": issue.get("title", ""),
        "Type": issue.get("type", "N/A"),
        "Status": issue.get("status", "N/A"),
        "Priority": issue.get("priority", "N/A"),
        "Position": pos if pos is not None else "—",
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
    # E71: Assignees list (primary marked)
    assignees = issue.get("assignees") or []
    if isinstance(assignees, list) and assignees:
        labels = []
        for i, a in enumerate(assignees):
            if not isinstance(a, dict):
                continue
            name = a.get("name") or a.get("sso_name") or a.get("id", "")
            labels.append(f"{name} (primary)" if i == 0 else str(name))
        skin.info("Assignees")
        skin.status_block({"Assignees": ", ".join(labels)})

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
    if issue.get("start_date"):
        dates["Start"] = issue["start_date"][:10]
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

    # E70: ChildProgress (omit when total==0 / missing)
    cp = issue.get("childProgress") or issue.get("child_progress")
    if isinstance(cp, dict) and cp.get("total"):
        pct = cp.get("percent")
        label = f"{cp.get('done', 0)}/{cp.get('total', 0)}"
        if pct is not None:
            label = f"{label} ({pct}%)"
        skin.info("ChildProgress")
        skin.status_block({"ChildProgress": label})

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
@click.option("--start-before", default=None, help="E73: start_date <= YYYY-MM-DD")
@click.option("--start-after", default=None, help="E73: start_date >= YYYY-MM-DD")
@click.option("--cycle", "cycle_id", default=None, help="E21: filter by cycle ID (__none__ = no cycle)")
@click.option("--milestone", "milestone_id", default=None, help="E81: filter by milestone ID (__none__ = no milestone)")
@click.option("--search", help="Search keyword")
@click.option("--open-only", is_flag=True, help="Show only open issues (shorthand for --status open)")
@click.option("--recent", is_flag=True, help="Show issues created in last 7 days")
@click.option("--updated-today", is_flag=True, help="Show issues updated today")
@click.option("--overdue", is_flag=True, help="Show overdue issues (due_date < today AND status IN (open, in_progress))")
@click.option("--unassigned", is_flag=True, help="Show unassigned issues")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=20, help="Page size")
@click.option("--sort-by", default="created_at", help="Sort field (E46: cf:<key> for CF/formula)")
@click.option("--sort-order", default="desc", help="Sort order (asc/desc)")
@click.option("--cf", multiple=True, help="E32/E43/E46: custom field filter key=value or key[gte]=8 (repeatable; formula keys match computed value)")
@click.option(
    "--group-by",
    "group_by",
    default=None,
    help="E37: client group key — none|status|assignee|priority|type|label|cf:<key>",
)
@click.option(
    "--include",
    "include",
    default=None,
    help="E25/E70: comma extras — custom_fields,childProgress",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_issues(obj: "Context", status, issue_type, priority, project_id, assignee_id, mine, watching, due_soon, start_before, start_after, cycle_id, milestone_id, search, open_only, recent, updated_today, overdue, unassigned, page, page_size, sort_by, sort_order, cf, group_by, include, as_json):
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

        # E37: group by custom field (client-side hint; loads custom_fields)
        issue list --group-by cf:severity
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

    # E37: validate --group-by (system enum or cf:<slug>)
    _GROUP_BY_OK = {"none", "status", "assignee", "priority", "type", "label"}
    _CF_GROUP_RE = re.compile(r"^cf:([a-z][a-z0-9_-]{0,63})$")
    if group_by is not None:
        gb = str(group_by).strip()
        if gb not in _GROUP_BY_OK and not _CF_GROUP_RE.match(gb):
            skin.error(
                "Invalid --group-by; use none|status|assignee|priority|type|label|cf:<key>"
            )
            return
        group_by = gb

    need_cf = bool(cf) or (isinstance(group_by, str) and group_by.startswith("cf:"))
    include_parts = [p.strip() for p in (include or "").split(",") if p.strip()]
    if need_cf and "custom_fields" not in include_parts:
        include_parts.append("custom_fields")
    include_arg = ",".join(include_parts) if include_parts else None

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
            start_before=start_before,
            start_after=start_after,
            cycle_id=cycle_id,
            milestone_id=milestone_id,
            cf=list(cf) if cf else None,
            include=include_arg,
        ))

        if json_mode:
            msg = f"Found {result.get('total', 0)} issue(s)"
            if group_by:
                msg = f"{msg}; group_by={group_by}"
                if isinstance(result, dict):
                    result = {**result, "group_by": group_by}
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=msg
            ))
            return

        rows = result.get("rows", [])
        total = result.get("total", 0)

        if not rows:
            skin.info("No issues found")
            return

        title = f"Issues ({total} total, Page {page})"
        if group_by:
            title = f"{title} · group_by={group_by}"
        skin.section(title)

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
@click.option("--sort-by", default="created_at", help="Sort field (E46: cf:<key> for CF/formula)")
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
@click.option("--assignees", default=None,
              help="E71: comma-separated assignee IDs (first=primary)")
@click.option("--estimate-points", type=float, default=None,
              help="Story points estimate (e.g. 1/2/3/5/8)")
@click.option("--start-date", default=None, help="E73: planned start date YYYY-MM-DD")
@click.option("--due-date", default=None, help="Due date YYYY-MM-DD")
@click.option("--milestone", "milestone_id", default=None, help="E81: set milestone_id")
@click.option("--template-id", "template_id", default=None, help="E82: apply issue template by id")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def create_issue(obj: "Context", title: str, description: str, issue_type: str, status: str, priority: str, project_id: str, assignee_id: str, assignees, estimate_points, start_date, due_date, milestone_id, template_id, verbose: bool, as_json: bool):
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
        assignee_ids = None
        if assignees:
            assignee_ids = [x.strip() for x in str(assignees).split(",") if x.strip()]
        result = asyncio.run(client.create_issue(
            title=title,
            description=description or "",
            type=issue_type,
            status=status,
            priority=priority,
            project_id=project_id,
            assignee_id=assignee_id,
            assignee_ids=assignee_ids,
            estimate_points=estimate_points,
            start_date=start_date,
            due_date=due_date,
            milestone_id=milestone_id,
            template_id=template_id,
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


@issue_cli.command(name="duplicate")
@click.argument("issue_id")
@click.option("--title", "-t", default=None, help="Override title (default: source + ' (copy)')")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def duplicate_issue_cmd(obj: "Context", issue_id: str, title: str | None, as_json: bool):
    """E75: Duplicate an issue (Linear-style copy). Prints new issue_code / id.

    Examples:
        opentask issue duplicate ISSUE-12
        opentask issue duplicate abc-uuid --title "New title" --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        result = asyncio.run(client.duplicate_issue(issue_id, title=title))
        # API may wrap in data
        if isinstance(result, dict) and "data" in result and isinstance(result["data"], dict):
            # some clients already unwrap; keep tolerant
            if "issue_code" not in result and "id" not in result:
                result = result["data"]
        code = result.get("issue_code") or result.get("issueCode") or ""
        new_id = result.get("id") or ""
        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Issue duplicated: {code or new_id}",
            ))
            return
        skin.success(f"[OK] Issue duplicated: {code or new_id}")
        skin.info(f"  id: {new_id}")
        if code:
            skin.info(f"  code: {code}")
        if result.get("title"):
            skin.info(f"  title: {result.get('title')}")
    except APIError as e:
        _handle_error(skin, e, "Failed to duplicate issue", json_mode=json_mode)


@issue_cli.command(name="update")
@click.argument("issue_id")
@click.option("--title", "-t", help="New title")
@click.option("--description", "-d", help="New description")
@click.option("--type", "-ty", "issue_type", type=click.Choice(["bug", "feature", "question", "feedback", "incident", "improvement"], case_sensitive=False), help="New issue type")
@click.option("--status", "-s", type=click.Choice(["open", "in_progress", "resolved", "closed"], case_sensitive=False), help="New status")
@click.option("--priority", "-p", type=click.Choice(["low", "medium", "high", "critical"], case_sensitive=False), help="New priority")
@click.option("--assignee", "-a", "assignee_id", help="New assignee user ID")
@click.option("--assignees", default=None,
              help="E71: comma-separated assignee IDs (first=primary; replaces set)")
@click.option("--reporter", "-r", "reporter_id", help="New reporter user ID")
@click.option("--estimate-points", type=float, default=None,
              help="Story points estimate (e.g. 1/2/3/5/8); omit to leave unchanged")
@click.option("--start-date", default=None, help="E73: planned start date YYYY-MM-DD (empty string clears)")
@click.option("--due-date", default=None, help="Due date YYYY-MM-DD (empty string clears)")
@click.option("--project", "project_id", default=None,
              help="E80: set project_id (empty string clears project)")
@click.option("--milestone", "milestone_id", default=None, help="E80: set milestone_id")
@click.option("--clear-milestone", is_flag=True, default=False,
              help="E80: clear milestone_id")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def update_issue(obj: "Context", issue_id: str, title, description, issue_type, status, priority, assignee_id, assignees, reporter_id, estimate_points, start_date, due_date, project_id, milestone_id, clear_milestone: bool, verbose: bool, as_json: bool):
    """Update an issue.

    Issue identifier format is auto-detected:
    - If KEY-N: treated as issue code (e.g., OT-1, WAY-42)
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

    if clear_milestone and milestone_id is not None:
        skin.error("--milestone and --clear-milestone are mutually exclusive")
        return

    # Auto-detect: check if it's an issue code (ISSUE + digits + hyphen + digits)
    import re
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
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
    if assignees is not None:
        kwargs["assignee_ids"] = [x.strip() for x in str(assignees).split(",") if x.strip()]
    elif assignee_id:
        kwargs["assignee_id"] = assignee_id
    if reporter_id:
        kwargs["reporter_id"] = reporter_id
    if estimate_points is not None:
        kwargs["estimate_points"] = estimate_points
    if start_date is not None:
        kwargs["start_date"] = start_date if start_date != "" else None
    if due_date is not None:
        kwargs["due_date"] = due_date if due_date != "" else None
    if project_id is not None:
        kwargs["project_id"] = project_id if project_id != "" else None
    if clear_milestone and milestone_id is not None:
        skin.error("--milestone and --clear-milestone are mutually exclusive")
        return
    if clear_milestone:
        kwargs["milestone_id"] = None
    elif milestone_id is not None:
        kwargs["milestone_id"] = milestone_id if milestone_id != "" else None

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
                "Project": issue.get("project_id") or "",
                "Milestone": issue.get("milestone_id") or "",
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
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)

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
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)

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
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)

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
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)

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
    - If KEY-N: treated as issue code (e.g., OT-1, WAY-42)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Examples:
        issue show OT-32                                # KEY-N (auto-detected)
        issue show OT-32                                # KEY-N
        issue show 5ee3420e-2d69-4509-9ae7-524e8c40d6d1 # Auto-detected as ID
        issue show OT-32 --json                         # JSON output
        issue show OT-32 --comments                      # Show full comments
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    import re
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
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
                skin.hint("Make sure the issue code is correct (e.g., OT-32 or WAY-42)")
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
    - If KEY-N: treated as issue code (e.g., OT-1, WAY-42)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Assignee formats:
    - User ID (UUID): Direct assignment
    - Username: Search by name or SSO account
    - 'me': Assign to current user
    - 'none': Unassign the issue

    Examples:
        issue assign ISSUE-ID --assignee jiangwei
        issue assign OT-32 -a me
        issue assign ISSUE-ID --assignee none
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code (ISSUE + digits + hyphen + digits)
    import re
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
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
    - If KEY-N: treated as issue code (e.g., OT-1, WAY-42)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Assignee formats:
    - User ID (UUID): Direct assignment
    - 'me': Assign to current user
    - 'none': Unassign the issues

    Examples:
        issue batch-assign ISSUE-ID1 ISSUE-ID2 ISSUE-ID3 --assignee me
        issue batch-assign OT-32 OT-33 -a jiangwei
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
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)

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
@click.option("--parent-id", "parent_id", default=None, help="Parent root comment ID (depth-1 reply)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def add_comment(obj: "Context", issue_id: str, content: str, message_content: str, parent_id: str | None, as_json: bool):
    """Add a comment to an issue.

    Issue identifier format is auto-detected:
    - If KEY-N: treated as issue code (e.g., OT-1, WAY-42)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Examples:
        issue comment add ISSUE-ID "This is a comment"
        issue comment add ISSUE-ID -m "Another comment"
        issue comment add ISSUE-ID "Reply text" --parent-id COMMENT-ID
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
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
    if issue_code_pattern.match(issue_id):
        # It's a code, need to get the real ID first
        try:
            issue_info = asyncio.run(client.get_issue(issue_id, by_code=True))
            issue_id = issue_info.get("id", issue_id)
        except APIError as e:
            skin.error(f"Failed to resolve issue code {issue_id}: {e.message}")
            return

    try:
        comment = asyncio.run(client.add_comment(issue_id, comment_text, parent_id=parent_id))

        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=comment,
                message=f"Comment added: {comment.get('id', '')[:8]}"
            ))
            return

        skin.success("Comment added successfully")

        skin.section("Comment Details")
        details = {
            "ID": comment.get("id", "")[:8],
            "Issue ID": comment.get("issue_id", "")[:8],
            "Content": comment_text[:50] + "..." if len(comment_text) > 50 else comment_text,
        }
        pid = comment.get("parent_id") or parent_id
        if pid:
            details["Parent"] = str(pid)[:8]
        skin.status_block(details)

    except APIError as e:
        skin.error(f"Failed to add comment: {e.message}")


@comment_cli.command(name="list")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_comments(obj: "Context", issue_id: str, as_json: bool):
    """List all comments for an issue.

    Issue identifier format is auto-detected:
    - If KEY-N: treated as issue code (e.g., OT-1, WAY-42)
    - Otherwise: treated as UUID ID (e.g., 5ee3420e-2d69-4509-9ae7-524e8c40d6d1)

    Examples:
        issue comment list ISSUE-ID
        issue comment list OT-32 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
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
            parent = comment.get("parent_id")
            if parent:
                click.echo(f"Parent: {str(parent)[:8]}")
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


# ============================================================================
# E94: issue reaction + comment-reaction
# ============================================================================


def _resolve_issue_arg(client: OpenTaskClient, issue_id: str) -> str:
    """Resolve KEY-N / UUID issue id for reaction commands."""
    if _looks_like_issue_code(issue_id):
        real_id, _info = asyncio.run(_resolve_issue_id(client, issue_id))
        return real_id
    return issue_id


@reaction_cli.command(name="list")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def reaction_list(obj: "Context", issue_id: str, as_json: bool):
    """List emoji reactions on an Issue."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        real_id = _resolve_issue_arg(client, issue_id)
        data = asyncio.run(client.list_issue_reactions(real_id))
        body = data if isinstance(data, dict) else {"rows": data or [], "total": 0}
        rows = body.get("rows") or []
        if not isinstance(rows, list):
            rows = []
        if json_mode:
            echo_json(True, data=body, message=f"Found {body.get('total', len(rows))} reaction(s)")
            return
        if not rows:
            skin.info("无反应")
            return
        skin.table(
            ["Emoji", "Count"],
            [[str(r.get("emoji", "")), str(r.get("count", ""))] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@reaction_cli.command(name="add")
@click.argument("issue_id")
@click.option("--emoji", required=True, help="Emoji to add")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def reaction_add(obj: "Context", issue_id: str, emoji: str, as_json: bool):
    """Add an emoji reaction to an Issue."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        real_id = _resolve_issue_arg(client, issue_id)
        data = asyncio.run(client.add_issue_reaction(real_id, emoji))
        body = data if isinstance(data, dict) else {"reaction_id": data}
        if json_mode:
            echo_json(True, data=body, message=f"Added reaction {emoji}")
            return
        rid = (body or {}).get("reaction_id", "")
        skin.success(f"已添加反应 {emoji}" + (f" ({str(rid)[:8]})" if rid else ""))
    except APIError as e:
        handle_api_error(e, json_mode)


@reaction_cli.command(name="remove")
@click.argument("issue_id")
@click.option("--emoji", required=True, help="Emoji to remove")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def reaction_remove(obj: "Context", issue_id: str, emoji: str, as_json: bool):
    """Remove an emoji reaction from an Issue."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        real_id = _resolve_issue_arg(client, issue_id)
        data = asyncio.run(client.remove_issue_reaction(real_id, emoji))
        if json_mode:
            echo_json(True, data=data or {"emoji": emoji, "issue_id": real_id}, message=f"Removed reaction {emoji}")
            return
        skin.success(f"已移除反应 {emoji}")
    except APIError as e:
        handle_api_error(e, json_mode)


# optional alias: reaction rm
reaction_cli.add_command(reaction_remove, name="rm")


@comment_reaction_cli.command(name="list")
@click.argument("issue_id")
@click.argument("comment_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def comment_reaction_list(obj: "Context", issue_id: str, comment_id: str, as_json: bool):
    """List emoji reactions on an Issue comment."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        real_id = _resolve_issue_arg(client, issue_id)
        data = asyncio.run(client.list_comment_reactions(real_id, comment_id))
        body = data if isinstance(data, dict) else {"reactions": data or {}}
        reactions = body.get("reactions") or {}
        if not isinstance(reactions, dict):
            reactions = {}
        if json_mode:
            echo_json(True, data=body, message=f"Found {len(reactions)} emoji(s)")
            return
        if not reactions:
            skin.info("无反应")
            return
        skin.table(
            ["Emoji", "UserIds"],
            [
                [str(emoji), ",".join(str(u)[:8] for u in (uids or []))]
                for emoji, uids in reactions.items()
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@comment_reaction_cli.command(name="add")
@click.argument("issue_id")
@click.argument("comment_id")
@click.option("--emoji", required=True, help="Emoji to add")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def comment_reaction_add(
    obj: "Context", issue_id: str, comment_id: str, emoji: str, as_json: bool
):
    """Add an emoji reaction to an Issue comment."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        real_id = _resolve_issue_arg(client, issue_id)
        data = asyncio.run(client.add_comment_reaction(real_id, comment_id, emoji))
        body = data if isinstance(data, dict) else {"reaction_id": data}
        if json_mode:
            echo_json(True, data=body, message=f"Added comment reaction {emoji}")
            return
        rid = (body or {}).get("reaction_id", "")
        skin.success(f"已添加评论反应 {emoji}" + (f" ({str(rid)[:8]})" if rid else ""))
    except APIError as e:
        handle_api_error(e, json_mode)


@comment_reaction_cli.command(name="remove")
@click.argument("issue_id")
@click.argument("comment_id")
@click.option("--emoji", required=True, help="Emoji to remove")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def comment_reaction_remove(
    obj: "Context", issue_id: str, comment_id: str, emoji: str, as_json: bool
):
    """Remove an emoji reaction from an Issue comment."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    try:
        real_id = _resolve_issue_arg(client, issue_id)
        data = asyncio.run(client.remove_comment_reaction(real_id, comment_id, emoji))
        if json_mode:
            echo_json(
                True,
                data=data or {"emoji": emoji, "issue_id": real_id, "comment_id": comment_id},
                message=f"Removed comment reaction {emoji}",
            )
            return
        skin.success(f"已移除评论反应 {emoji}")
    except APIError as e:
        handle_api_error(e, json_mode)


comment_reaction_cli.add_command(comment_reaction_remove, name="rm")


# ============================================================================
# E69: issue comment attachment
# ============================================================================

@comment_attachment_cli.command(name="list")
@click.argument("issue_id")
@click.argument("comment_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_comment_attachments(obj: "Context", issue_id: str, comment_id: str, as_json: bool):
    """List attachments on an issue comment."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        real_issue_id = issue_id
        import re
        issue_code_pattern = re.compile(
            r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE
        )
        if issue_code_pattern.match(issue_id):
            info = asyncio.run(client.get_issue(issue_id, by_code=True))
            real_issue_id = info.get("id", issue_id)
        rows = asyncio.run(client.list_comment_attachments(real_issue_id, comment_id))
        if not isinstance(rows, list):
            rows = rows or []
        if json_mode:
            echo_json(data={"attachments": rows, "total": len(rows)}, message=f"Found {len(rows)} attachment(s)")
            return
        if not rows:
            skin.info("No attachments")
            return
        for row in rows:
            skin.info(f"{row.get('id')}  {row.get('file_name')}  ({row.get('file_size')} bytes)")
    except APIError as e:
        _handle_error(skin, e, "Failed to list comment attachments", json_mode)
        sys.exit(1)


@comment_attachment_cli.command(name="upload")
@click.argument("issue_id")
@click.argument("comment_id")
@click.option("--file", "file_path", required=True, type=click.Path(exists=True), help="Local file to upload")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def upload_comment_attachment_cmd(obj: "Context", issue_id: str, comment_id: str, file_path: str, as_json: bool):
    """Upload a file onto an issue comment."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        real_issue_id = issue_id
        import re
        issue_code_pattern = re.compile(
            r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE
        )
        if issue_code_pattern.match(issue_id):
            info = asyncio.run(client.get_issue(issue_id, by_code=True))
            real_issue_id = info.get("id", issue_id)
        result = asyncio.run(client.upload_comment_attachment(real_issue_id, comment_id, file_path))
        if json_mode:
            echo_json(data=result, message="Comment attachment uploaded")
            return
        skin.success(f"Uploaded: {result.get('file_name') or result.get('id')}")
    except APIError as e:
        _handle_error(skin, e, "Failed to upload comment attachment", json_mode)
        sys.exit(1)


@comment_attachment_cli.command(name="download")
@click.argument("issue_id")
@click.argument("comment_id")
@click.argument("attachment_id")
@click.option("--out", "out_path", default=".", help="Output file or directory")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def download_comment_attachment_cmd(
    obj: "Context",
    issue_id: str,
    comment_id: str,
    attachment_id: str,
    out_path: str,
    as_json: bool,
):
    """Download a comment attachment (authenticated session; E66 ACL)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        real_issue_id = issue_id
        import re
        issue_code_pattern = re.compile(
            r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE
        )
        if issue_code_pattern.match(issue_id):
            info = asyncio.run(client.get_issue(issue_id, by_code=True))
            real_issue_id = info.get("id", issue_id)
        saved = asyncio.run(
            client.download_comment_attachment(real_issue_id, comment_id, attachment_id, out_path)
        )
        if json_mode:
            echo_json(
                data={
                    "path": saved,
                    "attachment_id": attachment_id,
                    "issue_id": real_issue_id,
                    "comment_id": comment_id,
                },
                message=f"Attachment downloaded to: {saved}",
            )
            return
        import os
        skin.success(f"Attachment downloaded: {os.path.basename(saved)}")
        skin.hint(f"Saved to: {saved}")
    except APIError as e:
        _handle_error(skin, e, "Failed to download comment attachment", json_mode)
        sys.exit(1)


@document_cli.command(name="list")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_documents(obj: "Context", issue_id: str, as_json: bool):
    """List issue documents (attachments).

    Supports both KEY-N issue codes (OT-32) and UUIDs.

    Examples:
        issue document list ISSUE-ID
        issue document list OT-32 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
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

    Supports both KEY-N issue codes (OT-32) and UUIDs.

    Examples:
        issue document upload ISSUE-ID /path/to/file.pdf
        issue document upload ISSUE-ID report.pdf --description "Weekly report"
        issue document upload OT-32 design.png --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    import os
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
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

    Supports both KEY-N issue codes (OT-32) and UUIDs for issue_id.

    Examples:
        issue document delete ISSUE-ID DOCUMENT-ID
        issue document delete OT-32 abc123 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
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

    Supports both KEY-N issue codes (OT-32) and UUIDs for issue_id.

    If save_path is a directory, the original filename will be used.
    If save_path is a file path, the file will be saved to that path.

    Examples:
        issue document download ISSUE-ID DOCUMENT-ID ./downloads/
        issue document download ISSUE-ID abc123 /path/to/save.pdf
        issue document download OT-32 abc123 . --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    import os
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
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

    Supports both KEY-N issue codes (OT-32) and UUIDs for issue_id.

    All documents will be saved to the specified directory with their original filenames.

    Examples:
        issue document download-all ISSUE-ID ./downloads/
        issue document download-all OT-32 /path/to/downloads
        issue document download-all ISSUE-ID . --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    json_mode = as_json or obj.json_mode

    # Auto-detect: check if it's an issue code
    import re
    import os
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
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


# ============================================================================
# E66: issue attachment (ACL download + signed-url)
# ============================================================================

@attachment_cli.command(name="download")
@click.argument("issue_id")
@click.argument("attachment_id")
@click.option("--out", "out_path", default=".", help="Output file or directory")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def download_attachment(obj: "Context", issue_id: str, attachment_id: str, out_path: str, as_json: bool):
    """Download an issue attachment (authenticated session; E66).

    Examples:
        issue attachment download ISSUE-ID ATTACHMENT-ID ./downloads/
        issue attachment download OT-1 abc123 ./file.bin --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        real_issue_id = issue_id
        import re
        issue_code_pattern = re.compile(
            r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE
        )
        if issue_code_pattern.match(issue_id):
            info = asyncio.run(client.get_issue(issue_id, by_code=True))
            real_issue_id = info.get("id", issue_id)

        saved_path = asyncio.run(
            client.download_issue_document(real_issue_id, attachment_id, out_path)
        )
        if json_mode:
            echo_json(
                data={"path": saved_path, "attachment_id": attachment_id, "issue_id": real_issue_id},
                message=f"Attachment downloaded to: {saved_path}",
            )
            return
        import os
        skin.success(f"Attachment downloaded: {os.path.basename(saved_path)}")
        skin.hint(f"Saved to: {saved_path}")
    except APIError as e:
        _handle_error(skin, e, "Failed to download attachment", json_mode)
        sys.exit(1)


@attachment_cli.command(name="signed-url")
@click.argument("issue_id")
@click.argument("attachment_id")
@click.option("--purpose", type=click.Choice(["preview", "download"]), default="preview")
@click.option("--ttl", "ttl_seconds", type=int, default=None, help="TTL seconds (default 900, max 3600)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def attachment_signed_url(
    obj: "Context",
    issue_id: str,
    attachment_id: str,
    purpose: str,
    ttl_seconds: int | None,
    as_json: bool,
):
    """Mint a short-TTL signed URL for an attachment (debug / FE preview; E66)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        # issue_id accepted for CLI symmetry; signed-url is attachment-scoped
        _ = issue_id
        result = asyncio.run(
            client.create_attachment_signed_url(
                attachment_id, purpose=purpose, ttl_seconds=ttl_seconds
            )
        )
        if json_mode:
            echo_json(data=result, message="Signed URL created")
            return
        skin.success("Signed URL created")
        skin.hint(f"url: {result.get('url')}")
        skin.hint(f"expiresAt: {result.get('expiresAt')}")
    except APIError as e:
        _handle_error(skin, e, "Failed to create signed URL", json_mode)
        sys.exit(1)


@issue_cli.command(name="board-move")
@click.argument("issue_id")
@click.option(
    "--status",
    required=True,
    type=click.Choice(
        ["open", "in_progress", "feedback", "resolved", "closed", "rejected"],
        case_sensitive=False,
    ),
    help="Target board column / IssueStatus",
)
@click.option(
    "--position",
    required=True,
    type=int,
    help="0-based position in target column",
)
@click.option(
    "--ordered-ids",
    "ordered_ids_csv",
    default=None,
    help="Optional CSV of issue ids rewriting target column order",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def board_move_issue(
    obj: "Context",
    issue_id: str,
    status: str,
    position: int,
    ordered_ids_csv: str | None,
    as_json: bool,
):
    """E91: Atomically move an Issue on the board (status + position; optional ordered_ids).

    Examples:
        opentask issue board-move ISSUE-12 --status in_progress --position 3
        opentask issue board-move <uuid> --status open --position 0 --ordered-ids a,b,c --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        sys.exit(1)

    if position < 0:
        msg = "--position must be >= 0"
        if json_mode:
            click.echo(_format_json_response(success=False, error=msg, message=msg))
        else:
            skin.error(msg)
        sys.exit(1)

    ordered: list[str] | None = None
    if ordered_ids_csv is not None:
        ordered = [p.strip() for p in str(ordered_ids_csv).split(",") if p.strip()]

    try:
        if _looks_like_issue_code(issue_id):
            real_id, _info = asyncio.run(_resolve_issue_id(client, issue_id))
        else:
            real_id = issue_id
        data = asyncio.run(
            client.move_issue_on_board(
                real_id,
                status.lower(),
                position,
                ordered_ids=ordered,
            )
        )
        body = data.get("data", data) if isinstance(data, dict) else data
        if json_mode:
            click.echo(
                _format_json_response(
                    success=True,
                    data=body,
                    message="Issue 看板位置已更新",
                )
            )
            return
        skin.success("Issue 看板位置已更新")
        if isinstance(body, dict):
            skin.hint(f"status: {body.get('status', status)}")
            skin.hint(f"position: {body.get('position', position)}")
    except APIError as e:
        _handle_error(skin, e, "Failed to board-move issue", json_mode)


@issue_cli.command(name="bulk-update")
@click.option("--ids", required=True, help="Comma-separated issue IDs / KEY-N")
@click.option("--status", default=None, help="New status")
@click.option("--priority", default=None, help="New priority")
@click.option("--assignee", default=None, help="Assignee user id / me / none")
@click.option("--cycle-id", default=None, help="Cycle id")
@click.option("--tag-ids", default=None, help="Comma-separated tag ids (replace)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def bulk_update_issues(obj: "Context", ids: str, status, priority, assignee, cycle_id, tag_ids, as_json):
    """E20: Bulk update issues in current workspace (status/priority/assignee/cycle/tags)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        sys.exit(1)

    import re
    issue_code_pattern = re.compile(r'^[A-Za-z][A-Za-z0-9]{1,5}-\d+$', re.IGNORECASE)
    raw_ids = [x.strip() for x in ids.split(',') if x.strip()]
    resolved = []
    for iid in raw_ids:
        if issue_code_pattern.match(iid):
            try:
                info = asyncio.run(client.get_issue(iid, by_code=True))
                resolved.append(info.get('id', iid))
            except APIError as e:
                _handle_error(skin, e, f"Failed to resolve {iid}", json_mode)
                return
        else:
            resolved.append(iid)

    payload = {"issue_ids": resolved}
    if status:
        payload["status"] = status
    if priority:
        payload["priority"] = priority
    if cycle_id:
        payload["cycle_id"] = cycle_id
    if tag_ids is not None and tag_ids != "":
        payload["tag_ids"] = [int(x.strip()) for x in tag_ids.split(',') if x.strip()]
    if assignee is not None:
        aid = _resolve_user_id(skin, client, assignee)
        if aid == "CANCELLED":
            return
        payload["assignee_id"] = aid

    if len(payload) == 1:
        skin.error("Specify at least one of --status/--priority/--assignee/--cycle-id/--tag-ids")
        sys.exit(1)

    try:
        data = asyncio.run(client.bulk_update_issues(payload))
        body = data.get("data", data) if isinstance(data, dict) else data
        if json_mode:
            click.echo(_format_json_response(success=True, data=body, message="bulk updated"))
        else:
            skin.success(f"Bulk updated: {body}")
    except APIError as e:
        _handle_error(skin, e, "Failed to bulk update", json_mode)



@issue_cli.command(name="trash")
@click.option("--limit", "-n", default=20, show_default=True, help="Max rows to show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_trash_cmd(obj: "Context", limit: int, as_json: bool):
    """E77: List soft-deleted Issues in the current workspace.

    Soft-delete happens via Web UI / API; use `issue restore` to undelete.
    CLI `issue delete` remains disabled for safety.

    Examples:
        opentask issue trash
        opentask issue trash --limit 50 --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        page_size = max(1, min(100, int(limit or 20)))
        data = asyncio.run(client.list_issue_trash(page=1, page_size=page_size))
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            if "rows" not in data:
                data = data["data"]
        rows = data.get("rows") if isinstance(data, dict) else data
        rows = rows or []
        total = data.get("total", len(rows)) if isinstance(data, dict) else len(rows)
        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data={"rows": rows, "total": total},
                message=f"trash: {total}",
            ))
            return
        if not rows:
            skin.info("Trash is empty")
            return
        skin.info(f"Trash ({total}):")
        for r in rows:
            code = r.get("issue_code") or r.get("issueCode") or ""
            title = r.get("title") or ""
            rid = r.get("id") or ""
            skin.info(f"  {code or rid}  {title}")
    except APIError as e:
        _handle_error(skin, e, "Failed to list trash", json_mode)
        sys.exit(1)


@issue_cli.command(name="restore")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_restore_cmd(obj: "Context", issue_id: str, as_json: bool):
    """E77: Restore a soft-deleted Issue (member+). Idempotent if already live.

    Examples:
        opentask issue restore WAY-12
        opentask issue restore <uuid> --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        real_id = issue_id
        if _looks_like_issue_code(issue_id):
            issue = asyncio.run(
                client.get_issue(issue_id, by_code=True, include_deleted=True)
            )
            if isinstance(issue, dict) and "data" in issue and isinstance(issue["data"], dict):
                if "id" not in issue:
                    issue = issue["data"]
            real_id = issue.get("id", issue_id)
        result = asyncio.run(client.restore_issue(real_id))
        if isinstance(result, dict) and "data" in result and isinstance(result["data"], dict):
            if "id" not in result and "issue_code" not in result:
                result = result["data"]
        code = result.get("issue_code") or result.get("issueCode") or ""
        rid = result.get("id") or real_id
        if json_mode:
            click.echo(_format_json_response(
                success=True,
                data=result,
                message=f"Issue restored: {code or rid}",
            ))
            return
        skin.success(f"[OK] Issue restored: {code or rid}")
        if code:
            skin.info(f"  code: {code}")
        skin.info(f"  id: {rid}")
    except APIError as e:
        _handle_error(skin, e, "Failed to restore issue", json_mode)
        sys.exit(1)


@issue_cli.command(name="delete")
@click.argument("issue_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def delete_issue(obj: "Context", issue_id: str, force: bool, as_json: bool):
    """Delete an issue (SECURITY: Not allowed via CLI).

    Soft-delete via Web UI / API; recover with `opentask issue restore`.
    CLI delete stays disabled to protect against accidental AI deletions.

    Examples:
        issue delete ISSUE-ID
        issue delete OT-1
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
        "Please use the Web UI / API to soft-delete, then `opentask issue restore` to undelete.",
        f"  Web: {obj.config.api_url.rstrip('/')}/issues/{issue_id}",
        "  Or: opentask issue trash  /  opentask issue restore <id|code>",
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
        re.compile(r"^[A-Za-z][A-Za-z0-9]{1,5}-\d+$", re.IGNORECASE).match(issue_id)
        is not None
    )


async def _resolve_issue_id(client: OpenTaskClient, issue_id: str) -> tuple[str, dict]:
    """Return (uuid, issue_dict) resolving KEY-N codes."""
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


@issue_cli.command(name="unlink-vcs")
@click.argument("issue_id")
@click.argument("link_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_unlink_vcs(obj: "Context", issue_id: str, link_id: str, as_json: bool):
    """E97: Unlink a VCS link from an Issue (DELETE …/vcs/links/{link_id}).

    Examples:
        issue unlink-vcs WAY-42 <link-id>
        issue vcs-unlink WAY-42 <link-id> --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    try:
        real_id, _issue = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(client.delete_issue_vcs_link(real_id, link_id))
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            if "id" not in data:
                data = data["data"]
        row = data if isinstance(data, dict) else {"id": link_id}
        if json_mode:
            click.echo(_format_json_response(success=True, data=row, message="unlinked vcs"))
            return
        kind = row.get("kind") or ""
        status = row.get("status") or ""
        ref = row.get("prUrl") or row.get("branchName") or ""
        extra = " ".join(p for p in (kind, status, ref) if p)
        if extra:
            skin.success(f"Unlinked VCS link {row.get('id', link_id)} [{extra}]")
        else:
            skin.success(f"Unlinked VCS link {row.get('id', link_id)}")
    except APIError as e:
        _handle_error(skin, e, "Failed to unlink VCS link", json_mode)
        sys.exit(1)


issue_cli.add_command(issue_unlink_vcs, name="vcs-unlink")


@issue_cli.command(name="update-vcs")
@click.argument("issue_id")
@click.argument("link_id")
@click.option("--status", default=None, help="PR/link status: open|draft|merged|closed|unknown")
@click.option("--title", default=None, help="Cached title")
@click.option("--pr-url", "pr_url", default=None, help="Pull request URL")
@click.option("--branch-name", "branch_name", default=None, help="Branch name")
@click.option("--provider", default=None, help="Provider: github|gitlab|gitea|manual")
@click.option("--external-id", "external_id", default=None, help="External id on provider")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_update_vcs(
    obj: "Context",
    issue_id: str,
    link_id: str,
    status: str | None,
    title: str | None,
    pr_url: str | None,
    branch_name: str | None,
    provider: str | None,
    external_id: str | None,
    as_json: bool,
):
    """E97: Update a VCS link on an Issue (PATCH …/vcs/links/{link_id}).

    At least one field flag is required (empty PATCH rejected locally).

    Examples:
        issue update-vcs WAY-42 <link-id> --status merged
        issue update-vcs WAY-42 <link-id> --status closed --title "Ship" --pr-url https://…
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode

    fields: dict = {}
    if status is not None:
        fields["status"] = status
    if title is not None:
        fields["title"] = title
    if pr_url is not None:
        fields["prUrl"] = pr_url
    if branch_name is not None:
        fields["branchName"] = branch_name
    if provider is not None:
        fields["provider"] = provider
    if external_id is not None:
        fields["externalId"] = external_id

    if not fields:
        msg = (
            "Provide at least one of "
            "--status/--title/--pr-url/--branch-name/--provider/--external-id"
        )
        if json_mode:
            click.echo(_format_json_response(success=False, error=msg, message=msg))
            sys.exit(1)
        skin.error(msg)
        sys.exit(1)

    try:
        real_id, _issue = asyncio.run(_resolve_issue_id(client, issue_id))
        row = asyncio.run(client.update_issue_vcs_link(real_id, link_id, **fields))
        if isinstance(row, dict) and "data" in row and isinstance(row["data"], dict):
            if "id" not in row:
                row = row["data"]
        if json_mode:
            click.echo(_format_json_response(success=True, data=row, message="updated vcs"))
            return
        rid = (row or {}).get("id", link_id)
        kind = (row or {}).get("kind") or ""
        st = (row or {}).get("status") or ""
        ref = (row or {}).get("prUrl") or (row or {}).get("branchName") or ""
        bits = [b for b in (kind, st, ref) if b]
        if bits:
            skin.success(f"Updated VCS link {rid} [{' '.join(bits)}]")
        else:
            skin.success(f"Updated VCS link {rid}")
    except APIError as e:
        _handle_error(skin, e, "Failed to update VCS link", json_mode)
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




@link_cli.command(name="list")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_link_list(obj: "Context", issue_id: str, as_json: bool):
    """List external links on an Issue (E76)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        real_id, _ = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(client.list_issue_links(real_id))
        if json_mode:
            click.echo(_format_json_response(success=True, data=data, message="links"))
            return
        rows = (data or {}).get("rows") or []
        if not rows:
            skin.info("No links")
            return
        skin.table(
            ["Id", "Title", "URL", "Pos"],
            [
                [
                    r.get("id") or "",
                    (r.get("title") or "")[:30],
                    (r.get("url") or "")[:50],
                    str(r.get("position", "")),
                ]
                for r in rows
            ],
        )
    except APIError as e:
        _handle_error(skin, e, "Failed to list links", json_mode)
        sys.exit(1)


@link_cli.command(name="add")
@click.argument("issue_id")
@click.argument("url")
@click.option("--title", default=None, help="Optional display title")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_link_add(obj: "Context", issue_id: str, url: str, title: str | None, as_json: bool):
    """Add an http(s) external link to an Issue (E76)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        real_id, _ = asyncio.run(_resolve_issue_id(client, issue_id))
        row = asyncio.run(client.create_issue_link(real_id, url, title=title))
        if isinstance(row, dict) and "data" in row and isinstance(row["data"], dict):
            if "id" not in row:
                row = row["data"]
        if json_mode:
            click.echo(_format_json_response(success=True, data=row, message="link added"))
            return
        skin.success(f"Added link {row.get('id', '')}")
        skin.info(f"  url: {row.get('url')}")
        if row.get("title"):
            skin.info(f"  title: {row.get('title')}")
    except APIError as e:
        _handle_error(skin, e, "Failed to add link", json_mode)
        sys.exit(1)


@link_cli.command(name="rm")
@click.argument("issue_id")
@click.argument("link_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_link_rm(obj: "Context", issue_id: str, link_id: str, as_json: bool):
    """Remove an external link from an Issue (E76)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        real_id, _ = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(client.delete_issue_link(real_id, link_id))
        if json_mode:
            click.echo(_format_json_response(success=True, data=data or {"id": link_id}, message="link removed"))
            return
        skin.success(f"Removed link {link_id}")
    except APIError as e:
        _handle_error(skin, e, "Failed to remove link", json_mode)
        sys.exit(1)


@link_cli.command(name="update")
@click.argument("issue_id")
@click.argument("link_id")
@click.option("--url", default=None, help="New URL")
@click.option("--title", default=None, help="New title")
@click.option("--position", type=int, default=None, help="New position")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_link_update(
    obj: "Context",
    issue_id: str,
    link_id: str,
    url: str | None,
    title: str | None,
    position: int | None,
    as_json: bool,
):
    """Update an Issue external link (E76 optional)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if url is None and title is None and position is None:
        skin.error("Provide at least one of --url / --title / --position")
        sys.exit(1)
    try:
        real_id, _ = asyncio.run(_resolve_issue_id(client, issue_id))
        row = asyncio.run(
            client.update_issue_link(
                real_id, link_id, url=url, title=title, position=position
            )
        )
        if isinstance(row, dict) and "data" in row and isinstance(row["data"], dict):
            if "id" not in row:
                row = row["data"]
        if json_mode:
            click.echo(_format_json_response(success=True, data=row, message="link updated"))
            return
        skin.success(f"Updated link {row.get('id', link_id)}")
    except APIError as e:
        _handle_error(skin, e, "Failed to update link", json_mode)
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


@issue_cli.command(name="set-field")
@click.argument("issue_id")
@click.argument("key")
@click.argument("value")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def set_issue_field(obj: "Context", issue_id: str, key: str, value: str, as_json: bool):
    """设置 Issue 自定义字段取值（E25）。

    VALUE 解析：
    - true/false → boolean
    - 纯数字 → number
    - YYYY-MM-DD → date/text 原样
    - 含逗号 → multi_select 数组
    - 否则 text / single_select 字符串
    - 字面量 null / ~ → 清除
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        sys.exit(1)

    raw = value.strip()
    if raw.lower() in ("null", "~", ""):
        parsed = None
    elif raw.lower() in ("true", "false"):
        parsed = raw.lower() == "true"
    elif "," in raw:
        parsed = [x.strip() for x in raw.split(",") if x.strip()]
    else:
        try:
            if "." in raw:
                parsed = float(raw)
            else:
                parsed = int(raw)
        except ValueError:
            parsed = raw

    try:
        real_id, _info = asyncio.run(_resolve_issue_id(client, issue_id))
        data = asyncio.run(
            client.set_issue_custom_fields(real_id, [{"key": key, "value": parsed}])
        )
        body = data.get("data", data) if isinstance(data, dict) else data
        if json_mode:
            click.echo(_format_json_response(success=True, data=body, message="field set"))
            return
        skin.success(f"已设置 {key}={parsed!r} on {issue_id}")
    except APIError as e:
        _handle_error(skin, e, "Failed to set field", json_mode)
        sys.exit(1)


@issue_cli.command(name="export")
@click.option("--out", "out_path", default=None, help="Write CSV to file (default: stdout)")
@click.option("--status", "-s", default=None, help="Filter by status")
@click.option("--priority", "-p", default=None, help="Filter by priority")
@click.option("--project", "-P", "project_id", default=None, help="Filter by project ID")
@click.option("--assignee", "-a", "assignee_id", default=None, help="Filter by assignee (me allowed)")
@click.option("--cycle", "cycle_id", default=None, help="Filter by cycle ID")
@click.option("--search", default=None, help="Search keyword")
@click.option("--json", "as_json", is_flag=True, help="JSON wrapper (meta only; body still CSV unless --out)")
@click.pass_obj
def export_issues(obj, out_path, status, priority, project_id, assignee_id, cycle_id, search, as_json):
    """E28/E34: Export workspace issues as CSV (includes cf.<key> custom field columns)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        sys.exit(1)

    params = {}
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if project_id:
        params["project_id"] = project_id
    if assignee_id:
        params["assignee_id"] = assignee_id
    if cycle_id:
        params["cycle_id"] = cycle_id
    if search:
        params["search"] = search

    try:
        content = asyncio.run(client.export_issues_csv(params))
        text = content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else str(content)
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            if json_mode:
                click.echo(_format_json_response(success=True, data={"out": out_path, "bytes": len(content)}, message="exported"))
            else:
                skin.success(f"Exported to {out_path}")
        else:
            click.echo(text, nl=False if text.endswith("\n") else True)
    except APIError as e:
        _handle_error(skin, e, "Failed to export issues", json_mode)
        sys.exit(1)


@issue_cli.command(name="import")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def import_issues(obj, file_path, as_json):
    """E28/E34: Import issues from CSV (upsert by issue_code; cf.<key> columns supported)."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        sys.exit(1)

    try:
        data = asyncio.run(client.import_issues_csv(file_path))
        body = data.get("data", data) if isinstance(data, dict) else data
        if json_mode:
            click.echo(_format_json_response(success=True, data=body, message="imported"))
            return
        created = body.get("created", 0) if isinstance(body, dict) else 0
        updated = body.get("updated", 0) if isinstance(body, dict) else 0
        errors = body.get("errors", []) if isinstance(body, dict) else []
        skin.success(f"Import done: created={created} updated={updated} errors={len(errors)}")
        for err in (errors or [])[:10]:
            skin.warn(f"  row {err.get('row')}: {err.get('message')}")
    except APIError as e:
        _handle_error(skin, e, "Failed to import issues", json_mode)
        sys.exit(1)


def _issue_id_by_code_flag(issue_id: str) -> tuple[str, bool]:
    import re
    issue_code_pattern = re.compile(
        r"^[A-Za-z][A-Za-z0-9]{1,5}-\d+$", re.IGNORECASE
    )
    return issue_id, issue_code_pattern.match(issue_id) is not None


@issue_cli.command(name="timeline")
@click.argument("issue_id")
@click.option("--limit", default=50, show_default=True, help="Max rows")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_timeline(obj, issue_id, limit, as_json):
    """E41: List issue timeline activities."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        sys.exit(1)
    iid, by_code = _issue_id_by_code_flag(issue_id)
    try:
        issue = asyncio.run(client.get_issue(iid, by_code=by_code))
        real_id = issue.get("id", iid)
        data = asyncio.run(client.get_issue_timeline(real_id, limit=limit))
        body = data.get("data", data) if isinstance(data, dict) else data
        if json_mode:
            click.echo(_format_json_response(success=True, data=body, message="timeline"))
            return
        rows = (body or {}).get("rows") if isinstance(body, dict) else body
        if not rows:
            skin.info("No timeline entries")
            return
        for r in rows:
            if not isinstance(r, dict):
                continue
            at = r.get("action_type") or r.get("actionType")
            created = r.get("created_at") or r.get("createdAt") or ""
            click.echo(f"{created}  {at}")
    except APIError as e:
        _handle_error(skin, e, "Failed to fetch timeline", json_mode)
        sys.exit(1)


@issue_cli.command(name="timeline-export")
@click.argument("issue_id")
@click.option("--out", "out_path", default=None, help="Write CSV to file (default: stdout)")
@click.option("--action-type", "action_types", multiple=True, help="Filter action_type (repeatable)")
@click.option("--limit", default=None, type=int, help="Row limit (server hard cap 10000)")
@click.option("--json", "as_json", is_flag=True, help="JSON wrapper when --out")
@click.pass_obj
def issue_timeline_export(obj, issue_id, out_path, action_types, limit, as_json):
    """E41: Export single-issue timeline as CSV."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        sys.exit(1)
    iid, by_code = _issue_id_by_code_flag(issue_id)
    try:
        issue = asyncio.run(client.get_issue(iid, by_code=by_code))
        real_id = issue.get("id", iid)
        params = {}
        if action_types:
            params["actionType"] = list(action_types)
        if limit is not None:
            params["limit"] = limit
        content = asyncio.run(client.export_issue_timeline_csv(real_id, params))
        text = content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else str(content)
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            if json_mode:
                click.echo(_format_json_response(success=True, data={"out": out_path, "bytes": len(content)}, message="exported"))
            else:
                skin.success(f"Exported to {out_path}")
        else:
            click.echo(text, nl=False if text.endswith("\n") else True)
    except APIError as e:
        _handle_error(skin, e, "Failed to export timeline", json_mode)
        sys.exit(1)


@issue_cli.command(name="timeline-export-workspace")
@click.option("--out", "out_path", default=None, help="Write CSV to file (default: stdout)")
@click.option("--since", default=None, help="ISO lower bound on created_at")
@click.option("--action-type", "action_types", multiple=True, help="Filter action_type (repeatable)")
@click.option("--issue-id", "filter_issue_id", default=None, help="Filter to one issue id")
@click.option("--limit", default=None, type=int, help="Row limit (server hard cap 10000)")
@click.option("--json", "as_json", is_flag=True, help="JSON wrapper when --out")
@click.pass_obj
def issue_timeline_export_workspace(obj, out_path, since, action_types, filter_issue_id, limit, as_json):
    """E41: Export workspace timeline as CSV."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        sys.exit(1)
    params = {}
    if since:
        params["since"] = since
    if action_types:
        params["actionType"] = list(action_types)
    if filter_issue_id:
        params["issueId"] = filter_issue_id
    if limit is not None:
        params["limit"] = limit
    try:
        content = asyncio.run(client.export_workspace_timeline_csv(params))
        text = content.decode("utf-8") if isinstance(content, (bytes, bytearray)) else str(content)
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            if json_mode:
                click.echo(_format_json_response(success=True, data={"out": out_path, "bytes": len(content)}, message="exported"))
            else:
                skin.success(f"Exported to {out_path}")
        else:
            click.echo(text, nl=False if text.endswith("\n") else True)
    except APIError as e:
        _handle_error(skin, e, "Failed to export workspace timeline", json_mode)
        sys.exit(1)


@parent_cli.command(name="set")
@click.argument("issue_id")
@click.argument("parent_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_parent_set(obj: "Context", issue_id: str, parent_id: str, as_json: bool):
    """E78: Set Issue parent (same workspace; cycle rejected by API).

    Examples:
        opentask issue parent set WAY-2 WAY-1
        opentask issue parent set <child-uuid> <parent-uuid> --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        child_uuid, _ = asyncio.run(_resolve_issue_id(client, issue_id))
        parent_uuid, parent_issue = asyncio.run(_resolve_issue_id(client, parent_id))
        result = asyncio.run(
            client.update_issue(child_uuid, parent_issue_id=parent_uuid)
        )
        if isinstance(result, dict) and "data" in result and isinstance(result["data"], dict):
            if "id" not in result or "parent_issue_id" not in result:
                result = result["data"]
        new_parent = result.get("parent_issue_id") if isinstance(result, dict) else parent_uuid
        parent_code = parent_issue.get("issue_code") or parent_uuid
        if json_mode:
            click.echo(
                _format_json_response(
                    success=True,
                    data={
                        "id": child_uuid,
                        "parent_issue_id": new_parent,
                        "parent_code": parent_code,
                    },
                    message=f"parent set → {parent_code}",
                )
            )
            return
        skin.success(f"[OK] Parent set: {parent_code} ({new_parent})")
    except APIError as e:
        _handle_error(skin, e, "Failed to set parent", json_mode)
        sys.exit(1)


@parent_cli.command(name="clear")
@click.argument("issue_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def issue_parent_clear(obj: "Context", issue_id: str, as_json: bool):
    """E78: Clear Issue parent (promote to root).

    Examples:
        opentask issue parent clear WAY-2
        opentask issue parent clear <uuid> --json
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    try:
        child_uuid, _ = asyncio.run(_resolve_issue_id(client, issue_id))
        result = asyncio.run(client.update_issue(child_uuid, parent_issue_id=None))
        if isinstance(result, dict) and "data" in result and isinstance(result["data"], dict):
            if "id" not in result or "parent_issue_id" not in result:
                result = result["data"]
        new_parent = result.get("parent_issue_id") if isinstance(result, dict) else None
        if json_mode:
            click.echo(
                _format_json_response(
                    success=True,
                    data={"id": child_uuid, "parent_issue_id": new_parent},
                    message="parent cleared (root)",
                )
            )
            return
        skin.success("[OK] Parent cleared (promoted to root)")
    except APIError as e:
        _handle_error(skin, e, "Failed to clear parent", json_mode)
        sys.exit(1)
