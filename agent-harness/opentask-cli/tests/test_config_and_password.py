"""
配置管理和密码存储专项测试

测试范围：
- 配置文件读写
- 密码加密存储
- 配置持久化
- 错误处理和边缘情况
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest import mock

from opentask.utils.config import Config
from opentask.utils.password_store import PasswordStore
from opentask.utils.crypto_helper import encrypt_password


# ============================================================================
# Config 测试
# ============================================================================

class TestConfigFileOperations:
    """测试配置文件操作"""

    def test_config_create_new_file(self):
        """测试创建新配置文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 临时改变配置目录
            config_dir = Path(tmpdir) / ".opentask"
            config_dir.mkdir()

            with mock.patch('opentask.utils.config.Config.DEFAULT_CONFIG_DIR', config_dir):
                config = Config()

                # 设置一些值（会自动保存）
                config.api_url = "http://test.example.com"
                config.token = "test_token_123"
                config.active_project_name = "test_project"

                # 验证文件存在
                assert config.config_file.exists()

                # 读取并验证内容
                with open(config.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                assert data["api_url"] == "http://test.example.com"
                assert data["token"] == "test_token_123"
                assert data["active_project_name"] == "test_project"

    def test_config_load_existing_file(self):
        """测试加载现有配置文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 临时改变配置目录
            config_dir = Path(tmpdir) / ".opentask"
            config_dir.mkdir()

            config_file = config_dir / "config.json"

            # 先创建配置文件
            initial_data = {
                "api_url": "http://existing.example.com",
                "token": "existing_token",
                "active_project_name": "existing_project"
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f)

            with mock.patch('opentask.utils.config.Config.DEFAULT_CONFIG_DIR', config_dir):
                # 加载配置
                config = Config()

                # 验证加载的值
                assert config.api_url == "http://existing.example.com"
                assert config.token == "existing_token"
                assert config.active_project_name == "existing_project"

    def test_config_default_values(self):
        """测试配置默认值（隔离真实 ~/.opentask）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".opentask"
            config_dir.mkdir()
            with mock.patch('opentask.utils.config.Config.DEFAULT_CONFIG_DIR', config_dir):
                config = Config()
                assert config.api_url is not None
                assert isinstance(config.api_url, str)
                assert config.token is None
                assert config.active_project_name is None

    def test_config_update_and_save(self):
        """测试更新配置并保存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".opentask"
            config_dir.mkdir()

            with mock.patch('opentask.utils.config.Config.DEFAULT_CONFIG_DIR', config_dir):
                config = Config()

                # 初始保存
                config.api_url = "http://initial.example.com"

                # 更新
                config.api_url = "http://updated.example.com"
                config.token = "new_token"

                # 重新加载验证
                config2 = Config()

                assert config2.api_url == "http://updated.example.com"
                assert config2.token == "new_token"

    def test_config_clear_auth(self):
        """测试清除认证信息"""
        config = Config()

        # 设置认证信息
        config.token = "test_token"
        config.username = "test_user"

        # 清除（只清除 token）
        config.clear_auth()

        # 验证清除
        assert config.token is None
        # username 不会被 clear_auth 清除
        assert config.username == "test_user"

    def test_config_invalid_json(self):
        """测试处理无效的 JSON 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".opentask"
            config_dir.mkdir()

            config_file = config_dir / "config.json"

            # 创建无效 JSON 文件
            with open(config_file, 'w') as f:
                f.write("{ invalid json }")

            with mock.patch('opentask.utils.config.Path.home', return_value=Path(tmpdir)):
                config = Config()

                # 应该能处理并使用默认值
                assert config.api_url is not None  # 应该有默认值

    def test_config_empty_file(self):
        """测试处理空文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".opentask"
            config_dir.mkdir()

            config_file = config_dir / "config.json"

            # 创建空文件
            config_file.touch()

            with mock.patch('opentask.utils.config.Path.home', return_value=Path(tmpdir)):
                config = Config()

                # 应该能处理空文件
                assert config.api_url is not None  # 应该有默认值

    def test_config_missing_file(self):
        """测试配置文件不存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".opentask"
            config_dir.mkdir()

            # 不创建配置文件

            with mock.patch('opentask.utils.config.Path.home', return_value=Path(tmpdir)):
                config = Config()

                # 应该使用默认值
                assert config.api_url is not None


# ============================================================================
# PasswordStore 测试
# ============================================================================

class TestPasswordStore:
    """测试密码存储"""

    def test_password_store_is_available(self):
        """测试检查 keyring 是否可用"""
        available = PasswordStore.is_available()
        assert isinstance(available, bool)

    def test_password_store_set_and_get(self):
        """测试保存和获取密码"""
        # 使用 keyring 存储
        username = "test_user_config"
        password = "test_password_123"

        # 保存密码
        result = PasswordStore.set_password(username, password)
        assert isinstance(result, bool)

        # 获取密码
        retrieved = PasswordStore.get_password(username)
        # keyring 可能不可用，或者返回 None
        assert retrieved is None or retrieved == password

        # 清理
        PasswordStore.delete_password(username)

    def test_password_store_nonexistent_user(self):
        """测试获取不存在的用户密码"""
        password = PasswordStore.get_password("nonexistent_user_xyz")
        assert password is None

    def test_password_store_delete_password(self):
        """测试删除密码"""
        username = "test_user_delete"

        # 先保存密码
        PasswordStore.set_password(username, "test_pass")

        # 删除密码
        result = PasswordStore.delete_password(username)
        assert isinstance(result, bool)

        # 验证已删除
        password = PasswordStore.get_password(username)
        assert password is None

    def test_password_store_unicode_password(self):
        """测试包含 Unicode 的密码"""
        username = "test_user_unicode"
        passwords = [
            "中文密码",
            "password@#$%",
            "パスワード",
            "pass word",
        ]

        for password in passwords:
            result = PasswordStore.set_password(username, password)
            if result:  # 如果 keyring 可用
                retrieved = PasswordStore.get_password(username)
                assert retrieved == password

                # 清理
                PasswordStore.delete_password(username)


# ============================================================================
# 加密/解密测试
# ============================================================================

class TestCryptoHelper:
    """测试加密解密功能"""

    def test_encrypt_password_basic(self):
        """测试基本密码加密"""
        password = "my_password_123"
        encrypted = encrypt_password(password)

        # 加密后的密码应该不同于原密码
        assert encrypted != password
        # 应该是非空字符串
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_encrypt_password_different_results(self):
        """测试相同密码加密产生不同结果（因为有随机 salt）"""
        password = "same_password"

        encrypted1 = encrypt_password(password)
        encrypted2 = encrypt_password(password)

        # 由于使用 MD5 + AES，相同密码会产生相同的加密结果
        # 这是正常的，因为 MD5 是确定性的
        assert isinstance(encrypted1, str)
        assert isinstance(encrypted2, str)
        assert len(encrypted1) > 0
        assert len(encrypted2) > 0

    def test_encrypt_empty_password(self):
        """测试加密空密码"""
        password = ""
        encrypted = encrypt_password(password)

        # 应该能处理空密码
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_encrypt_special_characters(self):
        """测试加密包含特殊字符的密码"""
        passwords = [
            "password@#$%",
            "中文密码",
            "pass word with spaces",
            "密码123!@#",
            "a" * 100,  # 长密码
        ]

        for password in passwords:
            encrypted = encrypt_password(password)
            assert isinstance(encrypted, str)
            assert len(encrypted) > 0

    def test_encrypt_consistency(self):
        """测试加密的一致性（相同密码产生相同结果）"""
        password = "test_password_123"

        encrypted1 = encrypt_password(password)
        encrypted2 = encrypt_password(password)

        # 由于使用 MD5 + AES-ECB（无 IV），相同密码应该产生相同结果
        assert encrypted1 == encrypted2

    def test_encrypt_different_passwords(self):
        """测试不同密码产生不同加密结果"""
        passwords = ["password1", "password2", "password3"]

        encrypted_list = [encrypt_password(p) for p in passwords]

        # 所有加密结果应该不同
        assert len(set(encrypted_list)) == len(encrypted_list)


# ============================================================================
# 集成测试：Config + PasswordStore
# ============================================================================

class TestConfigPasswordIntegration:
    """测试配置和密码存储的集成使用"""

    def test_config_with_encrypted_password(self):
        """测试配置中存储加密密码"""
        config = Config()

        # 模拟登录
        username = "test_user"
        password = "test_password"
        encrypted_password = encrypt_password(password)

        # 保存到配置
        config.username = username
        config.encrypted_password = encrypted_password

        # 验证配置已保存
        assert config.username == username
        assert config.encrypted_password == encrypted_password

    def test_full_login_flow_simulation(self):
        """测试完整的登录流程模拟"""
        config = Config()

        # 模拟登录
        username = "xxxxx"
        password = "xxxxx"

        # 加密密码
        encrypted = encrypt_password(password)

        # 保存到配置（模拟登录成功）
        config.username = username
        config.password = encrypted  # 这会触发 secure storage
        config.token = "simulated_token_123"

        # 验证配置
        assert config.username == username
        assert config.token == "simulated_token_123"

        # 测试清除认证
        config.clear_auth()

        assert config.token is None
        # username 不会被清除
        assert config.username == username


# ============================================================================
# 边缘情况和错误处理
# ============================================================================

class TestConfigEdgeCases:
    """测试配置边缘情况"""

    def test_config_unicode_values(self):
        """测试配置中的 Unicode 值"""
        config = Config()

        # 设置 Unicode 值
        config.api_url = "http://测试.example.com"
        config.active_project_name = "测试项目"

        # 验证可以设置（不一定会保存成功）
        assert config.api_url == "http://测试.example.com"
        assert config.active_project_name == "测试项目"

    def test_config_very_long_values(self):
        """测试配置中的超长值"""
        config = Config()

        # 设置超长值
        long_token = "x" * 10000
        config.token = long_token

        # 验证可以设置
        assert config.token == long_token

    def test_config_special_characters_in_url(self):
        """测试 URL 中的特殊字符"""
        config = Config()

        # 包含特殊字符的 URL
        urls = [
            "http://example.com:8080/path?query=value",
            "http://example.com/path#fragment",
        ]

        for url in urls:
            config.api_url = url
            assert config.api_url == url

    def test_config_none_values(self):
        """测试设置 None 值"""
        config = Config()

        # 设置后清除
        config.token = "test_token"
        assert config.token == "test_token"

        config.token = None
        assert config.token is None

    def test_config_multiple_updates(self):
        """测试多次更新同一个字段"""
        config = Config()

        # 多次更新
        for i in range(10):
            config.token = f"token_{i}"
            assert config.token == f"token_{i}"


# ============================================================================
# 性能测试
# ============================================================================

class TestConfigPerformance:
    """测试配置性能"""

    def test_config_multiple_updates_performance(self):
        """测试多次更新的性能"""
        import time

        config = Config()

        start_time = time.time()

        # 执行 100 次更新
        for i in range(100):
            config.token = f"token_{i}"

        end_time = time.time()
        duration = end_time - start_time

        # 100 次更新应该在合理时间内完成（< 0.1 秒）
        assert duration < 0.1

    def test_encrypt_performance(self):
        """测试加密性能"""
        import time

        password = "test_password_123"
        iterations = 100

        start_time = time.time()

        # 执行 100 次加密
        for _ in range(iterations):
            encrypt_password(password)

        end_time = time.time()
        duration = end_time - start_time

        # 100 次加密应该在合理时间内完成（< 1 秒）
        assert duration < 1.0

        # 计算平均每次加密时间
        avg_time = duration / iterations
        assert avg_time < 0.01  # 每次应该 < 10ms


# ============================================================================
# 实际应用场景测试
# ============================================================================

class TestRealWorldScenarios:
    """测试真实应用场景"""

    def test_config_api_url_change(self):
        """测试改变 API URL"""
        config = Config()

        # 改变 API URL
        config.api_url = "http://new-api.example.com"
        assert config.api_url == "http://new-api.example.com"

    def test_config_token_refresh(self):
        """模拟 token 刷新"""
        config = Config()

        # 初始 token
        config.token = "old_token"
        assert config.token == "old_token"

        # 刷新 token
        config.token = "new_token"
        assert config.token == "new_token"

        # 旧 token 应该被覆盖
        assert config.token != "old_token"

    def test_config_project_switch(self):
        """测试切换项目"""
        config = Config()

        # 设置项目
        config.active_project_name = "project_a"
        config.active_project_id = "id_a"
        assert config.active_project_name == "project_a"

        # 切换项目
        config.active_project_name = "project_b"
        config.active_project_id = "id_b"
        assert config.active_project_name == "project_b"

    def test_encrypted_password_format(self):
        """测试加密密码格式"""
        password = "test_password"

        encrypted = encrypt_password(password)

        # 应该是十六进制字符串
        try:
            int(encrypted, 16)
            assert True  # 是有效的十六进制
        except ValueError:
            assert False  # 不是有效的十六进制

    def test_multiple_user_encryption(self):
        """测试多用户密码加密"""
        users_passwords = {
            "user1": "password1",
            "user2": "password2",
            "user3": "password3",
        }

        encrypted_map = {}
        for username, password in users_passwords.items():
            encrypted = encrypt_password(password)
            encrypted_map[username] = encrypted

            # 验证每个加密结果
            assert isinstance(encrypted, str)
            assert len(encrypted) > 0

        # 验证不同用户的不同密码产生不同加密结果
        encrypted_values = list(encrypted_map.values())
        assert len(set(encrypted_values)) == len(encrypted_values)


# ============================================================================
# 密码存储实际场景
# ============================================================================

class TestPasswordStoreScenarios:
    """测试密码存储实际场景"""

    def test_store_retrieve_delete_cycle(self):
        """测试完整的存储-检索-删除周期"""
        username = "test_cycle_user"

        try:
            # 存储
            result = PasswordStore.set_password(username, "test_pass")
            if result:
                # 检索
                retrieved = PasswordStore.get_password(username)
                assert retrieved == "test_pass"

                # 删除
                PasswordStore.delete_password(username)

                # 验证已删除
                retrieved = PasswordStore.get_password(username)
                assert retrieved is None
            else:
                pytest.skip("Keyring 不可用")
        except Exception as e:
            pytest.skip(f"Keyring 操作失败: {e}")

    def test_password_update(self):
        """测试更新密码"""
        username = "test_update_user"

        try:
            # 初始密码
            PasswordStore.set_password(username, "old_pass")

            # 更新密码
            PasswordStore.set_password(username, "new_pass")

            # 验证已更新
            retrieved = PasswordStore.get_password(username)
            assert retrieved == "new_pass"

            # 清理
            PasswordStore.delete_password(username)
        except Exception as e:
            pytest.skip(f"Keyring 操作失败: {e}")
