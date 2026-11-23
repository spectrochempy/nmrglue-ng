"""Bounded interop for regular two-dimensional JCAMP-DX FIDs."""

import os
import re
from numbers import Real

import numpy as np

from ..fileio import jcampdx
from .jcampdx import (
    _check_line_grid, _label, _number,
    _profile_numbers,
)
from .result import (
    Axis, Component, NormalizedAcquisition, ReadResult, Reference,
    _same_axis_grid, _unscaled_normalization_operation,
)


def _columns(record, key):
    values = tuple(value.strip() for value in record.split(","))
    if len(values) != 4:
        raise ValueError(f"JCAMP-DX FID 2D {key} requires four columns")
    return values


def _endpoints(block, key, first_page):
    positions = [index for index, name in enumerate(block["_records"]) if name == key]
    values = block.get(key, ())
    if len(positions) != len(values) or sum(i < first_page for i in positions) != 1:
        raise ValueError(f"JCAMP-DX FID 2D requires one global {key}")
    reference = _profile_numbers(_columns(values[0], key), key)[1]
    for position, value in zip(positions[1:], values[1:]):
        previous = next((name for name in reversed(block["_records"][:position])
                         if name in ("PAGE", "DATATABLE")), None)
        if previous != "PAGE" or _profile_numbers(_columns(value, key), key)[1] != reference:
            raise ValueError(f"JCAMP-DX FID 2D requires a common direct time grid ({key})")


def _geometry(block):
    if (
        "".join(_label(block, "DATATYPE").upper().split()) != "NDNMRFID"
        or "".join(_label(block, "NTUPLES").upper().split()) != "NDNMRFID"
        or _label(block, "DATACLASS").upper() != "NTUPLES"
        or _number(block, "NUMDIM") != 2
        or _columns(_label(block, "SYMBOL"), "SYMBOL") != ("T1", "T2", "R", "I")
        or _columns(_label(block, "VARTYPE"), "VARTYPE")
        != ("INDEPENDENT", "INDEPENDENT", "DEPENDENT", "DEPENDENT")
    ):
        raise ValueError("JCAMP-DX FID 2D requires T1/T2/R/I NTUPLES")
    units = _columns(_label(block, "UNITS"), "UNITS")
    if (len(units) != 4 or any(unit.upper() not in ("SECONDS", "SECOND", "S") for unit in units[:2])
            or not units[2] or units[2] != units[3]):
        raise ValueError("JCAMP-DX FID 2D requires seconds and matching R/I units")
    sizes = _profile_numbers(_columns(_label(block, "VARDIM"), "VAR_DIM"), "VAR_DIM")
    if (len(sizes) != 4 or any(n < 2 or not n.is_integer() for n in sizes)
            or sizes[1:] != (sizes[1],) * 3):
        raise ValueError("JCAMP-DX FID 2D requires equally sized R/I traces")
    if not block.get("FIRST"):
        raise ValueError("JCAMP-DX FID 2D requires FIRST")
    first = _profile_numbers(_columns(block["FIRST"][0], "FIRST"), "FIRST")
    last = _profile_numbers(_columns(_label(block, "LAST"), "LAST"), "LAST")
    factors = _profile_numbers(_columns(_label(block, "FACTOR"), "FACTOR"), "FACTOR")
    if (len(first) != 4 or len(last) != 4 or len(factors) != 4
            or first[:2] != (0, 0) or any(b <= a for a, b in zip(first[:2], last[:2]))
            or min(factors[:2]) <= 0 or 0 in factors[2:]):
        raise ValueError("JCAMP-DX FID 2D requires zero-based increasing time grids and nonzero factors")
    shape = tuple(int(n) for n in sizes[:2])
    steps = tuple(last[i] / (shape[i] - 1) for i in range(2))
    if not np.isfinite([1 / step for step in steps]).all():
        raise ValueError("JCAMP-DX FID 2D sampling rates must be finite")
    return shape, last[:2], factors, steps


def _axes(block, shape, last):
    reference = None
    if ".OBSERVEFREQUENCY" in block:
        frequency = _number(block, ".OBSERVEFREQUENCY")
        if frequency <= 0:
            raise ValueError("JCAMP-DX requires positive .OBSERVE FREQUENCY")
        reference = Reference(observation_frequency=frequency, observation_frequency_unit="MHz")
    return tuple(
        Axis(values=np.linspace(0, end, size), unit="s", label=role, domain="time",
             direction="increasing", reference=reference if role == "F2" else None)
        for role, size, end in zip(("F1", "F2"), shape, last)
    )


def _digital_filter(block):
    descriptor = {"applied": False}
    if "$GRPDLY" in block:
        delay = _number(block, "$GRPDLY")
        descriptor.update(group_delay_points=delay if delay >= 0 else None, source="$GRPDLY")
    return descriptor


def read_jcampdx_fid_2d(filename):
    """Read interleaved R/I pages on a complete regular T1/T2 time grid.

    Parameters
    ----------
    filename : str or path-like
        File containing exactly one two-dimensional NMR FID NTUPLES block.
        Symbols must be T1, T2, R, I, with zero-based regular time grids in
        seconds and one R/I pair per indirect increment.

    Returns
    -------
    result : ReadResult
        Stored complex samples, F1/F2 time axes and original metadata.
        Page decoding alone does not establish the indirect quadrature.
    """
    blocks = jcampdx.read_blocks(filename, _record_order=True)
    candidates = [b for b in blocks if any("".join(v.upper().split()) == "NDNMRFID"
                                         for v in b.get("DATATYPE", ()))]
    if len(candidates) != 1:
        raise ValueError("JCAMP-DX requires exactly one nD NMR FID block")
    block = candidates[0]
    shape, last, factors, steps = _geometry(block)
    records = block["_records"]
    selected = [key for key in records if key in ("NTUPLES", "PAGE", "DATATABLE", "ENDNTUPLES")]
    if selected != ["NTUPLES", *(["PAGE", "DATATABLE"] * (2 * shape[0])), "ENDNTUPLES"]:
        raise ValueError("JCAMP-DX FID 2D requires one R/I pair per indirect increment")
    if any(key in block for key in ("XYDATA", "XYPOINTS", "PEAKTABLE")):
        raise ValueError("JCAMP-DX FID 2D contains extra tables")
    first_page = records.index("PAGE")
    _endpoints(block, "FIRST", first_page)
    _endpoints(block, "LAST", first_page)
    tables, pages = block["DATATABLE"], block["PAGE"]
    if len(tables) != 2 * shape[0] or len(pages) != len(tables):
        raise ValueError("JCAMP-DX FID 2D page count disagrees with VAR_DIM")
    for index in range(shape[0]):
        symbols = []
        for page, table in zip(pages[2 * index:2 * index + 2], tables[2 * index:2 * index + 2]):
            match = re.fullmatch(r"T1\s*=\s*(\S+)", page.strip())
            try:
                time = float(match[1]) if match else np.nan
            except ValueError:
                time = np.nan
            if not np.isclose(time, index * steps[0], rtol=1e-12, atol=steps[0] * 1e-9):
                raise ValueError("JCAMP-DX FID 2D PAGE disagrees with its indirect time grid")
            header = "".join(table.partition("\n")[0].split())
            match = re.fullmatch(r"\(T2\+\+\(([RI])\.\.\1\)\),PROFILE", header)
            if match is None:
                raise ValueError("JCAMP-DX FID 2D requires regular T2 R/I PROFILE tables")
            symbols.append(match[1])
        if sorted(symbols) != ["I", "R"]:
            raise ValueError("JCAMP-DX FID 2D requires both R and I at every increment")
    parts = jcampdx.getdataarray(block, True,
                                _check_xydata_x=_check_line_grid(0, steps[1], factors[1]),
                                _xydata_max_points=shape[1])
    if (not isinstance(parts, dict) or any(len(parts[k]) != shape[0] for k in ("real", "imaginary"))
            or any(a.shape != (shape[1],) for k in parts for a in parts[k])):
        raise ValueError("JCAMP-DX FID 2D samples disagree with VAR_DIM")
    data = np.stack(parts["real"]) + 1j * np.stack(parts["imaginary"])
    if not np.isfinite(data).all():
        raise ValueError("JCAMP-DX FID 2D requires finite complex samples")
    metadata = {k: v for k, v in block.items() if k not in ("DATATABLE", "_records")}
    return ReadResult(
        data=data, axes=_axes(block, shape, last), metadata=metadata,
        components=(Component("complex", data),), diagnostics=(), format="jcampdx-fid-2d",
        source=os.fspath(filename), domains=("time", "time"), encoding=("unknown", "complex"),
        dimensions={"points": shape},
        applied_corrections={"real_factor": factors[2], "imaginary_factor": factors[3]},
    )


def normalize_jcampdx_fid_2d(
    result, *, quadrature, conjugation,
    confirm_adjacent_pairs=False, indirect_dwell_s=None,
):
    """Confirm QF or adjacent phase-sensitive pairs without processing.

    Parameters
    ----------
    result : ReadResult
        Result from :func:`read_jcampdx_fid_2d`.
    quadrature : {"qf", "echo-antiecho", "states", "states-tppi", "tppi", "qseq"}
        Explicit confirmation of one complex direct trace per indirect
        increment. The declared acquisition scheme must also be not phase
        sensitive. Paired modes require the matching declared scheme,
        simultaneous DQD acquisition, confirmed adjacent pairs and a caller
        supplied physical indirect dwell.
        TPPI and QSEQ require their matching declaration, direct DQD and an
        explicit physical dwell between successive traces. QSEQ applies its
        ++-- sign pattern to produce the common real-F1 TPPI convention.
    conjugation : {"none", "conjugate"}
        Retain or conjugate the stored complex samples. The caller must
        establish the appropriate sign convention for the acquisition.
    confirm_adjacent_pairs : bool, optional
        Must be True for phase-sensitive pairs. The first and second stored traces
        of each pair become the two complex channels, without reconstruction.
    indirect_dwell_s : float, optional
        Physical time between phase-sensitive pairs, in seconds, established
        from acquisition provenance. The stored T1 row grid does not establish
        this physical dwell. For QF, optionally replace the declared T1 step
        with a caller-established physical dwell; adjacent-pair confirmation
        remains invalid. Without this option QF keeps the declared grid.
        TPPI/QSEQ always require this physical dwell between successive traces.

    Returns
    -------
    normalized : NormalizedAcquisition
        QF planes, four States-family planes or two complex echo/anti-echo channels with
        calibrated time grids, or a real-F1 TPPI matrix. No FFT, digital-filter correction,
        phasing, windowing or chemical-shift referencing is applied. A
        nonnegative Bruker GRPDLY, when present, is retained as an unapplied
        delay in complex direct points; a negative sentinel remains unknown.
    """
    if not isinstance(result, ReadResult) or result.format != "jcampdx-fid-2d":
        raise ValueError("requires a jcampdx-fid-2d ReadResult")
    scheme = "".join(_label(result.metadata, ".ACQUISITIONSCHEME").upper().split())
    if quadrature == "qf":
        if scheme != "NOTPHASESENSITIVE":
            raise ValueError("JCAMP-DX FID 2D normalization requires declared QF (not phase sensitive)")
        if confirm_adjacent_pairs is not False:
            raise ValueError("JCAMP-DX QF does not accept adjacent-pair confirmation")
    elif quadrature in ("echo-antiecho", "states", "states-tppi"):
        declared = {"echo-antiecho": "ECHOANTIECHO", "states": "STATES", "states-tppi": "STATESTPPI"}
        if re.sub(r"[-/]", "", scheme) != declared[quadrature]:
            raise ValueError(f"JCAMP-DX requires declared {quadrature}")
        if "".join(_label(result.metadata, ".ACQUISITIONMODE").upper().split()) != "SIMULTANEOUS(DQD)":
            raise ValueError("JCAMP-DX paired FID requires direct simultaneous DQD")
        if confirm_adjacent_pairs is not True:
            raise ValueError("JCAMP-DX paired FID requires confirm_adjacent_pairs=True")
        if (isinstance(indirect_dwell_s, (bool, np.bool_))
                or not isinstance(indirect_dwell_s, Real)
                or not np.isfinite(indirect_dwell_s) or indirect_dwell_s <= 0):
            raise ValueError("JCAMP-DX requires a finite positive indirect_dwell_s")
    elif quadrature in ("tppi", "qseq"):
        if scheme != quadrature.upper():
            raise ValueError(f"JCAMP-DX requires declared {quadrature}")
        if "".join(_label(result.metadata, ".ACQUISITIONMODE").upper().split()) != "SIMULTANEOUS(DQD)":
            raise ValueError("JCAMP-DX real F1 requires direct simultaneous DQD")
        if confirm_adjacent_pairs is not False:
            raise ValueError("JCAMP-DX real F1 does not accept adjacent-pair confirmation")
    else:
        raise ValueError("JCAMP-DX supports only QF, TPPI, QSEQ or confirmed echo/anti-echo, States or States-TPPI normalization")
    if conjugation not in ("none", "conjugate"):
        raise ValueError("JCAMP-DX FID 2D requires explicit conjugation='none' or 'conjugate'")
    shape, last, factors, steps = _geometry(result.metadata)
    axes = _axes(result.metadata, shape, last)
    data = result.data
    if (data.shape != shape or data.dtype.kind != "c" or not np.isfinite(data).all()
            or result.dimensions != {"points": shape} or result.domains != ("time", "time")
            or result.encoding != ("unknown", "complex") or len(result.axes) != 2
            or any(not _same_axis_grid(a, b) or a.reference != b.reference for a, b in zip(result.axes, axes))
            or len(result.components) != 1 or result.components[0].name != "complex"
            or not np.array_equal(result.components[0].data, data)
            or result.applied_corrections != {"real_factor": factors[2], "imaginary_factor": factors[3]}):
        raise ValueError("JCAMP-DX FID 2D description disagrees with its samples")
    data = data.conj() if conjugation == "conjugate" else data
    if quadrature in ("tppi", "qseq"):
        return _normalize_real_f1(result, data, axes, steps, conjugation, indirect_dwell_s, quadrature)
    if quadrature != "qf":
        return _normalize_paired_fid(result, data, axes, steps, conjugation, indirect_dwell_s, quadrature)
    operation = _unscaled_normalization_operation(
        name="normalize-jcampdx-fid-2d", stage="acquisition", input_dimensions=("F1", "F2"),
        output_dimensions=("channels", "F1", "F2"), axis="F2", conjugation=conjugation,
        evidence="NTUPLES T1/T2 grids, declared non-phase-sensitive scheme and explicit QF confirmation",
    )
    dwell_record, operations = {}, (operation,)
    if indirect_dwell_s is not None:
        if isinstance(indirect_dwell_s, (bool, np.bool_)) or not isinstance(indirect_dwell_s, Real):
            raise ValueError("JCAMP-DX QF requires a finite positive indirect_dwell_s")
        try:
            dwell = float(indirect_dwell_s)
        except (ValueError, OverflowError) as exc:
            raise ValueError("JCAMP-DX QF indirect dwell is not representable") from exc
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            grid = np.arange(shape[0], dtype=float) * dwell
            width = np.float64(1) / dwell
        if (not np.isfinite(dwell) or dwell <= 0 or not np.isfinite(width) or width <= 0
                or not np.isfinite(grid).all() or not np.all(grid[1:] > grid[:-1])):
            raise ValueError("JCAMP-DX QF requires representable physical time grids")
        dwell_record = {"declared_indirect_dwell_s": steps[0],
                        "indirect_dwell_s": dwell, "indirect_dwell_source": "caller"}
        steps = (dwell, steps[1])
        axes = (Axis(values=grid, unit="s", label="F1", domain="time",
                     direction="increasing", reference=axes[0].reference), axes[1])
        correction = _unscaled_normalization_operation(
            name="calibrate-jcampdx-qf-dwell", stage="acquisition",
            input_dimensions=("channels", "F1", "F2"), output_dimensions=("channels", "F1", "F2"),
            axis="F1", conjugation="none", evidence="caller-established physical indirect dwell",
        )
        correction["time_calibration"] = dict(dwell_record)
        operations += (correction,)
    return NormalizedAcquisition(
        data=np.stack((data.real, data.imag)), axes=axes,
        dimensions=("channels", "F1", "F2"), physical_dimensions=("F1", "F2"),
        domains=("time", "time"), encoding=("real", "complex"),
        quadrature_mode="stored-components-2d", branch_order=("rr", "ri"), channel_axis=0,
        normalization_state="storage-normalized", normalization_profile="jcampdx-fid-qf-2d-v1",
        applied_operations=operations, provenance={"source": result.source, "format": result.format},
        acquisition={"spectral_width_hz": tuple(1 / step for step in steps),
                     "dwell_time_s": steps, "indirect_sampling": "qf",
                     "digital_filter": _digital_filter(result.metadata), **dwell_record},
        metadata=result.metadata, diagnostics=result.diagnostics,
    )


def _normalize_real_f1(result, data, axes, steps, conjugation, dwell, quadrature):
    if isinstance(dwell, (bool, np.bool_)) or not isinstance(dwell, Real):
        raise ValueError("JCAMP-DX real F1 requires a finite positive indirect_dwell_s")
    try:
        dwell = float(dwell)
    except (ValueError, OverflowError) as exc:
        raise ValueError("JCAMP-DX real F1 indirect dwell is not representable") from exc
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        grid = np.arange(data.shape[0], dtype=float) * dwell
        width = np.float64(1) / dwell
    if (not np.isfinite(dwell) or dwell <= 0 or not np.isfinite(width) or width <= 0
            or not np.isfinite(grid).all() or not np.all(grid[1:] > grid[:-1])):
        raise ValueError("JCAMP-DX real F1 requires representable physical time grids")
    work = data.copy()
    if quadrature == "qseq":
        work[2::4] *= -1
        work[3::4] *= -1
    operation = _unscaled_normalization_operation(
        name=f"normalize-jcampdx-{quadrature}-traces", stage="acquisition",
        input_dimensions=("F1", "F2"), output_dimensions=("F1", "F2"),
        axis="F2", conjugation=conjugation,
        evidence="declared real F1 scheme, direct DQD and caller-established physical dwell",
    )
    operation["time_calibration"] = {
        "declared_indirect_dwell_s": steps[0], "indirect_dwell_s": dwell,
        "indirect_dwell_source": "caller",
    }
    operations = (operation,)
    if quadrature == "qseq":
        alternation = _unscaled_normalization_operation(
            name="alternate-jcampdx-qseq-pairs", stage="acquisition",
            input_dimensions=("F1", "F2"), output_dimensions=("F1", "F2"),
            axis="F1", conjugation="none", evidence="declared QSEQ ++-- convention",
        )
        alternation["sign"] = "alternate-pairs"
        operations += (alternation,)
    return NormalizedAcquisition(
        data=work,
        axes=(Axis(values=grid, unit="s", label="F1", domain="time",
                   direction="increasing", reference=axes[0].reference), axes[1]),
        dimensions=("F1", "F2"), physical_dimensions=("F1", "F2"),
        domains=("time", "time"), encoding=("tppi", "complex"),
        quadrature_mode="tppi-stored-2d", branch_order=("complex",),
        normalization_state="storage-normalized",
        normalization_profile=f"jcampdx-fid-{quadrature}-2d-v1",
        applied_operations=operations,
        provenance={"source": result.source, "format": result.format},
        acquisition={"spectral_widths_hz": (float(width), 1 / steps[1]),
                     "spectral_width_hz": (float(width), 1 / steps[1]),
                     "dwell_time_s": (dwell, steps[1]),
                     "physical_indirect_increments": data.shape[0],
                     "indirect_sampling": quadrature,
                     "declared_indirect_dwell_s": steps[0],
                     "indirect_dwell_s": dwell, "indirect_dwell_source": "caller",
                     "qseq_alternation": "applied" if quadrature == "qseq" else "not_applicable",
                     "digital_filter": _digital_filter(result.metadata)},
        metadata=result.metadata, diagnostics=result.diagnostics,
    )


def _normalize_paired_fid(result, data, axes, steps, conjugation, dwell, quadrature):
    if data.shape[0] < 4 or data.shape[0] % 2:
        raise ValueError("JCAMP-DX paired FID requires at least two complete adjacent pairs")
    dwell = float(dwell)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        grid = np.arange(data.shape[0] // 2, dtype=float) * dwell
        width = np.float64(1) / dwell
    if (not np.isfinite(width) or width <= 0 or not np.isfinite(grid).all()
            or not np.all(grid[1:] > grid[:-1])):
        raise ValueError("JCAMP-DX paired FID requires representable physical time grids")
    axes = (Axis(values=grid, unit="s", label="F1", domain="time", direction="increasing"), axes[1])
    operation = _unscaled_normalization_operation(
        name=f"pair-jcampdx-{quadrature}-traces", stage="acquisition",
        input_dimensions=("F1", "F2"), output_dimensions=("channels", "F1", "F2"),
        axis="F1", conjugation=conjugation,
        evidence=f"declared {quadrature} DQD, caller-confirmed adjacent pairs and physical dwell",
    )
    echo_antiecho = quadrature == "echo-antiecho"
    components = (np.stack((data[::2], data[1::2])) if echo_antiecho else
                  np.stack((data[::2].real, data[::2].imag, data[1::2].real, data[1::2].imag)))
    return NormalizedAcquisition(
        data=components, axes=axes,
        dimensions=("channels", "F1", "F2"), physical_dimensions=("F1", "F2"),
        domains=("time", "time"), encoding=("echo-antiecho", "complex") if echo_antiecho else ("complex", "complex"),
        quadrature_mode="echo-antiecho-stored-2d" if echo_antiecho else "stored-components-2d",
        branch_order=("first", "second") if echo_antiecho else ("rr", "ri", "ir", "ii"), channel_axis=0,
        normalization_state="storage-normalized", normalization_profile=f"jcampdx-fid-{quadrature}-2d-v1",
        applied_operations=(operation,), provenance={"source": result.source, "format": result.format},
        acquisition={"spectral_width_hz": (float(width), 1 / steps[1]),
                     "dwell_time_s": (dwell, steps[1]), "indirect_sampling": quadrature,
                     "indirect_dwell_s": dwell, "indirect_dwell_source": "caller",
                     "branch_order": "stored", "reconstruction": "not_applied",
                     **({"tppi_alternation": "declared_not_applied"} if quadrature == "states-tppi" else {}),
                     "digital_filter": _digital_filter(result.metadata)},
        metadata=result.metadata, diagnostics=result.diagnostics,
    )
