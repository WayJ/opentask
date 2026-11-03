"""
密码加密工具（Python 版本）

SSO 密码加密流程：
1. 对明文密码进行 MD5 加密
2. 使用 AES-ECB 模式加密（密钥为 MD5(VITE_CIPHER_KEY)）
3. 直接返回加密结果的 Hex 格式
"""
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# 密钥配置（与前端保持一致）
CIPHER_KEY = "EY8WePvjM5GGwQzn"


def encrypt_password(password: str) -> str:
    """
    SSO 密码加密

    .. deprecated::
        Phase 2 起后端默认走本地 bcrypt 校验（sso_enabled=false），
        登录密码以明文提交，不再需要 SSO 加密。本函数仅保留用于
        兼容旧的集成环境，后续版本可能移除。

    Args:
        password: 明文密码

    Returns:
        加密后的密码（Hex格式，直接是加密结果的 hex）
    """
    # 1. MD5 加密密码
    md5_password = hashlib.md5(password.encode()).hexdigest()

    # 2. AES 密钥（MD5 of CIPHER_KEY）
    # 注意：这里用 hexdigest() 然后 encode()，相当于 Node.js 的 Utf8.parse(md5())
    aes_key = hashlib.md5(CIPHER_KEY.encode()).hexdigest()

    # 3. AES-ECB 加密
    # 关键：Key 是 MD5 hex 字符串的 UTF-8 字节，不是 bytes.fromhex()
    key_bytes = aes_key.encode('utf-8')  # 相当于 Node.js 的 Utf8.parse()
    cipher = AES.new(key_bytes, AES.MODE_ECB)
    padded_data = pad(md5_password.encode('utf-8'), AES.block_size)
    encrypted = cipher.encrypt(padded_data)

    # 4. 直接返回加密结果的 hex（不是 Base64 的 hex）
    return encrypted.hex()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python crypto_helper.py <密码>")
        sys.exit(1)

    password = sys.argv[1]
    encrypted = encrypt_password(password)
    print(f"加密结果: {encrypted}")
