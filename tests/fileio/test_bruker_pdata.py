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
from numpy.testing import assert_array_equal
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


class TestBrukerProcessedSubmatrix:
    """Submatrix organization of the fixture processed data.

    Both 2D fixtures store full-width submatrices: `XDIM` equals `SI` in the
    direct and the indirect dimension, so `guess_shape_and_submatrix_shape`
    returns a submatrix shape identical to the data shape. These fixtures
    therefore verify the shape derivation and the (identity) submatrix
    reordering, but they do not exercise multi-submatrix tiling; the
    historical corpus data that did is no longer available.
    """

    def test_hsqc_submatrix_shape_is_identity(self):
        pdic, pdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        shape, submatrix = ng.bruker.guess_shape_and_submatrix_shape(pdic)
        assert shape == pdata.shape == (256, 4096)
        assert submatrix == (256, 4096)

    def test_cosy_submatrix_shape_is_identity(self):
        pdic, pdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
        shape, submatrix = ng.bruker.guess_shape_and_submatrix_shape(pdic)
        assert shape == pdata.shape == (512, 2048)
        assert submatrix == (512, 2048)


class TestBrukerProcessingFileFamilies:
    """Status (`procs`/`procNs`) and singular (`proc`/`procN`) files are distinct.

    The status files carry the applied `NC_proc`/`XDIM`; the singular files may
    hold editor-only parameters (`ABSF1`/`ABSF2`) and stale
    `NC_proc`/`XDIM`. Only the status files drive the default
    scaling, shape and axis; the singular files are available through explicit
    `procs_files` selection. See
    maintainer/reports/2026-10-bruker-processing-file-selection.md. These tests
    verify the current behavior and do not change default discovery.
    """

    def test_default_reads_status_files_only_1d(self):
        """1D default read uses only the status `procs` file."""
        pdic, _ = ng.bruker.read_pdata(PDATA_DIR)
        assert "procs" in pdic
        assert "proc" not in pdic
        assert pdic["procs"]["NC_proc"] == 13

    def test_default_reads_status_files_only_2d(self):
        """2D default read uses status files and ignores the singular `proc2`."""
        pdic, _ = ng.bruker.read_pdata(HSQC_PDATA_DIR)
        assert "procs" in pdic
        assert "proc2s" in pdic
        assert "proc2" not in pdic
        assert pdic["proc2s"]["XDIM"] == 256

    def test_explicit_selection_exposes_singular_1d(self):
        """Passing `proc` alongside `procs` exposes the editor parameters."""
        pdic, _ = ng.bruker.read_pdata(PDATA_DIR, procs_files=["proc", "procs"])
        assert pdic["proc"]["ABSF1"] == 10
        assert pdic["procs"]["ABSF1"] == 15.11424
        assert pdic["proc"]["NC_proc"] == 0
        assert pdic["procs"]["NC_proc"] == 13

    def test_explicit_selection_exposes_singular_2d(self):
        """Passing `proc2` alongside the status files exposes it unchanged."""
        pdic, _ = ng.bruker.read_pdata(
            HSQC_PDATA_DIR, procs_files=["proc2", "procs", "proc2s"])
        assert pdic["proc2"]["NC_proc"] == 0
        assert pdic["proc2"]["XDIM"] == 0
        assert pdic["proc2s"]["NC_proc"] == -12
        assert pdic["proc2s"]["XDIM"] == 256

    def test_singular_file_does_not_change_scaling_or_shape(self):
        """Adding the singular file leaves scaling, shape and axis unchanged."""
        default, ddata = ng.bruker.read_pdata(PDATA_DIR)
        explicit, edata = ng.bruker.read_pdata(
            PDATA_DIR, procs_files=["proc", "procs"])
        assert edata.shape == ddata.shape
        assert_array_equal(edata, ddata)
        assert (ng.bruker.guess_udic(explicit, edata)
                == ng.bruker.guess_udic(default, ddata))


# Capability tests that replace the historical external pdata datasets
# (`data/bruker_1d/pdata/1`, `data/bruker_2d/pdata/1`) with the versioned CC0
# fixtures. They are module-level so that their ids match the contract ids
# declared in `CRITICAL_TESTS` (see scripts/generate_testdata_manifest.py).


def test_pdata_1d_procs_metadata():
    """1D processed parameters and scaling match the procs file.

    Replaces the historical `test_read_pdata_1d`. NC_proc is 13, so the
    scaled array equals the unscaled int32 array multiplied by 2**13.
    """
    pdic, pdata = ng.bruker.read_pdata(PDATA_DIR)
    procs = pdic["procs"]
    assert procs["OFFSET"] == 15.11477
    assert procs["SF"] == 600.139999679976
    assert procs["FT_mod"] == 6
    assert procs["NC_proc"] == 13

    _, unscaled = ng.bruker.read_pdata(PDATA_DIR, scale_data=False)
    assert np.isclose(pdata[0], unscaled[0] * 2.0 ** procs["NC_proc"])
    assert np.isclose(pdata[-1], unscaled[-1] * 2.0 ** procs["NC_proc"])


def test_pdata_2d_procs_metadata():
    """2D processed parameters and scaling match procs and proc2s.

    Replaces the historical `test_read_pdata_2d`, using the HSQC and COSY
    fixtures. Both share NC_proc across dimensions.
    """
    hdic, hdata = ng.bruker.read_pdata(HSQC_PDATA_DIR)
    assert hdic["procs"]["OFFSET"] == 7.99684
    assert hdic["procs"]["SF"] == 600.150000007829
    assert hdic["proc2s"]["OFFSET"] == 189.3282
    assert hdic["proc2s"]["SF"] == 150.907895795745
    assert hdic["procs"]["NC_proc"] == -12
    _, hunscaled = ng.bruker.read_pdata(HSQC_PDATA_DIR, scale_data=False)
    assert np.isclose(hdata[0, 0], hunscaled[0, 0] * 2.0 ** hdic["procs"]["NC_proc"])

    cdic, cdata = ng.bruker.read_pdata(COSY_PDATA_DIR)
    assert cdic["procs"]["OFFSET"] == 16.00128
    assert cdic["proc2s"]["OFFSET"] == 16.00128
    assert cdic["procs"]["NC_proc"] == -4
    _, cunscaled = ng.bruker.read_pdata(COSY_PDATA_DIR, scale_data=False)
    assert np.isclose(cdata[0, 0], cunscaled[0, 0] * 2.0 ** cdic["procs"]["NC_proc"])


def _copy_bruker_dict(dic):
    """Return a shallow copy with fresh nested parameter sub-dicts.

    `write_pdata` updates `dic['procs']['PPARMOD']` in place; the copy keeps
    the dictionary read from the fixture unchanged for the comparison.
    """
    return {
        key: dict(value) if isinstance(value, dict) else value
        for key, value in dic.items()
    }


@pytest.mark.parametrize("pdata_folder", [False, 90])
def test_write_pdata_1d_roundtrip(tmp_path, pdata_folder):
    """1D processed data round-trips through write_pdata/read_pdata.

    Replaces the historical `test_write_pdata_1d`. The scaled array read
    from the fixture is written with `scale_data=True`, the documented mode
    for an array produced by `read_pdata`, and is recovered exactly; the
    procs metadata is preserved. Both the flat layout and the
    `pdata/<n>` layout are exercised.
    """
    dic, data = ng.bruker.read_pdata(PDATA_DIR, read_acqus=False)
    dic = _copy_bruker_dict(dic)
    ng.bruker.write_pdata(str(tmp_path), dic, data.copy(), scale_data=True,
                          write_procs=True, pdata_folder=pdata_folder)
    read_dir = str(tmp_path / "pdata" / str(pdata_folder)) if pdata_folder \
        else str(tmp_path)
    rdic, rdata = ng.bruker.read_pdata(read_dir, read_acqus=False)
    assert_array_equal(data, rdata)
    assert rdic["procs"] == dic["procs"]


@pytest.mark.parametrize("fixture", [HSQC_PDATA_DIR, COSY_PDATA_DIR])
@pytest.mark.parametrize("pdata_folder", [False, 90])
def test_write_pdata_2d_roundtrip(tmp_path, fixture, pdata_folder):
    """2D processed data round-trips through write_pdata/read_pdata.

    Replaces the historical `test_write_pdata_2d`. The real component is
    recovered exactly with `scale_data=True` and both procs and proc2s are
    preserved, for the flat and `pdata/<n>` layouts.
    """
    dic, data = ng.bruker.read_pdata(fixture, read_acqus=False)
    dic = _copy_bruker_dict(dic)
    ng.bruker.write_pdata(str(tmp_path), dic, data.copy(), scale_data=True,
                          write_procs=True, pdata_folder=pdata_folder)
    read_dir = str(tmp_path / "pdata" / str(pdata_folder)) if pdata_folder \
        else str(tmp_path)
    rdic, rdata = ng.bruker.read_pdata(read_dir, read_acqus=False)
    assert_array_equal(data, rdata)
    assert rdic["procs"] == dic["procs"]
    assert rdic["proc2s"] == dic["proc2s"]
