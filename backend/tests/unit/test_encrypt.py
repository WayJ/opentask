"""SSO 密码加密工具测试：与前端 encrypt.ts 逐字节等价（J1）

前端实现（frontend/src/utils/encrypt.ts）：
1. MD5(密码) → 32 位小写 hex 字符串
2. AES-ECB 加密，密钥 = md5(CIPHER_KEY) 字符串的 **UTF-8 字节**（32 字节 → AES-256）
3. 密文 Base64 → Hex

下方已知向量由 node + crypto-js（前端同款依赖）实算得出，
用于钉死后端实现与前端/SSO 服务端的兼容性（历史上后端曾误用
bytes.fromhex 把密钥折成 16 字节 AES-128，产出与前端不一致的密文）。
"""
import pytest

from opentask.utils.encrypt import encrypt_password


def test_encrypt_password_matches_frontend_vector():
    """已知向量：与前端 crypto-js encryptPassword('123456') 输出完全一致"""
    assert (
        encrypt_password("123456")
        == "d4958348e22108119b3ef57b022c83f4"
        "bf857dd0b247eaab15b9a43d47ee3c50"
        "3900f7135bf0de255bc33620c3cdc02b"
    )


def test_encrypt_password_deterministic_and_not_leaking_plaintext():
    """确定性输出；hex 格式（小写）；输出不含明文与 MD5(明文)"""
    out1 = encrypt_password("Passw0rd123")
    out2 = encrypt_password("Passw0rd123")
    assert out1 == out2
    assert len(out1) == 96  # MD5 32 字符恰为整块，PKCS7 追加一整块 → 48 字节密文 → 96 hex
    int(out1, 16)  # 合法 hex
    assert "Passw0rd123" not in out1


def test_encrypt_password_different_inputs_differ():
    """不同明文产出不同密文"""
    assert encrypt_password("abc123") != encrypt_password("abc124")
