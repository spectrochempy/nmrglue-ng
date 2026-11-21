import numpy as np
import pytest

from nmrglue.analysis import integration
from nmrglue.fileio.fileiobase import unit_conversion


@pytest.mark.parametrize('indices, value, count', [((-2,2), .5, 2), ((6,10), 0., 2),
                                               ((9,12), 0., 0), ((-5,-1), 0., 0)])
@pytest.mark.parametrize('unit', ['ppm', 'hz'])
@pytest.mark.parametrize('reverse', [False, True])
def test_signal_windows_clip_to_available_points(indices, value, count, unit, reverse):
    uc = unit_conversion(8, False, 800., 400., 0.)
    convert = getattr(uc, unit)
    bounds = tuple(convert(i) for i in indices)
    if reverse:
        bounds = bounds[::-1]
    data = np.array([1.,1.,1.,1.,1.,1.,-1.,1.])
    noise = (convert(6), convert(8))
    expected = [value, np.sqrt(count) * .25]
    actual = integration.integrate(data, uc, bounds, unit=unit, noise_limits=noise)
    np.testing.assert_allclose(actual[0], expected, rtol=0, atol=1e-14)
    actual_nd = integration.ndintegrate(data, uc, bounds, unit=unit, noise_limits=noise)
    np.testing.assert_allclose(actual_nd, expected, rtol=0, atol=1e-14)


@pytest.mark.parametrize('function', [integration.integrate, integration.ndintegrate])
def test_empty_noise_window_is_rejected(function):
    uc = unit_conversion(8, False, 800., 400., 0.)
    with pytest.raises(ValueError, match='noise.*empty'):
        function(np.ones(8), uc, (uc.ppm(0), uc.ppm(2)),
                 noise_limits=(uc.ppm(9), uc.ppm(12)))


def test_anisotropic_2d_clips_in_historical_reverse_axis_order():
    data = np.ones((4, 8))
    data[:2, 4:] = [[-1,1,-1,1], [1,-1,1,-1]]
    x = unit_conversion(8, False, 800., 400., 0.)
    y = unit_conversion(4, False, 800., 400., 0.)
    limits = [(x.ppm(-2), x.ppm(2)), (y.ppm(2), y.ppm(7))]
    noise = [(x.ppm(4), x.ppm(8)), (y.ppm(0), y.ppm(2))]
    actual = integration.ndintegrate(data, [x, y], limits, noise_limits=noise)
    np.testing.assert_allclose(actual, [.5, .25], rtol=0, atol=1e-14)
