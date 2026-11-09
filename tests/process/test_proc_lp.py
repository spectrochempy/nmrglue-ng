import numpy as np
import pytest

import nmrglue as ng


def test_find_lpc_qr():
    D = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
        ],
        dtype=np.float64,
    )
    d = np.array([[1.0], [2.0], [3.0]], dtype=np.float64)

    result = ng.proc_lp.find_lpc_qr(D, d)

    assert result.shape == (2, 1)
    assert result.dtype == np.dtype("float64")
    np.testing.assert_allclose(result, [[1.0], [2.0]], rtol=1e-14, atol=1e-14)


@pytest.mark.parametrize(
    ("mode", "append"),
    [
        ("f", "after"),
        ("b", "before"),
    ],
)
def test_lp_qr_complex_signal(mode, append):
    poles = np.array(
        [
            np.exp(-0.04 + 2j * np.pi * 0.12),
            np.exp(-0.08 - 2j * np.pi * 0.21),
        ]
    )
    amplitudes = np.array([1.0 + 0.2j, 0.35 - 0.1j])
    pred = 4

    def signal(points):
        return np.sum(
            amplitudes[:, None] * poles[:, None] ** points,
            axis=0,
        )

    trace = signal(np.arange(16)).astype(np.complex128)
    if append == "after":
        expected = signal(np.arange(trace.size + pred))
    else:
        expected = signal(np.arange(-pred, trace.size))

    result = ng.proc_lp.lp_qr(
        trace, pred=pred, order=2, mode=mode, append=append, bad_roots=None
    )

    assert result.shape == (trace.size + pred,)
    assert result.dtype == np.dtype("complex128")
    np.testing.assert_allclose(result, expected, rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("min_var", [False, True])
def test_cadzow_2d_matches_independent_1d_rows(min_var):
    rng = np.random.default_rng(945)
    data = (rng.normal(size=(3, 32)) + 1j * rng.normal(size=(3, 32)))[:, ::2]
    original = data.copy()
    expected = np.stack([
        ng.proc_lp.cadzow(row, M=6, K=2, niter=2, min_var=min_var)
        for row in original
    ])

    result = ng.proc_lp.cadzow(data, M=6, K=2, niter=2, min_var=min_var)

    np.testing.assert_array_equal(data, original)
    assert result.dtype == original.dtype
    assert not np.allclose(result, original)
    np.testing.assert_allclose(result, expected, rtol=1e-12, atol=1e-12)


def test_cadzow_2d_matrix_rows_are_processed_as_1d():
    data = np.asmatrix([[1., 2., 3.], [4., 5., 6.]])
    expected = np.stack([
        ng.proc_lp.cadzow(row, M=2, K=1, niter=1)
        for row in np.asarray(data)
    ])

    result = ng.proc_lp.cadzow(data, M=2, K=1, niter=1)

    assert isinstance(result, type(data))
    np.testing.assert_allclose(result, expected)
