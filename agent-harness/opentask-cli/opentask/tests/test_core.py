"""Unit tests for OpenTask CLI core modules.

These tests use mocked HTTP responses and synthetic data.
No external dependencies required.
"""
import json
import pytest
from unittest.mock import Mock, patch
from opentask.utils.api_client import OpenTaskClient, APIError
from opentask.utils.config import Config
from opentask.utils.repl_skin import ReplSkin


# ============================================================================
# API Client Tests
# ============================================================================

class TestAPIClient:
    """Test API client functionality."""

    def test_client_init(self):
        """Test client initialization."""
        client = OpenTaskClient("http://test.com")
        assert client.base_url == "http://test.com"
        assert client.token is None

    def test_client_init_with_token(self):
        """Test client initialization with token."""
        client = OpenTaskClient("http://test.com", token="test_token")
        assert client.token == "test_token"

    def test_get_headers_without_token(self):
        """Test header generation without token."""
        client = OpenTaskClient("http://test.com")
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_get_headers_with_token(self):
        """Test header generation with token."""
        client = OpenTaskClient("http://test.com", token="test_token")
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test_token"

    def test_handle_response_success(self):
        """Test successful response handling."""
        client = OpenTaskClient("http://test.com")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 200,
            "message": "success",
            "data": {"id": "123", "name": "Test"}
        }

        result = client._handle_response(mock_response)
        assert result == {"id": "123", "name": "Test"}

    def test_handle_response_error(self):
        """Test error response handling."""
        client = OpenTaskClient("http://test.com")
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "code": 400,
            "message": "Bad request"
        }

        with pytest.raises(APIError) as exc_info:
            client._handle_response(mock_response)

        assert exc_info.value.status_code == 400
        assert exc_info.value.message == "Bad request"

    @pytest.mark.asyncio
    async def test_list_projects(self):
        """Test project listing."""
        client = OpenTaskClient("http://test.com")

        with patch.object(client, '_request') as mock_request:
            mock_request.return_value = [
                {"id": "1", "name": "Project A"},
                {"id": "2", "name": "Project B"}
            ]

            projects = await client.list_projects()
            assert len(projects) == 2
            assert projects[0]["name"] == "Project A"

    @pytest.mark.asyncio
    async def test_create_project(self):
        """Test project creation."""
        client = OpenTaskClient("http://test.com")

        with patch.object(client, '_request') as mock_request:
            mock_request.return_value = {
                "id": "123",
                "name": "New Project",
                "description": "Test"
            }

            result = await client.create_project("New Project", "Test")
            assert result["name"] == "New Project"


# ============================================================================
# Config Tests
# ============================================================================

class TestConfig:
    """Test configuration management."""

    def test_config_defaults(self, tmp_path):
        """Test default configuration values."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = f"{tmpdir}/test_config.json"
            config = Config()
            config.config_file = test_file

            assert config.api_url == "http://localhost:7377"
            assert config.token is None
            assert config.active_project_id is None

    def test_config_set_get(self, tmp_path):
        """Test setting and getting values."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = f"{tmpdir}/test_config.json"
            config = Config()
            config.config_file = test_file

            config.set("test_key", "test_value")
            assert config.get("test_key") == "test_value"

    def test_api_url_property(self, tmp_path):
        """Test api_url property."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = f"{tmpdir}/test_config.json"
            config = Config()
            config.config_file = test_file

            config.api_url = "http://example.com"
            assert config.api_url == "http://example.com"
            assert config.get("api_url") == "http://example.com"

    def test_token_property(self, tmp_path):
        """Test token property."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = f"{tmpdir}/test_config.json"
            config = Config()
            config.config_file = test_file

            config.token = "test_token_123"
            assert config.token == "test_token_123"

    def test_clear_auth(self, tmp_path):
        """Test clearing authentication."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = f"{tmpdir}/test_config.json"
            config = Config()
            config.config_file = test_file

            config.token = "test_token"
            assert config.token is not None

            config.clear_auth()
            assert config.token is None


# ============================================================================
# REPL Skin Tests
# ============================================================================

class TestReplSkin:
    """Test REPL skin functionality."""

    def test_skin_init(self):
        """Test skin initialization."""
        skin = ReplSkin("opentask", version="1.0.0")
        assert skin.software == "opentask"
        assert skin.version == "1.0.0"

    def test_prompt_no_context(self):
        """Test prompt without project context."""
        skin = ReplSkin("opentask")
        prompt = skin.prompt()
        assert "opentask" in prompt
        assert "❯" in prompt

    def test_prompt_with_context(self):
        """Test prompt with project context."""
        skin = ReplSkin("opentask")
        prompt = skin.prompt(project_name="my-project")
        assert "opentask" in prompt
        assert "my-project" in prompt

    def test_prompt_modified(self):
        """Test prompt with unsaved changes indicator."""
        skin = ReplSkin("opentask")
        prompt = skin.prompt(project_name="my-project", modified=True)
        assert "*" in prompt

    def test_prompt_tokens(self):
        """Test prompt tokens for prompt_toolkit."""
        skin = ReplSkin("opentask")
        tokens = skin.prompt_tokens(project_name="test-project")

        # Convert to list of tuples
        token_list = list(tokens)
        assert len(token_list) > 0
        assert token_list[0][0] == "class:icon"

    def test_status_display(self, capsys):
        """Test status display."""
        skin = ReplSkin("opentask")
        skin.status("Key", "Value")

        captured = capsys.readouterr()
        assert "Key" in captured.out
        assert "Value" in captured.out

    def test_success_message(self, capsys):
        """Test success message."""
        skin = ReplSkin("opentask")
        skin.success("Operation successful")

        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "Operation successful" in captured.out

    def test_error_message(self, capsys):
        """Test error message."""
        skin = ReplSkin("opentask")
        skin.error("Operation failed")

        captured = capsys.readouterr()
        assert "✗" in captured.out
        assert "Operation failed" in captured.out

    def test_warning_message(self, capsys):
        """Test warning message."""
        skin = ReplSkin("opentask")
        skin.warning("Warning message")

        captured = capsys.readouterr()
        assert "⚠" in captured.out
        assert "Warning message" in captured.out

    def test_info_message(self, capsys):
        """Test info message."""
        skin = ReplSkin("opentask")
        skin.info("Info message")

        captured = capsys.readouterr()
        assert "●" in captured.out
        assert "Info message" in captured.out


# ============================================================================
# Data Formatting Tests
# ============================================================================

class TestDataFormatting:
    """Test data formatting functions."""

    def test_format_project(self):
        """Test project data formatting."""
        from opentask.core.project import format_project

        project = {
            "id": "12345678-1234-1234-1234-123456789012",
            "name": "Test Project",
            "description": "A test project",
            "is_active": True,
            "created_at": "2024-01-01T00:00:00"
        }

        formatted = format_project(project)
        assert formatted["id"] == "12345678"
        assert formatted["name"] == "Test Project"
        assert formatted["is_active"] == True

    def test_format_issue(self):
        """Test issue data formatting."""
        from opentask.core.issue import format_issue

        issue = {
            "id": "12345678-1234-1234-1234-123456789012",
            "title": "Test Issue",
            "type": "bug",
            "status": "open",
            "priority": "high",
            "assignee_id": "87654321-8765-8765-8765-876543210987",
            "created_at": "2024-01-01T00:00:00"
        }

        formatted = format_issue(issue)
        assert formatted["id"] == "12345678"
        assert formatted["title"] == "Test Issue"
        assert formatted["assignee"] == "87654321"
