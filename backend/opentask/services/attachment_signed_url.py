"""E66: short-TTL HMAC signed URLs for attachment download/preview (stateless)."""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone

DEFAULT_TTL_SECONDS = 900
MAX_TTL_SECONDS = 3600
ALLOWED_PURPOSES = frozenset({"download", "preview"})


def mint_signed_token(
    *,
    attachment_id: str,
    purpose: str,
    ttl_seconds: int,
    secret: str,
) -> tuple[str, datetime]:
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError("invalid purpose")
    if ttl_seconds < 1 or ttl_seconds > MAX_TTL_SECONDS:
        raise ValueError("ttl out of range")
    if not attachment_id or not secret:
        raise ValueError("missing attachment_id or secret")
    exp = int(time.time()) + int(ttl_seconds)
    msg = f"{attachment_id}.{exp}.{purpose}"
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    token = f"{msg}.{sig}"
    return token, datetime.fromtimestamp(exp, tz=timezone.utc)


def verify_signed_token(token: str, *, secret: str) -> dict:
    if not token or not secret:
        raise ValueError("missing token or secret")
    parts = token.split(".")
    if len(parts) != 4:
        raise ValueError("malformed")
    aid, exp_s, purpose, sig = parts
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError("bad purpose")
    try:
        exp = int(exp_s)
    except ValueError as e:
        raise ValueError("bad exp") from e
    msg = f"{aid}.{exp_s}.{purpose}"
    expected = hmac.new(
        secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("bad sig")
    if int(time.time()) > exp:
        raise ValueError("expired")
    return {"attachment_id": aid, "purpose": purpose, "exp": exp}
