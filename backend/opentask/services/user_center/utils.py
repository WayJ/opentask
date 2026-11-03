"""用户中心公共工具函数

- unique_username：username lower 归一化唯一化算法，
  从 migrate_service 抽出供 SSO 迁移与钉钉同步复用。
- generate_temp_password：12 位随机临时密码，供 SSO 迁移与
  管理端重置密码复用（明文只出现在响应体，绝不落日志/落盘）。

归一化手法与 Phase 1 迁移（alembic 2026_10_23_0001 _backfill_user_data）
保持一致：MySQL 默认 ci collation 的唯一索引不区分大小写，
判重必须统一 lower()。
"""
import secrets
import string

# username 列宽 50，为重名序号预留余量
USERNAME_MAX_BASE = 45

# 临时密码字符集：大小写字母 + 数字
_ALPHABET = string.ascii_letters + string.digits
# 临时密码长度
_TEMP_PASSWORD_LEN = 12


def unique_username(existing_names: set[str], candidate: str) -> str:
    """在 existing_names 中找不冲突的 username，冲突时追加 _2/_3... 序号。

    Args:
        existing_names: 已占用名字集合（必须已 lower 归一化）。
        candidate: 期望的用户名（原样使用，超长截断到 45）。

    Returns:
        唯一的用户名（不修改 existing_names，调用方自行 add 返回值）。
    """
    base = (candidate or "").strip()[:USERNAME_MAX_BASE]
    if not base:
        base = "user"
    result = base
    n = 1
    while result.lower() in existing_names:
        n += 1
        result = f"{base}_{n}"
    return result


def generate_temp_password(length: int = _TEMP_PASSWORD_LEN) -> str:
    """生成随机临时密码（默认 12 位，大小写字母 + 数字，secrets 加密安全随机）

    明文只允许出现在返回给管理员的响应体（CSV / 重置密码响应），
    绝不 print / logger 落盘。
    """
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
