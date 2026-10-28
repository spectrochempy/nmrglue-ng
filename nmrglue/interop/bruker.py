"""Bruker/TopSpin adapters for the neutral interop layer.

The supported profiles are deliberately narrow: processed 1D data read
through :func:`nmrglue.fileio.bruker.read_pdata`, raw 1D FIDs, and raw 2D QF
SER data. Hypercomplex reconstruction and NMRPipe 2D export remain outside
this module's contract.

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


def _raw_number(dic, section, key):
    value = dic.get(section, {}).get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Bruker %s parameter %s must be numeric" % (section, key))
    if not np.isfinite(float(value)):
        raise ValueError("Bruker %s parameter %s must be finite" % (section, key))
    return float(value)


def _raw_integer(dic, section, key):
    value = dic.get(section, {}).get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Bruker %s parameter %s must be an integer" % (section, key))
    if not np.isfinite(float(value)) or int(value) != value:
        raise ValueError(
            "Bruker %s parameter %s must be a finite integer" % (section, key)
        )
    if int(value) <= 0:
        raise ValueError("Bruker %s parameter %s must be positive" % (section, key))
    return int(value)


def read_bruker_fid(
    dir=".",
    *,
    remove_digital_filter=False,
    shape=None,
    cplex=None,
    big=None,
    isfloat=None,
    read_pulseprogram=True,
    read_acqus=True,
):
    """Read a raw Bruker 1D FID as a neutral :class:`ReadResult`.

    No RG/NS normalization is applied. If ``remove_digital_filter`` is true,
    the existing Bruker correction is applied once and recorded in
    ``applied_corrections``.
    """
    if not os.path.isdir(dir):
        raise OSError("directory %s does not exist" % (dir,))

    dic, data = bruker.read(
        dir,
        shape=shape,
        cplex=cplex,
        big=big,
        isfloat=isfloat,
        read_pulseprogram=read_pulseprogram,
        read_acqus=read_acqus,
        read_procs=False,
    )
    data = np.asarray(data)
    if data.ndim != 1 or not np.issubdtype(data.dtype, np.number):
        raise ValueError("the raw Bruker 1D profile requires one numeric dimension")

    corrections = {
        "digital_filter": {
            "applied": bool(remove_digital_filter),
            "parameters": {
                key: dic.get("acqus", {}).get(key)
                for key in ("DECIM", "DSPFVS", "GRPDLY")
                if key in dic.get("acqus", {})
            },
        },
        "normalization": "none",
    }
    if remove_digital_filter:
        data = bruker.remove_digital_filter(dic, data, truncate=True)

    acqus = dic.get("acqus", {})
    required = ("TD", "SW_h", "SFO1", "O1", "AQ_mod")
    missing = tuple(name for name in required if acqus.get(name) is None)
    diagnostics = []
    if missing:
        diagnostics.append(
            Diagnostic(
                code="acquisition.missing-parameter",
                severity="warning",
                message="Raw Bruker acquisition parameters are incomplete.",
                context={"missing": missing},
            )
        )

    sw_h = _raw_number(dic, "acqus", "SW_h") if acqus.get("SW_h") is not None else None
    sfo1 = _raw_number(dic, "acqus", "SFO1") if acqus.get("SFO1") is not None else None
    o1 = _raw_number(dic, "acqus", "O1") if acqus.get("O1") is not None else None
    td = _raw_integer(dic, "acqus", "TD") if acqus.get("TD") is not None else None
    if td is not None and np.iscomplexobj(data) and td % 2:
        raise ValueError("Bruker acqus parameter TD must be even for complex data")
    if sw_h is not None and sw_h <= 0:
        raise ValueError("Bruker acqus parameter SW_h must be positive")

    values = None if sw_h is None else np.arange(data.size, dtype=float) / sw_h
    reference = (
        Reference(
            observation_frequency=sfo1,
            observation_frequency_unit="MHz" if sfo1 is not None else None,
            offset=None,
            offset_unit=None,
            source="acquisition",
        )
        if sfo1 is not None
        else None
    )
    axis = Axis(
        values=values,
        unit="s" if values is not None else None,
        label=acqus.get("NUC1"),
        domain="time",
        direction="increasing" if values is not None else "unknown",
        reference=reference,
    )
    aq_mod = acqus.get("AQ_mod")
    encodings = {0: "QF", 1: "QSIM", 2: "QSEQ", 3: "DQD"}
    encoding = (encodings.get(aq_mod, "undefined"),) if aq_mod is not None else ()
    dimensions = {
        "TD": td,
        "TDeff": acqus.get("TDeff"),
        "returned_points": int(data.size),
        "returned_raw_points": int(
            data.size * 2 if np.iscomplexobj(data) else data.size
        ),
        "complex_points": int(data.size),
    }
    acquisition = {
        key: acqus[key]
        for key in (
            "TD",
            "SW_h",
            "SFO1",
            "O1",
            "AQ_mod",
            "RG",
            "NS",
            "DECIM",
            "DSPFVS",
            "GRPDLY",
        )
        if key in acqus
    }
    if sw_h is not None:
        acquisition["spectral_width_hz"] = sw_h
        acquisition["dwell_time_s"] = 1.0 / sw_h
    if sfo1 is not None:
        acquisition["observation_frequency_mhz"] = sfo1
    if o1 is not None:
        acquisition["carrier_hz"] = o1
    if "NUC1" in acqus:
        acquisition["nucleus"] = acqus["NUC1"]
    return ReadResult(
        data=data,
        axes=(axis,),
        metadata=dic,
        components=(
            Component(name="complex" if np.iscomplexobj(data) else "real", data=data),
        ),
        applied_corrections=corrections,
        diagnostics=tuple(diagnostics),
        format="bruker-fid",
        source=dir,
        domains=("time",),
        encoding=encoding,
        dimensions=dimensions,
        acquisition=acquisition,
    )


def read_bruker_ser(
    dir=".",
    *,
    remove_digital_filter=False,
    shape=None,
    cplex=None,
    big=None,
    isfloat=None,
    read_pulseprogram=True,
    read_acqus=True,
):
    """Read a raw Bruker 2D QF SER as a neutral :class:`ReadResult`.

    The returned matrix keeps the historical reader's ``(F1, F2)`` storage
    order: rows are successive F1 traces and the last axis is contiguous F2
    data. QF indirect data are represented by one complex component because
    the direct dimension is complex and the indirect dimension is real. No
    RR/RI/IR/II components are fabricated.

    No RG/NS normalization, FFT, apodization, phasing, or linear prediction is
    applied. Digital-filter removal is explicit and recorded when requested.
    """
    if not os.path.isdir(dir):
        raise OSError("directory %s does not exist" % (dir,))

    dic, data = bruker.read(
        dir,
        bin_file="ser",
        shape=shape,
        cplex=cplex,
        big=big,
        isfloat=isfloat,
        read_pulseprogram=read_pulseprogram,
        read_acqus=read_acqus,
        read_procs=False,
    )
    data = np.asarray(data)
    if data.ndim != 2 or not np.issubdtype(data.dtype, np.number):
        raise ValueError("the raw Bruker 2D profile requires a numeric 2D SER")
    if not np.iscomplexobj(data):
        raise ValueError("the raw Bruker QF profile requires complex direct traces")

    acqus = dic.get("acqus", {})
    acqu2s = dic.get("acqu2s", dic.get("acqu2", {}))
    missing = []
    for section, names in (
        ("acqus", ("TD", "AQ_mod", "SW_h", "SFO1", "O1")),
        ("acqu2s", ("TD", "FnMODE", "SW", "SFO1", "O1")),
    ):
        values = acqus if section == "acqus" else acqu2s
        missing.extend(
            f"{section}.{name}" for name in names if values.get(name) is None
        )
    if missing:
        raise ValueError(
            "raw Bruker QF 2D acquisition metadata missing: %s" % ", ".join(missing)
        )

    aq_mod = acqus["AQ_mod"]
    fnmode = acqu2s["FnMODE"]
    if aq_mod != 3:
        raise ValueError(
            "raw Bruker 2D QF profile requires direct AQ_mod=3 (DQD), got %r"
            % (aq_mod,)
        )
    if fnmode != 1:
        raise ValueError(
            "raw Bruker 2D QF profile requires indirect FnMODE=1, got %r" % (fnmode,)
        )

    td_f2 = _raw_integer(dic, "acqus", "TD")
    td_f1 = _raw_integer({"acqus": acqu2s}, "acqus", "TD")
    sw_f2 = _raw_number(dic, "acqus", "SW_h")
    obs_f2 = _raw_number(dic, "acqus", "SFO1")
    car_f2 = _raw_number(dic, "acqus", "O1")
    sw_f1_ppm = _raw_number({"acqus": acqu2s}, "acqus", "SW")
    obs_f1 = _raw_number({"acqus": acqu2s}, "acqus", "SFO1")
    car_f1 = _raw_number({"acqus": acqu2s}, "acqus", "O1")
    if sw_f2 <= 0 or obs_f2 <= 0 or sw_f1_ppm <= 0 or obs_f1 <= 0:
        raise ValueError(
            "raw Bruker QF 2D spectral widths and observations must be positive"
        )

    effective_f1 = td_f1
    effective_f2 = td_f2 // 2
    if td_f2 % 2 or effective_f2 <= 0:
        raise ValueError("raw Bruker complex direct TD must be positive and even")
    expected_shape = (effective_f1, effective_f2)
    if data.shape != expected_shape:
        raise ValueError(
            "raw Bruker QF 2D shape %r does not match TD-derived shape %r"
            % (data.shape, expected_shape)
        )

    storage_shape = tuple(data.shape)
    corrections = {
        "digital_filter": {
            "applied": bool(remove_digital_filter),
            "parameters": {
                key: acqus[key] for key in ("DECIM", "DSPFVS", "GRPDLY") if key in acqus
            },
        },
        "normalization": "none",
        "processing": "none",
    }
    if remove_digital_filter:
        data = np.asarray(bruker.remove_digital_filter(dic, data, truncate=True))

    sw_f1 = sw_f1_ppm * obs_f1
    axes = (
        Axis(
            values=np.arange(data.shape[0], dtype=float) / sw_f1,
            unit="s",
            label=acqu2s.get("NUC1"),
            domain="time",
            direction="increasing",
            reference=Reference(
                observation_frequency=obs_f1,
                observation_frequency_unit="MHz",
                source="acquisition",
            ),
        ),
        Axis(
            values=np.arange(data.shape[1], dtype=float) / sw_f2,
            unit="s",
            label=acqus.get("NUC1"),
            domain="time",
            direction="increasing",
            reference=Reference(
                observation_frequency=obs_f2,
                observation_frequency_unit="MHz",
                source="acquisition",
            ),
        ),
    )
    dimensions = {
        "physical_shape": expected_shape,
        "storage_shape": storage_shape,
        "axis_order": ("F1", "F2"),
        "trace_order": "F1-major, F2-contiguous",
        "TD": (td_f1, td_f2),
        "TDeff": (acqu2s.get("TDeff"), acqus.get("TDeff")),
        "returned_shape": tuple(int(size) for size in data.shape),
        "component_basis": ("complex",),
    }
    acquisition = {
        "axes": (
            {
                "name": "F1",
                "TD": td_f1,
                "TDeff": acqu2s.get("TDeff"),
                "returned_points": int(data.shape[0]),
                "SW_ppm": sw_f1_ppm,
                "SW_hz": sw_f1,
                "dwell_time_s": 1.0 / sw_f1,
                "observation_frequency_mhz": obs_f1,
                "carrier_hz": car_f1,
                "FnMODE": fnmode,
            },
            {
                "name": "F2",
                "TD": td_f2,
                "TDeff": acqus.get("TDeff"),
                "returned_points": int(data.shape[1]),
                "SW_hz": sw_f2,
                "dwell_time_s": 1.0 / sw_f2,
                "observation_frequency_mhz": obs_f2,
                "carrier_hz": car_f2,
                "AQ_mod": aq_mod,
            },
        ),
        "RG": acqus.get("RG"),
        "NS": acqus.get("NS"),
        "original_shape": storage_shape,
    }
    return ReadResult(
        data=data,
        axes=axes,
        metadata=dic,
        components=(Component(name="complex", data=data),),
        applied_corrections=corrections,
        diagnostics=(),
        format="bruker-ser-qf-2d",
        source=dir,
        domains=("time", "time"),
        encoding=("QF", "DQD"),
        dimensions=dimensions,
        acquisition=acquisition,
    )


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
