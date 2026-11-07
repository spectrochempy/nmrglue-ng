"""Explicit storage and normalization profile for JEOL 1D complex FIDs."""

import os
from pathlib import Path
import struct

import numpy as np


from ..fileio import jeol
from .result import Axis, Component, NormalizedAcquisition, ReadResult, Reference


_JDF_HEADER_BYTES = 1360


def _fid_geometry(header):
    if (
        header.get("file_identifier") != "JEOL.NMR"
        or header.get("data_dimension_number") != 1
        or jeol.dimension_names({"header": header}) != ["x"]
        or header.get("data_axis_type") != ["complex"] + [None] * 7
        or header.get("data_format") != "one_d"
        or header.get("data_type") != "float64"
        or header["units"][0] != ("none", 1, "second")
        or header["reversed"][0]
    ):
        raise ValueError("JEOL interop requires a 1D complex float64 FID in seconds")
    if header["data_axis_ranged"][0] != "ranged" or header["list_length"][0]:
        raise ValueError("JEOL interop requires a ranged time axis")
    points, *unused = header["data_points"]
    start = header["data_offset_start"][0]
    stop = header["data_offset_stop"][0]
    if any(size != 1 for size in unused) or start != 0 or not 1 <= stop < points:
        raise ValueError("JEOL FID has unsupported point counts or offsets")
    if header["data_length"] != 16 * points:
        raise ValueError("JEOL FID data length disagrees with its two float64 sections")
    return points, stop + 1


def read_jeol_fid(filename):
    """Read the full stored complex FID, including padding, as R + iI."""
    buffer = Path(filename).read_bytes()
    if len(buffer) < _JDF_HEADER_BYTES or not buffer.startswith(b"JEOL.NMR"):
        raise ValueError("JEOL interop requires a complete JDF header")
    try:
        reader = jeol.IOBuffer(buffer, conversion_table=jeol.ConversionTable)
        reader, header = jeol.read_header(reader)
    except (struct.error, KeyError, IndexError, UnicodeError) as exc:
        raise ValueError("JEOL JDF header could not be decoded") from exc

    points, acquired = _fid_geometry(header)
    start = header["data_start"]
    parameter_start = header["param_start"]
    parameter_end = parameter_start + header["param_length"]
    if not _JDF_HEADER_BYTES <= parameter_start < parameter_end <= start:
        raise ValueError("JEOL JDF parameter section overlaps header or data")
    if start + header["data_length"] > len(buffer):
        raise ValueError("JEOL FID data section is truncated")

    try:
        # Bound the legacy parser to the declared end of the parameter section.
        reader.buffer = memoryview(buffer)[:parameter_end]
        _, parameters = jeol.read_parameters(
            reader, parameter_start, header["endian"], inclusive=True,
        )
    except (struct.error, KeyError, IndexError, ValueError, OverflowError, TypeError) as exc:
        raise ValueError("JEOL JDF parameter section could not be decoded") from exc

    metadata = {"header": header, "parameters": parameters}
    endian = {"little_endian": "<", "big_endian": ">"}[header["endian"]]
    real, imag = np.frombuffer(buffer, dtype=endian + "f8", count=2 * points,
                              offset=start).reshape(2, points)
    data = np.empty(points, dtype=np.complex128)
    data.real = real
    data.imag = imag
    return ReadResult(
        data=data, axes=(Axis(label="stored sample", domain="time"),),
        metadata=metadata, components=(Component("stored-complex", data),),
        applied_corrections={}, diagnostics=(), format="jeol-fid-1d",
        source=os.fspath(filename), domains=("time",), encoding=("complex",),
        dimensions={"storage_points": points, "acquired_points": acquired},
    )


def _positive_parameter(parameters, key, *, hertz=False):
    record = parameters.get("info", {}).get(key, {})
    if record.get("value_type") not in ("integer", "float"):
        raise ValueError(f"JEOL FID requires a positive numeric {key}")
    try:
        value = float(parameters[key])
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"JEOL FID requires a positive numeric {key}") from exc
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"JEOL FID requires a positive numeric {key}")
    if hertz:
        if record.get("units") != [("none", 1, "hertz")] + [("none", 0, None)] * 4:
            raise ValueError(f"JEOL FID requires {key} in hertz")
    return value


def normalize_jeol_fid(result, *, conjugation):
    """Trim padding and construct the time axis, with an explicit sign policy."""
    if not isinstance(result, ReadResult) or result.format != "jeol-fid-1d":
        raise ValueError("normalize_jeol_fid requires a jeol-fid-1d ReadResult")
    if conjugation not in ("none", "conjugate"):
        raise ValueError("JEOL requires explicit conjugation: none or conjugate")
    header = result.metadata["header"]
    params = result.metadata["parameters"]
    points, acquired = _fid_geometry(header)
    data = result.data
    if (
        data.shape != (points,) or data.dtype != np.dtype("complex128")
        or not np.isfinite(data[:acquired]).all()
        or result.domains != ("time",) or result.encoding != ("complex",)
        or result.dimensions != {"storage_points": points, "acquired_points": acquired}
        or result.applied_corrections or len(result.components) != 1
        or result.components[0].name != "stored-complex"
        or not np.array_equal(result.components[0].data, data, equal_nan=True)
    ):
        raise ValueError("JEOL FID samples disagree with their storage description")
    width = _positive_parameter(params, "x_sweep", hertz=True)
    obs = _positive_parameter(params, "x_freq", hertz=True) / 1e6
    if not np.isclose(header["base_freq"][0], obs, rtol=1e-7, atol=0):
        raise ValueError("JEOL FID base frequency disagrees with x_freq")
    if _positive_parameter(params, "x_points") != acquired:
        raise ValueError("JEOL FID point count disagrees with x_points")
    last_time = (acquired - 1) / width
    if (header["data_axis_start"][0] != 0 or not np.isfinite(last_time)
            or not np.isclose(header["data_axis_stop"][0], last_time, rtol=1e-7, atol=0)):
        raise ValueError("JEOL FID time endpoints disagree with x_sweep")
    times = np.arange(acquired, dtype=float) / width
    label = params.get("x_domain") or header["data_axis_titles"][0]
    axis = Axis(values=times, unit="s", label=label, domain="time", direction="increasing",
                reference=Reference(observation_frequency=obs,
                                    observation_frequency_unit="MHz", source="acquisition"))
    work = data[:acquired]
    if conjugation == "conjugate":
        work = work.conj()
    operation = {
        "name": "normalize-jeol-fid", "stage": "acquisition",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": None, "conjugation": conjugation, "sign": "none",
        "permutation": None, "evidence": "JDF offsets and x_sweep; caller-selected conjugation",
    }
    return NormalizedAcquisition(
        data=work, axes=(axis,), dimensions=("F2",), physical_dimensions=("F2",),
        domains=("time",), quadrature_mode="complex-1d", branch_order=("complex",),
        normalization_state="storage-normalized", normalization_profile="jeol-fid-1d-complex-v1",
        applied_operations=(operation,), metadata=result.metadata, encoding=result.encoding,
        diagnostics=result.diagnostics, provenance={"source": result.source, "format": result.format},
        acquisition={"spectral_width_hz": width, "dwell_time_s": 1 / width,
                     "observation_frequency_mhz": obs, "storage_points": points,
                     "acquired_points": acquired, "trimmed_padding_points": points - acquired},
    )
