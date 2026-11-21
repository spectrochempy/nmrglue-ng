import numpy as np


import nmrglue as ng

def _gaussian_sum(grid, params, amplitudes):
    return sum(amplitude * np.exp(-4 * np.log(2) * ((grid - peak[0][0]) / peak[0][1])**2)
               for peak, amplitude in zip(params, amplitudes))


def test_fit_spectrum():
    lineshapes = ['g']
    params = [[(13797.0, 2.2495075273313034)],
              [(38979.0, 5.8705185693227664)],
              [(39066.0, 5.7125954296137103)],
              [(39153.0, 5.7791485451283791)],
              [(41649.0, 4.260242375400459)],
              [(49007.0, 4.2683625950679964)],
              [(54774.0, 3.2907139764685569)]]
    amps = [35083.008667, 32493.824402, 32716.156556, 33310.711914, 82682.928405,
            82876.544313, 85355.658142]
    grid = np.arange(65536.)
    clean = _gaussian_sum(grid, params, amps)
    spectrum = clean + np.random.default_rng(0).normal(0., .1, grid.size)
    guesses = [[(peak[0][0] + .3, peak[0][1] * 1.15)] for peak in params]
    amp_guesses = np.asarray(amps) * .8
    bounds = [[[(None, None), (0, None)]], [[(None, None), (0, None)]],
              [[(None, None), (0, None)]], [[(None, None), (0, None)]],
              [[(None, None), (0, None)]], [[(None, None), (0, None)]],
              [[(None, None), (0, None)]]]
    ampbounds = [None, None, None, None, None, None, None]
    centers = [(13797.0,), (38979.0,), (39066.0,), (39153.0,), (41649.0,),
               (49007.0,), (54774.0,)]
    rIDs = [1, 2, 3, 4, 5, 6, 7]
    box_width = (5,)
    error_flag = False

    params_best, amp_best, iers = ng.linesh.fit_spectrum(
        spectrum, lineshapes, guesses, amp_guesses, bounds, ampbounds, centers,
        rIDs, box_width, error_flag, verb=False)
    assert len(iers) == len(params)
    assert set(iers) <= {1, 2, 3, 4}
    np.testing.assert_allclose(params_best, params, rtol=0, atol=1e-3)
    np.testing.assert_allclose(amp_best, amps, rtol=1e-4, atol=0)
    fitted = _gaussian_sum(grid, params_best, amp_best)
    residual_rms = np.sqrt(np.mean((spectrum - fitted)**2))
    assert .095 < residual_rms < .105
