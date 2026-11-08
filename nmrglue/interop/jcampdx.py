"""Interoperability for JCAMP-DX NMR data."""

from decimal import Decimal
import os
import re

import numpy as np

from ..fileio import jcampdx
from .result import Axis, Component, NormalizedAcquisition, ReadResult, Reference, _same_axis_grid


def _label(block, name):
    values = block.get(name)
    if not isinstance(values, (list, tuple)) or len(values) != 1 or not isinstance(values[0], str):
        raise ValueError(f"JCAMP-DX requires one {name} record")
    return values[0].strip()


def _number(block, name):
    try:
        value = float(_label(block, name))
    except ValueError as exc:
        raise ValueError(f"JCAMP-DX requires a finite {name}") from exc
    if not np.isfinite(value):
        raise ValueError(f"JCAMP-DX requires a finite {name}")
    return value


def _yfactor(block):
    value = _number(block, "YFACTOR")
    if value == 0:
        raise ValueError("JCAMP-DX requires a nonzero YFACTOR")
    return value


def _spectrum_axis(block, data):
    if (
        _label(block, "DATATYPE").upper() != "NMR SPECTRUM"
        or _label(block, "DATACLASS").upper() != "XYDATA"
        or ("NUMDIM" in block and _number(block, "NUMDIM") != 1)
    ):
        raise ValueError("JCAMP-DX requires a real 1D NMR SPECTRUM in XYDATA form")
    if (
        not isinstance(data, np.ndarray) or data.ndim != 1 or data.dtype.kind not in "fiu"
        or data.size < 2 or data.size != _number(block, "NPOINTS")
        or not np.isfinite(data).all()
    ):
        raise ValueError("JCAMP-DX requires finite real intensities matching NPOINTS")

    unit = {"HZ": "Hz", "PPM": "ppm"}.get(_label(block, "XUNITS").upper())
    if unit is None:
        raise ValueError("JCAMP-DX requires XUNITS of Hz or ppm")
    first = _number(block, "FIRSTX")
    last = _number(block, "LASTX")
    if first == last or not np.isfinite(last - first):
        raise ValueError("JCAMP-DX requires distinct finite axis endpoints")
    values = np.linspace(first, last, data.size)
    direction = "increasing" if last > first else "decreasing"
    steps = np.diff(values)
    if not np.all(steps > 0 if direction == "increasing" else steps < 0):
        raise ValueError("JCAMP-DX axis is not strictly monotonic")
    reference = None
    if ".OBSERVEFREQUENCY" in block:
        frequency = _number(block, ".OBSERVEFREQUENCY")
        if frequency <= 0:
            raise ValueError("JCAMP-DX requires positive .OBSERVE FREQUENCY in MHz")
        reference = Reference(observation_frequency=frequency, observation_frequency_unit="MHz")
    return Axis(values=values, unit=unit, label="frequency", domain="frequency",
                direction=direction, reference=reference)


def _check_line_grid(first, step, xfactor, *, endpoint_tolerance=None):
    def check_x(raw, index):
        observed = raw * xfactor
        expected = first + index * step
        # Encoders can quantize line anchors to integer multiples of XFACTOR.
        tolerance = abs(xfactor) * 0.5 if raw.is_integer() else 0.0
        if endpoint_tolerance is not None:
            tolerance += endpoint_tolerance(index)
        if not np.isclose(observed, expected, rtol=1e-12, atol=tolerance):
            raise ValueError("JCAMP-DX XYDATA line abscissa disagrees with its grid")

    return check_x


def read_jcampdx_1d(filename):
    """Read one real 1D NMR spectrum with regularly spaced JCAMP-DX XYDATA."""
    blocks = jcampdx.read_blocks(filename)
    spectra = [
        block for block in blocks
        if any(value.strip().upper() == "NMR SPECTRUM" for value in block.get("DATATYPE", ()))
    ]
    if len(spectra) != 1:
        raise ValueError("JCAMP-DX requires exactly one NMR SPECTRUM block")
    block = spectra[0]
    table = _label(block, "XYDATA")
    if (
        "".join(table.partition("\n")[0].split()).upper() != "(X++(Y..Y))"
        or any(key in block for key in ("DATATABLE", "PEAKTABLE", "XYPOINTS"))
    ):
        raise ValueError("JCAMP-DX requires one regular X++(Y..Y) data table")
    yfactor = _yfactor(block)

    first = _number(block, "FIRSTX")
    last = _number(block, "LASTX")
    points = _number(block, "NPOINTS")
    xfactor = _number(block, "XFACTOR")
    if points < 2 or not points.is_integer() or xfactor == 0:
        raise ValueError("JCAMP-DX requires an integer NPOINTS >= 2 and nonzero XFACTOR")
    step = (last - first) / (points - 1)
    if step == 0 or not np.isfinite(step):
        raise ValueError("JCAMP-DX requires distinct finite axis endpoints")


    data = jcampdx.getdataarray(block, _check_xydata_x=_check_line_grid(first, step, xfactor),
                                 _xydata_max_points=int(points))
    axis = _spectrum_axis(block, data)
    metadata = {key: value for key, value in block.items() if key != "XYDATA"}
    return ReadResult(
        data=data, axes=(axis,), metadata=metadata, components=(Component("real", data),),
        applied_corrections={"yfactor": yfactor},
        diagnostics=(), format="jcampdx-spectrum-1d", source=os.fspath(filename),
        domains=("frequency",), encoding=("real",), dimensions={"points": data.size},
    )


def normalize_jcampdx_1d(result):
    """Validate a described JCAMP-DX spectrum and preserve its decoded values."""
    if not isinstance(result, ReadResult) or result.format != "jcampdx-spectrum-1d":
        raise ValueError("normalize_jcampdx_1d requires a jcampdx-spectrum-1d ReadResult")
    axis = _spectrum_axis(result.metadata, result.data)
    if (
        len(result.axes) != 1 or len(result.components) != 1
        or result.domains != ("frequency",) or result.encoding != ("real",)
        or result.dimensions != {"points": result.data.size}
        or result.applied_corrections != {"yfactor": _yfactor(result.metadata)}
        or result.components[0].name != "real"
        or not np.array_equal(result.components[0].data, result.data)
    ):
        raise ValueError("JCAMP-DX description disagrees with its spectrum")
    observed = result.axes[0]
    if observed.reference != axis.reference or not _same_axis_grid(observed, axis):
        raise ValueError("JCAMP-DX axis disagrees with its spectrum metadata")
    operation = {
        "name": "normalize-jcampdx-1d", "stage": "processing",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": None, "conjugation": "none", "sign": "none",
        "permutation": None, "evidence": "JCAMP-DX FIRSTX, LASTX, NPOINTS and XUNITS",
    }
    return NormalizedAcquisition(
        data=result.data, axes=(axis,), dimensions=("F2",), physical_dimensions=("F2",),
        domains=result.domains, quadrature_mode="real-1d", branch_order=("real",),
        normalization_state="storage-normalized", normalization_profile="jcampdx-spectrum-1d-v1",
        applied_operations=(operation,), provenance={"source": result.source, "format": result.format},
        acquisition={}, metadata=result.metadata, encoding=result.encoding,
        diagnostics=result.diagnostics,
    )


def _fid_geometry(block):
    if (
        _label(block, "DATATYPE").upper() != "NMR FID"
        or _label(block, "DATACLASS").upper() != "NTUPLES"
        or _label(block, "NTUPLES").upper() != "NMR FID"
        or ("NUMDIM" in block and _number(block, "NUMDIM") != 1)
    ):
        raise ValueError("JCAMP-DX requires a 1D NMR FID in NTUPLES form")
    symbols = tuple(item.strip() for item in _label(block, "SYMBOL").split(","))
    if symbols not in (("X", "R", "I"), ("X", "R", "I", "N")):
        raise ValueError("JCAMP-DX FID requires X, R, I and optional N page symbols")

    def columns(key):
        values = [item.strip() for item in _label(block, key).split(",")]
        if len(values) != len(symbols):
            raise ValueError(f"JCAMP-DX FID {key} must match SYMBOL")
        return values

    def numeric_columns(key):
        try:
            values = tuple(float(value) for value in columns(key))
        except ValueError as exc:
            raise ValueError(f"JCAMP-DX FID requires numeric {key} columns") from exc
        if not np.isfinite(values).all():
            raise ValueError(f"JCAMP-DX FID requires finite {key} columns")
        return values

    if "VARTYPE" in block:
        expected_types = ["INDEPENDENT", "DEPENDENT", "DEPENDENT"]
        if len(symbols) == 4:
            expected_types.append("PAGE")
        if [value.upper() for value in columns("VARTYPE")] != expected_types:
            raise ValueError("JCAMP-DX FID VAR_TYPE disagrees with its symbols")
    if "PAGE" in block or len(symbols) == 4:
        pages = ["".join(page.split()).upper() for page in block.get("PAGE", ())]
        if sorted(pages) != ["N=1", "N=2"]:
            raise ValueError("JCAMP-DX FID PAGE records must identify N=1 and N=2")

    units = columns("UNITS")
    if units[0].upper() not in ("SECOND", "SECONDS", "S") or units[1].upper() != units[2].upper() or not units[1]:
        raise ValueError("JCAMP-DX FID requires X in seconds and matching R/I units")
    sizes = numeric_columns("VARDIM")
    points = sizes[0]
    if (points < 2 or not points.is_integer() or sizes[1:3] != (points, points)
            or sizes[3:] not in ((), (2,))):
        raise ValueError("JCAMP-DX FID VAR_DIM must describe two equally sized components")
    if "NPOINTS" in block and _number(block, "NPOINTS") != points:
        raise ValueError("JCAMP-DX FID NPOINTS disagrees with VAR_DIM")

    first = numeric_columns("FIRST")[0]
    last = numeric_columns("LAST")[0]
    factors = numeric_columns("FACTOR")[:3]
    if first < 0 or last <= first or factors[0] <= 0 or 0 in factors[1:]:
        raise ValueError("JCAMP-DX FID requires increasing times and valid X/R/I factors")
    step = (last - first) / (points - 1)
    if step <= 0 or not np.isfinite(1 / step):
        raise ValueError("JCAMP-DX FID requires a finite positive sampling rate")
    return int(points), first, last, factors


def _fid_axis(block, data, geometry):
    points, first, last, _ = geometry
    if (
        not isinstance(data, np.ndarray) or data.shape != (points,)
        or data.dtype.kind != "c" or not np.isfinite(data).all()
    ):
        raise ValueError("JCAMP-DX FID requires finite complex samples matching VAR_DIM")
    times = np.linspace(first, last, points)
    if not np.all(np.diff(times) > 0):
        raise ValueError("JCAMP-DX FID axis is not strictly increasing")
    reference = None
    if ".OBSERVEFREQUENCY" in block:
        frequency = _number(block, ".OBSERVEFREQUENCY")
        if frequency <= 0:
            raise ValueError("JCAMP-DX requires positive .OBSERVE FREQUENCY in MHz")
        reference = Reference(observation_frequency=frequency, observation_frequency_unit="MHz")
    return Axis(values=times, unit="s", label="time", domain="time",
                direction="increasing", reference=reference)


def read_jcampdx_fid(filename):
    """Read a regular complex 1D NTUPLES FID in its stored sign convention."""
    blocks = jcampdx.read_blocks(filename, _record_order=True)
    fids = [
        block for block in blocks
        if any(value.strip().upper() == "NMR FID" for value in block.get("DATATYPE", ()))
    ]
    if len(fids) != 1:
        raise ValueError("JCAMP-DX requires exactly one NMR FID block")
    block = fids[0]
    geometry = _fid_geometry(block)
    points, first, last, (xfactor, rfactor, ifactor) = geometry
    records = [key for key in block["_records"]
               if key in ("NTUPLES", "PAGE", "DATATABLE", "ENDNTUPLES")]
    table_records = ["PAGE", "DATATABLE"] if "PAGE" in block else ["DATATABLE"]
    if records != ["NTUPLES", *table_records, *table_records, "ENDNTUPLES"]:
        raise ValueError("JCAMP-DX FID requires one table per PAGE within the NTUPLES block")
    tables = block.get("DATATABLE", ())
    symbols = []
    for table in tables:
        raw_header = table.partition("\n")[0]
        header = "".join(raw_header.split())
        match = re.fullmatch(r"\(X\+\+\(([RI])\.\.\1\)\),XYDATA", header)
        if match is None or jcampdx._parse_variable_list(raw_header) != ("X", match[1]):
            raise ValueError("JCAMP-DX FID requires regular X++ R/I data tables")
        symbols.append(match[1])
    if sorted(symbols) != ["I", "R"] or any(key in block for key in ("XYDATA", "XYPOINTS", "PEAKTABLE")):
        raise ValueError("JCAMP-DX FID requires one R table and one I table")
    parts = jcampdx.getdataarray(
        {**block, "DATACLASS": ["NTUPLES"]},
        _check_xydata_x=_check_line_grid(first, (last - first) / (points - 1), xfactor),
        _xydata_max_points=points,
    )
    data = jcampdx.get_complex_array(parts) if isinstance(parts, list) else None
    axis = _fid_axis(block, data, geometry)
    metadata = {key: value for key, value in block.items() if key not in ("DATATABLE", "_records")}
    return ReadResult(
        data=data, axes=(axis,), metadata=metadata,
        components=(Component("real", data.real), Component("imaginary", data.imag)),
        applied_corrections={"real_factor": rfactor, "imaginary_factor": ifactor},
        diagnostics=(), format="jcampdx-fid-1d", source=os.fspath(filename),
        domains=("time",), encoding=("complex",), dimensions={"points": points},
    )


def normalize_jcampdx_fid(result, *, conjugation):
    """Validate a JCAMP-DX FID and apply the caller's direct-axis sign choice."""
    if not isinstance(result, ReadResult) or result.format != "jcampdx-fid-1d":
        raise ValueError("normalize_jcampdx_fid requires a jcampdx-fid-1d ReadResult")
    if conjugation not in ("none", "conjugate"):
        raise ValueError("JCAMP-DX FIDs require conjugation='none' or 'conjugate'")
    geometry = _fid_geometry(result.metadata)
    points, first, last, (_, rfactor, ifactor) = geometry
    axis = _fid_axis(result.metadata, result.data, geometry)
    if (
        len(result.axes) != 1 or result.domains != ("time",) or result.encoding != ("complex",)
        or result.dimensions != {"points": points}
        or result.applied_corrections != {"real_factor": rfactor, "imaginary_factor": ifactor}
        or tuple(component.name for component in result.components) != ("real", "imaginary")
        or not np.array_equal(result.components[0].data, result.data.real)
        or not np.array_equal(result.components[1].data, result.data.imag)
    ):
        raise ValueError("JCAMP-DX description disagrees with its FID")
    observed = result.axes[0]
    if observed.reference != axis.reference or not _same_axis_grid(observed, axis):
        raise ValueError("JCAMP-DX axis disagrees with its FID metadata")
    operation = {
        "name": "normalize-jcampdx-fid", "stage": "acquisition",
        "input_dimensions": ("storage",), "output_dimensions": ("F2",),
        "axis": "F2", "scale": None, "conjugation": conjugation, "sign": "none",
        "permutation": None, "evidence": "JCAMP-DX NTUPLES time endpoints and explicit sign choice",
    }
    dwell = (last - first) / (points - 1)
    return NormalizedAcquisition(
        data=result.data.conj() if conjugation == "conjugate" else result.data,
        axes=(axis,), dimensions=("F2",), physical_dimensions=("F2",),
        domains=result.domains, quadrature_mode="complex-1d", branch_order=("complex",),
        normalization_state="storage-normalized", normalization_profile="jcampdx-fid-1d-v1",
        applied_operations=(operation,), provenance={"source": result.source, "format": result.format},
        acquisition={"dwell_time_s": dwell, "spectral_width_hz": 1 / dwell},
        metadata=result.metadata, encoding=result.encoding, diagnostics=result.diagnostics,
    )


def _profile_columns(record, key):
    columns = tuple(value.strip() for value in record.split(","))
    if len(columns) != 3:
        raise ValueError(f"JCAMP-DX 2D {key} requires F1, F2 and Y columns")
    return columns


def _profile_numbers(columns, key):
    try:
        values = tuple(float(value) for value in columns)
    except ValueError as exc:
        raise ValueError(f"JCAMP-DX 2D requires numeric {key} coordinates") from exc
    if not np.isfinite(values).all():
        raise ValueError(f"JCAMP-DX 2D requires finite {key} coordinates")
    return values


def _profile_endpoints(block, key, first_page):
    records = block["_records"]
    positions = [index for index, name in enumerate(records) if name == key]
    values = block.get(key, ())
    if len(positions) != len(values) or sum(index < first_page for index in positions) != 1:
        raise ValueError(f"JCAMP-DX 2D requires one global {key} record")
    columns = _profile_columns(values[0], key)[:2]
    endpoints = _profile_numbers(columns, key)
    precision = Decimal(columns[1]).as_tuple().exponent
    for position, value in zip(positions[1:], values[1:]):
        previous = next((name for name in reversed(records[:position])
                         if name in ("PAGE", "DATATABLE")), None)
        local_columns = _profile_columns(value, key)[:2]
        local = _profile_numbers(local_columns, key)
        if previous != "PAGE" or local[1] != endpoints[1]:
            raise ValueError(f"JCAMP-DX 2D requires a common F2 grid across pages ({key})")
        precision = min(precision, Decimal(local_columns[1]).as_tuple().exponent)
    return endpoints, precision


def _profile_2d_geometry(block):
    if (
        _label(block, "DATATYPE").upper() != "ND NMR SPECTRUM"
        or _label(block, "DATACLASS") != "NTUPLES"
        or _label(block, "NTUPLES").upper() != "ND NMR SPECTRUM"
        or _number(block, "NUMDIM") != 2
        or _profile_columns(_label(block, "SYMBOL"), "SYMBOL") != ("F1", "F2", "Y")
    ):
        raise ValueError("JCAMP-DX requires a real 2D F1/F2/Y NTUPLES spectrum")
    if "VARTYPE" in block and _profile_columns(
        _label(block, "VARTYPE").upper(), "VAR_TYPE",
    ) != ("INDEPENDENT", "INDEPENDENT", "DEPENDENT"):
        raise ValueError("JCAMP-DX 2D VAR_TYPE disagrees with F1/F2/Y symbols")
    sizes = _profile_numbers(_profile_columns(_label(block, "VARDIM"), "VAR_DIM"), "VAR_DIM")
    ny, nx, total = sizes
    if min(nx, ny) < 2 or not nx.is_integer() or not ny.is_integer() or total != ny * nx:
        raise ValueError("JCAMP-DX 2D VAR_DIM must describe a complete real plane")
    factors = _profile_numbers(_profile_columns(_label(block, "FACTOR"), "FACTOR"), "FACTOR")
    if factors[0] != 1 or factors[1] <= 0 or factors[2] == 0:
        raise ValueError("JCAMP-DX 2D requires unity F1 FACTOR and valid F2/Y factors")
    units = tuple({"HZ": "Hz", "PPM": "ppm"}.get(value.upper())
                  for value in _profile_columns(_label(block, "UNITS"), "UNITS")[:2])
    if None in units:
        raise ValueError("JCAMP-DX 2D requires F1 and F2 units of Hz or ppm")
    records = block["_records"]
    pages = block.get("PAGE", ())
    if len(pages) != ny or [key for key in records
                            if key in ("NTUPLES", "PAGE", "DATATABLE", "ENDNTUPLES")] != [
        "NTUPLES", *(("PAGE", "DATATABLE") * int(ny)), "ENDNTUPLES",
    ]:
        raise ValueError("JCAMP-DX 2D requires one PROFILE table per declared PAGE")
    first_page = records.index("PAGE")
    npoints_positions = [index for index, key in enumerate(records) if key == "NPOINTS"]
    npoints_values = _profile_numbers(block.get("NPOINTS", ()), "NPOINTS")
    if len(npoints_positions) != len(npoints_values) or any(
        value != (total if index < first_page else nx)
        for index, value in zip(npoints_positions, npoints_values)
    ):
        raise ValueError("JCAMP-DX 2D NPOINTS disagrees with VAR_DIM")
    first, first_f2 = _profile_endpoints(block, "FIRST", first_page)
    last, last_f2 = _profile_endpoints(block, "LAST", first_page)
    if not np.isfinite(last[1] - first[1]) or last[1] == first[1]:
        raise ValueError("JCAMP-DX 2D requires distinct finite F2 endpoints")

    coordinates = []
    for page in pages:
        match = re.fullmatch(r"F1\s*=\s*(\S+)", page)
        if match is None:
            raise ValueError("JCAMP-DX 2D requires an F1 coordinate on every PAGE")
        coordinates.append(match[1])
    f1 = np.array(_profile_numbers(coordinates, "PAGE"))
    if f1[0] != first[0] or f1[-1] != last[0]:
        raise ValueError("JCAMP-DX 2D PAGE endpoints disagree with FIRST/LAST")
    # Endpoints can themselves be rounded before line anchors are quantized.
    tolerances = tuple(float(f"5e{precision - 1}") for precision in (first_f2, last_f2))
    if not np.isfinite(tolerances).all():
        raise ValueError("JCAMP-DX 2D F2 endpoint precision is outside float range")
    return f1, (first[1], last[1]), units, (int(ny), int(nx)), factors, tolerances


def _profile_axes(f1, f2_endpoints, units, points):
    f2 = np.linspace(*f2_endpoints, points)
    axes = []
    for name, values, unit in zip(("F1", "F2"), (f1, f2), units):
        differences = np.diff(values)
        if np.all(differences > 0):
            direction = "increasing"
        elif np.all(differences < 0):
            direction = "decreasing"
        else:
            raise ValueError(f"JCAMP-DX 2D requires a strictly monotonic {name} axis")
        axes.append(Axis(values=values, unit=unit, label=name, domain="frequency",
                         direction=direction))
    return tuple(axes)


def _check_shared_f2_grid(endpoints, tolerances, intervals, anchor_ranges):
    # Each vertex is a possible pair of offsets from the written endpoints.
    first, last = endpoints
    start_tol, stop_tol = tolerances
    polygon = [(-start_tol, -stop_tol), (start_tol, -stop_tol),
               (start_tol, stop_tol), (-start_tol, stop_tol)]
    for index, (lower, upper) in sorted(anchor_ranges.items()):
        fraction = index / intervals
        expected = first + fraction * (last - first)
        for sign, limit in ((1, upper - expected), (-1, expected - lower)):
            clipped = []
            previous = polygon[-1]
            previous_distance = sign * ((1 - fraction) * previous[0] + fraction * previous[1]) - limit
            for point in polygon:
                distance = sign * ((1 - fraction) * point[0] + fraction * point[1]) - limit
                if (previous_distance <= 0) != (distance <= 0):
                    weight = previous_distance / (previous_distance - distance)
                    clipped.append(tuple(a + weight * (b - a) for a, b in zip(previous, point)))
                if distance <= 0:
                    clipped.append(point)
                previous, previous_distance = point, distance
            if not clipped:
                raise ValueError("JCAMP-DX 2D line abscissae cannot describe a common F2 grid")
            polygon = clipped


def read_jcampdx_2d(filename):
    """Read a real 2D NTUPLES spectrum in F1 page and F2 sample order."""
    blocks = jcampdx.read_blocks(filename, _record_order=True)
    spectra = [block for block in blocks
               if any(value.upper() == "ND NMR SPECTRUM" for value in block.get("DATATYPE", ()))]
    if len(spectra) != 1:
        raise ValueError("JCAMP-DX requires exactly one nD NMR SPECTRUM block")
    block = spectra[0]
    f1, f2_endpoints, units, shape, factors, tolerances = _profile_2d_geometry(block)
    tables = block.get("DATATABLE", ())
    if len(tables) != shape[0] or any(
        "".join(table.partition("\n")[0].split()) != "(F2++(Y..Y)),PROFILE"
        or jcampdx._parse_variable_list(table.partition("\n")[0]) != ("F2", "Y")
        for table in tables
    ):
        raise ValueError("JCAMP-DX 2D requires a regular F2++ Y PROFILE table per page")
    first, last = f2_endpoints
    intervals = shape[1] - 1

    def endpoint_tolerance(index):
        if not 0 <= index <= intervals:
            raise ValueError("JCAMP-DX 2D line index exceeds VAR_DIM")
        fraction = index / intervals
        return (1 - fraction) * tolerances[0] + fraction * tolerances[1]

    xfactor = factors[1]
    check_grid = _check_line_grid(first, (last - first) / intervals, xfactor,
                                  endpoint_tolerance=endpoint_tolerance)
    anchor_ranges = {}

    def check(raw, index):
        check_grid(raw, index)
        # Intersect the possible coordinates at each repeated sample index.
        center = raw * xfactor
        radius = (abs(xfactor) * 0.5 if raw.is_integer() else 0.0) + abs(center) * 1e-12
        lower, upper = anchor_ranges.get(index, (-np.inf, np.inf))
        lower, upper = max(lower, center - radius), min(upper, center + radius)
        if lower > upper:
            raise ValueError("JCAMP-DX 2D line abscissae disagree across pages")
        anchor_ranges[index] = lower, upper

    parts = jcampdx.getdataarray(block, show_all_data=True, _check_xydata_x=check,
                                 _xydata_max_points=shape[1])
    if (
        not isinstance(parts, dict) or len(parts["real"]) != shape[0]
        or any(row.shape != (shape[1],) or not np.isfinite(row).all() for row in parts["real"])
    ):
        raise ValueError("JCAMP-DX 2D PROFILE intensities disagree with VAR_DIM")
    _check_shared_f2_grid(f2_endpoints, tolerances, intervals, anchor_ranges)
    data = np.stack(parts["real"])
    axes = _profile_axes(f1, f2_endpoints, units, shape[1])
    return ReadResult(
        data=data, axes=axes, metadata={key: value for key, value in block.items() if key != "DATATABLE"},
        components=(Component("real", data),), applied_corrections={"yfactor": factors[2]},
        diagnostics=(), format="jcampdx-spectrum-2d", source=os.fspath(filename),
        domains=("frequency", "frequency"), encoding=("real", "real"),
        dimensions={"shape": shape, "axis_order": ("F1", "F2")},
    )


def normalize_jcampdx_2d(result):
    """Validate the JCAMP-DX real plane and preserve its axes and intensities."""
    if not isinstance(result, ReadResult) or result.format != "jcampdx-spectrum-2d":
        raise ValueError("normalize_jcampdx_2d requires a jcampdx-spectrum-2d ReadResult")
    f1, f2_endpoints, units, shape, factors, _ = _profile_2d_geometry(result.metadata)
    if result.data.shape != shape:
        raise ValueError("JCAMP-DX 2D description disagrees with VAR_DIM")
    axes = _profile_axes(f1, f2_endpoints, units, shape[1])
    dimensions = ("F1", "F2")
    domains = ("frequency", "frequency")
    encoding = ("real", "real")
    if (
        result.data.dtype.kind not in "fiu"
        or not np.isfinite(result.data).all() or len(result.axes) != 2
        or result.domains != domains or result.encoding != encoding
        or result.dimensions != {"shape": shape, "axis_order": dimensions}
        or result.applied_corrections != {"yfactor": factors[2]}
        or len(result.components) != 1 or result.components[0].name != "real"
        or not np.array_equal(result.components[0].data, result.data)
        or any(
            not _same_axis_grid(observed, expected)
            for observed, expected in zip(result.axes, axes)
        )
    ):
        raise ValueError("JCAMP-DX 2D description disagrees with its spectrum")
    operation = {
        "name": "normalize-jcampdx-2d", "stage": "processing",
        "input_dimensions": dimensions, "output_dimensions": dimensions,
        "axis": None, "scale": None, "conjugation": "none", "sign": "none",
        "permutation": None, "evidence": "JCAMP-DX PAGE coordinates and F2 endpoints",
    }
    return NormalizedAcquisition(
        data=result.data, axes=axes, dimensions=dimensions, physical_dimensions=dimensions,
        domains=domains, quadrature_mode="real-2d", branch_order=("real",),
        normalization_state="storage-normalized", normalization_profile="jcampdx-spectrum-2d-v1",
        applied_operations=(operation,), provenance={"source": result.source, "format": result.format},
        acquisition={}, metadata=result.metadata, encoding=encoding, diagnostics=result.diagnostics,
    )
