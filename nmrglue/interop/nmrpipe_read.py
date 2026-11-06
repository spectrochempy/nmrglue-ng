"""Strict processed NMRPipe 1D input for the neutral interoperability layer."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from ..fileio import pipe
from .result import Axis, Component, NormalizedAcquisition, ReadResult, Reference


def _geometry(header, max_points):
    def number(key):
        value = header.get(key)
        if isinstance(value, (bool, np.bool_)) or not isinstance(
            value, (int, float, np.integer, np.floating)
        ) or not np.isfinite(value):
            raise ValueError("NMRPipe requires finite numeric " + key)
        return float(value)

    for key, expected in (("FDDIMCOUNT", 1), ("FDDIMORDER1", 2),
                          ("FDTRANSPOSED", 0), ("FDF2FTFLAG", 1)):
        if number(key) != expected:
            raise ValueError("NMRPipe processed 1D profile requires %s=%s" % (key, expected))
    quad = number("FDF2QUADFLAG")
    if quad not in (0, 1) or number("FDQUADFLAG") != quad:
        raise ValueError("NMRPipe requires consistent real/complex quadrature flags")
    for key in ("FDF2X1", "FDF2XN"):
        if number(key) != 0:
            raise ValueError("NMRPipe extracted grids are not qualified")
    size = number("FDSIZE")
    if size < 2 or not size.is_integer():
        raise ValueError("NMRPipe requires integer FDSIZE >= 2")
    size = int(size)
    if size > max_points:
        raise ValueError("NMRPipe FDSIZE exceeds available samples")
    sw, obs, orig = (number(key) for key in ("FDF2SW", "FDF2OBS", "FDF2ORIG"))
    if sw <= 0 or obs <= 0:
        raise ValueError("NMRPipe SW and OBS must be positive")
    values = orig + (size - 1 - np.arange(size, dtype=float)) * (sw / size)
    if not np.isfinite(values).all() or not np.all(np.diff(values) < 0):
        raise ValueError("NMRPipe frequency grid must be finite and strictly decreasing")
    axis = Axis(
        values=values, unit="Hz", label=header.get("FDF2LABEL"),
        domain="frequency", direction="decreasing",
        reference=Reference(observation_frequency=obs,
                            observation_frequency_unit="MHz", source="processing"),
    )
    return size, quad == 0, axis, sw


def read_nmrpipe_1d(filename):
    """Read a complete real/complex frequency-domain 1D NMRPipe file.

    Only a filesystem path is accepted. Header geometry and exact payload size
    are checked before delegating binary decoding to the historical pipe reader.
    No FFT, conjugation, gain/scan scaling or chemical recalibration is applied.
    ORIG is the last-point frequency in Hz; CAR is retained but not substituted.
    """
    path = Path(filename)
    if path.stat().st_size < 2048:
        raise ValueError("NMRPipe requires a complete 2048-byte header")
    header = pipe.fdata2dic(pipe.get_fdata(path))
    size, complex_data, axis, sw = _geometry(header, (path.stat().st_size - 2048) // 4)
    expected_bytes = 2048 + size * 4 * (2 if complex_data else 1)
    if path.stat().st_size != expected_bytes:
        raise ValueError("NMRPipe payload size disagrees with FDSIZE/quadrature")
    header, data = pipe.read(path)
    if data.shape != (size,) or not np.isfinite(data).all():
        raise ValueError("NMRPipe requires one finite spectrum matching FDSIZE")
    mode = "complex" if complex_data else "real"
    return ReadResult(
        data=data, axes=(axis,), metadata=header,
        components=(Component(name=mode, data=data),),
        applied_corrections={"normalization": "none", "conjugation": "none"},
        diagnostics=(), format="nmrpipe-1d", source=os.fspath(filename),
        domains=("frequency",), encoding=("complex" if complex_data else "real",),
        dimensions={"FDSIZE": size},
        acquisition={"spectral_width_hz": sw,
                     "observation_frequency_mhz": axis.reference.observation_frequency,
                     "normalization": "none"},
    )


def normalize_nmrpipe_1d(result):
    """Validate an interop NMRPipe spectrum without altering its samples."""
    if not isinstance(result, ReadResult) or result.format != "nmrpipe-1d":
        raise ValueError("normalize_nmrpipe_1d requires a nmrpipe-1d ReadResult")
    data = np.asarray(result.data)
    size, complex_data, axis, sw = _geometry(result.metadata, data.size)
    mode = "complex" if complex_data else "real"
    if (data.shape != (size,) or data.dtype.kind not in "iufc"
        or np.iscomplexobj(data) != complex_data or not np.isfinite(data).all()
        or result.domains != ("frequency",) or result.encoding != (mode,)):
        raise ValueError("NMRPipe normalized data disagrees with its header")
    if len(result.axes) != 1:
        raise ValueError("NMRPipe requires one calibrated axis")
    supplied = result.axes[0]
    if (supplied.domain != axis.domain or supplied.unit != axis.unit
        or supplied.direction != axis.direction or supplied.reference != axis.reference
        or supplied.values is None or not np.array_equal(supplied.values, axis.values)):
        raise ValueError("NMRPipe axis disagrees with its header")
    if (len(result.components) != 1 or result.components[0].name != mode
        or not np.array_equal(result.components[0].data, data)):
        raise ValueError("NMRPipe component disagrees with its samples")
    corrections = {"normalization": "none", "conjugation": "none"}
    if dict(result.applied_corrections) != corrections:
        raise ValueError("NMRPipe has unrecognized corrections")
    operation = {
        "name": "normalize-nmrpipe-spectrum", "stage": "processing",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": None, "conjugation": "none", "sign": "none",
        "permutation": None, "evidence": "nmrglue.interop.read_nmrpipe_1d",
    }
    return NormalizedAcquisition(
        data=data, axes=(axis,), dimensions=("F2",), physical_dimensions=("F2",),
        domains=("frequency",), quadrature_mode=mode + "-1d", branch_order=(mode,),
        normalization_state="storage-normalized", normalization_profile="nmrpipe-spectrum-1d-v1",
        applied_operations=(operation,),
        provenance={"source": result.source, "format": result.format},
        acquisition={"spectral_width_hz": sw,
                     "observation_frequency_mhz": axis.reference.observation_frequency,
                     "reference_source": "processing", "normalization": "none"},
        metadata=result.metadata, encoding=result.encoding, diagnostics=result.diagnostics,
    )
