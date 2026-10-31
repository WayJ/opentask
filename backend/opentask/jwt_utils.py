from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from starlette.status import HTTP_401_UNAUTHORIZED

from opentask.config import config


# JWT配置：密钥必须显式配置，缺失即启动失败（config.auth_secret_key 会 raise）
SECRET_KEY = config.auth_secret_key
ALGORITHM = "HS256"
# access token 有效期（分钟）：默认 120，可通过 AUTH_ACCESS_EXPIRE_MINUTES / yaml auth.access_expire_minutes 配置
ACCESS_TOKEN_EXPIRE_MINUTES = config.access_expire_minutes


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """验证JWT令牌并返回payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def get_username_from_token(token: str) -> Optional[str]:
    """从JWT令牌中获取用户名"""
    try:
        payload = verify_token(token)
        username: str = payload.get("sub")
        return username
    except JWTError:
        return None