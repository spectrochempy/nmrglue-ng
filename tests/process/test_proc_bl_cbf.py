import numpy as np
import pytest

from nmrglue.process import proc_bl


@pytest.mark.parametrize("last", [100, 100., np.float64(100), 10., 0., 33.3])
@pytest.mark.parametrize("shape", [(10,), (3, 10)])
def test_constant_signal_is_removed(last, shape):
    data = np.full(shape, 3. + 2j)
    np.testing.assert_array_equal(proc_bl.cbf(data, last=last), np.zeros(shape))


@pytest.mark.parametrize("last, start", [(0, 9), (10, 8), (33.3, 6), (100, 0)])
def test_selected_samples_keep_historical_percentage_convention(last, start):
    data = np.arange(10.)
    expected = data - np.sum(data[start:]) / (10 - start)
    np.testing.assert_array_equal(proc_bl.cbf(data.copy(), last=last), expected)


def test_two_dimensional_apply_slice():
    data = np.array([[1., 2., 3.], [4., 8., 12.], [7., 8., 9.]])
    expected = data.copy()
    expected[1] -= 8.
    result = proc_bl.cbf(data, last=100., apply=slice(1, 2))
    np.testing.assert_array_equal(result, expected)


@pytest.mark.parametrize("last", [-1, 101, np.nan, np.inf])
def test_invalid_percentage_is_rejected(last):
    with pytest.raises(ValueError, match="last"):
        proc_bl.cbf(np.ones(10), last=last)


def test_empty_trace_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        proc_bl.cbf(np.empty((2, 0)))
