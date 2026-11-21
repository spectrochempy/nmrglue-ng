import numpy as np
import pytest

from nmrglue.fileio import bruker


@pytest.mark.parametrize("exponent", [-1071, -1000, -40, 0, 28, 29, 40, 1000, 1023])
def test_normalization_preserves_signed_ratios_across_dynamic_range(exponent):
    data = np.ldexp(np.array([1., -.5, 0., .25]), exponent)
    original = data.copy()
    data.setflags(write=False)
    expected_peak = 2 ** (29 if exponent == 29 else 28)
    result = bruker.array_to_int(data)
    np.testing.assert_array_equal(result, [expected_peak, -expected_peak // 2,
                                          0, expected_peak // 4])
    np.testing.assert_array_equal(data, original)
    assert result.dtype == np.dtype('int32')


@pytest.mark.parametrize("dtype", [np.int32, np.float32, np.float64])
def test_zero_and_empty_arrays(dtype):
    for shape in [(2, 3), (0,)]:
        data = np.zeros(shape, dtype=dtype)
        result = bruker.array_to_int(data)
        np.testing.assert_array_equal(result, data)
        assert result.dtype == np.dtype('int32')


def test_int32_minimum_and_noncontiguous_input():
    data = np.array([-2**31, 0, 2**30, 0], dtype=np.int32)[::2]
    original = data.copy()
    result = bruker.array_to_int(data)
    np.testing.assert_array_equal(result, [-2**28, 2**27])
    np.testing.assert_array_equal(data, original)


@pytest.mark.parametrize("value", [np.nextafter(0., 1.), np.finfo(float).max])
def test_extreme_finite_singletons(value):
    result = bruker.array_to_int(np.array([value]))
    assert 2**28 <= result[0] <= 2**29
    assert result[0] > 0


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_values_are_rejected(value):
    with pytest.raises(ValueError, match="finite"):
        bruker.array_to_int(np.array([1., value]))


@pytest.mark.parametrize("exponent", [-40, 40])
@pytest.mark.parametrize("shape", [(4,), (2, 2)])
@pytest.mark.parametrize("big", [False, True])
def test_pdata_writer_roundtrip_dynamic_range(tmp_path, exponent, shape, big):
    data = np.ldexp(np.array([1., -.5, 0., .25]), exponent).reshape(shape)
    dic = {'procs': {'NC_proc': 0}}
    bruker.write_pdata(str(tmp_path), dic, data, shape=shape,
                       submatrix_shape=shape, big=big, isfloat=False)
    _, result = bruker.read_binary(tmp_path / (str(len(shape)) + 'r' * len(shape)),
                                   shape=shape, cplex=False, big=big)
    expected = np.array([2**28, -2**27, 0, 2**26], dtype=np.int32).reshape(shape)
    np.testing.assert_array_equal(result, expected)
