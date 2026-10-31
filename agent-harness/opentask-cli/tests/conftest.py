"""
OpenTask CLI 测试共享配置

提供可复用的 fixtures 和辅助函数
"""

import pytest
from pathlib import Path
from opentask.utils.config import Config
from opentask.utils.api_client import VibeKingClient
from opentask.utils.repl_skin import ReplSkin


# ============================================================================
# Fixtures: 配置
# ============================================================================

@pytest.fixture
def temp_config_dir(tmp_path):
    """临时配置目录 fixture"""
    config_dir = tmp_path / ".opentask"
    config_dir.mkdir(exist_ok=True)
    return config_dir


@pytest.fixture
def mock_config(temp_config_dir):
    """Mock 配置对象"""
    config_file = temp_config_dir / "config.json"
    config = Config()
    config.config_dir = temp_config_dir
    config.config_file = config_file
    return config


@pytest.fixture
def clean_config(temp_config_dir):
    """清洁的配置对象（无预设数据）"""
    config_file = temp_config_dir / "config.json"
    config = Config()
    config.config_dir = temp_config_dir
    config.config_file = config_file
    config._data = {}
    return config


# ============================================================================
# Fixtures: API 客户端
# ============================================================================

@pytest.fixture
def mock_api_client():
    """Mock API 客户端（使用假 URL 和 token）"""
    return VibeKingClient(
        base_url="http://test-api.example.com",
        token="test_token_12345"
    )


@pytest.fixture
def api_client_with_real_url():
    """使用真实 URL 的 API 客户端（连接到 localhost）"""
    return VibeKingClient(
        base_url="http://localhost:7377",
        token=None
    )


# ============================================================================
# Fixtures: REPL Skin
# ============================================================================

@pytest.fixture
def mock_repl_skin():
    """Mock REPL Skin"""
    return ReplSkin("opentask", version="1.0.0")


# ============================================================================
# Fixtures: 示例数据
# ============================================================================

@pytest.fixture
def sample_project_data():
    """示例项目数据"""
    return {
        "id": "proj-123",
        "name": "Test Project",
        "description": "Test Description",
        "is_active": True,
        "created_at": "2026-03-23T12:00:00",
        "updated_at": "2026-03-23T12:00:00"
    }


@pytest.fixture
def sample_issue_data():
    """示例 Issue 数据"""
    return {
        "id": "issue-456",
        "issue_code": "ISSUE2026-32",
        "title": "Test Issue",
        "type": "bug",
        "status": "open",
        "priority": "high",
        "description": "Test issue description",
        "created_at": "2026-03-23T12:00:00"
    }


@pytest.fixture
def sample_requirement_data():
    """示例 Requirement 数据"""
    return {
        "id": "req-789",
        "title": "Test Requirement",
        "description": "Test requirement description",
        "status": "pending",
        "priority": "medium",
        "issue_id": "issue-456"
    }


@pytest.fixture
def sample_collection_data():
    """示例 Collection 数据"""
    return {
        "id": "coll-101",
        "title": "Test Collection",
        "description": "Test collection description",
        "issue_ids": ["issue-456", "issue-789"],
        "created_at": "2026-03-23T12:00:00"
    }


# ============================================================================
# Pytest 配置
# ============================================================================

def pytest_configure(config):
    """Pytest 配置钩子"""
    config.addinivalue_line(
        "markers",
        "integration: 集成测试（需要真实 API）"
    )
    config.addinivalue_line(
        "markers",
        "slow: 运行缓慢的测试"
    )
    config.addinivalue_line(
        "markers",
        "windows: Windows 特定测试"
    )

    # 设置环境变量，让 opentask_cli 知道在测试环境中
    import os
    import sys
    os.environ['PYTEST_RUNNING'] = '1'

    # 修复 pytest-asyncio I/O 捕获问题
    # 在 Windows 上禁用 asyncio 的自动模式
    if sys.platform == "win32":
        try:
            # 不修改 asyncio_mode，让 pytest.ini 中的设置生效
            pass
        except Exception:
            pass
