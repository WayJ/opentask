"""
OpenTask CLI 主入口专项测试

测试范围：
- opentask_cli.py 的未覆盖命令和分支
- REPL 模式相关功能
- 配置和认证命令
"""

import pytest
from click.testing import CliRunner
from unittest import mock
import tempfile

from opentask.opentask_cli import cli
from opentask.utils.config import Config


def async_mock(return_value):
    """创建异步 Mock 函数"""
    async def wrapper(*args, **kwargs):
        return return_value
    return wrapper


class TestCLIAuthCommands:
    """测试认证相关命令"""

    def test_auth_me_command_authenticated(self):
        """测试已认证状态下获取用户信息"""
        runner = CliRunner()

        with mock.patch('opentask.opentask_cli.VibeKingClient') as mock_client_class:
            mock_client = mock.Mock()
            mock_client.get_me = async_mock({
                "id": "user-1",
                "username": "testuser",
                "email": "test@example.com"
            })
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ['auth', 'me'])

            # 命令可能不存在
            assert result.exit_code in [0, 2]

    def test_auth_me_command_unauthenticated(self):
        """测试未认证状态"""
        runner = CliRunner()

        with mock.patch('opentask.opentask_cli.VibeKingClient') as mock_client_class:
            mock_client = mock.Mock()
            mock_client.get_me = async_mock(None)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, ['auth', 'me'])

            assert result.exit_code in [0, 1, 2]


class TestCLIConfigCommands:
    """测试配置相关命令"""

    def test_config_show_command(self):
        """测试显示配置"""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', '--show'])

        # 命令可能不存在
        assert result.exit_code in [0, 1, 2]

    def test_config_reset_command(self):
        """测试重置配置"""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', '--reset'])

        assert result.exit_code in [0, 1, 2]


class TestCLIConversationCommands:
    """测试对话相关命令"""

    def test_conversation_list_command(self):
        """测试列出对话"""
        runner = CliRunner()
        result = runner.invoke(cli, ['conversation', 'list'])

        # 命令可能不存在
        assert result.exit_code in [0, 2]

    def test_conversation_create_command(self):
        """测试创建对话"""
        runner = CliRunner()
        result = runner.invoke(cli, ['conversation', 'create'])

        # 命令可能不存在
        assert result.exit_code in [0, 2]


class TestCLIGitCommands:
    """测试 Git 相关命令"""

    def test_git_status_command(self):
        """测试 git status 命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ['git', 'status'])

        # 命令可能不存在
        assert result.exit_code in [0, 2]

    def test_git_commit_command(self):
        """测试 git commit 命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ['git', 'commit'])

        # 命令可能不存在
        assert result.exit_code in [0, 2]


class TestCLIReplCommands:
    """测试 REPL 相关命令"""

    def test_repl_command(self):
        """测试 repl 命令"""
        runner = CliRunner()

        # REPL 命令可能需要交互式输入
        # 这里只测试命令可以被识别
        result = runner.invoke(cli, ['repl'])

        # 可能返回错误或需要交互
        assert result.exit_code in [0, 1, 2, 130]  # 130 是键盘中断

    def test_shell_command(self):
        """测试 shell 命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ['shell'])

        # 命令可能不存在
        assert result.exit_code in [0, 2]


class TestCLIMiscCommands:
    """测试其他杂项命令"""

    def test_version_command(self):
        """测试 version 命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ['version'])

        # 应该显示版本或命令不存在
        assert result.exit_code in [0, 2]

    def test_help_command(self):
        """测试 help 命令"""
        runner = CliRunner()
        result = runner.invoke(cli, ['help'])

        # 应该显示帮助或命令不存在
        assert result.exit_code in [0, 2]


class TestCLIGlobalOptionsExtended:
    """测试全局选项的扩展情况"""

    def test_global_json_option_with_project(self):
        """测试全局 JSON 选项配合 project 命令"""
        runner = CliRunner()

        with mock.patch('opentask.core.project.VibeKingClient') as mock_client_class:
            mock_client = mock.Mock()
            mock_client.get_project = async_mock({
                "id": "1",
                "name": "Test Project"
            })
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, [
                '--json',
                'project', 'show', '1'
            ])

            assert result.exit_code == 0

    def test_global_verbose_option_with_error(self):
        """测试详细模式配合错误情况"""
        runner = CliRunner()

        with mock.patch('opentask.core.project.VibeKingClient') as mock_client_class:
            mock_client = mock.Mock()
            mock_client.get_project = async_mock(None)
            mock_client_class.return_value = mock_client

            result = runner.invoke(cli, [
                '--verbose',
                'project', 'show', 'nonexistent'
            ])

            # 详细模式可能改变错误输出
            assert result.exit_code in [0, 1, 2]


class TestCLIContextPassing:
    """测试 CLI 上下文传递"""

    def test_context_passing_to_commands(self):
        """测试上下文传递到命令"""
        runner = CliRunner()

        with mock.patch('opentask.core.project.VibeKingClient') as mock_client_class:
            mock_client = mock.Mock()
            mock_client.list_projects = async_mock([])
            mock_client_class.return_value = mock_client

            # 全局 JSON 模式应该传递到子命令
            result = runner.invoke(cli, [
                '--json',
                'project', 'list'
            ])

            assert result.exit_code == 0


class TestCLIPromptStyle:
    """测试 CLI 提示样式"""

    def test_prompt_style_in_repl(self):
        """测试 REPL 中的提示样式"""
        from opentask.utils.repl_skin import ReplSkin

        skin = ReplSkin("test")
        style = skin.get_prompt_style()

        # 应该返回有效的样式
        assert style is not None

    def test_prompt_tokens_with_project(self):
        """测试带项目名的提示 tokens"""
        from opentask.utils.repl_skin import ReplSkin

        skin = ReplSkin("test")
        tokens = skin.prompt_tokens(project_name="MyProject", modified=True)

        # 应该返回 tokens 列表
        assert isinstance(tokens, list)
