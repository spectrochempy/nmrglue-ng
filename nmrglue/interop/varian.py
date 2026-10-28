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
