"""JWT 密钥配置测试：密钥必须来自配置，禁止公开默认值"""
import pytest


def test_secret_key_not_default():
    """SECRET_KEY 必须不等于历史公开默认值"""
    from opentask import jwt_utils
    assert jwt_utils.SECRET_KEY != "your-secret-key-here-change-in-production"


def test_secret_key_missing_raises(monkeypatch):
    """未配置 AUTH_SECRET_KEY 时访问 config.auth_secret_key 必须报错"""
    monkeypatch.delenv("AUTH_SECRET_KEY", raising=False)
    # 隔离 yaml 层（local.yaml 无论 APP_ENV 都会加载，仅 setenv APP_ENV 防不住）
    monkeypatch.setattr("opentask.config.load_config_file", lambda environment="development": {})
    from opentask.config import config
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY"):
        _ = config.auth_secret_key


def test_secret_key_missing_error_mentions_legacy_jwt_name(monkeypatch):
    """报错文案须提示旧环境变量名 JWT_SECRET_KEY 已废弃、应改为 AUTH_SECRET_KEY（J10）"""
    monkeypatch.delenv("AUTH_SECRET_KEY", raising=False)
    monkeypatch.setattr("opentask.config.load_config_file", lambda environment="development": {})
    from opentask.config import config
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY") as exc_info:
        _ = config.auth_secret_key
    assert "AUTH_SECRET_KEY" in str(exc_info.value)
    assert "废弃" in str(exc_info.value)
