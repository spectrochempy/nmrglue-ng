import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from nmrglue.process import proc_bl as p


@pytest.mark.parametrize("length", [1, 2, 8, 64, 128])
@pytest.mark.parametrize("level", [-3., 0., 7.])
def test_constant_trace_is_removed_without_mutation(length, level):
    data = np.full(length, level)
    original = data.copy()
    with np.errstate(all="raise"):
        actual = p.baseline_corrector(data)
    assert actual.shape == data.shape
    assert_allclose(actual, 0., atol=3e-14)
    assert_array_equal(data, original)


@pytest.mark.parametrize("radius", [1, 2, 20])
def test_sd_uses_centered_clipped_windows_for_every_point(radius):
    data = np.array([1., 2., 4., 8., 16., 32., 64.])
    expected = np.array([np.std(data[max(0, i-radius):min(len(data), i+radius+1)])
                         for i in range(len(data))])
    assert_allclose(p._get_sd(data, radius), expected, rtol=2e-15, atol=0.)


def test_signal_dilation_includes_both_boundaries():
    expected = np.zeros(9)
    expected[2:7] = 1
    assert_array_equal(p._is_signal(1., np.array([0., 0., 0., 0., 2., 0., 0., 0., 0.]), 2),
                       expected)


def test_empty_signal_boundaries_are_integer_indices():
    actual = p._get_signal_start(np.zeros(8))
    assert np.issubdtype(actual.dtype, np.integer)
    assert actual.size == 0


@pytest.mark.parametrize("radius", [0, 1, 2])
def test_segment_interpolation_uses_both_averaged_endpoints(radius):
    data = np.array([1., 2., 4., 25., 30., 8., 7., 5., 2., 1.])
    expected = data.copy()
    left = np.mean(data[2-radius:3+radius])
    right = np.mean(data[6-radius:7+radius])
    expected[2:7] = np.linspace(left, right, 5)
    actual = p._get_temp_baseline(data, np.array([2]), np.array([6]), radius)
    assert_allclose(actual, expected)
    assert_array_equal(data, [1., 2., 4., 25., 30., 8., 7., 5., 2., 1.])


def test_no_segments_preserves_temporary_trace():
    data = np.arange(8.)
    assert_array_equal(p._get_temp_baseline(data, np.array([], dtype=int),
                                            np.array([], dtype=int), 7), data)


@pytest.mark.parametrize("radius", [0, 1, 3, 60])
def test_smooth_is_clipped_mean_not_zero_padded_median(radius):
    data = np.array([1., 3., 8., 2., 4.])
    expected = [np.mean(data[max(0, i-radius):min(len(data), i+radius+1)])
                for i in range(len(data))]
    assert_allclose(p._smooth(data, radius), expected, rtol=2e-15)


@pytest.mark.parametrize("data", [[], [[1., 2.]], [1.+1.j, 2.+2.j],
                                  [1., np.nan], [1., np.inf]])
def test_invalid_trace_is_rejected(data):
    with pytest.raises(ValueError, match="nonempty finite real one-dimensional"):
        p.baseline_corrector(np.asarray(data))


@pytest.mark.parametrize("radius", [0, -1, 1.5, True])
def test_invalid_radius_is_rejected(radius):
    with pytest.raises(ValueError, match="positive integer"):
        p.baseline_corrector(np.arange(128.), wd=radius)


def test_all_signal_is_not_silently_used_as_baseline(monkeypatch):
    monkeypatch.setattr(p, "_is_signal", lambda sigma, sd, w: np.ones(sd.size))
    with pytest.raises(ValueError, match="no noise-only support"):
        p.baseline_corrector(np.arange(128.))


@pytest.mark.parametrize("sign", [-1., 1.])
def test_known_curved_background_and_peak_area(sign):
    points = np.arange(4096)
    x = np.linspace(-1., 1., points.size)
    background = 2. + .2*x + .1*x*x
    peak = sign * 5. * np.exp(-.5*((points-2048)/6.)**2)
    noise = np.random.default_rng(31).normal(0., .01, points.size)
    data = background + peak + noise
    actual = p.baseline_corrector(data)
    estimated_background = data - actual
    assert np.sqrt(np.mean((estimated_background-background)**2)) < .003
    region = abs(points-2048) <= 30
    assert np.sum((actual-noise)[region]) == pytest.approx(np.sum(peak[region]), rel=.005)
    assert_allclose(p.baseline_corrector(data[::-1])[::-1], actual, atol=2e-12)
    assert_allclose(p.baseline_corrector(-2.*data+13.), -2.*actual, atol=2e-12)


def test_mask_is_not_silently_discarded():
    with pytest.raises(ValueError, match="without a mask"):
        p.baseline_corrector(np.ma.array([1., 2., 3.], mask=[False, True, False]))
