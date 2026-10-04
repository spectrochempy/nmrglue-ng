"""Validate installed metadata, imports, and packaged NMRPipe/Bruker fixtures."""

from importlib import import_module, metadata
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from packaging.version import Version


def main(report):
    import nmrglue

    package_path = Path(nmrglue.__file__).resolve()
    if not package_path.is_relative_to(Path(sys.prefix).resolve()):
        raise SystemExit(f"Import is outside the validation environment: {package_path}")
    if Version(metadata.version("nmrglue-ng")) != Version(nmrglue.__version__):
        raise SystemExit("Distribution and import versions differ")
    for module in (
        "analysis", "fileio", "process", "process.nmrtxt.rance_kay", "util",
    ):
        import_module(f"nmrglue.{module}")
    print(f"Installed nmrglue-ng {nmrglue.__version__}: {package_path}", flush=True)
    report = str(Path(report).resolve())
    with TemporaryDirectory(prefix="nmrglue-wheel-", dir=Path(report).parent) as directory:
        subprocess.run(
            [
                sys.executable, "-I", "-m", "pytest", "--pyargs",
                "nmrglue.fileio.tests.test_pipe",
                "nmrglue.fileio.tests.test_bruker",
                "--strict-markers", "--strict-config", "-ra",
                f"--junitxml={report}",
            ],
            cwd=directory,
            check=True,
        )


if __name__ == "__main__":
    main(sys.argv[1])
