"""Normalized processed spectra preserve components, scaling and references."""

from dataclasses import replace

import numpy as np
import pytest
import nmrglue as ng

from test_interop_bruker_pdata import _write_pdata


def _result(tmp_path, *, complex_data=True, scaled=True, missing_imaginary=False):
    components = {"1r": [100, 200, 300, 400]}
    if complex_data and not missing_imaginary:
        components["1i"] = [40, 30, 20, 10]
    source = _write_pdata(tmp_path, component_values=components, nc_proc=-2)
    return ng.interop.read_bruker_pdata(source, all_components=complex_data, scale_data=scaled)


@pytest.mark.parametrize("complex_data", [False, True])
@pytest.mark.parametrize("scaled", [False, True])
def test_normalize_preserves_reader_values_and_processing_grid(tmp_path, complex_data, scaled):
    raw = _result(tmp_path, complex_data=complex_data, scaled=scaled)
    before = raw.data.copy()
    result = ng.interop.normalize_bruker_pdata(raw)
    factor = 0.25 if scaled else 1
    expected = np.array([100, 200, 300, 400]) * factor
    if complex_data:
        expected = expected + 1j * np.array([40, 30, 20, 10]) * factor
    np.testing.assert_array_equal(result.data, expected)
    assert np.iscomplexobj(result.data) is complex_data
    assert result.domains == ("frequency",)
    assert result.quadrature_mode == ("complex-1d" if complex_data else "real-1d")
    assert result.branch_order == (("complex",) if complex_data else ("real",))
    np.testing.assert_array_equal(result.axes[0].values, [4000, 3000, 2000, 1000])
    assert result.axes[0].reference.source == "processing"
    assert result.axes[0].reference.observation_frequency == 400
    assert result.acquisition["storage_scaling"] == dict(raw.applied_corrections)
    assert result.applied_operations[0]["scale"] is None
    assert result.applied_operations[0]["conjugation"] == "none"
    assert not result.data.flags.writeable
    assert not np.shares_memory(result.data, raw.data)
    np.testing.assert_array_equal(raw.data, before)


def test_missing_imaginary_component_remains_real_with_diagnostic(tmp_path):
    raw = _result(tmp_path, complex_data=True, missing_imaginary=True)
    result = ng.interop.normalize_bruker_pdata(raw)
    assert not np.iscomplexobj(result.data)
    assert result.branch_order == ("real",)
    assert any(item.code == "component.missing" for item in result.diagnostics)
    assert result.applied_operations[0]["source_components"] == ("1r",)


def test_component_association_does_not_depend_on_order(tmp_path):
    raw = _result(tmp_path)
    swapped = replace(raw, components=tuple(reversed(raw.components)))
    np.testing.assert_array_equal(ng.interop.normalize_bruker_pdata(swapped).data, ng.interop.normalize_bruker_pdata(raw).data)


@pytest.mark.parametrize("change", ["format", "complex_primary", "missing", "duplicate", "shape", "axis", "reference", "unknown_scaling", "missing_exponent", "wrong_exponent", "unexpected_exponent"])
def test_inconsistent_contract_refuses_without_mutation(tmp_path, change):
    raw = _result(tmp_path)
    if change == "format":
        raw = replace(raw, format="bruker-fid")
    elif change == "complex_primary":
        raw = replace(raw, data=raw.data.astype(complex))
    elif change == "missing":
        raw = replace(raw, components=raw.components[1:])
    elif change == "duplicate":
        raw = replace(raw, components=(raw.components[0], raw.components[0]))
    elif change == "shape":
        raw = replace(raw, components=(raw.components[0], ng.interop.Component("1i", np.ones(3))))
    elif change == "axis":
        raw = replace(raw, axes=(replace(raw.axes[0], values=np.arange(4)),))
    elif change == "reference":
        raw = replace(raw, axes=(replace(raw.axes[0], reference=replace(raw.axes[0].reference, source="acquisition")),))
    elif change == "unknown_scaling":
        raw = replace(raw, applied_corrections={"scale_data": True, "NC_proc": -2, "RG": 40})
    elif change == "missing_exponent":
        raw = replace(raw, applied_corrections={"scale_data": True})
    elif change == "wrong_exponent":
        raw = replace(raw, applied_corrections={"scale_data": True, "NC_proc": -3})
    else:
        raw = replace(raw, applied_corrections={"scale_data": False, "NC_proc": -2})
    before = raw.data.copy()
    with pytest.raises(ValueError):
        ng.interop.normalize_bruker_pdata(raw)
    np.testing.assert_array_equal(raw.data, before)


def test_unknown_calibration_is_not_promoted_to_normalized_frequency(tmp_path):
    source = _write_pdata(tmp_path, omit=("SF",))
    raw = ng.interop.read_bruker_pdata(source)
    with pytest.raises(ValueError, match="calibration"):
        ng.interop.normalize_bruker_pdata(raw)


def test_real_quadrature_mode_requires_real_samples_and_branch(tmp_path):
    result = ng.interop.normalize_bruker_pdata(_result(tmp_path, complex_data=False))
    with pytest.raises(ValueError, match="real-1d"):
        replace(result, data=result.data.astype(complex))
    with pytest.raises(ValueError, match="real branch"):
        replace(result, branch_order=("complex",))


@pytest.mark.parametrize("key, value", [("SI", None), ("SI", 8), ("STSI", 2), ("STSR", 1)])
def test_incomplete_or_extracted_grids_are_not_promoted(tmp_path, key, value):
    raw = _result(tmp_path)
    metadata = dict(raw.metadata)
    metadata["procs"] = {**metadata["procs"], key: value}
    raw = replace(raw, metadata=metadata)
    with pytest.raises(ValueError, match="complete SI-matched"):
        ng.interop.normalize_bruker_pdata(raw)


@pytest.mark.parametrize("axis_reference", ["processing", "acquisition"])
def test_pdata_receiver_gain_and_axis_selection(tmp_path, axis_reference):
    raw = _result(tmp_path)
    raw = replace(raw, metadata={
        **raw.metadata, "acqus": {"SFO1": 400.001, "SW": 15, "RG": 5, "NS": 17},
    })
    result = ng.interop.normalize(
        raw, axis_reference=axis_reference, normalize_receiver_gain=True,
    )
    np.testing.assert_array_equal(
        result.data, (np.array([100, 200, 300, 400]) + 1j * np.array([40, 30, 20, 10])) / 20,
    )
    if axis_reference == "processing":
        np.testing.assert_array_equal(result.axes[0].values, [4000, 3000, 2000, 1000])
    else:
        expected = 1000 + np.linspace(3000.0075, -3000.0075, 4)
        np.testing.assert_allclose(result.axes[0].values, expected, rtol=0, atol=1e-7)
    assert result.axes[0].reference.source == axis_reference
    assert result.acquisition["acquisition_frequency_mhz"] == 400.001
    assert result.axes[0].reference.observation_frequency == (
        400 if axis_reference == "processing" else 400.001
    )
    assert result.acquisition["storage_scaling"]["NC_proc"] == -2
    assert result.applied_operations[0]["receiver_gain"] == 5
    assert result.applied_operations[0]["scale"] == 0.2


def test_pdata_refuses_to_guess_requested_metadata(tmp_path):
    raw = _result(tmp_path)
    with pytest.raises(ValueError, match="positive Bruker RG"):
        ng.interop.normalize(raw, normalize_receiver_gain=True)
    with pytest.raises(ValueError, match="positive acquisition SFO1"):
        ng.interop.normalize(raw, axis_reference="acquisition")


def test_zero_spectrum_rejects_nonfinite_receiver_gain_factor(tmp_path):
    source = _write_pdata(tmp_path, component_values={"1r": [0, 0, 0, 0]})
    raw = ng.interop.read_bruker_pdata(source)
    raw = replace(raw, metadata={**raw.metadata, "acqus": {"RG": 5e-324}})
    with pytest.raises(ValueError, match="correction factor must be finite"):
        ng.interop.normalize(raw, normalize_receiver_gain=True)


def test_pdata_rejects_flat_supplied_axis_within_calibration_tolerance(tmp_path):
    raw = ng.interop.read_bruker_pdata(_write_pdata(tmp_path, sw_p=1e-9))
    assert np.all(np.diff(raw.axes[0].values) < 0)
    flat = replace(raw.axes[0], values=np.full(4, raw.axes[0].values[0]))
    with pytest.raises(ValueError, match="processing axis must be strictly decreasing"):
        ng.interop.normalize(replace(raw, axes=(flat,)))


def test_pdata_accepts_decreasing_unsigned_coordinates(tmp_path):
    raw = _result(tmp_path)
    axis = replace(raw.axes[0], values=np.array([4000, 3000, 2000, 1000], dtype=np.uint64))
    result = ng.interop.normalize(replace(raw, axes=(axis,)))
    np.testing.assert_array_equal(result.axes[0].values, axis.values)
