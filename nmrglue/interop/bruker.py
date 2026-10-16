"""Bruker/TopSpin processed 1D adapter for the neutral interop layer.

The first supported profile is deliberately narrow: processed 1D data read
through :func:`nmrglue.fileio.bruker.read_pdata`.  No raw, 2D, HyperComplex
reconstruction, or universal component handling is promised.

The Hz axis is a *normative* scale, not a guess.  With ``OFFSET`` (ppm),
``SF`` (MHz) and ``SW_p`` (Hz) from ``procs``/``procNs`` and ``N`` points
actually read (``data.shape[0]``), the point frequencies are::

    f[i] = OFFSET * SF - i * (SW_p / N)

so the first point is exactly ``OFFSET * SF`` Hz and the direction is strictly
decreasing.  This is the Hz scale of
``fileiobase.uc_from_udic(bruker.guess_udic(dic, data, pdata=True))`` when the
three processing parameters are present and valid.  The convention (first point
at ``OFFSET``, bin ``SW_p / SI``) is documented in the Bruker *TopSpin -
Processing Commands and Parameters* manual (doc H9776SA3_7_007) and is already
relied on by ``nmrglue.fileio.bruker``.

A present parameter must be numeric and finite, ``SF`` and ``SW_p`` must be
strictly positive, and the computed axis must stay finite: otherwise a
``ValueError`` is raised, so the announced equivalence can never silently
degrade into a non-usable axis.
"""

from __future__ import annotations

import math
import os

import numpy as np

from ..fileio import bruker
from .result import Axis, Component, Diagnostic, ReadResult, Reference

_FORMAT = "bruker-pdata"
_PRIMARY = "1r"


def read_bruker_pdata(
    dir=".",
    scale_data=True,
    bin_files=None,
    procs_files=None,
    read_procs=True,
    acqus_files=None,
    read_acqus=True,
    shape=None,
    submatrix_shape=None,
    all_components=False,
    big=None,
    isfloat=None,
):
    """Read Bruker processed data as a neutral :class:`ReadResult`.

    The historical :func:`nmrglue.fileio.bruker.read_pdata` is called
    unchanged; this function adds name-to-array association, the normative Hz
    axis, and diagnostics.  It never duplicates parsing or scaling.

    Parameters
    ----------
    dir : str
        Bruker processed directory (for example ``.../pdata/1``).
    scale_data, bin_files, procs_files, read_procs, acqus_files, read_acqus, \
shape, submatrix_shape, all_components, big, isfloat
        Forwarded to :func:`nmrglue.fileio.bruker.read_pdata`.  Unsupported
        keyword arguments are rejected by the signature itself.

    Returns
    -------
    result : ReadResult

    Raises
    ------
    OSError
        If ``dir`` does not exist (historical behavior).
    ValueError
        For interop-contract violations: no primary ``1r`` component, an
        ``all_components=False`` call whose effective files are not exactly
        ``["1r"]``, duplicated component names, a reader return whose shape
        cannot be associated with the requested files, a non-1D result, or a
        present-but-incoherent processing parameter (non-numeric, non-finite,
        ``SF <= 0``, ``SW_p <= 0``, or an axis that would not stay finite).
    """
    if not os.path.isdir(dir):
        raise OSError("directory %s does not exist" % (dir,))

    candidates = _resolve_candidates(bin_files, all_components)
    effective = [name for name in candidates if os.path.isfile(os.path.join(dir, name))]
    missing = [name for name in candidates if name not in effective]

    if not all_components and effective != [_PRIMARY]:
        raise ValueError(
            "all_components=False requires the effective files to be exactly "
            "%r; got %r" % ([_PRIMARY], effective)
        )
    if _PRIMARY not in effective:
        raise ValueError(
            "the interop bruker-pdata profile requires the primary %r component, "
            "which is absent from %r" % (_PRIMARY, effective)
        )

    dic, returned = bruker.read_pdata(
        dir=dir,
        bin_files=effective,
        procs_files=procs_files,
        read_procs=read_procs,
        acqus_files=acqus_files,
        read_acqus=read_acqus,
        scale_data=scale_data,
        shape=shape,
        submatrix_shape=submatrix_shape,
        all_components=all_components,
        big=big,
        isfloat=isfloat,
    )

    arrays = _normalize_components(returned, len(effective))
    components = tuple(
        Component(name=name, data=array) for name, array in zip(effective, arrays)
    )
    by_name = {component.name: component for component in components}
    data = by_name[_PRIMARY].data

    if data.ndim != 1:
        raise ValueError(
            "the interop bruker-pdata profile supports 1D data only, got ndim=%d"
            % (data.ndim,)
        )

    diagnostics = []
    if missing:
        diagnostics.append(
            Diagnostic(
                code="component.missing",
                severity="warning",
                message=(
                    "Some requested component files are absent and were not fabricated."
                ),
                context={
                    "expected": tuple(candidates),
                    "missing": tuple(missing),
                },
            )
        )

    axis, axis_diagnostics = _build_axis(dic, data)
    diagnostics.extend(axis_diagnostics)

    applied_corrections = {"scale_data": bool(scale_data)}
    if scale_data:
        nc_proc = dic.get("procs", {}).get("NC_proc")
        if nc_proc is not None:
            applied_corrections["NC_proc"] = nc_proc

    return ReadResult(
        data=data,
        axes=(axis,),
        metadata=dic,
        components=components,
        applied_corrections=applied_corrections,
        diagnostics=tuple(diagnostics),
        format=_FORMAT,
        source=dir,
    )


def _resolve_candidates(bin_files, all_components):
    """Return the ordered candidate file names before existence filtering."""
    if bin_files is None:
        candidates = ["1r", "1i"] if all_components else [_PRIMARY]
    else:
        candidates = list(bin_files)
    seen = []
    for name in candidates:
        if name in seen:
            raise ValueError(
                "duplicate component name %r in %r is ambiguous for the "
                "name-to-array mapping" % (name, candidates)
            )
        seen.append(name)
    return candidates


def _normalize_components(returned, count):
    """Return a list of ``count`` ndarrays from the historical reader return.

    ``bruker.read_pdata`` returns a bare ``ndarray`` (not a list) when the
    effective list holds a single element.
    """
    if count == 1:
        if isinstance(returned, (list, tuple)):
            if len(returned) != 1:
                raise ValueError(
                    "reader returned %d components for a single file" % (len(returned),)
                )
            returned = returned[0]
        if not isinstance(returned, np.ndarray):
            raise ValueError(
                "reader returned %r for a single file, expected an ndarray"
                % (type(returned).__name__,)
            )
        return [returned]

    if isinstance(returned, (list, tuple)) and len(returned) == count:
        if not all(isinstance(array, np.ndarray) for array in returned):
            raise ValueError(
                "reader returned non-ndarray components for %d files" % (count,)
            )
        return list(returned)

    raise ValueError(
        "reader returned %r components for %d requested files"
        % (len(returned) if isinstance(returned, (list, tuple)) else 1, count)
    )


def _build_axis(dic, data):
    """Build the single 1D frequency axis and its diagnostics."""
    diagnostics = []
    procs = dic.get("procs", {})
    n = int(data.shape[0])

    if n == 0:
        raise ValueError("cannot build a 1D axis for zero-length data")

    offset = procs.get("OFFSET")
    sf = procs.get("SF")
    sw_p = procs.get("SW_p")
    label = _axis_label(dic)

    for name, value in (("OFFSET", offset), ("SF", sf), ("SW_p", sw_p)):
        if value is None:
            continue
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ValueError("incoherent Bruker parameter %s=%r" % (name, value))
    if sw_p is not None and float(sw_p) <= 0.0:
        raise ValueError("incoherent Bruker parameter SW_p=%r (must be > 0)" % (sw_p,))
    if sf is not None and float(sf) <= 0.0:
        raise ValueError("incoherent Bruker parameter SF=%r (must be > 0)" % (sf,))

    reference = _build_reference(offset, sf)

    missing = [
        name
        for name, value in (("OFFSET", offset), ("SF", sf), ("SW_p", sw_p))
        if value is None
    ]
    if missing:
        diagnostics.append(
            Diagnostic(
                code="axis.missing-parameter",
                severity="warning",
                message=(
                    "Processed-axis parameters are missing; no Hz axis was fabricated."
                ),
                context={"missing": tuple(missing)},
            )
        )
        return (
            Axis(
                values=None,
                unit=None,
                label=label,
                domain="unknown",
                direction="unknown",
                reference=reference,
            ),
            diagnostics,
        )

    values = float(offset) * float(sf) - np.arange(n, dtype=np.float64) * (
        float(sw_p) / n
    )
    if not np.isfinite(values).all():
        raise ValueError(
            "the processed axis overflows to non-finite values with OFFSET=%r, "
            "SF=%r, SW_p=%r and N=%d" % (offset, sf, sw_p, n)
        )

    si = procs.get("SI")
    if isinstance(si, (int, float)) and not isinstance(si, bool) and int(si) != n:
        diagnostics.append(
            Diagnostic(
                code="axis.size-mismatch",
                severity="warning",
                message=(
                    "Processed size SI differs from the number of points read; "
                    "the axis uses the read length N."
                ),
                context={"SI": si, "N": n},
            )
        )

    return (
        Axis(
            values=values,
            unit="Hz",
            label=label,
            domain="frequency",
            direction="decreasing",
            reference=reference,
        ),
        diagnostics,
    )


def _build_reference(offset, sf):
    """Build a (possibly partial) processing reference, or ``None``."""
    if offset is None and sf is None:
        return None
    return Reference(
        observation_frequency=float(sf) if sf is not None else None,
        observation_frequency_unit="MHz" if sf is not None else None,
        offset=float(offset) if offset is not None else None,
        offset_unit="ppm" if offset is not None else None,
        source="processing",
    )


def _axis_label(dic):
    """Return the nucleus label from acquisition or processing, if any."""
    acqus = dic.get("acqus", {})
    if "NUC1" in acqus:
        return acqus["NUC1"]
    procs = dic.get("procs", {})
    if "AXNUC" in procs:
        return procs["AXNUC"]
    return None
