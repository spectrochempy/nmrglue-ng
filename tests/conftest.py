"""Central classification for repository-level test dependencies."""

from importlib.util import find_spec
from pathlib import Path
import shutil

import pytest


DATASET_MODULES = {
    "tests/test_agilent.py",
    "tests/test_bruker_with_test_data.py",
    "tests/test_convert.py",
    "tests/test_jcampdx.py",
    "tests/test_jeol.py",
    "tests/test_pipe_with_test_data.py",
    "tests/test_rnmrtk.py",
    "tests/test_rs2d.py",
    "tests/test_simpson.py",
    "tests/test_sparky.py",
    "tests/test_spinsolve.py",
}

SELF_CONTAINED_EXCEPTIONS = {
    "tests/test_bruker_with_test_data.py::test_read_nuslist",
    "tests/test_bruker_with_test_data.py::test_read_vdlist",
    "tests/test_jeol.py::test_1d_real",
    "tests/test_jeol.py::test_2d_rr",
}

DATASET_TESTS = {
    "tests/test_tecmag.py::test_tecmag_load_time_domain",
}

OPTIONAL_DEPENDENCIES = {
    "nmrglue/fileio/tests/test_convert_csdm.py::test_csdm_1d": "csdmpy",
    "nmrglue/fileio/tests/test_convert_csdm.py::test_csdm_2d": "csdmpy",
    "nmrglue/fileio/tests/test_convert_csdm.py::test_csdm_3d": "csdmpy",
    "tests/test_rs2d.py::test_rs2d": "xmltodict",
}


def pytest_collection_modifyitems(config, items):
    """Mark and skip tests according to their verified external needs."""
    root = config.rootpath
    data_available = (root / "data").is_dir()
    nmrpipe_available = (
        shutil.which("nmrPipe") is not None and Path("/bin/csh").is_file()
    )

    for item in items:
        path = item.path.relative_to(root).as_posix()
        nodeid = item.nodeid.split("[", 1)[0]

        dependency = OPTIONAL_DEPENDENCIES.get(nodeid)
        if dependency is not None:
            item.add_marker(pytest.mark.optional_dependency)
            if find_spec(dependency) is None:
                item.add_marker(pytest.mark.skip(
                    reason=f"optional dependency not installed: {dependency}"
                ))

        requires_dataset = (
            path in DATASET_MODULES and nodeid not in SELF_CONTAINED_EXCEPTIONS
        ) or nodeid in DATASET_TESTS
        if requires_dataset:
            item.add_marker(pytest.mark.dataset)
            if not data_available:
                item.add_marker(pytest.mark.skip(
                    reason=f"external test data directory not available: {root / 'data'}"
                ))

        if path == "tests/test_pipe_proc.py":
            item.add_marker(pytest.mark.external_software)
            if not nmrpipe_available:
                item.add_marker(pytest.mark.skip(
                    reason="NMRPipe tests require nmrPipe and /bin/csh"
                ))
