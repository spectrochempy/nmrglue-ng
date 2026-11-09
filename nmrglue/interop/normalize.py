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


def _agilent_public_fid(result, data, operation):
    """Preserve the historical public reader's 1D presentation and scaling."""
    from .varian import _number, _procpar_number, _procpar_string

    acquisition = result.acquisition
    if acquisition.get("spectral_width_hz") is None or acquisition.get("observation_frequency_mhz") is None:
        raise ValueError("Agilent public FID requires a calibrated time axis and observation frequency")
    ns = _number(acquisition.get("NS"), "NS")
    ne = _number(acquisition.get("NE"), "NE")
    if any(value is not None and value < 0 for value in (ns, ne)):
        raise ValueError("Agilent public FID requires finite nonnegative NS and NE")
    divisor = (ns or 1.0) * (ne or 1.0)
    if not np.isfinite(divisor) or divisor <= 0 or not np.isfinite(1 / divisor):
        raise ValueError("Agilent public FID requires a finite positive NS/NE divisor")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        scaled = data / divisor
    if not np.isfinite(scaled).all():
        raise ValueError("Agilent public FID scaling produced non-finite samples")
    procpar = result.metadata.get("procpar", {})
    presentation = {
        "fft_input_transform": "conjugate-input",
        "reported_nucleus": _procpar_string(procpar, "dn") or acquisition.get("nucleus"),
        "decoupler_frequency_mhz": _procpar_number(procpar, "dfrq"),
        "pulse_program": _procpar_string(procpar, "array") or _procpar_string(procpar, "pulprog"),
        "date_raw": _procpar_string(procpar, "date"),
        "acquisition_time_s": _procpar_number(procpar, "at"),
        "nblocks": result.metadata.get("nblocks", 1),
        "ntraces": result.metadata.get("ntraces", 1),
        "ns": 1.0 if ns is None else ns,
        "ne": 1.0 if ne is None else ne,
    }
    correction = {
        **operation,
        "name": "normalize-agilent-ns-ne",
        "input_dimensions": ("F2",),
        "scale": 1 / divisor,
        "divisor": divisor,
        "evidence": "procpar.ns and procpar.ne",
    }
    return scaled, (operation, correction), presentation


def normalize_agilent_fid(
    result: ReadResult, *, legacy_presentation=False,
) -> NormalizedAcquisition:
    """Validate an Agilent descriptive result as a storage-normalized 1D FID.

    This profile records decoding and storage semantics only. It does not apply
    scaling, conjugation, digital-filter removal, FFT, phasing or referencing
    by default. With legacy_presentation=True, apply the historical NS×NE
    divisor and describe the conjugated-input display FFT. Completed scan
    counts (nt/ct/ctcount) remain provenance and are never used as the divisor.
    """
    if type(legacy_presentation) is not bool:
        raise ValueError("Agilent legacy_presentation must be a bool")
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
    acquisition = {**result.acquisition, "frequency_axis": _agilent_frequency_axis(result)}
    operations = (operation,)
    if legacy_presentation:
        data, operations, presentation = _agilent_public_fid(result, data, operation)
        acquisition.update(
            normalization="ns-ne",
            legacy_presentation=presentation,
        )
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
        applied_operations=operations,
        provenance=provenance,
        acquisition=acquisition,
        metadata=result.metadata,
        encoding=result.encoding,
        diagnostics=result.diagnostics,
    )


def normalize_bruker_fid(
    result: ReadResult,
    *,
    remove_digital_filter=False,
    remove_dc_offset=False,
    normalize_scan_gain=False,
    preserve_storage=False,
) -> NormalizedAcquisition:
    """Normalize an uncorrected complex QSIM/DQD FID for a negative-sign DFT.

    Trim storage padding to TD/2 by default. Use ``preserve_storage=True``
    to retain the decoded length, including verified zero padding.
    Optional DC removal subtracts the mean of the selected points before
    filtering. Use ``remove_digital_filter="if-decimated"`` to skip the
    correction for DECIM=1, as the public TopSpin reader does. An explicit
    ``True`` still applies the correction when a valid delay is supplied.
    Optional scan/gain normalization divides by NS times RG
    after filtering. Each missing factor defaults to one. The output is
    conjugated into the canonical frequency orientation.

    Prefiltered inputs are rejected. No FFT or referencing is applied.
    """
    if not isinstance(result, ReadResult):
        raise TypeError("normalize_bruker_fid requires an interop ReadResult")
    if result.format != "bruker-fid":
        raise ValueError("normalize_bruker_fid requires format='bruker-fid'")
    if_decimated = (
        isinstance(remove_digital_filter, str)
        and remove_digital_filter == "if-decimated"
    )
    if not isinstance(remove_digital_filter, bool) and not if_decimated:
        raise ValueError("remove_digital_filter must be a boolean or 'if-decimated'")
    for name, value in (
        ("remove_dc_offset", remove_dc_offset),
        ("normalize_scan_gain", normalize_scan_gain),
        ("preserve_storage", preserve_storage),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be an explicit boolean")
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
    input_points = data.size if preserve_storage else points
    trimmed_points = data.size - input_points
    operation: dict[str, object] = {
        "name": "normalize-bruker-complex-fid", "stage": "acquisition",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": None, "conjugation": "applied",
        "sign": "none", "permutation": None,
        "evidence": "nmrglue.interop.normalize_bruker_fid",
        "storage_points": int(data.size), "acquired_points": points,
        "trimmed_padding_points": int(trimmed_points),
    }
    work = np.array(data[:input_points], copy=True)
    if remove_dc_offset:
        work -= work.mean()
    dc_trace = {"applied": remove_dc_offset, "input_points": int(input_points)}
    parameters = filtering.get("parameters", {})
    def resolve_filter(only_if_decimated):
        if not isinstance(parameters, Mapping):
            raise ValueError("invalid Bruker digital-filter parameters")
        decim = number(parameters, "DECIM", positive=True)
        if not decim.is_integer():
            raise ValueError("Bruker digital-filter decimation must be an integer")
        if only_if_decimated and decim == 1:
            return None
        firmware = number(parameters, "DSPFVS")
        if not firmware.is_integer():
            raise ValueError("Bruker digital-filter firmware must be an integer")
        delay = number(parameters, "GRPDLY", optional=True)
        if delay is None or delay <= 0:
            table = bruker.bruker_dsp_table.get(int(firmware), {})
            if int(decim) not in table:
                raise ValueError("unknown Bruker digital-filter group delay")
            delay = float(table[int(decim)])
            source = "DSPFVS/DECIM"
        else:
            source = "GRPDLY"
        if not np.isfinite(delay) or delay <= 0:
            raise ValueError("invalid Bruker digital-filter group delay")
        skip = int(np.floor(delay)) + 2
        if skip >= points - 1:
            raise ValueError("Bruker group delay leaves fewer than two acquired points")
        return int(decim), int(firmware), delay, source, skip

    def resolve_gain():
        scans = number(acquisition, "NS", positive=True, optional=True)
        gain = number(acquisition, "RG", positive=True, optional=True)
        divisor = (1.0 if scans is None else scans) * (1.0 if gain is None else gain)
        if not np.isfinite(divisor) or divisor <= 0:
            raise ValueError("invalid Bruker scan/gain divisor")
        if not np.isfinite(1.0 / divisor):
            raise ValueError("invalid Bruker scan/gain scale")
        return {"scans": scans, "receiver_gain": gain, "divisor": divisor}

    filter_trace: dict[str, object] = {"requested": bool(remove_digital_filter), "applied": False}
    try:
        filter_spec = resolve_filter(if_decimated or not remove_digital_filter)
    except ValueError:
        if remove_digital_filter:
            raise
        pending_filter: dict[str, object] = {"state": "unavailable"}
    else:
        if filter_spec is None:
            pending_filter = {"state": "not-required"}
            if remove_digital_filter:
                filter_trace["reason"] = "no-decimation"
        else:
            decim, firmware, delay, source, skip = filter_spec
            pending_filter = {
                "state": "available",
                "method": "integer-shift-fold-trim",
                "group_delay_points": delay,
                "left_shift_points": skip - 2,
                "fold_points": max(skip - 6, 0),
                "discard_points": skip,
            }
            if remove_digital_filter:
                work = bruker.rm_dig_filter(
                    work, decim, firmware, delay, truncate_grpdly=True
                )
                filter_trace = {
                    "requested": True, "applied": True, "group_delay_points": delay,
                    "delay_source": source, "truncate_group_delay": True,
                    "removed_points": skip, "parameters": dict(parameters),
                }
    gain_trace: dict[str, object] = {"applied": normalize_scan_gain}
    try:
        gain_spec = resolve_gain()
    except ValueError:
        if normalize_scan_gain:
            raise
        pending_gain: dict[str, object] = {"state": "unavailable"}
    else:
        pending_gain = {"state": "available", **gain_spec}
        if normalize_scan_gain:
            divisor = gain_spec["divisor"]
            work /= divisor
            gain_trace.update(gain_spec)
            operation["scale"] = 1.0 / divisor
    if not np.isfinite(work).all():
        raise ValueError("Bruker corrections produced nonfinite samples")
    operation["dc_offset"] = dc_trace
    operation["scan_gain"] = gain_trace
    operation["digital_filter"] = filter_trace
    operation["returned_points"] = int(work.size)
    acqus = {**result.metadata.get("acqu", {}), **result.metadata.get("acqus", {})}
    frequency = number(acqus, "BF1", positive=True, optional=True)
    carrier = number(acquisition, "carrier_hz", optional=True)
    observation = number(acquisition, "observation_frequency_mhz", positive=True, optional=True)
    normalized_acquisition = {
        "spectral_width_hz": sw, "dwell_time_s": 1 / sw,
        "observation_frequency_mhz": observation,
        "nucleus": acquisition.get("nucleus"),
        "frequency_axis": {
            "schema": "normalized-frequency-axis-v1", "bin_sign": -1,
            "reference_frequency_mhz": frequency, "reference_enabled": None,
            "offsets_hz": {} if carrier is None else {"acquisition": carrier},
        },
        "normalization": "scan-gain" if normalize_scan_gain else "none",
        "digital_filter": filter_trace, "dc_offset": dc_trace, "scan_gain": gain_trace,
        "fid_preparation": {
            "schema": "fid-preparation-v1",
            "complex_convention": "centered-negative-exponent-dft",
            "sample_count": int(work.size),
            "digital_filter": pending_filter,
            "scan_gain": pending_gain,
        },
        "storage_points": int(data.size), "acquired_points": points,
        "returned_points": int(work.size), "trimmed_padding_points": int(trimmed_points),
    }
    if preserve_storage:
        processing = {
            **result.metadata.get("proc", {}), **result.metadata.get("procs", {})
        }
        processing_frequency = number(processing, "SF", positive=True, optional=True)
        display_width_ppm = number(acqus, "SW", positive=True, optional=True)
        if None not in (observation, frequency, processing_frequency, display_width_ppm):
            center = (observation - processing_frequency) * 1e6
            width = display_width_ppm * observation
            if not np.isfinite(center) or not np.isfinite(width):
                raise ValueError("invalid Bruker compatibility FFT display calibration")
            normalized_acquisition["fft_display_axis"] = {
                "grid": "inclusive-endpoints", "direction": "decreasing",
                "center_hz": center, "spectral_width_hz": width,
                "reference_frequency_mhz": frequency,
            }
        phase_zero = number(processing, "PHC0", optional=True)
        phase_first = number(processing, "PHC1", optional=True)
        if phase_zero is not None or phase_first is not None:
            normalized_acquisition["fft_initial_phase"] = {
                "zero_order_deg": phase_zero if phase_zero is not None else 0.0,
                "first_order_deg": phase_first if phase_first is not None else 0.0,
                "pivot_index": 0,
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


def normalize_bruker_pdata(
    result: ReadResult, *, axis_reference="processing", normalize_receiver_gain=False,
) -> NormalizedAcquisition:
    """Preserve a calibrated 1D processed spectrum and its available components.

    The raw reader owns NC_proc storage scaling. This normalization combines
    1r+i*1i when both are supplied, otherwise keeps real-only data real. It
    does not reapply storage scaling. By default, SF/OFFSET/SW_p describe the
    processing grid and receiver gain is unchanged. Select
    axis_reference="acquisition" for the acquisition-centered endpoint grid,
    and normalize_receiver_gain=True to divide by the recorded positive RG.
    The processing reference remains SF. When available for these options,
    the acquisition frequency SFO1 is recorded separately in
    acquisition["acquisition_frequency_mhz"]. Scan-count scaling, FFT and
    phasing are outside this profile.
    """
    from .bruker import _build_axis, _processed_acquisition_axis, _raw_number

    if axis_reference not in ("processing", "acquisition"):
        raise ValueError("Bruker pdata axis_reference must be processing or acquisition")
    if type(normalize_receiver_gain) is not bool:
        raise ValueError("normalize_receiver_gain must be a bool")

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
    if not (
        np.all(expected.values[1:] < expected.values[:-1])
        and np.all(axis.values[1:] < axis.values[:-1])
    ):
        raise ValueError("Bruker processing axis must be strictly decreasing")
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
    gain = None
    gain_scale = None
    if normalize_receiver_gain:
        gain = _raw_number(result.metadata, "acqus", "RG")
        if gain is None or gain <= 0:
            raise ValueError("receiver-gain normalization requires a positive Bruker RG")
        gain_scale = 1 / gain
        if not np.isfinite(gain_scale):
            raise ValueError("Bruker receiver-gain correction factor must be finite")
        with np.errstate(over="ignore"):
            output = output / gain
        if not np.isfinite(output).all():
            raise ValueError("Bruker receiver-gain normalization produced non-finite values")
    width = float(procs["SW_p"])
    sfo = None
    if axis_reference == "acquisition" or normalize_receiver_gain:
        sfo = _raw_number(result.metadata, "acqus", "SFO1")
        if sfo is not None and sfo <= 0:
            raise ValueError("Bruker acquisition SFO1 must be positive")
    if axis_reference == "acquisition":
        if sfo is None:
            raise ValueError("acquisition axis requires positive acquisition SFO1")
        sweep_ppm = _raw_number(result.metadata, "acqus", "SW")
        if sweep_ppm is None or sweep_ppm <= 0:
            raise ValueError("acquisition axis requires positive Bruker SW")
        axis, width = _processed_acquisition_axis(result.metadata, data.size, axis.label)
    mode = "complex" if complex_data else "real"
    operation = {
        "name": "normalize-bruker-processed-components", "stage": "processing",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": gain_scale,
        "conjugation": "none", "sign": "none",
        "permutation": None, "evidence": "nmrglue.interop.read_bruker_pdata",
        "source_components": tuple(component.name for component in result.components),
        "reader_corrections": corrections,
    }
    if gain is not None:
        operation["receiver_gain"] = gain
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
            "spectral_width_hz": width,
            "observation_frequency_mhz": reference.observation_frequency,
            "reference_source": reference.source, "nucleus": axis.label,
            **({"acquisition_frequency_mhz": sfo} if sfo is not None else {}),
            "storage_scaling": corrections,
            "normalization": "none" if gain is None else "receiver-gain",
        },
        metadata=result.metadata, encoding=result.encoding, diagnostics=result.diagnostics,
    )
