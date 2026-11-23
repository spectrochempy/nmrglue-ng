"""Explicit point anchors distinguish reference and observation frequencies."""

from copy import deepcopy

import numpy as np
import pytest

from nmrglue import interop
from test_jcampdx_topspin_processed import SPECTRUM


REFERENCES = {
    "F1": {
        "reference_frequency_mhz": 100.0,
        "point_index": 1,
        "ppm": 8.0,
        "source": "processing",
    },
    "F2": {
        "reference_frequency_mhz": 400.0,
        "point_index": 2,
        "ppm": -1.0,
        "source": "processing",
    },
}


def _read(tmp_path, contents=SPECTRUM):
    path = tmp_path / "spectrum.dx"
    path.write_text(
        contents.replace("##NTUPLES=", "##.OBSERVE FREQUENCY=399\n##NTUPLES=")
    )
    return interop.read(path, profile="jcampdx-spectrum-2d")


def test_explicit_two_axis_anchors_preserve_data_and_default(tmp_path):
    source = _read(tmp_path)
    before = source.data.copy()
    references = deepcopy(REFERENCES)
    result = interop.normalize(source, axis_reference=references)
    np.testing.assert_allclose(
        result.axes[0].values, [8.025, 8, 7.975], rtol=0, atol=1e-14
    )
    np.testing.assert_allclose(
        result.axes[1].values, [-0.99, -0.995, -1, -1.005], rtol=0, atol=1e-14
    )
    assert tuple(axis.unit for axis in result.axes) == ("ppm", "ppm")
    assert result.axes[0].reference.observation_frequency == 100
    assert result.axes[1].reference.observation_frequency == 400
    assert result.axes[0].reference.offset == result.axes[0].values[0]
    assert result.axes[0].reference.source == "processing"
    assert result.acquisition["axis_reference"]["F2"]["point_index"] == 2
    assert len(result.applied_operations) == 3
    assert (
        result.applied_operations[-1]["coordinate_reference"]["reference_frequency_mhz"]
        == 400
    )
    np.testing.assert_array_equal(result.data, before)
    np.testing.assert_array_equal(source.data, before)
    references["F1"]["ppm"] = 999
    assert result.acquisition["axis_reference"]["F1"]["ppm"] == 8
    default = interop.normalize(source)
    assert tuple(axis.unit for axis in default.axes) == ("Hz", "Hz")
    np.testing.assert_array_equal(default.axes[0].values, source.axes[0].values)
    assert default.acquisition == {}


@pytest.mark.parametrize("axis", ["F1", "F2"])
@pytest.mark.parametrize(
    "key,value",
    [
        ("reference_frequency_mhz", True),
        ("reference_frequency_mhz", 0),
        ("reference_frequency_mhz", -1),
        ("reference_frequency_mhz", np.nan),
        ("reference_frequency_mhz", np.inf),
        ("reference_frequency_mhz", "400"),
        ("reference_frequency_mhz", 1e-320),
        ("point_index", True),
        ("point_index", 1.0),
        ("point_index", -1),
        ("point_index", 4),
        ("ppm", True),
        ("ppm", np.inf),
        ("ppm", "8"),
        ("source", "auto"),
        ("extra", "x"),
    ],
)
def test_invalid_reference_fields_are_rejected(tmp_path, axis, key, value):
    source = _read(tmp_path)
    refs = deepcopy(REFERENCES)
    refs[axis][key] = value
    with pytest.raises(ValueError):
        interop.normalize(source, axis_reference=refs)


@pytest.mark.parametrize(
    "reference", [{}, {"F1": REFERENCES["F1"]}, False, [], {"F1": None, "F2": None}]
)
def test_requires_both_explicit_axis_mappings(tmp_path, reference):
    with pytest.raises(ValueError):
        interop.normalize(_read(tmp_path), axis_reference=reference)


def test_does_not_reinterpret_an_existing_ppm_axis(tmp_path):
    source = _read(tmp_path, SPECTRUM.replace("HZ,HZ", "PPM,HZ"))
    with pytest.raises(ValueError, match="Hz"):
        interop.normalize(source, axis_reference=REFERENCES)


@pytest.mark.parametrize(
    "key,value", [("ppm", 1e300), ("reference_frequency_mhz", 1e300)]
)
def test_rejects_precision_collapse(tmp_path, key, value):
    refs = deepcopy(REFERENCES)
    refs["F1"][key] = value
    with pytest.raises(ValueError, match="monotonic"):
        interop.normalize(_read(tmp_path), axis_reference=refs)


def test_increasing_grids_and_default_source(tmp_path):
    contents = (
        SPECTRUM.replace("10.12345679", "-10.12345679")
        .replace("7.62345679", "-7.62345679")
        .replace("5.12345679", "-5.12345679")
    )
    # Reverse F1 signs in all metadata/PAGE records without touching intensities.
    contents = contents.replace("10.123456789", "-10.123456789").replace("5.123456789", "-5.123456789")
    source = _read(tmp_path, contents)
    refs = deepcopy(REFERENCES)
    for spec in refs.values():
        spec.pop("source")
        spec["point_index"] = np.int64(spec["point_index"])
        spec["reference_frequency_mhz"] = np.float64(spec["reference_frequency_mhz"])
    result = interop.normalize(source, axis_reference=refs)
    np.testing.assert_allclose(
        result.axes[0].values, [7.975, 8, 8.025], rtol=0, atol=1e-14
    )
    assert result.axes[0].direction == "increasing"
    assert result.axes[0].reference.source == "unknown"
    np.testing.assert_array_equal(result.data, source.data)
