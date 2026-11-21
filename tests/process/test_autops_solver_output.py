import numpy as np
import pytest

from nmrglue.process.proc_autophase import autops


@pytest.mark.parametrize('full_output, retall', [(False, False), (True, False),
                                              (False, True), (True, True)])
@pytest.mark.parametrize('return_phases', [False, True])
def test_solver_diagnostics_do_not_change_autops_return_contract(full_output, retall, return_phases):
    data = np.linspace(1., 2., 64).astype(complex)
    original = data.copy()
    target = np.array([30., -20.])

    def score(angles, spectrum):
        return np.sum((angles - target)**2)

    result = autops(data, score, full_output=full_output, retall=retall,
                    return_phases=return_phases, disp=False, xtol=1e-9, ftol=1e-9)
    if return_phases:
        result, angles = result
        assert angles.shape == (2,)
        np.testing.assert_allclose(angles, target, rtol=0, atol=1e-6)
    expected = data * np.exp(1j * np.deg2rad(30. - 20. * np.arange(64) / 64))
    np.testing.assert_allclose(result, expected, rtol=0, atol=1e-7)
    np.testing.assert_array_equal(data, original)
