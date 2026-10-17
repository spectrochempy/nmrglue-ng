"""Test ``data_nd`` operations on concrete file-format subclasses."""

import copy
import importlib.util
import os
import sys
import types

import numpy as np
from numpy.testing import assert_array_equal
import pytest

# ``nmrglue.fileio.glue`` imports the optional ``h5py`` package at module
# import time.  Its low-memory wrappers only need an array-like dataset, so
# when h5py is missing a throwaway stub lets the wrapper-contract tests run;
# the stub is removed immediately so h5py stays absent for the rest of the
# session and the optional-dependency classification stays accurate.
HAS_H5PY = importlib.util.find_spec("h5py") is not None
if HAS_H5PY:
    from nmrglue.fileio import glue
else:
    sys.modules["h5py"] = types.ModuleType("h5py")
    try:
        from nmrglue.fileio import glue
    finally:
        del sys.modules["h5py"]

from nmrglue.fileio import bruker, fileiobase, pipe, rnmrtk


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "fileio", "data")
NMRPIPE_2D_FREQ = os.path.join(DATA_DIR, "nmrpipe_2d_freq.ft2")


def assert_view(view, expected, expected_order):
    """Check a lazy view's metadata, full values, and representative slices."""
    assert isinstance(view, fileiobase.data_nd)
    assert not isinstance(view, np.ndarray)
    assert tuple(view.order) == tuple(expected_order)
    assert view.shape == expected.shape
    assert view.dtype == expected.dtype
    assert_array_equal(view[:], np.squeeze(expected))
    assert_array_equal(view[0], np.squeeze(expected[0]))
    assert_array_equal(view[..., 0], np.squeeze(expected[..., 0]))


def assert_data_nd_contract(data, expected):
    """Check copies and axis transforms against a materialized NumPy oracle."""
    original_order = tuple(data.order)
    original_shape = data.shape

    copied = copy.copy(data)
    assert type(copied) is type(data)
    assert copied is not data
    assert_view(copied, expected, original_order)

    transposed = data.transpose(-1, -2)
    assert type(transposed) is type(data)
    assert_view(transposed, expected.transpose(-1, -2), original_order[::-1])

    swapped = data.swapaxes(-1, 0)
    assert type(swapped) is type(data)
    assert_view(swapped, expected.swapaxes(-1, 0), original_order[::-1])

    copied_transformed = copy.copy(swapped)
    assert type(copied_transformed) is type(data)
    assert_view(
        copied_transformed,
        expected.swapaxes(-1, 0),
        original_order[::-1],
    )

    transformed_copy = copy.copy(data).swapaxes(-1, 0)
    assert type(transformed_copy) is type(data)
    assert_view(
        transformed_copy,
        expected.swapaxes(-1, 0),
        original_order[::-1],
    )
    assert tuple(data.order) == original_order
    assert data.shape == original_shape


def test_nmrpipe_data_nd_contract():
    _, data = pipe.read_lowmem(NMRPIPE_2D_FREQ)
    _, expected = pipe.read(NMRPIPE_2D_FREQ)

    assert_data_nd_contract(data, expected)


@pytest.mark.parametrize(
    "isfloat, storage_dtype",
    [(False, "<i4"), (True, "<f8")],
)
def test_bruker_data_nd_contract(tmp_path, isfloat, storage_dtype):
    expected = np.arange(6, dtype=np.int32).reshape(1, 6)
    filename = tmp_path / "bruker.bin"
    filename.write_bytes(expected.astype(storage_dtype).tobytes())
    data = bruker.bruker_nd(
        str(filename), expected.shape, False, False, isfloat=isfloat
    )

    assert_data_nd_contract(data, expected)
    assert copy.copy(data).isfloat is isfloat
    assert data.swapaxes(-1, 0).isfloat is isfloat


def test_rnmrtk_data_nd_contract(tmp_path):
    expected = np.arange(6, dtype=np.float32).reshape(2, 3)
    filename = tmp_path / "rnmrtk.sec"
    filename.write_bytes(expected.astype("<f4").tobytes())
    data = rnmrtk.rnmrtk_nd(
        str(filename), expected.shape, False, False
    )

    assert_data_nd_contract(data, expected)


def test_glue_2d_data_nd_contract():
    expected = np.arange(12, dtype=np.float32).reshape(3, 4)
    data = glue.glue_2d(expected)

    assert_data_nd_contract(data, expected)


def test_glue_3d_data_nd_contract():
    expected = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
    data = glue.glue_3d(expected)

    assert_view(data, expected, (0, 1, 2))

    reversed_axes = data.transpose()
    assert type(reversed_axes) is glue.glue_3d
    assert_array_equal(reversed_axes[:], expected.transpose(2, 1, 0))

    swapped = data.swapaxes(-1, 0)
    assert type(swapped) is glue.glue_3d
    assert_array_equal(swapped[:], expected.swapaxes(-1, 0))


@pytest.mark.skipif(not HAS_H5PY, reason="optional dependency not installed: h5py")
def test_glue_hdf5_roundtrip_contract(tmp_path):
    expected_2d = np.arange(12, dtype=np.float32).reshape(3, 4)
    path_2d = tmp_path / "glue_2d.h5"
    glue.write(str(path_2d), {"ndim": 2}, expected_2d)
    _, data_2d = glue.read_lowmem(str(path_2d))
    assert_data_nd_contract(data_2d, expected_2d)

    expected_3d = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
    path_3d = tmp_path / "glue_3d.h5"
    glue.write(str(path_3d), {"ndim": 3}, expected_3d)
    _, data_3d = glue.read_lowmem(str(path_3d))
    assert_array_equal(data_3d[:], expected_3d)

    reversed_axes = data_3d.transpose()
    assert type(reversed_axes) is glue.glue_3d
    assert_array_equal(reversed_axes[:], expected_3d.transpose(2, 1, 0))
