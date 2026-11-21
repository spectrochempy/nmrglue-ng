import numpy as np
import pytest

from nmrglue.process.proc_bl import _find_noise_sd


def test_noise_median_is_recomputed_after_each_rejection():
    values = np.array([1.,1.,1.,1.,4.,4.,4.,9.,9.,10.,20.,20.,30.,30.,40.])
    original = values.copy()
    assert _find_noise_sd(values, .999) == 1.
    assert _find_noise_sd(values, .2) == 4.
    np.testing.assert_array_equal(values, original)


@pytest.mark.parametrize('values, expected', [
    ([1., 2., 3.], 2.), ([0., 0., 0.], 0.), ([0., 0., 1.], 0.),
    ([3.], 3.), ([1., 1., 100.], 1.),
])
def test_stable_and_zero_noise(values, expected):
    assert _find_noise_sd(np.array(values), .999) == expected


@pytest.mark.parametrize('values', [[], [-1., 2.], [1., np.nan], [1., np.inf], [[1.,2.]]])
def test_invalid_noise_samples(values):
    with pytest.raises(ValueError):
        _find_noise_sd(np.array(values), .999)


@pytest.mark.parametrize('ratio', [0., -1., 1.1, np.nan, np.inf])
def test_invalid_convergence_ratio(ratio):
    with pytest.raises(ValueError):
        _find_noise_sd(np.array([1., 2., 3.]), ratio)
