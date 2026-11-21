import numpy as np
import pytest

from nmrglue.process.proc_base import expand_nus


@pytest.mark.parametrize(
    "options",
    [
        {"nuslist": []},
        {"nuslist": [()]},
        {"nuslist": [(0,), (0,)]},
        {"nuslist": [(-1,), (0,)]},
        {"nuslist": [(0,), (2,)]},
        {"nuslist": [(0,), (1, 0)]},
        {"nuslist": [(0.,), (1.,)]},
        {"nuslist": [(False,), (True,)]},
        {"data": np.ones((5, 3))},
        {"data": np.ones((3, 3))},
        {"data": np.ones((4, 2))},
        {"data": np.ones((4, 1, 3))},
        {"shape": (4., 3)},
        {"shape": (0, 3)},
        {"shape": (4, -3)},
        {"shape": (4, True)},
        {"shape": (4, 3, 2)},
        {"aqorder": []},
        {"aqorder": [0, 0]},
        {"aqorder": [-1]},
        {"aqorder": [0.]},
        {"quadrature_order": []},
        {"quadrature_order": [(0,), (0,)]},
        {"quadrature_order": [(0,), (2,)]},
        {"quadrature_order": [(0,), (1.,)]},
        {"quadrature_order": [(0, 1), (1, 0)]},
    ],
)
def test_invalid_geometry_is_rejected_before_allocation(options, monkeypatch):
    arguments = dict(data=np.arange(12.).reshape(4, 3), shape=(4, 3),
                     nuslist=[(0,), (1,)])
    arguments.update(options)
    original = arguments["data"].copy()

    def unexpected_allocation(*args, **kwargs):
        pytest.fail("invalid geometry reached output allocation")

    monkeypatch.setattr(np, "zeros", unexpected_allocation)
    with pytest.raises(ValueError):
        expand_nus(**arguments)
    np.testing.assert_array_equal(arguments["data"], original)


def test_custom_orders_preserve_complex_traces_and_zero_unsampled_points():
    data = (np.arange(16).reshape(8, 2) + 1j).astype(np.complex64)
    original = data.copy()
    result = expand_nus(
        data, (4, 6, 2), [(2, 0), (0, 1)], aqorder=[1, 0],
        quadrature_order=[(1, 1), (0, 1), (1, 0), (0, 0)],
    )
    expected = np.zeros((4, 6, 2), dtype=np.complex64)
    expected[1, 5], expected[0, 5] = original[0], original[1]
    expected[1, 4], expected[0, 4] = original[2], original[3]
    expected[3, 1], expected[2, 1] = original[4], original[5]
    expected[3, 0], expected[2, 0] = original[6], original[7]
    np.testing.assert_array_equal(result, expected)
    np.testing.assert_array_equal(data, original)
    assert result.dtype == data.dtype


def test_numpy_integer_geometry():
    data = np.arange(12).reshape(4, 3)
    result = expand_nus(data, np.array([4, 3]), np.array([[1], [0]]),
                        aqorder=np.array([0]),
                        quadrature_order=np.array([[0], [1]]))
    np.testing.assert_array_equal(result, data[[2, 3, 0, 1]])
