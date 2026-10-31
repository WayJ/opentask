"""
REPL Skin 模块测试

测试范围：
- Skin 初始化
- 颜色支持检测
- Banner 输出
- Prompt 生成
- 消息格式化（success, error, warning, info）
- 辅助方法
"""

import sys
import pytest
from unittest import mock
from pathlib import Path

from opentask.utils.repl_skin import ReplSkin, _strip_ansi, _visible_len


# ============================================================================
# 辅助函数测试
# ============================================================================

class TestUtilityFunctions:
    """测试辅助函数"""

    def test_strip_ansi_removes_color_codes(self):
        """测试 ANSI 转义码移除"""
        text = "\033[38;5;80mHello\033[0m"
        result = _strip_ansi(text)
        assert result == "Hello"

    def test_strip_ansi_handles_plain_text(self):
        """测试处理纯文本"""
        text = "Plain text"
        result = _strip_ansi(text)
        assert result == "Plain text"

    def test_visible_len_excludes_ansi_codes(self):
        """测试可见长度计算（排除 ANSI 码）"""
        text = "\033[38;5;80mHello\033[0m"
        result = _visible_len(text)
        assert result == 5

    def test_visible_len_plain_text(self):
        """测试纯文本的可见长度"""
        text = "Hello"
        result = _visible_len(text)
        assert result == 5


# ============================================================================
# Skin 初始化测试
# ============================================================================

class TestSkinInitialization:
    """测试 Skin 初始化"""

    def test_init_with_defaults(self):
        """测试使用默认参数初始化"""
        skin = ReplSkin("test_software")
        assert skin.software == "test_software"
        assert skin.display_name == "Test Software"
        assert skin.version == "1.0.0"
        assert skin.history_file is not None

    def test_init_with_version(self):
        """测试带版本号初始化"""
        skin = ReplSkin("my_app", version="2.0.0")
        assert skin.version == "2.0.0"

    def test_init_normalizes_software_name(self):
        """测试软件名称标准化"""
        skin = ReplSkin("my_test_app")
        assert skin.software == "my_test_app"
        assert skin.display_name == "My Test App"

    def test_init_with_custom_history_file(self, tmp_path):
        """测试使用自定义历史文件"""
        history_file = tmp_path / "custom_history"
        skin = ReplSkin("test", history_file=str(history_file))
        assert skin.history_file == str(history_file)

    def test_init_creates_history_dir(self, tmp_path):
        """测试创建历史目录"""
        with mock.patch('pathlib.Path.home', return_value=tmp_path):
            skin = ReplSkin("test")
            hist_dir = tmp_path / ".opentask-test"
            assert hist_dir.exists()
            assert skin.history_file.endswith("history")


# ============================================================================
# 颜色支持检测测试
# ============================================================================

class TestColorDetection:
    """测试颜色支持检测"""

    def test_color_support_when_tty(self, monkeypatch):
        """测试 TTY 终端支持颜色"""
        with mock.patch('sys.stdout.isatty', return_value=True):
            skin = ReplSkin("test")
            assert skin._color is True

    def test_no_color_env_variable(self, monkeypatch):
        """测试 NO_COLOR 环境变量禁用颜色"""
        monkeypatch.setenv("NO_COLOR", "1")
        skin = ReplSkin("test")
        assert skin._color is False

    def test_opentask_no_color_env(self, monkeypatch):
        """测试 OPENTASK_NO_COLOR 环境变量"""
        monkeypatch.setenv("OPENTASK_NO_COLOR", "1")
        skin = ReplSkin("test")
        assert skin._color is False

    def test_no_color_when_not_tty(self, monkeypatch):
        """测试非 TTY 环境不使用颜色"""
        with mock.patch('sys.stdout.isatty', return_value=False):
            skin = ReplSkin("test")
            assert skin._color is False


# ============================================================================
# Banner 测试
# ============================================================================

class TestBanner:
    """测试 Banner 输出"""

    def test_print_banner_output(self, capsys):
        """测试 banner 输出"""
        skin = ReplSkin("test_app", version="1.5.0")
        skin.print_banner()

        captured = capsys.readouterr()
        output = captured.out

        # 验证包含关键信息
        assert "Test App" in output or "test_app" in output
        assert "1.5.0" in output
        assert "help" in output.lower()

    def test_banner_has_box_structure(self, capsys):
        """测试 banner 有边框结构"""
        skin = ReplSkin("test")
        skin.print_banner()

        captured = capsys.readouterr()
        output = captured.out

        # 验证有边框字符（Windows 或 Unix）
        has_box = any(char in output for char in ['-', '│', '╭', '╮', '╰', '╯'])
        assert has_box


# ============================================================================
# Prompt 测试
# ============================================================================

class TestPrompt:
    """测试 Prompt 生成"""

    def test_prompt_default(self):
        """测试默认 prompt"""
        skin = ReplSkin("test")
        prompt_text = skin.prompt()
        assert isinstance(prompt_text, str)
        assert len(prompt_text) > 0

    def test_prompt_with_project(self):
        """测试带项目名的 prompt"""
        skin = ReplSkin("test")
        prompt_text = skin.prompt(project_name="My Project")
        assert "My Project" in prompt_text or "my_project" in prompt_text

    def test_prompt_with_modified_marker(self):
        """测试带修改标记的 prompt"""
        skin = ReplSkin("test")
        prompt_text = skin.prompt(project_name="Test", modified=True)
        # 某种方式标记修改状态
        assert isinstance(prompt_text, str)

    def test_prompt_with_context(self):
        """测试带上下文的 prompt"""
        skin = ReplSkin("test")
        prompt_text = skin.prompt(context="[dev]")
        assert isinstance(prompt_text, str)

    def test_prompt_tokens_returns_list(self):
        """测试 prompt_tokens 返回列表"""
        skin = ReplSkin("test")
        tokens = skin.prompt_tokens(project_name="Test")
        assert isinstance(tokens, list)


# ============================================================================
# 消息格式化测试
# ============================================================================

class TestMessageFormatting:
    """测试消息格式化"""

    def test_success_message(self, capsys):
        """测试成功消息"""
        skin = ReplSkin("test")
        skin.success("Operation completed")

        captured = capsys.readouterr()
        assert "Operation completed" in captured.out

    def test_error_message(self, capsys):
        """测试错误消息"""
        skin = ReplSkin("test")
        skin.error("Something went wrong")

        captured = capsys.readouterr()
        # error 可能输出到 stderr
        assert "Something went wrong" in captured.out or "Something went wrong" in captured.err

    def test_warning_message(self, capsys):
        """测试警告消息"""
        skin = ReplSkin("test")
        skin.warning("Be careful")

        captured = capsys.readouterr()
        assert "Be careful" in captured.out

    def test_info_message(self, capsys):
        """测试信息消息"""
        skin = ReplSkin("test")
        skin.info("Processing...")

        captured = capsys.readouterr()
        assert "Processing..." in captured.out


# ============================================================================
# Help 和其他输出测试
# ============================================================================

class TestHelpAndOutput:
    """测试帮助和其他输出"""

    def test_help_output(self, capsys):
        """测试帮助输出"""
        skin = ReplSkin("test")
        commands = {"help": "Show help", "quit": "Exit"}
        skin.help(commands)

        captured = capsys.readouterr()
        output = captured.out
        # 应该显示命令列表
        assert "help" in output.lower() or "commands" in output.lower()

    def test_print_goodbye(self, capsys):
        """测试告别消息"""
        skin = ReplSkin("test")
        skin.print_goodbye()

        captured = capsys.readouterr()
        # 应该包含再见或退出相关消息
        output_lower = captured.out.lower()
        assert any(word in output_lower for word in ["goodbye", "exit", "quit", "bye"])


# ============================================================================
# 表格和状态测试
# ============================================================================

class TestTablesAndStatus:
    """测试表格和状态显示"""

    def test_table_output(self, capsys):
        """测试表格输出"""
        skin = ReplSkin("test")
        headers = ["Name", "Status"]
        rows = [
            ["Item 1", "Active"],
            ["Item 2", "Inactive"]
        ]
        skin.table(headers, rows)

        captured = capsys.readouterr()
        output = captured.out
        assert "Name" in output
        assert "Item 1" in output

    def test_status_output(self, capsys):
        """测试状态输出"""
        skin = ReplSkin("test")
        skin.status("Processing", "5 items")

        captured = capsys.readouterr()
        output = captured.out
        assert "Processing" in output


# ============================================================================
# 颜色应用测试
# ============================================================================

class TestColorApplication:
    """测试颜色应用"""

    def test_color_applied_when_enabled(self):
        """测试启用时应用颜色"""
        skin = ReplSkin("test")
        skin._color = True
        result = skin._c("\033[38;5;80m", "test")
        assert "\033[" in result
        assert "test" in result

    def test_color_not_applied_when_disabled(self):
        """测试禁用时不应用颜色"""
        skin = ReplSkin("test")
        skin._color = False
        result = skin._c("\033[38;5;80m", "test")
        assert result == "test"


# ============================================================================
# 边缘情况测试
# ============================================================================

class TestEdgeCases:
    """测试边缘情况"""

    def test_empty_project_name(self):
        """测试空项目名"""
        skin = ReplSkin("test")
        prompt = skin.prompt(project_name="")
        assert isinstance(prompt, str)

    def test_special_characters_in_messages(self, capsys):
        """测试消息中的特殊字符"""
        skin = ReplSkin("test")
        skin.success("Test with 'quotes' and \"double quotes\"")

        captured = capsys.readouterr()
        assert "quotes" in captured.out

    def test_unicode_in_messages(self, capsys):
        """测试消息中的 Unicode 字符"""
        skin = ReplSkin("test")
        skin.info("Testing 中文 🎉")

        captured = capsys.readouterr()
        assert "中文" in captured.out or "Testing" in captured.out

    def test_long_message(self, capsys):
        """测试长消息"""
        skin = ReplSkin("test")
        long_msg = "A" * 500
        skin.info(long_msg)

        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_software_name_with_hyphens(self):
        """测试带连字符的软件名"""
        skin = ReplSkin("my-test-app")
        # 连字符会被替换为下划线
        assert skin.software == "my_test_app"
        # display_name 保留连字符
        assert "My-Test-App" in skin.display_name


# ============================================================================
# Prompt Session 测试
# ============================================================================

class TestPromptSession:
    """测试 Prompt Session 创建"""

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows console compatibility")
    def test_create_prompt_session(self):
        """测试创建 prompt session"""
        skin = ReplSkin("test")
        session = skin.create_prompt_session()
        # 应该返回 None 或 session 对象
        assert session is None or hasattr(session, 'prompt')
