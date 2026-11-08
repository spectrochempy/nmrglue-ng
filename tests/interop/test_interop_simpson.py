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
