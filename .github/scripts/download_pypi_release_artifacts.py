"""Download and verify the PyPI artifacts for one nmrglue-ng release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


def download_release_artifacts(
    version: str, output: Path, opener=urlopen
) -> list[Path]:
    """Download the sdist and wheel recorded by PyPI, checking their hashes."""
    with opener(f"https://pypi.org/pypi/nmrglue-ng/{version}/json") as response:
        release = json.load(response)

    expected = (
        f"nmrglue_ng-{version}.tar.gz",
        f"nmrglue_ng-{version}-py3-none-any.whl",
    )
    files = release["urls"]
    if len(files) != len(expected) or {file["filename"] for file in files} != set(expected):
        raise RuntimeError("PyPI release does not contain exactly the expected artifacts")
    files = {file["filename"]: file for file in files}

    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename in expected:
        file = files[filename]
        with opener(file["url"]) as response:
            payload = response.read()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != file["digests"]["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch for {filename}")
        path = output / filename
        path.write_bytes(payload)
        paths.append(path)

    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    download_release_artifacts(args.version, args.output)


if __name__ == "__main__":
    main()
