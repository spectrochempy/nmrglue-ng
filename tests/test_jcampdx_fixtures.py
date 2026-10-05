"""Autonomous tests for JCAMP-DX reader using packaged CENAPTNMR fixtures.

Source: nmrXiv CENAPTNMR project P33 (doi:10.57992/nmrxiv.p33), CC0 1.0.
Sample: (-)-Epicatechin 400 MHz in DMSO-d6.
Original files: EpiCatechin_2880ug200uL_DMSOd6_1H/13C_400MHz_JDX.jdx
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

EXPECTED_SIZE = 104858

# Reference values decoded independently from the JCAMP-DX SQZ data.
REFERENCES = {
    "1h": {
        0: -0.00016932092497646685,
        1: -0.0001770019275771338,
        50000: -0.00017971286967148682,
        -1: -0.000156669861869486,
    },
    "13c": {
        0: 1.5481548475971462e-06,
        1: 2.4166319572248136e-06,
        50000: -1.4348752246022332e-06,
        -1: -2.1523128369033497e-06,
    },
}


class TestJCAMPDX1D:
    """Tests for 1D JCAMP-DX data."""

    @pytest.mark.parametrize("path, fid", [(JDX_1H, "1h"), (JDX_13C, "13c")], ids=["1h", "13c"])
    def test_read_1d(self, path, fid):
        """1D JCAMP-DX reads successfully with correct shape."""
        dic, data = ng.jcampdx.read(path)
        assert data.ndim == 1
        assert data.shape == (EXPECTED_SIZE,)
        assert data.dtype == np.float64

    @pytest.mark.parametrize("path, fid", [(JDX_1H, "1h"), (JDX_13C, "13c")], ids=["1h", "13c"])
    def test_reference_points(self, path, fid):
        """First, second, middle, and last points match reference values."""
        dic, data = ng.jcampdx.read(path)
        refs = REFERENCES[fid]
        for idx, expected in refs.items():
            assert np.isclose(data[idx], expected, rtol=1e-6), f"data[{idx}] for {fid}"

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
