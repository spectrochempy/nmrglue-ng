"""Qualification of the regular real 1D JCAMP-DX spectrum profile."""

from dataclasses import replace
import hashlib
import os
from pathlib import Path

import numpy as np
import pytest

from nmrglue import interop, jcampdx


EPICATECHIN = (
    Path(__file__).parents[1] / "fixtures/fileio/data/jcampdx/epicatechin_1h.jdx"
)


def test_epicatechin_1h_spectrum():
    read = interop.read_jcampdx_1d(EPICATECHIN)
    normalized = interop.normalize_jcampdx_1d(read)
    _, historical = jcampdx.read(EPICATECHIN)
    axis = normalized.axes[0]

    assert normalized.dimensions == ("F2",)
    assert normalized.data.shape == (104858,)
    assert axis.domain == "frequency"
    assert axis.unit == "Hz"
    assert axis.direction == "decreasing"
    assert axis.reference.observation_frequency == pytest.approx(399.78219837825)
    assert axis.reference.offset is None
    assert axis.values[0] == 4996.512910356473
    assert axis.values[-1] == -998.6909265739829
    assert axis.values[1000] == pytest.approx(4996.512910356473 - 1000 * 0.05717504636724736)
    # The first SQZ ordinate a499 is -1499 before applying YFACTOR.
    assert normalized.data[0] == pytest.approx(-1499 * 1.1295592059804325e-7)
    np.testing.assert_array_equal(normalized.data, historical)
    assert not normalized.data.flags.writeable


SPECTRUM = """##TITLE=regular spectrum
##JCAMP-DX=5.00
##DATA TYPE=NMR SPECTRUM
##DATA CLASS=XYDATA
##XUNITS=PPM
##FIRSTX=1
##LASTX=2
##NPOINTS=3
##XFACTOR=0.5
##YFACTOR=2
##XYDATA=(X++(Y..Y))
2 3 4 5
##END=
"""


def test_jcampdx_endpoint_units_and_scaling(tmp_path):
    path = tmp_path / "spectrum.jdx"
    path.write_text(SPECTRUM)
    read = interop.read_jcampdx_1d(path)
    normalized = interop.normalize_jcampdx_1d(read)
    assert normalized.axes[0].unit == "ppm"
    assert normalized.axes[0].direction == "increasing"
    np.testing.assert_array_equal(normalized.axes[0].values, [1, 1.5, 2])
    np.testing.assert_array_equal(normalized.data, [6, 8, 10])
    with pytest.raises(ValueError, match="description disagrees"):
        interop.normalize_jcampdx_1d(replace(read, applied_corrections={"yfactor": 1.0}))


@pytest.mark.parametrize("rows", ["2CJ\n3DJ\n4E", "2CJT\n4E", "2E+0 CDE"])
def test_jcampdx_valid_compressed_rows(tmp_path, rows):
    path = tmp_path / "spectrum.jdx"
    path.write_text(SPECTRUM.replace("2 3 4 5", rows))
    result = interop.read_jcampdx_1d(path)
    np.testing.assert_array_equal(result.data, [6, 8, 10])


@pytest.mark.parametrize(
    "original, replacement, message",
    [
        ("NMR SPECTRUM", "NMR FID", "one NMR SPECTRUM"),
        ("NPOINTS=3", "NPOINTS=4", "matching NPOINTS"),
        ("LASTX=2", "LASTX=1", "distinct finite axis endpoints"),
        ("YFACTOR=2", "YFACTOR=invalid", "finite YFACTOR"),
        ("YFACTOR=2", "YFACTOR=", "finite YFACTOR"),
        ("2 3 4 5", "2 3\n100 4 5", "line abscissa"),
        ("2 3 4 5", "2 3 4 ? 5", "XYDATA token"),
        ("2 3 4 5", "2 3 4 BAD 5", "XYDATA token"),
        ("2 3 4 5", "2CJ\n3IJ\n4E", "DIF checkpoint"),
        ("2 3 4 5", "2CJ\n3DJ\n4I", "DIF checkpoint"),
        ("2 3 4 5", "2CJ\n?E", "XYDATA abscissa"),
        ("2 3 4 5", "? 3 4 5", "XYDATA abscissa"),
        ("2 3 4 5", "2JAJ", "initial absolute ordinate"),
        ("2 3 4 5", "2ABC\n5 6", "initial absolute ordinate"),
        ("2 3 4 5", "2CJJ", "terminal DIF checkpoint"),
        ("2 3 4 5", "2CJT000000000\n4E", "DUP count exceeds NPOINTS"),
        ("2 3 4 5", "2A000000000000J\n3A000000000002J\n4A000000000002", "DIF checkpoint"),
        ("(X++(Y..Y))", "(XY..XY)", "regular X"),
    ],
)
def test_jcampdx_rejects_outside_profile(tmp_path, original, replacement, message):
    path = tmp_path / "spectrum.jdx"
    path.write_text(SPECTRUM.replace(original, replacement))
    with pytest.raises(ValueError, match=message):
        interop.read_jcampdx_1d(path)


def test_jcampdx_spaced_header_still_checks_rows(tmp_path):
    path = tmp_path / "spectrum.jdx"
    path.write_text(
        SPECTRUM.replace("(X++(Y..Y))", "(X+ +(Y..Y))")
        .replace("2 3 4 5", "2 3\n100 4 5")
    )
    with pytest.raises(ValueError, match="line abscissa"):
        interop.read_jcampdx_1d(path)


def test_jcampdx_squeezed_e_prefix_without_delimiter(tmp_path):
    path = tmp_path / "spectrum.jdx"
    path.write_text(SPECTRUM.replace("2 3 4 5", "2E4\n3DE"))
    result = interop.read_jcampdx_1d(path)
    np.testing.assert_array_equal(result.data, [108, 8, 10])


FID = """##TITLE=complex FID
##JCAMP-DX=5.01
##DATA TYPE=NMR FID
##DATA CLASS=NTUPLES
##NTUPLES=NMR FID
##SYMBOL=X,R,I
##UNITS=SECONDS,ARBITRARY UNITS,ARBITRARY UNITS
##VAR_DIM=3,3,3
##FIRST=0.001,2,10
##LAST=0.003,6,14
##FACTOR=0.001,2,0.5
##PAGE=N=1
##DATA TABLE=(X++(I..I)),XYDATA
1 20 24 28
##PAGE=N=2
##DATA TABLE=(X++(R..R)),XYDATA
1 1 2 3
##END NTUPLES=NMR FID
##END=
"""


def test_jcampdx_fid_scaling_and_sign(tmp_path):
    path = tmp_path / "fid.dx"
    path.write_text(FID)
    result = interop.read_jcampdx_fid(path)
    native = interop.normalize_jcampdx_fid(result, conjugation="none")
    conjugated = interop.normalize_jcampdx_fid(result, conjugation="conjugate")
    expected = np.array([2 + 10j, 4 + 12j, 6 + 14j])
    np.testing.assert_array_equal(native.data, expected)
    np.testing.assert_array_equal(conjugated.data, expected.conj())
    np.testing.assert_array_equal(result.data, expected)
    np.testing.assert_array_equal(native.axes[0].values, [0.001, 0.002, 0.003])
    assert native.axes[0].unit == "s"
    assert native.acquisition["dwell_time_s"] == pytest.approx(0.001)
    assert native.acquisition["spectral_width_hz"] == pytest.approx(1000)
    assert conjugated.applied_operations[0]["conjugation"] == "conjugate"
    with pytest.raises(ValueError, match="conjugation"):
        interop.normalize_jcampdx_fid(result, conjugation="auto")


@pytest.mark.parametrize(
    "old, new, message",
    [
        ("3,3,3", "3,2,3", "VAR_DIM"),
        ("SECONDS,", "HZ,", "seconds"),
        ("PAGE=N=2", "PAGE=N=1", "PAGE records"),
        ("PAGE=N=2", "PAGE=F1=0.25", "PAGE records"),
        ("##UNITS=", "##VAR_TYPE=INDEPENDENT,INDEPENDENT,DEPENDENT\n##UNITS=", "VAR_TYPE"),
        ("I..I", "R..R", "one R table and one I table"),
        ("1 1 2 3", "1 1\n20 2 3", "line abscissa"),
        ("0.001,2,0.5", "0.001,2,0", "factors"),
        ("1 20 24 28", "1 20 24", "VAR_DIM"),
    ],
)
def test_jcampdx_fid_rejects_inconsistent_metadata_and_tables(tmp_path, old, new, message):
    path = tmp_path / "fid.dx"
    path.write_text(FID.replace(old, new))
    with pytest.raises(ValueError, match=message):
        interop.read_jcampdx_fid(path)


@pytest.mark.parametrize("end_before_second_page", [False, True])
def test_jcampdx_fid_rejects_detached_tables(tmp_path, end_before_second_page):
    path = tmp_path / "fid.dx"
    if end_before_second_page:
        contents = FID.replace("##END NTUPLES=NMR FID\n", "").replace(
            "##PAGE=N=2\n", "##END NTUPLES=NMR FID\n##PAGE=N=2\n",
        )
    else:
        contents = FID.replace("##PAGE=N=2\n", "").replace(
            "##PAGE=N=1\n", "##PAGE=N=1\n##PAGE=N=2\n",
        )
    path.write_text(contents)
    with pytest.raises(ValueError, match="one table per PAGE"):
        interop.read_jcampdx_fid(path)


@pytest.mark.dataset
@pytest.mark.parametrize(
    "variable, digest, points, last, first",
    [
        ("JCAMP_TESTFID_DX", "140919dcbdaea2d3a30ef9408a261a2df605dd75ee393a9a7e8fcf827ae093d9",
         16384, 0.6815317, 573 * 5.200415052 + 1232 * 5.044282357j),
        ("JCAMP_ASPIRIN_FID_DX", "9d15f7f4b81113d0619aa2eb559ed52f51615296ac716ac85bde816e564c6cfd",
         8192, 1.7102808, 0j),
    ],
)
def test_jcampdx_external_fid_reference(variable, digest, points, last, first):
    path = os.environ.get(variable)
    if not path:
        pytest.skip(f"set {variable} to the archived JCAMP-DX reference")
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    result = interop.read_jcampdx_fid(path)
    normalized = interop.normalize_jcampdx_fid(result, conjugation="none")
    _, historical = jcampdx.read(path, as_complex=True)
    np.testing.assert_array_equal(normalized.data, historical)
    assert normalized.data.shape == (points,)
    assert normalized.data[0] == pytest.approx(first)
    assert normalized.axes[0].values[0] == 0
    assert normalized.axes[0].values[-1] == last
    assert normalized.acquisition["dwell_time_s"] == pytest.approx(last / (points - 1))
