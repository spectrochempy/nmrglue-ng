"""Check release version coherence and built distribution artifacts."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import tarfile
import tomllib
import zipfile


RELEASE_HEADING = re.compile(r"^## (?P<version>\S+) - \d{4}-\d{2}-\d{2}$", re.M)


def read_source_version(source_root: Path) -> str:
    try:
        from setuptools_scm import get_version
    except ModuleNotFoundError as exc:
        raise RuntimeError("setuptools_scm is required to check source version") from exc

    return get_version(root=source_root)


def metadata_value(metadata: str, field: str) -> str:
    prefix = f"{field}: "
    for line in metadata.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    raise RuntimeError(f"missing metadata field: {field}")


def check_source(source_root: Path, expected_version: str | None) -> str:
    version = read_source_version(source_root)
    if expected_version and version != expected_version:
        raise RuntimeError(f"expected version {expected_version}, got {version}")

    project = tomllib.loads((source_root / "pyproject.toml").read_text())["project"]
    if project["name"] != "nmrglue-ng":
        raise RuntimeError(f"unexpected project name: {project['name']}")
    if project["dynamic"] != ["version"]:
        raise RuntimeError("project version must remain dynamic")

    if "setuptools_scm" not in tomllib.loads(
        (source_root / "pyproject.toml").read_text()
    )["tool"]:
        raise RuntimeError("dynamic version must come from setuptools_scm")

    changelog = (source_root / "CHANGELOG.md").read_text()
    headings = [match.group("version") for match in RELEASE_HEADING.finditer(changelog)]
    if ".dev" not in version and version not in headings:
        raise RuntimeError(f"CHANGELOG.md has no dated heading for {version}")

    ref_type = os.environ.get("GITHUB_REF_TYPE")
    ref_name = os.environ.get("GITHUB_REF_NAME")
    if ref_type == "tag" and ref_name != f"v{version}":
        raise RuntimeError(f"tag {ref_name!r} does not match version {version!r}")

    print(f"source version: {version}")
    return version


def check_sdist(sdist: Path, version: str) -> None:
    expected_name = f"nmrglue_ng-{version}.tar.gz"
    if sdist.name != expected_name:
        raise RuntimeError(f"unexpected sdist name {sdist.name!r}, expected {expected_name!r}")

    prefix = f"nmrglue_ng-{version}/"
    with tarfile.open(sdist) as archive:
        names = set(archive.getnames())
        pkg_info_name = f"{prefix}PKG-INFO"
        metadata = archive.extractfile(pkg_info_name).read().decode()
        for required in (
            "maintainer/testdata-manifest.toml",
            "tests/infrastructure/test_ci_validation.py",
            "tests/infrastructure/test_testdata_manifest.py",
            ".github/scripts/check_installed_wheel.py",
            ".github/scripts/check_test_report.py",
        ):
            if f"{prefix}{required}" not in names:
                raise RuntimeError(f"sdist is missing {required}")

    check_distribution_metadata(metadata, version)
    print(f"checked sdist: {sdist.name}")


def check_wheel(wheel: Path, version: str) -> None:
    expected_name = f"nmrglue_ng-{version}-py3-none-any.whl"
    if wheel.name != expected_name:
        raise RuntimeError(f"unexpected wheel name {wheel.name!r}, expected {expected_name!r}")

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        metadata_name = f"nmrglue_ng-{version}.dist-info/METADATA"
        metadata = archive.read(metadata_name).decode()
        if not any(name.startswith("nmrglue/") for name in names):
            raise RuntimeError("wheel does not contain the nmrglue package")
        if any(name.startswith("tests/") for name in names):
            raise RuntimeError("runtime wheel must not contain tests/")
        if any(name.startswith("maintainer/") for name in names):
            raise RuntimeError("runtime wheel must not contain maintainer/")

    check_distribution_metadata(metadata, version)
    print(f"checked wheel: {wheel.name}")


def check_distribution_metadata(metadata: str, version: str) -> None:
    if metadata_value(metadata, "Name") != "nmrglue-ng":
        raise RuntimeError("distribution metadata name is not nmrglue-ng")
    if metadata_value(metadata, "Version") != version:
        raise RuntimeError("distribution metadata version does not match source")
    if metadata_value(metadata, "Requires-Python") != ">=3.10":
        raise RuntimeError("distribution metadata Requires-Python changed")


def check_dist(dist: Path, version: str) -> None:
    sdists = sorted(dist.glob("*.tar.gz"))
    wheels = sorted(dist.glob("*.whl"))
    if len(sdists) != 1:
        raise RuntimeError(f"expected one sdist, found {len(sdists)}")
    if len(wheels) != 1:
        raise RuntimeError(f"expected one wheel, found {len(wheels)}")
    check_sdist(sdists[0], version)
    check_wheel(wheels[0], version)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--expected-version", default="")
    parser.add_argument("--dist", type=Path)
    args = parser.parse_args()

    expected_version = args.expected_version or None
    source_root = args.source_root.resolve()
    version = check_source(source_root, expected_version)
    if args.dist is not None:
        check_dist(args.dist.resolve(), version)


if __name__ == "__main__":
    main()
