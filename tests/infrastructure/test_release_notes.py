"""Tests for extracting GitHub Release notes from the changelog."""

from pathlib import Path
import runpy

import pytest


extract_release_notes = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / ".github/scripts/extract_release_notes.py")
)["extract_release_notes"]


def test_extract_release_notes_returns_only_the_requested_release(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## Unreleased\n\n## 1.2.0 - 2026-10-23\n\n"
        "### Fixed\n\n- Repair release publishing.\n\n"
        "## 1.1.0 - 2026-10-22\n\n- Earlier entry.\n",
        encoding="utf-8",
    )

    assert extract_release_notes(changelog, "1.2.0") == (
        "### Fixed\n\n- Repair release publishing.\n"
    )


def test_extract_release_notes_rejects_missing_or_empty_release(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## 1.2.0 - 2026-10-23\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="has no changelog notes"):
        extract_release_notes(changelog, "1.2.0")

    with pytest.raises(RuntimeError, match="has no dated heading"):
        extract_release_notes(changelog, "1.1.0")
