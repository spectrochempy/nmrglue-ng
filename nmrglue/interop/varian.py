"""Agilent/Varian adapters for the neutral interop layer."""

from __future__ import annotations

import hashlib
import math
import os
import struct
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np

from ..fileio import varian
from .result import Axis, Component, Diagnostic, NormalizedAcquisition, ReadResult, Reference


def _number(value, name):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Agilent %s must be numeric" % name)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Agilent %s must be finite" % name)
    return value


def _procpar_number(procpar, key, default=None):
    values = procpar.get(key, {}).get("values", ())
    if not values:
        return default
    value = values[0]
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Agilent %s must be numeric" % key) from exc
    return _number(value, key)


def _procpar_string(procpar, key, default=None):
    values = procpar.get(key, {}).get("values", ())
    return values[0] if values else default


def _procpar_integer(procpar, key):
    """Return one finite integer procpar value, or ``None`` if absent."""
    values = procpar.get(key, {}).get("values", ())
    if not isinstance(values, (list, tuple)) or len(values) != 1:
        return None
    value = values[0]
    if isinstance(value, (list, tuple, np.ndarray, bool)):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(value) or not value.is_integer():
        return None
    return int(value)


def _procpar_phase(procpar):
    """Return the exact integer phase array stored in procpar."""
    values = procpar.get("phase", {}).get("values", ())
    if not isinstance(values, (list, tuple)):
        return None
    phases = []
    for value in values:
        if isinstance(value, (list, tuple, np.ndarray, bool)):
            return None
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(value) or not value.is_integer():
            return None
        phases.append(int(value))
    return tuple(phases)


def _scan_count(value, minimum=0, maximum=2147483647):
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (str, int, float, np.integer, np.floating)
    ):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number < minimum or number > maximum:
        return None
    if number != number.to_integral_value():
        return None
    return int(number)


def _agilent_scan_counts(dic, procpar):
    invalid = []
    parameters = {}
    for key, minimum, maximum in (("nt", 1, 1000000000), ("ct", 0, 2147483647)):
        values = procpar.get(key, {}).get("values", ())
        value = (
            _scan_count(values[0], minimum, maximum)
            if isinstance(values, (list, tuple)) and len(values) == 1
            else None
        )
        parameters[key] = value
        if key in procpar and value is None:
            invalid.append("procpar." + key)
    headers = dic.get("blockheader", ())
    if not isinstance(headers, (list, tuple)):
        headers = ()
        invalid.append("fid.blockheader")
    block_counts = []
    block_scales = []
    for header in headers:
        value = (
            _scan_count(header.get("ctcount")) if isinstance(header, Mapping) else None
        )
        block_counts.append(value)
        block_scales.append(header.get("scale") if isinstance(header, Mapping) else None)
        if value is None:
            invalid.append("fid.blockheader.ctcount")
    completed = None
    if invalid:
        status = "invalid"
    elif len(block_counts) > 1:
        status = "ambiguous"
    elif not block_counts:
        status = "unavailable"
    elif parameters["ct"] is not None and parameters["ct"] != block_counts[0]:
        status = "conflicting"
    else:
        completed = block_counts[0]
        status = "consistent" if parameters["ct"] is not None else "block-only"
    return {
        "requested": parameters["nt"],
        "procpar_completed": parameters["ct"],
        "block_completed": tuple(block_counts),
        "block_scales": tuple(block_scales),
        "completed": completed,
        "source": "fid.blockheader.ctcount" if completed is not None else None,
        "status": status,
        "invalid": tuple(invalid),
    }


def read_agilent_fid(
    dir=".",
    *,
    shape=None,
    torder=None,
    read_blockhead=False,
    carrier_hz=None,
    carrier_ppm=None,
    single_trace_only=False,
):
    """Read an Agilent/Varian raw 1D FID as a neutral ``ReadResult``.

    The historical Varian reader performs all binary and ``procpar`` parsing.
    This adapter applies no scan normalization or conjugation. A carrier must
    be supplied explicitly in Hz or ppm for NMRPipe export; ``rfl`` and other
    procpar reference candidates are preserved but never interpreted silently.
    The direct-axis nucleus and label use the observed transmitter nucleus
    ``tn`` only; absent or empty ``tn`` leaves them unknown, never inferred
    from the decoupler nucleus ``dn``.
    ``acquisition['scan_counts']`` distinguishes requested ``nt``, procpar
    ``ct`` and block-header ``ctcount``. A completed count is reported only
    for one valid, unambiguous block without contradictory procpar evidence.
    Counts and binary scale values are descriptive: no scaling is applied.
    Set single_trace_only=True to reject multi-block or multi-trace files
    from the binary header before reading samples.
    Block headers are always parsed for this evidence; ``read_blockhead``
    controls whether the full headers are retained in ``metadata``.
    """
    if not os.path.isdir(dir):
        raise OSError("directory %s does not exist" % (dir,))

    if single_trace_only:
        with open(os.path.join(dir, "fid"), "rb") as stream:
            try:
                header = varian.get_fileheader(stream)
            except struct.error as exc:
                raise ValueError("Agilent FID has an incomplete file header") from exc
        if header[:2] != (1, 1):
            raise ValueError("Agilent single-trace profile requires one block and one trace")

    dic, data = varian.read(
        dir,
        shape=shape,
        torder=torder,
        read_blockhead=True,
    )
    data = np.asarray(data)
    if data.ndim != 1 or not np.iscomplexobj(data):
        raise ValueError("the Agilent raw 1D profile requires one complex FID")

    procpar = dic.get("procpar", {})
    sw = _procpar_number(procpar, "sw")
    obs = _procpar_number(procpar, "sfrq")
    np_raw = _procpar_number(procpar, "np")
    ns = _procpar_number(procpar, "ns")
    ne = _procpar_number(procpar, "ne")
    nucleus = _procpar_string(procpar, "tn") or None
    scan_counts = _agilent_scan_counts(dic, procpar)
    if not read_blockhead:
        dic = {key: value for key, value in dic.items() if key != "blockheader"}
    if sw is not None and sw <= 0:
        raise ValueError("Agilent spectral width must be positive")
    if obs is not None and obs <= 0:
        raise ValueError("Agilent observation frequency must be positive")

    explicit_hz = _number(carrier_hz, "carrier_hz")
    explicit_ppm = _number(carrier_ppm, "carrier_ppm")
    if explicit_hz is not None and explicit_ppm is not None:
        if obs is None or not math.isclose(
            explicit_hz, explicit_ppm * obs, rel_tol=1e-12, abs_tol=1e-9
        ):
            raise ValueError("Agilent carrier_hz and carrier_ppm are inconsistent")
    if explicit_hz is None and explicit_ppm is not None:
        if obs is None:
            raise ValueError("carrier_ppm requires an observation frequency")
        explicit_hz = explicit_ppm * obs
    if explicit_ppm is None and explicit_hz is not None and obs is not None:
        explicit_ppm = explicit_hz / obs

    missing = []
    if sw is None:
        missing.append("sw")
    if obs is None:
        missing.append("sfrq/dfrq")
    if explicit_hz is None:
        missing.append("carrier_hz/carrier_ppm")
    diagnostics = ()
    if missing:
        diagnostics = (
            Diagnostic(
                code="acquisition.missing-parameter",
                severity="warning",
                message=(
                    "Agilent raw FID lacks normalized acquisition metadata; "
                    "raw reading remains available but export may be blocked."
                ),
                context={"missing": tuple(missing)},
            ),
        )

    axis_values = None if sw is None else np.arange(data.size, dtype=float) / sw
    axis = Axis(
        values=axis_values,
        unit="s" if axis_values is not None else None,
        label=nucleus,
        domain="time",
        direction="increasing" if axis_values is not None else "unknown",
        reference=(
            Reference(
                observation_frequency=obs,
                observation_frequency_unit="MHz" if obs is not None else None,
                source="acquisition",
            )
            if obs is not None
            else None
        ),
    )
    acquisition = {
        "spectral_width_hz": sw,
        "dwell_time_s": None if sw is None else 1.0 / sw,
        "observation_frequency_mhz": obs,
        "carrier_hz": explicit_hz,
        "carrier_ppm": explicit_ppm,
        "carrier_source": (
            "explicit_hz"
            if carrier_hz is not None
            else "explicit_ppm"
            if carrier_ppm is not None
            else None
        ),
        "nucleus": nucleus,
        "np_raw": np_raw,
        "NS": ns,
        "NE": ne,
        "scan_counts": scan_counts,
        "normalization": "none",
        "storage_convention": "interleaved real/imaginary decoded to complex",
        "conjugation": "none",
        "original_reference": {
            key: _procpar_number(procpar, key)
            for key in ("rfl", "rfp", "reffrq", "tof")
            if _procpar_number(procpar, key) is not None
        },
    }
    dimensions = {
        "TD": np_raw,
        "TDeff": int(data.size),
        "physical_shape": (int(data.size),),
        "storage_shape": (int(data.size),),
        "returned_shape": (int(data.size),),
        "trace_order": "direct FID",
        "component_basis": ("complex",),
    }
    return ReadResult(
        data=data,
        axes=(axis,),
        metadata=dic,
        components=(Component("complex", data),),
        applied_corrections={"normalization": "none", "conjugation": "none"},
        diagnostics=diagnostics,
        format="agilent-fid",
        source=dir,
        domains=("time",),
        encoding=("QSIM",),
        dimensions=dimensions,
        acquisition=acquisition,
    )


def read_agilent_states_2d(
    dir=".",
    *,
    shape=None,
    torder=None,
    read_blockhead=False,
):
    """Read the strict descriptive Agilent/Varian 2D States raw profile.

    The returned data preserves the decoded ``(stored F1 traces, complex F2
    points)`` matrix.  This adapter does not pair traces, construct RR/RI/IR/II
    components, normalize amplitudes, conjugate, alternate signs, or perform
    FFT processing.  Trace pairing remains the responsibility of a vendor-aware
    NMR adapter.
    """
    if not os.path.isdir(dir):
        raise OSError("directory %s does not exist" % (dir,))

    dic, data = varian.read(
        dir,
        shape=shape,
        torder=torder,
        read_blockhead=read_blockhead,
    )
    data = np.asarray(data)
    if data.ndim != 2 or not np.iscomplexobj(data):
        raise ValueError("the Agilent States profile requires a complex 2D matrix")

    procpar = dic.get("procpar", {})
    phase = _procpar_phase(procpar)
    ni = _procpar_integer(procpar, "ni")
    arraydim = _procpar_integer(procpar, "arraydim")
    np_raw = _procpar_integer(procpar, "np")
    ntraces = dic.get("ntraces")
    if phase != (1, 2):
        raise ValueError("Agilent States 2D requires exact phase=[1, 2]")
    if ni is None or ni <= 0:
        raise ValueError("Agilent States 2D requires positive integer ni")
    if arraydim != 2 * ni:
        raise ValueError("Agilent States 2D requires arraydim=2*ni")
    if np_raw is None or np_raw <= 0 or np_raw % 2:
        raise ValueError("Agilent States 2D requires positive even np")
    if ntraces != 1:
        raise ValueError("Agilent States 2D requires binary ntraces=1")
    expected_shape = (arraydim, np_raw // 2)
    if data.shape != expected_shape:
        raise ValueError(
            "Agilent States 2D shape %r does not match procpar shape %r"
            % (data.shape, expected_shape)
        )

    sw_f2 = _procpar_number(procpar, "sw")
    obs_f2 = _procpar_number(procpar, "sfrq")
    sw_f1 = _procpar_number(procpar, "sw1")
    obs_f1 = _procpar_number(procpar, "sfrq2")
    for name, value in (("sw", sw_f2), ("sw1", sw_f1)):
        if value is not None and value <= 0:
            raise ValueError("Agilent %s must be positive" % name)
    for name, value in (("sfrq/dfrq", obs_f2), ("sfrq2/dfrq2", obs_f1)):
        if value is not None and value <= 0:
            raise ValueError("Agilent %s must be positive" % name)

    missing = []
    for name, value in (
        ("sw", sw_f2),
        ("sw1", sw_f1),
        ("sfrq", obs_f2),
        ("sfrq2", obs_f1),
    ):
        if value is None:
            missing.append(name)
    diagnostics = ()
    if missing:
        diagnostics = (
            Diagnostic(
                code="acquisition.missing-parameter",
                severity="warning",
                message="Agilent States 2D lacks optional axis metadata.",
                context={"missing": tuple(missing)},
            ),
        )

    f1_axis = Axis(
        values=None,
        unit="s" if sw_f1 is not None else None,
        label=_procpar_string(procpar, "dn2") or _procpar_string(procpar, "tn2"),
        domain="time",
        direction="unknown",
        reference=(
            Reference(
                observation_frequency=obs_f1,
                observation_frequency_unit="MHz",
                source="acquisition",
            )
            if obs_f1 is not None
            else None
        ),
    )
    f2_axis = Axis(
        values=(
            None
            if sw_f2 is None
            else np.arange(data.shape[1], dtype=float) / sw_f2
        ),
        unit="s" if sw_f2 is not None else None,
        label=_procpar_string(procpar, "dn") or _procpar_string(procpar, "tn"),
        domain="time",
        direction="increasing" if sw_f2 is not None else "unknown",
        reference=(
            Reference(
                observation_frequency=obs_f2,
                observation_frequency_unit="MHz",
                source="acquisition",
            )
            if obs_f2 is not None
            else None
        ),
    )
    storage_shape = tuple(int(size) for size in data.shape)
    dimensions = {
        "physical_shape": (ni, int(data.shape[1])),
        "storage_shape": storage_shape,
        "returned_shape": storage_shape,
        "axis_order": ("F1", "F2"),
        "trace_order": "phase=1,2 successive within each d2 increment",
        "trace_pairing": "trace[2a]=phase=1; trace[2a+1]=phase=2",
        "stored_trace_count": int(data.shape[0]),
        "physical_indirect_increments": ni,
        "states_branches": 2,
        "TD": (arraydim, np_raw),
        "component_basis": ("complex",),
    }
    acquisition = {
        "axes": (
            {
                "name": "F1",
                "TD": arraydim,
                "physical_increments": ni,
                "stored_traces": int(data.shape[0]),
                "branches": 2,
                "SW_hz": sw_f1,
                "dwell_time_s": None if sw_f1 is None else 1.0 / sw_f1,
                "observation_frequency_mhz": obs_f1,
                "phase": phase,
            },
            {
                "name": "F2",
                "TD": np_raw,
                "returned_points": int(data.shape[1]),
                "SW_hz": sw_f2,
                "dwell_time_s": None if sw_f2 is None else 1.0 / sw_f2,
                "observation_frequency_mhz": obs_f2,
            },
        ),
        "np": np_raw,
        "ni": ni,
        "arraydim": arraydim,
        "ntraces": ntraces,
        "phase": phase,
        "array": _procpar_string(procpar, "array"),
        "seqcon": _procpar_string(procpar, "seqcon"),
        "NS": _procpar_number(procpar, "ns"),
        "NE": _procpar_number(procpar, "ne"),
        "normalization": "none",
        "storage_convention": "raw complex traces, phase branches successive",
        "conjugation": "none",
        "trace_reordering": "none",
    }
    return ReadResult(
        data=data,
        axes=(f1_axis, f2_axis),
        metadata=dic,
        components=(Component("complex", data),),
        applied_corrections={
            "normalization": "none",
            "conjugation": "none",
            "trace_reordering": "none",
        },
        diagnostics=diagnostics,
        format="agilent-states-2d",
        source=dir,
        domains=("time", "time"),
        encoding=("STATES", "QSIM"),
        dimensions=dimensions,
        acquisition=acquisition,
    )


def _agilent_2d_storage_shape(procpar, *, tppi):
    """Require an unambiguous single indirect dimension."""
    ni = _procpar_integer(procpar, "ni")
    words = _procpar_integer(procpar, "np")
    phases = (3,) if tppi else (1, 2)
    array = procpar.get("array", {}).get("values")
    allowed_arrays = (None, [""], ("",)) if tppi else (["phase"], ("phase",))
    if tppi and _procpar_string(procpar, "sampling", "").strip().lower() not in (
        "", "uniform"
    ):
        raise ValueError("Agilent TPPI storage requires uniform sampling")
    if (
        _procpar_phase(procpar) != phases
        or "seqcon" in procpar
        or array not in allowed_arrays
        or any(
            key in procpar and (tppi or _procpar_integer(procpar, key) != 0)
            for key in ("ni2", "ni3")
        )
        or ni is None or ni < (2 if tppi else 1)
        or _procpar_integer(procpar, "arraydim") != len(phases) * ni
        or words is None or words < 2 or words % 2
    ):
        if tppi:
            raise ValueError("Agilent TPPI storage requires phase=[3], ni>=2 and arraydim=ni")
        raise ValueError("Agilent States storage requires only phase=[1, 2] and arraydim=2*ni")
    return len(phases) * ni, words


def _agilent_series_shape(procpar, blocks, traces):
    """Recognize a flat series without declared indirect acquisition axes."""
    words = _procpar_integer(procpar, "np")
    nf = _procpar_integer(procpar, "nf")
    if (
        blocks < 1 or traces < 1 or blocks * traces < 2
        or words is None or words < 2 or words % 2
        or _procpar_integer(procpar, "arraydim") != blocks
        or any(key in procpar for key in ("ni", "ni2", "ni3", "seqcon", "sw2"))
        or _procpar_phase(procpar) != ()
        or ("nf" in procpar and nf != traces)
    ):
        raise ValueError("Agilent FID series requires a flat trace layout")
    shape = varian.find_shape(procpar)
    if shape not in ((words // 2,), (blocks * traces, words // 2)):
        raise ValueError("Agilent FID series does not match the declared procpar shape")
    return blocks * traces, words


_STATES_PROGRAMS = {
    ("NOESY", "94af3b927aa56a1c2891f4dff344eb360454564c63e1173a781d00ceecd94140"): (
        "states-tppi",
        "https://github.com/OpenVnmrJ/OpenVnmrJ/blob/0f6b0a4664def0cdf2ee9eb37cb2df7369f38ca3/src/psglib/NOESY.c",
    ),
}


def _select_states_quadrature(result, quadrature, pulse_program_source):
    if quadrature not in ("auto", "states", "states-tppi"):
        raise ValueError("Agilent quadrature must be auto, states or states-tppi")
    procpar = result.metadata.get("procpar", {})
    names = procpar.get("seqfil", {}).get("values", ())
    sequence = names[0] if len(names) == 1 and isinstance(names[0], str) else None
    selection = {"mode": None, "source": "undetermined", "sequence": sequence}
    if quadrature != "auto":
        if pulse_program_source is not None:
            raise ValueError("pulse_program_source requires automatic quadrature")
        selection.update(mode=quadrature, source="manual")
        return selection

    explicit = pulse_program_source is not None
    if not explicit:
        if not any(name == sequence for name, _ in _STATES_PROGRAMS):
            return selection
        candidate = Path(result.source).parent / f"{sequence}.c"
        if candidate.is_symlink() or not candidate.is_file():
            return selection
        pulse_program_source = candidate
    try:
        with Path(pulse_program_source).open("rb") as stream:
            source = stream.read(256 * 1024 + 1)
    except OSError:
        if explicit:
            raise
        return selection
    if len(source) > 256 * 1024:
        if explicit:
            raise ValueError("Agilent pulse program source exceeds 256 KiB")
        return selection
    fingerprint = hashlib.sha256(source).hexdigest()
    selection["sha256"] = fingerprint
    known = _STATES_PROGRAMS.get((sequence, fingerprint))
    d2 = procpar.get("d2", {}).get("values", ())
    if known is None or len(d2) != 1:
        return selection
    try:
        initial_delay = _procpar_number(procpar, "d2")
    except ValueError:
        return selection
    if initial_delay == 0:
        mode, reference = known
        selection.update(mode=mode, source="pulse-program", reference=reference)
    return selection


def normalize_agilent_states_2d(
    result, *, legacy_presentation=False, quadrature=None, pulse_program_source=None,
):
    """Pair verified Varian storage as two complex States branches in file order.

    Accept the scalar result of :func:`read_agilent_fid_storage`. The default
    uses physical time coordinates when known. The compatibility presentation
    preserves the historical public axes and explicit NS/NE divisor. Neither
    presentation applies phase, alternation, conjugation or an FFT.

    With quadrature="states" or "states-tppi", record the caller's choice.
    With quadrature="auto", recognize a supplied or adjacent pulse program
    source by sequence name and SHA-256. An unmatched source leaves F1
    quadrature undetermined.
    Samples remain in storage order. A selected mode describes the transport
    needed for NMRPipe-convention FFT processing.
    """
    return _normalize_agilent_2d(
        result, legacy_presentation, mode="states", quadrature=quadrature,
        pulse_program_source=pulse_program_source,
    )


def normalize_agilent_tppi_2d(result, *, legacy_presentation=False):
    """Normalize verified Varian phase=[3] scalar storage in acquisition order.

    Preserve one complex FID per F1 increment. The indirect TPPI phase
    convention is retained for downstream processing.
    """
    return _normalize_agilent_2d(result, legacy_presentation, mode="tppi")


def normalize_agilent_fid_series(result, *, legacy_presentation=False):
    """Decode a flat Agilent/Varian FID series in block and trace order.

    The leading axis is a trace index with no physical time calibration.
    Each row retains its complex F2 samples and acquisition provenance.
    """
    return _normalize_agilent_2d(result, legacy_presentation, mode="series")


def _normalize_agilent_fid_storage(result, *, legacy_presentation=False, **options):
    procpar = result.metadata.get("procpar", {})
    phase = _procpar_phase(procpar)
    normalizer = {
        (): normalize_agilent_fid_series,
        (3,): normalize_agilent_tppi_2d,
    }.get(phase, normalize_agilent_states_2d)
    return normalizer(result, legacy_presentation=legacy_presentation, **options)


def _normalize_agilent_2d(
    result, legacy_presentation, *, mode, quadrature=None, pulse_program_source=None,
):
    series = mode == "series"
    states = mode == "states"
    tppi = mode == "tppi"
    if not isinstance(result, ReadResult):
        raise TypeError("Agilent 2D normalization requires an interop ReadResult")
    if result.format != "agilent-fid-storage":
        raise ValueError("Agilent 2D normalization requires scalar FID storage")

    metadata = result.metadata
    procpar = metadata.get("procpar", {})
    blocks = metadata.get("nblocks", 0)
    traces_per_block = metadata.get("ntraces", 0)
    rows, words = (
        _agilent_series_shape(procpar, blocks, traces_per_block)
        if series else _agilent_2d_storage_shape(procpar, tppi=tppi)
    )
    if tppi and metadata.get("sampling_schedule_present"):
        raise ValueError("Agilent TPPI storage requires uniform sampling")
    if series and metadata.get("sampling_schedule_present"):
        raise ValueError("Agilent FID series does not accept a sampling schedule")
    if (
        result.data.shape != (rows, words)
        or metadata.get("np") != words
        or (not series and (blocks != rows or traces_per_block != 1))
        or (series and (metadata.get("S_DATA") != 1 or metadata.get("S_COMPLEX") != 1))
        or metadata.get("S_SPEC") != 0
        or metadata.get("S_HYPERCOMPLEX") != 0
        or not np.isfinite(result.data).all()
    ):
        raise ValueError("Agilent 2D storage disagrees with the declared raw trace geometry")
    traces = varian.uninterleave_data(result.data)
    data = np.stack((traces[::2], traces[1::2])) if states else traces
    direct_width = _procpar_number(procpar, "sw")
    indirect_width = None if series else _procpar_number(procpar, "sw1")
    transmitters = tuple(_procpar_number(procpar, key) for key in ("sfrq2", "sfrq"))
    observation = tuple(frequency or None for frequency in transmitters)
    reported_nuclei = tuple(
        _procpar_string(procpar, dn) or _procpar_string(procpar, tn)
        for dn, tn in (("dn2", "tn2"), ("dn", "tn"))
    )
    widths = (indirect_width, direct_width)
    selection = None
    if quadrature is not None or pulse_program_source is not None:
        selection = _select_states_quadrature(
            result, "auto" if quadrature is None else quadrature, pulse_program_source
        )
    selected = selection is not None and selection["mode"] is not None
    if selected:
        sampling = procpar.get("sampling", {}).get("values", ())
        uniform = not sampling or (
            len(sampling) == 1
            and isinstance(sampling[0], str)
            and sampling[0].strip().lower() in ("", "uniform")
        )
        legacy_float_status = 0xC9
        block_headers = metadata.get("blockheader", ())
        complex_storage = metadata.get("S_COMPLEX") == 1 or (
            metadata.get("status") == legacy_float_status
            and len(block_headers) == blocks
            and all(header.get("status") == legacy_float_status for header in block_headers)
        )
        if (
            not uniform or metadata.get("sampling_schedule_present")
            or any(width is None or width <= 0 for width in widths)
            or min(data.shape[-2:]) < 2
            or metadata.get("S_DATA") != 1 or metadata.get("S_TRANSF")
            or not complex_storage
        ):
            if selection["source"] == "manual":
                raise ValueError(
                    "Agilent States processing requires raw complex storage and "
                    "complete calibrated F1/F2 grids"
                )
            selection.update(mode=None, source="undetermined", reason="ineligible-time-grid")
            selected = False
    nuclei = (reported_nuclei[0], _procpar_string(procpar, "tn"))
    if tppi:
        nuclei = (_procpar_string(procpar, "tn2") or None, nuclei[1])
    if series:
        nuclei = (None, nuclei[1])
        observation = (None, observation[1])
    acquisition = {
        "spectral_widths_hz": widths,
        "observation_frequencies_mhz": observation,
        "nuclei": nuclei,
        "phase": _procpar_phase(procpar),
        "physical_indirect_increments": None if series else rows // 2 if states else rows,
        "storage_shape": (rows, words),
    }
    if selection is not None:
        acquisition["quadrature_selection"] = selection
    if selected:
        acquisition["spectral_width_hz"] = widths
        acquisition["states_fft_input_transform"] = "conjugate-and-negate-second-branch"
    physical = ("trace", "F2") if series else ("F1", "F2")
    dimensions = ("channels", *physical) if states else physical
    if series:
        acquisition.update(blocks=blocks, traces_per_block=traces_per_block)
    decode = {
        "name": "pair-states-traces" if states else f"decode-{mode}-traces",
        "stage": "acquisition",
        "input_dimensions": ("trace", "word"),
        "output_dimensions": dimensions,
        "axis": "F2" if series else "F1",
        "scale": None,
        "conjugation": "none",
        "sign": "none",
        "permutation": "even traces to first branch, odd traces to second branch" if states else None,
        "evidence": (
            "procpar phase=[3] and binary block order"
            if tppi else "procpar phase=[1, 2], array=phase and binary block order"
            if states else "binary block and trace order"
        ),
    }
    operations = (decode,)
    if legacy_presentation:
        from .normalize import _scale_agilent_ns_ne

        ns = _procpar_number(procpar, "ns")
        ne = _procpar_number(procpar, "ne")
        data, divisor = _scale_agilent_ns_ne(data, ns, ne)
        decoupler = tuple(_procpar_number(procpar, key) for key in ("dfrq2", "dfrq"))
        displayed_observation = tuple(
            fallback if transmitter is None else transmitter
            for transmitter, fallback in zip(transmitters, decoupler, strict=True)
        )
        display_widths = (_procpar_number(procpar, "sw2"), direct_width)
        if not selected:
            widths = display_widths
            nuclei = reported_nuclei
        acquisition["legacy_presentation"] = {
            "spectral_widths_hz": display_widths,
            "observation_frequencies_mhz": displayed_observation,
            "decoupler_frequencies_mhz": decoupler,
            "reported_nuclei": reported_nuclei,
            "pulse_program": _procpar_string(procpar, "array") or _procpar_string(procpar, "pulprog"),
            "sequence": _procpar_string(procpar, "seqfil"),
            "date_raw": _procpar_string(procpar, "date"),
            "acquisition_time_s": _procpar_number(procpar, "at"),
            "ns": 1.0 if ns is None else ns,
            "ne": 1.0 if ne is None else ne,
        }
        operations += ({
            **decode,
            "name": "normalize-agilent-ns-ne",
            "input_dimensions": dimensions,
            "axis": None,
            "scale": 1 / divisor,
            "divisor": divisor,
            "permutation": None,
            "evidence": "procpar.ns and procpar.ne",
        },)
    axes = []
    for size, width, frequency, nucleus in zip(
        data.shape[-2:], widths, observation, nuclei, strict=True
    ):
        if any(value is not None and value <= 0 for value in (width, frequency)):
            raise ValueError("Agilent 2D widths and observation frequencies must be positive")
        axes.append(Axis(
            values=None if width is None else np.arange(size, dtype=float) * (1 / width),
            unit=None if width is None else "s",
            label=nucleus,
            domain="time",
            direction="unknown" if width is None else "increasing",
            reference=None if frequency is None else Reference(
                observation_frequency=frequency,
                observation_frequency_unit="MHz",
                source="acquisition",
            ),
        ))
    if series:
        axes[0] = Axis(label="trace")
    return NormalizedAcquisition(
        data=data,
        axes=tuple(axes),
        dimensions=dimensions,
        physical_dimensions=physical,
        domains=("unknown", "time") if series else ("time", "time"),
        quadrature_mode=f"{mode}-stored-2d",
        branch_order=("branch_0", "branch_1") if states else ("complex",),
        normalization_state="storage-normalized",
        normalization_profile=f"agilent-{mode}-2d-v1",
        applied_operations=operations,
        provenance={"source": os.fspath(result.source), "format": result.format},
        acquisition=acquisition,
        metadata=metadata,
        encoding=("unknown" if series else mode, "complex"),
        diagnostics=result.diagnostics,
        channel_axis=0 if states else None,
    )
