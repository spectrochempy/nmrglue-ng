"""SIMPSON 1D FID decoding and calibration."""

import os
from pathlib import Path

import numpy as np
import pytest

from nmrglue import interop, simpson


HEADER = "SIMP\nNP=2\nSW=8000\nTYPE=FID\n"
TEXT = HEADER + "DATA\n1 -2\n3 4\nEND\n"
BINARY = HEADER + 'FORMAT=BINARY\nDATA\n!!!1!1!!!QQ!!!Y1!!!1"1!!\nEND\n'


@pytest.mark.parametrize(
    "contents", [TEXT, BINARY, BINARY.replace("\nEND", "END")],
    ids=["text", "binary", "binary-inline-end"],
)
def test_simpson_fid_axis_and_sign(tmp_path, contents):
    path = tmp_path / "signal.fid"
    path.write_text(contents)
    result = interop.read_simpson_fid(path)
    normalized = interop.normalize_simpson_fid(result, conjugation="conjugate")
    np.testing.assert_array_equal(result.data, [1 - 2j, 3 + 4j])
    np.testing.assert_array_equal(normalized.data, [1 + 2j, 3 - 4j])
    np.testing.assert_array_equal(normalized.axes[0].values, [0, 0.000125])
    assert normalized.axes[0].unit == "s"
    assert normalized.acquisition == {"spectral_width_hz": 8000, "dwell_time_s": 0.000125}


@pytest.mark.parametrize(
    "contents, message",
    [
        (TEXT.replace("3 4\n", ""), "TEXT block disagrees with NP"),
        (TEXT.replace("3 4", "END 0"), "two ordinates"),
        (TEXT.replace("TYPE=FID", "TYPE=SPE"), "single-element 1D FID"),
        (TEXT.replace("SW=8000", "SW=0"), "positive SW"),
        (TEXT.replace("TYPE=FID", "TYPE=FID\nNI=1"), "single-element 1D FID"),
        (BINARY.replace("!!!QQ", "!!QQ"), "BINARY block disagrees with NP"),
        (BINARY.replace("!!!1", "END\n1", 1), "premature END"),
    ],
)
def test_simpson_fid_rejects_invalid_input(tmp_path, contents, message):
    path = tmp_path / "signal.fid"
    path.write_text(contents)
    with pytest.raises(ValueError, match=message):
        interop.read_simpson_fid(path)


@pytest.mark.dataset
@pytest.mark.parametrize("filename", ["1d_text.fid", "1d_bin.fid"])
def test_simpson_fid_reference(filename):
    directory = os.environ.get("SIMPSON_INTEROP_DATA")
    if not directory:
        pytest.skip("set SIMPSON_INTEROP_DATA to the simpson_1d corpus directory")
    directory = Path(directory)
    result = interop.read_simpson_fid(directory / filename)
    normalized = interop.normalize_simpson_fid(result, conjugation="none")
    _, historical = simpson.read(directory / filename)
    indexed, samples = simpson.read(directory / "1d_ftext.fid")
    assert normalized.data.shape == (4096,)
    np.testing.assert_array_equal(normalized.data, historical)
    np.testing.assert_allclose(normalized.data, samples, rtol=1e-5, atol=1e-7)
    np.testing.assert_allclose(normalized.axes[0].values, indexed["units"], rtol=1e-7, atol=0)
    assert normalized.axes[0].values[-1] == pytest.approx(0.102375)


@pytest.mark.parametrize("contents", [TEXT, BINARY], ids=["text", "binary"])
def test_simpson_spectrum_even_bins(tmp_path, contents):
    path = tmp_path / "signal.spe"
    path.write_text(contents.replace("TYPE=FID", "TYPE=SPE"))
    read = interop.read_simpson_spectrum(path)
    normalized = interop.normalize_simpson_spectrum(read)
    np.testing.assert_array_equal(normalized.data, [1 - 2j, 3 + 4j])
    np.testing.assert_array_equal(normalized.axes[0].values, [-4000, 0])
    assert normalized.axes[0].unit == "Hz"
    assert normalized.axes[0].direction == "increasing"
    assert normalized.acquisition == {"spectral_width_hz": 8000}
    with pytest.raises(ValueError, match="FID data"):
        interop.read_simpson_fid(path)


def test_simpson_spectrum_odd_bins(tmp_path):
    path = tmp_path / "odd.spe"
    path.write_text("SIMP\nNP=5\nSW=100\nTYPE=SPE\nDATA\n0 0\n1 0\n2 0\n3 0\n4 0\nEND\n")
    # Independent SIMPSON 4.2.1 fload/fsave -xreim result.
    read = interop.read_simpson_spectrum(path)
    np.testing.assert_allclose(read.axes[0].values, [-50, -30, -10, 10, 30])
    np.testing.assert_array_equal(read.data, [0, 1, 2, 3, 4])


def test_simpson_spectrum_reference_offset(tmp_path):
    path = tmp_path / "shifted.spe"
    path.write_text(TEXT.replace("TYPE=FID", "REF=25\nTYPE=SPE").replace("SW=8000", "SW=100"))
    normalized = interop.normalize_simpson_spectrum(interop.read_simpson_spectrum(path))
    # Independent SIMPSON 4.2.1 fload/fsave -xreim result with REF=25.
    np.testing.assert_array_equal(normalized.axes[0].values, [-25, 25])
    assert normalized.metadata["REF"] == "25"

    path.write_text(path.read_text().replace("REF=25", "REF=nan"))
    with pytest.raises(ValueError, match="finite REF"):
        interop.read_simpson_spectrum(path)


@pytest.mark.dataset
@pytest.mark.parametrize("filename", ["1d_text.spe", "1d_bin.spe"])
def test_simpson_spectrum_reference(filename):
    directory = os.environ.get("SIMPSON_INTEROP_DATA")
    if not directory:
        pytest.skip("set SIMPSON_INTEROP_DATA to the simpson_1d corpus directory")
    directory = Path(directory)
    normalized = interop.normalize_simpson_spectrum(interop.read_simpson_spectrum(directory / filename))
    indexed, samples = simpson.read(directory / "1d_ftext.spe")
    assert normalized.data.shape == (4096,)
    np.testing.assert_allclose(normalized.data, samples, rtol=1e-5, atol=1e-7)
    np.testing.assert_allclose(normalized.axes[0].values, indexed["units"], rtol=5e-6, atol=0)
    np.testing.assert_array_equal(normalized.axes[0].values[[0, 2048, -1]], [-20000, 0, 19990.234375])


@pytest.mark.parametrize("contents", [TEXT, BINARY], ids=["text", "binary"])
def test_simpson_fid_2d_axis_order_and_sign(tmp_path, contents):
    path = tmp_path / "signal.fid"
    path.write_text(contents.replace("NP=2", "NP=1\nNI=2\nSW1=4000"))
    read = interop.read_simpson_fid_2d(path)
    normalized = interop.normalize_simpson_fid_2d(read, conjugation="conjugate")
    assert normalized.dimensions == ("F1", "F2")
    assert normalized.encoding == ("unknown", "complex")
    np.testing.assert_array_equal(read.data, [[1 - 2j], [3 + 4j]])
    np.testing.assert_array_equal(normalized.data, [[1 + 2j], [3 - 4j]])
    np.testing.assert_array_equal(normalized.axes[0].values, [0, 0.00025])
    np.testing.assert_array_equal(normalized.axes[1].values, [0])
    assert normalized.acquisition["dwell_time_s"] == (0.00025, 0.000125)


@pytest.mark.parametrize(
    "changes, message",
    [
        (("SW1=4000", "SW1=nan"), "positive SW1"),
        (("NI=2\n", ""), "single-element 2D FID"),
        (("NI=2", "NI=2\nNELEM=2"), "single-element 2D FID"),
        (("NI=2", "NI=3"), "block disagrees"),
    ],
)
def test_simpson_fid_2d_rejects_inconsistent_header(tmp_path, changes, message):
    path = tmp_path / "signal.fid"
    path.write_text(TEXT.replace("NP=2", "NP=1\nNI=2\nSW1=4000").replace(*changes))
    with pytest.raises(ValueError, match=message):
        interop.read_simpson_fid_2d(path)


@pytest.mark.dataset
@pytest.mark.parametrize("filename", ["2d_text.fid", "2d.fid"])
def test_simpson_fid_2d_reference(filename):
    directory = os.environ.get("SIMPSON_INTEROP_2D_DATA")
    if not directory:
        pytest.skip("set SIMPSON_INTEROP_2D_DATA to the simpson_2d corpus directory")
    directory = Path(directory)
    read = interop.read_simpson_fid_2d(directory / filename)
    normalized = interop.normalize_simpson_fid_2d(read, conjugation="none")
    indexed, samples = simpson.read(directory / "2d_ftext.fid")
    assert normalized.data.shape == (48, 128)
    np.testing.assert_allclose(normalized.data, samples, rtol=1e-5, atol=1e-7)
    np.testing.assert_allclose(normalized.axes[0].values, indexed["units"].ni_unit[:, 0], rtol=5e-6)
    np.testing.assert_allclose(normalized.axes[1].values, indexed["units"].np_unit[0], rtol=5e-6)
    assert normalized.axes[0].values[-1] == pytest.approx(0.00092470697117)
    assert normalized.axes[1].values[-1] == pytest.approx(0.003175)


SPE_2D = (
    "SIMP\nNP=3\nNI=2\nSW=90\nSW1=80\nREF=-12.5\nREF1=15\nTYPE=SPE\nDATA\n"
    "0 0\n1 -1\n2 -2\n3 -3\n4 -4\n5 -5\nEND\n"
)


def test_simpson_spectrum_2d_reference_offsets_and_odd_bins(tmp_path):
    path = tmp_path / "shifted.spe"
    path.write_text(SPE_2D)
    normalized = interop.normalize_simpson_spectrum_2d(interop.read_simpson_spectrum_2d(path))
    # Independent SIMPSON 4.2.1 fload/fsave -xyreim on this input.
    np.testing.assert_allclose(normalized.axes[0].values, [-25, 15])
    np.testing.assert_allclose(normalized.axes[1].values, [-57.5, -27.5, 2.5])
    np.testing.assert_array_equal(normalized.data, [[0, 1 - 1j, 2 - 2j], [3 - 3j, 4 - 4j, 5 - 5j]])
    assert normalized.domains == ("frequency", "frequency")
    assert normalized.dimensions == ("F1", "F2")
    assert normalized.acquisition == {"spectral_width_hz": (80, 90)}


@pytest.mark.parametrize("key, value", [("REF", "-12.5"), ("REF1", "15")])
def test_simpson_spectrum_2d_rejects_invalid_reference(tmp_path, key, value):
    path = tmp_path / "shifted.spe"
    path.write_text(SPE_2D.replace(f"{key}={value}", f"{key}=nan"))
    with pytest.raises(ValueError, match=f"finite {key} in Hz"):
        interop.read_simpson_spectrum_2d(path)


@pytest.mark.dataset
@pytest.mark.parametrize("filename", ["2d_text.spe", "2d.spe"])
def test_simpson_spectrum_2d_corpus(filename):
    directory = os.environ.get("SIMPSON_INTEROP_2D_DATA")
    if not directory:
        pytest.skip("set SIMPSON_INTEROP_2D_DATA to the simpson_2d corpus directory")
    directory = Path(directory)
    normalized = interop.normalize_simpson_spectrum_2d(interop.read_simpson_spectrum_2d(directory / filename))
    indexed, samples = simpson.read(directory / "2d_ftext.spe")
    assert normalized.data.shape == (512, 256)
    np.testing.assert_allclose(normalized.data, samples, rtol=1e-5, atol=1e-7)
    np.testing.assert_allclose(normalized.axes[0].values, indexed["units"].ni_unit[:, 0], rtol=5e-6)
    np.testing.assert_allclose(normalized.axes[1].values, indexed["units"].np_unit[0], rtol=5e-6)
    assert normalized.axes[0].values[256] == normalized.axes[1].values[128] == 0
