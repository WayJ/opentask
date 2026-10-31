"""
配置管理模块测试（修复版）

使用 tmp_path fixture 替代 Mock，更可靠
"""

import pytest
import json
from pathlib import Path

from opentask.utils.config import Config


# ============================================================================
# 配置持久化测试（使用 tmp_path）
# ============================================================================

class TestConfigPersistence:
    """测试配置持久化"""

    def test_save_and_load_config(self, tmp_path):
        """测试保存和加载配置"""
        config_file = tmp_path / "config.json"

        # 创建配置并保存
        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.set("test_key", "test_value")

        # 验证文件被创建
        assert config_file.exists()

        # 加载配置
        data = json.loads(config_file.read_text(encoding='utf-8'))
        assert data["test_key"] == "test_value"

    def test_load_from_existing_file(self, tmp_path):
        """测试从现有文件加载"""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"api_url": "http://test.com"}), encoding='utf-8')

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config._load()

        assert config.get("api_url") == "http://test.com"

    def test_load_from_invalid_json(self, tmp_path):
        """测试加载无效 JSON"""
        config_file = tmp_path / "config.json"
        config_file.write_text("invalid json", encoding='utf-8')

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config._load()

        # 应该回退到空配置
        assert config._data == {}

    def test_delete_persists_to_disk(self, tmp_path):
        """测试删除操作持久化到磁盘"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.set("to_delete", "value")
        config.delete("to_delete")

        # 验证文件被更新
        data = json.loads(config_file.read_text(encoding='utf-8'))
        assert "to_delete" not in data


# ============================================================================
# API URL 配置测试
# ============================================================================

class TestAPIUrlConfig:
    """测试 API URL 配置"""

    def test_set_and_get_api_url(self, tmp_path):
        """测试设置和获取 API URL"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.api_url = "http://example.com:8080"

        assert config.api_url == "http://example.com:8080"

        # 验证持久化
        data = json.loads(config_file.read_text(encoding='utf-8'))
        assert data["api_url"] == "http://example.com:8080"

    def test_api_url_trims_trailing_slash(self, tmp_path):
        """测试 API URL 移除尾部斜杠"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.api_url = "http://localhost:7377/"

        assert config.api_url == "http://localhost:7377"

    def test_default_api_url(self, monkeypatch):
        """测试默认 API URL"""
        config = Config()
        monkeypatch.setattr(config, '_data', {})
        assert config.api_url == "http://localhost:7377"


# ============================================================================
# Token 配置测试
# ============================================================================

class TestTokenConfig:
    """测试 Token 配置"""

    def test_set_and_get_token(self, tmp_path):
        """测试设置和获取 token"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.token = "test_token_123"

        assert config.token == "test_token_123"

        # 验证持久化
        data = json.loads(config_file.read_text(encoding='utf-8'))
        assert data["token"] == "test_token_123"

    def test_clear_token(self, tmp_path):
        """测试清除 token"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.token = "secret_token"
        config.clear_auth()

        assert config.token is None

        # 验证持久化
        data = json.loads(config_file.read_text(encoding='utf-8'))
        assert "token" not in data


# ============================================================================
# 项目配置测试
# ============================================================================

class TestProjectConfig:
    """测试项目配置"""

    def test_set_and_get_project_context(self, tmp_path):
        """测试设置和获取项目上下文"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.active_project_id = "proj_123"
        config.active_project_name = "Test Project"

        assert config.active_project_id == "proj_123"
        assert config.active_project_name == "Test Project"

    def test_clear_project_context(self, tmp_path):
        """测试清除项目上下文"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.active_project_id = "proj_123"
        config.active_project_name = "Test Project"
        config.clear_project_context()

        assert config.active_project_id is None
        assert config.active_project_name is None

        # 验证持久化
        data = json.loads(config_file.read_text(encoding='utf-8'))
        assert "active_project_id" not in data
        assert "active_project_name" not in data


# ============================================================================
# 配置导出测试
# ============================================================================

class TestConfigExport:
    """测试配置导出"""

    def test_to_dict_returns_copy(self, monkeypatch):
        """测试 to_dict 返回副本"""
        config = Config()
        monkeypatch.setattr(config, '_data', {"key": "value"})
        data = config.to_dict()
        data["new_key"] = "new_value"

        # 原始数据不应被修改
        assert "new_key" not in config._data

    def test_to_dict_includes_all_data(self, monkeypatch):
        """测试 to_dict 包含所有数据"""
        config = Config()
        monkeypatch.setattr(config, '_data', {"key1": "val1", "key2": "val2"})
        data = config.to_dict()
        assert data == {"key1": "val1", "key2": "val2"}


# ============================================================================
# 边缘情况测试
# ============================================================================

class TestEdgeCases:
    """测试边缘情况"""

    def test_overwrite_existing_value(self, tmp_path):
        """测试覆盖已存在的值"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.set("key", "value1")
        config.set("key", "value2")

        assert config.get("key") == "value2"

    def test_empty_string_value(self, tmp_path):
        """测试空字符串值"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.set("empty", "")

        assert config.get("empty") == ""

    def test_none_value(self, tmp_path):
        """测试 None 值"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.set("none_val", None)

        assert config.get("none_val") is None

    def test_complex_data_types(self, tmp_path):
        """测试复杂数据类型"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        complex_data = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "bool": True
        }
        config.set("complex", complex_data)

        result = config.get("complex")
        assert result["list"] == [1, 2, 3]
        assert result["dict"]["nested"] == "value"
        assert result["bool"] is True

    def test_get_with_default_value(self, monkeypatch):
        """测试获取带默认值的配置"""
        config = Config()
        monkeypatch.setattr(config, '_data', {})
        assert config.get("nonexistent", "default") == "default"

    def test_delete_nonexistent_key(self, tmp_path):
        """测试删除不存在的键（不应报错）"""
        config_file = tmp_path / "config.json"

        config = Config()
        config.config_dir = tmp_path
        config.config_file = config_file
        config.delete("nonexistent")  # 不应抛出异常
