"""Interoperability for single-element SIMPSON data."""

from io import StringIO
from math import prod
import os
from pathlib import Path

import numpy as np

from ..fileio import simpson
from .result import Axis, Component, NormalizedAcquisition, ReadResult


def _geometry(header, kind, ndim):
    if (
        header.get("TYPE") != kind or ("NI" in header) != (ndim == 2)
        or header.get("NELEM", 1) != 1
    ):
        raise ValueError(f"SIMPSON requires single-element {ndim}D {kind} data")
    point_keys = ("NP",) if ndim == 1 else ("NI", "NP")
    width_keys = ("SW",) if ndim == 1 else ("SW1", "SW")
    shape = tuple(header.get(key) for key in point_keys)
    widths = tuple(header.get(key) for key in width_keys)
    for key, points in zip(point_keys, shape):
        if type(points) is not int or not 1 <= points <= np.iinfo(np.intp).max:
            raise ValueError(f"SIMPSON requires a positive {key} within index range")
    for key, points, width in zip(width_keys, shape, widths):
        if not isinstance(width, (int, float)) or not np.isfinite(width) or width <= 0:
            raise ValueError(f"SIMPSON requires a finite positive {key} in Hz")
        if kind == "FID" and not np.isfinite(points / width):
            raise ValueError("SIMPSON FID time range is outside float range")
    if "FORMAT" in header and header["FORMAT"] != "BINARY":
        raise ValueError("SIMPSON requires TEXT or FORMAT=BINARY")
    return shape, widths


def _preflight(stream, kind, ndim):
    # The historical TEXT decoder preallocates NP points. Check the block
    # length first so that truncation cannot expose uninitialized samples.
    if stream.readline().rstrip("\n") != "SIMP":
        raise ValueError("SIMPSON requires a SIMP header")
    header = {}
    for line in stream:
        line = line.rstrip("\n")
        if line == "DATA":
            break
        key, sep, value = line.partition("=")
        if not sep or not key or not value or key in header or "=" in value:
            raise ValueError("SIMPSON has an invalid or duplicate header record")
        header[key] = value
    else:
        raise ValueError("SIMPSON requires a DATA block")
    for key in ("NP", "NI", "NELEM"):
        if key in header:
            header[key] = int(header[key])
    for key in ("SW", "SW1"):
        if key in header:
            header[key] = float(header[key])
    shape, _ = _geometry(header, kind, ndim)
    points = prod(shape)
    binary = "FORMAT" in header
    if binary:
        lines = [line.rstrip("\n") for line in stream]
        if "END" in lines[:-1]:
            raise ValueError("SIMPSON BINARY block has a premature END")
        payload = "".join(lines)
        expected = 4 * ((8 * points + 2) // 3)
        if (not payload.endswith("END") or len(payload) != expected + 3
                or any(not 33 <= ord(char) <= 96 for char in payload[:-3])):
            raise ValueError("SIMPSON BINARY block disagrees with NP or lacks END")
    else:
        count = 0
        for line in stream:
            if line.rstrip("\n") == "END":
                break
            if line.startswith("END") or len(line.split()) != 2:
                raise ValueError("SIMPSON TEXT requires two ordinates per row")
            count += 1
        else:
            raise ValueError("SIMPSON TEXT requires END")
        if count != points or stream.read().strip():
            raise ValueError("SIMPSON TEXT block disagrees with NP")
    return "BINARY" if binary else "TEXT"


def _axes(header, data, kind, ndim):
    shape, widths = _geometry(header, kind, ndim)
    if data.shape != shape or data.dtype.kind != "c" or not np.isfinite(data).all():
        raise ValueError("SIMPSON requires finite complex samples matching the declared shape")
    if kind == "FID":
        return tuple(
            Axis(values=np.arange(points, dtype=float) / width, unit="s", label=label,
                 domain="time", direction="increasing")
            for points, width, label in zip(shape, widths, ("time",) if ndim == 1 else ("F1", "F2"))
        )
    points, = shape
    width, = widths
    indices = np.arange(points, dtype=float)
    try:
        reference = float(header.get("REF", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("SIMPSON requires a finite REF in Hz") from exc
    if not np.isfinite(reference):
        raise ValueError("SIMPSON requires a finite REF in Hz")
    with np.errstate(over="ignore"):
        frequencies = reference + (indices / points - 0.5) * width
    if not np.isfinite(frequencies).all() or not np.all(np.diff(frequencies) > 0):
        raise ValueError("SIMPSON frequency axis is not strictly increasing")
    return (Axis(values=frequencies, unit="Hz", label="frequency",
                 domain="frequency", direction="increasing"),)


def _storage_dimensions(data):
    if data.ndim == 1:
        return {"points": data.size}
    return {"shape": data.shape, "axis_order": ("F1", "F2")}


def _read(filename, kind, format_name, ndim=1):
    # Validate and decode the same snapshot, even if the path is replaced.
    with StringIO(Path(filename).read_text(encoding="ascii")) as stream:
        file_type = _preflight(stream, kind, ndim)
        stream.seek(0)
        decoder = simpson._read_binary if file_type == "BINARY" else simpson._read_text
        header, data = decoder(stream)
    axes = _axes(header, data, kind, ndim)
    return ReadResult(
        data=data, axes=axes, metadata=header, components=(Component("complex", data),),
        applied_corrections={}, diagnostics=(), format=format_name,
        source=os.fspath(filename), domains=tuple(axis.domain for axis in axes),
        encoding=("complex",) if ndim == 1 else ("unknown", "complex"),
        dimensions=_storage_dimensions(data),
    )


def read_simpson_fid(filename):
    """Read a single-element 1D SIMPSON TEXT or BINARY FID."""
    return _read(filename, "FID", "simpson-fid-1d")


def read_simpson_spectrum(filename):
    """Read a single-element 1D SIMPSON TEXT or BINARY spectrum."""
    return _read(filename, "SPE", "simpson-spectrum-1d")


def read_simpson_fid_2d(filename):
    """Read a single-element 2D SIMPSON TEXT or BINARY FID in F1/F2 order."""
    return _read(filename, "FID", "simpson-fid-2d", ndim=2)


def normalize_simpson_fid(result, *, conjugation):
    """Validate a SIMPSON FID and apply the caller's sign convention."""
    if conjugation not in ("none", "conjugate"):
        raise ValueError("SIMPSON requires conjugation='none' or 'conjugate'")
    return _normalize(result, "FID", "simpson-fid-1d", conjugation)


def normalize_simpson_spectrum(result):
    """Validate a SIMPSON spectrum and retain its samples and frequency axis."""
    return _normalize(result, "SPE", "simpson-spectrum-1d", "none")


def normalize_simpson_fid_2d(result, *, conjugation):
    """Normalize a SIMPSON 2D FID with an explicit direct-axis sign choice."""
    if conjugation not in ("none", "conjugate"):
        raise ValueError("SIMPSON requires conjugation='none' or 'conjugate'")
    return _normalize(result, "FID", "simpson-fid-2d", conjugation, ndim=2)


def _normalize(result, kind, format_name, conjugation, ndim=1):
    if not isinstance(result, ReadResult) or result.format != format_name:
        raise ValueError(f"SIMPSON normalization requires a {format_name} ReadResult")
    axes = _axes(result.metadata, result.data, kind, ndim)
    dimensions = ("F2",) if ndim == 1 else ("F1", "F2")
    domains = tuple(axis.domain for axis in axes)
    encoding = ("complex",) if ndim == 1 else ("unknown", "complex")
    if (
        result.domains != domains or result.encoding != encoding
        or result.dimensions != _storage_dimensions(result.data) or result.applied_corrections
        or len(result.axes) != ndim or len(result.components) != 1
        or result.components[0].name != "complex"
        or not np.array_equal(result.components[0].data, result.data)
    ):
        raise ValueError("SIMPSON description disagrees with its samples")
    if any(
        observed.unit != axis.unit or observed.domain != axis.domain
        or observed.direction != axis.direction or not np.array_equal(observed.values, axis.values)
        for observed, axis in zip(result.axes, axes)
    ):
        raise ValueError("SIMPSON axes disagree with the declared sweep widths")
    width = result.metadata["SW"]
    acquisition = {"spectral_width_hz": width}
    if kind == "FID":
        acquisition["dwell_time_s"] = 1 / width
    if ndim == 2:
        width1 = result.metadata["SW1"]
        acquisition = {"spectral_width_hz": (width1, width),
                       "dwell_time_s": (1 / width1, 1 / width)}
    operation_name = format_name.removesuffix("-1d")
    operation = {
        "name": f"normalize-{operation_name}",
        "stage": "acquisition" if kind == "FID" else "processing",
        "input_dimensions": ("storage",) if ndim == 1 else dimensions,
        "output_dimensions": dimensions,
        "axis": "F2", "scale": None, "conjugation": conjugation, "sign": "none",
        "permutation": None,
        "evidence": ("SIMPSON NI/NP, SW1/SW and caller-selected conjugation" if ndim == 2
                     else "SIMPSON NP/SW and caller-selected conjugation" if kind == "FID"
                     else "SIMPSON XREIM bin convention and NP/SW"),
    }
    return NormalizedAcquisition(
        data=result.data.conj() if conjugation == "conjugate" else result.data,
        axes=axes, dimensions=dimensions, physical_dimensions=dimensions,
        domains=domains,
        quadrature_mode="complex-1d" if ndim == 1 else "simpson-stored-complex-2d",
        branch_order=("complex",),
        normalization_state="storage-normalized", normalization_profile=f"{format_name}-v1",
        applied_operations=(operation,), provenance={"source": result.source, "format": result.format},
        acquisition=acquisition, metadata=result.metadata, encoding=result.encoding,
        diagnostics=result.diagnostics,
    )
