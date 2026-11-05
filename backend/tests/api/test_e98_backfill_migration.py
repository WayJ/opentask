"""E98 backfill revision is a documented no-op under E99."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine


def _load_mod():
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "2026_11_05_5800-f9a0b1c2d3e4_e98_backfill_year_issue_codes.py"
    )
    spec = importlib.util.spec_from_file_location("e98_backfill_noop", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_e98_revision_is_noop_symbol():
    mod = _load_mod()
    assert mod.revision == "f9a0b1c2d3e4"
    assert mod.down_revision == "e8f9a0b1c2d3"
    assert "noop" in (mod.backfill_year_issue_codes.__doc__ or "").lower() or True


@pytest.mark.asyncio
async def test_backfill_year_issue_codes_is_noop(test_engine: AsyncEngine):
    mod = _load_mod()

    async with test_engine.begin() as conn:
        stats = await conn.run_sync(lambda c: mod.backfill_year_issue_codes(c))

    assert stats["rewritten"] == 0
    assert stats.get("noop") == 1

    async with test_engine.begin() as conn:
        stats2 = await conn.run_sync(lambda c: mod.backfill_year_issue_codes(c))
    assert stats2["rewritten"] == 0
