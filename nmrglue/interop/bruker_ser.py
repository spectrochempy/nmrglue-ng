"""Normalize a complete, uncorrected Bruker QF SER for interop."""

from collections.abc import Mapping

import numpy as np

from .result import NormalizedAcquisition, ReadResult


def normalize_bruker_ser_qf(result: ReadResult) -> NormalizedAcquisition:
    """Expose a complete uniformly sampled QF SER as real and imaginary planes.

    The planes preserve the stored direct complex convention. Axes remain
    in F1/F2 order and no filter correction, scaling or FFT is applied.
    """
    if not isinstance(result, ReadResult) or result.format != "bruker-ser-qf-2d":
        raise ValueError("normalize_bruker_ser_qf requires a Bruker QF SER ReadResult")
    if result.metadata.get("acqus", {}).get("FnTYPE", 0) != 0:
        raise ValueError("Bruker QF normalization requires uniform sampling")
    corrections = result.applied_corrections
    digital_filter = corrections.get("digital_filter")
    if (
        set(corrections) != {"digital_filter", "normalization", "processing"}
        or corrections["normalization"] != "none"
        or corrections["processing"] != "none"
        or not isinstance(digital_filter, Mapping)
        or set(digital_filter) != {"applied", "parameters"}
        or digital_filter["applied"] is not False
        or not isinstance(digital_filter["parameters"], Mapping)
        or not set(digital_filter["parameters"]) <= {"DECIM", "DSPFVS", "GRPDLY"}
    ):
        raise ValueError("Bruker QF normalization requires an uncorrected SER")
    data = np.asarray(result.data)
    order = ("F1", "F2")
    if (
        data.ndim != 2 or min(data.shape) < 2
        or data.dtype.kind != "c" or data.dtype.itemsize not in (8, 16)
        or not np.isfinite(data).all()
        or result.domains != ("time", "time") or result.encoding != ("QF", "DQD")
        or result.dimensions.get("axis_order") != order
        or result.dimensions.get("trace_order") != "F1-major, F2-contiguous"
        or any(
            result.dimensions.get(key) != data.shape
            for key in ("physical_shape", "storage_shape", "returned_shape")
        )
    ):
        raise ValueError("Bruker QF normalization requires a complete complex F1/F2 grid")
    td = result.dimensions.get("TD")
    if td != (data.shape[0], 2 * data.shape[1]):
        raise ValueError("Bruker QF shape does not match the acquired TD")
    if (
        len(result.components) != 1 or result.components[0].name != "complex"
        or not np.array_equal(result.components[0].data, data)
    ):
        raise ValueError("Bruker QF complex component disagrees with the SER samples")
    descriptions = result.acquisition.get("axes", ())
    if len(descriptions) != 2 or len(result.axes) != 2:
        raise ValueError("Bruker QF normalization requires two calibrated axes")
    widths = []
    for name, size, axis, description in zip(order, data.shape, result.axes, descriptions, strict=True):
        width = description.get("SW_hz")
        if (
            description.get("name") != name
            or not isinstance(width, (int, float))
            or isinstance(width, bool) or not np.isfinite(width) or width <= 0
            or axis.unit != "s" or axis.domain != "time" or axis.direction != "increasing"
            or axis.values is None or axis.values.shape != (size,)
            or axis.values.dtype.kind not in "iuf"
            or not np.isfinite(axis.values).all()
            or not np.all(axis.values[1:] > axis.values[:-1])
        ):
            raise ValueError("Bruker QF normalization requires calibrated uniform time grids")
        with np.errstate(over="ignore"):
            expected = np.arange(size, dtype=float) / width
        if not np.isfinite(expected).all() or not np.allclose(
            axis.values, expected, rtol=1e-12, atol=0
        ):
            raise ValueError("Bruker QF time grid is inconsistent with spectral width")
        widths.append(width)

    dimensions = ("channels", *order)
    operation = {
        "name": "split-bruker-qf-direct-component",
        "stage": "acquisition",
        "input_dimensions": order,
        "output_dimensions": dimensions,
        "axis": "F2",
        "scale": None,
        "conjugation": "none",
        "sign": "none",
        "permutation": None,
        "evidence": "nmrglue.interop.read_bruker_ser",
    }
    return NormalizedAcquisition(
        data=np.stack((data.real, data.imag)),
        axes=result.axes,
        dimensions=dimensions,
        physical_dimensions=order,
        domains=("time", "time"),
        quadrature_mode="stored-components-2d",
        branch_order=("rr", "ri"),
        channel_axis=0,
        normalization_state="storage-normalized",
        normalization_profile="bruker-ser-qf-2d-v1",
        applied_operations=(operation,),
        provenance={"source": result.source, "format": result.format},
        acquisition={
            **result.acquisition,
            "spectral_width_hz": tuple(widths),
            "indirect_sampling": "qf",
        },
        metadata=result.metadata,
        encoding=("real", "complex"),
        diagnostics=result.diagnostics,
    )
