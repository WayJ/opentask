"""``scripts/create_admin_user.py`` 的单元测试。

只覆盖**不碰数据库**的部分：口令生成器与命令行契约。
建号本身依赖真实数据库连接（脚本走全局 ``SessionCreator``，绑的是配置里的 DSN
而不是测试库），因此不在单测里跑——它由发布流程在目标库上真实执行，
证据见 ``deploy/README.md``。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "create_admin_user.py"


def _load_module():
    """按文件路径加载脚本（scripts/ 不是包，没有 __init__.py）"""
    spec = importlib.util.spec_from_file_location("create_admin_user", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def module():
    return _load_module()


def test_generate_password_length_and_charset(module):
    """生成的口令长度固定，且字符集避开易混淆的 0/O/1/l"""
    allowed = set("abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#%*-_")
    for _ in range(50):
        pwd = module.generate_password()
        assert len(pwd) == 20
        assert set(pwd) <= allowed
        # 不含易混淆字符
        assert not (set(pwd) & set("01lIO"))


def test_generate_password_is_random(module):
    """两次生成不应相同（随机源有效）"""
    assert module.generate_password() != module.generate_password()


def test_script_exposes_expected_cli(module):
    """脚本应提供 main 入口（供 `python scripts/create_admin_user.py` 调用）"""
    assert callable(module.main)


def test_script_is_idempotent_by_default(module):
    """--reset-password 默认为 False：账号已存在时跳过而非覆盖口令"""
    parser = module.build_parser()
    assert parser.parse_args([]).reset_password is False
    assert parser.parse_args(["--reset-password"]).reset_password is True


def test_cli_defaults(module):
    """不传参时的默认契约：用户名 admin、口令由脚本生成、显示名留空、不跳过工作区"""
    args = module.build_parser().parse_args([])
    assert args.username is None          # main() 里回落到 "admin"
    assert args.password is None          # main() 里生成随机口令
    assert args.name is None
    assert args.workspace_name == "OpenTask"
    assert args.skip_workspace is False
    assert args.reset_password is False
