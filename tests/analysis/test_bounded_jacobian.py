import numpy as np
import pytest

from nmrglue.analysis.leastsqbound import leastsqbound


@pytest.mark.parametrize("col_deriv", [False, True])
@pytest.mark.parametrize("container", [np.asarray, np.asmatrix, list])
@pytest.mark.parametrize("bounds", [
    [(0., None), (0., None)],
    [(None, 10.), (None, 5.)],
    [(0., 10.), (0., 5.)],
    [(0., None), (None, 5.)],
    [(None, None), (None, None)],
])
def test_bounded_analytic_jacobian_recovers_known_parameters(bounds, col_deriv, container):
    matrix = np.array([[1., 2.], [2., -1.], [1., 3.], [4., .5]])
    truth = np.array([3., 1.])
    observed = matrix @ truth**2

    def residual(p, a, y):
        return a @ p**2 - y

    def jacobian(p, a, y):
        result = a * (2 * p)
        return container(result.T if col_deriv else result)

    result, ier = leastsqbound(
        residual, [2., .5], args=(matrix, observed), bounds=bounds,
        Dfun=jacobian, col_deriv=col_deriv,
    )
    numeric, numeric_ier = leastsqbound(
        residual, [2., .5], args=(matrix, observed), bounds=bounds,
    )

    assert ier in (1, 2, 3, 4)
    assert numeric_ier in (1, 2, 3, 4)
    np.testing.assert_allclose(result, truth, rtol=0, atol=1e-8)
    np.testing.assert_allclose(result, numeric, rtol=0, atol=1e-8)
    np.testing.assert_allclose(residual(result, matrix, observed), 0., atol=1e-7)
