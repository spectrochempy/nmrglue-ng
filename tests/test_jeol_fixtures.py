"""Autonomous tests for JEOL reader using packaged fixtures.

Source: cheminfo/jeol-data-test (MIT), original data Harvard Dataverse
doi:10.7910/DVN/ZAZDNM (CC0 1.0). Sample: Rutin 400 MHz DMSO-d6.
"""

import os

import numpy as np
import pytest

import nmrglue as ng


PACKAGED_DIR = os.path.join(
    os.path.dirname(__file__), "..", "nmrglue", "fileio", "tests", "data", "jeol"
)

FLUORINE_JDF = os.path.join(PACKAGED_DIR, "fluorine.jdf")
PHOSPHORUS_JDF = os.path.join(PACKAGED_DIR, "phosphorus.jdf")
RUTIN_1H_JDF = os.path.join(
    PACKAGED_DIR, "Rutin_3080ug200uL_DMSOd6_qHNMR_400MHz_Jeol.jdf"
)
RUTIN_13C_JDF = os.path.join(
    PACKAGED_DIR, "Rutin_3080ug200uL_DMSOd6_13CNMR_400MHz_Jeol.jdf"
)

ALL_JDF = [FLUORINE_JDF, PHOSPHORUS_JDF, RUTIN_1H_JDF, RUTIN_13C_JDF]
ALL_IDS = ["fluorine", "phosphorus", "rutin_1h", "rutin_13c"]


@pytest.mark.parametrize("path", ALL_JDF, ids=ALL_IDS)
def test_read_1d(path):
    """Each packaged 1D fixture reads successfully."""
    dic, data = ng.jeol.read(path)
    assert data.ndim == 1
    assert data.shape == (32768,)
    assert data.dtype == np.complex128
    assert "header" in dic
    assert "parameters" in dic


@pytest.mark.parametrize("path", ALL_JDF, ids=ALL_IDS)
def test_data_not_all_zero(path):
    """Fixture data contains non-zero values."""
    dic, data = ng.jeol.read(path)
    assert np.any(data != 0)


def test_rutin_1h_udic():
    """guess_udic returns sane values for the Rutin 1H fixture."""
    dic, data = ng.jeol.read(RUTIN_1H_JDF)
    udic = ng.jeol.guess_udic(dic, data)
    assert udic["ndim"] == 1
    assert udic[0]["size"] == 32768
    assert udic[0]["encoding"] == "complex"
    assert udic[0]["obs"] > 0
    assert udic[0]["sw"] > 0


def test_rutin_13c_udic():
    """guess_udic returns sane values for the Rutin 13C fixture."""
    dic, data = ng.jeol.read(RUTIN_13C_JDF)
    udic = ng.jeol.guess_udic(dic, data)
    assert udic["ndim"] == 1
    assert udic[0]["size"] == 32768
    assert udic[0]["encoding"] == "complex"
    assert udic[0]["obs"] > 0
    assert udic[0]["sw"] > 0


def test_fluorine_and_phosphorus_distinct():
    """The two element-specific fixtures contain different data."""
    _, fdata = ng.jeol.read(FLUORINE_JDF)
    _, pdata = ng.jeol.read(PHOSPHORUS_JDF)
    assert not np.array_equal(fdata, pdata)
