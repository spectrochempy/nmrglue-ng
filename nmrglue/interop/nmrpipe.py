"""Experimental export of a one-dimensional :class:`ReadResult` to NMRPipe.

This module adapts the neutral result contract to the existing NMRPipe writer;
it does not implement another binary writer or a processing engine.  The first
supported profile is one time-domain axis with normalized acquisition metadata:

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


def _provenance_comment(result: ReadResult) -> str:
    corrections = json.dumps(
        result.applied_corrections, sort_keys=True, separators=(",", ":"), default=str
    )
    source = os.fspath(result.source)
    comment = f"source={source}; corrections={corrections}; storage=float32"
    if len(comment.encode("utf-8")) > 160:
        raise ValueError("ReadResult provenance does not fit NMRPipe FDCOMMENT")
    return comment


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
    float32_limit = np.finfo(np.float32).max
    source_real = np.asarray(result.data.real)
    source_imag = np.asarray(result.data.imag) if np.iscomplexobj(result.data) else None
    if (
        not np.isfinite(source_real).all()
        or np.abs(source_real).max(initial=0) > float32_limit
        or (
            source_imag is not None
            and (
                not np.isfinite(source_imag).all()
                or np.abs(source_imag).max(initial=0) > float32_limit
            )
        )
    ):
        raise ValueError("ReadResult data cannot be represented as finite float32")

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
        data = np.asarray(result.data, dtype=np.complex64)
        encoding = "QSIM"
    else:
        if result.encoding[0] not in ("QF", "real"):
            raise ValueError("real raw export requires QF or real encoding")
        data = np.asarray(result.data, dtype=np.float32)
        encoding = "QF"
    return data, acquisition, encoding


def write_readresult_nmrpipe(
    result: ReadResult,
    filename: str | os.PathLike[str],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write a validated 1D time-domain ``ReadResult`` as an NMRPipe file.

    The function returns the generated header dictionary for inspection.  It
    raises ``ValueError`` rather than inventing defaults when the normalized
    acquisition metadata or coordinate convention is incomplete.
    """
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
