"""Processed NMRPipe input: exact payload, last-point reference and guards."""

from dataclasses import replace
import numpy as np
import pytest
import nmrglue as ng


def write_spectrum(path, complex_data=True, endian="<", **changes):
    data = np.array([1, -2, 7, 0, 3, -5, 11, 9], dtype=np.float32)
    if complex_data:
        data = data + 1j * np.arange(8, dtype=np.float32)
    header = ng.pipe.create_empty_dic()
    header.update(FDDIMCOUNT=1., FDDIMORDER1=2., FDSIZE=8., FDF2FTFLAG=1.,
                  FDF2SW=2000., FDF2OBS=400., FDF2ORIG=-625., FDF2CAR=99.,
                  FDF2QUADFLAG=float(not complex_data), FDQUADFLAG=float(not complex_data))
    header.update(changes)
    words = np.concatenate((data.real, data.imag)) if complex_data else data
    path.write_bytes(ng.pipe.dic2fdata(header).astype(endian + "f4").tobytes()
                     + words.astype(endian + "f4").tobytes())
    return data


@pytest.mark.parametrize("complex_data", [False, True])
@pytest.mark.parametrize("endian", ["<", ">"])
def test_read_normalize_preserves_payload_axis_and_reference(tmp_path, complex_data, endian):
    path = tmp_path / "spectrum.ft1"
    expected = write_spectrum(path, complex_data, endian)
    before = path.read_bytes()
    raw = ng.interop.read_nmrpipe_1d(path)
    result = ng.interop.normalize_nmrpipe_1d(raw)
    np.testing.assert_array_equal(result.data, expected)
    np.testing.assert_array_equal(result.axes[0].values, 1125 - np.arange(8) * 250)
    assert result.axes[0].values[-1] == -625
    assert result.axes[0].reference.observation_frequency == 400
    assert result.axes[0].reference.source == "processing"
    assert np.iscomplexobj(result.data) == complex_data
    assert not result.data.flags.writeable
    assert result.quadrature_mode == ("complex-1d" if complex_data else "real-1d")
    np.testing.assert_array_equal(ng.pipe.make_uc(raw.metadata, raw.data).hz_scale(), result.axes[0].values)
    assert path.read_bytes() == before


@pytest.mark.parametrize("changes", [
    {"FDMAGIC": 1}, {"FDFLTORDER": np.nan}, {"FDFLTORDER": 1},
    {"FDDIMCOUNT": 2}, {"FDF2FTFLAG": 0}, {"FDTRANSPOSED": 1},
    {"FDDIMORDER1": 1}, {"FDF2SW": 0}, {"FDF2OBS": -1},
    {"FDF2ORIG": np.nan}, {"FDSIZE": 8.5}, {"FDSIZE": 1e30}, {"FDSIZE": 1},
    {"FDF2QUADFLAG": 2}, {"FDQUADFLAG": 1}, {"FDF2X1": 1}, {"FDF2XN": 8},
    {"FDF2ORIG": 1e30, "FDF2SW": 1e-20},
])
def test_reject_unqualified_or_incoherent_header(tmp_path, changes):
    path = tmp_path / "bad.ft1"
    write_spectrum(path, **changes)
    with pytest.raises(ValueError):
        ng.interop.read_nmrpipe_1d(path)


@pytest.mark.parametrize("delta", [-8, -1, 1, 8])
def test_reject_payload_size_mismatch(tmp_path, delta):
    path = tmp_path / "bad.ft1"
    write_spectrum(path)
    payload = path.read_bytes()
    path.write_bytes(payload[:delta] if delta < 0 else payload + bytes(delta))
    with pytest.raises(ValueError, match="payload size"):
        ng.interop.read_nmrpipe_1d(path)


def test_reject_incomplete_header_and_nonfinite_data(tmp_path):
    path = tmp_path / "short.ft1"
    path.write_bytes(bytes(100))
    with pytest.raises(ValueError, match="header"):
        ng.interop.read_nmrpipe_1d(path)
    write_spectrum(path)
    payload = bytearray(path.read_bytes())
    payload[2048:2052] = np.array([np.nan], dtype="<f4").tobytes()
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="finite spectrum"):
        ng.interop.read_nmrpipe_1d(path)


@pytest.mark.parametrize("mutation", ["axis", "domain", "components", "corrections", "data"])
def test_normalizer_rejects_mutated_description(tmp_path, mutation):
    path = tmp_path / "spectrum.ft1"
    write_spectrum(path)
    raw = ng.interop.read_nmrpipe_1d(path)
    kwargs = {
        "axis": {"axes": (replace(raw.axes[0], values=raw.axes[0].values + 1),)},
        "domain": {"domains": ("time",)},
        "components": {"components": ()},
        "corrections": {"applied_corrections": {"normalization": "scans"}},
        "data": {"data": raw.data.real},
    }[mutation]
    with pytest.raises(ValueError):
        ng.interop.normalize_nmrpipe_1d(replace(raw, **kwargs))


def test_legacy_zero_byte_order_marker_is_accepted(tmp_path):
    path = tmp_path / "legacy.ft1"
    expected = write_spectrum(path, FDFLTORDER=0)
    result = ng.interop.normalize_nmrpipe_1d(ng.interop.read_nmrpipe_1d(path))
    np.testing.assert_array_equal(result.data, expected)
