"""Stored traces and qualified spectra for the interoperability layer."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from ..fileio import pipe
from .result import Axis, Component, NormalizedAcquisition, ReadResult, Reference


def _number(header, key):
    value = header.get(key)
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ) or not np.isfinite(value):
        raise ValueError("NMRPipe requires finite numeric " + key)
    return float(value)


def _geometry(header, max_points):
    def number(key):
        return _number(header, key)

    if number("FDMAGIC") != 0 or number("FDFLTORDER") not in (0, float(np.float32(2.345))):
        raise ValueError("NMRPipe requires a valid magic and byte-order marker")
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
    axis, sw = _frequency_axis(header, "FDF2", size)
    return size, quad == 0, axis, sw


def _frequency_axis(header, prefix, size):
    sw, obs, orig = (_number(header, prefix + key) for key in ("SW", "OBS", "ORIG"))
    if sw <= 0 or obs <= 0:
        raise ValueError("NMRPipe SW and OBS must be positive")
    values = orig + (size - 1 - np.arange(size, dtype=float)) * (sw / size)
    if not np.isfinite(values).all() or not np.all(np.diff(values) < 0):
        raise ValueError("NMRPipe frequency grid must be finite and strictly decreasing")
    axis = Axis(
        values=values, unit="Hz", label=header.get(prefix + "LABEL"),
        domain="frequency", direction="decreasing",
        reference=Reference(observation_frequency=obs,
                            observation_frequency_unit="MHz", source="processing"),
    )
    return axis, sw


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

def _storage_2d_layout(header):
    if _number(header, "FDMAGIC") != 0 or _number(header, "FDDIMCOUNT") != 2:
        raise ValueError("NMRPipe storage reader requires a 2D file")
    transposed = _number(header, "FDTRANSPOSED")
    if transposed not in (0, 1):
        raise ValueError("NMRPipe requires FDTRANSPOSED=0 or 1")
    order = ("F2", "F1") if transposed else ("F1", "F2")
    if tuple(header[key] for key in ("FDDIMORDER2", "FDDIMORDER1")) != tuple(
        int(dim[-1]) for dim in order
    ):
        raise ValueError("NMRPipe dimension order disagrees with FDTRANSPOSED")

    prefixes = tuple("FD" + dim for dim in order)
    quadrature = tuple(_number(header, prefix + "QUADFLAG") for prefix in prefixes)
    if any(flag not in (0, 1) for flag in quadrature):
        raise ValueError("NMRPipe storage reader requires real or complex quadrature flags")
    if _number(header, "FDQUADFLAG") != min(quadrature):
        raise ValueError("NMRPipe requires consistent real/complex quadrature flags")
    transformed = tuple(_number(header, prefix + "FTFLAG") for prefix in prefixes)
    if any(flag not in (0, 1) for flag in transformed):
        raise ValueError("NMRPipe requires FTFLAG=0 or 1 on each axis")
    sizes = tuple(_number(header, key) for key in ("FDSPECNUM", "FDSIZE"))
    if any(size < 1 or not size.is_integer() for size in sizes):
        raise ValueError("NMRPipe requires positive integer FDSPECNUM and FDSIZE")
    rows, words = pipe.find_shape(header)
    domains = tuple("frequency" if flag else "time" for flag in transformed)
    encoding = tuple("real" if flag else "complex" for flag in quadrature)
    dimensions = {
        "axis_order": order,
        "shape": (rows, int(sizes[1])),
        "stored_shape": (rows, words),
        "row_layout": "interleaved-real-imaginary" if quadrature[0] == 0 else "real",
        "trace_layout": "appended-real-imaginary" if quadrature[1] == 0 else "real",
    }
    return order, domains, encoding, dimensions


def read_nmrpipe_2d_storage(filename):
    """Read one NMRPipe 2D file in stored trace order.

    Accept standard real and complex quadrature in time, frequency or mixed
    domains. The historical reader combines the real and imaginary halves
    of each complex trace. If the row axis is complex, its branches remain
    interleaved in file order. An extraction can start on either branch
    and contain an incomplete pair. The result carries the header and file
    layout without physical coordinate values or quadrature reconstruction.
    """
    with Path(filename).open("rb", buffering=0) as stream:
        raw_header = stream.read(2048)
        if len(raw_header) != 2048:
            raise ValueError("NMRPipe requires a complete 2048-byte header")
        marker = np.float32(2.345)
        for dtype in ("<f4", ">f4"):
            fdata = np.frombuffer(raw_header, dtype=dtype)
            if fdata[2] == marker:
                break
        else:
            raise ValueError("NMRPipe requires a valid byte-order marker")
        header = pipe.fdata2dic(fdata.astype(np.float32, copy=False))
        order, domains, encoding, dimensions = _storage_2d_layout(header)
        rows, words = dimensions["stored_shape"]
        if os.fstat(stream.fileno()).st_size != 2048 + 4 * rows * words:
            raise ValueError("NMRPipe payload size disagrees with the trace layout")

        stream.seek(0)
        _, data = pipe.read_2D(stream)
        if data.shape != dimensions["shape"]:
            raise ValueError("NMRPipe payload does not decode to the declared trace layout")

    return ReadResult(
        data=data,
        axes=tuple(
            Axis(label=header["FD" + dim + "LABEL"] or dim, domain=domain)
            for dim, domain in zip(order, domains, strict=True)
        ),
        metadata=header,
        components=(Component("stored-traces", data),),
        applied_corrections={},
        diagnostics=(),
        format="nmrpipe-2d-storage",
        source=filename,
        domains=domains,
        encoding=encoding,
        dimensions=dimensions,
    )


_REAL_2D_DOMAINS = ("frequency", "frequency")
_REAL_2D_ENCODING = ("real", "real")
_REAL_2D_CORRECTIONS = {"normalization": "none", "conjugation": "none"}


def _real_2d_geometry(header, points):
    required = {
        "FDMAGIC": 0,
        "FDFLTORDER": float(np.float32(2.345)),
        "FDDIMCOUNT": 2,
        "FDQUADFLAG": 1,
        "FDF1QUADFLAG": 1,
        "FDF2QUADFLAG": 1,
        "FDF1FTFLAG": 1,
        "FDF2FTFLAG": 1,
    }
    for key, expected in required.items():
        if _number(header, key) != expected:
            raise ValueError(
                f"NMRPipe real frequency 2D profile requires {key}={expected}"
            )
    if _number(header, "FDPIPEFLAG") not in (0, 1):
        raise ValueError("NMRPipe requires FDPIPEFLAG=0 or 1")
    transposed = _number(header, "FDTRANSPOSED")
    if transposed not in (0, 1):
        raise ValueError("NMRPipe requires FDTRANSPOSED=0 or 1")
    order = ("F2", "F1") if transposed else ("F1", "F2")
    if tuple(_number(header, key) for key in ("FDDIMORDER2", "FDDIMORDER1")) != tuple(
        int(dim[-1]) for dim in order
    ):
        raise ValueError("NMRPipe dimension order disagrees with FDTRANSPOSED")
    sizes = tuple(_number(header, key) for key in ("FDSPECNUM", "FDSIZE"))
    if any(size < 2 or not size.is_integer() for size in sizes):
        raise ValueError("NMRPipe requires integer FDSPECNUM and FDSIZE >= 2")
    rows, cols = shape = tuple(int(size) for size in sizes)
    if rows * cols != points:
        raise ValueError("NMRPipe payload size disagrees with FDSPECNUM/FDSIZE")
    axes = []
    widths = []
    for dim, size in zip(order, shape, strict=True):
        prefix = "FD" + dim
        if (
            _number(header, prefix + "X1") != 0
            or _number(header, prefix + "XN") != 0
            or _number(header, prefix + "FTSIZE") != size
        ):
            raise ValueError("NMRPipe requires a complete unextracted frequency grid")
        axis, width = _frequency_axis(header, prefix, size)
        axes.append(axis)
        widths.append(width)
    return shape, order, tuple(axes), tuple(widths)


def _real_2d_acquisition(axes, widths):
    return {
        "spectral_width_hz": widths,
        "observation_frequency_mhz": tuple(
            axis.reference.observation_frequency for axis in axes
        ),
        "reference_source": "processing",
        "normalization": "none",
    }


def read_nmrpipe_2d(filename):
    """Read one complete real NMRPipe frequency/frequency plane.

    Samples and axes are in file order. Both orientations are supported.
    Each axis uses its own SW, OBS and last-point ORIG. Only a single
    unextracted two-dimensional file is accepted.
    """
    with Path(filename).open("rb", buffering=0) as stream:
        raw_header = stream.read(2048)
        if len(raw_header) != 2048:
            raise ValueError("NMRPipe requires a complete 2048-byte header")
        marker = np.float32(2.345)
        for dtype in ("<f4", ">f4"):
            fdata = np.frombuffer(raw_header, dtype=dtype)
            if fdata[2] == marker:
                break
        else:
            raise ValueError("NMRPipe requires a valid byte-order marker")
        header = pipe.fdata2dic(fdata.astype(np.float32, copy=False))
        points, remainder = divmod(os.fstat(stream.fileno()).st_size - 2048, 4)
        if remainder:
            raise ValueError("NMRPipe payload size must be a multiple of four bytes")
        shape, order, axes, widths = _real_2d_geometry(header, points)
        samples = np.fromfile(stream, dtype=dtype, count=points)
        if samples.size != points or stream.read(1) or not np.isfinite(samples).all():
            raise ValueError("NMRPipe requires an exact, finite real payload")
    data = samples.astype(np.float32, copy=False).reshape(shape)
    return ReadResult(
        data=data,
        axes=axes,
        metadata=header,
        components=(Component(name="real", data=data),),
        applied_corrections=_REAL_2D_CORRECTIONS,
        diagnostics=(),
        format="nmrpipe-2d",
        source=os.fspath(filename),
        domains=_REAL_2D_DOMAINS,
        encoding=_REAL_2D_ENCODING,
        dimensions={"axis_order": order, "storage_shape": shape},
        acquisition=_real_2d_acquisition(axes, widths),
    )


def _normalize_nmrpipe_2d_storage(result, confirm_time_grid):
    header = result.metadata
    order, domains, encoding, layout = _storage_2d_layout(header)
    data = result.data
    row_complex, trace_complex = (kind == "complex" for kind in encoding)
    expected_dtype = np.dtype(np.complex64 if trace_complex else np.float32)
    if (
        data.shape != layout["shape"]
        or data.dtype != expected_dtype
        or not np.isfinite(data).all()
        or result.domains != domains
        or result.encoding != encoding
        or dict(result.dimensions) != layout
        or result.applied_corrections
        or len(result.components) != 1
        or result.components[0].name != "stored-traces"
        or result.components[0].data.dtype != expected_dtype
        or not np.array_equal(result.components[0].data, data)
    ):
        raise ValueError("NMRPipe storage result disagrees with its header or samples")
    if row_complex and data.shape[0] % 2:
        raise ValueError("NMRPipe normalization requires complete row pairs")
    if _number(header, "FDNUSDIM") != 0:
        raise ValueError("NMRPipe normalization requires a uniformly sampled grid")
    plane_type = _number(header, "FD2DPHASE")
    if plane_type not in (0, 1, 2):
        raise ValueError("NMRPipe normalization requires a spectral plane")
    if "time" in domains:
        if confirm_time_grid is not True:
            raise ValueError("NMRPipe time-domain normalization requires confirm_time_grid=True")
        if plane_type not in (1, 2):
            raise ValueError("NMRPipe time-domain normalization requires States or TPPI layout")

    axes = []
    widths = []
    sizes = (data.shape[0] // 2 if row_complex else data.shape[0], data.shape[1])
    for dim, domain, kind, size in zip(order, domains, encoding, sizes, strict=True):
        prefix = "FD" + dim
        if _number(header, prefix + "X1") or _number(header, prefix + "XN"):
            raise ValueError("NMRPipe normalization requires an unextracted grid")
        tppi_indirect = plane_type == 1 and dim == "F1"
        size_field = "FTSIZE" if domain == "frequency" else "TDSIZE"
        if _number(header, prefix + size_field) != size:
            raise ValueError("NMRPipe normalization requires a complete grid matching " + size_field)
        if domain == "frequency":
            axis, width = _frequency_axis(header, prefix, size)
        else:
            expected_kind = "real" if tppi_indirect else "complex"
            if kind != expected_kind:
                raise ValueError(
                    f"NMRPipe time-domain {dim} requires {expected_kind} samples for this layout"
                )
            width = _number(header, prefix + "SW")
            obs = _number(header, prefix + "OBS")
            if width <= 0 or obs <= 0:
                raise ValueError("NMRPipe SW and OBS must be positive")
            axis = Axis(
                values=np.arange(size, dtype=float) / (2 * width if tppi_indirect else width),
                unit="s",
                label=header[prefix + "LABEL"], domain="time", direction="increasing",
                reference=Reference(observation_frequency=obs,
                                    observation_frequency_unit="MHz", source="acquisition"),
            )
        axes.append(axis)
        widths.append(width)

    dimensions = order
    branch_order = ("real",)
    channel_axis = None
    if row_complex or trace_complex:
        rows = (("r", data[::2]), ("i", data[1::2])) if row_complex else (("r", data),)
        names = []
        planes = []
        for branch, traces in rows:
            names.append(branch + "r")
            planes.append(traces.real)
            if trace_complex:
                names.append(branch + "i")
                planes.append(traces.imag)
        data = np.stack(planes)
        dimensions = ("channels", *order)
        branch_order = tuple(names)
        channel_axis = 0

    operation = {
        "name": "normalize-nmrpipe-stored-components",
        "stage": "processing" if domains == _REAL_2D_DOMAINS else "acquisition",
        "input_dimensions": order,
        "output_dimensions": dimensions,
        "axis": None,
        "scale": None,
        "conjugation": "none",
        "sign": "none",
        "permutation": None,
        "evidence": "nmrglue.interop.read_nmrpipe_2d_storage",
    }
    return NormalizedAcquisition(
        data=data, axes=tuple(axes), dimensions=dimensions, physical_dimensions=order,
        domains=domains, quadrature_mode="stored-components-2d" if channel_axis == 0 else "real-2d",
        branch_order=branch_order, channel_axis=channel_axis,
        normalization_state="storage-normalized",
        normalization_profile="nmrpipe-stored-components-2d-v1",
        applied_operations=(operation,),
        provenance={"source": result.source, "format": result.format},
        acquisition={"spectral_width_hz": tuple(widths)},
        metadata=header, encoding=encoding, diagnostics=result.diagnostics,
    )


def normalize_nmrpipe_2d(result, *, confirm_time_grid=False):
    """Normalize a qualified real plane or complete NMRPipe 2D storage grid.

    Preserve file axis order and split stored quadrature into real channels.
    Time axes support complex States storage and pure TPPI with a real
    indirect time axis sampled at twice its spectral width.
    Set ``confirm_time_grid=True`` only for a known complete, uniformly
    sampled acquisition grid starting at the original time and branch.
    NMRPipe time-domain extraction can leave the relevant header fields
    unchanged.
    """
    if isinstance(result, ReadResult) and result.format == "nmrpipe-2d-storage":
        return _normalize_nmrpipe_2d_storage(result, confirm_time_grid)
    if not isinstance(result, ReadResult) or result.format != "nmrpipe-2d":
        raise ValueError("normalize_nmrpipe_2d requires a nmrpipe-2d ReadResult")
    data = np.asarray(result.data)
    shape, order, axes, widths = _real_2d_geometry(result.metadata, data.size)
    acquisition = _real_2d_acquisition(axes, widths)
    if (
        data.shape != shape
        or data.dtype != np.dtype(np.float32)
        or not np.isfinite(data).all()
        or result.domains != _REAL_2D_DOMAINS
        or result.encoding != _REAL_2D_ENCODING
        or dict(result.dimensions) != {"axis_order": order, "storage_shape": shape}
        or dict(result.acquisition) != acquisition
    ):
        raise ValueError("NMRPipe normalized plane disagrees with its header")
    if len(result.axes) != 2 or any(
        (
            supplied.domain,
            supplied.unit,
            supplied.direction,
            supplied.label,
            supplied.reference,
        )
        != (axis.domain, axis.unit, axis.direction, axis.label, axis.reference)
        or not np.array_equal(supplied.values, axis.values)
        for supplied, axis in zip(result.axes, axes, strict=True)
    ):
        raise ValueError("NMRPipe axes disagree with the header")
    if (
        len(result.components) != 1
        or result.components[0].name != "real"
        or result.components[0].data.dtype != data.dtype
        or not np.array_equal(result.components[0].data, data)
    ):
        raise ValueError("NMRPipe component disagrees with its samples")
    if dict(result.applied_corrections) != _REAL_2D_CORRECTIONS:
        raise ValueError("NMRPipe has unrecognized corrections")
    operation = {
        "name": "normalize-nmrpipe-plane",
        "stage": "processing",
        "input_dimensions": order,
        "output_dimensions": order,
        "axis": None,
        "scale": None,
        "conjugation": "none",
        "sign": "none",
        "permutation": None,
        "evidence": "nmrglue.interop.read_nmrpipe_2d",
    }
    return NormalizedAcquisition(
        data=data,
        axes=axes,
        dimensions=order,
        physical_dimensions=order,
        domains=_REAL_2D_DOMAINS,
        quadrature_mode="real-2d",
        branch_order=("real",),
        normalization_state="storage-normalized",
        normalization_profile="nmrpipe-spectrum-2d-real-v1",
        applied_operations=(operation,),
        provenance={"source": result.source, "format": result.format},
        acquisition=acquisition,
        metadata=result.metadata,
        encoding=result.encoding,
        diagnostics=result.diagnostics,
    )
