"""Autonomous tests for JEOL 2D reader using packaged CENAPTNMR fixture.

Source: nmrXiv CENAPTNMR project P33 (doi:10.57992/nmrxiv.p33), CC0 1.0.
Sample: (-)-Epicatechin 400 MHz in DMSO-d6.
Directory: (-)-Epicatechin 400 MHz in DMSOd6 NMR data/
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


class TestJEOL2DHSQC:
    """Tests for 2D JEOL HSQC data."""

    def test_read_2d(self):
        """2D JEOL HSQC reads successfully."""
        dic, data = ng.jeol.read(HSQC_JDF)
        assert data.ndim == 2
        assert data.shape == (64, 1024)
        assert data.dtype == np.complex128

    def test_reference_points(self):
        """Data corners match independently decoded reference values."""
        dic, data = ng.jeol.read(HSQC_JDF)
        assert np.isclose(data[0, 0].real, -5.050323944963172e-09, rtol=1e-6)
        assert np.isclose(data[0, 0].imag, 3.5653795334153503e-09, rtol=1e-6)
        assert np.isclose(data[-1, -1].real, 0.010997792545297659, rtol=1e-6)
        assert np.isclose(data[-1, -1].imag, 0.013005593413259567, rtol=1e-6)

    def test_data_finite(self):
        """All data values are finite."""
        dic, data = ng.jeol.read(HSQC_JDF)
        assert np.all(np.isfinite(data))

    def test_dic_structure(self):
        """Dictionary contains header and parameters."""
        dic, data = ng.jeol.read(HSQC_JDF)
        assert "header" in dic
        assert "parameters" in dic
