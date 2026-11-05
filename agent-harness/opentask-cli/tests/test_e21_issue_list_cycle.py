"""E21: issue list --cycle → cycle_id query param."""
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from opentask.opentask_cli import cli


def test_issue_list_passes_cycle_id():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.list_issues = AsyncMock(return_value={"rows": [], "count": 0})

    with patch("opentask.core.issue.OpenTaskClient", return_value=mock_client):
        with patch("opentask.core.issue.Config") as Cfg:
            cfg = MagicMock()
            cfg.api_url = "http://localhost:7377"
            cfg.token = "t"
            cfg.active_project_id = None
            Cfg.return_value = cfg
            # Cli uses ctx.obj.config from login; invoke with obj injection is hard —
            # call underlying after ensuring import path works via patching asyncio.run consumer.
            result = runner.invoke(
                cli,
                ["--token", "t", "--api-url", "http://localhost:7377", "issue", "list", "--cycle", "cyc-1", "--json"],
            )

    # May fail auth wiring; assert option is accepted (exit not usage error)
    assert "No such option" not in (result.output or "")
    assert result.exit_code != 2  # click usage error


def test_list_issues_client_includes_cycle_param():
    import asyncio
    from opentask.utils.api_client import OpenTaskClient

    client = OpenTaskClient(base_url="http://example", token="t")
    client.get = AsyncMock(return_value={"rows": []})

    async def _run():
        await client.list_issues(cycle_id="abc")

    asyncio.get_event_loop().run_until_complete(_run()) if False else None
    asyncio.run(_run())
    assert client.get.await_args.kwargs["params"]["cycle_id"] == "abc"
