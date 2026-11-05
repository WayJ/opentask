"""E98: year-code → KEY-N backfill migration safety."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

def _load_backfill():
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "2026_11_05_5800-f9a0b1c2d3e4_e98_backfill_year_issue_codes.py"
    )
    spec = importlib.util.spec_from_file_location("e98_backfill", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_backfill_rewrites_year_code_keeps_legacy(test_engine: AsyncEngine):
    mod = _load_backfill()
    wid = str(uuid.uuid4())
    iid = str(uuid.uuid4())
    key = f"B{uuid.uuid4().hex[:4].upper()}"
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO workspaces (id, name, slug, issue_key, issue_counter, "
                "cycles_enabled, cycle_duration_days, cycle_rollover_policy, "
                "cycle_capacity_lookback, git_status_hooks_enabled, "
                "git_hook_on_pr_open, git_hook_on_pr_merged, created_at, updated_at) "
                "VALUES (:id, 'BF', :slug, :key, 2, false, 14, 'into_next', 3, "
                "false, 'in_progress', 'resolved', NOW(), NOW())"
            ),
            {"id": wid, "slug": f"bf-{uuid.uuid4().hex[:8]}", "key": key},
        )
        await conn.execute(
            text(
                "INSERT INTO issues (id, title, type, priority, status, issue_code, "
                "workspace_id, reporter_id, is_deleted, comment_count, attachment_count, "
                "view_count, created_at, updated_at) "
                "VALUES (:id, 'year', 'bug', 'medium', 'open', 'ISSUE2026-42', "
                ":wid, :rid, false, 0, 0, 0, NOW(), NOW())"
            ),
            {"id": iid, "wid": wid, "rid": str(uuid.uuid4())},
        )

    # run sync backfill via sync_engine bridge
    sync_url = str(test_engine.url).replace("+asyncpg", "").replace("+aiosqlite", "")
    # Use run_sync on the async connection
    async with test_engine.begin() as conn:
        def _run(sync_conn):
            return mod.backfill_year_issue_codes(sync_conn)

        stats = await conn.run_sync(_run)

    assert stats["rewritten"] >= 1
    async with test_engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT issue_code, legacy_issue_code FROM issues WHERE id = :id"
                ),
                {"id": iid},
            )
        ).fetchone()
        counter = (
            await conn.execute(
                text("SELECT issue_counter FROM workspaces WHERE id = :id"),
                {"id": wid},
            )
        ).scalar_one()
    assert row is not None
    assert row[0] == f"{key}-3"  # counter was 2 → next is 3
    assert row[1] == "ISSUE2026-42"
    assert int(counter) >= 3

    # idempotent
    async with test_engine.begin() as conn:
        stats2 = await conn.run_sync(lambda c: mod.backfill_year_issue_codes(c))
    assert stats2["rewritten"] == 0


@pytest.mark.asyncio
async def test_backfill_skips_key_n_with_other_legacy(test_engine: AsyncEngine):
    mod = _load_backfill()
    wid = str(uuid.uuid4())
    iid = str(uuid.uuid4())
    key = f"K{uuid.uuid4().hex[:4].upper()}"
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO workspaces (id, name, slug, issue_key, issue_counter, "
                "cycles_enabled, cycle_duration_days, cycle_rollover_policy, "
                "cycle_capacity_lookback, git_status_hooks_enabled, "
                "git_hook_on_pr_open, git_hook_on_pr_merged, created_at, updated_at) "
                "VALUES (:id, 'KS', :slug, :key, 7, false, 14, 'into_next', 3, "
                "false, 'in_progress', 'resolved', NOW(), NOW())"
            ),
            {"id": wid, "slug": f"ks-{uuid.uuid4().hex[:8]}", "key": key},
        )
        await conn.execute(
            text(
                "INSERT INTO issues (id, title, type, priority, status, issue_code, "
                "legacy_issue_code, workspace_id, reporter_id, is_deleted, comment_count, "
                "attachment_count, view_count, created_at, updated_at) "
                "VALUES (:id, 'keep', 'bug', 'medium', 'open', :code, 'OLD-OTHER', "
                ":wid, :rid, false, 0, 0, 0, NOW(), NOW())"
            ),
            {"id": iid, "code": f"{key}-7", "wid": wid, "rid": str(uuid.uuid4())},
        )
    async with test_engine.begin() as conn:
        stats = await conn.run_sync(lambda c: mod.backfill_year_issue_codes(c))
    assert stats["rewritten"] == 0
    async with test_engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT issue_code, legacy_issue_code FROM issues WHERE id = :id"
                ),
                {"id": iid},
            )
        ).fetchone()
    assert row[0] == f"{key}-7"
    assert row[1] == "OLD-OTHER"


@pytest.mark.asyncio
async def test_backfill_skips_unreliable_orphan_no_delete(test_engine: AsyncEngine):
    mod = _load_backfill()
    iid = str(uuid.uuid4())
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO issues (id, title, type, priority, status, issue_code, "
                "workspace_id, created_by, reporter_id, is_deleted, comment_count, "
                "attachment_count, view_count, created_at, updated_at) "
                "VALUES (:id, 'orphan', 'bug', 'medium', 'open', 'ISSUE2026-99', "
                "NULL, :uid, :uid, false, 0, 0, 0, NOW(), NOW())"
            ),
            {"id": iid, "uid": str(uuid.uuid4())},
        )
    async with test_engine.begin() as conn:
        stats = await conn.run_sync(lambda c: mod.backfill_year_issue_codes(c))
    assert stats["skipped_orphan"] >= 1
    async with test_engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT issue_code, workspace_id FROM issues WHERE id = :id"
                ),
                {"id": iid},
            )
        ).fetchone()
    assert row is not None
    assert row[0] == "ISSUE2026-99"
    assert row[1] is None


@pytest.mark.asyncio
async def test_backfill_empty_db_noop(test_engine: AsyncEngine):
    mod = _load_backfill()
    # Just ensure no crash; stats keys present
    async with test_engine.begin() as conn:
        stats = await conn.run_sync(lambda c: mod.backfill_year_issue_codes(c))
    assert "rewritten" in stats
