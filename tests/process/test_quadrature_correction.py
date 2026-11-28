import numpy as np
import pytest

from nmrglue.process import proc_base


@pytest.mark.parametrize("dtype", [np.complex64, np.complex128, np.clongdouble])
@pytest.mark.parametrize("gain, leakage", [(1., 0.), (2., .5), (.4, -.25)])
def test_automatic_quadrature_recovers_orthogonal_channels(dtype, gain, leakage):
    real = np.array([1., 0., -1., 0.])
    ideal_imag = np.array([0., 1., 0., -1.])
    data = (real + 1j * (gain * ideal_imag + leakage * real)).astype(dtype)
    original = data.copy()

    a, f = proc_base.gram_schmidt(data)
    np.testing.assert_array_equal(data, original)
    actual = proc_base.qart_auto(data.copy())

    tolerance = 2e-7 if dtype == np.complex64 else 1e-14
    np.testing.assert_allclose([a, f], [1 / gain - 1, -leakage / gain],
                               rtol=tolerance, atol=tolerance)
    np.testing.assert_allclose(actual, real + 1j * ideal_imag,
                               rtol=tolerance, atol=tolerance)
    np.testing.assert_array_equal(actual.real, original.real)
    assert actual.dtype == data.dtype
    assert np.vdot(actual.real, actual.imag) == pytest.approx(0., abs=tolerance)
    assert np.vdot(actual.real, actual.real) == pytest.approx(
        np.vdot(actual.imag, actual.imag), rel=tolerance)


@pytest.mark.parametrize("scale", [1e-150, 1e150])
def test_automatic_quadrature_is_independent_of_signal_scale(scale):
    data = scale * np.array([1+.5j, 2j, -1-.5j, -2j])
    actual = proc_base.qart_auto(data.copy())
    np.testing.assert_allclose(actual / scale, [1, 1j, -1, -1j], atol=1e-14)


@pytest.mark.parametrize("data", [
    np.array([], complex), np.zeros(4, complex),
    np.array([1., 2.]), np.array([1j, 2j]),
    np.array([1+1j, 2+2j]), np.array([1+1j, np.nan+1j]),
    np.array([1+1j, np.inf+1j]),
    np.array([1+7j, 3+21j, 5+35j]),
])
def test_automatic_quadrature_rejects_undefined_correction(data):
    original = data.copy()
    with pytest.raises(ValueError):
        proc_base.qart_auto(data)
    np.testing.assert_array_equal(data, original)
