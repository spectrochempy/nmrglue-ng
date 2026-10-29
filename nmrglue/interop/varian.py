"""Agilent/Varian adapters for the neutral interop layer."""

from __future__ import annotations

import math
import os

import numpy as np

from ..fileio import varian
from .result import Axis, Component, Diagnostic, ReadResult, Reference


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


def read_agilent_fid(
    dir=".",
    *,
    shape=None,
    torder=None,
    read_blockhead=False,
    carrier_hz=None,
    carrier_ppm=None,
):
    """Read an Agilent/Varian raw 1D FID as a neutral ``ReadResult``.

    The historical Varian reader performs all binary and ``procpar`` parsing.
    This adapter applies no scan normalization or conjugation. A carrier must
    be supplied explicitly in Hz or ppm for NMRPipe export; ``rfl`` and other
    procpar reference candidates are preserved but never interpreted silently.
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
    if data.ndim != 1 or not np.iscomplexobj(data):
        raise ValueError("the Agilent raw 1D profile requires one complex FID")

    procpar = dic.get("procpar", {})
    sw = _procpar_number(procpar, "sw")
    obs = _procpar_number(procpar, "sfrq")
    np_raw = _procpar_number(procpar, "np")
    ns = _procpar_number(procpar, "ns")
    ne = _procpar_number(procpar, "ne")
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
        label=_procpar_string(procpar, "dn") or _procpar_string(procpar, "tn"),
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
        "nucleus": _procpar_string(procpar, "dn") or _procpar_string(procpar, "tn"),
        "np_raw": np_raw,
        "NS": ns,
        "NE": ne,
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
            "states_pairing": "declared_not_applied",
        },
        diagnostics=diagnostics,
        format="agilent-states-2d",
        source=dir,
        domains=("time", "time"),
        encoding=("STATES", "QSIM"),
        dimensions=dimensions,
        acquisition=acquisition,
    )
