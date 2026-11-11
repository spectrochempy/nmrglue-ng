"""Normalize a complete, uncorrected Bruker QF SER for interop."""

from collections.abc import Mapping
from dataclasses import replace

import numpy as np

from ..fileio import bruker
from .bruker import _raw_integer, _raw_number, _require_bruker_2d
from .result import Axis, NormalizedAcquisition, ReadResult, Reference


def _fft_presentation(metadata, shape, *, indirect_transform="conjugate-input"):
    presentation = {}
    for size, (role, acqu, proc) in zip(
        shape, (("F1", "acqu2", "proc2"), ("F2", "acqu", "proc")), strict=True
    ):
        acquisition = {**metadata.get(acqu, {}), **metadata.get(acqu + "s", {})}
        processing = {**metadata.get(proc, {}), **metadata.get(proc + "s", {})}
        acquisition = {"acqus": acquisition}
        processing = {"procs": processing}
        observation = _raw_number(acquisition, "acqus", "SFO1")
        reference = _raw_number(acquisition, "acqus", "BF1")
        ppm_width = _raw_number(acquisition, "acqus", "SW")
        sf = _raw_number(processing, "procs", "SF")
        entry: dict[str, object] = {
            "transform": indirect_transform if role == "F1" else "conjugate-input",
        }
        if (
            observation is not None and reference is not None
            and ppm_width is not None and sf is not None
        ):
            width = observation * ppm_width
            center = (observation - sf) * 1e6
            high, low = center + width / 2, center - width / 2
            if (
                min(observation, reference, ppm_width, sf, width) <= 0
                or not np.isfinite([high, low]).all() or high <= low
                or not np.isfinite([high / reference, low / reference]).all()
                or high / reference <= low / reference
            ):
                raise ValueError("invalid Bruker QF FFT display calibration")
            grid = high - np.arange(size, dtype=float) * (width / (size - 1))
            ppm = grid / reference
            if (
                not np.isfinite(grid).all() or not np.isfinite(ppm).all()
                or not np.all(grid[1:] < grid[:-1])
                or not np.all(ppm[1:] < ppm[:-1])
            ):
                raise ValueError("unrepresentable Bruker QF FFT display calibration")
            entry["display_axis"] = {
                "grid": "inclusive-endpoints",
                "direction": "decreasing",
                "center_hz": center,
                "spectral_width_hz": width,
                "reference_frequency_mhz": reference,
            }
        phase_zero = _raw_number(processing, "procs", "PHC0")
        phase_first = _raw_number(processing, "procs", "PHC1")
        entry["initial_phase"] = {
            "zero_order_deg": phase_zero or 0.0,
            "first_order_deg": phase_first or 0.0,
            "pivot_index": 0,
        }
        presentation[role] = entry
    return presentation


def _correct_ser_traces(
    data, metadata, filter_parameters, *,
    remove_dc_offset, remove_digital_filter, normalize_scan_gain,
):
    corrected = data
    if remove_dc_offset:
        corrected = corrected - corrected.mean(axis=-1, keepdims=True)
    filter_trace = {"requested": remove_digital_filter, "applied": False}
    if remove_digital_filter:
        parameters = {"acqus": filter_parameters}
        decimation = _raw_number(parameters, "acqus", "DECIM")
        if decimation is None or decimation < 1:
            raise ValueError("Bruker SER filter requires valid decimation evidence")
        if decimation > 1:
            firmware = _raw_number(parameters, "acqus", "DSPFVS")
            delay = _raw_number(parameters, "acqus", "GRPDLY")
            if firmware is None or not firmware.is_integer():
                raise ValueError("Bruker SER filter requires valid firmware evidence")
            if (delay is None or delay <= 0) and not decimation.is_integer():
                raise ValueError("Bruker SER fractional decimation requires explicit group delay")
            corrected = bruker.remove_digital_filter(parameters, corrected, truncate=True)
            if corrected.shape[1] < 2:
                raise ValueError("Bruker SER filter leaves fewer than two direct points")
            filter_trace = {
                "requested": True, "applied": True,
                "removed_points": data.shape[1] - corrected.shape[1],
            }
    gain_trace = {"applied": normalize_scan_gain}
    scale = None
    if normalize_scan_gain:
        acqus = {**metadata.get("acqu", {}), **metadata.get("acqus", {})}
        scans = _raw_number({"acqus": acqus}, "acqus", "NS")
        gain = _raw_number({"acqus": acqus}, "acqus", "RG")
        divisor = (1.0 if scans is None else scans) * (1.0 if gain is None else gain)
        if (scans is not None and scans <= 0) or (gain is not None and gain <= 0):
            raise ValueError("Bruker SER scan count and gain must be positive")
        if not np.isfinite(divisor) or divisor <= 0 or not np.isfinite(1.0 / divisor):
            raise ValueError("invalid Bruker SER scan/gain divisor")
        scale = 1.0 / divisor
        corrected = corrected / divisor
        gain_trace = {"applied": True, "scans": scans, "receiver_gain": gain, "divisor": divisor}
    if corrected is not data and not np.isfinite(corrected).all():
        raise ValueError("Bruker SER correction produced nonfinite samples")
    return corrected, filter_trace, gain_trace, scale


def normalize_bruker_ser_qf(
    result: ReadResult, *, remove_dc_offset=False, remove_digital_filter=False,
    normalize_scan_gain=False, fft_presentation=False,
) -> NormalizedAcquisition:
    """Expose a complete uniformly sampled QF SER as real and imaginary planes.

    The planes preserve the stored direct complex convention. Axes remain
    in F1/F2 order. Optional corrections apply per-trace DC removal, the
    time-domain filter for decimated data, and scan/gain scaling in that
    order. No corrections are applied by default.
    """
    if not isinstance(result, ReadResult) or result.format != "bruker-ser-qf-2d":
        raise ValueError("normalize_bruker_ser_qf requires a Bruker QF SER ReadResult")
    if not all(isinstance(value, bool) for value in (
        remove_dc_offset, remove_digital_filter, normalize_scan_gain, fft_presentation,
    )):
        raise ValueError("Bruker QF correction options must be booleans")
    if result.metadata.get("acqus", {}).get("FnTYPE", 0) != 0:
        raise ValueError("Bruker QF normalization requires uniform sampling")
    corrections = result.applied_corrections
    digital_filter = corrections.get("digital_filter")
    if (
        set(corrections) != {"digital_filter", "normalization", "processing"}
        or corrections["normalization"] != "none"
        or corrections["processing"] != "none"
        or not isinstance(digital_filter, Mapping)
        or set(digital_filter) != {"applied", "parameters"}
        or digital_filter["applied"] is not False
        or not isinstance(digital_filter["parameters"], Mapping)
        or not set(digital_filter["parameters"]) <= {"DECIM", "DSPFVS", "GRPDLY"}
    ):
        raise ValueError("Bruker QF normalization requires an uncorrected SER")
    data = np.asarray(result.data)
    order = ("F1", "F2")
    if (
        data.ndim != 2 or min(data.shape) < 2
        or data.dtype.kind != "c" or data.dtype.itemsize not in (8, 16)
        or not np.isfinite(data).all()
        or result.domains != ("time", "time") or result.encoding != ("QF", "DQD")
        or result.dimensions.get("axis_order") != order
        or result.dimensions.get("trace_order") != "F1-major, F2-contiguous"
        or any(
            result.dimensions.get(key) != data.shape
            for key in ("physical_shape", "storage_shape", "returned_shape")
        )
    ):
        raise ValueError("Bruker QF normalization requires a complete complex F1/F2 grid")
    td = result.dimensions.get("TD")
    if td != (data.shape[0], 2 * data.shape[1]):
        raise ValueError("Bruker QF shape does not match the acquired TD")
    if (
        len(result.components) != 1 or result.components[0].name != "complex"
        or not np.array_equal(result.components[0].data, data)
    ):
        raise ValueError("Bruker QF complex component disagrees with the SER samples")
    descriptions = result.acquisition.get("axes", ())
    if len(descriptions) != 2 or len(result.axes) != 2:
        raise ValueError("Bruker QF normalization requires two calibrated axes")
    widths = []
    for name, size, axis, description in zip(order, data.shape, result.axes, descriptions, strict=True):
        width = description.get("SW_hz")
        if (
            description.get("name") != name
            or not isinstance(width, (int, float))
            or isinstance(width, bool) or not np.isfinite(width) or width <= 0
            or axis.unit != "s" or axis.domain != "time" or axis.direction != "increasing"
            or axis.values is None or axis.values.shape != (size,)
            or axis.values.dtype.kind not in "iuf"
            or not np.isfinite(axis.values).all()
            or not np.all(axis.values[1:] > axis.values[:-1])
        ):
            raise ValueError("Bruker QF normalization requires calibrated uniform time grids")
        with np.errstate(over="ignore"):
            expected = np.arange(size, dtype=float) / width
        if not np.isfinite(expected).all() or not np.allclose(
            axis.values, expected, rtol=1e-12, atol=0
        ):
            raise ValueError("Bruker QF time grid is inconsistent with spectral width")
        widths.append(width)

    corrected, filter_trace, gain_trace, scale = _correct_ser_traces(
        data, result.metadata, digital_filter["parameters"],
        remove_dc_offset=remove_dc_offset,
        remove_digital_filter=remove_digital_filter,
        normalize_scan_gain=normalize_scan_gain,
    )
    axes = result.axes
    if corrected.shape[1] != data.shape[1]:
        direct_values = axes[1].values
        assert direct_values is not None
        axes = (axes[0], replace(axes[1], values=direct_values[:corrected.shape[1]]))
        descriptions = (
            descriptions[0],
            {**descriptions[1], "returned_points": corrected.shape[1]},
        )

    dimensions = ("channels", *order)
    operation = {
        "name": "split-bruker-qf-direct-component",
        "stage": "acquisition",
        "input_dimensions": order,
        "output_dimensions": dimensions,
        "axis": "F2",
        "scale": scale,
        "conjugation": "none",
        "sign": "none",
        "permutation": None,
        "evidence": "nmrglue.interop.read_bruker_ser",
        "dc_offset": {"applied": remove_dc_offset},
        "digital_filter": filter_trace,
        "scan_gain": gain_trace,
    }
    presentation = (
        {"fft_presentation": _fft_presentation(result.metadata, corrected.shape)}
        if fft_presentation else {}
    )
    return NormalizedAcquisition(
        data=np.stack((corrected.real, corrected.imag)),
        axes=axes,
        dimensions=dimensions,
        physical_dimensions=order,
        domains=("time", "time"),
        quadrature_mode="stored-components-2d",
        branch_order=("rr", "ri"),
        channel_axis=0,
        normalization_state="storage-normalized",
        normalization_profile="bruker-ser-qf-2d-v1",
        applied_operations=(operation,),
        provenance={"source": result.source, "format": result.format},
        acquisition={
            **result.acquisition,
            **presentation,
            "axes": descriptions,
            "spectral_width_hz": tuple(widths),
            "indirect_sampling": "qf",
            "dc_offset": operation["dc_offset"],
            "digital_filter": filter_trace,
            "scan_gain": gain_trace,
            "returned_shape": corrected.shape,
        },
        metadata=result.metadata,
        encoding=("real", "complex"),
        diagnostics=result.diagnostics,
    )


def normalize_bruker_ser_states(
    result: ReadResult, *, preserve_storage=False, remove_dc_offset=False,
    remove_digital_filter=False, normalize_scan_gain=False, fft_presentation=False,
) -> NormalizedAcquisition:
    """Pair complete uniform States traces in storage order, without alternation."""
    return _normalize_paired_ser(
        result, fnmode=4, preserve_storage=preserve_storage,
        remove_dc_offset=remove_dc_offset, remove_digital_filter=remove_digital_filter,
        normalize_scan_gain=normalize_scan_gain, fft_presentation=fft_presentation,
    )


def normalize_bruker_ser_states_tppi(
    result: ReadResult, *, preserve_storage=False, remove_dc_offset=False,
    remove_digital_filter=False, normalize_scan_gain=False, fft_presentation=False,
) -> NormalizedAcquisition:
    """Pair a complete uniform States-TPPI SER without applying alternation.

    The default uses the acquired TD words and applies no corrections.
    Preserve the aligned length explicitly for public reader parity.
    """
    return _normalize_paired_ser(
        result, fnmode=5, preserve_storage=preserve_storage,
        remove_dc_offset=remove_dc_offset, remove_digital_filter=remove_digital_filter,
        normalize_scan_gain=normalize_scan_gain, fft_presentation=fft_presentation,
    )


def normalize_bruker_ser_echo_antiecho(
    result: ReadResult, *, preserve_storage=False, remove_dc_offset=False,
    remove_digital_filter=False, normalize_scan_gain=False, fft_presentation=False,
) -> NormalizedAcquisition:
    """Pair complete uniform echo/anti-echo traces in their stored order."""
    return _normalize_paired_ser(
        result, fnmode=6, preserve_storage=preserve_storage,
        remove_dc_offset=remove_dc_offset, remove_digital_filter=remove_digital_filter,
        normalize_scan_gain=normalize_scan_gain, fft_presentation=fft_presentation,
    )


def _normalize_paired_ser(
    result, *, fnmode, preserve_storage, remove_dc_offset,
    remove_digital_filter, normalize_scan_gain, fft_presentation,
):
    mode, label = {
        4: ("states", "States"),
        5: ("states-tppi", "States-TPPI"),
        6: ("echo-antiecho", "echo/anti-echo"),
    }[fnmode]
    echo_antiecho = fnmode == 6
    if not isinstance(result, ReadResult) or result.format != "bruker-ser-storage":
        raise ValueError(f"{label} normalization requires a Bruker SER storage result")
    if not all(isinstance(value, bool) for value in (
        preserve_storage, remove_dc_offset, remove_digital_filter, normalize_scan_gain,
        fft_presentation,
    )):
        raise ValueError(f"{label} correction and storage options must be booleans")
    metadata = result.metadata
    _require_bruker_2d(
        metadata, higher_dimension_files=result.dimensions.get("higher_dimension_files", ()),
    )
    direct = metadata.get("acqus", {})
    indirect = metadata.get("acqu2s", {})
    if (
        direct.get("FnTYPE", 0) != 0 or "nuslist_raw" in metadata
        or direct.get("AQ_mod") != 3 or indirect.get("FnMODE") != fnmode
    ):
        raise ValueError(f"Bruker SER requires uniform {label} with direct DQD")
    rows = _raw_integer(metadata, "acqu2s", "TD")
    words = _raw_integer(metadata, "acqus", "TD")
    if rows is None or words is None or min(rows, words) < 4 or rows % 2 or words % 2:
        raise ValueError(f"{label} requires complete paired TD geometry")

    data = np.asarray(result.data)
    word_type = (data.dtype.kind, data.dtype.itemsize)
    required_type = {0: ("i", 4), 2: ("f", 8)}.get(direct.get("DTYPA"))
    if word_type != required_type:
        raise ValueError(f"{label} requires a supported scalar storage type")
    stride = ((words * data.dtype.itemsize + 1023) // 1024) * 1024 // data.dtype.itemsize
    if (
        data.shape != (rows, stride)
        or result.dimensions.get("declared_td") != words
        or result.dimensions.get("axis_order") != ("trace", "word")
        or result.dimensions.get("shape") != data.shape
        or result.domains != ("unknown", "unknown") or result.applied_corrections
        or len(result.components) != 1
        or result.components[0].name != "stored-words"
        or not np.array_equal(result.components[0].data, data, equal_nan=True)
    ):
        raise ValueError(f"{label} requires uncorrected storage with complete TD geometry")
    selected_words = stride if preserve_storage else words
    selected = data[:, :selected_words]
    if not np.isfinite(selected).all():
        raise ValueError(f"{label} selected samples must be finite")
    traces = np.empty((rows, selected_words // 2), dtype=np.complex128)
    traces.real = selected[:, ::2]
    traces.imag = selected[:, 1::2]
    traces, filter_trace, gain_trace, scale = _correct_ser_traces(
        traces, metadata, direct,
        remove_dc_offset=remove_dc_offset,
        remove_digital_filter=remove_digital_filter,
        normalize_scan_gain=normalize_scan_gain,
    )

    sw_f2 = _raw_number(metadata, "acqus", "SW_h")
    sw_f1_ppm = _raw_number(metadata, "acqu2s", "SW")
    obs_f1 = _raw_number(metadata, "acqu2s", "SFO1")
    obs_f2 = _raw_number(metadata, "acqus", "SFO1")
    if sw_f2 is None or sw_f1_ppm is None or obs_f1 is None or obs_f2 is None:
        raise ValueError(f"{label} requires both calibrated acquisition axes")
    if min(sw_f2, sw_f1_ppm, obs_f1, obs_f2) <= 0:
        raise ValueError(f"{label} axis widths and observations must be positive")

    widths = (sw_f1_ppm * obs_f1, sw_f2)
    axes = []
    for size, width, observation, section in zip(
        (rows // 2, traces.shape[1]), widths, (obs_f1, obs_f2), (indirect, direct), strict=True
    ):
        if not np.isfinite(width) or width <= 0:
            raise ValueError(f"unrepresentable {label} spectral width")
        with np.errstate(over="ignore"):
            values = np.arange(size, dtype=float) / width
        if not np.isfinite(values).all() or not np.all(values[1:] > values[:-1]):
            raise ValueError(f"unrepresentable {label} time grid")
        axes.append(Axis(
            values=values, unit="s", label=section.get("NUC1"),
            domain="time", direction="increasing",
            reference=Reference(
                observation_frequency=observation, observation_frequency_unit="MHz",
                source="acquisition",
            ),
        ))

    order = ("F1", "F2")
    dimensions = ("channels", *order)
    if echo_antiecho:
        components = np.stack((traces[0::2], traces[1::2]))
        branch_order = ("first", "second")
        encoding = ("echo-antiecho", "complex")
        quadrature_mode = "echo-antiecho-stored-2d"
        group_delay = direct.get("GRPDLY")
        if isinstance(group_delay, (int, float)) and not isinstance(group_delay, bool) and np.isfinite(group_delay) and group_delay > 0:
            filter_trace["group_delay_points"] = group_delay
        indirect_state = {"branch_order": "stored", "reconstruction": "not_applied"}
    else:
        components = np.stack((
            traces[0::2].real, traces[0::2].imag,
            traces[1::2].real, traces[1::2].imag,
        ))
        branch_order = ("rr", "ri", "ir", "ii")
        encoding = ("complex", "complex")
        quadrature_mode = "stored-components-2d"
        indirect_state = {"tppi_alternation": "declared_not_applied"} if fnmode == 5 else {}
    operation = {
        "name": f"pair-bruker-{mode}-traces",
        "stage": "acquisition",
        "input_dimensions": ("trace", "word"),
        "output_dimensions": dimensions,
        "axis": "F1",
        "scale": scale,
        "conjugation": "none",
        "sign": "none",
        "permutation": None,
        "evidence": "nmrglue.interop.read_bruker_ser_storage",
        "padding_words_per_trace": stride - words,
        "retained_padding_words_per_trace": selected_words - words,
        "dc_offset": {"applied": remove_dc_offset},
        "digital_filter": filter_trace,
        "scan_gain": gain_trace,
    }
    presentation = (
        {"fft_presentation": _fft_presentation(
            metadata, components.shape[1:], indirect_transform=(
                "echo-antiecho-branch-fft" if echo_antiecho else f"{mode}-cross-pairs"
            ),
        )}
        if fft_presentation else {}
    )
    return NormalizedAcquisition(
        data=components, axes=tuple(axes), dimensions=dimensions,
        physical_dimensions=order, domains=("time", "time"),
        quadrature_mode=quadrature_mode,
        branch_order=branch_order, channel_axis=0,
        normalization_state="storage-normalized",
        normalization_profile=f"bruker-ser-{mode}-2d-v1",
        applied_operations=(operation,),
        provenance={"source": result.source, "format": result.format},
        acquisition={
            "spectral_width_hz": widths,
            "indirect_sampling": mode,
            **indirect_state,
            **presentation,
            "storage_shape": data.shape,
            "dc_offset": operation["dc_offset"],
            "digital_filter": filter_trace,
            "scan_gain": gain_trace,
        },
        metadata=metadata, encoding=encoding,
        diagnostics=result.diagnostics,
    )
