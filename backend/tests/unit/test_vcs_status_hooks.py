"""E11-S3: pure helpers for PR→Issue status hooks."""
from opentask.services.vcs.status_hooks import should_apply_merged_hook, should_apply_open_hook


def test_open_hook_only_from_open():
    assert should_apply_open_hook("open") is True
    assert should_apply_open_hook("in_progress") is False
    assert should_apply_open_hook("feedback") is False


def test_merged_hook_skips_closed_rejected():
    assert should_apply_merged_hook("open") is True
    assert should_apply_merged_hook("in_progress") is True
    assert should_apply_merged_hook("closed") is False
    assert should_apply_merged_hook("rejected") is False
