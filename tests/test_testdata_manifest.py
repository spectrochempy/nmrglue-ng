"""Tests for test-data manifest verification contracts."""

import hashlib
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_testdata


def make_manifest(groups=None, total_groups=None, total_files=None, total_size=None):
    """Build a minimal manifest dict."""
    if groups is None:
        groups = {}
    info = {
        "version": "2",
        "total_groups": total_groups if total_groups is not None else len(groups),
        "total_files": total_files if total_files is not None else sum(
            g.get("file_count", 0) for g in groups.values()
        ),
        "total_size": total_size if total_size is not None else sum(
            g.get("total_size", 0) for g in groups.values()
        ),
    }
    return {"manifest": info, "groups": groups, "missing": {}}


def make_group(files=None, file_count=None, total_size=None):
    """Build a minimal group dict."""
    if files is None:
        files = {}
    return {
        "file_count": file_count if file_count is not None else len(files),
        "total_size": total_size if total_size is not None else sum(
            f.get("size", 0) for f in files.values()
        ),
        "files": files,
    }


def make_file_entry(content=b"data"):
    """Build a file entry with correct hash and size."""
    return {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}


def run_verify(manifest_path, data_dir, manifest):
    """Run verify_testdata.main() with patched paths."""
    with patch.object(verify_testdata, "MANIFEST_PATH", manifest_path), \
         patch.object(verify_testdata, "DATA_DIR", data_dir):
        manifest_path.write_text(_toml_dumps(manifest), encoding="utf-8")
        return verify_testdata.main()


def _toml_dumps(manifest):
    """Minimal TOML serializer for test manifests."""
    lines = []
    info = manifest["manifest"]
    lines.append("[manifest]")
    for k, v in info.items():
        lines.append(f"{k} = {repr(v) if isinstance(v, str) else v}")
    lines.append("")
    for gname, gdata in manifest.get("groups", {}).items():
        lines.append(f"[groups.{gname}]")
        for k, v in gdata.items():
            if k == "files":
                continue
            lines.append(f"{k} = {repr(v) if isinstance(v, str) else v}")
        for fpath, fdata in gdata.get("files", {}).items():
            lines.append(f'[groups.{gname}.files."{fpath}"]')
            for fk, fv in fdata.items():
                lines.append(f"{fk} = {repr(fv) if isinstance(fv, str) else fv}")
        lines.append("")
    for gname, gdata in manifest.get("missing", {}).items():
        lines.append(f"[missing.{gname}]")
        for k, v in gdata.items():
            lines.append(f"{k} = {repr(v) if isinstance(v, str) else v}")
        lines.append("")
    return "\n".join(lines)


class TestGlobalCounters:
    def test_group_count_mismatch_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})},
            total_groups=99,
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_file_count_mismatch_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})},
            total_files=99,
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_size_mismatch_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})},
            total_size=999,
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1


class TestExtraFiles:
    def test_extra_in_known_group_detected(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        (data_dir / "grp" / "extra.bin").write_bytes(b"y")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})}
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_extra_in_unknown_dir_detected(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        (data_dir / "unexpected").mkdir()
        (data_dir / "unexpected" / "extra.bin").write_bytes(b"y")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})}
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1


class TestEmptyManifest:
    def test_empty_groups_rejected(self, tmp_path):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        manifest = make_manifest(groups={})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1


class TestFileVerification:
    def test_missing_file_detected(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})}
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_corrupt_file_detected(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"tampered")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})}
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_valid_group_passes(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})}
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 0
