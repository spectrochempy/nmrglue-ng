"""Identify GitHub Release assets that are not part of a release build."""

from __future__ import annotations

import argparse
from pathlib import Path


def surplus_assets(existing: list[str], expected: list[str]) -> list[str]:
    """Return existing asset names absent from the expected build output."""
    return sorted(set(existing) - set(expected))


def read_asset_names(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    args = parser.parse_args()

    print(*surplus_assets(read_asset_names(args.existing), read_asset_names(args.expected)), sep="\n")


if __name__ == "__main__":
    main()
