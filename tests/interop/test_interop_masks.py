"""Exercise the interop constructors before ndarray coercion."""

import numpy as np
import pytest

from nmrglue import interop


def _read_result(data):
    return interop.ReadResult(
        data=data,
        axes=(),
        metadata={},
        components=(),
        applied_corrections={},
        diagnostics=(),
        format="test",
        source="test",
    ).data


def _normalized_data(data):
    return interop.NormalizedAcquisition(
        data=data,
        axes=(interop.Axis(),),
        dimensions=("F2",),
        physical_dimensions=("F2",),
        domains=("time",),
        quadrature_mode="complex-1d",
        branch_order=("complex",),
        normalization_state="storage-normalized",
        normalization_profile="test",
        applied_operations=(),
        provenance={},
        acquisition={},
    ).data


@pytest.mark.parametrize(
    ("convert", "field", "dtype"),
    [
        (lambda a: interop.Axis(values=a).values, "axis values", float),
        (lambda a: interop.Component("complex", a).data, "component data", complex),
        (_read_result, "reader data", complex),
        (_normalized_data, "acquisition data", complex),
    ],
)
@pytest.mark.parametrize("mask", [True, [False, True, False], False, np.ma.nomask])
def test_interop_array_mask_boundary(convert, field, dtype, mask):
    values = np.arange(3, dtype=dtype)
    samples = np.ma.array(values, mask=mask)
    if np.ma.is_masked(samples):
        with pytest.raises(ValueError, match=f"{field} must be unmasked"):
            convert(samples)
    else:
        result = convert(samples)
        assert type(result) is np.ndarray
        assert not result.flags.writeable
        np.testing.assert_array_equal(result, values)


@pytest.mark.parametrize("active", [False, True])
def test_interop_structured_mask_boundary(active):
    values = np.array([(1, 2), (3, 4)], dtype=[("a", "i8"), ("b", "i8")])
    samples = np.ma.array(values, mask=False)
    samples.mask["b"][0] = active
    if active:
        with pytest.raises(ValueError, match="axis values must be unmasked"):
            interop.Axis(values=samples)
    else:
        result = interop.Axis(values=samples).values
        assert not result.flags.writeable
        np.testing.assert_array_equal(result, values)
