"""Autonomous tests for Bruker raw and processed data using packaged fixtures.

Sources:
- exp1: nmrXiv project P52 (doi:10.57992/nmrxiv.p52), CC0 1.0.
  Directory: nmrxiv-pt-succrose/1/
- exp2d_hsqc: nmrXiv CENAPTNMR project P33 (doi:10.57992/nmrxiv.p33),
  sample S208 Ginsenoside Rg1, CC0 1.0.
  Directory: Ginsenoside_3110ug200uL_HSQC_600MHz_Bruker/
- exp2d_cosy: nmrXiv CENAPTNMR project P33 (doi:10.57992/nmrxiv.p33),
  sample S213 Gossypol, CC0 1.0.
  Directory: Gossypol_3650ug200uL_CDCl3_COSY_600MHz_JDX/

Reference values are decoded independently from the binary files.
Processed values include the NC_proc scaling factor from the procs file.
Tolerances: rtol=1e-6 for scaled float64 values; exact match for
integer-valued raw complex data.

Note: in exp2d_hsqc the processed files and the acquisition files describe
two different acquisitions (see the fixture README), so that fixture
exercises a discordance between parameter sets rather than a
re-referencing of one coherent dataset.
"""

import os

import numpy as np
import pytest

import nmrglue as ng
from nmrglue.fileio import fileiobase


DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "fileio", "data",
    "bruker_pdata", "exp1"
)

PDATA_DIR = os.path.join(DATA_DIR, "pdata", "1")

HSQC_DIR = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "fileio", "data",
    "bruker_pdata", "exp2d_hsqc"
)

HSQC_PDATA_DIR = os.path.join(HSQC_DIR, "pdata", "1")

COSY_DIR = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "fileio", "data",
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

    def test_raw_data_reference_points(self):
        """First and last raw data points match independently decoded values."""
        dic, data = ng.bruker.read(DATA_DIR)
        assert data[0] == np.complex128(1070.375 + 474.421875j)
        assert data[-1] == np.complex128(181362.5546875 - 308311.4140625j)

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

    def test_pdata_finite(self):
        """All processed data values are finite."""
        pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
        assert np.all(np.isfinite(pdata))

    def test_pdata_procs_present(self):
        """Processing parameters are read."""
        pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
        assert "procs" in pdic
        assert "acqus" in pdic

    def test_pdata_shape_exceeds_raw(self):
        """Processed data is larger than raw data (zero-filled)."""
        _, raw = ng.bruker.read(DATA_DIR)
        _, pdata = ng.bruker.read_pdata(PDATA_DIR)
        assert pdata.shape[0] > raw.shape[0]

    def test_pdata_reference_values(self):
        """First and last processed data points match reference values.

        Raw 1r values: -17796 and -18403 (int32).
        NC_proc scaling factor: 2**13 = 8192.
        Scaled: -17796 * 8192 = -145784832; -18403 * 8192 = -150757376.
        """
        pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
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

    def test_raw_2d_reference_points(self):
        """Raw 2D data corners match independently decoded values."""
        dic, data = ng.bruker.read(HSQC_DIR)
        assert data[0, 0] == np.complex128(0j)
        assert data[-1, -1] == np.complex128(86 + 87j)
        assert data[0, -1] == np.complex128(-60 - 187j)

    def test_read_pdata_2d(self):
        """2D HSQC processed data reads successfully."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        assert pdata.ndim == 2
        assert pdata.shape == (256, 4096)
        assert pdata.dtype == np.float64

    def test_pdata_2d_reference_points(self):
        """2D HSQC processed data corners match reference values."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        assert np.isclose(pdata[0, 0], 112.0087890625, rtol=1e-6)
        assert np.isclose(pdata[-1, -1], 96.127197265625, rtol=1e-6)

    def test_read_pdata_2d_all_components(self):
        """2D HSQC returns four distinct quadrature components."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR, all_components=True)
        assert isinstance(pdata, list)
        assert len(pdata) == 4
        for comp in pdata:
            assert comp.shape == (256, 4096)
            assert comp.dtype == np.float64
        # Each component has distinct values at [0,0] and [-1,-1].
        c00 = [c[0, 0] for c in pdata]
        c_ll = [c[-1, -1] for c in pdata]
        assert len(set(c00)) == 4
        assert len(set(c_ll)) == 4

    def test_pdata_2d_component_references(self):
        """Each HSQC quadrature component matches its reference values.

        Components in order: 2rr, 2ri, 2ir, 2ii.
        Values decoded independently from each binary file.
        """
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR, all_components=True)
        expected_00 = [112.0087890625, -20.171142578125, 11.845947265625, -9.540283203125]
        expected_ll = [96.127197265625, -48.282470703125, -12.356689453125, 20.320068359375]
        for i, comp in enumerate(pdata):
            assert np.isclose(comp[0, 0], expected_00[i], rtol=1e-6), f"comp[{i}][0,0]"
            assert np.isclose(comp[-1, -1], expected_ll[i], rtol=1e-6), f"comp[{i}][-1,-1]"

    def test_pdata_2d_finite(self):
        """All 2D HSQC processed data values are finite."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        assert np.all(np.isfinite(pdata))

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

    def test_raw_2d_reference_points(self):
        """Raw 2D COSY data corners match independently decoded values."""
        dic, data = ng.bruker.read(COSY_DIR)
        assert data[0, 0] == np.complex128(0j)
        assert data[-1, -1] == np.complex128(9470 - 18671j)

    def test_read_pdata_2d(self):
        """2D COSY processed data reads successfully."""
        pdic, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        assert pdata.ndim == 2
        assert pdata.shape == (512, 2048)
        assert pdata.dtype == np.float64

    def test_pdata_2d_reference_points(self):
        """2D COSY processed data corners match reference values."""
        pdic, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        assert np.isclose(pdata[0, 0], 49.9375, rtol=1e-6)
        assert np.isclose(pdata[-1, -1], 114.4375, rtol=1e-6)

    def test_pdata_2d_finite(self):
        """All 2D COSY processed data values are finite."""
        pdic, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        assert np.all(np.isfinite(pdata))


class TestBrukerProcessedAxes:
    """Tests for the explicit `pdata` processing-parameter selection (#55).

    When pdata=True, guess_udic derives axes from procs/procNs
    (OFFSET, SF, SW_p) rather than from acqus (SFO1, O1, SW_h).
    Expected values are derived from the fixture's procs parameters:
        first point = OFFSET (ppm)
        last point  = OFFSET - (SI-1) * SW_p / (SI * SF) (ppm)
    which is the convention documented by Bruker TopSpin, "Processing Commands
    and Parameters", Version 007 (doc H9776SA3_7_007), p. 27 and p. 121.

    What these tests show: that the option reproduces the axis stored in the
    processed file, that the raw axis is untouched, and that pdata=False and
    pdata=None keep the historical default. They do not show that the default
    (acquisition-parameter) axis is wrong. In exp2d_hsqc the processed
    parameters and the acquisition headers come from two different
    acquisitions 2.000000 ppm apart (see
    tests/fixtures/fileio/data/bruker_pdata/README.md), which is why only the
    HSQC direct first/last point assertions separate the two choices; in
    exp1 and exp2d_cosy the two parameter sets agree and both choices give
    the same axis.
    """

    def test_hsqc_direct_first_point(self):
        """HSQC direct first point matches procs OFFSET."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        udic = ng.bruker.guess_udic(pdic, pdata, pdata=True)
        uc = fileiobase.uc_from_udic(udic, 1)
        first, _ = uc.ppm_limits()
        assert np.isclose(first, pdic["procs"]["OFFSET"], atol=1e-4)

    def test_hsqc_direct_last_point(self):
        """HSQC direct last point matches OFFSET-derived value."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        udic = ng.bruker.guess_udic(pdic, pdata, pdata=True)
        uc = fileiobase.uc_from_udic(udic, 1)
        _, last = uc.ppm_limits()
        p = pdic["procs"]
        expected = p["OFFSET"] - (p["SI"] - 1) * p["SW_p"] / (p["SI"] * p["SF"])
        assert np.isclose(last, expected, atol=1e-4)

    def test_hsqc_indirect_first_point(self):
        """HSQC indirect first point matches proc2s OFFSET."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        udic = ng.bruker.guess_udic(pdic, pdata, pdata=True)
        uc = fileiobase.uc_from_udic(udic, 0)
        first, _ = uc.ppm_limits()
        assert np.isclose(first, pdic["proc2s"]["OFFSET"], atol=1e-4)

    def test_hsqc_indirect_last_point(self):
        """HSQC indirect last point matches OFFSET-derived value."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        udic = ng.bruker.guess_udic(pdic, pdata, pdata=True)
        uc = fileiobase.uc_from_udic(udic, 0)
        _, last = uc.ppm_limits()
        p = pdic["proc2s"]
        expected = p["OFFSET"] - (p["SI"] - 1) * p["SW_p"] / (p["SI"] * p["SF"])
        assert np.isclose(last, expected, atol=1e-4)

    def test_cosy_direct_first_point(self):
        """COSY direct first point matches procs OFFSET."""
        pdic, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        udic = ng.bruker.guess_udic(pdic, pdata, pdata=True)
        uc = fileiobase.uc_from_udic(udic, 1)
        first, _ = uc.ppm_limits()
        assert np.isclose(first, pdic["procs"]["OFFSET"], atol=1e-4)

    def test_cosy_indirect_first_point(self):
        """COSY indirect first point matches proc2s OFFSET."""
        pdic, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        udic = ng.bruker.guess_udic(pdic, pdata, pdata=True)
        uc = fileiobase.uc_from_udic(udic, 0)
        first, _ = uc.ppm_limits()
        assert np.isclose(first, pdic["proc2s"]["OFFSET"], atol=1e-4)

    def test_1d_pdata_first_point(self):
        """1D processed first point matches procs OFFSET."""
        pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
        udic = ng.bruker.guess_udic(pdic, pdata, pdata=True)
        uc = fileiobase.uc_from_udic(udic, 0)
        first, _ = uc.ppm_limits()
        assert np.isclose(first, pdic["procs"]["OFFSET"], atol=1e-4)

    def test_raw_data_axis_unchanged(self):
        """Raw data axis uses acqus parameters (backward compat)."""
        dic, data = ng.bruker.read(HSQC_DIR)
        udic = ng.bruker.guess_udic(dic, data)
        uc = fileiobase.uc_from_udic(udic, 1)
        first, _ = uc.ppm_limits()
        # Raw axis uses O1/SFO1, not OFFSET
        expected = (dic["acqus"]["O1"] + dic["acqus"]["SW_h"] / 2) / \
                   dic["acqus"]["SFO1"]
        assert np.isclose(first, expected, atol=1e-4)

    def test_pdata_false_same_as_none(self):
        """pdata=False gives same result as pdata=None (backward compat)."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        u_none = ng.bruker.guess_udic(pdic, pdata, pdata=None)
        u_false = ng.bruker.guess_udic(pdic, pdata, pdata=False)
        uc_none = fileiobase.uc_from_udic(u_none, 1)
        uc_false = fileiobase.uc_from_udic(u_false, 1)
        assert np.allclose(uc_none.ppm_limits(), uc_false.ppm_limits())

    def test_strip_fake_with_pdata(self):
        """strip_fake=True combined with pdata=True does not crash."""
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        udic = ng.bruker.guess_udic(pdic, pdata, strip_fake=True, pdata=True)
        uc = fileiobase.uc_from_udic(udic, 1)
        first, last = uc.ppm_limits()
        assert np.isfinite(first)
        assert np.isfinite(last)
