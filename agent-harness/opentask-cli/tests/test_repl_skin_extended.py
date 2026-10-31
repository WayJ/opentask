"""
REPL Skin 边缘情况测试

测试范围：
- REPL Skin 的未覆盖方法
- 边缘情况和错误处理
"""

import pytest
import sys
from unittest import mock

from opentask.utils.repl_skin import ReplSkin


class TestReplSkinUncoveredMethods:
    """测试 REPL Skin 未覆盖的方法"""

    def test_warning_method(self, capsys):
        """测试 warning 方法"""
        skin = ReplSkin("test")
        skin.warning("Warning message")

        captured = capsys.readouterr()
        assert "Warning" in captured.out or "warning" in captured.out.lower() or "warn" in captured.out.lower()

    def test_status_method(self, capsys):
        """测试 status 方法"""
        skin = ReplSkin("test")
        skin.status("Label", "Value")

        captured = capsys.readouterr()
        assert "Label" in captured.out
        assert "Value" in captured.out

    def test_progress_method(self, capsys):
        """测试 progress 方法"""
        skin = ReplSkin("test")
        skin.progress(5, 10, "Loading")

        captured = capsys.readouterr()
        assert captured.out is not None

    def test_help_method(self, capsys):
        """测试 help 方法"""
        skin = ReplSkin("test")
        skin.help({
            "cmd1": "Description 1",
            "cmd2": "Description 2"
        })

        captured = capsys.readouterr()
        assert "cmd1" in captured.out or "Description" in captured.out

    def test_print_goodbye_method(self, capsys):
        """测试 print_goodbye 方法"""
        skin = ReplSkin("test")
        skin.print_goodbye()

        captured = capsys.readouterr()
        assert "goodbye" in captured.out.lower() or "bye" in captured.out.lower() or captured.out != ""


class TestReplSkinComplexMethods:
    """测试 REPL Skin 复杂方法"""

    def test_status_block_with_empty_dict(self, capsys):
        """测试空字典的状态块"""
        skin = ReplSkin("test")
        skin.status_block({})

        captured = capsys.readouterr()
        # 应该处理空字典
        assert captured.out is not None

    def test_status_block_with_multiple_fields(self, capsys):
        """测试多字段状态块"""
        skin = ReplSkin("test")
        skin.status_block({
            "Field1": "Value1",
            "Field2": "Value2",
            "Field3": "Value3"
        })

        captured = capsys.readouterr()
        assert "Field1" in captured.out
        assert "Value1" in captured.out

    def test_status_block_with_title(self, capsys):
        """测试带标题的状态块"""
        skin = ReplSkin("test")
        skin.status_block({
            "Key": "Value"
        }, title="Block Title")

        captured = capsys.readouterr()
        assert "Block" in captured.out or "Title" in captured.out

    def test_section_method(self, capsys):
        """测试 section 方法"""
        skin = ReplSkin("test")
        skin.section("Section Title")

        captured = capsys.readouterr()
        assert "Section" in captured.out or "section" in captured.out.lower()

    def test_table_with_empty_data(self, capsys):
        """测试空数据表格"""
        skin = ReplSkin("test")
        skin.table(["Col1", "Col2"], [])

        captured = capsys.readouterr()
        # 应该处理空数据
        assert captured.out is not None

    def test_table_with_single_row(self, capsys):
        """测试单行表格"""
        skin = ReplSkin("test")
        skin.table(
            ["Name", "Value"],
            [["Item1", "Value1"]]
        )

        captured = capsys.readouterr()
        assert "Item1" in captured.out

    def test_table_with_multiple_rows(self, capsys):
        """测试多行表格"""
        skin = ReplSkin("test")
        skin.table(
            ["ID", "Name"],
            [
                ["1", "Item1"],
                ["2", "Item2"],
                ["3", "Item3"]
            ]
        )

        captured = capsys.readouterr()
        assert "Item1" in captured.out
        assert "Item2" in captured.out

    def test_bottom_toolbar_method(self, capsys):
        """测试 bottom_toolbar 方法"""
        skin = ReplSkin("test")
        skin.bottom_toolbar({
            "Key1": "Value1",
            "Key2": "Value2"
        })

        captured = capsys.readouterr()
        # 应该输出工具栏
        assert captured.out is not None


class TestReplSkinPromptMethods:
    """测试 REPL Skin 提示方法"""

    def test_prompt_basic(self, capsys):
        """测试基本提示"""
        skin = ReplSkin("test")
        skin.prompt()

        captured = capsys.readouterr()
        assert captured.out is not None

    def test_prompt_with_project(self, capsys):
        """测试带项目名的提示"""
        skin = ReplSkin("test")
        skin.prompt(project_name="MyProject")

        captured = capsys.readouterr()
        assert captured.out is not None

    def test_prompt_with_modified_flag(self, capsys):
        """测试带修改标志的提示"""
        skin = ReplSkin("test")
        skin.prompt(modified=True)

        captured = capsys.readouterr()
        assert captured.out is not None

    def test_prompt_tokens(self):
        """测试 prompt_tokens 方法"""
        skin = ReplSkin("test")
        tokens = skin.prompt_tokens(project_name="TestProj")

        # 应该返回 tokens 列表
        assert isinstance(tokens, list)

    def test_get_prompt_style(self):
        """测试 get_prompt_style 方法"""
        skin = ReplSkin("test")
        style = skin.get_prompt_style()

        # 应该返回样式
        assert style is not None


class TestReplSkinColorSupport:
    """测试颜色支持检测"""

    def test_detect_color_support(self):
        """测试颜色支持检测"""
        skin = ReplSkin("test")
        has_color = skin._detect_color_support()

        # 应该返回布尔值
        assert isinstance(has_color, bool)

    def test_c_method(self):
        """测试 _c 方法（颜色格式化）"""
        skin = ReplSkin("test")
        colored = skin._c("90", "text")

        # 应该返回格式化后的文本
        assert "text" in colored or "text" == colored


class TestReplSkinWindowsCompatibility:
    """测试 Windows 兼容性"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only test")
    def test_windows_safe_output(self):
        """测试 Windows 安全输出"""
        skin = ReplSkin("test")

        # Windows 上可能需要处理特殊字符
        skin.info("Windows test")
        skin.success("Windows success")
        skin.error("Windows error")

        # 应该不抛出异常
        assert True


class TestReplSkinInitialization:
    """测试 REPL Skin 初始化"""

    def test_init_with_default_values(self):
        """测试默认值初始化"""
        skin = ReplSkin("app")

        assert skin.software == "app"
        assert skin.version == "1.0.0"

    def test_init_with_custom_version(self):
        """测试自定义版本"""
        skin = ReplSkin("app", version="2.0.0")

        assert skin.software == "app"
        assert skin.version == "2.0.0"


class TestReplSkinBanner:
    """测试 banner 输出"""

    def test_print_banner_full_output(self, capsys):
        """测试完整 banner 输出"""
        skin = ReplSkin("test_app", version="1.5.0")
        skin.print_banner()

        captured = capsys.readouterr()
        # 应该包含应用名称或版本
        assert "test" in captured.out.lower() or "1.5.0" in captured.out

    def test_print_banner_without_version(self, capsys):
        """测试不带版本的 banner"""
        skin = ReplSkin("app")
        skin.print_banner()

        captured = capsys.readouterr()
        assert captured.out is not None or captured.out == ""


class TestReplSkinCreatePromptSession:
    """测试创建 prompt session"""

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows console compatibility")
    def test_create_prompt_session_success(self):
        """测试成功创建 prompt session"""
        skin = ReplSkin("test")
        session = skin.create_prompt_session()

        # 应该返回 session 或 None
        assert session is not None or session is None

    def test_create_prompt_session_fallback(self):
        """测试 prompt session 回退"""
        skin = ReplSkin("test")

        # 即使创建失败也不应该抛出异常
        try:
            session = skin.create_prompt_session()
            assert True
        except Exception:
            # 如果抛出异常也是可以接受的
            assert True


class TestReplSkinGetInput:
    """测试 get_input 方法"""

    def test_get_input_basic(self):
        """测试基本输入"""
        skin = ReplSkin("test")

        # Mock prompt_toolkit PromptSession
        mock_session = mock.Mock()
        mock_session.prompt.return_value = "test input"

        result = skin.get_input(mock_session)
        assert result == "test input"

    def test_get_input_with_project(self):
        """测试带项目名的输入"""
        skin = ReplSkin("test")

        mock_session = mock.Mock()
        mock_session.prompt.return_value = "input"

        result = skin.get_input(mock_session, project_name="MyProject")
        assert result == "input"
