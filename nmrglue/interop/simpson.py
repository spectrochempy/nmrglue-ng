"""Interoperability for single-element 1D SIMPSON data."""

from io import StringIO
import os
from pathlib import Path

import numpy as np

from ..fileio import simpson
from .result import Axis, Component, NormalizedAcquisition, ReadResult


def _geometry(header, kind):
    if header.get("TYPE") != kind or "NI" in header or header.get("NELEM", 1) != 1:
        raise ValueError(f"SIMPSON requires single-element 1D {kind} data")
    points = header.get("NP")
    width = header.get("SW")
    if type(points) is not int or points < 1:
        raise ValueError("SIMPSON requires a positive NP")
    if not isinstance(width, (int, float)) or not np.isfinite(width) or width <= 0:
        raise ValueError("SIMPSON requires a finite positive SW in Hz")
    if kind == "FID" and not np.isfinite(points / width):
        raise ValueError("SIMPSON FID time range is outside float range")
    if "FORMAT" in header and header["FORMAT"] != "BINARY":
        raise ValueError("SIMPSON requires TEXT or FORMAT=BINARY")
    return points, width


def _preflight(stream, kind):
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
    for key in ("NP", "NELEM"):
        if key in header:
            header[key] = int(header[key])
    if "SW" in header:
        header["SW"] = float(header["SW"])
    points, _ = _geometry(header, kind)
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


def _axis(header, data, kind):
    points, width = _geometry(header, kind)
    if data.shape != (points,) or data.dtype.kind != "c" or not np.isfinite(data).all():
        raise ValueError("SIMPSON requires finite complex samples matching NP")
    indices = np.arange(points, dtype=float)
    if kind == "FID":
        return Axis(values=indices / width, unit="s", label="time",
                    domain="time", direction="increasing")
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
    return Axis(values=frequencies, unit="Hz", label="frequency",
                domain="frequency", direction="increasing")


def _read_1d(filename, kind, format_name):
    # Validate and decode the same snapshot, even if the path is replaced.
    with StringIO(Path(filename).read_text(encoding="ascii")) as stream:
        file_type = _preflight(stream, kind)
        stream.seek(0)
        decoder = simpson._read_binary if file_type == "BINARY" else simpson._read_text
        header, data = decoder(stream)
    axis = _axis(header, data, kind)
    return ReadResult(
        data=data, axes=(axis,), metadata=header, components=(Component("complex", data),),
        applied_corrections={}, diagnostics=(), format=format_name,
        source=os.fspath(filename), domains=(axis.domain,), encoding=("complex",),
        dimensions={"points": data.size},
    )


def read_simpson_fid(filename):
    """Read a single-element 1D SIMPSON TEXT or BINARY FID."""
    return _read_1d(filename, "FID", "simpson-fid-1d")


def read_simpson_spectrum(filename):
    """Read a single-element 1D SIMPSON TEXT or BINARY spectrum."""
    return _read_1d(filename, "SPE", "simpson-spectrum-1d")


def normalize_simpson_fid(result, *, conjugation):
    """Validate a SIMPSON FID and apply the caller's sign convention."""
    if conjugation not in ("none", "conjugate"):
        raise ValueError("SIMPSON requires conjugation='none' or 'conjugate'")
    return _normalize_1d(result, "FID", "simpson-fid-1d", conjugation)


def normalize_simpson_spectrum(result):
    """Validate a SIMPSON spectrum and retain its samples and frequency axis."""
    return _normalize_1d(result, "SPE", "simpson-spectrum-1d", "none")


def _normalize_1d(result, kind, format_name, conjugation):
    if not isinstance(result, ReadResult) or result.format != format_name:
        raise ValueError(f"SIMPSON normalization requires a {format_name} ReadResult")
    axis = _axis(result.metadata, result.data, kind)
    if (
        result.domains != (axis.domain,) or result.encoding != ("complex",)
        or result.dimensions != {"points": result.data.size} or result.applied_corrections
        or len(result.axes) != 1 or len(result.components) != 1
        or result.components[0].name != "complex"
        or not np.array_equal(result.components[0].data, result.data)
    ):
        raise ValueError("SIMPSON description disagrees with its samples")
    observed = result.axes[0]
    if (
        observed.unit != axis.unit or observed.domain != axis.domain
        or observed.direction != axis.direction or not np.array_equal(observed.values, axis.values)
    ):
        raise ValueError("SIMPSON axis disagrees with SW")
    width = result.metadata["SW"]
    acquisition = {"spectral_width_hz": width}
    if kind == "FID":
        acquisition["dwell_time_s"] = 1 / width
    operation = {
        "name": "normalize-simpson-fid" if kind == "FID" else "normalize-simpson-spectrum",
        "stage": "acquisition" if kind == "FID" else "processing",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": None, "conjugation": conjugation, "sign": "none",
        "permutation": None,
        "evidence": ("SIMPSON NP/SW and caller-selected conjugation" if kind == "FID"
                     else "SIMPSON XREIM bin convention and NP/SW"),
    }
    return NormalizedAcquisition(
        data=result.data.conj() if conjugation == "conjugate" else result.data,
        axes=(axis,), dimensions=("F2",), physical_dimensions=("F2",),
        domains=result.domains, quadrature_mode="complex-1d", branch_order=("complex",),
        normalization_state="storage-normalized", normalization_profile=f"{format_name}-v1",
        applied_operations=(operation,), provenance={"source": result.source, "format": result.format},
        acquisition=acquisition,
        metadata=result.metadata, encoding=result.encoding, diagnostics=result.diagnostics,
    )
