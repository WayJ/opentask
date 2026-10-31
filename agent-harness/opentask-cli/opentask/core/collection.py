"""Issue Collection management commands for OpenTask CLI."""
import asyncio
import json
import click
from ..utils.api_client import OpenTaskClient, APIError
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


@click.group(name="collection")
def collection_cli():
    """Issue Collection management commands."""
    pass


@collection_cli.command(name="list")
@click.option("--status", "-s", help="Filter by status")
@click.option("--creator", "-c", help="Filter by creator ID")
@click.option("--search", "-k", help="Search keyword")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=20, help="Page size")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def list_collections(obj: "Context", status, creator, search, page, page_size, as_json):
    """List issue collections with filtering."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    try:
        result = asyncio.run(client.list_collections(
            page=page,
            page_size=page_size,
            status=status,
            creator_id=creator,
            search=search
        ))

        if json_mode:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return

        data = result.get("data", result)
        rows = data.get("rows", [])
        total = data.get("total", 0)

        if not rows:
            skin.info("No collections found")
            return

        skin.section(f"Issue Collections ({total} total)")

        headers = ["ID", "Title", "Status", "Issues", "Creator", "Created"]
        table_rows = []
        for col in rows:
            creator_name = "N/A"
            if col.get("creator"):
                creator_name = col["creator"].get("name", col["creator"].get("jnpf_name", "Unknown"))
            elif col.get("creator_id"):
                creator_name = col["creator_id"][:8]

            table_rows.append([
                col.get("id", "")[:8],
                col.get("title", "")[:40],
                col.get("status", "draft"),
                str(len(col.get("issue_ids", []))),
                creator_name,
                col.get("created_at", "")[:10] if col.get("created_at") else ""
            ])

        skin.table(headers, table_rows, max_col_width=40)

    except APIError as e:
        skin.error(f"Failed to list collections: {e.message}")


@collection_cli.command(name="show")
@click.argument("collection_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def show_collection(obj: "Context", collection_id: str, as_json: bool):
    """Show issue collection details."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    try:
        collection = asyncio.run(client.get_collection(collection_id))

        if json_mode:
            click.echo(json.dumps(collection, indent=2, ensure_ascii=False))
            return

        data = collection.get("data", collection)
        skin.section("Issue Collection Details")

        # Creator info
        creator_name = "N/A"
        if data.get("creator"):
            creator_name = data["creator"].get("name", data["creator"].get("jnpf_name", "Unknown"))
        elif data.get("creator_id"):
            creator_name = data["creator_id"][:8]

        # Statistics
        stats = data.get("statistics", {})
        issue_ids = data.get("issue_ids", [])

        skin.status_block({
            "ID": data.get("id", ""),
            "Title": data.get("title", ""),
            "Status": data.get("status", "draft"),
            "Creator": creator_name,
            "Total Issues": str(len(issue_ids)),
            "Created": data.get("created_at", "")[:19] if data.get("created_at") else "N/A",
            "Updated": data.get("updated_at", "")[:19] if data.get("updated_at") else "N/A"
        })

        # Description - 显示描述（保留emoji）
        description = data.get("description", "")
        if description:
            skin.section("Description")
            try:
                # 直接尝试显示原始描述
                # 如果终端支持UTF-8，emoji会正常显示
                # 如果不支持，系统会自动处理
                click.echo(f"  {description}")
            except (UnicodeEncodeError, Exception) as e:
                # 如果编码失败，提供友好的提示
                skin.hint(f"  (Description: {len(description)} characters - contains special characters)")
                skin.hint("  Note: Your terminal may not support all Unicode characters")

        # Linked Issues
        if issue_ids:
            skin.section("Linked Issues")
            for i, issue_id in enumerate(issue_ids[:10], 1):  # Show first 10
                click.echo(f"  {i}. {issue_id}")
            if len(issue_ids) > 10:
                skin.hint(f"  ... and {len(issue_ids) - 10} more")

    except APIError as e:
        skin.error(f"Failed to get collection: {e.message}")


@collection_cli.command(name="create")
@click.option("--title", "-t", required=True, help="Collection title")
@click.option("--description", "-d", default="", help="Collection description")
@click.option("--status", default="draft", type=click.Choice(["draft", "active", "completed", "archived"]), help="Collection status")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def create_collection(obj: "Context", title, description, status, as_json):
    """Create a new issue collection."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    try:
        collection = asyncio.run(client.create_collection(
            title=title,
            description=description,
            status=status
        ))

        if json_mode:
            click.echo(json.dumps(collection, indent=2, ensure_ascii=False))
            return

        data = collection.get("data", collection)
        skin.success(f"Collection created: {title}")

        skin.section("Collection Details")
        skin.status_block({
            "ID": data.get("id", ""),
            "Title": data.get("title", ""),
            "Status": data.get("status", "")
        })

    except APIError as e:
        skin.error(f"Failed to create collection: {e.message}")


@collection_cli.command(name="update")
@click.argument("collection_id")
@click.option("--title", "-t", help="New title")
@click.option("--description", "-d", help="New description")
@click.option("--status", "-s", type=click.Choice(["draft", "active", "completed", "archived"]), help="New status")
@click.option("--issue-ids", help="Issue IDs as JSON array string, e.g. '[\"id1\",\"id2\"]'")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def update_collection(obj: "Context", collection_id, title, description, status, issue_ids, as_json):
    """Update issue collection."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    kwargs = {}
    if title:
        kwargs["title"] = title
    if description is not None:  # Allow empty string
        kwargs["description"] = description
    if status:
        kwargs["status"] = status
    if issue_ids:
        try:
            kwargs["issue_ids"] = json.loads(issue_ids)
        except json.JSONDecodeError:
            skin.error("Invalid JSON format for --issue-ids")
            skin.hint("Example: --issue-ids '[\"id1\",\"id2\",\"id3\"]'")
            return

    if not kwargs:
        skin.error("At least one field must be specified for update")
        return

    try:
        collection = asyncio.run(client.update_collection(collection_id, **kwargs))

        if json_mode:
            click.echo(json.dumps(collection, indent=2, ensure_ascii=False))
            return

        data = collection.get("data", collection)
        skin.success(f"Collection updated: {data.get('title', collection_id)}")

        skin.section("Updated Details")
        skin.status_block({
            "ID": data.get("id", ""),
            "Title": data.get("title", ""),
            "Status": data.get("status", ""),
            "Issues": str(len(data.get("issue_ids", [])))
        })

    except APIError as e:
        skin.error(f"Failed to update collection: {e.message}")


@collection_cli.command(name="parse")
@click.argument("collection_id")
@click.option("--file", "-f", type=click.Path(exists=True), help="JSON file with parsed issues")
@click.option("--stdin", is_flag=True, help="Read issues JSON from stdin")
@click.option("--issues", "-i", "issues_json", help="Issues JSON string")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def parse_collection(obj: "Context", collection_id: str, file, stdin, issues_json, verbose: bool, as_json):
    """Parse collection and create issues.

    Supports multiple input methods:
    1. From file: --file issues.json
    2. From stdin: --stdin (pipe JSON data)
    3. From string: --issues '[{"title":"..."}]'

    JSON format:
    [
        {
            "title": "Issue title",
            "description": "Issue description",
            "type": "task|bug|feature|improvement",
            "priority": "low|medium|high|critical"
        },
        ...
    ]

    Examples:
        collection parse COLL-ID --file issues.json
        cat issues.json | collection parse COLL-ID --stdin
        collection parse COLL-ID --issues '[{"title":"Bug","type":"bug"}]'
        collection parse COLL-ID --file issues.json --verbose  # Show full details
    """
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # Load issues data from different sources
    issues = None

    # Method 1: From file
    if file:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                issues = json.load(f)
        except Exception as e:
            skin.error(f"Failed to load JSON file: {e}")
            return

    # Method 2: From stdin
    elif stdin:
        try:
            import sys
            json_text = sys.stdin.read()
            if not json_text.strip():
                skin.error("No data received from stdin")
                return
            issues = json.loads(json_text)
        except Exception as e:
            skin.error(f"Failed to parse JSON from stdin: {e}")
            return

    # Method 3: From string
    elif issues_json:
        try:
            issues = json.loads(issues_json)
        except Exception as e:
            skin.error(f"Failed to parse JSON string: {e}")
            return

    # No input method provided
    else:
        skin.error("Please provide issues data using one of the following methods:")
        skin.hint("  --file issues.json   Load from file")
        skin.hint("  --stdin             Read from stdin")
        skin.hint("  --issues '[{...}]'  JSON string")
        skin.hint("")
        skin.hint("JSON format: [{'title': '...', 'description': '...', 'type': 'task', 'priority': 'medium'}, ...]")
        return

    if not isinstance(issues, list) or not issues:
        skin.error("Issues data must be a non-empty array")
        return

    try:
        # Get current user info to obtain reporter_id
        try:
            user_info = asyncio.run(client.get_me())
            reporter_id = user_info.get("id") or user_info.get("userId") or user_info.get("user_id")
            if not reporter_id:
                # Fallback to known admin ID
                reporter_id = "cc92be75-ad63-4eaf-84ed-963d5712f93d"
        except Exception as e:
            # Use fallback admin ID
            reporter_id = "cc92be75-ad63-4eaf-84ed-963d5712f93d"

        # Add reporter_id to each issue
        for issue in issues:
            if "reporter_id" not in issue:
                issue["reporter_id"] = reporter_id

        result = asyncio.run(client.parse_collection(collection_id, issues))

        if json_mode:
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            return

        data = result.get("data", result)
        parsed_count = data.get("parsed_count", 0)
        issue_ids = data.get("issue_ids", [])

        # Concise output (default)
        skin.success(f"✓ Created {parsed_count} issues")

        # Verbose output
        if verbose:
            if issue_ids:
                skin.section("Created Issues")
                for i, issue_id in enumerate(issue_ids, 1):
                    click.echo(f"  {i}. {issue_id}")

    except APIError as e:
        skin.error(f"Failed to parse collection: {e.message}")


@collection_cli.command(name="stats")
@click.argument("collection_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def collection_statistics(obj: "Context", collection_id: str, as_json):
    """Get issue collection statistics."""
    config: Config = obj.config
    client = OpenTaskClient(base_url=config.api_url, token=config.token, config=config)
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    try:
        stats = asyncio.run(client.get_collection_statistics(collection_id))

        if json_mode:
            click.echo(json.dumps(stats, indent=2, ensure_ascii=False))
            return

        data = stats.get("data", stats)
        skin.section("Collection Statistics")

        skin.status_block({
            "Total Issues": str(data.get("total_issues", 0)),
            "Open Issues": str(data.get("open_issues", 0)),
            "In Progress": str(data.get("in_progress_issues", 0)),
            "Resolved": str(data.get("resolved_issues", 0)),
            "Closed": str(data.get("closed_issues", 0)),
            "Critical Priority": str(data.get("critical_priority", 0)),
            "High Priority": str(data.get("high_priority", 0)),
            "Medium Priority": str(data.get("medium_priority", 0)),
            "Low Priority": str(data.get("low_priority", 0))
        })

    except APIError as e:
        skin.error(f"Failed to get statistics: {e.message}")


@collection_cli.command(name="delete")
@click.argument("collection_id")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def delete_collection(obj: "Context", collection_id: str, force: bool, as_json: bool):
    """Delete a collection (SECURITY: Not allowed via CLI).

    For security reasons, deletion operations are not allowed through CLI.
    This protects against accidental deletions by AI assistants.

    Examples:
        collection delete COLLECTION-ID
        collection delete COLL-1
        collection delete COLLECTION-ID --force
        collection delete COLLECTION-ID --json
    """
    skin: ReplSkin = obj.skin

    # Use global JSON mode if no local flag
    json_mode = as_json or obj.json_mode

    # 构建错误信息
    error_lines = [
        "❌ ERROR: Cannot delete collection via CLI",
        "",
        "For security reasons, deletion operations are not allowed through CLI.",
        "",
        "Please use the Web UI to delete this collection:",
        f"  1. Open: http://39.183.172.160:28000/opentask/collections/{collection_id}",
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
            "message": "Cannot delete collection via CLI for security reasons",
            "web_ui_url": f"http://39.183.172.160:28000/opentask/collections/{collection_id}",
            "reason": "AI assistant protection"
        }
        click.echo(json.dumps(error_data, indent=2, ensure_ascii=False))

    # 返回错误码
    raise SystemExit(1)
