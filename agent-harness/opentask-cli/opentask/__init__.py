"""OpenTask CLI - AI Agent interface for OpenTask platform.

This package provides a complete command-line interface for OpenTask,
designed for both human users and AI agents.

Features:
- Interactive REPL mode
- One-shot command mode
- JSON output for agent consumption
- Project, Issue, Requirement, and Conversation management
"""

__version__ = "1.54.0"
__author__ = "OpenTask Team"

from .core.project import project_cli
from .core.issue import issue_cli
from .core.requirement import requirement_cli

__all__ = [
    "project_cli",
    "issue_cli",
    "requirement_cli",
]
