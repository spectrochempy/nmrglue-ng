"""Autonomous tests for JEOL 2D reader using packaged CENAPTNMR fixtures.

Source: nmrXiv CENAPTNMR project P33 (doi:10.57992/nmrxiv.p33), CC0 1.0.
Sample: (-)-Epicatechin 400 MHz in DMSO-d6.
Directory: (-)-Epicatechin 400 MHz in DMSOd6 NMR data/
Original files: EpiCatechin_2880ug200uL_DMSOd6_{HSQC,COSY,HMBC}_400MHz_Jeol.jdf
"""

import os

import numpy as np
import pytest

import nmrglue as ng


DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "fileio", "data",
    "jeol"
)

HSQC_JDF = os.path.join(DATA_DIR, "epicatechin_hsqc.jdf")
COSY_JDF = os.path.join(DATA_DIR, "epicatechin_cosy.jdf")
HMBC_JDF = os.path.join(DATA_DIR, "epicatechin_hmbc.jdf")

# Reference values decoded independently from each JDF binary.
# HSQC: submatrix size 32x32; interior points at boundaries distinguish
# correct submatrix reordering from a simple reshape.
# atol=1e-12 ensures values near zero are still validated.
HSQC_REFERENCES = {
    (0, 0): complex(-5.050323944963172e-09, 3.5653795334153503e-09),
    (0, 32): complex(0.008414949347426837, 0.004781845031130792),
    (32, 0): complex(4.620134065195179e-09, -2.203621699232194e-09),
    (32, 32): complex(-0.04451286247176576, -0.032451003426983635),
    (1, 33): complex(0.016227229038634525, -0.0026962399809283707),
    (33, 1): complex(2.7001365553112083e-07, 1.8242492177960163e-07),
    (-1, -1): complex(0.010997792545297659, 0.013005593413259567),
}

COSY_REFERENCES = {
    (0, 0): complex(-7.537155207052352e-07, 2.561132283040064e-07),
    (0, 32): complex(-2.397288285564876, 4.517910674832686),
    (32, 0): complex(1.2465051125683823e-07, 7.790479356127177e-09),
    (32, 32): complex(-10.4356564593323, 1.8116640726789084),
    (-1, -1): complex(-4.993196699058739, -0.5408737688172018),
}

HMBC_REFERENCES = {
    (0, 0): complex(-2.025988170987633e-09, -6.127570486879564e-10),
    (0, 32): complex(0.00774774689996836, 0.011893940320856503),
    (32, 0): complex(4.679944279416002e-09, -3.333675325122146e-10),
    (32, 32): complex(-0.00874695746755315, 0.004135239170093128),
    (-1, -1): complex(0.005758069347642383, 0.009595761176026063),
}

EXPERIMENTS = [
    ("HSQC", HSQC_JDF, (64, 1024), HSQC_REFERENCES),
    ("COSY", COSY_JDF, (256, 1280), COSY_REFERENCES),
    ("HMBC", HMBC_JDF, (128, 2048), HMBC_REFERENCES),
]


@pytest.mark.parametrize("name,path,expected_shape,refs", EXPERIMENTS, ids=["hsqc", "cosy", "hmbc"])
def test_read_2d(name, path, expected_shape, refs):
    """2D JEOL experiment reads successfully with correct shape."""
    dic, data = ng.jeol.read(path)
    assert data.ndim == 2
    assert data.shape == expected_shape
    assert data.dtype == np.complex128
    assert "header" in dic
    assert "parameters" in dic


@pytest.mark.parametrize("name,path,expected_shape,refs", EXPERIMENTS, ids=["hsqc", "cosy", "hmbc"])
def test_reference_points(name, path, expected_shape, refs):
    """Reference points match independently decoded values."""
    dic, data = ng.jeol.read(path)
    for (row, col), expected in refs.items():
        assert np.isclose(data[row, col].real, expected.real, rtol=1e-6, atol=1e-12), f"{name}[{row},{col}].real"
        assert np.isclose(data[row, col].imag, expected.imag, rtol=1e-6, atol=1e-12), f"{name}[{row},{col}].imag"


@pytest.mark.parametrize("name,path,expected_shape,refs", EXPERIMENTS, ids=["hsqc", "cosy", "hmbc"])
def test_data_finite(name, path, expected_shape, refs):
    """All data values are finite."""
    dic, data = ng.jeol.read(path)
    assert np.all(np.isfinite(data))


def test_experiments_distinct():
    """The three 2D experiment types contain different data."""
    _, hsqc = ng.jeol.read(HSQC_JDF)
    _, cosy = ng.jeol.read(COSY_JDF)
    _, hmbc = ng.jeol.read(HMBC_JDF)
    assert not np.array_equal(hsqc, cosy)
    assert not np.array_equal(hsqc, hmbc)
    assert not np.array_equal(cosy, hmbc)
