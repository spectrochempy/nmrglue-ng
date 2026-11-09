import numpy as np
import pytest

from nmrglue.process import proc_base


@pytest.mark.parametrize("size", [8, 9])
@pytest.mark.parametrize("dtype", [np.complex64, np.complex128])
@pytest.mark.parametrize(
    "forward, inverse, sign, normalized",
    [
        (proc_base.fft, proc_base.ifft, 1, False),
        (proc_base.fft_norm, proc_base.ifft_norm, 1, True),
        (proc_base.fft_positive, proc_base.ifft_positive, -1, False),
    ],
)
def test_complex_fft_conventions(size, dtype, forward, inverse, sign, normalized):
    bins = np.array([0, 1, size - 1, size // 2])
    signal = np.exp(2j * np.pi * bins[:, None] * np.arange(size) / size)
    signal = signal.astype(dtype)
    original = signal.copy()
    expected = np.zeros_like(signal)
    expected[np.arange(bins.size), (sign * bins + size // 2) % size] = (
        np.sqrt(size) if normalized else size
    )
    tolerance = 2e-6 if dtype == np.complex64 else 1e-12

    spectrum = forward(signal)
    np.testing.assert_allclose(spectrum, expected, atol=tolerance, rtol=tolerance)
    np.testing.assert_array_equal(signal, original)

    expected_before = expected.copy()
    np.testing.assert_allclose(inverse(expected), original, atol=tolerance, rtol=tolerance)
    np.testing.assert_array_equal(expected, expected_before)
