"""Verify the local test-data corpus against maintainer/testdata-manifest.toml.

Checks that every file listed in the manifest exists with the expected
SHA-256 checksum and size. Reports missing, extra, and corrupted files.
Rejects empty or malformed manifests.

Requires Python >= 3.11 (tomllib) or Python 3.10 with tomli installed.
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

EXCLUDE_NAMES = {"README", "conversion_scripts"}
EXCLUDE_SUFFIXES = {".com"}
EXCLUDE_PREFIXES = {"make_"}


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        print(f"Error: manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(MANIFEST_PATH, "rb") as f:
        return tomllib.load(f)


def should_exclude(name: str) -> bool:
    if name in EXCLUDE_NAMES:
        return True
    if any(name.startswith(p) for p in EXCLUDE_PREFIXES):
        return True
    if any(name.endswith(s) for s in EXCLUDE_SUFFIXES):
        return True
    return False


def verify_group(group_name: str, group_data: dict, data_dir: Path) -> tuple[list[str], int]:
    """Verify one group. Returns (errors, verified_count)."""
    errors = []
    files = group_data.get("files", {})
    if not files:
        errors.append(f"EMPTY GROUP: {group_name} has no files listed")
        return errors, 0

    verified = 0
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
        else:
            verified += 1
    return errors, verified


def detect_extra_files(group_name: str, group_data: dict, data_dir: Path) -> list[str]:
    """Detect files in the group directory that are not in the manifest."""
    files = group_data.get("files", {})
    if not files:
        return []
    group_dir = data_dir / group_name
    if not group_dir.is_dir():
        return []
    expected_paths = set(files.keys())
    extras = []
    for path in sorted(group_dir.rglob("*")):
        if not path.is_file():
            continue
        if should_exclude(path.name):
            continue
        rel = path.relative_to(data_dir).as_posix()
        if rel not in expected_paths:
            extras.append(rel)
    return extras


def main():
    manifest = load_manifest()
    groups = manifest.get("groups", {})
    missing_groups = manifest.get("missing", {})

    # Validate manifest structure
    if not groups:
        print("FAILED: manifest contains no groups", file=sys.stderr)
        return 1

    manifest_info = manifest.get("manifest", {})
    declared_total_files = manifest_info.get("total_files", 0)
    declared_total_groups = manifest_info.get("total_groups", 0)

    if declared_total_groups != len(groups):
        print(
            f"WARNING: manifest declares {declared_total_groups} groups "
            f"but contains {len(groups)}"
        )
    if declared_total_files != sum(g.get("file_count", 0) for g in groups.values()):
        print(
            f"WARNING: manifest declares {declared_total_files} files "
            f"but groups sum to {sum(g.get('file_count', 0) for g in groups.values())}"
        )

    print(f"Manifest: {MANIFEST_PATH}")
    print(f"  Available groups: {len(groups)}")
    print(f"  Missing groups:   {len(missing_groups)}")
    print()

    total_declared = 0
    total_verified = 0
    total_errors = 0

    for gname in sorted(groups):
        gdata = groups[gname]
        declared_count = gdata.get("file_count", 0)
        total_declared += declared_count
        errors, verified = verify_group(gname, gdata, DATA_DIR)
        total_verified += verified
        extras = detect_extra_files(gname, gdata, DATA_DIR)
        for e in extras:
            errors.append(f"EXTRA: {e}")

        # Confront declared file_count with actual entries
        actual_entries = len(gdata.get("files", {}))
        if declared_count != actual_entries:
            errors.append(
                f"COUNT MISMATCH: {gname} declares file_count={declared_count} "
                f"but has {actual_entries} file entries"
            )

        if errors:
            print(f"[{gname}] {declared_count} declared, {verified} verified — {len(errors)} errors")
            for e in errors:
                print(f"  {e}")
            total_errors += len(errors)
        else:
            print(f"[{gname}] {declared_count} files — OK ({verified} verified)")

    print()
    if total_errors:
        print(f"FAILED: {total_errors} errors across {total_declared} declared files")
        return 1
    if total_verified == 0:
        print("FAILED: no files were verified", file=sys.stderr)
        return 1
    print(f"PASSED: {total_verified}/{total_declared} files verified, 0 errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
