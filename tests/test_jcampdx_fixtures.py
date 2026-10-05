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
JDX_PINENE_COSY = os.path.join(DATA_DIR, "betapinene_cosy_400mhz.jdx")

# Reference values decoded independently from the JCAMP-DX SQZ/DIF data.
# Intermediate references at index 50000 distinguish correct decoding from
# truncation or sign errors.
REFERENCES = {
    "epic_1h": {
        "size": 104858,
        0: -0.00016932092497646685,
        1: -0.0001770019275771338,
        50000: -0.00017971286967148682,
        -1: -0.000156669861869486,
    },
    "epic_13c": {
        "size": 104858,
        0: 1.5481548475971462e-06,
        1: 2.4166319572248136e-06,
        50000: -1.4348752246022332e-06,
        -1: -2.1523128369033497e-06,
    },
    "pinene_1h": {
        "size": 65536,
        0: 0.03146649637602431,
        1: 0.03175891230194292,
        50000: 0.04514223830268161,
        -1: 0.03105541891495032,
    },
    "caffeic_13c": {
        "size": 52430,
        0: -1.8542965080818778e-06,
        1: -3.1787940138546475e-06,
        25000: -9.933731293295773e-07,
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
        """All declared reference points match decoded values."""
        path = dict(zip(ALL_IDS, ALL_JDX))[fid]
        dic, data = ng.jcampdx.read(path)
        refs = REFERENCES[fid]
        for idx in refs:
            if idx == "size":
                continue
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


class TestJCAMPDX2D:
    """Tests for 2D JCAMP-DX NTUPLES data (nD NMR SPECTRUM)."""

    def test_read_nd_show_all_data(self):
        """2D JCAMP-DX reads all pages with show_all_data=True."""
        dic, data = ng.jcampdx.read(JDX_PINENE_COSY, show_all_data=True)
        assert isinstance(data, dict)
        assert "real" in data
        assert "imaginary" in data
        assert len(data["real"]) == 128
        assert len(data["imaginary"]) == 0

    def test_read_nd_pages_shape(self):
        """Each page has the correct shape."""
        dic, data = ng.jcampdx.read(JDX_PINENE_COSY, show_all_data=True)
        for page in data["real"]:
            assert page.shape == (3278,)
            assert page.dtype == np.float64

    def test_read_nd_reference_points(self):
        """First and last points of first and last pages match references."""
        dic, data = ng.jcampdx.read(JDX_PINENE_COSY, show_all_data=True)
        assert np.isclose(data["real"][0][0], 6.70497e-07, rtol=1e-5)
        assert np.isclose(data["real"][0][-1], 1.18323e-06, rtol=1e-5)
        assert np.isclose(data["real"][-1][0], 9.031989e-07, rtol=1e-5)

    def test_read_nd_data_finite(self):
        """All page data values are finite."""
        dic, data = ng.jcampdx.read(JDX_PINENE_COSY, show_all_data=True)
        for page in data["real"]:
            assert np.all(np.isfinite(page))

    def test_read_nd_default_returns_first(self):
        """Default read returns only the first real page."""
        dic, data = ng.jcampdx.read(JDX_PINENE_COSY, show_all_data=False)
        assert isinstance(data, np.ndarray)
        assert data.shape == (3278,)
        assert np.isclose(data[0], 6.70497e-07, rtol=1e-5)


class TestJCAMPDXSynthetic:
    """Synthetic JCAMP-DX tests adapted from upstream jjhelmus/nmrglue#260."""

    # NTUPLES data whose dependent variable is declared as Y (not R/I),
    # as written by JEOL/MestReNova and Bruker for 2D spectra.
    _NTUPLES_Y_TEMPLATE = (
        "##TITLE=Test NTUPLES with Y symbol\n"
        "##JCAMPDX=6.0\n"
        "##DATATYPE=NMR SPECTRUM\n"
        "##DATA CLASS=NTUPLES\n"
        "##NUM DIM=2\n"
        "##NTUPLES=NMR SPECTRUM\n"
        "##VAR_NAME=FREQUENCY1, FREQUENCY2, SPECTRUM\n"
        "##SYMBOL=F1, F2, Y\n"
        "##VAR_TYPE=INDEPENDENT, INDEPENDENT, DEPENDENT\n"
        "##VAR_FORM=AFFN, AFFN, ASDF\n"
        "%s"
        "##PAGE=F1=1\n"
        "##DATA TABLE=(F2++(Y..Y)), PROFILE\n"
        "1.0 10 20\n"
        "##PAGE=F1=2\n"
        "##DATA TABLE=(F2++(Y..Y)), PROFILE\n"
        "1.0 30 40\n"
        "##END=\n"
    )

    @staticmethod
    def _write_jcamp(content):
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".jdx")
        with open(fd, "w") as f:
            f.write(content)
        return path

    def test_ntuples_symbol_factor(self):
        """NTUPLES FACTOR is picked by the table's own dependent symbol."""
        path = self._write_jcamp(self._NTUPLES_Y_TEMPLATE % "##FACTOR=1, 1, 2.0\n")
        try:
            _, data_all = ng.jcampdx.read(path, show_all_data=True)
            assert isinstance(data_all, dict)
            assert len(data_all["real"]) == 2
            assert data_all["imaginary"] == []
            assert np.allclose(data_all["real"][0], [20.0, 40.0])
            assert np.allclose(data_all["real"][1], [60.0, 80.0])
            _, data = ng.jcampdx.read(path, show_all_data=False)
            assert np.allclose(data, [20.0, 40.0])
        finally:
            import os
            os.remove(path)

    def test_ntuples_symbol_factor_missing(self):
        """NTUPLES data is left unscaled with a warning if FACTOR is absent."""
        path = self._write_jcamp(self._NTUPLES_Y_TEMPLATE % "##FACTOR=1, 1\n")
        try:
            import pytest as _pytest
            with _pytest.warns(UserWarning, match="no FACTOR found for symbol Y"):
                _, data_all = ng.jcampdx.read(path, show_all_data=True)
            assert np.allclose(data_all["real"][0], [10.0, 20.0])
            assert np.allclose(data_all["real"][1], [30.0, 40.0])
        finally:
            import os
            os.remove(path)

    def test_read_nd_spectrum(self):
        """nD NMR SPECTRUM sections are found and scaled."""
        content = (
            "##TITLE=Test nD NTUPLES\n"
            "##JCAMPDX=6.0\n"
            "##DATATYPE=nD NMR SPECTRUM\n"
            "##DATA CLASS=NTUPLES\n"
            "##NUM DIM=2\n"
            "##.OBSERVE FREQUENCY=100.0\n"
            "##.OBSERVE NUCLEUS=^1H\n"
            "##NTUPLES=nD NMR SPECTRUM\n"
            "##VAR_NAME=FREQUENCY1, FREQUENCY2, SPECTRUM\n"
            "##SYMBOL=F1, F2, Y\n"
            "##VAR_TYPE=INDEPENDENT, INDEPENDENT, DEPENDENT\n"
            "##VAR_FORM=AFFN, AFFN, ASDF\n"
            "##UNITS=HZ, HZ, ARBITRARY UNITS\n"
            "##FIRST=500, 400, 10\n"
            "##LAST=100, 200, 40\n"
            "##FACTOR=1, 1, 2.0\n"
            "##PAGE=F1=500\n"
            "##DATA TABLE=(F2++(Y..Y)), PROFILE\n"
            "1.0 10 20\n"
            "##PAGE=F1=100\n"
            "##DATA TABLE=(F2++(Y..Y)), PROFILE\n"
            "1.0 30 40\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            import pytest as _pytest
            dic, data_all = ng.jcampdx.read(path, show_all_data=True)
            assert len(data_all["real"]) == 2
            assert np.allclose(data_all["real"][0], [20.0, 40.0])
            assert np.allclose(data_all["real"][1], [60.0, 80.0])
            assert dic["DATATYPE"][0] == "nD NMR SPECTRUM"
            with _pytest.warns(UserWarning, match="direct dimension only"):
                udic = ng.jcampdx.guess_udic(dic, data_all)
            assert udic[0]["size"] == 2
            assert udic[0]["sw"] == 200.0
            assert udic[0]["obs"] == 100.0
            assert udic[0]["label"] == "1H"
        finally:
            import os
            os.remove(path)

    def test_prefers_1d_over_nd(self):
        """A 1D section wins over an nD one in the same file."""
        nd_section = (
            "##TITLE=The nD part\n"
            "##JCAMPDX=6.0\n"
            "##DATATYPE=nD NMR SPECTRUM\n"
            "##DATA CLASS=NTUPLES\n"
            "##NUM DIM=2\n"
            "##NTUPLES=nD NMR SPECTRUM\n"
            "##VAR_NAME=FREQUENCY1, FREQUENCY2, SPECTRUM\n"
            "##SYMBOL=F1, F2, Y\n"
            "##VAR_TYPE=INDEPENDENT, INDEPENDENT, DEPENDENT\n"
            "##VAR_FORM=AFFN, AFFN, ASDF\n"
            "##FACTOR=1, 1, 2.0\n"
            "##PAGE=F1=1\n"
            "##DATA TABLE=(F2++(Y..Y)), PROFILE\n"
            "1.0 10 20\n"
            "##END=\n"
        )
        content = (
            "##TITLE=Both\n"
            "##JCAMPDX=6.0\n"
            "##DATATYPE=LINK\n"
            "##BLOCKS=2\n"
            + nd_section +
            "##TITLE=The 1D part\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##DATA CLASS=XYDATA\n"
            "##FIRSTX=1\n"
            "##LASTX=2\n"
            "##XUNITS=HZ\n"
            "##YFACTOR=1\n"
            "##XYDATA=(X++(Y..Y))\n"
            "1.0 7 8\n"
            "##END=\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data is not None
            assert np.allclose(data, [7.0, 8.0])
            assert dic["DATATYPE"][0] == "NMR SPECTRUM"
            assert "_datatype_NDNMRSPECTRUM" in dic
        finally:
            import os
            os.remove(path)

    def test_affn_commas_not_xy_pairs(self):
        """AFFN data with commas is not misread as XY pairs.

        Regression for: (X++(Y..Y)) data with comma-separated values
        must be parsed as AFFN, not as coordinate pairs.
        """
        content = (
            "##TITLE=Test AFFN Commas\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##DATA CLASS=XYDATA\n"
            "##XYDATA=(X++(Y..Y))\n"
            "0,10,20,30\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data is not None
            assert np.allclose(data, [10.0, 20.0, 30.0])
        finally:
            import os
            os.remove(path)

    def test_ntuples_commas_not_xy_pairs(self):
        """NTUPLES data with commas is not misread as XY pairs."""
        content = (
            "##TITLE=Test NTUPLES Commas\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##DATA CLASS=NTUPLES\n"
            "##SYMBOL=X,R\n"
            "##FACTOR=1,2\n"
            "##DATA TABLE=(X++(R..R)), PROFILE\n"
            "0,10,20,30\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data is not None
            assert np.allclose(data, [20.0, 40.0, 60.0])
        finally:
            import os
            os.remove(path)

    def test_leading_zero_decimals(self):
        """Decimals without leading zero are handled in XY pairs."""
        content = (
            "##TITLE=Test Leading Zero\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##XYPOINTS=(XY..XY)\n"
            "-.5, 2\n"
            "1, .5\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data is not None
            assert data.shape == (1, 2, 2)
            assert np.allclose(data[0], [[-0.5, 2.0], [1.0, 0.5]])
        finally:
            import os
            os.remove(path)

    def test_xy_header_european_decimals(self):
        """European decimals with (XY..XY) header are handled.

        Commas in "(XY..XY)" data with European decimal values and
        semicolon row separators need disambiguation between decimal
        separators and X/Y delimiters.
        """
        content = (
            "##TITLE=Test XY European\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##XYPOINTS=(XY..XY)\n"
            "1,0, 10,5; 2,0, 20,5\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data is not None
            # Semicolon-separated rows with European decimals should be
            # parsed as two XY pairs after comma-to-dot conversion
            assert data.shape == (1, 2, 2)
            assert np.allclose(data[0], [[1.0, 10.5], [2.0, 20.5]])
        finally:
            import os
            os.remove(path)


class TestJCAMPDXXYFormats:
    """Tests for JCAMP-DX coordinate list and extended formats.

    Adapted from upstream jjhelmus/nmrglue#262.
    """

    @staticmethod
    def _write_jcamp(content):
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".jdx")
        with open(fd, "w") as f:
            f.write(content)
        return path

    def test_xy_coordinate_format(self):
        """(XY..XY) coordinate list format is parsed."""
        content = (
            "##TITLE=Test XY\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##DATA CLASS=XYDATA\n"
            "##XYDATA=(X..XY)\n"
            "1.0, 10.0; 2.0, 20.0; 3.0, 30.0\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data.shape == (1, 3, 2)
            assert np.allclose(data[0], [[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]])
        finally:
            import os
            os.remove(path)

    def test_peakttable(self):
        """PEAKTABLE blocks are parsed."""
        content = (
            "##TITLE=Test PEAKTABLE\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##PEAKTABLE=(XY..XY)\n"
            "1.0, 100.0\n"
            "2.0, 200.0\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data.shape == (1, 2, 2)
            assert np.allclose(data[0], [[1.0, 100.0], [2.0, 200.0]])
        finally:
            import os
            os.remove(path)

    def test_xypoints(self):
        """XYPOINTS blocks are parsed."""
        content = (
            "##TITLE=Test XYPOINTS\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##XYPOINTS=(XY..XY)\n"
            "1.5, 150.0\n"
            "2.5, 250.0\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data.shape == (1, 2, 2)
            assert np.allclose(data[0], [[1.5, 150.0], [2.5, 250.0]])
        finally:
            import os
            os.remove(path)

    def test_comma_decimal_separator(self):
        """Comma decimal separators are handled."""
        content = (
            "##TITLE=Test Comma\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##DATA CLASS=XYDATA\n"
            "##XYDATA=(X..XY)\n"
            "1,0, 10,5; 2,0, 20,5\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data.shape == (1, 2, 2)
            assert np.allclose(data[0], [[1.0, 10.5], [2.0, 20.5]])
        finally:
            import os
            os.remove(path)

    def test_scientific_notation(self):
        """Scientific notation in XY pairs is handled."""
        content = (
            "##TITLE=Test Scientific\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##XYPOINTS=(XY..XY)\n"
            "1.5e3, 2.0E-1\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data.shape == (1, 1, 2)
            assert np.allclose(data[0], [[1500.0, 0.2]])
        finally:
            import os
            os.remove(path)

    def test_xy_pairs_indented_and_signed(self):
        """(XY..XY) pairs with leading whitespace or signs."""
        cases = [
            (" 199.9, 1097735\n 199.95, 1097736\n",
             [[199.9, 1097735.0], [199.95, 1097736.0]]),
            (" 27, 1248 28, 2067\n 29, 5538\n",
             [[27.0, 1248.0], [28.0, 2067.0], [29.0, 5538.0]]),
            ("-1.5, 20\n-1.4, -21\n", [[-1.5, 20.0], [-1.4, -21.0]]),
        ]
        for lines, expected in cases:
            content = (
                "##TITLE=Test\n##JCAMPDX=5.0\n"
                "##DATATYPE=NMR SPECTRUM\n##DATA CLASS=XYDATA\n"
                "##XYDATA=(XY..XY)\n" + lines + "##END=\n"
            )
            path = self._write_jcamp(content)
            try:
                dic, data = ng.jcampdx.read(path)
                assert data.shape == (1, len(expected), 2)
                assert np.allclose(data[0], expected)
            finally:
                import os
                os.remove(path)

    def test_empty_table(self):
        """A table with no values gives no data, not an error."""
        content = (
            "##TITLE=Test\n##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n##DATA CLASS=PEAKTABLE\n"
            "##NPOINTS=0\n##PEAKTABLE=(XY..XY)\n##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data is None
        finally:
            import os
            os.remove(path)

    def test_xy_pairs_factors(self):
        """XFACTOR scales X and YFACTOR scales Y of (XY..XY) pairs."""
        content = (
            "##TITLE=Test\n##JCAMPDX=5.0\n##DATATYPE=NMR SPECTRUM\n"
            "##XFACTOR=10\n##YFACTOR=2\n"
            "##XYDATA=(XY..XY)\n1, 5\n2, 6\n##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert np.allclose(data[0], [[10.0, 10.0], [20.0, 12.0]])
        finally:
            import os
            os.remove(path)

    def test_compact_integer_pairs(self):
        """Compact integer coordinate pairs preserve comma delimiters.

        Regression for: comma-to-dot normalization must not rewrite the
        X/Y separator in (XY..XY) data like "15,420 16,1201".
        """
        content = (
            "##TITLE=Test Compact\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##DATA CLASS=XYDATA\n"
            "##XYDATA=(XY..XY)\n"
            "15,420 16,1201\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data is not None
            assert data.shape == (1, 2, 2)
            assert np.allclose(data[0], [[15.0, 420.0], [16.0, 1201.0]])
        finally:
            import os
            os.remove(path)

    def test_compact_pairs_peakttable(self):
        """Compact integer pairs in PEAKTABLE also preserve delimiters."""
        content = (
            "##TITLE=Test Compact PEAKTABLE\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##PEAKTABLE=(XY..XY)\n"
            "15,420 16,1201\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data is not None
            assert data.shape == (1, 2, 2)
            assert np.allclose(data[0], [[15.0, 420.0], [16.0, 1201.0]])
        finally:
            import os
            os.remove(path)

    def test_compact_pairs_semicolon(self):
        """Compact XY pairs separated by semicolons preserve delimiters.

        Regression for: comma-to-dot fallback must not destroy valid
        coordinate pairs like "15,420; 16,1201".
        """
        content = (
            "##TITLE=Test Compact Semicolon\n"
            "##JCAMPDX=5.0\n"
            "##DATATYPE=NMR SPECTRUM\n"
            "##XYPOINTS=(XY..XY)\n"
            "15,420; 16,1201\n"
            "##END=\n"
        )
        path = self._write_jcamp(content)
        try:
            dic, data = ng.jcampdx.read(path)
            assert data is not None
            assert data.shape == (1, 2, 2)
            assert np.allclose(data[0], [[15.0, 420.0], [16.0, 1201.0]])
        finally:
            import os
            os.remove(path)
