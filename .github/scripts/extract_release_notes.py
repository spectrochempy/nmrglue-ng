"""Extract one release's Markdown body from CHANGELOG.md."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


def extract_release_notes(changelog: Path, version: str) -> str:
    """Return the non-empty body under the dated heading for *version*."""
    heading = re.compile(rf"^## {re.escape(version)} - \d{{4}}-\d{{2}}-\d{{2}}$")
    lines = changelog.read_text(encoding="utf-8").splitlines(keepends=True)

    for index, line in enumerate(lines):
        if not heading.match(line.rstrip("\n")):
            continue
        end = next(
            (
                following
                for following in range(index + 1, len(lines))
                if lines[following].startswith("## ")
            ),
            len(lines),
        )
        notes = "".join(lines[index + 1 : end]).strip()
        if notes:
            return f"{notes}\n"
        raise RuntimeError(f"release {version!r} has no changelog notes")

    raise RuntimeError(f"CHANGELOG.md has no dated heading for {version!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.write_text(
        extract_release_notes(args.changelog, args.version), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
