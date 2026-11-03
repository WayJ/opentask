"""登录口令传输加密（RSA-OAEP）的单元测试。

覆盖：
- 加密 → 解密往返（模拟前端 node-forge 的 RSA-OAEP/SHA-256 密文）
- 明文载荷解不开时返回 None（调用方据此回退按明文处理）
- 没有密钥文件时返回 None
- 公钥导出格式（base64 SPKI DER）能被前端还原成 PEM

注：前端用 node-forge 加密、服务端用 cryptography 解密，两边的 OAEP 参数
（SHA-256 + MGF1-SHA256 + 空 label）必须一致——这里用 cryptography 按同样的
参数造密文，等价于前端的产出。
"""

from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from opentask.utils import login_crypto
from opentask.utils.login_crypto import (
    decrypt_login_payload,
    generate_keypair,
    public_key_b64,
)

_OAEP = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)


@pytest.fixture()
def keypair(tmp_path, monkeypatch):
    """生成一对密钥，并让 login_crypto 指向它"""
    priv = tmp_path / "login_private.pem"
    pub = tmp_path / "login_public.pem"
    generate_keypair(priv, pub)

    monkeypatch.setattr(login_crypto, "private_key_path", lambda: priv)
    monkeypatch.setattr(login_crypto, "public_key_path", lambda: pub)
    login_crypto.reload_private_key()
    yield priv, pub
    login_crypto.reload_private_key()


def _encrypt_like_frontend(priv_path, plaintext: str) -> str:
    """按前端（node-forge RSA-OAEP/SHA-256）的口径造一份密文"""
    key = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
    ciphertext = key.public_key().encrypt(plaintext.encode("utf-8"), _OAEP)
    return base64.b64encode(ciphertext).decode("ascii")


def test_roundtrip(keypair):
    """加密 → 解密 → 明文一致"""
    priv, _ = keypair
    payload = _encrypt_like_frontend(priv, "my-secret-password")
    assert decrypt_login_payload(payload) == "my-secret-password"


def test_unicode_password(keypair):
    """非 ASCII 口令也能正确往返"""
    priv, _ = keypair
    payload = _encrypt_like_frontend(priv, "口令-密码-123")
    assert decrypt_login_payload(payload) == "口令-密码-123"


def test_plaintext_payload_returns_none(keypair):
    """明文载荷解不开 → 返回 None（调用方回退按明文处理）"""
    assert decrypt_login_payload("123456") is None


def test_garbage_payload_returns_none(keypair):
    """非法 base64 / 乱码 → None，不抛异常"""
    assert decrypt_login_payload("!!!not-base64!!!") is None
    assert decrypt_login_payload(base64.b64encode(b"x" * 256).decode()) is None


def test_empty_payload_returns_none(keypair):
    assert decrypt_login_payload("") is None


def test_missing_key_file_returns_none(tmp_path, monkeypatch):
    """没有私钥文件 → None（未配置密钥的环境照常按明文工作）"""
    monkeypatch.setattr(login_crypto, "private_key_path", lambda: tmp_path / "nope.pem")
    login_crypto.reload_private_key()
    assert decrypt_login_payload("anything") is None


def test_public_key_is_base64_spk_der(keypair):
    """公钥导出为 base64 的 SPKI DER——前端据此还原 PEM 交给 node-forge"""
    priv, pub = keypair
    b64 = public_key_b64()
    assert b64

    der = base64.b64decode(b64)
    key = serialization.load_der_public_key(der)
    assert key.public_numbers() == serialization.load_pem_public_key(
        pub.read_bytes()
    ).public_numbers()


def test_public_key_matches_private(keypair):
    """公钥与私钥是一对（否则前端加密的密文服务端解不开）"""
    priv, pub = keypair
    private_key = serialization.load_pem_private_key(priv.read_bytes(), password=None)
    public_key = serialization.load_pem_public_key(pub.read_bytes())
    assert private_key.public_key().public_numbers() == public_key.public_numbers()
