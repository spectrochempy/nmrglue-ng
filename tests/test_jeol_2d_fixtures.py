"""Autonomous tests for JEOL 2D reader using packaged CENAPTNMR fixture.

Source: nmrXiv CENAPTNMR project P33 (doi:10.57992/nmrxiv.p33), CC0 1.0.
Sample: (-)-Epicatechin 400 MHz in DMSO-d6.
Directory: (-)-Epicatechin 400 MHz in DMSOd6 NMR data/
Original file: EpiCatechin_2880ug200uL_DMSOd6_HSQC_400MHz_Jeol.jdf
"""

import os

import numpy as np
import pytest

import nmrglue as ng


DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "nmrglue", "fileio", "tests", "data",
    "jeol"
)

HSQC_JDF = os.path.join(DATA_DIR, "epicatechin_hsqc.jdf")

# Reference values decoded independently from the JDF binary.
# Submatrix size is 32x32; interior points at boundaries distinguish
# correct submatrix reordering from a simple reshape.
# atol=1e-12 ensures values near zero are still validated.
REFERENCES = {
    (0, 0): complex(-5.050323944963172e-09, 3.5653795334153503e-09),
    (0, 32): complex(0.008414949347426837, 0.004781845031130792),
    (32, 0): complex(4.620134065195179e-09, -2.203621699232194e-09),
    (32, 32): complex(-0.04451286247176576, -0.032451003426983635),
    (1, 33): complex(0.016227229038634525, -0.0026962399809283707),
    (33, 1): complex(2.7001365553112083e-07, 1.8242492177960163e-07),
    (-1, -1): complex(0.010997792545297659, 0.013005593413259567),
}


class TestJEOL2DHSQC:
    """Tests for 2D JEOL HSQC data."""

    def test_read_2d(self):
        """2D JEOL HSQC reads successfully."""
        dic, data = ng.jeol.read(HSQC_JDF)
        assert data.ndim == 2
        assert data.shape == (64, 1024)
        assert data.dtype == np.complex128

    @pytest.mark.parametrize("row,col", sorted(REFERENCES.keys()))
    def test_reference_point(self, row, col):
        """Each reference point matches independently decoded values."""
        dic, data = ng.jeol.read(HSQC_JDF)
        expected = REFERENCES[(row, col)]
        assert np.isclose(data[row, col].real, expected.real, rtol=1e-6, atol=1e-12)
        assert np.isclose(data[row, col].imag, expected.imag, rtol=1e-6, atol=1e-12)

    def test_data_finite(self):
        """All data values are finite."""
        dic, data = ng.jeol.read(HSQC_JDF)
        assert np.all(np.isfinite(data))

    def test_dic_structure(self):
        """Dictionary contains header and parameters."""
        dic, data = ng.jeol.read(HSQC_JDF)
        assert "header" in dic
        assert "parameters" in dic
