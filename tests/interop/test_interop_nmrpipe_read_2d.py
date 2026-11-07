"""Neutral NMRPipe real frequency/frequency plane contract."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import nmrglue as ng


FIXTURES = Path(__file__).parents[1] / "fixtures" / "fileio" / "data"


@pytest.mark.parametrize("transposed", [False, True])
@pytest.mark.parametrize("endian", ["<", ">"])
def test_read_real_plane_in_file_order(tmp_path, transposed, endian):
    suffix = "_tp" if transposed else ""
    source = FIXTURES / f"nmrpipe_2d_freq{suffix}.ft2"
    path = tmp_path / "spectrum%.ft2"
    path.write_bytes(
        np.frombuffer(source.read_bytes(), dtype="<f4").astype(endian + "f4").tobytes()
    )
    raw = ng.interop.read_nmrpipe_2d(path)
    normalized = ng.interop.normalize_nmrpipe_2d(raw)
    f1 = np.array([22375, 12375])
    f2 = 27350 - np.arange(8) * 6250
    expected = np.tile([1, 2, 0, 0, 0, 0, 0, 0], (2, 1))
    order = ("F1", "F2")
    axes = (f1, f2)
    labels = ("C13", "H1")
    frequencies = (125, 500)
    if transposed:
        expected, order, axes = expected.T, order[::-1], axes[::-1]
        labels, frequencies = labels[::-1], frequencies[::-1]
    np.testing.assert_array_equal(normalized.data, expected)
    assert normalized.data.dtype == np.float32
    assert not normalized.data.flags.writeable
    assert normalized.dimensions == order
    assert normalized.domains == ("frequency", "frequency")
    for axis, values, label, observation in zip(
        normalized.axes, axes, labels, frequencies, strict=True
    ):
        np.testing.assert_array_equal(axis.values, values)
        assert axis.unit == "Hz"
        assert axis.label == label
        assert axis.reference.observation_frequency == observation
        assert axis.reference.observation_frequency_unit == "MHz"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("FDDIMCOUNT", 3),
        ("FDF1FTFLAG", 0),
        ("FDF1QUADFLAG", 0),
        ("FDTRANSPOSED", 1),
        ("FDF1FTSIZE", 3),
        ("FDF2XN", 7),
        ("FDF1OBS", 0),
        ("FDSPECNUM", 1e30),
        ("FDFLTORDER", 0),
    ],
)
def test_reject_unsupported_or_inconsistent_header(tmp_path, key, value):
    source = FIXTURES / "nmrpipe_2d_freq.ft2"
    path = tmp_path / "bad.ft2"
    payload = source.read_bytes()
    header = ng.pipe.fdata2dic(np.frombuffer(payload[:2048], dtype="<f4"))
    header[key] = value
    path.write_bytes(ng.pipe.dic2fdata(header).astype("<f4").tobytes() + payload[2048:])
    with pytest.raises(ValueError):
        ng.interop.read_nmrpipe_2d(path)


@pytest.mark.parametrize("change", ["short", "extra", "nonfinite"])
def test_reject_invalid_payload(tmp_path, change):
    payload = (FIXTURES / "nmrpipe_2d_freq.ft2").read_bytes()
    path = tmp_path / "bad.ft2"
    if change == "short":
        payload = payload[:-4]
    elif change == "extra":
        payload += b"\0"
    else:
        payload = payload[:-4] + np.array([np.nan], dtype="<f4").tobytes()
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="payload"):
        ng.interop.read_nmrpipe_2d(path)


def test_normalizer_rejects_mismatched_axis_order():
    raw = ng.interop.read_nmrpipe_2d(FIXTURES / "nmrpipe_2d_freq.ft2")
    with pytest.raises(ValueError, match="axes"):
        ng.interop.normalize_nmrpipe_2d(replace(raw, axes=raw.axes[::-1]))


def test_normalizer_rejects_retyped_samples():
    raw = ng.interop.read_nmrpipe_2d(FIXTURES / "nmrpipe_2d_freq.ft2")
    data = raw.data.astype(np.float64)
    changed = replace(raw, data=data, components=(ng.interop.Component("real", data),))
    with pytest.raises(ValueError, match="disagrees with its header"):
        ng.interop.normalize_nmrpipe_2d(changed)
