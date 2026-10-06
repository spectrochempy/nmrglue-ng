""" Unit tests for nmrglue/fileio/fileiobase.py module """

import copy
import os

import numpy as np
from numpy.testing import assert_array_equal
import nmrglue as ng
import pytest


# Test data.
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
NMRPIPE_1D_FREQ = os.path.join(DATA_DIR, 'nmrpipe_1d_freq.fid')


class DummyDataND(ng.fileiobase.data_nd):
    """Minimal data_nd implementation for testing base-class operations."""

    def __init__(self, order=None, fshape=(2, 3, 4)):
        self.fshape = fshape
        if order is None:
            order = range(len(fshape))
        self.order = tuple(order)
        self.dtype = np.dtype("float64")
        self.__setdimandshape__()

    def __fcopy__(self, order):
        return DummyDataND(order, self.fshape)

    def __fgetitem__(self, slices):
        return np.arange(np.prod(self.fshape)).reshape(self.fshape)[slices]


def test_uc_from_freqscale():
    """
    Test that `uc_from_freqscale` gives equivalent results as `uc_from_udic`.
    """
    from nmrglue.fileio.fileiobase import uc_from_freqscale

    # read frequency test data
    dic, data = ng.pipe.read(NMRPIPE_1D_FREQ)

    # make udic and uc using uc_from_udic
    udic = ng.pipe.guess_udic(dic, data)
    uc = ng.fileiobase.uc_from_udic(udic)

    ppm_scale = uc.ppm_scale()
    uc_from_ppm = uc_from_freqscale(ppm_scale, udic[0]['obs'], 'ppm')
    new_ppm_scale = uc_from_ppm.ppm_scale()
    assert_array_equal(ppm_scale, new_ppm_scale)

    hz_scale = uc.hz_scale()
    uc_from_hz = uc_from_freqscale(hz_scale, udic[0]['obs'], 'hz')
    new_hz_scale = uc_from_hz.hz_scale()
    assert_array_equal(hz_scale, new_hz_scale)

    khz_scale = hz_scale * 1.0e3
    uc_from_khz = uc_from_freqscale(khz_scale, udic[0]['obs'], 'khz')
    new_khz_scale = uc_from_khz.hz_scale() * 1.0e3
    assert_array_equal(khz_scale, new_khz_scale)


# regression test for https://github.com/jjhelmus/nmrglue/issues/113
def test_uc_with_float_size():
    uc = ng.fileiobase.unit_conversion(
        size=64.0, cplx=False, sw=1.0, obs=1.0, car=1.0)
    scale = uc.ppm_scale()
    assert len(scale) == 64


def test_update_uc():
    uc = ng.fileiobase.unit_conversion(
        size=64.0, cplx=False, sw=1.0, obs=1.0, car=1.0)
    uc2 = ng.fileiobase.update_uc(uc, size=10, cplx=True, sw=2.0, car=5.2, obs=3.0)
    assert uc2._size == 10
    assert uc2._cplx is True
    assert abs(uc2._sw - 2.0) < 1e-5
    assert abs(uc2._car - 5.2) < 1e-5
    assert abs(uc2._obs - 3.0) < 1e-5


def test_data_nd_copy():
    data = DummyDataND()

    copied = copy.copy(data)

    assert copied is not data
    assert copied.order == data.order
    assert_array_equal(copied[:], data[:])


def test_data_nd_copy_and_transform_orders_are_independent():
    data = DummyDataND(fshape=(2, 3, 4))
    expected = np.arange(24).reshape(data.fshape)

    transformed = data.transpose(-1, -2, -3)
    copied_transformed = copy.copy(transformed)
    transformed_copy = copy.copy(data).swapaxes(-3, 2)

    assert data.order == (0, 1, 2)
    assert transformed.order == (2, 1, 0)
    assert copied_transformed.order == transformed.order
    assert transformed_copy.order == (2, 1, 0)
    assert_array_equal(copied_transformed[:], expected.transpose(2, 1, 0))
    assert_array_equal(transformed_copy[:], expected.swapaxes(-3, 2))
    assert data.order == (0, 1, 2)
    assert data.shape == (2, 3, 4)


def test_data_nd_copy_preserves_low_memory_access():
    data = DummyDataND(fshape=(2, 3, 4))

    copied = copy.copy(data)

    assert isinstance(copied, DummyDataND)
    assert not isinstance(copied, np.ndarray)


@pytest.mark.parametrize("axes", [(-1, 0), (0, -1)])
def test_data_nd_swapaxes_with_negative_axis(axes):
    data = DummyDataND(fshape=(2, 3))

    swapped = data.swapaxes(*axes)

    assert swapped.order == (1, 0)
    assert swapped.shape == (3, 2)
    assert_array_equal(swapped[:], np.arange(6).reshape(2, 3).swapaxes(0, 1))


def test_data_nd_swapaxes_3d_with_negative_axis():
    data = DummyDataND(fshape=(2, 3, 4))

    swapped = data.swapaxes(-3, 2)

    assert swapped.order == (2, 1, 0)
    expected = np.arange(24).reshape(2, 3, 4).swapaxes(-3, 2)
    assert_array_equal(swapped[:], expected)


def test_data_nd_swapaxes_does_not_mutate_source():
    data = DummyDataND(fshape=(2, 3, 4))
    original_order = tuple(data.order)
    original_shape = data.shape

    data.swapaxes(-1, 0)
    data.swapaxes(0, -1)

    assert data.order == original_order
    assert data.shape == original_shape


def test_data_nd_swapaxes_normalizes_negative_axes():
    data = DummyDataND(fshape=(2, 3, 4))

    swapped = data.swapaxes(-3, 2)

    assert swapped.order == (2, 1, 0)
    expected = np.arange(24).reshape(2, 3, 4).swapaxes(-3, 2)
    assert_array_equal(swapped[:], expected)


@pytest.mark.parametrize(
    "axes",
    [
        (-4, 0),
        (0, -4),
        (3, 0),
        (0, 3),
        (4, 0),
        (0, 4),
    ],
)
def test_data_nd_swapaxes_rejects_invalid_axis(axes):
    with pytest.raises(ValueError):
        DummyDataND().swapaxes(*axes)


@pytest.mark.parametrize(
    "axes, expected_order",
    [
        ((0, 1, 2), (0, 1, 2)),
        ((2, 1, 0), (2, 1, 0)),
        ((-1, -2, -3), (2, 1, 0)),
        ((-3, 1, -1), (0, 1, 2)),
    ],
)
def test_data_nd_transpose_axes(axes, expected_order):
    data = DummyDataND(fshape=(2, 3, 4))

    transposed = data.transpose(*axes)

    assert transposed.order == expected_order
    expected = np.arange(24).reshape(data.fshape).transpose(axes)
    assert_array_equal(transposed[:], expected)


def test_data_nd_transpose_does_not_mutate_source():
    data = DummyDataND(fshape=(2, 3, 4))
    original_order = tuple(data.order)
    original_shape = data.shape

    data.transpose(-1, -2, -3)
    data.transpose(2, 1, 0)

    assert data.order == original_order
    assert data.shape == original_shape


@pytest.mark.parametrize(
    "axes",
    [
        (-4, 0, 1),
        (0, -4, 1),
        (3, 0, 1),
        (0, 3, 1),
        (0, 0, 1),
        (0,),
        (0, 1),
        (0, 1, 2, 3),
    ],
)
def test_data_nd_transpose_rejects_invalid_axes(axes):
    with pytest.raises(ValueError):
        DummyDataND(fshape=(2, 3, 4)).transpose(*axes)


@pytest.mark.parametrize(
    "call_form",
    ["no_args", "single_int", "single_np_int64", "single_tuple"],
)
def test_data_nd_transpose_1d(call_form):
    data = DummyDataND(fshape=(5,))
    expected = np.arange(5)

    if call_form == "no_args":
        transposed = data.transpose()
    elif call_form == "single_int":
        transposed = data.transpose(0)
    elif call_form == "single_np_int64":
        transposed = data.transpose(np.int64(0))
    else:
        transposed = data.transpose((0,))

    assert transposed.order == (0,)
    assert transposed.shape == (5,)
    assert_array_equal(transposed[:], expected)


def test_data_nd_transpose_1d_accepts_sequence_axes():
    data = DummyDataND(fshape=(5,))

    assert data.transpose(np.array([0])).order == (0,)
    assert data.transpose(range(1)).order == (0,)


def test_data_nd_transpose_2d_accepts_sequence_axes():
    data = DummyDataND(fshape=(3, 4))
    expected = np.arange(12).reshape(3, 4)

    r = data.transpose(np.array([1, 0]))
    assert r.order == (1, 0)
    assert_array_equal(r[:], expected.transpose(1, 0))

    r = data.transpose(range(2))
    assert r.order == (0, 1)
    assert_array_equal(r[:], expected)


def test_data_nd_transpose_rejects_float_axis():
    data = DummyDataND(fshape=(5,))
    with pytest.raises(TypeError):
        data.transpose(0.5)


def test_data_nd_transpose_2d_does_not_regress():
    data = DummyDataND(fshape=(3, 4))
    expected = np.arange(12).reshape(3, 4)

    assert data.transpose().order == (1, 0)
    assert_array_equal(data.transpose()[:], expected.transpose())
    assert data.transpose(1, 0).order == (1, 0)
    assert_array_equal(data.transpose(1, 0)[:], expected.transpose(1, 0))
    assert data.transpose((1, 0)).order == (1, 0)
    assert_array_equal(data.transpose((1, 0))[:], expected.transpose((1, 0)))


def test_data_nd_slicing_after_transform():
    data = DummyDataND(fshape=(2, 3, 4))
    expected = np.arange(24).reshape(data.fshape)

    swapped = data.swapaxes(-1, 0)
    swapped_expected = expected.swapaxes(-1, 0)
    assert swapped.shape == swapped_expected.shape
    assert_array_equal(swapped[0], swapped_expected[0])
    assert_array_equal(swapped[0, 1], swapped_expected[0, 1])
    assert_array_equal(swapped[0, 1, 1], swapped_expected[0, 1, 1])

    transposed = data.transpose(-1, -2, -3)
    transposed_expected = expected.transpose(2, 1, 0)
    assert transposed.shape == transposed_expected.shape
    assert_array_equal(transposed[0], transposed_expected[0])
    assert_array_equal(transposed[0, 1], transposed_expected[0, 1])
    assert_array_equal(transposed[0, 1, 1], transposed_expected[0, 1, 1])
