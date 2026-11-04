"""E12-S3: CodingWorker.md is Issue-first; PGE not mandatory."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CW = ROOT / "CodingWorker.md"


def test_codingworker_exists():
    assert CW.is_file(), f"missing {CW}"


def test_codingworker_not_mandatory_pge():
    text = CW.read_text(encoding="utf-8")
    assert "严格遵守以下 **PGE 流程**" not in text
    assert "必须严格遵循流程中的所有约束" not in text


def test_codingworker_issue_first():
    text = CW.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "issue" in lowered
    assert ("opentask issue show" in lowered) or ("key-n" in lowered) or ("issue_code" in lowered)
