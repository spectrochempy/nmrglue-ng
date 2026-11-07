"""Interoperability for regular real 1D JCAMP-DX NMR spectra."""

import os

import numpy as np

from ..fileio import jcampdx
from .result import Axis, Component, NormalizedAcquisition, ReadResult, Reference


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

    def check_x(raw, index):
        observed = raw * xfactor
        expected = first + index * step
        # Encoders can quantize line anchors to integer multiples of XFACTOR.
        tolerance = abs(xfactor) * 0.5 if raw.is_integer() else 0.0
        if not np.isclose(observed, expected, rtol=1e-12, atol=tolerance):
            raise ValueError("JCAMP-DX XYDATA line abscissa disagrees with its grid")

    data = jcampdx.getdataarray(block, _check_xydata_x=check_x, _xydata_max_points=int(points))
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
    if (
        observed.unit != axis.unit or observed.domain != axis.domain
        or observed.direction != axis.direction or observed.reference != axis.reference
        or not np.array_equal(observed.values, axis.values)
    ):
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
