"""Generate a TOML manifest of the local release-critical test-data corpus.

Scans the data/ directory, computes SHA-256 checksums and sizes for every
file, and writes data/manifest.toml. The manifest documents each logical
group with its provenance and redistribution status.
"""

import hashlib
import os
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MANIFEST_PATH = Path(__file__).resolve().parents[1] / "maintainer" / "testdata-manifest.toml"

# Directories and files excluded from the manifest (scripts, docs, metadata).
EXCLUDE_NAMES = {"README", "conversion_scripts"}
EXCLUDE_SUFFIXES = {".com"}
EXCLUDE_PREFIXES = {"make_"}

# Provenance and redistribution status per logical group.
# Status values: CLEAR, UNKNOWN, POTENTIALLY_RESTRICTED, NOT_AVAILABLE
GROUP_STATUS = {
    "agilent_1d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release test data; historical community contribution",
        "redistribution": "BSD-3-Clause",
        "notes": "real 1D acquisition; read/write and conversion tests",
    },
    "agilent_2d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release test data; historical community contribution",
        "redistribution": "BSD-3-Clause",
        "notes": "real 2D blocks; read/low-memory and conversion tests",
    },
    "agilent_2d_tppi": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release test data; historical community contribution",
        "redistribution": "BSD-3-Clause",
        "notes": "TPPI ordering; read/low-memory tests",
    },
    "agilent_3d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release test data; historical community contribution",
        "redistribution": "BSD-3-Clause",
        "notes": "real 3D blocks; read/low-memory and conversion tests",
    },
    "agilent_4d": {
        "format": "Varian/Agilent",
        "provenance": "nmrglue v0.5 release test data; fake explicit-shape boundary case",
        "redistribution": "BSD-3-Clause",
        "notes": "4D boundary case without procpar; shape supplied manually",
    },
    "bruker_1d": {
        "format": "Bruker",
        "provenance": "nmrglue v0.5 release test data; historical community contribution",
        "redistribution": "BSD-3-Clause",
        "notes": "real FID, parameters, pulse program; read tests",
    },
    "bruker_2d": {
        "format": "Bruker",
        "provenance": "nmrglue v0.5 release test data; historical community contribution",
        "redistribution": "BSD-3-Clause",
        "notes": "ser, padding, parameters; read/low-memory and conversion tests",
    },
    "bruker_3d": {
        "format": "Bruker",
        "provenance": "nmrglue v0.5 release test data; historical community contribution",
        "redistribution": "BSD-3-Clause",
        "notes": "3D parameters, ser, indexed fid reference; read/low-memory tests",
    },
    "simpson_1d": {
        "format": "SIMPSON",
        "provenance": "nmrglue v0.5 release test data; generated simulator output",
        "redistribution": "BSD-3-Clause",
        "notes": "1D input file; encoding-set tests need additional generated outputs",
    },
    "simpson_2d": {
        "format": "SIMPSON",
        "provenance": "nmrglue v0.5 release test data; generated simulator output",
        "redistribution": "BSD-3-Clause",
        "notes": "2D input file; encoding-set tests need additional generated outputs",
    },
    "tecmag": {
        "format": "Tecmag",
        "provenance": "nmrglue v0.5 release test data; historical community contribution",
        "redistribution": "BSD-3-Clause",
        "notes": "LiCl reference pair (.tnt + .txt); load-time and sign-check tests",
    },
}

# Release-critical logical groups that are NOT available in the local corpus.
# These remain blocked on provenance/rights resolution or data acquisition.
MISSING_GROUPS = {
    "jeol_1d_complex_pipe_reference": {
        "format": "JEOL + Pipe",
        "redistribution": "NOT_AVAILABLE",
        "notes": "never published; PR #228 added code+tests only, data absent from repo and release archives",
    },
    "jeol_2d_complex_pipe_reference": {
        "format": "JEOL + Pipe",
        "redistribution": "NOT_AVAILABLE",
        "notes": "never published; PR #228 added code+tests only, data absent from repo and release archives",
    },
    "sparky_2d_ucsf_pipe_reference": {
        "format": "UCSF + Pipe",
        "redistribution": "UNKNOWN",
        "notes": "tiled UCSF layout; requires trace source or licensed spectrum",
    },
    "rnmrtk_3d_time_reference": {
        "format": "RNMRTK",
        "redistribution": "UNKNOWN",
        "notes": "real complex 3D file; requires independent generation",
    },
    "rnmrtk_3d_frequency_pipe_reference": {
        "format": "RNMRTK + Pipe",
        "redistribution": "UNKNOWN",
        "notes": "real frequency file and independent conversion reference",
    },
    "jcampdx_affn_spectrum": {
        "format": "JCAMP-DX",
        "redistribution": "UNKNOWN",
        "notes": "human-auditable real spectrum; requires licensed test set",
    },
    "jcampdx_ntuples_spectrum": {
        "format": "JCAMP-DX",
        "redistribution": "UNKNOWN",
        "notes": "real NTUPLES arrays; requires licensed test set",
    },
    "simpson_1d_encoding_set": {
        "format": "SIMPSON",
        "redistribution": "LIKELY_CLEAR",
        "notes": "TEXT/BINARY/XREIM/RAWBIN equivalence; requires SIMPSON regeneration",
    },
    "simpson_2d_encoding_set": {
        "format": "SIMPSON",
        "redistribution": "LIKELY_CLEAR",
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


def compute_group(root: Path, group_dir: Path) -> dict:
    files = {}
    total_size = 0
    for path in sorted(group_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        name = path.name
        if should_exclude(name):
            continue
        data = path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        size = len(data)
        files[rel] = {"sha256": sha256, "size": size}
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
        info = compute_group(DATA_DIR, entry)
        if info["file_count"] == 0:
            continue
        status = GROUP_STATUS.get(group_name, {})
        groups[group_name] = {
            "format": status.get("format", "unknown"),
            "provenance": status.get("provenance", "unknown"),
            "redistribution": status.get("redistribution", "UNKNOWN"),
            "notes": status.get("notes", ""),
            "file_count": info["file_count"],
            "total_size": info["total_size"],
            "files": info["files"],
        }

    # Write TOML manifest
    lines = []
    lines.append("# nmrglue-ng release-critical test-data manifest")
    lines.append("# Generated by scripts/generate_testdata_manifest.py")
    lines.append("# Do not edit manually; regenerate when the corpus changes.")
    lines.append("")
    lines.append("[manifest]")
    lines.append('version = "1"')
    lines.append(f'total_groups = {len(groups)}')
    lines.append(f'total_files = {sum(g["file_count"] for g in groups.values())}')
    lines.append(f'total_size = {sum(g["total_size"] for g in groups.values())}')
    lines.append("")

    for gname, gdata in groups.items():
        lines.append(f"[groups.{gname}]")
        lines.append(f'format = "{gdata["format"]}"')
        lines.append(f'provenance = "{gdata["provenance"]}"')
        lines.append(f'redistribution = "{gdata["redistribution"]}"')
        lines.append(f'notes = "{gdata["notes"]}"')
        lines.append(f'file_count = {gdata["file_count"]}')
        lines.append(f'total_size = {gdata["total_size"]}')
        lines.append("")
        for fname, fdata in gdata["files"].items():
            key = fname.replace(".", "_").replace("/", "__").replace("-", "_")
            lines.append(f'[groups.{gname}.files."{fname}"]')
            lines.append(f'sha256 = "{fdata["sha256"]}"')
            lines.append(f'size = {fdata["size"]}')
        lines.append("")

    # Document missing groups
    lines.append("# Release-critical groups NOT available in the local corpus.")
    lines.append("# These require provenance/rights resolution or data acquisition.")
    lines.append("")
    for gname, gdata in MISSING_GROUPS.items():
        lines.append(f"[missing.{gname}]")
        lines.append(f'format = "{gdata["format"]}"')
        lines.append(f'redistribution = "{gdata["redistribution"]}"')
        lines.append(f'notes = "{gdata["notes"]}"')
        lines.append("")

    MANIFEST_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Manifest written: {MANIFEST_PATH}")
    print(f"  Groups available: {len(groups)}")
    print(f"  Groups missing:   {len(MISSING_GROUPS)}")
    print(f"  Total files:      {sum(g['file_count'] for g in groups.values())}")
    print(f"  Total size:       {sum(g['total_size'] for g in groups.values())} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
