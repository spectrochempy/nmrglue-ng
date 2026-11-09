import numpy as np
import pytest

from nmrglue.process.proc_autophase import autops


@pytest.mark.parametrize("size, center", [(256, 128), (256, 20), (256, 235), (11, 3)])
def test_peak_minima_handles_truncated_windows(size, center):
    x = np.arange(size) - center
    data = (1 / (1 + (x / 3) ** 2)).astype(complex)

    result, phases = autops(data, "peak_minima", disp=False, return_phases=True)

    assert result.shape == data.shape
    assert np.isfinite(result).all()
    assert np.isfinite(phases).all()


@pytest.mark.parametrize("center", [0, 10])
def test_peak_minima_rejects_endpoint_at_initial_phase(center):
    x = np.arange(11) - center
    data = (1 / (1 + (x / 3) ** 2)).astype(complex)

    with pytest.raises(ValueError, match="initial peak.*endpoint"):
        autops(data, "peak_minima", disp=False)


def test_peak_minima_requires_positive_width():
    with pytest.raises(ValueError, match="peak_width must be positive"):
        autops(np.array([0, 1, 0], dtype=complex), "peak_minima", peak_width=0)
