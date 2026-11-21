import numpy as np
import pytest

from nmrglue.analysis import peakpick


@pytest.mark.parametrize('algorithm', ['thres', 'thres-fast'])
@pytest.mark.parametrize('ndim', [1, 2])
def test_negative_threshold_peaks_preserve_location_width_and_signed_volume(algorithm, ndim,
                                                                         monkeypatch):
    if ndim == 1:
        positive = np.array([0., 1., 3., 1., 0.])
        location, widths, volume = (2,), (1.5,), -5.
        windows = [((i,), (slice(max(0, i-1), min(5, i+2)),)) for i in range(5)]
    else:
        positive = np.outer([0., 1., 3., 1., 0.], [0., 2., 4., 2., 0.])
        location, widths, volume = (2, 2), (1.5, 2.), -40.
        windows = [((i,j), (slice(max(0,i-1),min(5,i+2)),
                           slice(max(0,j-1),min(5,j+2))))
                   for i in range(5) for j in range(5)]
    if algorithm == 'thres':
        monkeypatch.setattr(peakpick, 'ndwindow_index', lambda shape, size: iter(windows))
    locations, scales, amps = peakpick.pick(
        -positive, None, -.5, msep=(1,) * ndim, algorithm=algorithm,
        table=False, cluster=False)
    assert locations == [location]
    np.testing.assert_allclose(scales, [widths], rtol=0, atol=1e-14)
    np.testing.assert_array_equal(amps, [volume])


def test_negative_segments_match_positive_signal_segments():
    data = np.array([0., 1., 3., 1., 0., 0., 2., 4., 2., 0.])
    positive = peakpick.find_all_thres_fast(data, .5, (1,), True)
    negative = peakpick.find_all_nthres_fast(-data, -.5, (1,), True)
    assert positive == negative == ([(2,), (7,)], [(slice(1,4),), (slice(6,9),)])
