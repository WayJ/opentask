"""登录口令的非对称加密（RSA-OAEP）。

## 为什么是非对称

旧版的 ``frontend/src/utils/encrypt.ts`` 用的是**共享密钥**（AES-ECB，密钥 =
MD5(VITE_CIPHER_KEY)）——那份密钥要打进前端 bundle，任何人打开开发者工具就能抠
出来，于是「加密的密码」和明文密码对中间人而言没有区别（这条已登记为 TD10）。

这里改成非对称：

- **私钥**只存在于服务端（``<DATA_DIRECTORY>/login_private.pem``，chmod 600）
- **公钥**打进前端 bundle（``VITE_LOGIN_PUBLIC_KEY``，SPKI DER 的 base64）

于是抓包拿到密文的人，没有私钥就解不开口令。

## 密文格式

RSA-OAEP / SHA-256（MGF1-SHA256），输出 base64。前端用 Web Crypto 的
``crypto.subtle``（原生实现，无需引依赖）::

    const key = await crypto.subtle.importKey('spki', der, {name:'RSA-OAEP', hash:'SHA-256'}, false, ['encrypt'])
    const ct  = await crypto.subtle.encrypt({name:'RSA-OAEP'}, key, new TextEncoder().encode(password))

2048 位密钥的单次明文上限 190 字节——口令远小于此。

## 与明文提交的兼容

服务端解密失败时**回退按明文处理**（返回 ``None``）：

- CLI 等未接入加密的客户端仍可明文登录
- 未配置密钥对的环境（本地开发）照常工作
- 前端未拿到公钥时也照常发明文

因此这是一层**渐进增强**，不是硬切换。
"""

from __future__ import annotations

import base64
import binascii
from functools import lru_cache
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from opentask.config import config

# 密钥对的文件名（相对 DATA_DIRECTORY）
PRIVATE_KEY_FILENAME = "login_private.pem"
PUBLIC_KEY_FILENAME = "login_public.pem"

# OAEP 参数：与前端 crypto.subtle 的默认保持一致（SHA-256 + MGF1-SHA256）
_OAEP = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)


def private_key_path() -> Path:
    """私钥文件路径（默认落在 DATA_DIRECTORY 下）"""
    return Path(config.login_private_key_path)


def public_key_path() -> Path:
    """公钥文件路径（与私钥同目录）"""
    return private_key_path().with_name(PUBLIC_KEY_FILENAME)


@lru_cache(maxsize=1)
def _load_private_key() -> rsa.RSAPrivateKey | None:
    """加载私钥；文件不存在或损坏时返回 None（此时登录走明文路径）"""
    path = private_key_path()
    if not path.is_file():
        return None
    try:
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    except Exception:  # noqa: BLE001 - 任何解析失败都按「没有密钥」处理
        return None
    return key if isinstance(key, rsa.RSAPrivateKey) else None


def reload_private_key() -> None:
    """清掉缓存（密钥轮换后调用）"""
    _load_private_key.cache_clear()


def decrypt_login_payload(payload: str) -> str | None:
    """尝试解密登录口令载荷。

    Returns:
        解密后的明文；**无法解密时返回 None**——调用方应据此回退按明文处理
        （兼容未接入加密的客户端与未配置密钥的环境）。
    """
    if not payload:
        return None

    key = _load_private_key()
    if key is None:
        return None

    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None

    try:
        plain = key.decrypt(raw, _OAEP)
    except (InvalidTag, ValueError, TypeError):
        # 不是我们签发的密文（多半是明文口令）→ 交给调用方按明文处理
        return None

    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError:
        return None


def public_key_b64() -> str | None:
    """公钥（SPKI DER 的 base64）——前端构建时注入 ``VITE_LOGIN_PUBLIC_KEY``"""
    path = public_key_path()
    if not path.is_file():
        return None
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(key, rsa.RSAPublicKey):
        return None
    der = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return base64.b64encode(der).decode("ascii")


def generate_keypair(private_path: Path, public_path: Path, key_size: int = 2048) -> None:
    """生成密钥对并落盘（私钥 600、公钥 644）"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)

    private_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    private_path.chmod(0o600)

    public_path.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    public_path.chmod(0o644)
