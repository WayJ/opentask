"""Task management commands for OpenTask CLI."""
import asyncio
import json
import click
from ..utils.api_client import VibeKingClient, APIError
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


@click.group(name="task")
def task_cli():
    """Task management commands."""
    pass


@task_cli.command("run")
@click.argument("task_id", required=False)
@click.option("--id", "task_id", help="Task ID or short ID (first 8 chars) to run")
@click.pass_obj
def run_task(ctx: "Context", task_id: str):
    """
    Get task prompt for AI Agent execution.

    This command retrieves a structured prompt for a PGE task,
    which includes task information, subtask progress, required skills,
    and current execution position.

    \b
    Examples:
        # Get prompt for a task (using full ID)
        vibe task run abc123de-1234-5678-90ab-1234567890ab

        # Get prompt for a task (using short ID - first 8 chars)
        vibe task run abc123de

        # Using --id flag (same as positional argument)
        vibe task run --id abc123de

    \b
    Short IDs:
        You can use the first 8 characters of a task ID as a short ID.
        If the short ID matches multiple tasks, an error will be displayed
        with the list of matching full IDs for you to choose from.
    """
    if not task_id:
        click.echo("Error: Task ID is required", err=True)
        click.echo("")
        click.echo("Usage: vibe task run TASK_ID")
        click.echo("")
        click.echo("Examples:")
        click.echo("  vibe task run abc123de        # Use short ID (8 chars)")
        click.echo("  vibe task run abc123de-1234...  # Or use full ID")
        return 1

    try:
        client = VibeKingClient(
            api_url=ctx.config.api_url,
            token=ctx.config.token,
            skin=ctx.skin,
        )

        # Call the API to get task prompt (backend now supports short IDs)
        prompt_response = asyncio.run(client.get_task_prompt(task_id))

        if ctx.json_mode:
            # JSON output for AI agents
            output = {
                "success": True,
                "data": {
                    "task_id": prompt_response.get("task_id"),
                    "prompt": prompt_response.get("prompt", "")
                },
                "message": "Task prompt retrieved successfully"
            }
            click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            # Human-readable output
            resolved_id = prompt_response.get("task_id", task_id)
            is_short = len(task_id) <= 8 and task_id != resolved_id

            if is_short:
                click.echo(f"ℹ️  Short ID '{task_id}' resolved to:")
                click.echo(f"   {resolved_id}")
                click.echo("")

            click.echo(f"{'='*60}")
            click.echo(f"PGE Task Prompt")
            click.echo(f"{'='*60}")
            click.echo("")
            click.echo(prompt_response.get("prompt", ""))

        return 0

    except APIError as e:
        if ctx.json_mode:
            output = {
                "success": False,
                "error": str(e),
                "message": "Failed to get task prompt"
            }
            click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            # Human-friendly error messages
            error_msg = str(e)
            if "匹配到多个任务" in error_msg or "matches multiple tasks" in error_msg.lower():
                click.echo("❌ Error: Short ID matches multiple tasks", err=True)
                click.echo("")
                click.echo(error_msg)
                click.echo("")
                click.echo("💡 Tip: Please use the full ID from the list above")
            elif "未找到匹配的任务" in error_msg or "not found" in error_msg.lower():
                click.echo(f"❌ Error: Task not found: {task_id}", err=True)
                click.echo("")
                click.echo("💡 Tips:")
                click.echo("   - Make sure the short ID is correct (first 8 characters)")
                click.echo("   - Use 'vibe task list' to see all available tasks")
                click.echo("   - Copy the full ID from the web UI")
            else:
                click.echo(f"❌ Error: {e}", err=True)
        return 1
    except Exception as e:
        if ctx.json_mode:
            output = {
                "success": False,
                "error": str(e),
                "message": "Unexpected error occurred"
            }
            click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            click.echo(f"❌ Error: {e}", err=True)
        return 1


@task_cli.command("create")
@click.option("--requirement-id", "-r", required=True, help="Requirement ID")
@click.option("--title", "-t", required=True, help="Task title")
@click.option("--description", "-d", help="Task description")
@click.option("--skills", "-s", multiple=True, help="Required Superpower Skills (can specify multiple)")
@click.pass_obj
def create_task(
    ctx: "Context",
    requirement_id: str,
    title: str,
    description: str,
    skills: tuple,
):
    """
    Create a new PGE task.

    This command creates a PGE (Plan-Generation-Evaluation) task with
    3 subtasks. Superpower Skills can be specified to guide AI execution.

    \b
    Examples:
        # Create a task with basic info
        vibe task create -r req-123 -t "Implement login feature"

        # Create a task with description
        vibe task create -r req-123 -t "Implement login" -d "Add JWT authentication"

        # Create a task with Superpower Skills
        vibe task create -r req-123 -t "Implement login" \\
          -s "superpowers:brainstorming" \\
          -s "superpowers:test-driven-development"

    \b
    Available Superpower Skills:
      • superpowers:brainstorming - 创意风暴
      • superpowers:writing-plans - 编写计划
      • superpowers:test-driven-development - 测试驱动开发
      • superpowers:executing-plans - 执行计划
      • superpowers:systematic-debugging - 系统化调试
      • superpowers:code-review - 代码审查
      • superpowers:verification-before-completion - 完成前验证
      • superpowers:frontend-design - 前端设计
    """
    try:
        client = VibeKingClient(
            api_url=ctx.config.api_url,
            token=ctx.config.token,
            skin=ctx.skin,
        )

        # Prepare task data
        task_data = {
            "requirement_id": requirement_id,
            "title": title,
            "framework": "PGE",
            "required_skills": list(skills) if skills else []
        }

        if description:
            task_data["description"] = description

        # Call the API to create task
        task_response = asyncio.run(client.create_pge_task(task_data))

        if ctx.json_mode:
            # JSON output for AI agents
            output = {
                "success": True,
                "data": task_response,
                "message": "PGE task created successfully"
            }
            click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            # Human-readable output
            click.echo(f"✅ PGE Task Created Successfully")
            click.echo(f"")
            click.echo(f"Task ID: {task_response.get('id')}")
            click.echo(f"Title: {task_response.get('title')}")
            click.echo(f"Framework: {task_response.get('framework')}")
            click.echo(f"Status: {task_response.get('status')}")
            click.echo(f"")

            # Show subtasks
            children = task_response.get('data', {}).get('children', [])
            if children:
                click.echo(f"Subtasks ({len(children)}):")
                for child in children:
                    click.echo(f"  - {child.get('code')}: {child.get('title')} [{child.get('status')}]")

            # Show required skills
            required_skills = task_response.get('data', {}).get('required_skills', [])
            if required_skills and 'skills' in required_skills:
                click.echo(f"Required Skills ({len(required_skills['skills'])}):")
                for skill in required_skills['skills']:
                    click.echo(f"  - {skill}")

        return 0

    except APIError as e:
        if ctx.json_mode:
            output = {
                "success": False,
                "error": str(e),
                "message": "Failed to create task"
            }
            click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            click.echo(f"Error: {e}", err=True)
        return 1
    except Exception as e:
        if ctx.json_mode:
            output = {
                "success": False,
                "error": str(e),
                "message": "Unexpected error occurred"
            }
            click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            click.echo(f"Error: {e}", err=True)
        return 1


@task_cli.command("list")
@click.option("--requirement-id", "-r", help="Filter by requirement ID")
@click.option("--status", "-s", help="Filter by status")
@click.pass_obj
def list_tasks(ctx: "Context", requirement_id: str, status: str):
    """
    List tasks with optional filtering.

    \b
    Examples:
        # List all tasks
        vibe task list

        # List tasks for a requirement
        vibe task list --requirement-id req-123

        # List pending tasks
        vibe task list --status PENDING
    """
    try:
        client = VibeKingClient(
            api_url=ctx.config.api_url,
            token=ctx.config.token,
            skin=ctx.skin,
        )

        # Call the API to list tasks
        tasks_response = asyncio.run(client.list_tasks(requirement_id=requirement_id, status=status))

        if ctx.json_mode:
            # JSON output for AI agents
            output = {
                "success": True,
                "data": tasks_response,
                "message": f"Retrieved {len(tasks_response.get('rows', []))} tasks"
            }
            click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            # Human-readable output
            tasks = tasks_response.get('rows', [])
            total = tasks_response.get('total', 0)

            click.echo(f"Tasks: {total} total")
            click.echo(f"{'='*60}")

            if not tasks:
                click.echo("No tasks found.")
                return 0

            for task in tasks:
                status_icon = {
                    'PENDING': '⏳',
                    'RUNNING': '🔄',
                    'COMPLETED': '✅',
                    'FAILED': '❌',
                }.get(task.get('status'), '📌')

                click.echo(f"{status_icon} [{task.get('code', 'N/A')}] {task.get('title')}")
                click.echo(f"    Status: {task.get('status')}")
                click.echo(f"    Framework: {task.get('framework', 'N/A')}")
                if task.get('description'):
                    click.echo(f"    Description: {task.get('description')[:60]}...")
                click.echo("")

        return 0

    except APIError as e:
        if ctx.json_mode:
            output = {
                "success": False,
                "error": str(e),
                "message": "Failed to list tasks"
            }
            click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            click.echo(f"Error: {e}", err=True)
        return 1
    except Exception as e:
        if ctx.json_mode:
            output = {
                "success": False,
                "error": str(e),
                "message": "Unexpected error occurred"
            }
            click.echo(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            click.echo(f"Error: {e}", err=True)
        return 1
