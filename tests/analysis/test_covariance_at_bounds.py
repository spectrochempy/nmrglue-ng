import numpy as np
import pytest

from nmrglue.analysis import linesh
from nmrglue.analysis.leastsqbound import leastsqbound


def _fit(target, start, bounds, derivative):
    kw = {}
    if derivative != 'numeric':
        kw['Dfun'] = lambda p: np.array([[1., 2.]]) if derivative == 'col' else np.array([[1.], [2.]])
        kw['col_deriv'] = derivative == 'col'
    return leastsqbound(lambda p: np.array([p[0] - target, 2*(p[0] - target)]),
                        [start], bounds=[bounds], full_output=True, **kw)


@pytest.mark.parametrize("bounds", [(0., 10.), (-10., 0.), (10., 20.), (-20., -10.)])
@pytest.mark.parametrize("side", [0, 1])
@pytest.mark.parametrize("derivative", ['numeric', 'row', 'col'])
def test_two_sided_endpoint_has_no_covariance(bounds, side, derivative):
    target = bounds[side]
    result, covariance, info, message, ier = _fit(target, target, bounds, derivative)
    assert ier in (1, 2, 3, 4), message
    np.testing.assert_allclose(result, [target], rtol=0, atol=1e-12)
    np.testing.assert_allclose(info['fvec'], 0., atol=1e-12)
    assert covariance is None


@pytest.mark.parametrize("bounds,target", [((0., None), 0.), ((None, 10.), 10.)])
@pytest.mark.parametrize("derivative", ['numeric', 'row', 'col'])
def test_one_sided_endpoint_still_has_no_covariance(bounds, target, derivative):
    result, covariance, info, message, ier = _fit(target, target, bounds, derivative)
    assert ier in (1, 2, 3, 4), message
    np.testing.assert_array_equal(result, [target])
    assert covariance is None


@pytest.mark.parametrize("derivative", ['numeric', 'row', 'col'])
def test_interior_covariance_still_matches_linear_precision(derivative):
    result, covariance, info, message, ier = _fit(2.5, 2., (0., 10.), derivative)
    assert ier in (1, 2, 3, 4), message
    np.testing.assert_allclose(result, [2.5], atol=1e-9)
    np.testing.assert_allclose(covariance, [[1/5]], rtol=1e-6)


@pytest.mark.parametrize("derivative", ['numeric', 'row', 'col'])
def test_any_endpoint_makes_joint_covariance_unavailable(derivative):
    matrix = np.array([[1., 0.], [0., 1.], [1., 2.]])
    truth = np.array([0., 2.])
    kw = {}
    if derivative != 'numeric':
        kw['Dfun'] = lambda p: matrix.T if derivative == 'col' else matrix
        kw['col_deriv'] = derivative == 'col'
    result, covariance, info, message, ier = leastsqbound(
        lambda p: matrix @ (p - truth), truth, bounds=[(0., 10.), (None, None)],
        full_output=True, **kw,
    )
    assert ier in (1, 2, 3, 4), message
    np.testing.assert_allclose(result, truth, atol=1e-12)
    assert covariance is None


def test_lineshape_endpoint_errors_are_unavailable():
    grid = np.arange(32.)
    data = 3 * np.exp(-4 * np.log(2) * ((grid - 14) / 4)**2)
    params, amps, param_errors, amp_errors, ier = linesh.fit_NDregion(
        data, ['g'], [[(14., 4.)]], [3.],
        bounds=[[[(None, None), (4., 8.)]]], ampbounds=[(0., None)],
        error_flag=True,
    )
    assert ier in (1, 2, 3, 4)
    np.testing.assert_allclose(params, [[(14., 4.)]], atol=1e-9)
    np.testing.assert_allclose(amps, [3.], atol=1e-9)
    assert amp_errors == [None]
    assert param_errors == [[[None, None]]]
