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


def read_bruker_ser_storage(directory):
    """Read a standard Bruker SER as scalar traces, including row padding.

    The acquisition status files describe the stored words and retain the
    acquisition mode, indirect sizes and referencing parameters. Trace count
    comes from the binary file and its 1024-byte-aligned trace stride.
    """
    directory = Path(directory)
    metadata = bruker.read_acqus_file(directory)
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
        words = bruker.get_data(stream, big=bool(byte_order), isfloat=data_type == 2)
    data = words.reshape(trace_count, trace_bytes // word_bytes)
    for filename in ("nuslist", "pulseprogram"):
        ancillary = directory / filename
        if ancillary.is_file():
            metadata[filename + "_raw"] = ancillary.read_bytes()
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
