import numpy as np
import pytest

from nmrglue.process.proc_base import expand_nus


@pytest.mark.parametrize('dtype, coordinate', [
    (np.int8, 100), (np.uint8, 200), (np.int16, 20000), (np.uint16, 40000),
])
@pytest.mark.parametrize('numpy_branches', [False, True])
def test_narrow_coordinate_uses_full_python_integer_index(dtype, coordinate, numpy_branches):
    data = np.array([[1.+2j], [3.+4j]])
    branches = np.array([[1], [0]], dtype=np.uint8) if numpy_branches else [(1,), (0,)]
    result = expand_nus(data, (2 * coordinate + 2, 1),
                        np.array([[coordinate]], dtype=dtype), quadrature_order=branches)
    np.testing.assert_array_equal(result[2 * coordinate], data[1])
    np.testing.assert_array_equal(result[2 * coordinate + 1], data[0])
    assert np.count_nonzero(result) == 2
