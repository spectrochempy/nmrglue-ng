"""JEOL 1D storage and explicit quadrature normalization."""

from dataclasses import replace
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


def test_epicatechin_fid_legacy_presentation():
    path = _JDF_FIXTURES / "epicatechin_1h.jdf"
    stored = interop.read_jeol_fid(path)
    ordinary = interop.normalize_jeol_fid(stored, conjugation="none")
    assert ordinary.acquisition["carrier_offset_ppm"] == 5.0
    assert ordinary.acquisition["nucleus"] == "Proton"
    assert ordinary.encoding == ("complex",)
    with pytest.raises(ValueError, match="requires conjugated"):
        interop.normalize_jeol_fid(stored, conjugation="none", legacy_presentation=True)

    result = interop.normalize_jeol_fid(
        stored, conjugation="conjugate", legacy_presentation=True,
    )
    np.testing.assert_array_equal(result.data, jeol.read(path)[1])
    assert result.encoding == ("QSIM",)
    assert len(result.applied_operations) == 1
    assert result.applied_operations[0]["conjugation"] == "conjugate"
    display = result.acquisition["legacy_presentation"]
    assert display["fft_input_transform"] == "conjugate-input"
    assert display["scan_count"] == 64
    assert display["solvent"] == "DMSO-D6"
    assert display["pulse_program"] == "single_pulse_dec"
    assert display["acquisition_date"] == (2019, 8, 5)


@pytest.mark.parametrize("scaler, expected", [(20, 5e20), (308, None)])
def test_jeol_fid_scaled_integer_offset(tmp_path, scaler, expected):
    payload = bytearray((_JDF_FIXTURES / "epicatechin_1h.jdf").read_bytes())
    record = payload.index(b"X_OFFSET") - 36
    struct.pack_into("<h", payload, record + 4, scaler)
    struct.pack_into("<i", payload, record + 16, 5)
    struct.pack_into("<i", payload, record + 32, 1)
    path = tmp_path / "integer-offset.jdf"
    path.write_bytes(payload)
    stored = interop.read_jeol_fid(path)
    assert stored.metadata["parameters"]["x_offset"] == 5 * 10 ** scaler
    ordinary = interop.normalize_jeol_fid(stored, conjugation="none")
    assert ordinary.acquisition.get("carrier_offset_ppm") == expected
    if expected is None:
        with pytest.raises(ValueError, match="finite offset in ppm"):
            interop.normalize_jeol_fid(
                stored, conjugation="conjugate", legacy_presentation=True,
            )
    else:
        legacy = interop.normalize_jeol_fid(
            stored, conjugation="conjugate", legacy_presentation=True,
        )
        assert legacy.acquisition["carrier_offset_ppm"] == expected


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


@pytest.mark.parametrize(
    "experiment, nominal_y, y_count, y_dwell, y_increments, x_dwell, y_end",
    [
        ("cosy", 256, 256, 166.74e-6, (0, 1, 2, 3), 133.12e-6, 0.0425187),
        ("hsqc", 128, 32, 58.48e-6, (0, 2, 4, 7), 133.44e-6, 0.00707608),
        ("hmbc", 256, 64, 39.76e-6, (0, 1, 2, 4), 133.44e-6, 0.00982072),
    ],
)
def test_normalize_jeol_2d_reference(
    experiment, nominal_y, y_count, y_dwell, y_increments, x_dwell, y_end,
):
    path = _JDF_FIXTURES / f"epicatechin_{experiment}.jdf"
    stored = interop.read_jeol_2d_storage(path)
    normalized = interop.normalize_jeol_2d(stored, conjugation="conjugate")
    original_sign = interop.normalize_jeol_2d(stored, conjugation="none")
    _, legacy = jeol.read(path)

    assert normalized.normalization_state == "storage-normalized"
    assert normalized.physical_dimensions == ("F1", "F2")
    assert normalized.domains == ("time", "time")
    assert normalized.acquisition["nominal_shape"] == (nominal_y, legacy.shape[1])
    assert normalized.acquisition["dwell_time_s"] == pytest.approx((y_dwell, x_dwell))
    assert normalized.axes[0].values.size == y_count
    np.testing.assert_allclose(normalized.axes[0].values[:4], np.array(y_increments) * y_dwell)
    assert normalized.axes[0].values[-1] == pytest.approx(y_end)
    np.testing.assert_allclose(normalized.axes[1].values, np.arange(legacy.shape[1]) * x_dwell)
    assert normalized.axes[0].unit == normalized.axes[1].unit == "s"
    np.testing.assert_array_equal(original_sign.data, normalized.data.conj())
    if experiment == "cosy":
        assert normalized.channel_axis is None
        assert normalized.acquisition["sampling"] == ("regular", "regular")
        np.testing.assert_array_equal(normalized.data, legacy)
    else:
        assert normalized.channel_axis == 0
        assert normalized.branch_order == ("section-0/1", "section-2/3")
        assert normalized.acquisition["sampling"] == ("listed", "regular")
        np.testing.assert_array_equal(normalized.data[0], legacy[::2])
        np.testing.assert_array_equal(normalized.data[1], -legacy[1::2])


def test_jeol_cosy_public_presentation():
    path = _JDF_FIXTURES / "epicatechin_cosy.jdf"
    stored = interop.read(path)
    result = interop.normalize(stored, conjugation="conjugate", legacy_presentation=True)
    assert result.quadrature_mode == "f2-traces-stored-2d"
    assert result.encoding == ("unknown", "complex")
    assert result.branch_order == ("complex",)
    assert result.acquisition["carrier_offset_ppm"] == (5.0, 5.0)
    assert result.acquisition["spectral_width_hz"] == pytest.approx(
        (1 / 166.74e-6, 1 / 133.12e-6)
    )
    assert result.acquisition["legacy_presentation"]["pulse_program"] == "cosy.jxp"
    np.testing.assert_array_equal(result.data, jeol.read(path)[1])


def test_jeol_public_2d_presentation_requires_explicit_sign():
    stored = interop.read(_JDF_FIXTURES / "epicatechin_cosy.jdf")
    with pytest.raises(ValueError, match="requires conjugated traces"):
        interop.normalize(stored, conjugation="none", legacy_presentation=True)


@pytest.mark.parametrize("experiment", ["hsqc", "hmbc"])
def test_jeol_listed_public_presentation(experiment):
    path = _JDF_FIXTURES / f"epicatechin_{experiment}.jdf"
    stored = interop.read(path)
    branches = interop.normalize(stored, conjugation="conjugate")
    public = interop.normalize(stored, conjugation="conjugate", legacy_presentation=True)
    assert public.quadrature_mode == "f2-traces-stored-2d"
    assert public.channel_axis is None
    assert public.acquisition["sampling"] == ("listed-paired", "regular")
    assert public.acquisition["trace_branch_order"] == branches.branch_order
    assert public.acquisition["nominal_shape"] == branches.acquisition["nominal_shape"]
    assert public.applied_operations[1]["sign"] == "negate-second"
    np.testing.assert_array_equal(public.axes[0].values, np.repeat(branches.axes[0].values, 2))
    np.testing.assert_array_equal(public.data, jeol.read(path)[1])
    np.testing.assert_array_equal(public.data[::2], branches.data[0])
    np.testing.assert_array_equal(public.data[1::2], -branches.data[1])


@pytest.mark.parametrize(
    "index, time_ms",
    [(1, float("nan")), (1, 0.0), (1, 0.1), (1, 20.0),
     (31, (128 - 5e-8) * 0.05848)],
)
def test_normalize_jeol_rejects_invalid_nus_schedule(index, time_ms):
    stored = interop.read_jeol_2d_storage(_JDF_FIXTURES / "epicatechin_hsqc.jdf")
    raw = bytearray(stored.metadata["axis_lists_raw"]["y"])
    struct.pack_into(">d", raw, 8 * index, time_ms)
    metadata = {**stored.metadata, "axis_lists_raw": {"y": bytes(raw)}}
    with pytest.raises(ValueError, match="nominal NUS grid"):
        interop.normalize_jeol_2d(replace(stored, metadata=metadata), conjugation="none")


def _assert_uniform_jeol_2d(stored, sections, shape, dwell):
    ny, nx = shape
    # JDF gives the tiles in row-major order and the samples in row-major
    # order within each tile. Address scalar words without the reader helper.
    y, x = np.ogrid[:ny, :nx]
    index = ((y // 32 * (nx // 32) + x // 32) * 32 + y % 32) * 32 + x % 32

    original = interop.normalize(stored, conjugation="none")
    conjugated = interop.normalize(stored, conjugation="conjugate")
    assert original.quadrature_mode == "jeol-stored-section-pairs"
    assert original.channel_axis == 0
    assert original.branch_order == ("section-0/1", "section-2/3")
    assert original.dimensions == ("channels", "F1", "F2")
    assert original.domains == ("time", "time")
    assert original.data.shape == (2, ny, nx)
    assert original.acquisition["sampling"] == ("regular", "regular")
    assert original.acquisition["nominal_shape"] == (ny, nx)
    for k in range(2):
        np.testing.assert_array_equal(original.data[k].real, sections[2 * k, index])
        np.testing.assert_array_equal(original.data[k].imag, sections[2 * k + 1, index])
    np.testing.assert_array_equal(conjugated.data, original.data.conj())

    # Allow floating-point rounding when taking the reciprocal of a sweep.
    for axis, name, size, step in zip(original.axes, ("F1", "F2"), shape, dwell):
        assert axis.domain == "time" and axis.unit == "s"
        np.testing.assert_allclose(axis.values, np.arange(size) * step, rtol=0, atol=1e-15,
                                   err_msg=name)

    legacy = interop.normalize(stored, conjugation="conjugate", legacy_presentation=True)
    assert legacy.channel_axis is None
    assert legacy.encoding == ("unknown", "complex")
    assert legacy.quadrature_mode == "f2-traces-stored-2d"
    assert legacy.acquisition["sampling"] == ("regular-paired", "regular")
    assert legacy.acquisition["nominal_shape"] == (ny, nx)
    assert legacy.acquisition["trace_branch_order"] == original.branch_order
    np.testing.assert_array_equal(legacy.axes[0].values, np.repeat(original.axes[0].values, 2))
    np.testing.assert_array_equal(legacy.axes[1].values, original.axes[1].values)
    np.testing.assert_array_equal(legacy.data[::2], conjugated.data[0])
    np.testing.assert_array_equal(legacy.data[1::2], -conjugated.data[1])
    return legacy


def test_normalize_jeol_uniform_2d():
    path = _JDF_FIXTURES / "epicatechin_hsqc.jdf"
    stored = interop.read(path)
    metadata = stored.metadata
    header = metadata["header"]
    # Replace the listed axis with a synthetic contiguous 32-increment axis.
    regular = replace(stored, metadata={
        **metadata,
        "header": {
            **header,
            "units": [header["units"][0], ("none", 1, "second"), *header["units"][2:]],
            "data_axis_ranged": ["ranged", "ranged", *header["data_axis_ranged"][2:]],
            "data_axis_start": [0.0, 0.0, *header["data_axis_start"][2:]],
            "data_axis_stop": [
                header["data_axis_stop"][0], 31 * 58.48e-6, *header["data_axis_stop"][2:],
            ],
            "list_length": [0, 0, *header["list_length"][2:]],
            "list_start": [0, 0, *header["list_start"][2:]],
        },
        "axis_lists_raw": {},
    })
    sections = np.frombuffer(path.read_bytes(), "<f8", count=4 * 32 * 1024,
                             offset=20480).reshape(4, -1)
    _assert_uniform_jeol_2d(regular, sections, (32, 1024), (58.48e-6, 133.44e-6))


@pytest.mark.dataset
def test_normalize_jeol_rutin_uniform_hsqc():
    source = os.environ.get("JEOL_RUTIN_HSQC_JDF")
    if not source:
        pytest.skip("set JEOL_RUTIN_HSQC_JDF to the Rutin uniform HSQC reference")
    raw = Path(source).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "6918f30526488f2657f627af880ca62770d834b0939b2b8f9c00c83005889342"
    )
    sections = np.frombuffer(raw, "<f8", count=4 * 256 * 4096, offset=16384).reshape(4, -1)
    legacy = _assert_uniform_jeol_2d(interop.read(source), sections, (256, 4096),
                                    (58.48e-6, 181.76e-6))
    np.testing.assert_array_equal(legacy.data, jeol.read(source)[1])


@pytest.mark.parametrize("endian", ["<", ">"])
def test_legacy_parse_jeol_reads_last_parameter(endian):
    payload = _synthetic_jdf(endian)
    params = jeol.parse_jeol(payload)["parameters"]
    assert list(params["info"]) == ["x_points", "x_sweep", "x_scale", "x_freq"]
    assert params["x_freq"] == 400e6
    assert params["info"]["x_freq"]["units"][0] == ("none", 1, "hertz")

    buffer = jeol.IOBuffer(payload, conversion_table=jeol.ConversionTable)
    _, direct = jeol.read_parameters(buffer, 1360, "little_endian" if endian == "<" else "big_endian")
    assert list(direct["info"]) == ["x_points", "x_sweep", "x_scale"]


@pytest.mark.parametrize("variant", ["exclusive", "short-length", "overlaps-data", "short-buffer"])
def test_legacy_parse_jeol_preserves_previous_parameter_bound(variant):
    payload = _synthetic_jdf(">")
    if variant == "exclusive":
        struct.pack_into(">I", payload, 1372, 3 * 64)
    elif variant == "short-length":
        struct.pack_into(">I", payload, 1216, 16 + 3 * 64)
    elif variant == "overlaps-data":
        struct.pack_into(">I", payload, 1284, 1360 + 16 + 3 * 64)
    else:
        payload = payload[:1360 + 16 + 3 * 64]

    parsed = jeol.parse_jeol(payload)["parameters"]
    assert list(parsed["info"]) == ["x_points", "x_sweep", "x_scale"]
    assert "x_freq" not in parsed


@pytest.mark.parametrize("path", sorted(_JDF_FIXTURES.glob("*.jdf")), ids=lambda path: path.stem)
def test_legacy_parse_jeol_last_parameter_in_packaged_files(path):
    raw = path.read_bytes()
    start, length = struct.unpack_from(">II", raw, 1212)
    data_start, = struct.unpack_from(">I", raw, 1284)
    endian = "<" if raw[8] else ">"
    size, low, high, total = struct.unpack_from(endian + "IIII", raw, start)
    assert size == 64 and low == 0
    assert total == size * (high + 1)
    assert length == 16 + total
    assert start + length <= data_start
    last = start + 16 + size * high
    value, = struct.unpack_from(endian + "i", raw, last + 16)
    value_type, = struct.unpack_from(endian + "i", raw, last + 32)
    name = raw[last + 36:last + size].decode().strip().lower()
    assert name == ("x_scale" if raw[12] == 1 else "y_scale")
    assert value_type == 1 and value == 1

    params = jeol.parse_jeol(raw)["parameters"]
    assert params[name] == value
    assert params["info"][name]["value_type"] == "integer"
    assert params["info"][name]["value"] == value


@pytest.mark.parametrize("endian", ["<", ">"])
@pytest.mark.parametrize("invalid", ["type", "scaler"])
def test_legacy_read_jeol_ignores_undecodable_final_parameter(tmp_path, endian, invalid):
    payload = _synthetic_jdf(endian)
    last = 1360 + 16 + 3 * 64
    if invalid == "type":
        struct.pack_into(endian + "i", payload, last + 32, 5)
    else:
        struct.pack_into(endian + "h", payload, last + 4, 309)

    path = tmp_path / "fid.jdf"
    path.write_bytes(payload)
    metadata, data = jeol.read(path)
    assert list(metadata["parameters"]["info"]) == ["x_points", "x_sweep", "x_scale"]
    assert "x_freq" not in metadata["parameters"]
    np.testing.assert_array_equal(data, [1+1j, 2-4j, 3+6j, 4-8j, 5+10j])

    with pytest.raises(ValueError, match="parameter section could not be decoded"):
        interop.read_jeol_fid(path)


def test_jeol_float32_regular_storage_and_normalization(tmp_path):
    source = _JDF_FIXTURES / "epicatechin_cosy.jdf"
    raw = source.read_bytes()
    offset, length = struct.unpack_from(">IQ", raw, 1284)
    words = np.frombuffer(raw, "<f8", count=length // 8, offset=offset).astype("<f4")
    payload = bytearray(raw[:offset])
    payload[14] |= 0x40
    struct.pack_into(">Q", payload, 1288, words.nbytes)
    payload.extend(words.tobytes())
    path = tmp_path / "cosy-float32.jdf"
    path.write_bytes(payload)
    stored = interop.read(path)
    assert stored.data.dtype == np.dtype("<f4")
    np.testing.assert_array_equal(stored.data, words.reshape(2, -1))
    result = interop.normalize(stored, conjugation="conjugate", legacy_presentation=True)
    np.testing.assert_array_equal(result.data, jeol.read(path)[1])
    assert result.data.dtype == np.dtype("complex128")
    np.testing.assert_allclose(result.axes[0].values, np.arange(256) * 166.74e-6,
                               rtol=0, atol=1e-15)
    np.testing.assert_allclose(result.axes[1].values, np.arange(1280) * 133.12e-6,
                               rtol=0, atol=1e-15)
    with pytest.raises(ValueError, match="storage description"):
        interop.normalize(replace(stored, data=stored.data.astype("float64")), conjugation="none")
    struct.pack_into(">Q", payload, 1288, words.nbytes + 4)
    path.write_bytes(payload)
    with pytest.raises(ValueError, match="data length"):
        interop.read(path)


@pytest.mark.dataset
def test_jeol_luteolin_float32_cosy():
    source = os.environ.get("JEOL_LUTEOLIN_COSY_JDF")
    if not source:
        pytest.skip("set JEOL_LUTEOLIN_COSY_JDF to nmrXiv D1155")
    raw = Path(source).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "2cceb9c5e19ef6569c113cd6b24ca913b628ccd8dc6eb582b69dee084b6d7dfa"
    )
    y, x = np.ogrid[:512, :5120]
    index = ((y // 32 * (5120 // 32) + x // 32) * 32 + y % 32) * 32 + x % 32
    words = np.frombuffer(raw, "<f4", offset=16384, count=2 * index.size).reshape(2, -1)
    stored = interop.read(source)
    assert stored.data.dtype == np.dtype("<f4")
    np.testing.assert_array_equal(stored.data, words)
    normalized = interop.normalize(stored, conjugation="none")
    assert normalized.quadrature_mode == "jeol-stored-section-pairs"
    assert normalized.branch_order == ("section-0/1",)
    assert normalized.channel_axis is None
    np.testing.assert_array_equal(normalized.data.real, words[0, index])
    np.testing.assert_array_equal(normalized.data.imag, words[1, index])
    np.testing.assert_allclose(normalized.axes[0].values, np.arange(512) * 227.38e-6,
                               rtol=0, atol=1e-15)
    np.testing.assert_allclose(normalized.axes[1].values, np.arange(5120) * 181.76e-6,
                               rtol=0, atol=1e-15)
    legacy = interop.normalize(stored, conjugation="conjugate", legacy_presentation=True)
    assert legacy.encoding == ("unknown", "complex")
    np.testing.assert_array_equal(legacy.data, jeol.read(source)[1])
