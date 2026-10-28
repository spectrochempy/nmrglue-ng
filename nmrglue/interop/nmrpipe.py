"""Experimental export of raw 1D and QF 2D :class:`ReadResult` to NMRPipe.

This module adapts the neutral result contract to the existing NMRPipe writer;
it does not implement another binary writer or a processing engine.  Supported
profiles are one time-domain axis or strict raw QF 2D with normalized
acquisition metadata:

``spectral_width_hz``, ``observation_frequency_mhz`` and ``carrier_hz``.

NMRPipe stores samples as IEEE ``float32`` values.  Complex samples are stored
as the existing writer's concatenated real and imaginary vectors.  The input is
therefore explicitly converted to ``complex64`` or ``float32`` before calling
``pipe.write``.  The generated header records the source and applied
transformations in its bounded provenance fields.
"""

from __future__ import annotations

import json
import numbers
import os
from pathlib import Path
from typing import Any

import numpy as np

from nmrglue.fileio import fileiobase, pipe

from .result import ReadResult


_REQUIRED_ACQUISITION = (
    "spectral_width_hz",
    "observation_frequency_mhz",
    "carrier_hz",
)


def _finite_positive(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"ReadResult acquisition {name!r} must be numeric")
    value = float(value)
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"ReadResult acquisition {name!r} must be finite and positive")
    return value


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise ValueError(f"ReadResult acquisition {name!r} must be numeric")
    value = float(value)
    if not np.isfinite(value):
        raise ValueError(f"ReadResult acquisition {name!r} must be finite")
    return value


def _provenance_comment(result: ReadResult, *, compact: bool = False) -> str:
    corrections = json.dumps(
        result.applied_corrections, sort_keys=True, separators=(",", ":"), default=str
    )
    source = os.fspath(result.source)
    if compact:
        source = os.path.basename(os.path.normpath(source)) or source
        summary = {}
        for key, value in result.applied_corrections.items():
            if isinstance(value, dict) and "applied" in value:
                summary[key] = value["applied"]
            else:
                summary[key] = value
        corrections = json.dumps(
            summary, sort_keys=True, separators=(",", ":"), default=str
        )
        shape = "x".join(str(size) for size in result.data.shape)
        comment = f"source={source}; corrections={corrections}; shape={shape}; storage=float32"
    else:
        comment = f"source={source}; corrections={corrections}; storage=float32"
    if len(comment.encode("utf-8")) > 160:
        raise ValueError("ReadResult provenance does not fit NMRPipe FDCOMMENT")
    return comment


def _validate_float32_data(data: np.ndarray) -> None:
    """Reject samples that cannot be represented by NMRPipe float32 storage."""
    float32_limit = np.finfo(np.float32).max
    real = np.asarray(data.real)
    imag = np.asarray(data.imag) if np.iscomplexobj(data) else None
    if (
        not np.isfinite(real).all()
        or np.abs(real).max(initial=0) > float32_limit
        or (
            imag is not None
            and (
                not np.isfinite(imag).all()
                or np.abs(imag).max(initial=0) > float32_limit
            )
        )
    ):
        raise ValueError("ReadResult data cannot be represented as finite float32")


def _as_float32_data(data: np.ndarray) -> np.ndarray:
    """Convert validated data to the existing NMRPipe storage dtype."""
    _validate_float32_data(data)
    return np.asarray(data, dtype=np.complex64 if np.iscomplexobj(data) else np.float32)


def _validate_result(result: ReadResult) -> tuple[np.ndarray, dict[str, float], str]:
    if not isinstance(result, ReadResult):
        raise TypeError("result must be a ReadResult")
    if result.data.ndim != 1:
        raise ValueError("NMRPipe ReadResult export currently supports 1D data only")
    if result.data.size == 0:
        raise ValueError("NMRPipe ReadResult export requires at least one sample")
    if len(result.axes) != 1:
        raise ValueError("NMRPipe ReadResult export requires exactly one axis")
    if result.domains != ("time",):
        raise ValueError("NMRPipe raw export requires domains=('time',)")
    if len(result.encoding) != 1:
        raise ValueError("NMRPipe raw export requires exactly one encoding")
    axis = result.axes[0]
    if axis.domain != "time" or axis.unit != "s" or axis.values is None:
        raise ValueError("NMRPipe raw export requires a time axis in seconds")
    if axis.values.shape != result.data.shape:
        raise ValueError("ReadResult time axis and data sizes do not match")
    if not np.issubdtype(result.data.dtype, np.number):
        raise ValueError("ReadResult data must have a numeric dtype")
    missing = [
        key for key in _REQUIRED_ACQUISITION if result.acquisition.get(key) is None
    ]
    if missing:
        raise ValueError(
            f"ReadResult acquisition metadata missing: {', '.join(missing)}"
        )
    acquisition = {
        "spectral_width_hz": _finite_positive(
            result.acquisition["spectral_width_hz"], "spectral_width_hz"
        ),
        "observation_frequency_mhz": _finite_positive(
            result.acquisition["observation_frequency_mhz"],
            "observation_frequency_mhz",
        ),
        "carrier_hz": _finite(result.acquisition["carrier_hz"], "carrier_hz"),
    }
    dwell = 1.0 / acquisition["spectral_width_hz"]
    expected = np.arange(result.data.size, dtype=float) * dwell
    if not np.allclose(axis.values, expected, rtol=1e-12, atol=1e-15):
        raise ValueError("ReadResult time axis is inconsistent with spectral_width_hz")

    if np.iscomplexobj(result.data):
        if result.encoding[0] not in ("QSIM", "complex"):
            raise ValueError("complex raw export requires QSIM or complex encoding")
        data = _as_float32_data(result.data)
        encoding = "QSIM"
    else:
        if result.encoding[0] not in ("QF", "real"):
            raise ValueError("real raw export requires QF or real encoding")
        data = _as_float32_data(result.data)
        encoding = "QF"
    return data, acquisition, encoding


def _validate_qf_2d_result(
    result: ReadResult,
) -> tuple[np.ndarray, tuple[dict[str, float], dict[str, float]]]:
    """Validate and normalize the narrow raw QF 2D export contract."""
    if result.data.ndim != 2:
        raise ValueError("QF 2D NMRPipe export requires 2D data")
    if any(size == 0 for size in result.data.shape):
        raise ValueError("QF 2D NMRPipe export requires non-empty data")
    if len(result.axes) != 2 or result.domains != ("time", "time"):
        raise ValueError("QF 2D NMRPipe export requires two time axes")
    if result.encoding != ("QF", "DQD"):
        raise ValueError("QF 2D NMRPipe export requires encoding=('QF', 'DQD')")
    if not np.iscomplexobj(result.data):
        raise ValueError("QF 2D NMRPipe export requires complex direct traces")
    if len(result.components) != 1 or result.components[0].name != "complex":
        raise ValueError("QF 2D export requires one named 'complex' component")
    if result.components[0].data.shape != result.data.shape:
        raise ValueError("QF 2D component and data shapes do not match")

    shape = tuple(int(size) for size in result.data.shape)
    if tuple(result.dimensions.get("returned_shape", ())) != shape:
        raise ValueError("QF 2D returned_shape must match the ReadResult data")
    physical_shape = tuple(result.dimensions.get("physical_shape", ()))
    storage_shape = tuple(result.dimensions.get("storage_shape", ()))
    td = tuple(result.dimensions.get("TD", ()))
    if len(physical_shape) != 2 or len(storage_shape) != 2 or len(td) != 2:
        raise ValueError("QF 2D physical_shape, storage_shape and TD are required")
    if any(size <= 0 for size in physical_shape + storage_shape + td):
        raise ValueError("QF 2D dimensions must be positive")
    if td[1] % 2:
        raise ValueError("QF 2D direct TD must be even")
    raw_shape = (td[0], td[1] // 2)
    if physical_shape != raw_shape or storage_shape != raw_shape:
        raise ValueError(
            "QF 2D physical/storage shapes must match TD-derived raw shape"
        )
    if result.dimensions.get("axis_order") != ("F1", "F2"):
        raise ValueError("QF 2D export requires axis_order=('F1', 'F2')")
    if result.dimensions.get("trace_order") != "F1-major, F2-contiguous":
        raise ValueError("QF 2D export requires the declared F1-major trace order")

    axes_metadata = result.acquisition.get("axes")
    if not isinstance(axes_metadata, (tuple, list)) or len(axes_metadata) != 2:
        raise ValueError("QF 2D acquisition requires axes metadata for F1 and F2")
    normalized = []
    for index, (axis, metadata) in enumerate(zip(result.axes, axes_metadata)):
        if axis.values is None or axis.unit != "s" or axis.domain != "time":
            raise ValueError("QF 2D axes must be time coordinates in seconds")
        if axis.values.shape != (shape[index],):
            raise ValueError("QF 2D axis and data shapes do not match")
        if not isinstance(metadata, dict):
            raise ValueError("QF 2D axis metadata must be mappings")
        sw = _finite_positive(metadata.get("SW_hz"), f"axes[{index}].SW_hz")
        obs = _finite_positive(
            metadata.get("observation_frequency_mhz"),
            f"axes[{index}].observation_frequency_mhz",
        )
        carrier = _finite(metadata.get("carrier_hz"), f"axes[{index}].carrier_hz")
        expected = np.arange(shape[index], dtype=float) / sw
        if not np.allclose(axis.values, expected, rtol=1e-12, atol=1e-15):
            raise ValueError(f"QF 2D axis {index} is inconsistent with SW_hz")
        normalized.append({"sw_hz": sw, "obs_mhz": obs, "carrier_hz": carrier})

    return _as_float32_data(result.data), (normalized[0], normalized[1])


def write_readresult_nmrpipe(
    result: ReadResult,
    filename: str | os.PathLike[str],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write a validated 1D or raw QF 2D ``ReadResult`` as an NMRPipe file.

    The function returns the generated header dictionary for inspection.  It
    raises ``ValueError`` rather than inventing defaults when the normalized
    acquisition metadata or coordinate convention is incomplete.
    """
    if not isinstance(result, ReadResult):
        raise TypeError("result must be a ReadResult")
    if result.data.ndim == 2:
        data, axes = _validate_qf_2d_result(result)
        udic = fileiobase.create_blank_udic(2)
        for index, axis_metadata in enumerate(axes):
            udic[index].update(
                size=data.shape[index],
                complex=index == 1,
                sw=axis_metadata["sw_hz"],
                obs=axis_metadata["obs_mhz"],
                car=axis_metadata["carrier_hz"],
                label=result.axes[index].label or ("F1", "F2")[index],
                time=True,
                freq=False,
                encoding="magnitude" if index == 0 else "direct",
            )
        header = pipe.create_dic(udic)
        header["FDSRCNAME"] = "nmrglue-ng"
        header["FDTITLE"] = "ReadResult QF 2D"
        header["FDCOMMENT"] = _provenance_comment(result, compact=True)
        pipe.write(str(Path(filename)), header, data, overwrite=overwrite)
        return header

    data, acquisition, encoding = _validate_result(result)
    udic = fileiobase.create_blank_udic(1)
    udic[0].update(
        size=data.size,
        complex=np.iscomplexobj(data),
        sw=acquisition["spectral_width_hz"],
        obs=acquisition["observation_frequency_mhz"],
        car=acquisition["carrier_hz"],
        label=result.axes[0].label or "X",
        time=True,
        freq=False,
        encoding="direct",
    )
    header = pipe.create_dic(udic)
    header["FDSRCNAME"] = "nmrglue-ng"
    header["FDTITLE"] = f"ReadResult {encoding} 1D"
    header["FDCOMMENT"] = _provenance_comment(result)
    pipe.write(str(Path(filename)), header, data, overwrite=overwrite)
    return header
