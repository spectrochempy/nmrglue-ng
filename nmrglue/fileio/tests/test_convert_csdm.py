"""Self-contained tests for conversion to CSDM."""

import numpy as np
from numpy.testing import assert_array_equal
import pytest

import nmrglue as ng


AXIS_PARAMETERS = (
    {"sw": 800.0, "obs": 400.0, "car": 1200.0, "label": "1H"},
    {"sw": 1200.0, "obs": 100.0, "car": -350.0, "label": "15N"},
    {"sw": 2400.0, "obs": 60.0, "car": 75.0, "label": "13C"},
)


def _synthetic_input(shape):
    """Return an independently constructed universal dictionary and data."""
    udic = {"ndim": len(shape)}
    for index, size in enumerate(shape):
        udic[index] = {
            "size": size,
            "complex": True,
            "time": True,
            "freq": False,
            "encoding": "direct" if index == len(shape) - 1 else "states",
            **AXIS_PARAMETERS[index],
        }

    values = np.arange(np.prod(shape), dtype=np.float64).reshape(shape)
    data = (values + 1j * (1000.0 + 7.0 * values)).astype(np.complex128)
    return udic, data


def _to_csdm(udic, data, freq_dims=None):
    pytest.importorskip("csdmpy")
    converter = ng.convert.converter()
    converter.from_universal(udic, data)
    return converter.to_csdm(freq_dims=freq_dims)


def _assert_common(csdm_data, expected_data, ndim):
    assert len(csdm_data.dimensions) == ndim
    assert len(csdm_data.dependent_variables) == 1

    component = csdm_data.dependent_variables[0].components[0]
    assert component.shape == expected_data.shape
    assert component.dtype == expected_data.dtype
    assert_array_equal(component, expected_data)


def _assert_time_dimension(dimension, parameters):
    assert dimension.count == parameters["size"]
    assert np.isclose(dimension.increment.value, 1.0 / parameters["sw"])
    assert str(dimension.increment.unit) == "s"
    assert np.isclose(
        dimension.reciprocal.coordinates_offset.value,
        parameters["car"],
    )
    assert str(dimension.reciprocal.coordinates_offset.unit) == "Hz"
    assert dimension.reciprocal.origin_offset.value == parameters["obs"]
    assert dimension.label == parameters["label"]


def _assert_frequency_dimension(dimension, parameters):
    assert dimension.count == parameters["size"]
    assert np.isclose(
        dimension.increment.value,
        parameters["sw"] / parameters["size"],
    )
    assert str(dimension.increment.unit) == "Hz"
    assert dimension.origin_offset.value == parameters["obs"]
    assert str(dimension.reciprocal.quantity_name) == "time"
    assert dimension.label == parameters["label"]


def _assert_all_time_dimensions(csdm_data, udic):
    for udic_index in range(udic["ndim"]):
        csdm_index = udic["ndim"] - udic_index - 1
        _assert_time_dimension(csdm_data.dimensions[csdm_index], udic[udic_index])


def test_csdm_1d():
    """Convert distinctive complex 1D data in time and frequency domains."""
    udic, data = _synthetic_input((8,))

    time_data = _to_csdm(udic, data)
    _assert_common(time_data, data, ndim=1)
    _assert_all_time_dimensions(time_data, udic)

    frequency_data = _to_csdm(udic, data, freq_dims=[True])
    _assert_common(frequency_data, data[::-1], ndim=1)
    _assert_frequency_dimension(frequency_data.dimensions[0], udic[0])


def test_csdm_2d():
    """Preserve 2D axis order and reverse only the frequency-domain axis."""
    udic, data = _synthetic_input((3, 8))

    time_data = _to_csdm(udic, data)
    _assert_common(time_data, data, ndim=2)
    _assert_all_time_dimensions(time_data, udic)

    mixed_data = _to_csdm(udic, data, freq_dims=[False, True])
    _assert_common(mixed_data, np.flip(data, axis=1), ndim=2)
    _assert_frequency_dimension(mixed_data.dimensions[0], udic[1])
    _assert_time_dimension(mixed_data.dimensions[1], udic[0])


def test_csdm_3d():
    """Preserve complex values and explicit axis order in three dimensions."""
    udic, data = _synthetic_input((2, 3, 8))

    csdm_data = _to_csdm(udic, data)
    _assert_common(csdm_data, data, ndim=3)
    _assert_all_time_dimensions(csdm_data, udic)
