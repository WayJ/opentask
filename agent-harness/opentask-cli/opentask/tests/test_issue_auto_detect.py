"""Test automatic detection of issue ID format for issue show command."""
import pytest
import re


def detect_by_code(issue_id: str) -> bool:
    """Detect if issue_id is a code (vs UUID ID).

    This mirrors the logic in opentask.core.issue.show_issue
    """
    issue_code_pattern = re.compile(r'^ISSUE\d+-\d+', re.IGNORECASE)
    return issue_code_pattern.match(issue_id) is not None


class TestIssueAutoDetect:
    """Test automatic detection of issue ID format."""

    def test_issue_code_detection(self):
        """Test that issue codes are automatically detected."""
        # Test case 1: ISSUE prefix with pattern (should be treated as code)
        test_cases_code = [
            "ISSUE2026-32",
            "issue2026-32",
            "Issue2026-32",
            "ISSUE2025-1",
            "ISSUE2024-999",
            "ISSUE2026-1",
            "ISSUE2025-123",
        ]

        for issue_id in test_cases_code:
            by_code = detect_by_code(issue_id)
            assert by_code is True, f"Failed for {issue_id}: should be detected as code"

    def test_issue_id_detection(self):
        """Test that UUID IDs are automatically detected."""
        # Test case 2: UUID format (should be treated as ID)
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
        """Test edge cases that should NOT be treated as code."""
        # Edge cases that should NOT be treated as code
        not_code = [
            "MYISSUE-123",      # Doesn't start with ISSUE
            "TEST-ISSUE-123",   # ISSUE is not at the start
            "issue123",         # No hyphen (format doesn't match)
            "PREFIX-ISSUE-123", # ISSUE is not at the start
            "ISSUE-123",        # ISSUE followed by hyphen (no year)
            "ISSUE123",         # ISSUE followed by digits without hyphen
            "",                 # Empty string
            "ISSUE",            # Just ISSUE without numbers
        ]

        for issue_id in not_code:
            by_code = detect_by_code(issue_id)
            assert by_code is False, f"Failed for '{issue_id}': should NOT be detected as code"

    def test_real_world_examples(self):
        """Test real-world issue identifier examples."""
        # Real issue codes from the system
        real_codes = [
            "ISSUE2026-32",
            "ISSUE2026-1",
            "ISSUE2025-123",
        ]

        for code in real_codes:
            by_code = detect_by_code(code)
            assert by_code is True, f"Real code {code} should be detected as code"

        # Real UUIDs
        real_uuids = [
            "5ee3420e-2d69-4509-9ae7-524e8c40d6d1",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        ]

        for uuid in real_uuids:
            by_code = detect_by_code(uuid)
            assert by_code is False, f"Real UUID {uuid} should be detected as ID"
