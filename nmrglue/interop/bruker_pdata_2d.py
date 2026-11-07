"""Complete Bruker 2D processed int32 planes with four stored components."""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np

from ..fileio import bruker
from .bruker import _build_processed_axis, _raw_number
from .result import Component, NormalizedAcquisition, ReadResult

_FORMAT = "bruker-pdata-2d"
_COMPONENTS = ("2rr", "2ri", "2ir", "2ii")
_AXES = ("F1", "F2")
_DOMAINS = ("frequency", "frequency")
_ENCODING = ("stored", "stored")


def _integer(metadata, section, key):
    value = _raw_number(metadata, section, key)
    if value is None or not value.is_integer():
        raise ValueError(f"Bruker {section} requires integer {key}")
    return int(value)


def _geometry(metadata):
    if "proc3s" in metadata or "proc4s" in metadata:
        raise ValueError("Bruker 2D profile requires exactly two processing dimensions")
    shape = []
    tiles = []
    for section in ("proc2s", "procs"):
        if (
            "PPARMOD" in metadata.get(section, {})
            and _integer(metadata, section, "PPARMOD") != 1
        ):
            raise ValueError(f"Bruker {section} PPARMOD must describe a 2D dataset")
        size = _integer(metadata, section, "SI")
        tile = _integer(metadata, section, "XDIM")
        if size < 2 or tile < 1 or size % tile:
            raise ValueError(f"Bruker {section} requires complete SI/XDIM tiles")
        if (
            _integer(metadata, section, "STSI") != size
            or _integer(metadata, section, "STSR") != 0
            or _integer(metadata, section, "FTSIZE") != size
            or _integer(metadata, section, "FT_mod") not in (4, 6)
        ):
            raise ValueError(f"Bruker {section} requires a complete Fourier grid")
        shape.append(size)
        tiles.append(tile)
    byte_order = _integer(metadata, "procs", "BYTORDP")
    if byte_order not in (0, 1):
        raise ValueError("Bruker BYTORDP must be 0 or 1")
    for section in ("proc2s", "procs"):
        if _integer(metadata, section, "DTYPP") != 0:
            raise ValueError("Bruker 2D profile requires int32 DTYPP=0")
        if _integer(metadata, section, "BYTORDP") != byte_order:
            raise ValueError("Bruker BYTORDP disagrees across dimensions")
    return tuple(shape), tuple(tiles), bool(byte_order)


def _axes(metadata, shape):
    axes = []
    for section, size in zip(("proc2s", "procs"), shape, strict=True):
        axis, _ = _build_processed_axis({"procs": metadata[section]}, size)
        if axis.values is None or not np.all(np.diff(axis.values) < 0):
            raise ValueError(
                f"Bruker {section} requires a calibrated decreasing Hz axis"
            )
        axes.append(axis)
    return tuple(axes)


def _corrections(metadata, scale_data):
    if type(scale_data) is not bool:
        raise ValueError("Bruker scale_data must be a bool")
    corrections = {"scale_data": scale_data}
    if scale_data:
        exponent = _integer(metadata, "procs", "NC_proc")
        if not -1022 <= exponent <= 1022:
            raise ValueError("Bruker NC_proc is outside the supported scaling range")
        corrections["NC_proc"] = exponent
    return corrections


def read_bruker_pdata_2d(directory, *, scale_data=True):
    """Read four complete Bruker processed int32 planes in F1, F2 order.

    Component names are the original file names. Applying storage scaling
    multiplies every plane by 2**NC_proc from procs.
    """
    path = Path(directory)
    if not path.is_dir():
        raise OSError(f"directory {path} does not exist")
    metadata = bruker.read_procs_file(path)
    shape, tiles, big = _geometry(metadata)
    corrections = _corrections(metadata, scale_data)
    expected_size = math.prod(shape) * 4
    for name in _COMPONENTS:
        file = path / name
        if not file.is_file() or file.stat().st_size != expected_size:
            raise ValueError(
                f"Bruker {name} is missing or disagrees with the declared payload size"
            )
    axes = _axes(metadata, shape)
    components = []
    for name in _COMPONENTS:
        _, data = bruker.read_pdata_binary(path / name, shape, tiles, big=big)
        if data.shape != shape:
            raise ValueError(f"Bruker {name} disagrees with the declared plane shape")
        if scale_data:
            with np.errstate(over="ignore"):
                data = bruker.scale_pdata(metadata, data)
            if not np.isfinite(data).all():
                raise ValueError(
                    f"Bruker {name} storage scaling produced non-finite values"
                )
        components.append(Component(name=name, data=data))
    return ReadResult(
        data=components[0].data,
        axes=axes,
        metadata=metadata,
        components=tuple(components),
        applied_corrections=corrections,
        diagnostics=(),
        format=_FORMAT,
        source=os.fspath(directory),
        domains=_DOMAINS,
        encoding=_ENCODING,
        dimensions={"axis_order": _AXES, "shape": shape, "submatrix_shape": tiles},
    )


def normalize_bruker_pdata_2d(result):
    """Stack the four named planes along a channel axis without mixing them."""
    if not isinstance(result, ReadResult) or result.format != _FORMAT:
        raise ValueError(
            "normalize_bruker_pdata_2d requires a bruker-pdata-2d ReadResult"
        )
    shape, tiles, _ = _geometry(result.metadata)
    expected_dimensions = {
        "axis_order": _AXES,
        "shape": shape,
        "submatrix_shape": tiles,
    }
    if (
        result.domains != _DOMAINS
        or result.encoding != _ENCODING
        or dict(result.dimensions) != expected_dimensions
    ):
        raise ValueError("Bruker 2D plane geometry disagrees with its metadata")
    axes = _axes(result.metadata, shape)
    if len(result.axes) != 2 or any(
        (got.unit, got.label, got.domain, got.direction, got.reference)
        != (
            expected.unit,
            expected.label,
            expected.domain,
            expected.direction,
            expected.reference,
        )
        or not np.array_equal(got.values, expected.values)
        for got, expected in zip(result.axes, axes, strict=True)
    ):
        raise ValueError("Bruker 2D axes disagree with their calibration")
    corrections = _corrections(
        result.metadata, result.applied_corrections.get("scale_data")
    )
    if dict(result.applied_corrections) != corrections:
        raise ValueError("Bruker 2D scaling disagrees with its metadata")
    if tuple(component.name for component in result.components) != _COMPONENTS:
        raise ValueError(
            "Bruker 2D requires the four stored components in file-name order"
        )
    planes = tuple(component.data for component in result.components)
    kind = "f" if corrections["scale_data"] else "i"
    width = 8 if corrections["scale_data"] else 4
    if (
        any(
            plane.shape != shape
            or plane.dtype.kind != kind
            or plane.dtype.itemsize != width
            or not np.isfinite(plane).all()
            for plane in planes
        )
        or result.data.dtype != planes[0].dtype
        or not np.array_equal(result.data, planes[0])
    ):
        raise ValueError(
            "Bruker 2D component data disagrees with the stored-plane profile"
        )
    dimensions = ("channels", *_AXES)
    operation = {
        "name": "stack-bruker-processed-planes",
        "stage": "processing",
        "input_dimensions": _AXES,
        "output_dimensions": dimensions,
        "axis": None,
        "scale": None,
        "conjugation": "none",
        "sign": "none",
        "permutation": None,
        "evidence": "nmrglue.interop.read_bruker_pdata_2d",
    }
    return NormalizedAcquisition(
        data=np.stack(planes),
        axes=axes,
        dimensions=dimensions,
        physical_dimensions=_AXES,
        domains=_DOMAINS,
        quadrature_mode="stored-components-2d",
        branch_order=_COMPONENTS,
        normalization_state="storage-normalized",
        normalization_profile="bruker-pdata-2d-int32-v1",
        applied_operations=(operation,),
        provenance={"source": os.fspath(result.source), "format": result.format},
        acquisition={"storage_scaling": corrections, "reference_source": "processing"},
        metadata=result.metadata,
        encoding=result.encoding,
        diagnostics=result.diagnostics,
        channel_axis=0,
    )
