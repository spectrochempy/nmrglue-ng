"""Interoperability for single-element 1D SIMPSON FIDs."""

from io import StringIO
import os
from pathlib import Path

import numpy as np

from ..fileio import simpson
from .result import Axis, Component, NormalizedAcquisition, ReadResult


def _fid_geometry(header):
    if header.get("TYPE") != "FID" or "NI" in header or header.get("NELEM", 1) != 1:
        raise ValueError("SIMPSON requires a single-element 1D FID")
    points = header.get("NP")
    width = header.get("SW")
    if type(points) is not int or points < 1:
        raise ValueError("SIMPSON FID requires a positive NP")
    if not isinstance(width, (int, float)) or not np.isfinite(width) or width <= 0:
        raise ValueError("SIMPSON FID requires a finite positive SW in Hz")
    if not np.isfinite(points / width):
        raise ValueError("SIMPSON FID time range is outside float range")
    if "FORMAT" in header and header["FORMAT"] != "BINARY":
        raise ValueError("SIMPSON FID requires TEXT or FORMAT=BINARY")
    return points, width


def _preflight(stream):
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
            raise ValueError("SIMPSON FID has an invalid or duplicate header record")
        header[key] = value
    else:
        raise ValueError("SIMPSON FID requires a DATA block")
    for key in ("NP", "NELEM"):
        if key in header:
            header[key] = int(header[key])
    if "SW" in header:
        header["SW"] = float(header["SW"])
    points, _ = _fid_geometry(header)
    binary = "FORMAT" in header
    if binary:
        payload = "".join(line.rstrip("\n") for line in stream)
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
                raise ValueError("SIMPSON TEXT FID requires two ordinates per row")
            count += 1
        else:
            raise ValueError("SIMPSON TEXT FID requires END")
        if count != points or stream.read().strip():
            raise ValueError("SIMPSON TEXT block disagrees with NP")
    return "BINARY" if binary else "TEXT"


def _fid_axis(header, data):
    points, width = _fid_geometry(header)
    if data.shape != (points,) or data.dtype.kind != "c" or not np.isfinite(data).all():
        raise ValueError("SIMPSON requires finite complex samples matching NP")
    return Axis(values=np.arange(points, dtype=float) / width, unit="s",
                label="time", domain="time", direction="increasing")


def read_simpson_fid(filename):
    """Read a single-element 1D SIMPSON TEXT or BINARY FID."""
    # Validate and decode the same snapshot, even if the path is replaced.
    with StringIO(Path(filename).read_text(encoding="ascii")) as stream:
        file_type = _preflight(stream)
        stream.seek(0)
        decoder = simpson._read_binary if file_type == "BINARY" else simpson._read_text
        header, data = decoder(stream)
    axis = _fid_axis(header, data)
    return ReadResult(
        data=data, axes=(axis,), metadata=header, components=(Component("complex", data),),
        applied_corrections={}, diagnostics=(), format="simpson-fid-1d",
        source=os.fspath(filename), domains=("time",), encoding=("complex",),
        dimensions={"points": data.size},
    )


def normalize_simpson_fid(result, *, conjugation):
    """Validate a SIMPSON FID and apply the caller's sign convention."""
    if not isinstance(result, ReadResult) or result.format != "simpson-fid-1d":
        raise ValueError("normalize_simpson_fid requires a simpson-fid-1d ReadResult")
    if conjugation not in ("none", "conjugate"):
        raise ValueError("SIMPSON requires conjugation='none' or 'conjugate'")
    axis = _fid_axis(result.metadata, result.data)
    if (
        result.domains != ("time",) or result.encoding != ("complex",)
        or result.dimensions != {"points": result.data.size} or result.applied_corrections
        or len(result.axes) != 1 or len(result.components) != 1
        or result.components[0].name != "complex"
        or not np.array_equal(result.components[0].data, result.data)
    ):
        raise ValueError("SIMPSON description disagrees with its FID")
    observed = result.axes[0]
    if (
        observed.unit != axis.unit or observed.domain != axis.domain
        or observed.direction != axis.direction or not np.array_equal(observed.values, axis.values)
    ):
        raise ValueError("SIMPSON axis disagrees with SW")
    width = result.metadata["SW"]
    operation = {
        "name": "normalize-simpson-fid", "stage": "acquisition",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": None, "conjugation": conjugation, "sign": "none",
        "permutation": None, "evidence": "SIMPSON NP/SW and caller-selected conjugation",
    }
    return NormalizedAcquisition(
        data=result.data.conj() if conjugation == "conjugate" else result.data,
        axes=(axis,), dimensions=("F2",), physical_dimensions=("F2",),
        domains=result.domains, quadrature_mode="complex-1d", branch_order=("complex",),
        normalization_state="storage-normalized", normalization_profile="simpson-fid-1d-v1",
        applied_operations=(operation,), provenance={"source": result.source, "format": result.format},
        acquisition={"spectral_width_hz": width, "dwell_time_s": 1 / width},
        metadata=result.metadata, encoding=result.encoding, diagnostics=result.diagnostics,
    )
