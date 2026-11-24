import warnings

import numpy as np
import pytest

from nmrglue.process.proc_autophase import _ps_acme_score, autops
from nmrglue.process.proc_base import ps


@pytest.mark.parametrize("data", [
    1j * np.array([0., 1., 2., 1., 0.]),
    np.array([-1e308, 1e308, 0], dtype=complex),
    np.array([0., 1e-320, 2e-320, 0.], dtype=complex),
])
def test_autops_rejects_nonfinite_initial_acme_score_without_runtime_warnings(data):
    original = data.copy()
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        assert _ps_acme_score([0, 0], data) == np.inf
        with pytest.raises(ValueError, match="finite initial score.*phases.*rescale"):
            autops(data, "acme", disp=False)
    np.testing.assert_array_equal(data, original)


def test_imaginary_spectrum_accepts_an_identifiable_initial_projection():
    data = 1j * np.array([0., 1., 2., 1., 0.])
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        result, angles = autops(data, "acme", p0=-90, return_phases=True, disp=False)
    assert np.isfinite(angles).all()
    np.testing.assert_allclose(result.real, data.imag, atol=1e-5)


@pytest.mark.parametrize("amplitude", [1e-3, 1., 1e3])
@pytest.mark.parametrize("angles", [(0, 0), (35, -80), (180, 0)])
def test_finite_acme_score_matches_historical_expression(amplitude, angles):
    points = np.arange(128)
    data = amplitude / (1 + 1j * (points - 51) / 6)
    real = ps(data, p0=angles[0], p1=angles[1]).real
    derivative = abs(np.diff(real) / 2)
    probability = derivative / sum(derivative)
    probability[probability == 0] = 1
    entropy = sum(-probability * np.log(probability))
    penalty = sum(np.minimum(real, 0)**2)
    expected = (entropy + 1000 * penalty) / len(real) / max(real)
    assert _ps_acme_score(angles, data) == pytest.approx(expected, rel=2e-14)


def test_acme_rejects_nonfinite_trial_and_final_scores(monkeypatch):
    import nmrglue.process.proc_autophase as module

    data = 1j * np.array([0., 1., 2., 1., 0.])

    def optimizer(score, x0, args, **kwargs):
        assert np.isfinite(score(x0, *args))
        assert score([0, 0], *args) == np.inf
        return np.array([0., 0.])

    monkeypatch.setattr(module.scipy.optimize, "fmin", optimizer)
    with pytest.raises(ValueError, match="did not produce a finite score"):
        autops(data, "acme", p0=-90, disp=False)


def test_custom_score_is_not_subject_to_acme_initial_projection_guard():
    data = 1j * np.array([0., 1., 2., 1., 0.])
    result = autops(data, lambda angles, data: np.sum(np.asarray(angles)**2), disp=False)
    np.testing.assert_array_equal(result, data)
