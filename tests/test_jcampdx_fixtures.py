"""Autonomous tests for JCAMP-DX reader using packaged CENAPTNMR fixtures.

Source: nmrXiv CENAPTNMR project P33 (doi:10.57992/nmrxiv.p33), CC0 1.0.
Samples: (-)-Epicatechin 400 MHz DMSO-d6; (-)-beta-Pinene 60/400 MHz CDCl3;
Caffeic acid 400 MHz DMSO-d6.
"""

import os

import numpy as np
import pytest

import nmrglue as ng


DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "nmrglue", "fileio", "tests", "data",
    "jcampdx"
)

JDX_EPIC_1H = os.path.join(DATA_DIR, "epicatechin_1h.jdx")
JDX_EPIC_13C = os.path.join(DATA_DIR, "epicatechin_13c.jdx")
JDX_PINENE_1H = os.path.join(DATA_DIR, "betapinene_1h_60mhz.jdx")
JDX_CAFFEIC_13C = os.path.join(DATA_DIR, "caffeicacid_13c.jdx")

# Reference values decoded independently from the JCAMP-DX SQZ/DIF data.
REFERENCES = {
    "epic_1h": {
        "size": 104858,
        0: -0.00016932092497646685,
        1: -0.0001770019275771338,
        -1: -0.000156669861869486,
    },
    "epic_13c": {
        "size": 104858,
        0: 1.5481548475971462e-06,
        1: 2.4166319572248136e-06,
        -1: -2.1523128369033497e-06,
    },
    "pinene_1h": {
        "size": 65536,
        0: 0.03146649637602431,
        1: 0.03175891230194292,
        -1: 0.03105541891495032,
    },
    "caffeic_13c": {
        "size": 52430,
        0: -1.8542965080818778e-06,
        1: -3.1787940138546475e-06,
        -1: 2.847669637411455e-06,
    },
}

ALL_JDX = [JDX_EPIC_1H, JDX_EPIC_13C, JDX_PINENE_1H, JDX_CAFFEIC_13C]
ALL_IDS = ["epic_1h", "epic_13c", "pinene_1h", "caffeic_13c"]


class TestJCAMPDX1D:
    """Tests for 1D JCAMP-DX data."""

    @pytest.mark.parametrize("fid", ALL_IDS)
    def test_read_1d(self, fid):
        """1D JCAMP-DX reads successfully with correct shape."""
        path = dict(zip(ALL_IDS, ALL_JDX))[fid]
        dic, data = ng.jcampdx.read(path)
        assert data.ndim == 1
        assert data.shape == (REFERENCES[fid]["size"],)
        assert data.dtype == np.float64

    @pytest.mark.parametrize("fid", ALL_IDS)
    def test_reference_points(self, fid):
        """First, second, and last points match reference values."""
        path = dict(zip(ALL_IDS, ALL_JDX))[fid]
        dic, data = ng.jcampdx.read(path)
        refs = REFERENCES[fid]
        for idx in [0, 1, -1]:
            assert np.isclose(data[idx], refs[idx], rtol=1e-6), f"data[{idx}] for {fid}"

    @pytest.mark.parametrize("fid", ALL_IDS)
    def test_data_finite(self, fid):
        """All data values are finite."""
        path = dict(zip(ALL_IDS, ALL_JDX))[fid]
        dic, data = ng.jcampdx.read(path)
        assert np.all(np.isfinite(data))

    @pytest.mark.parametrize("fid", ALL_IDS)
    def test_dic_is_dict(self, fid):
        """Reader returns a dictionary."""
        path = dict(zip(ALL_IDS, ALL_JDX))[fid]
        dic, data = ng.jcampdx.read(path)
        assert isinstance(dic, dict)
