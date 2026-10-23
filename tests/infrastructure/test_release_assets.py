"""Tests for keeping GitHub Release assets identical to the PyPI build."""

from pathlib import Path
import runpy


surplus_assets = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / ".github/scripts/release_assets.py")
)["surplus_assets"]


def test_surplus_assets_identifies_only_unexpected_existing_assets():
    assert surplus_assets(
        ["nmrglue_ng-1.2.0.tar.gz", "checksums.txt", "notes.txt"],
        ["nmrglue_ng-1.2.0.tar.gz", "nmrglue_ng-1.2.0-py3-none-any.whl"],
    ) == ["checksums.txt", "notes.txt"]
