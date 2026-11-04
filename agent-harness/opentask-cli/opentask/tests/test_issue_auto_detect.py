"""Test automatic detection of issue ID format for issue show command."""
import pytest
import re


def detect_by_code(issue_id: str) -> bool:
    """Detect if issue_id is a code (vs UUID ID).

    Mirrors opentask.core.issue + helpers.validate_issue_code (E12-S1 KEY-N).
    """
    issue_code_pattern = re.compile(
        r"^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$",
        re.IGNORECASE,
    )
    return issue_code_pattern.match(issue_id) is not None


class TestIssueAutoDetect:
    """Test automatic detection of issue ID format."""

    def test_issue_code_detection(self):
        """Legacy ISSUE{year}-N and KEY-N are treated as codes."""
        test_cases_code = [
            "ISSUE2026-32",
            "issue2026-32",
            "Issue2026-32",
            "ISSUE2025-1",
            "ISSUE2024-999",
            "ISSUE2026-1",
            "ISSUE2025-123",
            "OT-1",
            "ABC-42",
            "way-99",
            "ISSUE-123",  # KEY-N with prefix ISSUE
        ]

        for issue_id in test_cases_code:
            by_code = detect_by_code(issue_id)
            assert by_code is True, f"Failed for {issue_id}: should be detected as code"

    def test_issue_id_detection(self):
        """UUID IDs are not treated as codes."""
        test_cases_id = [
            "5ee3420e-2d69-4509-9ae7-524e8c40d6d1",
            "12345678-1234-1234-1234-123456789abc",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        ]

        for issue_id in test_cases_id:
            by_code = detect_by_code(issue_id)
            assert by_code is False, f"Failed for {issue_id}: should be detected as ID"

    def test_edge_cases(self):
        """Strings that are neither KEY-N nor legacy ISSUE{year}-N."""
        not_code = [
            "MYISSUE-123",  # prefix longer than 6
            "TEST-ISSUE-123",  # extra hyphen segment
            "issue123",  # no hyphen
            "PREFIX-ISSUE-123",
            "ISSUE123",  # no hyphen after ISSUE+digits form
            "",
            "ISSUE",
            "ABC",  # no number
        ]

        for issue_id in not_code:
            by_code = detect_by_code(issue_id)
            assert by_code is False, f"Failed for '{issue_id}': should NOT be detected as code"

    def test_real_world_examples(self):
        """Real-world issue identifier examples."""
        real_codes = [
            "ISSUE2026-32",
            "ISSUE2026-1",
            "ISSUE2025-123",
            "OT-1",
            "WAY-42",
        ]

        for code in real_codes:
            by_code = detect_by_code(code)
            assert by_code is True, f"Real code {code} should be detected as code"

        real_uuids = [
            "5ee3420e-2d69-4509-9ae7-524e8c40d6d1",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        ]

        for uuid in real_uuids:
            by_code = detect_by_code(uuid)
            assert by_code is False, f"Real UUID {uuid} should be detected as ID"
