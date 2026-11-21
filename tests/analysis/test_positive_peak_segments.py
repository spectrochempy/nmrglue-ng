import numpy as np
import pytest

from nmrglue.analysis import peakpick


@pytest.mark.parametrize("data, expected_locations, expected_slices", [
    (np.array([0., 2., 5., 2., 0., 3., 8., 3., 0.]),
     [(2,), (6,)], [(slice(1, 4),), (slice(5, 8),)]),
    (np.array([[0., 0., 0., 0., 0., 0., 0.],
               [0., 2., 0., 0., 0., 3., 0.],
               [2., 5., 2., 0., 3., 8., 3.],
               [0., 2., 0., 0., 0., 3., 0.],
               [0., 0., 0., 0., 0., 0., 0.]]),
     [(2, 1), (2, 5)],
     [(slice(1, 4), slice(0, 3)), (slice(1, 4), slice(4, 7))]),
    (np.zeros(5), [], []),
])
def test_positive_slow_segments_match_peak_locations(data, expected_locations,
                                                     expected_slices):
    separation = (1,) * data.ndim
    locations, slices = peakpick.find_all_thres(data, 1., separation, True)
    assert locations == expected_locations
    assert slices == expected_slices
    assert peakpick.find_all_thres_fast(data, 1., separation, True) == (locations, slices)
    assert peakpick.find_all_thres(data, 1., separation, False) == locations
