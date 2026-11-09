"""Complete Bruker 2D processed int32 planes with four stored components."""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np

from ..fileio import bruker
from .bruker import _build_processed_axis, _processed_acquisition_axis, _raw_number, _require_bruker_2d
from .result import Axis, Component, NormalizedAcquisition, ReadResult

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


def _geometry(metadata, *, stored=False):
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
        if stored and "STSI" in metadata[section]:
            size = _integer(metadata, section, "STSI") or size
        tile = _integer(metadata, section, "XDIM")
        if size < (1 if stored else 2) or tile < 1 or size % tile:
            raise ValueError(
                f"Bruker {section} requires the plane size to be divisible by XDIM"
            )
        shape.append(size)
        tiles.append(tile)
    byte_order = _integer(metadata, "procs", "BYTORDP")
    if byte_order not in (0, 1):
        raise ValueError("Bruker BYTORDP must be 0 or 1")
    data_type = _integer(metadata, "procs", "DTYPP")
    if data_type not in (0, 2):
        raise ValueError("Bruker DTYPP must be 0 (int32) or 2 (float64)")
    for key, expected in (("BYTORDP", byte_order), ("DTYPP", data_type)):
        if key in metadata["proc2s"] and _integer(metadata, "proc2s", key) != expected:
            raise ValueError(f"Bruker {key} disagrees across dimensions")
    return tuple(shape), tuple(tiles), bool(byte_order), data_type == 2


def _profile_geometry(metadata):
    shape, tiles, big, isfloat = _geometry(metadata)
    for index, section in enumerate(("proc2s", "procs")):
        if (
            _integer(metadata, section, "STSI") != shape[index]
            or _integer(metadata, section, "STSR") != 0
            or _integer(metadata, section, "FTSIZE") != shape[index]
            or _integer(metadata, section, "FT_mod") not in (4, 6)
        ):
            raise ValueError(f"Bruker {section} requires a complete Fourier grid")
        if _integer(metadata, section, "DTYPP") != 0:
            raise ValueError("Bruker 2D profile requires int32 DTYPP=0")
        if _integer(metadata, section, "BYTORDP") != big:
            raise ValueError("Bruker BYTORDP disagrees across dimensions")
    return shape, tiles, big, isfloat


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


def _read_components(path, names, shape, tiles, big, isfloat, *, scale_metadata=None):
    expected_size = math.prod(shape) * (8 if isfloat else 4)
    components = []
    for name in names:
        file = path / name
        if not file.is_file() or file.stat().st_size != expected_size:
            raise ValueError(
                f"Bruker {name} is missing or disagrees with the declared payload size"
            )
        _, data = bruker.read_pdata_binary(file, shape, tiles, big=big, isfloat=isfloat)
        if data.shape != shape:
            raise ValueError(f"Bruker {name} disagrees with the declared plane shape")
        if scale_metadata is not None:
            with np.errstate(over="ignore"):
                data = bruker.scale_pdata(scale_metadata, data)
            if not np.isfinite(data).all():
                raise ValueError(
                    f"Bruker {name} storage scaling produced non-finite values"
                )
        components.append(Component(name=name, data=data))
    return tuple(components)


def read_bruker_pdata_2d_storage(directory):
    """Read available Bruker pdata planes at their stored scale.

    Return named int32 or float64 matrices in row/column order after undoing
    disk tiling, using STSI for stored strip sizes when present. The first
    available plane in 2rr, 2ri, 2ir, 2ii order is also exposed as data.
    Processing parameters are retained in metadata.
    """
    path = Path(directory)
    if not path.is_dir():
        raise OSError(f"directory {path} does not exist")
    metadata = bruker.read_procs_file(path)
    shape, tiles, big, isfloat = _geometry(metadata, stored=True)
    names = tuple(name for name in _COMPONENTS if (path / name).exists())
    if not names:
        raise ValueError("Bruker pdata contains no recognized 2D component")
    components = _read_components(path, names, shape, tiles, big, isfloat)
    return ReadResult(
        data=components[0].data,
        axes=(Axis(label="row"), Axis(label="column")),
        metadata=metadata,
        components=components,
        applied_corrections={},
        diagnostics=(),
        format="bruker-pdata-2d-storage",
        source=os.fspath(directory),
        domains=("unknown", "unknown"),
        dimensions={
            "axis_order": ("row", "column"),
            "shape": shape,
            "submatrix_shape": tiles,
        },
    )


def read_bruker_pdata_2d(directory, *, scale_data=True, acqus_files=None, procs_files=None):
    """Read four complete Bruker processed int32 planes in F1, F2 order.

    Component names are the original file names. Applying storage scaling
    multiplies every plane by 2**NC_proc from procs.
    """
    path = Path(directory)
    if not path.is_dir():
        raise OSError(f"directory {path} does not exist")
    metadata = bruker.read_procs_file(
        path, None if procs_files is None else list(procs_files),
    )
    if acqus_files is not None:
        metadata.update(bruker.read_acqus_file(path.parent.parent, acqus_files))
    shape, tiles, big, isfloat = _profile_geometry(metadata)
    corrections = _corrections(metadata, scale_data)
    axes = _axes(metadata, shape)
    components = _read_components(
        path,
        _COMPONENTS,
        shape,
        tiles,
        big,
        isfloat,
        scale_metadata=metadata if scale_data else None,
    )
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


def normalize_bruker_pdata_2d(result, *, axis_reference=None):
    """Stack the stored planes or opt into the calibrated TopSpin spectrum.

    With axis_reference="acquisition" or "processing", return two complex
    channels with receiver gain applied once and the selected calibrated axes.
    The default retains the four stored planes and their storage scale.
    """
    if axis_reference not in (None, "acquisition", "processing"):
        raise ValueError("Bruker pdata axis_reference must be processing or acquisition")
    if not isinstance(result, ReadResult) or result.format != _FORMAT:
        raise ValueError(
            "normalize_bruker_pdata_2d requires a bruker-pdata-2d ReadResult"
        )
    shape, tiles, _, _ = _profile_geometry(result.metadata)
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
    data = np.stack(planes) if axis_reference is None else None
    mode, branches, encoding = "stored-components-2d", _COMPONENTS, result.encoding
    profile = "bruker-pdata-2d-int32-v1"
    acquisition = {"storage_scaling": corrections, "reference_source": "processing"}
    if axis_reference is not None:
        metadata = result.metadata
        _require_bruker_2d(metadata)
        if not corrections["scale_data"]:
            raise ValueError("Bruker public pdata requires NC_proc storage scaling")
        gain = _raw_number(metadata, "acqus", "RG")
        if gain is None or gain <= 0 or not np.isfinite(1 / gain):
            raise ValueError("Bruker public pdata requires a positive finite gain correction")
        direct = _raw_number(metadata, "acqus", "SFO1")
        indirect = _raw_number(metadata, "acqu2s", "SFO1")
        if direct is None or indirect is None or min(direct, indirect) <= 0:
            raise ValueError("Bruker public pdata requires positive SFO1 for both axes")
        if axis_reference == "acquisition":
            axes = tuple(
                _processed_acquisition_axis(
                    {"acqus": metadata[acqu], "procs": metadata[proc]}, size, axis.label,
                )[0]
                for acqu, proc, size, axis in zip(
                    ("acqu2s", "acqus"), ("proc2s", "procs"), shape, axes, strict=True,
                )
            )
        rr, ri, ir, ii = planes
        with np.errstate(over="ignore", invalid="ignore"):
            data = np.stack((rr + 1j * ir, ri + 1j * ii)) / gain
        if not np.isfinite(data).all():
            raise ValueError("Bruker receiver-gain normalization produced non-finite values")
        mode, branches, encoding = "complex-channel-pair-2d", ("S_R", "S_I"), ("complex", "complex")
        profile = "bruker-pdata-2d-public-v1"
        operation.update(
            name="pack-bruker-processed-channels", scale=1 / gain,
            source_components=_COMPONENTS, receiver_gain=gain,
        )
        acquisition.update(
            reference_source=axis_reference, acquisition_frequency_mhz=(indirect, direct),
            normalization="receiver-gain", complex_axis="F1",
        )
    return NormalizedAcquisition(
        data=data,
        axes=axes,
        dimensions=dimensions,
        physical_dimensions=_AXES,
        domains=_DOMAINS,
        quadrature_mode=mode,
        branch_order=branches,
        normalization_state="storage-normalized",
        normalization_profile=profile,
        applied_operations=(operation,),
        provenance={"source": os.fspath(result.source), "format": result.format},
        acquisition=acquisition,
        metadata=result.metadata,
        encoding=encoding,
        diagnostics=result.diagnostics,
        channel_axis=0,
    )
