"""Token 安全工具函数

提供 JWT token 和 SSO token 的安全存储和验证功能。
"""
import hashlib
import base64
import os
from typing import Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from opentask.config import config


# ============================================================================
# JWT Token 指纹工具
# ============================================================================

def create_token_fingerprint(token: str) -> str:
    """生成 JWT token 的 SHA-256 指纹

    Args:
        token: JWT token 字符串

    Returns:
        64 字符的十六进制哈希字符串

    Example:
        >>> token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        >>> fingerprint = create_token_fingerprint(token)
        >>> print(fingerprint)
        'a1b2c3d4e5f6...'
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def verify_token_fingerprint(token: str, expected_fingerprint: str) -> bool:
    """验证 JWT token 指纹是否匹配

    Args:
        token: JWT token 字符串
        expected_fingerprint: 期望的指纹值

    Returns:
        True if 指纹匹配，False otherwise
    """
    actual_fingerprint = create_token_fingerprint(token)
    # 使用恒定时间比较防止时序攻击
    return _constant_time_compare(actual_fingerprint, expected_fingerprint)


def _constant_time_compare(a: str, b: str) -> bool:
    """恒定时间字符串比较，防止时序攻击

    Args:
        a: 字符串 a
        b: 字符串 b

    Returns:
        True if 完全相同，False otherwise
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a.encode(), b.encode()):
        result |= x ^ y
    return result == 0


# ============================================================================
# SSO Token 加密工具
# ============================================================================

def _get_encryption_key() -> bytes:
    """获取加密密钥

    从配置中读取密钥，如果不存在则生成新的。
    使用 PBKDF2 从配置密钥派生加密密钥。

    Returns:
        32 字节的 Fernet 密钥
    """
    # 从配置获取主密钥
    master_key = getattr(config, 'encryption_key', None) or os.getenv('ENCRYPTION_KEY')

    if not master_key:
        # 如果没有配置密钥，使用环境相关的默认值（仅用于开发环境）
        import warnings
        warnings.warn(
            "未配置 ENCRYPTION_KEY，使用不安全的默认密钥！"
            "请在生产环境中设置 ENCRYPTION_KEY 环境变量。"
        )
        master_key = "change-this-key-in-production"

    # 使用 PBKDF2HMAC 派生 32 字节密钥
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'opentask-sso-token-salt',  # 固定 salt，仅用于 token 加密
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    return key


def encrypt_sso_token(token: str) -> str:
    """加密 SSO token

    Args:
        token: 明文的 SSO token

    Returns:
        加密后的 token（Base64 编码）

    Example:
        >>> encrypted = encrypt_sso_token("bearer xxx")
        >>> print(encrypted)
        'gAAAAABh...'
    """
    key = _get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(token.encode('utf-8'))
    return encrypted.decode('utf-8')


def decrypt_sso_token(encrypted_token: str) -> str:
    """解密 SSO token

    Args:
        encrypted_token: 加密的 token

    Returns:
        明文的 SSO token

    Raises:
        ValueError: 如果解密失败（token 已损坏或密钥错误）
    """
    key = _get_encryption_key()
    f = Fernet(key)
    try:
        decrypted = f.decrypt(encrypted_token.encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to decrypt SSO token: {e}")


# ============================================================================
# Token 验证辅助函数
# ============================================================================

def validate_token_not_expired(
    expires_at: any,
    buffer_minutes: int = 5
) -> bool:
    """验证 token 是否未过期（带缓冲时间）

    Args:
        expires_at: token 过期时间（datetime 对象）
        buffer_minutes: 缓冲时间（分钟），默认 5 分钟

    Returns:
        True if token 未过期（包含缓冲时间），False otherwise
    """
    from datetime import datetime, timezone, timedelta

    if not expires_at:
        return False

    # 使用时区感知的当前时间
    now = datetime.now(timezone.utc)
    buffer = timedelta(minutes=buffer_minutes)

    # 如果过期时间在（当前时间 + 缓冲）之后，则认为未过期
    return expires_at > now + buffer


def get_token_remaining_time(expires_at: any) -> float:
    """获取 token 剩余有效时间（小时）

    Args:
        expires_at: token 过期时间（datetime 对象）

    Returns:
        剩余小时数，如果已过期返回 0
    """
    from datetime import datetime, timezone

    if not expires_at:
        return 0.0

    now = datetime.now(timezone.utc)
    if expires_at <= now:
        return 0.0

    delta = expires_at - now
    return delta.total_seconds() / 3600  # 转换为小时
