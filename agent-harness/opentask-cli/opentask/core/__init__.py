"""Core command modules for OpenTask CLI."""

from .project import project_cli
from .issue import issue_cli
from .requirement import requirement_cli

__all__ = [
    "project_cli",
    "issue_cli",
    "requirement_cli",
]
