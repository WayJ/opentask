"""E14: X-Workspace-Id header from active workspace config."""
from __future__ import annotations

from pathlib import Path

import pytest

from opentask.utils.api_client import OpenTaskClient
from opentask.utils.config import Config


@pytest.fixture
def config_with_ws(tmp_path: Path) -> Config:
    cfg = Config()
    cfg.config_dir = tmp_path / ".opentask"
    cfg.config_file = cfg.config_dir / "config.json"
    cfg._data = {}
    cfg.active_workspace_id = "ws-abc-123"
    cfg.active_workspace_name = "Smoke WS"
    return cfg


def test_headers_include_x_workspace_id_when_active(config_with_ws: Config):
    client = OpenTaskClient(base_url="http://example.test", token="tok", config=config_with_ws)
    headers = client._get_headers()
    assert headers.get("X-Workspace-Id") == "ws-abc-123"
    assert headers.get("Authorization") == "Bearer tok"


def test_headers_omit_workspace_when_unset(tmp_path: Path):
    cfg = Config()
    cfg.config_dir = tmp_path / ".opentask"
    cfg.config_file = cfg.config_dir / "config.json"
    cfg._data = {}
    client = OpenTaskClient(base_url="http://example.test", token="tok", config=cfg)
    headers = client._get_headers()
    assert "X-Workspace-Id" not in headers


def test_config_active_workspace_persists(tmp_path: Path):
    cfg = Config()
    cfg.config_dir = tmp_path / ".opentask"
    cfg.config_file = cfg.config_dir / "config.json"
    cfg._data = {}
    cfg.active_workspace_id = "ws-1"
    cfg.active_workspace_name = "Alpha"
    # reload from disk
    cfg2 = Config()
    cfg2.config_dir = cfg.config_dir
    cfg2.config_file = cfg.config_file
    cfg2._load()
    assert cfg2.active_workspace_id == "ws-1"
    assert cfg2.active_workspace_name == "Alpha"
    cfg2.clear_workspace_context()
    cfg3 = Config()
    cfg3.config_dir = cfg.config_dir
    cfg3.config_file = cfg.config_file
    cfg3._load()
    assert cfg3.active_workspace_id is None
