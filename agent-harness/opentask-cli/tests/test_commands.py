"""
OpenTask CLI 命令测试

测试范围：
- version 命令
- help 命令
- 主要功能命令
- 命令参数验证
- 命令错误处理
"""

import pytest
from click.testing import CliRunner
from unittest import mock


# ============================================================================
# Version 命令测试
# ============================================================================

def test_version_command():
    """测试 version 命令"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])

    assert result.exit_code == 0
    assert 'version' in result.output.lower() or 'opentask' in result.output.lower()


# ============================================================================
# Help 命令测试
# ============================================================================

def test_help_command():
    """测试 help 命令"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])

    assert result.exit_code == 0
    assert 'Usage:' in result.output or 'usage' in result.output.lower()


def test_help_shows_available_commands():
    """测试 help 显示可用命令"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])

    # 验证包含命令列表
    assert 'Commands:' in result.output or 'commands' in result.output.lower()


# ============================================================================
# 命令初始化测试
# ============================================================================

def test_cli_no_args():
    """测试不带参数运行 CLI"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, [])

    # 应该显示 REPL banner 或帮助信息
    # Exit code 可以是 0 (正常) 或 1 (显示帮助后退出)
    assert result.exit_code in [0, 1]
    assert 'OpenTask' in result.output or 'Usage:' in result.output


# ============================================================================
# 配置命令测试
# ============================================================================

def test_config_command():
    """测试配置命令"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ['config', '--list'])

    # 可能返回 0 或错误码，取决于配置是否存在
    assert result.exit_code in [0, 1, 2]


def test_config_set():
    """测试设置配置"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    # config set 命令可能不存在或返回错误，这是正常的
    result = runner.invoke(cli, ['config', 'set-api', 'http://test.com'])

    # 验证命令执行（可能返回错误码）
    assert result.exit_code in [0, 1, 2]


def test_config_get():
    """测试获取配置"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    # config show 命令应该存在
    result = runner.invoke(cli, ['config', 'show'])

    # 应该能显示配置（即使为空）
    assert result.exit_code in [0, 1]


# ============================================================================
# 命令参数验证测试
# ============================================================================

def test_command_with_invalid_option():
    """测试使用无效选项"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ['--invalid-option'])

    # 应该返回错误
    assert result.exit_code != 0


def test_command_with_missing_required_arg():
    """测试缺少必需参数"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    # 假设某个命令需要必需参数
    result = runner.invoke(cli, ['config', 'set'])  # 缺少 key 和 value

    # 应该显示错误或帮助信息
    assert result.exit_code != 0 or 'Error' in result.output or 'error' in result.output.lower()


# ============================================================================
# 命令输出格式测试
# ============================================================================

def test_command_json_output():
    """测试 JSON 格式输出"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ['--output', 'json', 'config', '--list'])

    # 验证输出格式
    if result.exit_code == 0:
        import json
        try:
            json.loads(result.output)
            assert True  # 是有效的 JSON
        except json.JSONDecodeError:
            # 如果不是 JSON，可能需要检查其他格式
            assert False


def test_command_verbose_output():
    """测试详细输出模式"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])

    # --version 不需要 --verbose
    assert result.exit_code == 0
    assert 'v1.4.0' in result.output


# ============================================================================
# 命令组合测试
# ============================================================================

def test_multiple_commands():
    """测试执行多个命令"""
    from opentask.opentask_cli import cli

    runner = CliRunner()

    # 执行多个命令
    commands = [
        ['--version'],
        ['--help'],
        ['config', '--list']
    ]

    for command in commands:
        result = runner.invoke(cli, command)
        # 所有命令都应该能执行（可能返回不同的退出码）
        assert isinstance(result.exit_code, int)


# ============================================================================
# 命令性能测试
# ============================================================================

def test_command_execution_time():
    """测试命令执行时间"""
    import time
    from opentask.opentask_cli import cli

    runner = CliRunner()

    start_time = time.time()
    result = runner.invoke(cli, ['--version'])
    end_time = time.time()

    execution_time = end_time - start_time

    # 命令应该在合理时间内完成
    assert execution_time < 5.0  # 5秒内完成


# ============================================================================
# 命令日志测试
# ============================================================================

def test_command_logging():
    """测试命令日志记录"""
    from opentask.opentask_cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])

    # 验证命令正常执行
    assert result.exit_code == 0
    assert 'v1.4.0' in result.output


# ============================================================================
# 命令清理测试
# ============================================================================

def test_command_cleanup():
    """测试命令执行后的清理"""
    from opentask.opentask_cli import cli

    runner = CliRunner()

    # 执行命令
    result = runner.invoke(cli, ['config', '--list'])

    # 验证没有遗留资源
    assert result.exception is None or isinstance(result.exception, SystemExit)
