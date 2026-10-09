"""Verify the local test-data corpus against maintainer/testdata-manifest.toml.

Two result axes are reported separately:

* INTEGRITY -- every inventoried file exists with the expected SHA-256 and
  size, no extra file sits under data/, and the declared counters form a
  consistent chain.
* AVAILABILITY -- every required component is either fully inventoried
  (status ``present``) or explicitly declared absent (status ``absent``),
  the declared status matches the on-disk reality, and the declared group
  availability is derived from those components.

``INTEGRITY: PASSED`` never claims that the critical corpus is complete.
Results and exit codes:

* ``0`` -- integrity OK and every release-critical component is present.
  Deferred and extended-only absences are listed but do not change the exit
  code (deferred components are held out of the first-release critical
  contract by the maintainer decisions of 2026-10-08).
* ``1`` -- error: structural inconsistency, integrity failure, or a
  component whose declaration does not match the corpus.
* ``2`` -- integrity OK and every declaration consistent, but at least one
  release-critical component is explicitly declared absent (files conform,
  critical corpus incomplete).

Requires Python >= 3.11 (tomllib) or Python 3.10 with tomli installed.
"""

import hashlib
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from generate_testdata_manifest import resolve_matches


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "maintainer" / "testdata-manifest.toml"

EXCLUDE_NAMES = {"README", "conversion_scripts"}
EXCLUDE_SUFFIXES = {".com"}
EXCLUDE_PREFIXES = {"make_"}

VALID_STATUSES = {"present", "absent"}
VALID_SCOPES = {"critical", "deferred", "extended"}


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


def iter_components(manifest: dict):
    for section, entries in (
        ("groups", manifest.get("groups", {})),
        ("missing", manifest.get("missing", {})),
    ):
        for entry, data in entries.items():
            for comp_id, comp in data.get("components", {}).items():
                yield section, entry, comp_id, comp


def derive_availability(statuses: list) -> str:
    if statuses and all(s == "present" for s in statuses):
        return "complete"
    if any(s == "present" for s in statuses):
        return "partial"
    return "not_available"


def verify_structure(manifest: dict) -> list:
    """Data-independent consistency checks. Returns a list of errors."""
    errors = []
    groups = manifest.get("groups", {})
    missing = manifest.get("missing", {})
    info = manifest.get("manifest", {})

    if not groups:
        errors.append("STRUCTURAL: manifest contains no groups")
        return errors
    if info.get("version") != "4":
        errors.append(
            f"STRUCTURAL: unsupported manifest version {info.get('version')!r} (expected '4')"
        )

    critical_tests = info.get("critical_tests", [])
    if not isinstance(critical_tests, list) or not critical_tests:
        errors.append("STRUCTURAL: manifest.critical_tests must be a non-empty list")
        critical_tests = []
    deferred_tests = info.get("deferred_tests", [])
    if not isinstance(deferred_tests, list):
        errors.append("STRUCTURAL: manifest.deferred_tests must be a list")
        deferred_tests = []

    total_files = sum(g.get("file_count", 0) for g in groups.values())
    total_size = sum(g.get("total_size", 0) for g in groups.values())
    components = list(iter_components(manifest))
    total_components = len(components)
    absent_components = sum(1 for *_, c in components if c.get("status") == "absent")

    def is_scope(comp, scope):
        required_by = set(comp.get("required_by", []))
        if scope == "critical":
            return bool(required_by & set(critical_tests))
        if scope == "deferred":
            return not (required_by & set(critical_tests)) and bool(
                required_by & set(deferred_tests)
            )
        return not (required_by & set(critical_tests)) and not (
            required_by & set(deferred_tests)
        )

    critical_components = sum(1 for *_, c in components if is_scope(c, "critical"))
    absent_critical_components = sum(
        1 for *_, c in components
        if c.get("status") == "absent" and is_scope(c, "critical")
    )
    deferred_components = sum(1 for *_, c in components if is_scope(c, "deferred"))
    absent_deferred_components = sum(
        1 for *_, c in components
        if c.get("status") == "absent" and is_scope(c, "deferred")
    )

    for key, actual in (
        ("total_groups", len(groups)),
        ("total_files", total_files),
        ("total_size", total_size),
        ("missing_groups", len(missing)),
        ("total_components", total_components),
        ("absent_components", absent_components),
        ("critical_components", critical_components),
        ("absent_critical_components", absent_critical_components),
        ("deferred_components", deferred_components),
        ("absent_deferred_components", absent_deferred_components),
    ):
        declared = info.get(key)
        if declared != actual:
            errors.append(
                f"STRUCTURAL: manifest declares {key}={declared} but computed value is {actual}"
            )

    seen_paths = {}
    for section, entry, comp_id, comp in components:
        label = f"{section}.{entry}.components.{comp_id}"
        status = comp.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"STRUCTURAL: {label} has invalid status {status!r}")
        paths = comp.get("paths")
        if not paths or not isinstance(paths, list):
            errors.append(f"STRUCTURAL: {label} must declare a non-empty paths list")
            paths = []
        required_by = comp.get("required_by")
        if not isinstance(required_by, list):
            errors.append(f"STRUCTURAL: {label} must declare a required_by list")
            required_by = []
        expected_scope = next(
            s for s in ("critical", "deferred", "extended")
            if is_scope(comp, s)
        )
        if comp.get("scope") not in VALID_SCOPES:
            errors.append(
                f"STRUCTURAL: {label} has invalid scope {comp.get('scope')!r}"
            )
        elif comp.get("scope") != expected_scope:
            errors.append(
                f"STRUCTURAL: {label} declares scope={comp.get('scope')!r} "
                f"but required_by implies {expected_scope!r}"
            )
        for p in paths:
            if p in seen_paths:
                errors.append(
                    f"STRUCTURAL: path {p} declared by both {seen_paths[p]} and {label}"
                )
            else:
                seen_paths[p] = label

    for entry, gdata in groups.items():
        comps = gdata.get("components", {})
        if not comps:
            errors.append(
                f"STRUCTURAL: groups.{entry} declares no required component"
            )
        for fname in gdata.get("files", {}):
            if not fname.startswith(f"{entry}/"):
                errors.append(
                    f"STRUCTURAL: groups.{entry} inventories {fname} outside its directory"
                )
        file_sizes = sum(f.get("size", 0) for f in gdata.get("files", {}).values())
        if file_sizes != gdata.get("total_size", 0):
            errors.append(
                f"STRUCTURAL: groups.{entry} declares total_size={gdata.get('total_size')} "
                f"but files sum to {file_sizes}"
            )
        if gdata.get("file_count") != len(gdata.get("files", {})):
            errors.append(
                f"STRUCTURAL: groups.{entry} declares file_count={gdata.get('file_count')} "
                f"but has {len(gdata.get('files', {}))} file entries"
            )

    for section, entries in (("groups", groups), ("missing", missing)):
        for entry, gdata in entries.items():
            comps = gdata.get("components", {})
            statuses = [c.get("status") for c in comps.values()]
            declared_absent = sorted(
                cid for cid, c in comps.items() if c.get("status") == "absent"
            )
            if gdata.get("component_count") != len(comps):
                errors.append(
                    f"STRUCTURAL: {section}.{entry} declares component_count="
                    f"{gdata.get('component_count')} but has {len(comps)} components"
                )
            if gdata.get("absent_component_count") != len(declared_absent):
                errors.append(
                    f"STRUCTURAL: {section}.{entry} declares absent_component_count="
                    f"{gdata.get('absent_component_count')} but has {len(declared_absent)} absent"
                )
            if section == "groups":
                expected = derive_availability(statuses)
                if gdata.get("availability") != expected:
                    errors.append(
                        f"STRUCTURAL: groups.{entry} declares availability="
                        f"{gdata.get('availability')!r} but components imply {expected!r}"
                    )
                summary = ", ".join(declared_absent)
                if gdata.get("missing_components") != summary:
                    errors.append(
                        f"STRUCTURAL: groups.{entry} declares missing_components="
                        f"{gdata.get('missing_components')!r} but components imply {summary!r}"
                    )
    return errors


def verify_group(group_name: str, group_data: dict, data_dir: Path) -> tuple:
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


def scan_data_dir(data_dir: Path) -> set:
    """Return all non-excluded file paths under data/ as relative POSIX paths."""
    found = set()
    if not data_dir.is_dir():
        return found
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue
        if should_exclude(path.name):
            continue
        found.add(path.relative_to(data_dir).as_posix())
    return found


def detect_extra_files(manifest_groups: dict, data_dir: Path) -> list:
    """Return files under data/ that are not listed in any manifest group."""
    expected = set()
    for gdata in manifest_groups.values():
        expected.update(gdata.get("files", {}).keys())
    actual = scan_data_dir(data_dir)
    return sorted(actual - expected)


def verify_availability(manifest: dict, data_dir: Path) -> tuple:
    """Check component statuses against the corpus.

    Returns ``(errors, stats, absent)`` where stats counts components per
    scope/status and ``absent`` lists every absent component labeled by its
    scope.
    """
    errors = []
    critical_tests = set(manifest.get("manifest", {}).get("critical_tests", []))
    deferred_tests = set(manifest.get("manifest", {}).get("deferred_tests", []))
    inventoried = {
        rel for gdata in manifest.get("groups", {}).values()
        for rel in gdata.get("files", {})
    }
    on_disk = scan_data_dir(data_dir) if data_dir.is_dir() else None

    stats = {
        "total": 0,
        "present": 0,
        "absent": 0,
        "critical": 0,
        "critical_present": 0,
        "critical_absent": 0,
        "deferred": 0,
        "deferred_absent": 0,
    }
    absent = []
    for section, entry, comp_id, comp in iter_components(manifest):
        label = f"{section}.{entry}.components.{comp_id}"
        status = comp.get("status")
        required_by = set(comp.get("required_by", []))
        if required_by & critical_tests:
            scope = "critical"
        elif required_by & deferred_tests:
            scope = "deferred"
        else:
            scope = "extended"
        stats["total"] += 1
        if scope == "critical":
            stats["critical"] += 1
        elif scope == "deferred":
            stats["deferred"] += 1

        if on_disk is not None:
            matches = set()
            for p in comp.get("paths", []):
                matches |= resolve_matches(on_disk, p)
            if status == "absent" and matches:
                errors.append(
                    f"DECLARED ABSENT BUT PRESENT: {label} matches {sorted(matches)}"
                )
            if status == "present":
                if not matches:
                    errors.append(f"DECLARED PRESENT BUT ABSENT: {label} matches nothing")
                for rel in sorted(matches - inventoried):
                    errors.append(
                        f"NOT INVENTORIED: {label} matches {rel} which is not checksummed"
                    )

        if status == "present":
            stats["present"] += 1
            if scope == "critical":
                stats["critical_present"] += 1
        else:
            stats["absent"] += 1
            absent.append((scope, label))
            if scope == "critical":
                stats["critical_absent"] += 1
            elif scope == "deferred":
                stats["deferred_absent"] += 1
    return errors, stats, absent


def main():
    manifest = load_manifest()
    groups = manifest.get("groups", {})
    missing_groups = manifest.get("missing", {})

    structural_errors = verify_structure(manifest)
    if structural_errors:
        for e in structural_errors:
            print(e, file=sys.stderr)
        print("FAILED: manifest structural inconsistencies", file=sys.stderr)
        return 1

    print(f"Manifest: {MANIFEST_PATH}")
    print(f"  Available groups: {len(groups)}")
    print(f"  Missing groups:   {len(missing_groups)}")
    print()

    total_declared = 0
    total_verified = 0
    total_errors = 0

    print("INTEGRITY")
    for gname in sorted(groups):
        gdata = groups[gname]
        declared_count = gdata.get("file_count", 0)
        total_declared += declared_count
        errors, verified = verify_group(gname, gdata, DATA_DIR)
        total_verified += verified

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

    extras = detect_extra_files(groups, DATA_DIR)
    for e in extras:
        print(f"EXTRA (not in manifest): {e}")
        total_errors += 1

    if total_errors:
        print(f"INTEGRITY: FAILED — {total_errors} errors across {total_declared} declared files")
    elif total_verified == 0:
        print("INTEGRITY: FAILED — no files were verified")
        total_errors += 1
    else:
        print(f"INTEGRITY: PASSED — {total_verified}/{total_declared} inventoried files verified, 0 errors")
    print()

    print("AVAILABILITY")
    avail_errors, stats, absent = verify_availability(manifest, DATA_DIR)
    for e in avail_errors:
        print(f"  {e}")
        total_errors += 1
    print(
        f"  required components: {stats['total']} "
        f"({stats['critical']} release-critical, {stats['deferred']} deferred), "
        f"absent: {stats['absent']} "
        f"({stats['critical_absent']} release-critical, "
        f"{stats['deferred_absent']} deferred)"
    )
    for scope, label in absent:
        print(f"  ABSENT ({scope}): {label}")
    if stats["critical_absent"]:
        print(
            f"AVAILABILITY: INCOMPLETE — {stats['critical_absent']} of "
            f"{stats['critical']} release-critical components declared absent "
            f"({stats['deferred_absent']} deferred, "
            f"{stats['absent'] - stats['critical_absent'] - stats['deferred_absent']}"
            f" extended-only)"
        )
    else:
        print(
            f"AVAILABILITY: COMPLETE — all {stats['critical']} release-critical "
            f"components inventoried ({stats['deferred_absent']} deferred, "
            f"{stats['absent'] - stats['critical_absent'] - stats['deferred_absent']}"
            f" extended-only absences)"
        )
    print()

    if total_errors:
        print(f"FAILED: {total_errors} errors; see INTEGRITY/AVAILABILITY above")
        return 1
    if stats["critical_absent"]:
        print(
            "RESULT: INTEGRITY OK, RELEASE-CRITICAL CORPUS INCOMPLETE "
            f"({stats['critical_absent']} declared absences)"
        )
        return 2
    print("RESULT: INTEGRITY OK, RELEASE-CRITICAL CORPUS COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
