import numpy as np
import pytest

from nmrglue.process import proc_bl


@pytest.mark.parametrize('width, left, right', [(1, .5, 6.5), (2, 1., 6.)])
@pytest.mark.parametrize('complex_data', [False, True])
def test_edge_node_averages_use_available_samples(width, left, right, complex_data):
    factor = 1.+2j if complex_data else 1.
    data = np.arange(8.) * factor
    original = data.copy()
    expected = np.linspace(left, right, 8) * factor
    result = proc_bl.calc_bl_linear(data, [0, 7], nw=width)
    np.testing.assert_allclose(result, expected, rtol=0, atol=2e-15)
    np.testing.assert_array_equal(data, original)


def test_corrected_ramp_matches_nmrpipe_edge_nodes():
    """NMRPipe 13.0 Rev 2026.072.12.03: BASE -nl 1 8 -nw 1 on float32 arange(8)."""
    data = np.arange(8.)
    expected = [-.5, -.35714293, -.21428585, -.07142878,
                .0714283, .21428537, .35714245, .5]
    result = proc_bl.base(data, [0, 7], nw=1)
    np.testing.assert_allclose(result, expected, rtol=0, atol=6e-7)


def test_two_dimensional_tracewise_baseline():
    x = np.arange(8.)
    corrected = x - np.linspace(.5, 6.5, 8)
    data = np.stack([x, 3*x+5])
    np.testing.assert_allclose(proc_bl.base(data, [0, 7], nw=1),
                               np.stack([corrected, 3*corrected]), rtol=0, atol=4e-15)


def test_wide_averaging_window_and_noncontiguous_input():
    data = np.arange(16.)[::2]
    np.testing.assert_array_equal(proc_bl.calc_bl_linear(data, [0, 7], nw=100),
                                  np.full(8, 7.))
