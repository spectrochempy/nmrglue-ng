"""Validated, dependency-free normalization profiles for interop results."""

from __future__ import annotations

import os
from collections.abc import Mapping

import numpy as np

from .result import Axis, NormalizedAcquisition, ReadResult
from ..fileio import bruker


def _agilent_frequency_axis(result):
    """Describe physical frequency relative to a negative-exponent centered DFT."""
    acquisition = result.acquisition
    original = dict(acquisition.get("original_reference", {}))
    procpar = result.metadata.get("procpar", {})
    if isinstance(procpar, Mapping):
        for key in tuple(original):
            entry = procpar.get(key)
            if entry is not None and len(entry.get("values", ())) != 1:
                original.pop(key)

    def number(mapping, key, positive=False):
        value = mapping.get(key)
        if isinstance(value, (bool, np.bool_)):
            return None
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return value if np.isfinite(value) and (not positive or value > 0) else None

    sw = number(acquisition, "spectral_width_hz", True)
    obs = number(acquisition, "observation_frequency_mhz", True)
    if isinstance(procpar, Mapping) and "sfrq" in procpar:
        if len(procpar["sfrq"].get("values", ())) != 1:
            obs = None
    frequency = number(original, "reffrq", True)
    rfl = number(original, "rfl")
    rfp = number(original, "rfp")
    offsets = {}
    if sw is not None and rfl is not None and rfp is not None:
        offsets["rfl-rfp"] = sw / 2 - rfl + rfp
    if obs is not None and frequency is not None:
        offsets["sfrq-reffrq"] = (obs - frequency) * 1e6
    offsets = {key: value for key, value in offsets.items() if np.isfinite(value)}
    procpar = result.metadata.get("procpar", {})
    refpos = procpar.get("refpos") if isinstance(procpar, Mapping) else None
    enabled = None
    if refpos is not None:
        values = refpos.get("values", ()) if isinstance(refpos, Mapping) else ()
        enabled = len(values) == 1 and str(values[0]).strip() == "0"
    return {
        "schema": "normalized-frequency-axis-v1",
        "bin_sign": -1,
        "reference_frequency_mhz": frequency,
        "reference_enabled": enabled,
        "offsets_hz": offsets,
    }


def normalize_agilent_fid(result: ReadResult) -> NormalizedAcquisition:
    """Validate an Agilent descriptive result as a storage-normalized 1D FID.

    This profile records decoding and storage semantics only. It does not apply
    scaling, conjugation, digital-filter removal, FFT, phasing or referencing.
    """
    if not isinstance(result, ReadResult):
        raise TypeError("normalize_agilent_fid requires an interop ReadResult")
    if result.format != "agilent-fid":
        raise ValueError("normalize_agilent_fid requires format='agilent-fid'")
    data = np.asarray(result.data)
    if data.ndim != 1 or not np.iscomplexobj(data):
        raise ValueError("Agilent normalized 1D profile requires one complex FID")
    if result.domains != ("time",) or len(result.axes) != 1:
        raise ValueError("Agilent normalized 1D profile requires one time axis")
    if tuple(result.encoding) != ("QSIM",):
        raise ValueError("Agilent normalized 1D profile requires encoding=('QSIM',)")
    if result.acquisition.get("normalization") != "none":
        raise ValueError("Agilent result has an unrecognized normalization state")
    if set(result.applied_corrections) != {"normalization", "conjugation"}:
        raise ValueError("Agilent result has unsupported corrections")
    if result.applied_corrections.get("normalization") != "none":
        raise ValueError("Agilent result has an unrecognized normalization correction")
    if result.applied_corrections.get("conjugation") != "none":
        raise ValueError("Agilent result has an unrecognized conjugation correction")
    procpar = result.metadata.get("procpar", {})
    if isinstance(procpar, Mapping) and "sw" in procpar:
        if len(procpar["sw"].get("values", ())) > 1:
            raise ValueError("Agilent normalized 1D requires one spectral width")
    dimensions = result.dimensions
    if dimensions.get("TDeff") != data.size:
        raise ValueError("Agilent TDeff must match the returned complex point count")
    if dimensions.get("TD") != data.size * 2:
        raise ValueError("Agilent TD must match interleaved complex storage")
    for key in ("physical_shape", "storage_shape", "returned_shape"):
        if tuple(dimensions.get(key, ())) != (data.size,):
            raise ValueError("Agilent dimensions must match the returned 1D data")
    if len(result.components) != 1 or result.components[0].name != "complex":
        raise ValueError("Agilent normalized profile requires one complex component")
    if result.components[0].data.shape != data.shape or not np.array_equal(
        result.components[0].data, data
    ):
        raise ValueError("Agilent component metadata does not match returned data")
    axis_values = result.axes[0].values
    if axis_values is not None:
        if axis_values.ndim != 1 or axis_values.shape != (data.size,):
            raise ValueError("Agilent time-axis length must match returned data")
        dwell = result.acquisition.get("dwell_time_s")
        if dwell is not None and axis_values.size > 1:
            if not np.allclose(np.diff(axis_values), dwell, rtol=1e-12, atol=1e-15):
                raise ValueError("Agilent time-axis spacing does not match dwell time")

    operation = {
        "name": "decode-agilent-complex-fid",
        "stage": "acquisition",
        "input_dimensions": ("storage",),
        "output_dimensions": ("F2",),
        "axis": "F2",
        "scale": None,
        "conjugation": "none",
        "sign": "none",
        "permutation": None,
        "evidence": "nmrglue.interop.read_agilent_fid",
    }
    provenance = {
        "source": os.fspath(result.source),
        "format": result.format,
        "reader_encoding": result.encoding,
    }
    return NormalizedAcquisition(
        data=data,
        axes=result.axes,
        dimensions=("F2",),
        physical_dimensions=("F2",),
        domains=("time",),
        quadrature_mode="complex-1d",
        branch_order=("complex",),
        normalization_state="storage-normalized",
        normalization_profile="agilent-fid-1d-complex-v1",
        applied_operations=(operation,),
        provenance=provenance,
        acquisition={**result.acquisition, "frequency_axis": _agilent_frequency_axis(result)},
        metadata=result.metadata,
        encoding=result.encoding,
        diagnostics=result.diagnostics,
    )


def normalize_bruker_fid(result: ReadResult, *, remove_digital_filter=False) -> NormalizedAcquisition:
    """Normalize an uncorrected complex QSIM/DQD FID for a negative-sign DFT.

    Trim storage padding to TD/2 before any optional digital-filter correction,
    then conjugate the samples into the canonical frequency orientation.
    No RG/NS scaling, FFT, phase correction or referencing is applied.
    Prefiltered results are rejected because padding may already have entered
    the filter correction. Historical raw reader behavior is unchanged.
    """
    if not isinstance(result, ReadResult):
        raise TypeError("normalize_bruker_fid requires an interop ReadResult")
    if result.format != "bruker-fid":
        raise ValueError("normalize_bruker_fid requires format='bruker-fid'")
    if not isinstance(remove_digital_filter, bool):
        raise ValueError("remove_digital_filter must be an explicit boolean")
    data = np.asarray(result.data)
    if data.ndim != 1 or not np.iscomplexobj(data) or not np.isfinite(data).all():
        raise ValueError("Bruker normalized profile requires one finite complex FID")
    if result.domains != ("time",) or len(result.axes) != 1 or result.axes[0].domain != "time":
        raise ValueError("Bruker normalized profile requires one time axis")
    if result.encoding not in (("QSIM",), ("DQD",)):
        raise ValueError("Bruker normalized profile supports only QSIM/DQD")
    corrections = result.applied_corrections
    if set(corrections) != {"normalization", "digital_filter"} or corrections.get("normalization") != "none":
        raise ValueError("unsupported Bruker acquisition corrections")
    filtering = corrections.get("digital_filter", {})
    if not isinstance(filtering, Mapping) or filtering.get("applied") is not False:
        raise ValueError("Bruker normalization requires an unfiltered input")
    td = result.dimensions.get("TD")
    if isinstance(td, (bool, np.bool_)) or not isinstance(td, (int, np.integer)) or td < 4 or td % 2:
        raise ValueError("Bruker TD must be a positive even interleaved point count")
    points = int(td) // 2
    for key, expected in (("returned_points", data.size), ("returned_raw_points", 2 * data.size), ("complex_points", data.size)):
        if result.dimensions.get(key) != expected:
            raise ValueError("Bruker descriptive dimensions do not match returned data")
    if points > data.size:
        raise ValueError("Bruker TD exceeds the returned storage")
    if len(result.components) != 1 or result.components[0].name != "complex" or not np.array_equal(result.components[0].data, data):
        raise ValueError("Bruker complex component does not match returned data")
    if np.any(data[points:] != 0):
        raise ValueError("nonzero samples beyond Bruker TD are not storage padding")
    acquisition = result.acquisition

    def number(mapping, key, positive=False, optional=False):
        value = mapping.get(key)
        if value is None and optional:
            return None
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
            raise ValueError("Bruker %s must be a finite scalar" % key)
        try:
            value = float(value)
        except (ValueError, OverflowError) as exc:
            raise ValueError("invalid Bruker %s" % key) from exc
        if not np.isfinite(value) or (positive and value <= 0):
            raise ValueError("invalid Bruker %s" % key)
        return value

    sw = number(acquisition, "spectral_width_hz", positive=True)
    dwell = number(acquisition, "dwell_time_s", positive=True)
    if not np.isclose(dwell, 1 / sw, rtol=1e-12, atol=0):
        raise ValueError("Bruker spectral width and dwell time disagree")
    axis = result.axes[0]
    if axis.unit != "s" or axis.values is None or np.asarray(axis.values).shape != data.shape or not np.allclose(axis.values, np.arange(data.size) / sw, rtol=1e-12, atol=1e-15):
        raise ValueError("Bruker time axis does not match the acquisition grid")
    operation: dict[str, object] = {
        "name": "normalize-bruker-complex-fid", "stage": "acquisition",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": None, "conjugation": "applied",
        "sign": "none", "permutation": None,
        "evidence": "nmrglue.interop.normalize_bruker_fid",
        "storage_points": int(data.size), "acquired_points": points,
        "trimmed_padding_points": int(data.size) - points,
    }
    work = np.array(data[:points], copy=True)
    filter_trace: dict[str, object] = {"requested": remove_digital_filter, "applied": False}
    if remove_digital_filter:
        parameters = filtering.get("parameters", {})
        decim = number(parameters, "DECIM", positive=True)
        firmware = number(parameters, "DSPFVS")
        if not decim.is_integer() or not firmware.is_integer():
            raise ValueError("Bruker digital-filter parameters must be integers")
        delay = number(parameters, "GRPDLY", optional=True)
        if delay is None or delay <= 0:
            if int(firmware) not in bruker.bruker_dsp_table or int(decim) not in bruker.bruker_dsp_table[int(firmware)]:
                raise ValueError("unknown Bruker digital-filter group delay")
            delay = float(bruker.bruker_dsp_table[int(firmware)][int(decim)])
            source = "DSPFVS/DECIM"
        else:
            source = "GRPDLY"
        if not np.isfinite(delay) or delay <= 0:
            raise ValueError("invalid Bruker digital-filter group delay")
        skip = int(np.floor(delay)) + 2
        if skip >= points - 1:
            raise ValueError("Bruker group delay leaves fewer than two points")
        work = bruker.rm_dig_filter(work, int(decim), int(firmware), delay, truncate_grpdly=True)
        filter_trace = {
            "requested": True, "applied": True, "group_delay_points": delay,
            "delay_source": source, "truncate_group_delay": True,
            "removed_points": skip, "parameters": dict(parameters),
        }
    operation["digital_filter"] = filter_trace
    operation["returned_points"] = int(work.size)
    acqus = result.metadata.get("acqus", {})
    frequency = number(acqus, "BF1", positive=True, optional=True)
    carrier = number(acquisition, "carrier_hz", optional=True)
    normalized_acquisition = {
        "spectral_width_hz": sw, "dwell_time_s": 1 / sw,
        "observation_frequency_mhz": acquisition.get("observation_frequency_mhz"),
        "nucleus": acquisition.get("nucleus"),
        "frequency_axis": {
            "schema": "normalized-frequency-axis-v1", "bin_sign": -1,
            "reference_frequency_mhz": frequency, "reference_enabled": None,
            "offsets_hz": {} if carrier is None else {"acquisition": carrier},
        },
        "normalization": "none", "digital_filter": filter_trace,
        "storage_points": int(data.size), "acquired_points": points,
        "returned_points": int(work.size), "trimmed_padding_points": int(data.size) - points,
    }
    return NormalizedAcquisition(
        data=np.conj(work),
        axes=(Axis(values=np.arange(work.size) / sw, unit="s", label=axis.label,
                   domain="time", direction="increasing", reference=axis.reference),),
        dimensions=("F2",), physical_dimensions=("F2",), domains=("time",),
        quadrature_mode="complex-1d", branch_order=("complex",),
        normalization_state="quadrature-normalized",
        normalization_profile="bruker-fid-1d-complex-v1",
        applied_operations=(operation,),
        provenance={"source": os.fspath(result.source), "format": result.format,
                    "reader_encoding": result.encoding},
        acquisition=normalized_acquisition, metadata=result.metadata,
        encoding=result.encoding, diagnostics=result.diagnostics,
    )


def normalize_bruker_pdata(result: ReadResult) -> NormalizedAcquisition:
    """Preserve a calibrated 1D processed spectrum and its available components.

    The raw reader owns NC_proc storage scaling. This normalization combines
    1r+i*1i when both are supplied, otherwise keeps real-only data real. It
    never reapplies scaling, acquisition gain, scan-count normalization, FFT,
    phasing or chemical referencing. SF/OFFSET/SW_p describe the supplied grid.
    """
    from .bruker import _build_axis

    if not isinstance(result, ReadResult):
        raise TypeError("normalize_bruker_pdata requires an interop ReadResult")
    if result.format != "bruker-pdata":
        raise ValueError("normalize_bruker_pdata requires format='bruker-pdata'")
    data = np.asarray(result.data)
    if data.ndim != 1 or data.size < 2 or data.dtype.kind not in "iuf" or not np.isfinite(data).all():
        raise ValueError("processed normalization requires one finite real primary spectrum")
    components = {}
    for component in result.components:
        if component.name not in ("1r", "1i") or component.name in components:
            raise ValueError("processed normalization requires unique 1r/1i components")
        values = np.asarray(component.data)
        if values.shape != data.shape or values.dtype.kind not in "iuf" or not np.isfinite(values).all():
            raise ValueError("processed components must be finite real arrays matching the primary spectrum")
        components[component.name] = values
    if "1r" not in components or not np.array_equal(components["1r"], data):
        raise ValueError("processed primary 1r component does not match returned data")
    if len(result.axes) != 1:
        raise ValueError("processed normalization requires one calibrated frequency axis")
    procs = result.metadata.get("procs", {})
    for key, required in (("SI", data.size), ("STSI", data.size), ("STSR", 0)):
        value = procs.get(key)
        if key != "SI" and value is None:
            continue
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)) or value != required:
            raise ValueError("normalized pdata requires a complete SI-matched spectrum without extraction")
    axis = result.axes[0]
    expected, _ = _build_axis(result.metadata, data)
    if expected.domain != "frequency" or expected.values is None:
        raise ValueError("processed normalization requires known SF/OFFSET/SW_p calibration")
    if (axis.domain != "frequency" or axis.unit != "Hz" or axis.values is None
        or np.asarray(axis.values).shape != data.shape
        or not np.isfinite(axis.values).all()
        or not np.allclose(axis.values, expected.values, rtol=1e-12, atol=1e-9)
        or axis.reference != expected.reference or axis.direction != expected.direction):
        raise ValueError("processed frequency axis disagrees with its calibration")
    corrections = dict(result.applied_corrections)
    if set(corrections) - {"scale_data", "NC_proc"} or type(corrections.get("scale_data")) is not bool:
        raise ValueError("unknown processed storage-scaling corrections")
    if corrections["scale_data"]:
        exponent = corrections.get("NC_proc")
        if isinstance(exponent, (bool, np.bool_)) or not isinstance(exponent, (int, float, np.integer, np.floating)):
            raise ValueError("scaled processed data requires a known scalar NC_proc")
        try:
            exponent = float(exponent)
        except (ValueError, OverflowError) as exc:
            raise ValueError("invalid processed NC_proc") from exc
        if not np.isfinite(exponent) or not exponent.is_integer() or exponent != result.metadata.get("procs", {}).get("NC_proc"):
            raise ValueError("processed storage scaling disagrees with NC_proc")
    elif "NC_proc" in corrections:
        raise ValueError("unscaled processed data cannot claim an applied NC_proc")
    complex_data = "1i" in components
    output = components["1r"] + 1j * components["1i"] if complex_data else data
    mode = "complex" if complex_data else "real"
    operation = {
        "name": "normalize-bruker-processed-components", "stage": "processing",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": None, "conjugation": "none", "sign": "none",
        "permutation": None, "evidence": "nmrglue.interop.read_bruker_pdata",
        "source_components": tuple(component.name for component in result.components),
        "reader_corrections": corrections,
    }
    reference = axis.reference
    if reference is None:
        raise ValueError("processed normalization requires a processing reference")
    return NormalizedAcquisition(
        data=output, axes=(axis,), dimensions=("F2",), physical_dimensions=("F2",),
        domains=("frequency",), quadrature_mode=mode + "-1d", branch_order=(mode,),
        normalization_state="storage-normalized", normalization_profile="bruker-pdata-1d-v1",
        applied_operations=(operation,),
        provenance={"source": os.fspath(result.source), "format": result.format},
        acquisition={
            "spectral_width_hz": float(result.metadata["procs"]["SW_p"]),
            "observation_frequency_mhz": reference.observation_frequency,
            "reference_source": reference.source, "nucleus": axis.label,
            "storage_scaling": corrections, "normalization": "none",
        },
        metadata=result.metadata, encoding=result.encoding, diagnostics=result.diagnostics,
    )
