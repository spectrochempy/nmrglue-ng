"""Acquisition traces in file order, with scalar words left intact."""

from __future__ import annotations

import os
import struct
from pathlib import Path

from ..fileio import bruker, varian
from .bruker import _raw_integer, _raw_number
from .result import Axis, Component, ReadResult


def _trace_result(path, data, metadata, format_name, **dimensions):
    return ReadResult(
        data=data,
        axes=(Axis(label="stored trace"), Axis(label="stored word")),
        metadata=metadata,
        components=(Component("stored-words", data),),
        applied_corrections={},
        diagnostics=(),
        format=format_name,
        source=path,
        domains=("unknown", "unknown"),
        dimensions={
            "axis_order": ("trace", "word"),
            "shape": data.shape,
            **dimensions,
        },
    )


def read_bruker_ser_storage(
    directory, *, acqus_files=None, procs_files=None, states_tppi_only=False,
    read_pulseprogram=False,
):
    """Read a standard Bruker SER as scalar traces, including row padding.

    The acquisition status files describe the stored words and retain the
    acquisition mode, indirect sizes and referencing parameters. Trace count
    comes from the binary file and its 1024-byte-aligned trace stride.
    Explicit parameter file lists may be supplied. Set
    ``states_tppi_only=True`` to preflight the acquisition mode before
    decoding the binary.
    """
    directory = Path(directory)
    metadata = bruker.read_acqus_file(directory, acqus_files)
    if states_tppi_only and (
        metadata.get("acqus", {}).get("FnTYPE", 0) != 0
        or metadata.get("acqus", {}).get("AQ_mod") != 3
        or metadata.get("acqu2s", {}).get("FnMODE") != 5
        or (directory / "nuslist").exists()
    ):
        raise ValueError("Bruker SER requires uniform States-TPPI with direct DQD")
    if procs_files is not None:
        metadata.update(bruker.read_procs_file(directory, list(procs_files)))
    td = _raw_integer(metadata, "acqus", "TD")
    byte_order = _raw_number(metadata, "acqus", "BYTORDA")
    data_type = _raw_number(metadata, "acqus", "DTYPA")
    if td is None or byte_order not in (0, 1) or data_type not in (0, 2):
        raise ValueError("Bruker SER storage requires TD, BYTORDA and supported DTYPA")
    word_bytes = 8 if data_type == 2 else 4
    trace_bytes = ((td * word_bytes + 1023) // 1024) * 1024
    path = directory / "ser"
    with path.open("rb") as stream:
        trace_count, remainder = divmod(os.fstat(stream.fileno()).st_size, trace_bytes)
        if not trace_count or remainder:
            raise ValueError("Bruker SER size disagrees with the aligned trace stride")
        if states_tppi_only and (
            td < 4 or td % 2 or trace_count < 4 or trace_count % 2
            or trace_count != _raw_integer(metadata, "acqu2s", "TD")
        ):
            raise ValueError("States-TPPI requires complete paired TD geometry")
        words = bruker.get_data(stream, big=bool(byte_order), isfloat=data_type == 2)
    data = words.reshape(trace_count, trace_bytes // word_bytes)
    for filename in ("nuslist", "pulseprogram"):
        ancillary = directory / filename
        if ancillary.is_file():
            metadata[filename + "_raw"] = ancillary.read_bytes()
    if read_pulseprogram and (directory / "pulseprogram").is_file():
        metadata["pprog"] = bruker.read_pprog(directory / "pulseprogram")
    return _trace_result(path, data, metadata, "bruker-ser-storage", declared_td=td)


def read_agilent_fid_storage(directory):
    """Read Agilent/Varian FID scalar traces in block and trace order.

    Return the binary file and block headers alongside procpar. Each row
    contains the original scalar words, even for complex or hypercomplex
    encodings. The binary geometry determines the shape.
    """
    directory = Path(directory)
    path = directory / "fid"
    with path.open("rb") as stream:
        try:
            metadata = varian.fileheader2dic(varian.get_fileheader(stream))
        except struct.error as exc:
            raise ValueError("Agilent FID requires a complete file header") from exc
        blocks = metadata["nblocks"]
        traces = metadata["ntraces"]
        words = metadata["np"]
        headers = metadata["nbheaders"]
        dtype = varian.find_dtype(metadata)
        trace_bytes = words * dtype.itemsize
        block_bytes = headers * 28 + traces * trace_bytes
        if (
            min(blocks, traces, words) < 1
            or headers not in (1, 2)
            or metadata["ebytes"] != dtype.itemsize
            or metadata["tbytes"] != trace_bytes
            or metadata["bbytes"] != block_bytes
            or os.fstat(stream.fileno()).st_size != 32 + blocks * block_bytes
        ):
            raise ValueError(
                "Agilent FID size disagrees with the declared block geometry"
            )
        metadata["blockheader"], data = varian.get_nblocks_ntraces(
            stream, blocks, traces, words, headers, dtype, True
        )
    procpar = directory / "procpar"
    if procpar.is_file():
        metadata["procpar"] = varian.read_procpar(procpar)
    return _trace_result(
        path,
        data,
        metadata,
        "agilent-fid-storage",
        blocks=blocks,
        traces_per_block=traces,
    )
