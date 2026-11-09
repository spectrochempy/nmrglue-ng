"""JEOL storage readers and explicit normalization for complex 1D FIDs."""

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


def _fid_storage_geometry(header):
    points, acquired = _fid_geometry(header)
    return (2, points), acquired


def _read_jdf(filename, geometry):
    buffer = Path(filename).read_bytes()
    if len(buffer) < _JDF_HEADER_BYTES or not buffer.startswith(b"JEOL.NMR"):
        raise ValueError("JEOL interop requires a complete JDF header")
    try:
        reader = jeol.IOBuffer(buffer, conversion_table=jeol.ConversionTable)
        reader, header = jeol.read_header(reader)
    except (struct.error, KeyError, IndexError, UnicodeError) as exc:
        raise ValueError("JEOL JDF header could not be decoded") from exc

    shape, layout = geometry(header)
    start = header["data_start"]
    parameter_start = header["param_start"]
    parameter_end = parameter_start + header["param_length"]
    if not _JDF_HEADER_BYTES <= parameter_start < parameter_end <= start:
        raise ValueError("JEOL JDF parameter section overlaps header or data")
    if start + header["data_length"] > len(buffer):
        raise ValueError("JEOL JDF data section is truncated")

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
    sections = np.frombuffer(
        buffer, dtype=endian + "f8", count=header["data_length"] // 8, offset=start,
    ).reshape(shape)
    return sections, metadata, layout, buffer


def read_jeol_fid(filename):
    """Read the full stored complex FID, including padding, as R + iI."""
    sections, metadata, acquired, _ = _read_jdf(filename, _fid_storage_geometry)
    real, imag = sections
    points = real.size
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


def _2d_storage_geometry(header):
    metadata = {"header": header}
    axis_types = header["data_axis_type"]
    if (
        header["data_dimension_number"] != 2
        or jeol.dimension_names(metadata) != ["x", "y"]
        or header["data_format"] != "two_d"
        or header["data_type"] != "float64"
        or None in axis_types[:2]
        or any(axis_types[2:])
        or any(size != 1 for size in header["data_points"][2:])
    ):
        raise ValueError("JEOL storage requires a two_d float64 JDF with X and Y axes")

    # Restrict section counting to encodings with an established JDF layout.
    if tuple(axis_types[:2]) not in (
        ("real", "real"),
        ("complex", "real"),
        ("real_complex", "real_complex"),
        ("complex", "complex"),
    ):
        raise ValueError("JEOL 2D storage has unsupported axis types")

    nx, ny = header["data_points"][:2]
    edge = header["submatrix_edge"]
    if min(nx, ny) < edge or nx % edge or ny % edge:
        raise ValueError("JEOL 2D dimensions do not contain complete storage tiles")
    windows = tuple(zip(header["data_offset_start"][:2], header["data_offset_stop"][:2]))
    if any(not 0 <= first <= last < size for (first, last), size in zip(windows, (nx, ny))):
        raise ValueError("JEOL 2D data offsets are outside the stored grid")

    count = jeol.nsections(metadata)
    if header["data_length"] != 8 * count * nx * ny:
        raise ValueError("JEOL 2D data length disagrees with the stored sections")
    return (count, nx * ny), {
        "axis_order": ("section", "word"),
        "grid_axis_order": ("y", "x"),
        "grid_shape": (ny, nx),
        "tile_shape": (edge, edge),
        "valid_index_ranges": {"x": windows[0], "y": windows[1]},
    }


def read_jeol_2d_storage(filename):
    """Read float64 JDF sections as scalar words in on-disk tile order."""
    sections, metadata, dimensions, buffer = _read_jdf(filename, _2d_storage_geometry)
    header = metadata["header"]
    parameter_end = header["param_start"] + header["param_length"]
    axis_lists = {}
    list_spans = []
    for index, axis in enumerate(("x", "y")):
        start = header["list_start"][index]
        length = header["list_length"][index]
        if header["data_axis_ranged"][index] == "listed":
            if length != 8 * header["data_points"][index]:
                raise ValueError(f"JEOL 2D {axis} axis list length disagrees with its grid")
        if not length:
            continue
        end = start + length
        if not parameter_end <= start < end <= header["data_start"]:
            raise ValueError(f"JEOL 2D {axis} axis list overlaps metadata or data")
        if any(start < stop and first < end for first, stop in list_spans):
            raise ValueError("JEOL 2D axis lists overlap")
        list_spans.append((start, end))
        axis_lists[axis] = buffer[start:end]

    metadata["axis_lists_raw"] = axis_lists
    return ReadResult(
        data=sections,
        axes=(Axis(label="stored section"), Axis(label="stored word")),
        metadata=metadata,
        components=tuple(Component(f"section-{i}", row) for i, row in enumerate(sections)),
        applied_corrections={}, diagnostics=(), format="jeol-2d-storage",
        source=os.fspath(filename), domains=("unknown", "unknown"),
        dimensions=dimensions,
    )


def _positive_parameter(parameters, key, *, unit=None):
    record = parameters.get("info", {}).get(key, {})
    if record.get("value_type") not in ("integer", "float"):
        raise ValueError(f"JEOL FID requires a positive numeric {key}")
    try:
        value = float(parameters[key])
    except (KeyError, ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"JEOL FID requires a positive numeric {key}") from exc
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"JEOL FID requires a positive numeric {key}")
    expected_units = [("none", 0, None)] * 5
    if unit is not None:
        expected_units[0] = ("none", 1, unit)
    if record.get("units") != expected_units:
        if unit is not None:
            raise ValueError(f"JEOL FID requires {key} in {unit}")
        raise ValueError(f"JEOL FID requires dimensionless {key}")
    return value


def _carrier_offset(params, axis, *, required):
    offset = params.get(f"{axis}_offset")
    if offset is not None:
        record = params.get("info", {}).get(f"{axis}_offset", {})
        expected_units = [("none", 1, "ppm")] + [("none", 0, None)] * 4
        try:
            offset = float(offset)
        except (TypeError, ValueError, OverflowError):
            offset = float("nan")
        if (
            record.get("value_type") in ("integer", "float")
            and record.get("units") == expected_units
            and np.isfinite(offset)
        ):
            return offset
        if required:
            raise ValueError("JEOL legacy presentation requires a finite offset in ppm")
    return None


def _legacy_metadata(header, params):
    date = header["creation_time"]
    return {
        "data_endianness": header.get("endian"),
        "storage_format": header.get("data_format"),
        "storage_dtype": header.get("data_type"),
        "scan_count": params.get("total_scans", params.get("scans", 1)),
        "solvent": params.get("solvent"),
        "sample": params.get("sample"),
        "pulse_program": params.get("experiment"),
        "acquisition_time": params.get("x_acq_time"),
        "relaxation_delay": params.get("relaxation_delay"),
        "pulse_width": params.get("x90"),
        "acquisition_date": (date["year"], date["month"], date["day"]),
    }


def normalize_jeol_fid(result, *, conjugation, legacy_presentation=False):
    """Trim padding and construct the time axis, with an explicit sign policy.

    The optional legacy presentation describes the conjugated-input display FFT
    and preserves acquisition metadata used by historical JDF consumers.
    """
    if type(legacy_presentation) is not bool:
        raise ValueError("JEOL legacy_presentation must be a bool")
    if legacy_presentation and conjugation != "conjugate":
        raise ValueError("JEOL legacy presentation requires conjugated samples")
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
    width = _positive_parameter(params, "x_sweep", unit="hertz")
    obs = _positive_parameter(params, "x_freq", unit="hertz") / 1e6
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
    acquisition = {
        "spectral_width_hz": width,
        "dwell_time_s": 1 / width,
        "observation_frequency_mhz": obs,
        "storage_points": points,
        "acquired_points": acquired,
        "trimmed_padding_points": points - acquired,
        "nucleus": params.get("x_domain"),
    }
    offset = _carrier_offset(params, "x", required=legacy_presentation)
    if offset is not None:
        acquisition["carrier_offset_ppm"] = offset
    if legacy_presentation:
        acquisition["legacy_presentation"] = {
            **_legacy_metadata(header, params),
            "fft_input_transform": "conjugate-input",
        }
    return NormalizedAcquisition(
        data=work, axes=(axis,), dimensions=("F2",), physical_dimensions=("F2",),
        domains=("time",), quadrature_mode="complex-1d", branch_order=("complex",),
        normalization_state="storage-normalized", normalization_profile="jeol-fid-1d-complex-v1",
        applied_operations=(operation,), metadata=result.metadata,
        encoding=("QSIM",) if legacy_presentation else result.encoding,
        diagnostics=result.diagnostics, provenance={"source": result.source, "format": result.format},
        acquisition=acquisition,
    )


def _jeol_2d_time_axis(result, index, size, axis_name):
    header = result.metadata["header"]
    parameters = result.metadata["parameters"]
    width = _positive_parameter(parameters, f"{axis_name}_sweep", unit="hertz")
    obs = _positive_parameter(parameters, f"{axis_name}_freq", unit="hertz") / 1e6
    if _positive_parameter(parameters, f"{axis_name}_points") != size:
        raise ValueError(f"JEOL 2D {axis_name} point count disagrees with its window")
    if obs <= 0 or not np.isclose(header["base_freq"][index], obs, rtol=1e-7, atol=0):
        raise ValueError(f"JEOL 2D {axis_name} base frequency disagrees with its parameters")

    units = header["units"][index]
    mode = header["data_axis_ranged"][index]
    axis_lists = result.metadata["axis_lists_raw"]
    if mode == "ranged" and units == ("none", 1, "second") and axis_name not in axis_lists:
        times = np.arange(size, dtype=float) / width
        if (header["data_axis_start"][index] != 0
                or not np.isfinite(times[-1])
                or not np.isclose(header["data_axis_stop"][index], times[-1], rtol=1e-7, atol=0)):
            raise ValueError(f"JEOL 2D {axis_name} time endpoints disagree with its sweep")
        nominal_size = size
    elif axis_name == "y" and mode == "listed" and units == ("milli", 1, "second"):
        raw = axis_lists.get(axis_name)
        if not isinstance(raw, bytes) or len(raw) != 8 * header["data_points"][index]:
            raise ValueError("JEOL 2D Y axis requires its complete stored list")
        times = np.frombuffer(raw, dtype=">f8")[:size] * 1e-3
        nominal_size = _positive_parameter(parameters, "y_orig_points")
        increments = times * width
        indices = np.rint(increments)
        if (nominal_size <= size or not nominal_size.is_integer()
                or np.any(increments < 0) or np.any(indices >= nominal_size)
                or not np.allclose(increments, indices, rtol=0, atol=1e-7)
                or np.any(np.diff(indices) <= 0)):
            raise ValueError("JEOL 2D Y times disagree with the nominal NUS grid")
        nominal_size = int(nominal_size)
    else:
        raise ValueError(f"JEOL 2D {axis_name} has an unsupported time axis")

    axis = Axis(
        values=times, unit="s", domain="time", direction="increasing",
        label=parameters.get(f"{axis_name}_domain") or header["data_axis_titles"][index],
        reference=Reference(observation_frequency=obs, observation_frequency_unit="MHz",
                            source="acquisition"),
    )
    return axis, width, nominal_size


def normalize_jeol_2d(result, *, conjugation, legacy_presentation=False):
    """Untile a raw JEOL acquisition and calibrate sampled times.

    The optional public presentation covers regular single-matrix acquisitions
    with conjugated samples. It permits direct FFT and leaves F1 unqualified.
    """
    if type(legacy_presentation) is not bool:
        raise ValueError("JEOL legacy_presentation must be a bool")
    if not isinstance(result, ReadResult) or result.format != "jeol-2d-storage":
        raise ValueError("normalize_jeol_2d requires a jeol-2d-storage ReadResult")
    if conjugation not in ("none", "conjugate"):
        raise ValueError("JEOL requires explicit conjugation: none or conjugate")
    header = result.metadata["header"]
    shape, layout = _2d_storage_geometry(header)
    types = tuple(header["data_axis_type"][:2])
    axis_modes = tuple(header["data_axis_ranged"][:2])
    if (types, axis_modes) not in (
        (("real_complex", "real_complex"), ("ranged", "ranged")),
        (("complex", "complex"), ("ranged", "listed")),
    ):
        raise ValueError("JEOL 2D requires a qualified regular or listed raw layout")
    if legacy_presentation and (
        axis_modes != ("ranged", "ranged")
        or header["reversed"][0]
        or conjugation != "conjugate"
    ):
        raise ValueError("JEOL public 2D presentation requires regular conjugated traces")
    if (
        result.data.shape != shape or result.data.dtype.kind != "f"
        or result.data.dtype.itemsize != 8 or result.dimensions != layout
        or result.applied_corrections or len(result.components) != shape[0]
        or any(
            component.name != f"section-{index}"
            or not np.array_equal(component.data, row, equal_nan=True)
            for index, (component, row) in enumerate(zip(result.components, result.data))
        )
    ):
        raise ValueError("JEOL 2D samples disagree with their storage description")

    (x_start, x_stop), (y_start, y_stop) = (
        layout["valid_index_ranges"][axis] for axis in ("x", "y")
    )
    if x_start or y_start or min(x_stop, y_stop) < 1:
        raise ValueError("JEOL 2D requires uncropped axes with at least two valid points")
    nx, ny = x_stop + 1, y_stop + 1
    x_axis, x_width, _ = _jeol_2d_time_axis(result, 0, nx, "x")
    y_axis, y_width, nominal_y = _jeol_2d_time_axis(result, 1, ny, "y")
    planes = [
        jeol.reorder_submatrix(row, layout["grid_shape"], layout["tile_shape"])[:ny, :nx]
        for row in result.data
    ]
    if not all(np.isfinite(plane).all() for plane in planes):
        raise ValueError("JEOL 2D valid samples must be finite")

    branches = np.empty((len(planes) // 2, ny, nx), dtype=np.complex128)
    for branch, real, imag in zip(branches, planes[::2], planes[1::2]):
        branch.real = real
        branch.imag = -imag if conjugation == "conjugate" else imag
    dimensions = ("F1", "F2")
    if len(branches) == 1:
        data = branches[0]
        channel_axis = None
        branch_order = ("section-0/1",)
    else:
        data = branches
        channel_axis = 0
        branch_order = ("section-0/1", "section-2/3")
    output_dimensions = dimensions if channel_axis is None else ("channels", *dimensions)
    operation = {
        "name": "normalize-jeol-2d", "stage": "acquisition",
        "input_dimensions": ("section", "word"), "output_dimensions": output_dimensions,
        "axis": "F2", "scale": None, "conjugation": conjugation, "sign": "none",
        "permutation": None, "evidence": "JDF tile order and section pairs; caller-selected conjugation",
    }
    acquisition = {
        "dwell_time_s": (1 / y_width, 1 / x_width),
        "spectral_width_hz": (y_width, x_width),
        "sampling": ("listed" if channel_axis is not None else "regular", "regular"),
        "nominal_shape": (nominal_y, nx),
    }
    if legacy_presentation:
        params = result.metadata["parameters"]
        acquisition.update(
            legacy_presentation=_legacy_metadata(header, params),
            nucleus=tuple(params.get(f"{axis}_domain") for axis in ("y", "x")),
            carrier_offset_ppm=tuple(
                _carrier_offset(params, axis, required=True) for axis in ("y", "x")
            ),
        )
    return NormalizedAcquisition(
        data=data, axes=(y_axis, x_axis), dimensions=output_dimensions,
        physical_dimensions=dimensions, domains=("time", "time"),
        quadrature_mode=("f2-traces-stored-2d" if legacy_presentation
                         else "jeol-stored-section-pairs"),
        branch_order=("complex",) if legacy_presentation else branch_order,
        channel_axis=channel_axis, normalization_state="storage-normalized",
        normalization_profile="jeol-2d-time-v1", applied_operations=(operation,),
        provenance={"source": result.source, "format": result.format},
        acquisition=acquisition,
        metadata=result.metadata, diagnostics=result.diagnostics,
        encoding=("unknown", "complex") if legacy_presentation else (types[1], types[0]),
    )
