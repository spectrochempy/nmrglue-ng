import numpy as np
import pytest

from nmrglue.process import proc_autophase


@pytest.mark.parametrize('data', [
    np.array([], complex), np.ones(1, complex), np.zeros(8, complex),
    np.ones(8, complex), np.full(8, 1.+2j),
    np.array([1., np.nan, 2.], complex), np.array([1., np.inf, 2.], complex),
])
def test_acme_rejects_degenerate_input_before_solver(data, monkeypatch):
    def unexpected_solver(*args, **kwargs):
        pytest.fail('degenerate ACME input reached the optimizer')
    monkeypatch.setattr(proc_autophase.scipy.optimize, 'fmin', unexpected_solver)
    with pytest.raises(ValueError, match='finite.*variation'):
        proc_autophase.autops(data, 'acme', disp=False)


def test_custom_score_remains_responsible_for_its_own_input_contract():
    data = np.zeros(8, complex)
    def score(angles, spectrum):
        return np.sum(np.asarray(angles)**2)
    result, phases = proc_autophase.autops(data, score, disp=False, return_phases=True)
    np.testing.assert_array_equal(result, data)
    np.testing.assert_array_equal(phases, [0., 0.])
