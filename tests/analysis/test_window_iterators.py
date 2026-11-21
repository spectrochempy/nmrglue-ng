import numpy as np
import pytest

from nmrglue.analysis import analysisbase, peakpick


@pytest.mark.parametrize('indexed', [False, True])
@pytest.mark.parametrize('width, bounds', [
    (2, [(0,1), (0,2), (1,3), (2,4)]),
    (3, [(0,2), (0,3), (1,4), (2,4)]),
    (np.uint8(2), [(0,1), (0,2), (1,3), (2,4)]),
])
def test_partial_windows_have_integer_bounds_and_historical_centering(indexed, width, bounds):
    cls = analysisbase.ndwindow_index if indexed else analysisbase.ndwindow
    iterator = cls((4,), (width,))
    assert iter(iterator) is iterator
    for i, (start, stop) in enumerate(bounds):
        value = next(iterator)
        if indexed:
            center, slices = value
            assert center == (i,)
        else:
            slices = value
        np.testing.assert_array_equal(np.arange(4)[slices], np.arange(4)[start:stop])
    with pytest.raises(StopIteration):
        next(iterator)


@pytest.mark.parametrize('indexed', [False, True])
def test_uniform_windows_follow_numpy_row_major_order(indexed):
    cls = analysisbase.ndwindow_inside_index if indexed else analysisbase.ndwindow_inside
    data = np.arange(12).reshape(3, 4)
    iterator = cls(data.shape, (2, 2))
    starts = [(0,0), (0,1), (0,2), (1,0), (1,1), (1,2)]
    for y, x in starts:
        value = next(iterator)
        if indexed:
            start, slices = value
            assert start == (y, x)
        else:
            slices = value
        np.testing.assert_array_equal(data[slices], data[y:y+2, x:x+2])
    with pytest.raises(StopIteration):
        next(iterator)


@pytest.mark.parametrize('cls', [analysisbase.ndwindow, analysisbase.ndwindow_index])
def test_empty_partial_iterator(cls):
    assert list(cls((0, 4), (3, 3))) == []


def test_slow_threshold_locations_use_real_iterator():
    data = np.array([0., 1., 3., 1., 0., 2., 4., 2., 0.])
    assert peakpick.find_all_thres(data, .5, (1,)) == [(2,), (6,)]
    assert peakpick.find_all_nthres(-data, -.5, (1,)) == [(2,), (6,)]


@pytest.mark.parametrize('cls', [analysisbase.ndwindow, analysisbase.ndwindow_index,
                                analysisbase.ndwindow_inside, analysisbase.ndwindow_inside_index])
@pytest.mark.parametrize('width', [0, -1, 1.5, True])
def test_invalid_window_widths(cls, width):
    with pytest.raises(ValueError, match='positive integers'):
        cls((4,), (width,))
