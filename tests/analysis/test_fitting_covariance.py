import numpy as np
import pytest
from scipy.optimize import _minpack

from nmrglue.analysis import linesh
from nmrglue.analysis.leastsqbound import leastsqbound


@pytest.mark.parametrize("bounds", [
    [(None, None), (None, None)],
    [(0., None), (None, 5.)],
    [(0., 10.), (0., 5.)],
])
@pytest.mark.parametrize("one_based", [False, True])
def test_full_output_covariance_matches_linear_model(bounds, one_based, monkeypatch):
    if one_based:
        original = _minpack._lmdif

        def with_one_based_pivots(*args):
            result = original(*args)
            if result[1]['ipvt'].min() == 0:
                result[1]['ipvt'] += 1
            return result

        monkeypatch.setattr(_minpack, '_lmdif', with_one_based_pivots)
    matrix = np.array([[.1, 3.], [.2, -1.], [.1, 5.], [.4, .5]])
    truth = np.array([3., 1.])
    observed = matrix @ truth
    result, covariance, info, message, ier = leastsqbound(
        lambda p: matrix @ p - observed, [2., .5], bounds=bounds, full_output=True,
    )

    assert ier in (1, 2, 3, 4), message
    np.testing.assert_allclose(result, truth, rtol=0, atol=1e-8)
    np.testing.assert_allclose(covariance, np.linalg.inv(matrix.T @ matrix),
                               rtol=2e-6, atol=1e-8)
    np.testing.assert_allclose(info['fvec'], matrix @ result - observed, atol=1e-12)


def test_full_output_at_degenerate_bound_has_no_covariance():
    result, covariance, info, message, ier = leastsqbound(
        lambda p: np.array([p[0], 2*p[0]]), [0.],
        bounds=[(0., None)], full_output=True,
    )
    assert ier in (1, 2, 3, 4), message
    np.testing.assert_array_equal(result, [0.])
    assert covariance is None


def test_gaussian_fit_returns_analytic_uncertainties():
    x = np.arange(64.)
    data = 3 * np.exp(-4 * np.log(2) * ((x - 29) / 6)**2)
    data += .01 * np.sin(x * 1.7)

    params, amps, param_errors, amp_errors, ier = linesh.fit_NDregion(
        data, ['g'], [[(28., 5.)]], [2.],
        bounds=[[[(20., 40.), (1., 15.)]]], ampbounds=[(0., None)],
        error_flag=True,
    )

    assert ier in (1, 2, 3, 4)
    center, width = params[0][0]
    amplitude = amps[0]
    g = np.exp(-4 * np.log(2) * ((x - center) / width)**2)
    jac = np.column_stack((g, amplitude * g * 8 * np.log(2) * (x-center) / width**2,
                           amplitude * g * 8 * np.log(2) * (x-center)**2 / width**3))
    variance = np.sum((data - amplitude * g)**2) / (data.size - 3)
    expected = np.sqrt(np.diag(np.linalg.inv(jac.T @ jac)) * variance)
    actual = np.r_[amp_errors, np.ravel(param_errors)]
    np.testing.assert_allclose(actual, expected, rtol=2e-4, atol=1e-9)
