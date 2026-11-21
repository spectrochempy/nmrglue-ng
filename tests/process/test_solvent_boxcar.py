import numpy as np
import pytest

from nmrglue.process.proc_bl import sol_boxcar


@pytest.mark.parametrize('width', [1, 3, 4])
@pytest.mark.parametrize('ndim', [1, 2])
@pytest.mark.parametrize('complex_data', [False, True])
def test_boxcar_matches_normalized_rectangular_convolution(width, ndim, complex_data):
    data = np.arange(14., dtype=float).reshape(2, 7)
    if complex_data:
        data = data + 1j * data[:, ::-1]
    if ndim == 1:
        data = data[0]
    original = data.copy()
    traces = np.atleast_2d(data)
    expected = np.stack([row - np.convolve(row, np.ones(width) / width, mode='same')
                         for row in traces])
    if ndim == 1:
        expected = expected[0]
    np.testing.assert_allclose(sol_boxcar(data, w=width), expected, rtol=0, atol=2e-14)
    np.testing.assert_array_equal(data, original)
