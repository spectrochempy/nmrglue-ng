"""Autonomous tests for JEOL reader using packaged fixtures.

Provenance:
- fluorine.jdf, phosphorus.jdf: cheminfo/jeol-data-test commit 70bf716 (MIT).
- Rutin_*: cheminfo/jeol-data-test, Harvard Dataverse doi:10.7910/DVN/ZAZDNM
  (CC0 1.0). Sample: Rutin 400 MHz DMSO-d6.
- betapinene_1h.jdf: nmrXiv CENAPTNMR P33 (doi:10.57992/nmrxiv.p33), CC0 1.0.
  Sample: (-)-beta-Pinene 400 MHz CDCl3.
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
BETAPINENE_1H_JDF = os.path.join(PACKAGED_DIR, "betapinene_1h.jdf")

ALL_JDF = [FLUORINE_JDF, PHOSPHORUS_JDF, RUTIN_1H_JDF, RUTIN_13C_JDF, BETAPINENE_1H_JDF]
ALL_IDS = ["fluorine", "phosphorus", "rutin_1h", "rutin_13c", "betapinene_1h"]

# Reference values independently decoded from file headers.
# Tolerances: obs/sw/car use rtol=1e-9 (float64 header fields);
# data points use rtol=1e-12, atol=1e-15 (complex128 raw values).
REFERENCES = {
    "fluorine": {
        "obs": 470.3635083723063,
        "sw": 120192.30769230769,
        "car": -47036.35083723063,
        "label": "Fluorine19",
        "data0": complex(7.620145409751202e-06, -1.1279323971145658e-05),
        "data_last": complex(0.9854882215952051, -7.403006410224372),
    },
    "phosphorus": {
        "obs": 202.35776576271843,
        "sw": 100806.45161290323,
        "car": 0.0,
        "label": "Phosphorus31",
        "data0": complex(1.3274132619759818e-06, -1.657363657238721e-06),
        "data_last": complex(1.2426289372795047, 1.1737636211514353),
    },
    "rutin_1h": {
        "obs": 399.78219837825003,
        "sw": 10016.02564102564,
        "car": 3598.0397854042494,
        "label": "1H",
        "data0": complex(1.0030291683557906e-05, -5.259830863566379e-06),
        "data_last": complex(-0.013827245303944658, 0.015472459899770677),
    },
    "rutin_13c": {
        "obs": 100.52530332516541,
        "sw": 31565.656565656565,
        "car": 10052.53033251654,
        "label": "13C",
        "data0": complex(1.0346708107190219e-08, 2.5246874318274507e-08),
        "data_last": complex(0.0034788697442304714, -0.010487021382253317),
    },
    "betapinene_1h": {
        "obs": 399.78219837825003,
        "sw": 7494.00479616307,
        "car": 1998.9109918912502,
        "label": "Proton",
        "data0": complex(2.2085355861803515e-05, -1.7638300730708127e-05),
        "data_last": complex(0.005702196020709063, -0.0040669821388828005),
    },
}


@pytest.mark.parametrize("fid", ALL_IDS)
def test_read_1d(fid):
    """Each packaged 1D fixture reads successfully."""
    path = dict(zip(ALL_IDS, ALL_JDF))[fid]
    dic, data = ng.jeol.read(path)
    assert data.ndim == 1
    assert data.shape[0] > 0
    assert data.dtype == np.complex128
    assert "header" in dic
    assert "parameters" in dic


@pytest.mark.parametrize("path", ALL_JDF, ids=ALL_IDS)
def test_data_finite(path):
    """All fixture data values are finite."""
    dic, data = ng.jeol.read(path)
    assert np.all(np.isfinite(data))


@pytest.mark.parametrize("fid", ALL_IDS)
def test_udic_reference(fid):
    """guess_udic matches independently decoded header values."""
    path = dict(zip(ALL_IDS, ALL_JDF))[fid]
    ref = REFERENCES[fid]
    dic, data = ng.jeol.read(path)
    udic = ng.jeol.guess_udic(dic, data)
    assert udic["ndim"] == 1
    assert udic[0]["size"] == data.shape[0]
    assert udic[0]["encoding"] == "complex"
    assert udic[0]["label"] == ref["label"]
    assert np.isclose(udic[0]["obs"], ref["obs"], rtol=1e-9)
    assert np.isclose(udic[0]["sw"], ref["sw"], rtol=1e-9)
    assert np.isclose(udic[0]["car"], ref["car"], rtol=1e-9)


@pytest.mark.parametrize("fid", ALL_IDS)
def test_data_points_reference(fid):
    """First and last complex data points match reference values."""
    path = dict(zip(ALL_IDS, ALL_JDF))[fid]
    ref = REFERENCES[fid]
    dic, data = ng.jeol.read(path)
    assert np.isclose(data[0].real, ref["data0"].real, rtol=1e-12, atol=1e-15)
    assert np.isclose(data[0].imag, ref["data0"].imag, rtol=1e-12, atol=1e-15)
    assert np.isclose(data[-1].real, ref["data_last"].real, rtol=1e-12, atol=1e-15)
    assert np.isclose(data[-1].imag, ref["data_last"].imag, rtol=1e-12, atol=1e-15)


def test_fluorine_and_phosphorus_distinct():
    """The two element-specific fixtures contain different data."""
    _, fdata = ng.jeol.read(FLUORINE_JDF)
    _, pdata = ng.jeol.read(PHOSPHORUS_JDF)
    assert not np.array_equal(fdata, pdata)
