"""
加密工具
SSO 密码加密实现（与前端 encrypt.ts 保持一致）

加密流程：
1. 对明文密码进行 MD5 加密
2. 使用 AES-ECB 模式加密（密钥为 MD5(CIPHER_KEY)）
3. 将加密结果（Base64）转换为 Hex 格式
"""
import hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import binascii

from opentask.config import config


def md5_hash(text: str) -> str:
    """计算 MD5 哈希值"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def get_cipher_key() -> str:
    """获取加密密钥：MD5(CIPHER_KEY)"""
    # 从配置中读取 CIPHER_KEY，如果没有则使用默认值
    cipher_key = getattr(config, 'cipher_key', 'EY8WePvjM5GGwQzn')
    return md5_hash(cipher_key)


def encrypt_by_aes_ecb(plaintext: str, key: str) -> str:
    """
    使用 AES-ECB 模式加密

    Args:
        plaintext: 明文
        key: 32 字符的 MD5 hex 字符串

    Returns:
        Base64 编码的密文

    注意：密钥取 MD5 hex 字符串的 **UTF-8 字节**（32 字节 → AES-256），
    与前端 encrypt.ts 的 CryptoJS UTF8.parse(defaultKey) 逐字节一致。
    历史实现误用 bytes.fromhex(key) 折成 16 字节（AES-128），
    产出与前端/SSO 服务端不一致的密文（已知向量见 tests/unit/test_encrypt.py）。
    """
    # 密钥 = MD5 hex 字符串的 UTF-8 字节（32 字节，AES-256），与前端一致
    key_bytes = key.encode('utf-8')

    # 创建 AES-ECB 加密器
    cipher = AES.new(key_bytes, AES.MODE_ECB)

    # 对明文进行 PKCS7 填充并加密
    padded_data = pad(plaintext.encode('utf-8'), AES.block_size)
    ciphertext = cipher.encrypt(padded_data)

    # 返回 Base64 编码的密文
    return base64.b64encode(ciphertext).decode('utf-8')


def base64_to_hex(base64_string: str) -> str:
    """
    将 Base64 字符串转换为 Hex 字符串

    Args:
        base64_string: Base64 编码的字符串

    Returns:
        Hex 编码的字符串
    """
    # 解码 Base64
    binary_data = base64.b64decode(base64_string)
    # 转换为 Hex
    return binascii.hexlify(binary_data).decode('utf-8')


def encrypt_password(password: str) -> str:
    """
    密码加密（SSO 登录专用）

    完全按照前端 encrypt.ts 的实现：
    1. MD5(密码) → AES-ECB加密 → Hex编码

    Args:
        password: 明文密码

    Returns:
        加密后的密码（Hex 格式）

    Example:
        >>> encrypt_password("123456")
        'e10adc3949ba59abbe56e057f20f883e' # (示例输出，实际会不同)
    """
    # 1. 先对原始密码进行 MD5 加密
    md5_password = md5_hash(password)

    # 2. 获取加密密钥
    cipher_key = get_cipher_key()

    # 3. 对 MD5 结果进行 AES-ECB 加密
    encrypted_base64 = encrypt_by_aes_ecb(md5_password, cipher_key)

    # 4. 将 Base64 结果转换为 Hex 格式
    encrypted_hex = base64_to_hex(encrypted_base64)

    return encrypted_hex
