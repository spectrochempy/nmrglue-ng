"""Validate a release tag and print its nmrglue-ng version."""

from __future__ import annotations

import argparse
import re


TAG_PATTERN = re.compile(r"^v(?P<version>\d+\.\d+\.\d+(?:rc\d+)?)$")


def version_from_tag(tag: str) -> str:
    """Return the package version encoded by a release tag."""
    match = TAG_PATTERN.fullmatch(tag)
    if match is None:
        raise ValueError(f"release tag must have the form vX.Y.Z, got {tag!r}")
    return match.group("version")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag")
    args = parser.parse_args()
    print(version_from_tag(args.tag))


if __name__ == "__main__":
    main()
