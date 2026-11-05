"""E74: comment parent validation (depth=1)."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from opentask.services.comment_threading import ParentCommentView, validate_comment_parent


def test_no_parent_ok():
    validate_comment_parent(issue_id="i1", parent=None, parent_id=None)


def test_root_parent_ok():
    p = ParentCommentView(id="c1", issue_id="i1", parent_id=None, is_deleted=False)
    validate_comment_parent(issue_id="i1", parent=p, parent_id="c1")


def test_parent_not_found_400():
    with pytest.raises(HTTPException) as ei:
        validate_comment_parent(issue_id="i1", parent=None, parent_id="missing")
    assert ei.value.status_code == 400
    assert ei.value.detail["code"] == "parent_not_found"


def test_cross_issue_400():
    p = ParentCommentView(id="c1", issue_id="other", parent_id=None, is_deleted=False)
    with pytest.raises(HTTPException) as ei:
        validate_comment_parent(issue_id="i1", parent=p, parent_id="c1")
    assert ei.value.status_code == 400
    assert ei.value.detail["code"] == "parent_cross_issue"


def test_deleted_parent_400():
    p = ParentCommentView(id="c1", issue_id="i1", parent_id=None, is_deleted=True)
    with pytest.raises(HTTPException) as ei:
        validate_comment_parent(issue_id="i1", parent=p, parent_id="c1")
    assert ei.value.status_code == 400
    assert ei.value.detail["code"] == "parent_deleted"


def test_reply_to_reply_400():
    p = ParentCommentView(id="c2", issue_id="i1", parent_id="c1", is_deleted=False)
    with pytest.raises(HTTPException) as ei:
        validate_comment_parent(issue_id="i1", parent=p, parent_id="c2")
    assert ei.value.status_code == 400
    assert ei.value.detail["code"] == "parent_not_root"
