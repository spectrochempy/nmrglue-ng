"""Tests for test-data manifest generation and verification contracts."""

import hashlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_testdata_manifest
import verify_testdata


DEFAULT_CRITICAL_TEST = "tests/test_dummy.py::test_critical"


def make_component(paths, status="present", required_by=None, notes=""):
    if required_by is None:
        required_by = []
    scope = "critical" if DEFAULT_CRITICAL_TEST in required_by else "extended"
    return {
        "status": status,
        "scope": scope,
        "paths": list(paths),
        "required_by": list(required_by),
        "notes": notes,
    }


def make_manifest(groups=None, missing=None, critical_tests=None, overrides=None):
    """Build a manifest dict with self-consistent declared counters."""
    if groups is None:
        groups = {}
    if missing is None:
        missing = {}
    if critical_tests is None:
        critical_tests = [DEFAULT_CRITICAL_TEST]
    components = [
        c for g in list(groups.values()) + list(missing.values())
        for c in g.get("components", {}).values()
    ]
    critical = set(critical_tests)
    info = {
        "version": "3",
        "total_groups": len(groups),
        "total_files": sum(g.get("file_count", 0) for g in groups.values()),
        "total_size": sum(g.get("total_size", 0) for g in groups.values()),
        "missing_groups": len(missing),
        "total_components": len(components),
        "absent_components": sum(1 for c in components if c.get("status") == "absent"),
        "critical_components": sum(
            1 for c in components if set(c.get("required_by", [])) & critical
        ),
        "absent_critical_components": sum(
            1 for c in components
            if c.get("status") == "absent" and set(c.get("required_by", [])) & critical
        ),
        "critical_tests": list(critical_tests),
    }
    if overrides:
        info.update(overrides)
    return {"manifest": info, "groups": groups, "missing": missing}


def make_group(files=None, components=None, file_count=None, total_size=None):
    """Build a minimal group dict.

    Without explicit components, a single ``raw`` component covers the
    inventoried files so that availability is derivable.
    """
    if files is None:
        files = {}
    if components is None:
        components = {"raw": make_component(sorted(files), status="present")}
    statuses = [c.get("status") for c in components.values()]
    absent = sorted(cid for cid, c in components.items() if c.get("status") == "absent")
    if statuses and all(s == "present" for s in statuses):
        availability = "complete"
    elif any(s == "present" for s in statuses):
        availability = "partial"
    else:
        availability = "not_available"
    return {
        "file_count": file_count if file_count is not None else len(files),
        "total_size": total_size if total_size is not None else sum(
            f.get("size", 0) for f in files.values()
        ),
        "availability": availability,
        "missing_components": ", ".join(absent),
        "component_count": len(components),
        "absent_component_count": len(absent),
        "files": files,
        "components": components,
    }


def make_missing(components=None):
    components = components or {}
    absent = sum(1 for c in components.values() if c.get("status") == "absent")
    return {
        "components": components,
        "component_count": len(components),
        "absent_component_count": absent,
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


def _toml_key(name):
    if all(c.isalnum() or c in "_-" for c in name):
        return name
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _toml_value(value):
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    return str(value)


def _toml_dumps(manifest):
    """Minimal TOML serializer for test manifests."""
    lines = []

    def emit_table(prefix, data):
        scalars = {k: v for k, v in data.items() if not isinstance(v, dict)}
        nested = {k: v for k, v in data.items() if isinstance(v, dict)}
        if scalars or not nested:
            lines.append(f"[{prefix}]" if prefix else "[manifest]")
            for k, v in scalars.items():
                lines.append(f"{_toml_key(k)} = {_toml_value(v)}")
            lines.append("")
        for k, v in nested.items():
            emit_table(f"{prefix}.{_toml_key(k)}" if prefix else _toml_key(k), v)

    emit_table("", manifest["manifest"])
    for gname, gdata in manifest.get("groups", {}).items():
        files = gdata.get("files", {})
        rest = {k: v for k, v in gdata.items() if k != "files"}
        emit_table(f"groups.{_toml_key(gname)}", rest)
        for fpath, fdata in files.items():
            lines.append(f'[groups.{_toml_key(gname)}.files."{fpath}"]')
            for fk, fv in fdata.items():
                lines.append(f"{_toml_key(fk)} = {_toml_value(fv)}")
            lines.append("")
    for gname, gdata in manifest.get("missing", {}).items():
        emit_table(f"missing.{_toml_key(gname)}", gdata)
    return "\n".join(lines)


def load_tracked_manifest():
    with open(generate_testdata_manifest.MANIFEST_PATH, "rb") as f:
        return tomllib.load(f)


def tracked_component_paths(manifest):
    paths = set()
    for section in ("groups", "missing"):
        for gdata in manifest.get(section, {}).values():
            for comp in gdata.get("components", {}).values():
                paths.update(comp.get("paths", []))
    return paths


class TestGlobalCounters:
    def test_group_count_mismatch_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})},
            overrides={"total_groups": 99},
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_file_count_mismatch_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})},
            overrides={"total_files": 99},
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_size_mismatch_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"x")})},
            overrides={"total_size": 999},
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_component_count_mismatch_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        group = make_group(files={"grp/f.bin": make_file_entry(b"x")})
        group["component_count"] = 99
        manifest = make_manifest(groups={"grp": group})
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


class TestSizeChain:
    def test_group_total_mismatch_fails(self, tmp_path):
        """Group total_size inconsistent with sum of file sizes must fail."""
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        # File is 1 byte, but group declares total_size=999
        group = make_group(files={"grp/f.bin": make_file_entry(b"x")}, total_size=999)
        # Global total matches the (wrong) group total, so only the
        # file->group chain check catches the inconsistency.
        manifest = make_manifest(
            groups={"grp": group}, overrides={"total_size": 999}
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_consistent_size_chain_passes(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"xy")
        manifest = make_manifest(
            groups={"grp": make_group(files={"grp/f.bin": make_file_entry(b"xy")})}
        )
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 0


class TestClassifyFile:
    def test_archive_top_level_file_is_original(self):
        assert generate_testdata_manifest.classify_file("agilent_1d/fid", "agilent_1d") == "original"
        assert generate_testdata_manifest.classify_file("bruker_3d/ser", "bruker_3d") == "original"

    def test_derived_pattern_matches_relative_path(self):
        assert generate_testdata_manifest.classify_file("bruker_3d/fid/test001.fid", "bruker_3d") == "derived"
        assert generate_testdata_manifest.classify_file("bruker_3d/fid/test116.fid", "bruker_3d") == "derived"

    def test_same_basename_in_wrong_path_is_unknown(self):
        # "fid" exists in archive for agilent_1d, but not under generated/
        assert generate_testdata_manifest.classify_file("agilent_1d/generated/fid", "agilent_1d") == "unknown"

    def test_similar_name_in_wrong_path_is_unknown(self):
        # "test999.fid" looks derived but is not under fid/
        assert generate_testdata_manifest.classify_file("bruker_3d/unrelated/test999.fid", "bruker_3d") == "unknown"

    def test_unknown_group_file_is_unknown(self):
        assert generate_testdata_manifest.classify_file("agilent_1d/new-reference.bin", "agilent_1d") == "unknown"


class TestComponentStructure:
    def test_group_without_components_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        group = make_group(files={"grp/f.bin": make_file_entry(b"x")})
        group["components"] = {}
        group["component_count"] = 0
        group["absent_component_count"] = 0
        manifest = make_manifest(groups={"grp": group})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_duplicate_component_path_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        group = make_group(
            files={"grp/f.bin": make_file_entry(b"x")},
            components={
                "raw": make_component(["grp/f.bin"]),
                "again": make_component(["grp/f.bin"]),
            },
        )
        manifest = make_manifest(groups={"grp": group})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_availability_not_derived_from_components_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        group = make_group(
            files={"grp/f.bin": make_file_entry(b"x")},
            components={
                "raw": make_component(["grp/f.bin"], status="present"),
                "ref": make_component(["grp/test.fid"], status="absent"),
            },
        )
        group["availability"] = "complete"
        manifest = make_manifest(groups={"grp": group})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_scope_not_derived_from_required_by_fails(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "f.bin").write_bytes(b"x")
        comp = make_component(["grp/f.bin"], required_by=[DEFAULT_CRITICAL_TEST])
        comp["scope"] = "extended"
        group = make_group(files={"grp/f.bin": make_file_entry(b"x")},
                           components={"raw": comp})
        manifest = make_manifest(groups={"grp": group})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1


class TestAvailabilityResultAxes:
    def _corpus(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "raw.bin").write_bytes(b"x")
        return data_dir

    def test_all_required_components_present_returns_zero(self, tmp_path):
        data_dir = self._corpus(tmp_path)
        group = make_group(
            files={"grp/raw.bin": make_file_entry(b"x")},
            components={"raw": make_component(["grp/raw.bin"], status="present")},
        )
        manifest = make_manifest(groups={"grp": group})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 0

    def test_absent_critical_component_returns_two(self, tmp_path):
        data_dir = self._corpus(tmp_path)
        group = make_group(
            files={"grp/raw.bin": make_file_entry(b"x")},
            components={
                "raw": make_component(["grp/raw.bin"], status="present"),
                "pipe_reference": make_component(
                    ["grp/test.fid"], status="absent",
                    required_by=[DEFAULT_CRITICAL_TEST],
                ),
            },
        )
        manifest = make_manifest(groups={"grp": group})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 2

    def test_absent_extended_component_returns_zero(self, tmp_path):
        data_dir = self._corpus(tmp_path)
        group = make_group(
            files={"grp/raw.bin": make_file_entry(b"x")},
            components={
                "raw": make_component(["grp/raw.bin"], status="present"),
                "extended_ref": make_component(["grp/test.sec"], status="absent"),
            },
        )
        manifest = make_manifest(groups={"grp": group})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 0

    def test_integrity_failure_returns_one_not_two(self, tmp_path):
        data_dir = self._corpus(tmp_path)
        group = make_group(
            files={"grp/raw.bin": make_file_entry(b"x")},
            components={
                "raw": make_component(["grp/raw.bin"], status="present"),
                "pipe_reference": make_component(
                    ["grp/test.fid"], status="absent",
                    required_by=[DEFAULT_CRITICAL_TEST],
                ),
            },
        )
        manifest = make_manifest(groups={"grp": group})
        (data_dir / "grp" / "raw.bin").write_bytes(b"tampered")
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_declared_absent_but_present_on_disk_returns_one(self, tmp_path):
        data_dir = self._corpus(tmp_path)
        (data_dir / "grp" / "test.fid").write_bytes(b"y")
        group = make_group(
            files={"grp/raw.bin": make_file_entry(b"x")},
            components={
                "raw": make_component(["grp/raw.bin"], status="present"),
                "pipe_reference": make_component(
                    ["grp/test.fid"], status="absent",
                    required_by=[DEFAULT_CRITICAL_TEST],
                ),
            },
        )
        manifest = make_manifest(groups={"grp": group})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 1

    def test_output_distinguishes_integrity_from_availability(self, tmp_path, capsys):
        data_dir = self._corpus(tmp_path)
        group = make_group(
            files={"grp/raw.bin": make_file_entry(b"x")},
            components={
                "raw": make_component(["grp/raw.bin"], status="present"),
                "pipe_reference": make_component(
                    ["grp/test.fid"], status="absent",
                    required_by=[DEFAULT_CRITICAL_TEST],
                ),
            },
        )
        manifest = make_manifest(groups={"grp": group})
        code = run_verify(tmp_path / "m.toml", data_dir, manifest)
        out = capsys.readouterr().out
        assert code == 2
        assert "INTEGRITY: PASSED" in out
        assert "AVAILABILITY: INCOMPLETE" in out
        assert "RELEASE-CRITICAL CORPUS INCOMPLETE" in out
        assert "INTEGRITY: PASSED" in out.split("AVAILABILITY")[0]


class TestDerivation:
    def test_status_absent_when_nothing_matches(self):
        assert generate_testdata_manifest.derive_component_status(
            {}, ["grp/test.fid"]
        ) == "absent"

    def test_status_present_when_all_paths_match(self):
        files = {"grp/a.sec": {}, "grp/a.par": {}}
        assert generate_testdata_manifest.derive_component_status(
            files, ["grp/a.sec", "grp/a.par"]
        ) == "present"

    def test_mixed_materialization_is_rejected(self):
        files = {"grp/a.sec": {}}
        with pytest.raises(ValueError):
            generate_testdata_manifest.derive_component_status(
                files, ["grp/a.sec", "grp/a.par"]
            )

    def test_mask_matches_digit_series(self):
        files = {"grp/data/test001.fid": {}, "grp/data/test002.fid": {}}
        assert generate_testdata_manifest.derive_component_status(
            files, ["grp/data/test%03d.fid"]
        ) == "present"

    def test_availability_rules(self):
        derive = generate_testdata_manifest.derive_availability
        assert derive(["present", "present"]) == "complete"
        assert derive(["present", "absent"]) == "partial"
        assert derive(["absent", "absent"]) == "not_available"
        assert derive([]) == "not_available"

    def test_scope_derived_from_required_by(self):
        scope = generate_testdata_manifest.component_scope
        assert scope(["tests/test_convert.py::test_agilent_1d"]) == "critical"
        assert scope([]) == "extended"
        assert scope(["tests/test_x.py::test_y"]) == "extended"


class TestRequirementCoverage:
    """The inventory-scope defect: consumed references must be accounted.

    A reference consumed by a tracked dataset test must be inventoried in the
    manifest or explicitly declared absent in a required component. Before the
    fix, groups such as agilent_1d were declared complete while their tests
    consumed unlisted missing references (test.fid, RNMRTK .sec/.par pairs).

    This test confronts the references the static extractor recognizes;
    ``TestStaticExtractorScope`` pins those constructions and their limits,
    and ``test_critical_tests_are_all_declared`` covers the test-id side of
    the contract independently of extraction.
    """

    def test_every_consumed_reference_is_accounted(self):
        manifest = load_tracked_manifest()
        declared = tracked_component_paths(manifest)
        files = {
            rel for gdata in manifest.get("groups", {}).values()
            for rel in gdata.get("files", {})
        }
        unaccounted = []
        for module in generate_testdata_manifest.SCANNED_TEST_MODULES:
            refs = generate_testdata_manifest.extract_data_references(
                generate_testdata_manifest.TESTS_DIR / module
            )
            for func, paths in refs.items():
                for p in sorted(paths):
                    if not generate_testdata_manifest.is_accounted(p, declared, files):
                        unaccounted.append(f"tests/{module}::{func} -> {p}")
        assert not unaccounted, (
            "recognized references neither inventoried nor declared absent:\n"
            + "\n".join(unaccounted)
        )

    def test_critical_tests_are_all_declared(self):
        manifest = load_tracked_manifest()
        covered = set()
        for section in ("groups", "missing"):
            for gdata in manifest.get(section, {}).values():
                for comp in gdata.get("components", {}).values():
                    covered.update(comp.get("required_by", []))
        critical = set(manifest["manifest"]["critical_tests"])
        assert critical == set(generate_testdata_manifest.CRITICAL_TESTS)
        missing = sorted(critical - covered)
        assert not missing, f"release-critical tests in no component: {missing}"

    def test_declared_test_ids_exist(self):
        known = generate_testdata_manifest.known_test_ids()
        manifest = load_tracked_manifest()
        unknown = set()
        for section in ("groups", "missing"):
            for gdata in manifest.get(section, {}).values():
                for comp in gdata.get("components", {}).values():
                    for test_id in comp.get("required_by", []):
                        if test_id not in known:
                            unknown.add(test_id)
        assert not unknown, f"required_by references unknown tests: {sorted(unknown)}"

    def test_tracked_manifest_structure_is_consistent(self):
        errors = verify_testdata.verify_structure(load_tracked_manifest())
        assert not errors, "\n".join(errors)

    def test_tracked_manifest_counters_match_generator(self):
        manifest = load_tracked_manifest()
        info = manifest["manifest"]
        assert info["version"] == generate_testdata_manifest.MANIFEST_VERSION
        assert set(info["critical_tests"]) == set(generate_testdata_manifest.CRITICAL_TESTS)


class TestStaticExtractorScope:
    """Pin the extractor's recognized constructions and its documented limits.

    The extractor is a complementary control: generation-time validation and
    ``test_every_consumed_reference_is_accounted`` only see references these
    forms resolve. The append-list loop form is the one exercised by
    ``tests/test_jcampdx.py``; iterating a literal list directly is out of
    scope and must stay documented as such.
    """

    @staticmethod
    def _extract(tmp_path, source):
        module = tmp_path / "test_probe.py"
        module.write_text(source, encoding="utf-8")
        refs = generate_testdata_manifest.extract_data_references(module)
        return refs.get("test_probe", set())

    def test_recognizes_direct_join(self, tmp_path):
        paths = self._extract(tmp_path, (
            "import os\n"
            "from setup import DATA_DIR\n"
            "def test_probe():\n"
            "    read(os.path.join(DATA_DIR, 'grp', 'fid'))\n"
        ))
        assert paths == {"grp/fid"}

    def test_recognizes_path_division(self, tmp_path):
        paths = self._extract(tmp_path, (
            "from pathlib import Path\n"
            "from setup import DATA_DIR\n"
            "def test_probe():\n"
            "    read(Path(DATA_DIR) / 'bruker_1d')\n"
        ))
        assert paths == {"bruker_1d"}

    def test_recognizes_alias_rooted_fstring(self, tmp_path):
        paths = self._extract(tmp_path, (
            "import os\n"
            "from setup import DATA_DIR\n"
            "def test_probe():\n"
            "    d = os.path.join(DATA_DIR, 'grp')\n"
            "    read(f'{d}/fid')\n"
        ))
        assert paths == {"grp", "grp/fid"}

    def test_recognizes_append_list_loop(self, tmp_path):
        paths = self._extract(tmp_path, (
            "import os\n"
            "from setup import DATA_DIR\n"
            "def test_probe():\n"
            "    cases = []\n"
            "    cases.append('a.dx')\n"
            "    cases.append('b.dx')\n"
            "    for case in cases:\n"
            "        read(os.path.join(DATA_DIR, 'jcampdx', case))\n"
        ))
        assert paths == {"jcampdx/a.dx", "jcampdx/b.dx"}

    def test_recognizes_enumerate_subscript_loop(self, tmp_path):
        paths = self._extract(tmp_path, (
            "import os\n"
            "from setup import DATA_DIR\n"
            "def test_probe():\n"
            "    cases = []\n"
            "    cases.append(('a.dx', 16384))\n"
            "    cases.append(('b.dx', 4096))\n"
            "    for i, case in enumerate(cases):\n"
            "        read(os.path.join(DATA_DIR, 'jcampdx', case[0]))\n"
        ))
        assert paths == {"jcampdx/a.dx", "jcampdx/b.dx"}

    def test_literal_list_iteration_is_out_of_scope(self, tmp_path):
        paths = self._extract(tmp_path, (
            "import os\n"
            "from setup import DATA_DIR\n"
            "def test_probe():\n"
            "    for name in ['a.bin', 'b.bin']:\n"
            "        read(os.path.join(DATA_DIR, 'grp', name))\n"
        ))
        assert paths == set(), (
            "iterating a literal list is not a recognized construction; if "
            "this starts returning paths, update the extractor docstring "
            "and the CONTRIBUTING scope description together"
        )


class TestArchetypeRawPresentReferenceMissing:
    """A group whose raw data is present but whose conversion reference is
    missing must not be declared complete."""

    def test_tracked_agilent_1d_declares_its_conversion_reference(self):
        manifest = load_tracked_manifest()
        group = manifest["groups"]["agilent_1d"]
        assert group["availability"] != "complete"
        pipe = group["components"]["pipe_reference"]
        assert pipe["status"] == "absent"
        assert "agilent_1d/test.fid" in pipe["paths"]
        assert "tests/test_convert.py::test_agilent_1d" in pipe["required_by"]

    def test_tracked_agilent_1d_raw_is_present(self):
        manifest = load_tracked_manifest()
        group = manifest["groups"]["agilent_1d"]
        assert group["components"]["raw"]["status"] == "present"

    def test_synthetic_raw_present_reference_missing_is_partial(self, tmp_path):
        data_dir = tmp_path / "data"
        (data_dir / "grp").mkdir(parents=True)
        (data_dir / "grp" / "fid").write_bytes(b"x")
        (data_dir / "grp" / "procpar").write_bytes(b"y")
        files = {
            "grp/fid": make_file_entry(b"x"),
            "grp/procpar": make_file_entry(b"y"),
        }
        group = make_group(
            files=files,
            components={
                "raw": make_component(["grp/fid", "grp/procpar"], status="present"),
                "pipe_reference": make_component(
                    ["grp/test.fid"], status="absent",
                    required_by=[DEFAULT_CRITICAL_TEST],
                ),
            },
        )
        assert group["availability"] == "partial"
        assert group["missing_components"] == "pipe_reference"
        manifest = make_manifest(groups={"grp": group})
        assert run_verify(tmp_path / "m.toml", data_dir, manifest) == 2
