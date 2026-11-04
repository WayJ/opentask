"""Shared helper functions for OpenTask CLI.

This module contains common utilities used across multiple CLI modules
to avoid code duplication and improve maintainability.
"""
import asyncio
import json
import sys
from typing import Any

from .api_client import OpenTaskClient, APIError
from .config import Config
from .repl_skin import ReplSkin


# ============================================================================
# JSON Output Helpers
# ============================================================================

def format_json_response(
    success: bool,
    data: dict | None = None,
    error: str | None = None,
    message: str | None = None
) -> str:
    """Format JSON response in standard structure for AI consumption.

    Args:
        success: Whether the operation succeeded
        data: Response data (for successful operations)
        error: Error message (for failed operations)
        message: Optional human-readable message

    Returns:
        JSON string with standardized format

    Examples:
        >>> format_json_response(True, {"id": "123"}, message="Created")
        '{"success": true, "data": {"id": "123"}, "error": null, "message": "Created"}'
    """
    response = {
        "success": success,
        "data": data,
        "error": error,
        "message": message or ("Operation successful" if success else "Operation failed")
    }
    return json.dumps(response, indent=2, ensure_ascii=False)


# ============================================================================
# Error Handling Helpers
# ============================================================================

def handle_api_error(
    skin: ReplSkin,
    error: APIError,
    message: str,
    json_mode: bool = False
) -> None:
    """Handle API error and exit with proper status code.

    Args:
        skin: REPL skin for output
        error: The API error
        message: Context message (e.g., "Failed to create issue")
        json_mode: Whether to output JSON format

    Examples:
        >>> try:
        ...     await client.create_issue(...)
        ... except APIError as e:
        ...     handle_api_error(skin, e, "Failed to create issue")
    """
    if json_mode:
        click_echo(format_json_response(
            success=False,
            error=error.message,
            message=f"{message}: {error.message}"
        ))
    else:
        skin.error(f"{message}: {error.message}")

    # Exit with error code for automation
    sys.exit(1)


def click_echo(text: str) -> None:
    """Click echo wrapper to avoid circular import.

    Args:
        text: Text to echo
    """
    import click
    click.echo(text)


# ============================================================================
# User Resolution Helpers
# ============================================================================

def get_current_user_id(client: OpenTaskClient) -> str | None:
    """Get current user ID using standardized method.

    This helper wraps the get_me() API call and extracts the user ID
    using the standardized method that handles multiple response formats.

    Args:
        client: API client

    Returns:
        User ID as string, or None if not found

    Examples:
        >>> user_id = get_current_user_id(client)
        >>> if user_id:
        ...     print(f"Current user: {user_id}")
    """
    user_info = asyncio.run(client.get_me())
    return client.get_user_id_from_response(user_info)


# ============================================================================
# Command Output Helpers
# ============================================================================

def display_success_message(
    skin: ReplSkin,
    message: str,
    json_mode: bool,
    data: dict | None = None
) -> None:
    """Display success message in appropriate format.

    Args:
        skin: REPL skin for output
        message: Success message
        json_mode: Whether to output JSON format
        data: Optional data to include in JSON output

    Examples:
        >>> display_success_message(skin, "Issue created", json_mode=False)
        ✓ Issue created
        >>> display_success_message(skin, "Issue created", json_mode=True, data={"id": "123"})
        {"success": true, "data": {"id": "123"}, "message": "Issue created"}
    """
    if json_mode:
        click_echo(format_json_response(
            success=True,
            data=data,
            message=message
        ))
    else:
        skin.success(f"✓ {message}")


def display_table(
    skin: ReplSkin,
    headers: list[str],
    rows: list[list[str]],
    title: str | None = None,
    max_col_width: int = 40
) -> None:
    """Display data in table format.

    Args:
        skin: REPL skin for output
        headers: Table headers
        rows: Table rows (list of lists)
        title: Optional title for the table
        max_col_width: Maximum column width

    Examples:
        >>> display_table(skin, ["ID", "Title"], [["123", "My Issue"]], title="Issues")
    """
    if title:
        skin.section(title)

    if not rows:
        skin.info("No data to display")
        return

    skin.table(headers, rows, max_col_width=max_col_width)


# ============================================================================
# Validation Helpers
# ============================================================================

def validate_uuid(uuid_str: str) -> bool:
    """Validate if string is a valid UUID.

    Args:
        uuid_str: String to validate

    Returns:
        True if valid UUID format, False otherwise

    Examples:
        >>> validate_uuid("123e4567-e89b-12d3-a456-426614174000")
        True
        >>> validate_uuid("not-a-uuid")
        False
    """
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return uuid_pattern.match(uuid_str) is not None


def validate_issue_code(code: str) -> bool:
    """Validate if string is a valid issue code.

    Args:
        code: String to validate

    Returns:
        True if valid issue code format, False otherwise

    Examples:
        >>> validate_issue_code("ISSUE2026-123")
        True
        >>> validate_issue_code("OT-1")
        True
        >>> validate_issue_code("NOT-A-CODE")
        False
    """
    import re
    # KEY-N (2–6 alnum prefix) or legacy ISSUE{year}-N
    pattern = re.compile(
        r'^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$',
        re.IGNORECASE,
    )
    return pattern.match(code) is not None
