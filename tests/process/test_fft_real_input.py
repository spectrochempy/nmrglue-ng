import numpy as np
import pytest

from nmrglue.process import proc_base


@pytest.mark.parametrize("dtype", [np.float32, np.float64, np.int32])
@pytest.mark.parametrize("size", [4, 5])
@pytest.mark.parametrize("forward,inverse,sign,norm", [
    (proc_base.fft, proc_base.ifft, -1, False),
    (proc_base.fft_positive, proc_base.ifft_positive, 1, False),
    (proc_base.fft_norm, proc_base.ifft_norm, -1, True),
])
def test_fft_real_input_preserves_full_complex_transform(dtype, size, forward, inverse, sign, norm):
    data = np.arange(2 * size * 2).reshape(2, -1).astype(dtype)[:, ::2]
    original = data.copy()
    points = np.arange(size)
    kernel = np.exp(sign * 2j * np.pi * np.outer(points, points) / size)
    expected = np.roll(data @ kernel, size // 2, axis=-1)
    if norm:
        expected /= np.sqrt(size)

    actual = forward(data)

    assert np.iscomplexobj(actual)
    assert actual.dtype == forward(data.astype(np.result_type(dtype, np.complex64))).dtype
    np.testing.assert_allclose(actual, expected, rtol=2e-6, atol=2e-6)
    np.testing.assert_allclose(inverse(actual), original, rtol=2e-6, atol=2e-6)
    np.testing.assert_array_equal(data, original)


@pytest.mark.parametrize("dtype", [np.float32, np.float64, np.int32])
@pytest.mark.parametrize("inverse,sign,norm", [
    (proc_base.ifft, 1, False),
    (proc_base.ifft_positive, -1, False),
    (proc_base.ifft_norm, 1, True),
])
def test_inverse_fft_real_spectrum_preserves_imaginary_signal(dtype, inverse, sign, norm):
    spectrum = np.array([0, 1, 0, 0, 0], dtype=dtype)
    original = spectrum.copy()
    size = spectrum.size
    points = np.arange(size)
    kernel = np.exp(sign * 2j * np.pi * np.outer(points, points) / size)
    expected = np.roll(spectrum, -(size // 2)) @ kernel / size
    if norm:
        expected *= np.sqrt(size)

    actual = inverse(spectrum)

    assert np.iscomplexobj(actual)
    assert actual.dtype == inverse(spectrum.astype(np.result_type(dtype, np.complex64))).dtype
    np.testing.assert_allclose(actual, expected, rtol=2e-6, atol=2e-6)
    np.testing.assert_array_equal(spectrum, original)
