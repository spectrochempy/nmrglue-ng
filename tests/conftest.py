"""Central classification for repository-level test dependencies."""

from importlib.util import find_spec
from pathlib import Path
import shutil

import pytest


DATASET_MODULES = {
    "tests/fileio/test_agilent.py",
    "tests/fileio/test_bruker_with_test_data.py",
    "tests/fileio/test_convert.py",
    "tests/fileio/test_jcampdx.py",
    "tests/fileio/test_jeol.py",
    "tests/fileio/test_pipe_with_test_data.py",
    "tests/fileio/test_rnmrtk.py",
    "tests/fileio/test_rs2d.py",
    "tests/fileio/test_simpson.py",
    "tests/fileio/test_sparky.py",
    "tests/fileio/test_spinsolve.py",
}

SELF_CONTAINED_EXCEPTIONS = {
    "tests/fileio/test_bruker_with_test_data.py::test_read_nuslist",
    "tests/fileio/test_bruker_with_test_data.py::test_read_vdlist",
    "tests/fileio/test_convert.py::test_bruker_3d_acqu3s_isolation",
    "tests/fileio/test_convert.py::test_pipe_to_pipe_preserves_digital_filter_value",
}

DATASET_TESTS = {
    "tests/fileio/test_tecmag.py::test_tecmag_load_time_domain",
}

OPTIONAL_DEPENDENCIES = {
    "tests/fileio/test_convert_csdm.py::test_csdm_1d": "csdmpy",
    "tests/fileio/test_convert_csdm.py::test_csdm_2d": "csdmpy",
    "tests/fileio/test_convert_csdm.py::test_csdm_3d": "csdmpy",
    "tests/fileio/test_rs2d.py::test_rs2d": "xmltodict",
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

        if path == "tests/process/test_pipe_proc.py":
            item.add_marker(pytest.mark.external_software)
            if not nmrpipe_available:
                item.add_marker(pytest.mark.skip(
                    reason="NMRPipe tests require nmrPipe and /bin/csh"
                ))
