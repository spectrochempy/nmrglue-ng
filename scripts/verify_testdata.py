"""Verify the local test-data corpus against data/manifest.toml.

Checks that every file listed in the manifest exists with the expected
SHA-256 checksum and size. Reports missing, extra, and corrupted files.
"""

import hashlib
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "maintainer" / "testdata-manifest.toml"


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        print(f"Error: manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(MANIFEST_PATH, "rb") as f:
        return tomllib.load(f)


def verify_group(group_name: str, group_data: dict, data_dir: Path) -> list[str]:
    errors = []
    files = group_data.get("files", {})
    for rel_path, expected in files.items():
        path = data_dir / rel_path
        if not path.is_file():
            errors.append(f"MISSING: {rel_path}")
            continue
        data = path.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest()
        actual_size = len(data)
        if actual_sha256 != expected["sha256"]:
            errors.append(
                f"CORRUPT: {rel_path} "
                f"(expected sha256 {expected['sha256'][:16]}..., "
                f"got {actual_sha256[:16]}...)"
            )
        elif actual_size != expected["size"]:
            errors.append(
                f"SIZE MISMATCH: {rel_path} "
                f"(expected {expected['size']}, got {actual_size})"
            )
    return errors


def main():
    manifest = load_manifest()
    groups = manifest.get("groups", {})
    missing_groups = manifest.get("missing", {})

    print(f"Manifest: {MANIFEST_PATH}")
    print(f"  Available groups: {len(groups)}")
    print(f"  Missing groups:   {len(missing_groups)}")
    print()

    total_files = 0
    total_errors = 0

    for gname in sorted(groups):
        gdata = groups[gname]
        errors = verify_group(gname, gdata, DATA_DIR)
        file_count = gdata.get("file_count", 0)
        total_files += file_count
        if errors:
            print(f"[{gname}] {file_count} files — {len(errors)} errors")
            for e in errors:
                print(f"  {e}")
            total_errors += len(errors)
        else:
            print(f"[{gname}] {file_count} files — OK")

    print()
    if total_errors:
        print(f"FAILED: {total_errors} errors across {total_files} files")
        return 1
    print(f"PASSED: all {total_files} files verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
