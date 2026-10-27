"""Tests for deriving package versions from release tags."""

from pathlib import Path
import runpy

import pytest


version_from_tag = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / ".github/scripts/release_version.py")
)["version_from_tag"]


@pytest.mark.parametrize(
    ("tag", "version"), [("v1.1.2", "1.1.2"), ("v1.0.0rc1", "1.0.0rc1")]
)
def test_version_from_tag(tag, version):
    assert version_from_tag(tag) == version


@pytest.mark.parametrize("tag", ["1.1.2", "release-1.1.2", "v1.1", "v1.1.2.dev1"])
def test_version_from_tag_rejects_non_release_tags(tag):
    with pytest.raises(ValueError, match="release tag"):
        version_from_tag(tag)
