"""Optional, additive interoperability layer for nmrglue-ng readers.

``nmrglue.interop`` exposes a neutral :class:`ReadResult` built from existing
readers.  It is additive: the historical ``(dic, data)`` APIs are unchanged,
and no SpectroChemPy, NDDataset, Pint, or CSDM dependency is imported.

The first supported profile is Bruker/TopSpin processed 1D data::

    import nmrglue as ng

    result = ng.interop.read_bruker_pdata(".../pdata/1", scale_data=True)
    dic, data = ng.bruker.read_pdata(".../pdata/1", scale_data=True)
"""

from __future__ import annotations

from .bruker import read_bruker_fid, read_bruker_pdata
from .nmrpipe import write_readresult_nmrpipe
from .result import (
    DIAGNOSTIC_CONTEXT_SCHEMA,
    Axis,
    Component,
    Diagnostic,
    ReadResult,
    Reference,
)

__all__ = [
    "Axis",
    "Component",
    "DIAGNOSTIC_CONTEXT_SCHEMA",
    "Diagnostic",
    "ReadResult",
    "Reference",
    "read_bruker_pdata",
    "read_bruker_fid",
    "write_readresult_nmrpipe",
]
