"""Generate a TOML manifest of the local release-critical test-data corpus.

Scans the data/ directory, computes SHA-256 checksums and sizes for every
file, and writes maintainer/testdata-manifest.toml. The manifest documents
each logical group with provenance, license, redistribution status, and
availability.

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

# Files in the nmrglue v0.5 release archive for each group.
# Derived/generated files (not in the archive) are listed separately.
ARCHIVE_FILES = {
    "agilent_1d": ["fid", "procpar"],
    "agilent_2d": ["fid", "procpar"],
    "agilent_2d_tppi": ["fid", "procpar"],
    "agilent_3d": ["fid", "procpar"],
    "agilent_4d": ["fid"],
    "bruker_1d": ["acqu", "acqus", "fid", "pulseprogram"],
    "bruker_2d": ["acqu", "acqu2", "acqu2s", "acqus", "pulseprogram", "ser"],
    "bruker_3d": ["acqu", "acqu2", "acqu2s", "acqus", "pulseprogram", "ser"],
    "simpson_1d": ["rr.in"],
    "simpson_2d": ["2d.in"],
    "tecmag": ["LiCl_ref1.tnt", "LiCl_ref1.txt"],
}

# Derived files generated locally (e.g., NMRPipe references), not in the archive.
DERIVED_FILES = {
    "bruker_3d": {
        "pattern": "fid/test*.fid",
        "count": 116,
        "source": "NMRPipe-generated indexed references from ser",
        "tool": "NMRPipe (external software), per conversion_scripts/bruker2pipe_3d.com",
        "redistribution_status": "UNRESOLVED",
        "evidence": "generated locally; no explicit license; derivation tool is NMRPipe",
    },
}

# Per-group metadata.
GROUP_META = {
    "agilent_1d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "complete",
        "notes": "real 1D acquisition; read/write and conversion tests",
    },
    "agilent_2d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "complete",
        "notes": "real 2D blocks; read/low-memory and conversion tests",
    },
    "agilent_2d_tppi": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "complete",
        "notes": "TPPI ordering; read/low-memory tests",
    },
    "agilent_3d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "complete",
        "notes": "real 3D blocks; read/low-memory and conversion tests",
    },
    "agilent_4d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release archive; synthetic boundary case",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "complete",
        "notes": "4D boundary case without procpar; shape supplied manually",
    },
    "bruker_1d": {
        "format": "Bruker",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "partial",
        "missing_components": "pdata/1 processed data (referenced by test_read_pdata_1d)",
        "notes": "real FID, parameters, pulse program; read tests",
    },
    "bruker_2d": {
        "format": "Bruker",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "partial",
        "missing_components": "pdata/1 processed data (referenced by test_read_pdata_2d)",
        "notes": "ser, padding, parameters; read/low-memory and conversion tests",
    },
    "bruker_3d": {
        "format": "Bruker",
        "provenance": "nmrglue v0.5 release archive (6 original files) + 116 locally generated NMRPipe references",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "original files from release asset; derived references generated by NMRPipe, no explicit license",
        "availability": "partial",
        "missing_components": "pdata/ processed data (referenced by test_bruker_3d)",
        "notes": "3D parameters, ser, indexed fid references; read/low-memory and conversion tests",
    },
    "simpson_1d": {
        "format": "SIMPSON",
        "provenance": "nmrglue v0.5 release archive; simulator input",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "partial",
        "missing_components": "encoding-set outputs (TEXT/BINARY/XREIM/RAWBIN); only input .in present",
        "notes": "1D input file; encoding-set tests need generated outputs",
    },
    "simpson_2d": {
        "format": "SIMPSON",
        "provenance": "nmrglue v0.5 release archive; simulator input",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "partial",
        "missing_components": "encoding-set outputs (2D variants); only input .in present",
        "notes": "2D input file; encoding-set tests need generated outputs",
    },
    "tecmag": {
        "format": "Tecmag",
        "provenance": "nmrglue v0.5 release archive; community contribution",
        "license": "BSD-3-Clause (nmrglue repository license; not separately applied to data)",
        "redistribution_status": "UNRESOLVED",
        "evidence": "release asset has no explicit data license; repository license scope unconfirmed",
        "availability": "complete",
        "notes": "LiCl reference pair (.tnt + .txt); load-time and sign-check tests",
    },
}

# Release-critical groups NOT present in the local corpus.
MISSING_GROUPS = {
    "jeol_1d_complex_pipe_reference": {
        "format": "JEOL + Pipe",
        "redistribution_status": "NOT_AVAILABLE",
        "evidence": "absent from nmrglue repository, v0.5 release archive, and local corpus; PR #228 added code+tests only; maintainer asked about data availability but no resolution recorded",
        "notes": "real JDF binary structure; data not found in examined sources",
    },
    "jeol_2d_complex_pipe_reference": {
        "format": "JEOL + Pipe",
        "redistribution_status": "NOT_AVAILABLE",
        "evidence": "absent from nmrglue repository, v0.5 release archive, and local corpus; PR #228 added code+tests only; maintainer asked about data availability but no resolution recorded",
        "notes": "real 2D JDF quadrature/layout; data not found in examined sources",
    },
    "sparky_2d_ucsf_pipe_reference": {
        "format": "UCSF + Pipe",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "tiled UCSF layout; requires acquisition or licensed spectrum",
    },
    "rnmrtk_3d_time_reference": {
        "format": "RNMRTK",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "real complex 3D file; requires independent generation",
    },
    "rnmrtk_3d_frequency_pipe_reference": {
        "format": "RNMRTK + Pipe",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "real frequency file and independent conversion reference",
    },
    "jcampdx_affn_spectrum": {
        "format": "JCAMP-DX",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "human-auditable real spectrum; requires licensed test set",
    },
    "jcampdx_ntuples_spectrum": {
        "format": "JCAMP-DX",
        "redistribution_status": "UNRESOLVED",
        "evidence": "not present in local corpus or v0.5 archive",
        "notes": "real NTUPLES arrays; requires licensed test set",
    },
    "simpson_1d_encoding_set": {
        "format": "SIMPSON",
        "redistribution_status": "UNRESOLVED",
        "evidence": "input .in present; encoding outputs not generated",
        "notes": "TEXT/BINARY/XREIM/RAWBIN equivalence; requires SIMPSON regeneration",
    },
    "simpson_2d_encoding_set": {
        "format": "SIMPSON",
        "redistribution_status": "UNRESOLVED",
        "evidence": "input .in present; encoding outputs not generated",
        "notes": "2D encoding variants; requires SIMPSON regeneration",
    },
}


def should_exclude(name: str) -> bool:
    if name in EXCLUDE_NAMES:
        return True
    if any(name.startswith(p) for p in EXCLUDE_PREFIXES):
        return True
    if any(name.endswith(s) for s in EXCLUDE_SUFFIXES):
        return True
    return False


def classify_file(rel_path: str, group_name: str) -> str:
    """Classify a file by its exact relative path.

    Returns 'original' for files present in the v0.5 archive,
    'derived' for locally generated references matching known patterns,
    or 'unknown' for unrecognized files.
    """
    # Build the exact archive path: group_name/filename
    parts = rel_path.split("/")
    if len(parts) < 2:
        return "unknown"
    fname = parts[-1]
    archive_path = f"{group_name}/{fname}"
    archive_files = ARCHIVE_FILES.get(group_name, [])
    if fname in archive_files:
        return "original"
    derived = DERIVED_FILES.get(group_name, {})
    if derived:
        pattern = derived.get("pattern", "")
        if pattern and fname.startswith("test") and fname.endswith(".fid"):
            return "derived"
    return "unknown"


def compute_group(root: Path, group_dir: Path, group_name: str) -> dict:
    files = {}
    total_size = 0
    for path in sorted(group_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if should_exclude(path.name):
            continue
        data = path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        size = len(data)
        provenance_class = classify_file(rel, group_name)
        files[rel] = {"sha256": sha256, "size": size, "provenance_class": provenance_class}
        total_size += size
    return {"files": files, "total_size": total_size, "file_count": len(files)}


def main():
    if not DATA_DIR.is_dir():
        print(f"Error: data directory not found: {DATA_DIR}", file=sys.stderr)
        return 1

    groups = {}
    for entry in sorted(DATA_DIR.iterdir()):
        if not entry.is_dir() or entry.name in EXCLUDE_NAMES:
            continue
        group_name = entry.name
        info = compute_group(DATA_DIR, entry, group_name)
        if info["file_count"] == 0:
            continue
        meta = GROUP_META.get(group_name, {})
        original_count = sum(1 for f in info["files"].values() if f["provenance_class"] == "original")
        derived_count = sum(1 for f in info["files"].values() if f["provenance_class"] == "derived")
        groups[group_name] = {
            "format": meta.get("format", "unknown"),
            "provenance": meta.get("provenance", "unknown"),
            "license": meta.get("license", "UNRESOLVED"),
            "redistribution_status": meta.get("redistribution_status", "UNRESOLVED"),
            "evidence": meta.get("evidence", ""),
            "availability": meta.get("availability", "unknown"),
            "missing_components": meta.get("missing_components", ""),
            "notes": meta.get("notes", ""),
            "file_count": info["file_count"],
            "original_count": original_count,
            "derived_count": derived_count,
            "total_size": info["total_size"],
            "files": info["files"],
        }

    lines = []
    lines.append("# nmrglue-ng release-critical test-data manifest")
    lines.append("# Generated by scripts/generate_testdata_manifest.py")
    lines.append("# Do not edit manually; regenerate when the corpus changes.")
    lines.append("#")
    lines.append("# Redistribution status values:")
    lines.append("#   UNRESOLVED    - no explicit license or rights evidence found")
    lines.append("#   NOT_AVAILABLE - data not found in examined sources")
    lines.append("#   CLEAR         - explicit redistribution permission documented")
    lines.append("")
    lines.append("[manifest]")
    lines.append('version = "2"')
    lines.append(f'total_groups = {len(groups)}')
    lines.append(f'total_files = {sum(g["file_count"] for g in groups.values())}')
    lines.append(f'total_size = {sum(g["total_size"] for g in groups.values())}')
    lines.append(f'missing_groups = {len(MISSING_GROUPS)}')
    lines.append("")

    for gname, gdata in groups.items():
        lines.append(f"[groups.{gname}]")
        lines.append(f'format = "{gdata["format"]}"')
        lines.append(f'provenance = "{gdata["provenance"]}"')
        lines.append(f'license = "{gdata["license"]}"')
        lines.append(f'redistribution_status = "{gdata["redistribution_status"]}"')
        lines.append(f'evidence = "{gdata["evidence"]}"')
        lines.append(f'availability = "{gdata["availability"]}"')
        if gdata["missing_components"]:
            lines.append(f'missing_components = "{gdata["missing_components"]}"')
        lines.append(f'notes = "{gdata["notes"]}"')
        lines.append(f'file_count = {gdata["file_count"]}')
        lines.append(f'original_count = {gdata["original_count"]}')
        lines.append(f'derived_count = {gdata["derived_count"]}')
        lines.append(f'total_size = {gdata["total_size"]}')
        lines.append("")
        for fname, fdata in gdata["files"].items():
            lines.append(f'[groups.{gname}.files."{fname}"]')
            lines.append(f'sha256 = "{fdata["sha256"]}"')
            lines.append(f'size = {fdata["size"]}')
            lines.append(f'provenance_class = "{fdata["provenance_class"]}"')
        lines.append("")

    lines.append("# Release-critical groups NOT present in the local corpus.")
    lines.append("")
    for gname, gdata in MISSING_GROUPS.items():
        lines.append(f"[missing.{gname}]")
        lines.append(f'format = "{gdata["format"]}"')
        lines.append(f'redistribution_status = "{gdata["redistribution_status"]}"')
        lines.append(f'evidence = "{gdata["evidence"]}"')
        lines.append(f'notes = "{gdata["notes"]}"')
        lines.append("")

    MANIFEST_PATH.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    print(f"Manifest written: {MANIFEST_PATH}")
    print(f"  Groups available: {len(groups)}")
    print(f"  Groups missing:   {len(MISSING_GROUPS)}")
    print(f"  Total files:      {sum(g['file_count'] for g in groups.values())}")
    print(f"  Total size:       {sum(g['total_size'] for g in groups.values())} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
