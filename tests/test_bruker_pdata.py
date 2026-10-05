"""Autonomous tests for Bruker raw and processed data using packaged fixtures.

Sources:
- exp1: nmrXiv project P52 (doi:10.57992/nmrxiv.p52), CC0 1.0.
- exp2d_hsqc, exp2d_cosy: nmrXiv CENAPTNMR dataset, CC0 1.0.
"""

import os

import numpy as np
import pytest

import nmrglue as ng


DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "nmrglue", "fileio", "tests", "data",
    "bruker_pdata", "exp1"
)

PDATA_DIR = os.path.join(DATA_DIR, "pdata", "1")

HSQC_DIR = os.path.join(
    os.path.dirname(__file__), "..", "nmrglue", "fileio", "tests", "data",
    "bruker_pdata", "exp2d_hsqc"
)

HSQC_PDATA_DIR = os.path.join(HSQC_DIR, "pdata", "1")

COSY_DIR = os.path.join(
    os.path.dirname(__file__), "..", "nmrglue", "fileio", "tests", "data",
    "bruker_pdata", "exp2d_cosy"
)

COSY_PDATA_DIR = os.path.join(COSY_DIR, "pdata", "1")


class TestBrukerRawData:
    """Tests for reading raw Bruker fid data."""

    def test_read_raw(self):
        """Raw fid data reads successfully."""
        dic, data = ng.bruker.read(DATA_DIR)
        assert data.ndim == 1
        assert data.shape == (32768,)
        assert data.dtype == np.complex128

    def test_raw_data_not_all_zero(self):
        """Raw data contains non-zero values."""
        dic, data = ng.bruker.read(DATA_DIR)
        assert np.any(data != 0)

    def test_raw_data_finite(self):
        """All raw data values are finite."""
        dic, data = ng.bruker.read(DATA_DIR)
        assert np.all(np.isfinite(data))

    def test_acqus_present(self):
        """Acquisition parameters are read."""
        dic, data = ng.bruker.read(DATA_DIR)
        assert "acqus" in dic
        acqus = dic["acqus"]
        assert acqus.get("TD", 0) > 0
        assert acqus.get("SW", 0) > 0


class TestBrukerProcessedData:
    """Tests for reading Bruker processed data (pdata)."""

    def test_read_pdata(self):
        """Processed data reads successfully."""
        pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
        assert pdata.ndim == 1
        assert pdata.shape == (65536,)
        assert pdata.dtype == np.float64

    def test_pdata_not_all_zero(self):
        """Processed data contains non-zero values."""
        pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
        assert np.any(pdata != 0)

    def test_pdata_finite(self):
        """All processed data values are finite."""
        pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
        assert np.all(np.isfinite(pdata))

    def test_pdata_procs_present(self):
        """Processing parameters are read."""
        pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
        assert "procs" in pdic
        assert "acqus" in pdic

    def test_pdata_zero_filled(self):
        """Processed data is zero-filled relative to raw data."""
        _, raw = ng.bruker.read(DATA_DIR)
        _, pdata = ng.bruker.read_pdata(PDATA_DIR)
        assert pdata.shape[0] > raw.shape[0]

    def test_pdata_reference_values(self):
        """First and last processed data points match reference values."""
        pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
        # Reference values from the scaled float64 output of read_pdata.
        assert np.isclose(pdata[0], -145784832.0, rtol=1e-6)
        assert np.isclose(pdata[-1], -150757376.0, rtol=1e-6)


class TestBruker2DHSQC:
    """Tests for 2D HSQC raw and processed data."""

    def test_read_raw_2d(self):
        """2D HSQC raw data reads successfully."""
        dic, data = ng.bruker.read(HSQC_DIR)
        assert data.ndim == 2
        assert data.shape == (256, 1024)
        assert data.dtype == np.complex128

    def test_read_pdata_2d(self):
        """2D HSQC processed data reads successfully."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        assert pdata.ndim == 2
        assert pdata.shape == (256, 4096)
        assert pdata.dtype == np.float64

    def test_read_pdata_2d_all_components(self):
        """2D HSQC processed data returns all four quadrature components."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR, all_components=True)
        assert isinstance(pdata, list)
        assert len(pdata) == 4
        for comp in pdata:
            assert comp.shape == (256, 4096)
            assert comp.dtype == np.float64

    def test_pdata_2d_not_all_zero(self):
        """2D HSQC processed data contains non-zero values."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        assert np.any(pdata != 0)

    def test_pdata_2d_finite(self):
        """All 2D HSQC processed data values are finite."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        assert np.all(np.isfinite(pdata))

    def test_pdata_2d_zero_filled(self):
        """Processed 2D data is zero-filled relative to raw data."""
        _, raw = ng.bruker.read(HSQC_DIR)
        _, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        assert pdata.shape[0] >= raw.shape[0]
        assert pdata.shape[1] >= raw.shape[1]

    def test_pdata_2d_procs_present(self):
        """Processing parameters are read for 2D data."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        assert "procs" in pdic
        assert "acqus" in pdic


class TestBruker2DCOSY:
    """Tests for 2D COSY raw and processed data."""

    def test_read_raw_2d(self):
        """2D COSY raw data reads successfully."""
        dic, data = ng.bruker.read(COSY_DIR)
        assert data.ndim == 2
        assert data.shape == (128, 1024)
        assert data.dtype == np.complex128

    def test_read_pdata_2d(self):
        """2D COSY processed data reads successfully."""
        pdic, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        assert pdata.ndim == 2
        assert pdata.shape == (512, 2048)
        assert pdata.dtype == np.float64

    def test_pdata_2d_not_all_zero(self):
        """2D COSY processed data contains non-zero values."""
        pdic, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        assert np.any(pdata != 0)

    def test_pdata_2d_finite(self):
        """All 2D COSY processed data values are finite."""
        pdic, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        assert np.all(np.isfinite(pdata))

    def test_pdata_2d_zero_filled(self):
        """Processed 2D COSY data is zero-filled relative to raw data."""
        _, raw = ng.bruker.read(COSY_DIR)
        _, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        assert pdata.shape[0] >= raw.shape[0]
        assert pdata.shape[1] >= raw.shape[1]
