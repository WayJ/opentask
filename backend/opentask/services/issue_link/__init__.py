"""E76: Issue external links (issue_links) — not attachments / VCS / relations."""
from opentask.services.issue_link.service import (
    MAX_LINKS_PER_ISSUE,
    MAX_TITLE_LEN,
    MAX_URL_LEN,
    IssueLinkService,
    require_writer,
    serialize_issue_link,
    validate_http_url,
)

__all__ = [
    "MAX_LINKS_PER_ISSUE",
    "MAX_TITLE_LEN",
    "MAX_URL_LEN",
    "IssueLinkService",
    "require_writer",
    "serialize_issue_link",
    "validate_http_url",
]
