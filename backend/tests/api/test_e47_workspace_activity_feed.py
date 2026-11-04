"""E47：WS Activity Feed v1 — JSON cursor API + no-emit."""
from __future__ import annotations

import base64
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Unit: cursor + clamp
# ---------------------------------------------------------------------------


def test_activity_cursor_roundtrip():
    from opentask.services.issue_timeline_export import (
        decode_activity_cursor,
        encode_activity_cursor,
    )

    ts = datetime(2026, 11, 5, 1, 2, 3, 456789)
    rid = "abc-def-012"
    cur = encode_activity_cursor(ts, rid)
    assert isinstance(cur, str) and len(cur) > 8
    got_ts, got_id = decode_activity_cursor(cur)
    assert got_ts == ts
    assert got_id == rid


def test_activity_cursor_invalid_raises():
    from opentask.services.issue_timeline_export import decode_activity_cursor

    with pytest.raises(ValueError):
        decode_activity_cursor("not-a-cursor!!!")
    with pytest.raises(ValueError):
        decode_activity_cursor(base64.urlsafe_b64encode(b"only-one-part").decode())


def test_clamp_activity_limit():
    from opentask.services.issue_timeline_export import clamp_activity_limit

    assert clamp_activity_limit(50) == 50
    assert clamp_activity_limit(500) == 200
    assert clamp_activity_limit(200) == 200
    assert clamp_activity_limit(0) == 1
    assert clamp_activity_limit(-5) == 1
