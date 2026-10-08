"""Validate a runtime wheel with functional tests staged from its sdist."""

from importlib import import_module, metadata
from pathlib import Path
import shutil
import sys
import sysconfig
from tempfile import TemporaryDirectory

from packaging.version import Version


EXPECTED_CASES = 64


class InstalledOriginGuard:
    def __init__(self, source_root, staged_tests):
        self.source_root = source_root.resolve()
        self.staged_tests = staged_tests.resolve()
        self.site_packages = {
            Path(path).resolve()
            for path in (sysconfig.get_path("purelib"), sysconfig.get_path("platlib"))
            if path
        }
        self.collected = 0

    def _assert_origin(self, module):
        path = getattr(module, "__file__", None)
        if path is None:
            return
        path = Path(path).resolve()
        if path.is_relative_to(self.source_root) or path.is_relative_to(self.staged_tests):
            raise RuntimeError(f"nmrglue imported from test source: {path}")
        if not any(path.is_relative_to(site) for site in self.site_packages):
            raise RuntimeError(f"nmrglue import is outside site-packages: {path}")

    def _assert_origins(self):
        import nmrglue

        self._assert_origin(nmrglue)
        for module in tuple(sys.modules.values()):
            if module is not None and getattr(module, "__name__", "").startswith("nmrglue"):
                self._assert_origin(module)
        for package_path in nmrglue.__path__:
            path = Path(package_path).resolve()
            if not any(path.is_relative_to(site) for site in self.site_packages):
                raise RuntimeError(f"nmrglue package path is outside site-packages: {path}")

    def pytest_sessionstart(self, session):
        self._assert_origins()

    def pytest_collection_finish(self, session):
        self.collected = len(session.items)
        if self.collected != EXPECTED_CASES:
            raise RuntimeError(
                f"expected {EXPECTED_CASES} wheel functional cases, collected {self.collected}"
            )
        self._assert_origins()

    def pytest_sessionfinish(self, session, exitstatus):
        self._assert_origins()


def main(sdist_root, report):
    import pytest
    import nmrglue

    sdist_root = Path(sdist_root).resolve()
    package_path = Path(nmrglue.__file__).resolve()
    if Version(metadata.version("nmrglue-ng")) != Version(nmrglue.__version__):
        raise SystemExit("Distribution and import versions differ")
    for module in ("analysis", "fileio", "process", "process.nmrtxt.rance_kay", "util"):
        import_module(f"nmrglue.{module}")
    print(f"Installed nmrglue-ng {nmrglue.__version__}: {package_path}", flush=True)

    report = Path(report).resolve()
    with TemporaryDirectory(prefix="nmrglue-wheel-", dir=report.parent) as directory:
        directory = Path(directory)
        staged_tests = directory / "tests"
        shutil.copytree(sdist_root / "tests", staged_tests)
        config = sdist_root / "pytest.ini"
        guard = InstalledOriginGuard(sdist_root, staged_tests)
        status = pytest.main(
            [
                "--import-mode=importlib",
                "--rootdir", str(staged_tests),
                "-c", str(config),
                str(staged_tests / "fileio" / "test_pipe.py"),
                str(staged_tests / "fileio" / "test_bruker.py"),
                "--strict-markers", "--strict-config", "-ra",
                f"--junitxml={report}",
            ],
            plugins=[guard],
        )
        if status:
            raise SystemExit(status)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
