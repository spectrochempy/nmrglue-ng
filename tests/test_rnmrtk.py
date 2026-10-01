"""Tests requiring the historical external RNMRTK reference files."""

import os

import nmrglue as ng
import numpy as np
import pytest

from setup import DATA_DIR


@pytest.mark.slow
def test_3d_time():
    """Read and preserve the real 3D time-domain RNMRTK reference."""
    dic, data = ng.rnmrtk.read(
        os.path.join(DATA_DIR, "rnmrtk_3d", "time_3d.sec"))
    assert data.shape == (128, 88, 1250)
    assert np.abs(data[0, 1, 2].real - 7.98) <= 0.01
    assert np.abs(data[0, 1, 2].imag - 33.82) <= 0.01
    assert np.abs(data[10, 11, 18].real - -9.36) <= 0.01
    assert np.abs(data[10, 11, 18].imag - -7.75) <= 0.01
    assert dic['sw'] == [5555.556, 2777.778, 50000.0]
    assert dic['sf'] == [125.68, 50.65, 125.68]
    assert dic['ppm'] == [56.0, 120.0, 56.0]


@pytest.mark.slow
def test_3d_freq():
    """Read and preserve the real 3D frequency-domain RNMRTK reference."""
    dic, data = ng.rnmrtk.read(
        os.path.join(DATA_DIR, "rnmrtk_3d", "freq_3d.sec"))
    assert data.shape == (128, 128, 4096)
    assert np.abs(data[0, 1, 2] - 3.23) <= 0.01
    assert np.abs(data[10, 11, 18] - 1.16) <= 0.01
    assert dic['sw'] == [5555.556, 2777.778, 50000.0]
    assert dic['sf'] == [125.68, 50.65, 125.68]
    assert dic['ppm'] == [56.0, 120.0, 56.0]
