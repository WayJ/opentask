"""Trusted public MCP resource identifiers and authentication challenge."""

from urllib.parse import urlsplit

from fastapi import HTTPException
from opentask.config import config


def public_origin() -> str:
    raw = config.frontend_base_url
    try:
        parsed = urlsplit(raw)
        valid = (not any(ord(c) <= 32 or ord(c) >= 127 or c in '\"\\' for c in raw)
                 and parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username
                 and not parsed.password and not parsed.query and not parsed.fragment
                 and parsed.path in ("", "/") and parsed.port != 0)
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(status_code=503, detail="MCP 外部地址未配置")
    return raw.rstrip("/")


def mcp_challenge() -> str:
    return f'Bearer resource_metadata="{public_origin()}/.well-known/oauth-protected-resource/mcp"'
