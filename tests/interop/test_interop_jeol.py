"""JEOL 1D storage and explicit quadrature normalization."""

import hashlib
import os
from pathlib import Path
import struct

import numpy as np
import pytest

from nmrglue import interop, jeol


def _synthetic_jdf(endian):
    header = bytearray(1360)
    header[:8] = b"JEOL.NMR"
    header[8:16] = bytes((int(endian == "<"), 1, 0, 2, 1, 128, 1, 25))
    header[24] = 3
    header[32:34] = bytes((1, 28))
    struct.pack_into(">8I", header, 176, 8, *([1] * 7))
    struct.pack_into(">I", header, 240, 4)
    struct.pack_into(">d", header, 336, 0.001)
    struct.pack_into(">d", header, 1064, 400.0)
    params = bytearray(struct.pack(endian + "4I", 64, 0, 3, 256))
    for name, value in ((b"x_points", 5.0), (b"x_sweep", 4000.0), (b"x_scale", 1.0), (b"x_freq", 400e6)):
        record = bytearray(64)
        if name in (b"x_sweep", b"x_freq"):
            record[6:8] = bytes((1, 13))
        struct.pack_into(endian + "d", record, 16, value)
        struct.pack_into(endian + "i", record, 32, 2)
        record[36:36 + len(name)] = name
        params.extend(record)
    struct.pack_into(">2I", header, 1212, len(header), len(params))
    struct.pack_into(">IQ", header, 1284, len(header) + len(params), 128)
    payload = struct.pack(endian + "16d", 1, 2, 3, 4, 5, 90, 91, 92,
                          -1, 4, -6, 8, -10, 93, 94, 95)
    return header + params + payload


@pytest.mark.parametrize("endian", ["<", ">"])
def test_jeol_fid_storage_and_normalization(tmp_path, endian):
    path = tmp_path / "fid.jdf"
    payload = _synthetic_jdf(endian)
    path.write_bytes(payload)
    stored = interop.read_jeol_fid(path)
    expected = np.array([1-1j, 2+4j, 3-6j, 4+8j, 5-10j])
    np.testing.assert_array_equal(stored.data[:5], expected)
    np.testing.assert_array_equal(stored.data[5:], [90+93j, 91+94j, 92+95j])
    normalized = interop.normalize_jeol_fid(stored, conjugation="none")
    np.testing.assert_array_equal(normalized.data, expected)
    np.testing.assert_array_equal(normalized.axes[0].values, [0, .00025, .0005, .00075, .001])
    assert normalized.axes[0].reference.observation_frequency == 400.0
    assert normalized.acquisition["trimmed_padding_points"] == 3
    conjugated = interop.normalize_jeol_fid(stored, conjugation="conjugate")
    np.testing.assert_array_equal(conjugated.data, expected.conj())
    assert conjugated.applied_operations[0]["conjugation"] == "conjugate"
    path.write_bytes(payload[:-1])
    with pytest.raises(ValueError, match="truncated"):
        interop.read_jeol_fid(path)


@pytest.mark.parametrize(
    "offset, replacement, message",
    [
        (172, b"\x10", "ranged time axis"),
        (1252, struct.pack(">I", 8), "ranged time axis"),
        (1216, struct.pack(">I", 16), "parameter section could not be decoded"),
        (1380, struct.pack(">h", 32767), "parameter section could not be decoded"),
    ],
)
def test_jeol_rejects_unsupported_storage(tmp_path, offset, replacement, message):
    path = tmp_path / "fid.jdf"
    payload = _synthetic_jdf(">")
    payload[offset:offset + len(replacement)] = replacement
    path.write_bytes(payload)
    with pytest.raises(ValueError, match=message):
        interop.read_jeol_fid(path)


@pytest.mark.parametrize(
    "offset, replacement, message",
    [
        (1451, bytes((28,)), "x_sweep in hertz"),
        (1579, bytes((28,)), "x_freq in hertz"),
        (1456, struct.pack(">i12xi", 4000, 4), "positive numeric x_sweep"),
        (1392, struct.pack(">i12xi", 5, 4), "positive numeric x_points"),
        (1382, bytes((1, 28)), "dimensionless x_points"),
        (1064, struct.pack(">d", 300.0), "base frequency disagrees"),
    ],
)
def test_jeol_rejects_inconsistent_calibration(tmp_path, offset, replacement, message):
    path = tmp_path / "fid.jdf"
    payload = _synthetic_jdf(">")
    payload[offset:offset + len(replacement)] = replacement
    path.write_bytes(payload)
    stored = interop.read_jeol_fid(path)
    with pytest.raises(ValueError, match=message):
        interop.normalize_jeol_fid(stored, conjugation="none")


def test_jeol_rejects_scaled_text(tmp_path):
    path = tmp_path / "fid.jdf"
    payload = _synthetic_jdf(">")
    struct.pack_into(">h", payload, 1508, 1)
    struct.pack_into(">16si", payload, 1520, b"0123456789abcdef", 0)
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="parameter section could not be decoded"):
        interop.read_jeol_fid(path)


def test_jeol_rejects_overflowing_scaled_integer(tmp_path):
    path = tmp_path / "fid.jdf"
    payload = _synthetic_jdf(">")
    struct.pack_into(">h", payload, 1380, 1000)
    struct.pack_into(">i12xi", payload, 1392, 5, 1)
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="parameter section could not be decoded"):
        interop.read_jeol_fid(path)


@pytest.mark.dataset
def test_zenodo_jeol_fid_reference():
    source = os.environ.get("JEOL_INTEROP_JDF")
    if not source:
        pytest.skip("set JEOL_INTEROP_JDF to the reference JDF")
    raw = Path(source).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "8709f7e15dbdbdd79882a1b05e89ad49037f588b6a0b4eda00491fd26989ed38"
    )
    real, imag = np.frombuffer(raw, dtype="<f8", count=2 * 353160,
                              offset=20480).reshape(2, 353160)
    stored = interop.read_jeol_fid(source)
    np.testing.assert_array_equal(stored.data.real, real)
    np.testing.assert_array_equal(stored.data.imag, imag)
    normalized = interop.normalize_jeol_fid(stored, conjugation="conjugate")
    np.testing.assert_array_equal(normalized.data, jeol.read(source)[1])
    assert normalized.data.size == 353155
    assert normalized.axes[0].label == "Fluorine19"
    assert normalized.axes[0].values[-1] == pytest.approx(2.98768284)
    assert normalized.axes[0].values[1] == pytest.approx(8.46e-6)


_JDF_FIXTURES = Path(__file__).parents[1] / "fixtures" / "fileio" / "data" / "jeol"


@pytest.mark.parametrize(
    "experiment, grid, count, data_offset, list_offset, second_time",
    [
        ("hsqc", (32, 1024), 4, 20480, 19488, 0.11696),
        ("cosy", (256, 1280), 2, 16384, None, None),
        ("hmbc", (64, 2048), 4, 20480, 19808, 0.03976),
    ],
)
def test_epicatechin_2d_storage(experiment, grid, count, data_offset, list_offset, second_time):
    path = _JDF_FIXTURES / f"epicatechin_{experiment}.jdf"
    original = path.read_bytes()
    ny, nx = grid
    words = np.frombuffer(original, "<f8", count=count * ny * nx, offset=data_offset)
    stored = interop.read_jeol_2d_storage(path)

    assert stored.format == "jeol-2d-storage"
    assert stored.domains == ("unknown", "unknown")
    assert not stored.applied_corrections
    assert stored.dimensions["grid_axis_order"] == ("y", "x")
    assert stored.dimensions["grid_shape"] == grid
    assert stored.dimensions["tile_shape"] == (32, 32)
    assert stored.dimensions["valid_index_ranges"] == {"x": (0, nx - 1), "y": (0, ny - 1)}
    np.testing.assert_array_equal(stored.data, words.reshape(count, ny * nx))
    assert not stored.data.flags.writeable
    for index, section in enumerate(stored.components):
        assert section.name == f"section-{index}"
        np.testing.assert_array_equal(section.data, stored.data[index])

    if list_offset is None:
        assert not stored.metadata["axis_lists_raw"]
    else:
        axis_list = stored.metadata["axis_lists_raw"]["y"]
        assert axis_list == original[list_offset:list_offset + ny * 8]
        assert struct.unpack_from(">d", axis_list)[0] == 0.0
        assert struct.unpack_from(">d", axis_list, 8)[0] == pytest.approx(second_time)

    # Independently undo the tile layout and reproduce the historical reader's signs.
    planes = words.reshape(count, ny // 32, nx // 32, 32, 32)
    planes = planes.transpose(0, 1, 3, 2, 4).reshape(count, ny, nx)
    expected = planes[0] - 1j * planes[1]
    if count == 4:
        expected = np.empty((ny * 2, nx), dtype=complex)
        expected[0::2] = planes[0] - 1j * planes[1]
        expected[1::2] = -planes[2] + 1j * planes[3]
    np.testing.assert_array_equal(jeol.read(path)[1], expected)
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "offset, value, message",
    [
        (176, 1023, "complete storage tiles"),
        (240, 1024, "offsets are outside"),
        (1224, 20480, "axis list overlaps"),
        (1256, 0, "axis list length disagrees"),
        (1256, 1, "axis list length disagrees"),
        (1252, 8, "axis lists overlap"),
    ],
)
def test_jeol_rejects_invalid_2d_geometry(tmp_path, offset, value, message):
    original = (_JDF_FIXTURES / "epicatechin_hsqc.jdf").read_bytes()
    path = tmp_path / "bad.jdf"
    payload = bytearray(original)
    struct.pack_into(">I", payload, offset, value)
    path.write_bytes(payload)
    with pytest.raises(ValueError, match=message):
        interop.read_jeol_2d_storage(path)
