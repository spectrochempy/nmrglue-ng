"""Tests for retrieving the exact release files recorded by PyPI."""

from contextlib import nullcontext
import hashlib
import io
import json
from pathlib import Path
import runpy

import pytest


download_release_artifacts = runpy.run_path(
    str(
        Path(__file__).resolve().parents[2]
        / ".github/scripts/download_pypi_release_artifacts.py"
    )
)["download_release_artifacts"]


def opener_for(files):
    def opener(url):
        return nullcontext(io.BytesIO(files[url]))

    return opener


def test_download_release_artifacts_checks_pypi_hashes(tmp_path):
    version = "1.2.0"
    sdist = b"sdist"
    wheel = b"wheel"
    urls = {
        f"https://files.example/nmrglue_ng-{version}.tar.gz": sdist,
        f"https://files.example/nmrglue_ng-{version}-py3-none-any.whl": wheel,
    }
    index = {
        "urls": [
            {
                "filename": filename.rsplit("/", 1)[1],
                "url": filename,
                "digests": {"sha256": hashlib.sha256(payload).hexdigest()},
            }
            for filename, payload in urls.items()
        ]
    }
    urls[f"https://pypi.org/pypi/nmrglue-ng/{version}/json"] = json.dumps(index).encode()

    paths = download_release_artifacts(version, tmp_path, opener_for(urls))

    assert [path.name for path in paths] == [
        f"nmrglue_ng-{version}.tar.gz",
        f"nmrglue_ng-{version}-py3-none-any.whl",
    ]
    assert [path.read_bytes() for path in paths] == [sdist, wheel]


def test_download_release_artifacts_rejects_invalid_pypi_hash(tmp_path):
    version = "1.2.0"
    filename = f"nmrglue_ng-{version}.tar.gz"
    index = {
        "urls": [
            {
                "filename": filename,
                "url": "https://files.example/sdist",
                "digests": {"sha256": "0" * 64},
            },
            {
                "filename": f"nmrglue_ng-{version}-py3-none-any.whl",
                "url": "https://files.example/wheel",
                "digests": {"sha256": hashlib.sha256(b"wheel").hexdigest()},
            },
        ]
    }
    files = {
        f"https://pypi.org/pypi/nmrglue-ng/{version}/json": json.dumps(index).encode(),
        "https://files.example/sdist": b"sdist",
        "https://files.example/wheel": b"wheel",
    }

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        download_release_artifacts(version, tmp_path, opener_for(files))


def test_download_release_artifacts_rejects_extra_pypi_artifacts(tmp_path):
    version = "1.2.0"
    index = {
        "urls": [
            {"filename": f"nmrglue_ng-{version}.tar.gz"},
            {"filename": f"nmrglue_ng-{version}-py3-none-any.whl"},
            {"filename": f"nmrglue_ng-{version}-cp313-cp313-manylinux.whl"},
        ]
    }
    files = {f"https://pypi.org/pypi/nmrglue-ng/{version}/json": json.dumps(index).encode()}

    with pytest.raises(RuntimeError, match="exactly the expected artifacts"):
        download_release_artifacts(version, tmp_path, opener_for(files))
