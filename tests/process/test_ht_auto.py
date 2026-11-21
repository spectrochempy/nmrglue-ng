import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from nmrglue.fileio import pipe
from nmrglue.process import pipe_proc


def analytic_signal_dft(data, size):
    length = data.shape[-1]
    padded = np.zeros(data.shape[:-1] + (size,))
    padded[..., :length] = data.real
    indices = np.arange(size)
    forward = np.exp(-2.j * np.pi * np.outer(indices, indices) / size)
    weights = np.zeros(size)
    weights[0] = 1.
    weights[1:(size + 1) // 2] = 2.
    if size % 2 == 0:
        weights[size // 2] = 1.
    result = ((padded @ forward.T) * weights) @ forward.conj() / size
    result = result[..., :length] * (size / length)
    result.real = data.real
    return result


@pytest.mark.parametrize("length", [5, 6, 7, 10, 11, 16])
@pytest.mark.parametrize("two_dimensional", [False, True])
@pytest.mark.parametrize("zero_fill", [False, True])
@pytest.mark.parametrize("ftflag", [0., 1.])
def test_ht_auto_preserves_explicit_zero_fill(length, two_dimensional, zero_fill, ftflag):
    data = (np.arange(length) % 4 - 1.).astype(np.float32)
    if two_dimensional:
        data = np.stack([data, data[::-1]])
    dic = pipe.create_empty_dic()
    dic.update(FDF2FTFLAG=ftflag, FDF2P1=0., FDF2X1=0., FDF2XN=0.)
    size = 2 ** (length - 1).bit_length() if zero_fill else length
    expected = analytic_signal_dft(data, size)
    _, actual = pipe_proc.ht(dic, data, auto=True, zf=zero_fill)
    assert actual.dtype == np.complex64
    assert_array_equal(actual.real, data)
    assert_allclose(actual, expected, rtol=2e-6, atol=2e-6)


@pytest.mark.parametrize("extracted", [False, True])
@pytest.mark.parametrize("zero_fill", [False, True])
def test_ht_auto_retains_mirror_selection(extracted, zero_fill):
    data = np.array([1., 2., 4., 8., 16.], dtype=np.float32)
    dic = pipe.create_empty_dic()
    dic.update(FDF2P1=180., FDF2X1=float(extracted), FDF2XN=0.)
    if extracted:
        size = 8 if zero_fill else 5
        expected = analytic_signal_dft(data, size)
    else:
        expected = np.array([1.-12.242127j, 2.-5.3340144j, 4.-5.8728495j,
                             8.-6.950515j, 16.+5.830447j])
    _, actual = pipe_proc.ht(dic, data, auto=True, zf=zero_fill)
    assert_allclose(actual, expected, rtol=2e-6, atol=2e-6)
