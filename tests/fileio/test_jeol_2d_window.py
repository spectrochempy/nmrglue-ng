"""JEOL 2D valid windows are expressed in grid points before interleaving."""

from pathlib import Path
import struct

import numpy as np
import pytest

from nmrglue import jeol


CASES = (
    (("real", "real"), 1),
    (("complex", "real"), 2),
    (("real_complex", "real_complex"), 2),
    (("complex", "complex"), 4),
)


@pytest.mark.parametrize("axis_types,count", CASES, ids=["rr", "cr", "rcrc", "cc"])
@pytest.mark.parametrize("y_start", [0, 3])
def test_2d_valid_window(axis_types, count, y_start):
    ny, nx = 64, 96
    y, x = np.indices((ny, nx))
    planes = np.stack([(-1)**i * (10000*i + 100*y + x) for i in range(count)])
    words = np.concatenate([
        plane[row:row+32, col:col+32].ravel()
        for plane in planes
        for row in range(0, ny, 32)
        for col in range(0, nx, 32)
    ])
    dic = {"header": {
        "data_format": "two_d",
        "data_points": [nx, ny],
        "data_axis_type": list(axis_types),
        "data_offset_start": [5, y_start],
        "data_offset_stop": [36, 34],
    }}
    data = jeol.truncate_data(dic, jeol.reorganize_2d(dic, words))
    expected = planes[:, y_start:35, 5:37]
    if count == 4:
        assert data.shape == (2 * (35 - y_start), 32)
        restored = np.stack([
            data[::2].real, -data[::2].imag, -data[1::2].real, data[1::2].imag,
        ])
    elif count == 2:
        assert data.shape == (35 - y_start, 32)
        restored = np.stack([data.real, -data.imag])
    else:
        assert data.shape == (35 - y_start, 32)
        restored = data[None]
    np.testing.assert_array_equal(restored, expected)


@pytest.mark.parametrize("experiment,rows_per_increment", [("cosy", 1), ("hsqc", 2), ("hmbc", 2)])
def test_read_2d_valid_window(tmp_path, experiment, rows_per_increment):
    fixtures = Path(__file__).parents[1] / "fixtures/fileio/data/jeol"
    source = fixtures / f"epicatechin_{experiment}.jdf"
    _, original = jeol.read(source)
    contents = bytearray(source.read_bytes())
    struct.pack_into(">II", contents, 208, 19, 3)
    struct.pack_into(">II", contents, 240, 100, 12)
    cropped = tmp_path / "cropped.jdf"
    cropped.write_bytes(contents)

    _, data = jeol.read(cropped)
    assert data.shape == (10 * rows_per_increment, 82)
    np.testing.assert_array_equal(
        data, original[3 * rows_per_increment:13 * rows_per_increment, 19:101],
    )
