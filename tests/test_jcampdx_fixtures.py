"""Autonomous tests for JCAMP-DX reader using packaged CENAPTNMR fixtures.

Source: nmrXiv CENAPTNMR project P33 (doi:10.57992/nmrxiv.p33), CC0 1.0.
Sample: (-)-Epicatechin 400 MHz in DMSO-d6.
"""

import os

import numpy as np
import pytest

import nmrglue as ng


DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "nmrglue", "fileio", "tests", "data",
    "jcampdx"
)

JDX_1H = os.path.join(DATA_DIR, "epicatechin_1h.jdx")
JDX_13C = os.path.join(DATA_DIR, "epicatechin_13c.jdx")


class TestJCAMPDX1D:
    """Tests for 1D JCAMP-DX data."""

    @pytest.mark.parametrize(
        "path, ref0, ref_last",
        [
            (JDX_1H, -0.00016932092497646685, -0.000156669861869486),
            (JDX_13C, 1.5481548475971462e-06, -2.1523128369033497e-06),
        ],
        ids=["1h", "13c"],
    )
    def test_read_1d(self, path, ref0, ref_last):
        """1D JCAMP-DX reads successfully with correct reference values."""
        dic, data = ng.jcampdx.read(path)
        assert data.ndim == 1
        assert data.dtype == np.float64
        assert np.isclose(data[0], ref0, rtol=1e-6)
        assert np.isclose(data[-1], ref_last, rtol=1e-6)

    @pytest.mark.parametrize("path", [JDX_1H, JDX_13C], ids=["1h", "13c"])
    def test_data_finite(self, path):
        """All data values are finite."""
        dic, data = ng.jcampdx.read(path)
        assert np.all(np.isfinite(data))

    @pytest.mark.parametrize("path", [JDX_1H, JDX_13C], ids=["1h", "13c"])
    def test_dic_is_dict(self, path):
        """Reader returns a dictionary."""
        dic, data = ng.jcampdx.read(path)
        assert isinstance(dic, dict)
